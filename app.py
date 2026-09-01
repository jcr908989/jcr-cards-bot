import time
import threading
import requests
from bs4 import BeautifulSoup
import streamlit as st

st.title("🤖 JCR Cards Bot - Panel 24/7")
st.subheader("Control de Stock Automático")

token = st.text_input("Telegram Bot Token", type="password")
chat_id = st.text_input("Telegram Chat ID")

intervalo_minutos = st.slider(
    "Tiempo entre comprobaciones (minutos)", 
    min_value=1, 
    max_value=60, 
    value=3
)

urls_texto = st.text_area(
    "Enlaces a vigilar (pon uno por línea)",
    "https://tcgfactory.com/es/distribucion/booster-box-display-op-17-24-sobres-ingles-one-piece-card-game.html"
)

# Contenedor para mostrar el estado en vivo en la pantalla
st.markdown("### 📋 Registro de Estado en Vivo")
log_container = st.empty()

if "corriendo" not in st.session_state:
    st.session_state.corriendo = False
if "historial_logs" not in st.session_state:
    st.session_state.historial_logs = []

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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }
    
    palabras_stock = ["add to cart", "añadir al carrito", "añadir a la cesta", "comprar", "pre-order", "preventa", "in den warenkorb", "en stock", "disponible"]
    palabras_no_stock = ["sold out", "out of stock", "agotado", "ausverkauft", "nicht verfügbar", "próximamente"]

    while st.session_state.corriendo:
        for url in lista_urls:
            if not st.session_state.corriendo:
                break
            
            nombre_corto = url.split("/")[2] if len(url.split("/")) > 2 else url
            
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    texto = response.text.lower()
                    tiene_stock = any(p in texto for p in palabras_stock)
                    esta_agotado = any(p in texto for p in palabras_no_stock)
                    
                    if tiene_stock and not esta_agotado:
                        mensaje_log = f"🟢 [STOCK DISPONIBLE] {nombre_corto}"
                        enviar_telegram(f"🚨 ¡STOCK O PREVENTA DETECTADA! 🚨\n\n{url}", t_token, t_chat)
                    else:
                        mensaje_log = f"🔴 [AGOTADO / SIN CAMBIOS] {nombre_corto}"
                else:
                    mensaje_log = f"⚠️ [ERROR HTTP {response.status_code}] {nombre_corto}"
            except Exception as e:
                mensaje_log = f"❌ [ERROR DE CONEXIÓN] {nombre_corto}"
            
            # Guardar en el historial para mostrarlo en pantalla
            st.session_state.historial_logs.insert(0, mensaje_log)
            if len(st.session_state.historial_logs) > 10:
                st.session_state.historial_logs.pop()
                
        time.sleep(segundos_espera)

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Encender Bot"):
        urls_lista = [linea.strip() for linea in urls_texto.split("\n") if linea.strip()]
        segundos = intervalo_minutos * 60
        
        if token and chat_id and urls_lista:
            st.session_state.corriendo = True
            st.session_state.historial_logs = ["🚀 Bot iniciado correctamente..."]
            hilo = threading.Thread(
                target=bucle_verificacion, 
                args=(token, chat_id, urls_lista, segundos), 
                daemon=True
            )
            hilo.start()
            st.success(f"¡Bot encendido vigilando {len(urls_lista)} enlaces!")
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

# Mostrar el registro actualizado en la interfaz
if st.session_state.historial_logs:
    log_container.code("\n".join(st.session_state.historial_logs))
