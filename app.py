import time
import threading
import requests
from bs4 import BeautifulSoup
import streamlit as st

st.title("🤖 JCR Cards Bot - Panel 24/7")
st.subheader("Control de Stock por Botón")

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

def verificar_urls(lista_urls, t_token, t_chat, enviar_alerta=False):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }

    # Palabras que indican que SÍ se puede comprar / añadir
    palabras_positivo = ["añadir", "comprar", "add to cart", "pre-order", "preventa", "in den warenkorb", "disponible"]
    # Palabras que indican bloqueo o falta de stock
    palabras_bloqueado = ["venta bloqueada", "agotado", "out of stock", "sold out", "ausverkauft"]

    resultados = []
    for url in lista_urls:
        nombre_corto = url.split("/")[2] if len(url.split("/")) > 2 else url
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                texto = response.text.lower()
                
                tiene_boton_añadir = any(p in texto for p in palabras_positivo)
                esta_bloqueado = any(p in texto for p in palabras_bloqueado)
                
                # Se pone en verde solo si encuentra palabras de compra y NO está bloqueado
                if tiene_boton_añadir and not esta_bloqueado:
                    resultados.append(f"🟢 ¡BOTÓN DE AÑADIR DISPONIBLE!: {nombre_corto}")
                    if enviar_alerta:
                        enviar_telegram(f"🚨 ¡YA SE PUEDE AÑADIR / COMPRAR! 🚨\n\n{url}", t_token, t_chat)
                else:
                    resultados.append(f"🟠 BLOQUEADO / NO DISPONIBLE: {nombre_corto}")
            else:
                resultados.append(f"⚠️ ERROR HTTP {response.status_code}: {nombre_corto}")
        except Exception as e:
            resultados.append(f"❌ ERROR DE CONEXIÓN: {nombre_corto}")
    return resultados

def bucle_verificacion(t_token, t_chat, lista_urls, segundos_espera):
    while st.session_state.corriendo:
        verificar_urls(lista_urls, t_token, t_chat, enviar_alerta=True)
        time.sleep(segundos_espera)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Encender Bot 24/7"):
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
            st.success("¡Bot encendido en segundo plano!")
        else:
            st.error("Rellena token, chat ID y enlaces.")

with col2:
    if st.button("🔍 Comprobar Ahora"):
        urls_lista = [linea.strip() for linea in urls_texto.split("\n") if linea.strip()]
        if urls_lista:
            with st.spinner("Comprobando el estado del botón..."):
                res = verificar_urls(urls_lista, token, chat_id, enviar_alerta=False)
            st.markdown("### Resultados de la comprobación:")
            for r in res:
                st.write(r)
        else:
            st.error("Introduce al menos un enlace.")

with col3:
    if st.button("⏹️ Apagar Bot"):
        st.session_state.corriendo = False
        st.warning("Bot detenido.")

if st.session_state.corriendo:
    st.info(f"🟢 Estado: ACTIVO (Comprobando cada {intervalo_minutos} minutos)")
else:
    st.error("🔴 Estado: DETENIDO")
