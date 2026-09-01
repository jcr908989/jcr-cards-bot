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
url_tienda = st.text_input("Enlace a vigilar", "https://www.inside-the-box.de")

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

def bucle_verificacion(t_token, t_chat, url):
    headers = {"User-Agent": "Mozilla/5.0"}
    while st.session_state.corriendo:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                texto = response.text.lower()
                if "agotado" not in texto and "out of stock" not in texto and "sold out" not in texto:
                    enviar_telegram(f"🚨 ¡POSIBLE STOCK DISPONIBLE! 🚨\n\n{url}", t_token, t_chat)
        except Exception as e:
            print(f"Error comprobando stock: {e}")
        
        # Espera 10 minutos antes de la siguiente comprobación
        time.sleep(600)

# Botones de control en la interfaz
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Encender Bot"):
        if token and chat_id and url_tienda:
            st.session_state.corriendo = True
            hilo = threading.Thread(target=bucle_verificacion, args=(token, chat_id, url_tienda), daemon=True)
            hilo.start()
            st.success("¡Bot encendido y operando en segundo plano!")
        else:
            st.error("Rellena todos los campos antes de encender.")

with col2:
    if st.button("⏹️ Apagar Bot"):
        st.session_state.corriendo = False
        st.warning("Bot detenido.")

if st.session_state.corriendo:
    st.info("🟢 Estado: ACTIVO (Comprobando cada 10 minutos)")
else:
    st.error("🔴 Estado: DETENIDO")
