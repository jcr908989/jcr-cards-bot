import streamlit as st
import pandas as pd
from datetime import datetime
import time
import requests
from bs4 import BeautifulSoup

# Configuración de página
st.set_page_config(
    page_title="JCR Cards Bot Dashboard",
    page_icon="🃏",
    layout="wide"
)

# Estilo personalizado: ocultar sidebar
st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# Inicialización de Estado (Session State)
if 'running' not in st.session_state:
    st.session_state.running = False
if 'last_check' not in st.session_state:
    st.session_state.last_check = "No realizado"
if 'results_df' not in st.session_state:
    st.session_state.results_df = pd.DataFrame(columns=["Producto / Tienda", "Estado Stock", "Hora Escaneo", "URL"])
if 'total_con_stock' not in st.session_state:
    st.session_state.total_con_stock = 0
if 'notified_urls' not in st.session_state:
    st.session_state.notified_urls = set()

# Enviar alerta exclusiva por Telegram
def enviar_alerta_telegram(bot_token, chat_id, producto, url):
    if not bot_token or not chat_id:
        return False, "Por favor completa ambos campos (Bot Token y Chat ID)."
    
    bot_token = bot_token.strip()
    chat_id = chat_id.strip()

    mensaje = (
        f"🚨 <b>¡STOCK DETECTADO!</b> 🚨\n\n"
        f"📦 <b>Producto:</b> {producto}\n"
        f"🔗 <b>Enlace:</b> {url}\n\n"
        f"⏰ <i>Hora: {datetime.now().strftime('%H:%M:%S')}</i>"
    )
    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(telegram_url, data=payload, timeout=8)
        data = res.json()
        
        if res.status_code == 200 and data.get("ok"):
            return True, "Mensaje enviado con éxito."
        else:
            descripcion_error = data.get("description", "Error desconocido en Telegram")
            return False, f"Telegram rechazó la petición: [{res.status_code}] {descripcion_error}"
            
    except Exception as e:
        return False, f"Error de conexión desde Python: {str(e)}"

# Verificar múltiples URLs mediante peticiones ligeras
def verificar_multiples_urls(lista_urls, bot_token="", chat_id="", usar_telegram=True):
    resultados = []
    con_stock_count = 0
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for url in lista_urls:
        url = url.strip()
        if not url:
            continue
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                resultados.append({
                    "Producto / Tienda": "Error de Servidor",
                    "Estado Stock": f"⚠️ HTTP {response.status_code}",
                    "Hora Escaneo": datetime.now().strftime('%H:%M:%S'),
                    "URL": url
                })
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Obtener el título de la página web
            title_tag = soup.find('title')
            title = title_tag.text.split('|')[0].strip() if title_tag else url
            if not title:
                title = url
            
            content = response.text.lower()
            
            kw_disponible = ["añadir al carrito", "add to cart", "comprar", "reserva", "en stock", "pre-order"]
            kw_agotado = ["agotado", "out of stock", "sin stock", "no disponible", "sold out"]
            
            disponible = any(kw in content for kw in kw_disponible) and not any(kw in content for kw in kw_agotado)
            
            if disponible:
                con_stock_count += 1
                estado_texto = "🟢 DISPONIBLE / PREVENTA"
                
                if usar_telegram and (url not in st.session_state.notified_urls):
                    enviar_alerta_telegram(bot_token, chat_id, title if len(title) > 5 else "Producto detectado", url)
                    st.session_state.notified_urls.add(url)
            else:
                estado_texto = "🔴 AGOTADO / SIN STOCK"
                st.session_state.notified_urls.discard(url)
            
            resultados.append({
                "Producto / Tienda": title[:50] + "..." if len(title) > 50 else title,
                "Estado Stock": estado_texto,
                "Hora Escaneo": datetime.now().strftime('%H:%M:%S'),
                "URL": url
            })
        except Exception:
            resultados.append({
                "Producto / Tienda": "Error de Conexión",
                "Estado Stock": "⚠️ ERROR AL CARGAR",
                "Hora Escaneo": datetime.now().strftime('%H:%M:%S'),
                "URL": url
            })
    
    return pd.DataFrame(resultados), con_stock_count

# --- INTERFAZ GRÁFICA ---

st.title("🃏 JCR Cards - Monitor con Alerta de Telegram")
st.caption("Rastreo continuo de preventas con notificaciones exclusivas por Telegram.")

st.divider()

metrics_container = st.empty()

def render_metrics():
    with metrics_container.container():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Estado del Bot", "🟢 BUCLE ACTIVO" if st.session_state.running else "🔴 DETENIDO")
        col2.metric("Preventas Detectadas", f"{st.session_state.total_con_stock} Ítems")
        col3.metric("Último Rastreo", st.session_state.last_check)
        col4.metric("URLs Analizadas", len(st.session_state.results_df))

render_metrics()

st.divider()

col_ctrl, col_config, col_tg = st.columns([1, 1, 1])

with col_config:
    st.subheader("⚙️ Configuración Escaneo")
    urls_input = st.text_area(
        "Pega los enlaces (uno por línea):",
        value="https://www.game.es/\nhttps://tcgfactory.com/es/distribucion/story-booster-display-st-01\nhttps://www.topps.com/",
        height=140
    )
    
    intervalo = st.number_input(
        "Intervalo de escaneo (segundos):",
        min_value=5,
        max_value=3600,
        value=30,
        step=5
    )

with col_tg:
    st.subheader("✈️ Notificaciones Telegram")
    usar_telegram = st.checkbox("Activar alertas por Telegram", value=True)
    bot_token = st.text_input("Telegram Bot Token:", type="password", placeholder="123456789:ABCdefGhI...")
    chat_id = st.text_input("Tu Telegram Chat ID:", placeholder="8514421716")
    
    if st.button("🔔 Enviar Alerta de Prueba a Telegram"):
        exito, mensaje_detalle = enviar_alerta_telegram(
            bot_token, 
            chat_id, 
            "Producto de Prueba JCR Cards", 
            "https://www.topps.com/"
        )
        if exito:
            st.success("¡Prueba enviada a Telegram con éxito!")
        else:
            st.error(f"❌ Error al enviar: {mensaje_detalle}")

with col_ctrl:
    st.subheader("🎮 Control de Automatización")
    st.write("")
    
    activar_bucle = st.toggle("🚀 ENCENDER ESCANEO AUTOMÁTICO", value=st.session_state.running)
    
    if activar_bucle != st.session_state.running:
        st.session_state.running = activar_bucle
        st.rerun()

st.divider()

st.subheader("📊 Resultados en Tiempo Real")
table_container = st.empty()

def render_table():
    with table_container.container():
        if not st.session_state.results_df.empty:
            st.dataframe(
                st.session_state.results_df,
                column_config={
                    "URL": st.column_config.LinkColumn("Enlace directo")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Activa el escaneo para mostrar la tabla de productos.")

render_table()

if st.session_state.running:
    lista_urls = [u for u in urls_input.split('\n') if u.strip()]
    if not lista_urls:
        st.warning("Añade al menos una URL válida.")
        st.session_state.running = False
        st.rerun()
    else:
        df_res, con_stock = verificar_multiples_urls(
            lista_urls, 
            bot_token=bot_token, 
            chat_id=chat_id, 
            usar_telegram=usar_telegram
        )
        
        st.session_state.results_df = df_res
        st.session_state.total_con_stock = con_stock
        st.session_state.last_check = datetime.now().strftime('%H:%M:%S')
        
        render_metrics()
        render_table()
        
        time.sleep(intervalo)
        st.rerun()