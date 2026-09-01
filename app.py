
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
    headers = {"User-Agent": "Mozilla/5.0"}
    while st.session_state.corriendo:
        for url in lista_urls:
            if not st.session_state.corriendo:
                break
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    texto = response.text.lower()
                    if "agotado" not in texto and "out of stock" not in texto and "sold out" not in texto:
                        enviar_telegram(f"🚨 ¡POSIBLE STOCK DISPONIBLE! 🚨\n\n{url}", t_token, t_chat)
            except Exception as e:
                print(f"Error comprobando stock de {url}: {e}")
        
        # Espera el tiempo configurado en la interfaz antes de volver a comprobar
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
