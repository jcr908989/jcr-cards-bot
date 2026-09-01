import time
import threading
import requests
from bs4 import BeautifulSoup
import streamlit as st

# Configuración de la interfaz
st.title("🤖 JCR Cards Bot - Panel 24/7")
st.subheader("Control de Stock Automático")

# Campos para rellenar desde la interfaz
token = st.text_input("Telegram Bot Token", type="password")
chat_id = st.text_input("Telegram Chat ID")

# Selector de tiempo interactivo (en minutos)
intervalo_minutos = st.slider(
    "Tiempo entre comprobaciones (minutos)", 
    min_value=1, 
    max_value=60, 
    value=10
)

# Caja de texto grande para poner múltiples enlaces (uno por línea)
urls_texto = st.text_area(
    "Enlaces a vigilar (pon uno por línea)",
    "https://www.inside-the-box.de\nhttps://www.pokemoncenter.com"
)

# Estado global para el bot
if "corriendo" not in st.session_state:
    st.session_state.corriendo = False

def enviar_telegram(mensaje, t_token, t_chat):
    if not t_token or not t_chat:
        return
    url = f"https://api.telegram.org/bot{t_token}/sendMessage"
    payload = {"chat_id": t_chat, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

def bucle_verificacion(t_token, t_chat, lista_urls, segundos_espera):
    # Cabecera simulando un navegador real para evitar bloqueos
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }
    
    # Palabras que indican que SÍ hay stock o preventa disponible
    palabras_stock = [
        "add to cart", "añadir al carrito", "añadir a la cesta", 
        "comprar", "pre-order", "preventa", "in den warenkorb", 
        "en stock", "disponible"
    ]
    
    # Palabras que confirman que definitivamente NO hay stock
    palabras_no_stock = [
        "sold out", "out of stock", "agotado", 
        "ausverkauft", "nicht verfügbar", "próximamente"
    ]

    while st.session_state.corriendo:
        for url in lista_urls:
            if not st.session_state.corriendo:
                break
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    texto = response.text.lower()
                    
                    # Verificamos si encuentra palabras de compra y evita falsos positivos de agotado
                    tiene_stock = any(p in texto for p in palabras_stock)
                    esta_agotado = any(p in texto for p in palabras_no_stock)
                    
                    if tiene_stock and not esta_agotado:
                        enviar_telegram(f"🚨 ¡STOCK O PREVENTA DETECTADA! 🚨\n\n{url}", t_token, t_chat)
            except Exception as e:
                print(f"Error comprobando stock de {url}: {e}")
        
        time.sleep(segundos_espera)

# Botones de control en la interfaz
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Encender Bot"):
        urls_lista = [linea.strip() for linea in urls_texto.split("\n") if linea.strip()]
        segundos = intervalo_minutos * 60
        
        if token and chat_id and urls_lista:
            st.session_state.corriendo = True
            hilo = threading.Thread(
                target=bucle_verificacion, 
                args=(token, chat_id, urls_lista, segundos), 
                daemon=True
            )
            hilo.start()
            st.success(f"¡Bot encendido vigilando {len(urls_lista)} enlaces cada {intervalo_minutos} minutos!")
        else:
            st.error("Rellena el token, el chat ID y al menos un enlace.")

with col2:
    if st.button("⏹️ Apagar Bot"):
        st.session_state.corriendo = False
        st.warning("Bot detenido.")

if st.session_state.corriendo:
    st.info(f"🟢 Estado: ACTIVO (Comprobando cada {intervalo_minutos} minutos)")
else:
    st.error("🔴 Estado: DETENIDO")
