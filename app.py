"""
Dashboard SIES — Chat IA + Grafo + KPIs
Fuente: www.mifuturo.cl, de Mineduc.
"""
import traceback
import sqlite3, pandas as pd, streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import sys

st.set_page_config(page_title="SIES Dashboard", layout="wide", page_icon="🎓")

APP_DIR = Path(__file__).resolve().parent
CHROMA_DIR = APP_DIR / "chromadb"
sys.path.insert(0, str(APP_DIR))

DB = APP_DIR / "mifuturo_sies.db"
DB_EXISTS = DB.exists()

for key, default in [
    ("dark_mode", False),
    ("page", "💬 Chat IA"),
    ("messages", [{"role": "assistant", "content": "¡Hola! Pregúntame sobre educación superior chilena."}]),
    ("kb", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def palette(dark):
    return {"bg":"#0F172A","card":"#1E293B","text":"#F1F5F9","primary":"#60A5FA","accent":"#FBBF24","border":"#334155","header_from":"#0B1E3A","header_to":"#1E3A5F","shadow":"rgba(0,0,0,0.3)","grid":"#334155","gray_500":"#64748B"} if dark else \
           {"bg":"#F8FAFC","card":"#FFFFFF","text":"#0F172A","primary":"#0B4A7A","accent":"#D4951A","border":"#CBD5E1","header_from":"#002A55","header_to":"#0B4A7A","shadow":"rgba(0,0,0,0.08)","grid":"#E2E8F0","gray_500":"#64748B"}

p = palette(st.session_state.dark_mode)

st.markdown(f"""<style>
    .stApp, .main, .block-container {{ background: {p['bg']} !important; }}
    p, li, div, h1, h2, h3 {{ color: {p['text']}; }}
    .header {{ background: linear-gradient(135deg, {p['header_from']}, {p['header_to']});
        padding: 1rem 2rem; border-radius: 14px; margin-bottom: 1rem; }}
    .header h1 {{ margin: 0; font-size: 1.4rem; font-weight: 700; color: #FFF !important; }}
    [data-testid="stToolbar"], #MainMenu, footer {{ display: none; }}
    section[data-testid="stSidebar"] {{ background: {p['card']}; }}
</style>""", unsafe_allow_html=True)

st.markdown(f'<div class="header"><h1>🎓 SIES — Educación Superior Chile</h1></div>', unsafe_allow_html=True)

# Sidebar nav
with st.sidebar:
    st.button(f"{'🌙' if st.session_state.dark_mode else '☀️'} Modo {'Claro' if st.session_state.dark_mode else 'Oscuro'}", on_click=lambda: setattr(st.session_state, 'dark_mode', not st.session_state.dark_mode))
    st.session_state.page = st.radio("Navegación", ["💬 Chat IA", "🧠 Grafo", "📊 Dashboard", "🔧 Diagnóstico"], index=["💬 Chat IA", "🧠 Grafo", "📊 Dashboard", "🔧 Diagnóstico"].index(st.session_state.page))

# ── PÁGINAS ───────────────────────────────────────────────────────────

# CHAT
if st.session_state.page == "💬 Chat IA":
    try:
        if st.session_state.kb is None:
            with st.spinner("Cargando base de conocimiento..."):
                from glue import SIESKnowledgeBase
                st.session_state.kb = SIESKnowledgeBase()
                st.success(f"✅ {len(st.session_state.kb.documents)} documentos listos")

        kb = st.session_state.kb
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Pregunta sobre educación superior..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Consultando..."):
                    try:
                        r = kb.consultar(prompt)
                        st.markdown(r["respuesta"])
                        if r.get("fuentes"):
                            st.caption(f"📎 {', '.join(r['fuentes'][:3])}")
                        st.session_state.messages.append({"role": "assistant", "content": r["respuesta"]})
                    except Exception as e:
                        err = f"⚠️ {traceback.format_exc()}"
                        st.error(err)
    except Exception as e:
        st.error(f"Error: {traceback.format_exc()}")

# GRAFO
elif st.session_state.page == "🧠 Grafo":
    try:
        graph_html = CHROMA_DIR / "grafo_conocimiento.html"
        if graph_html.exists():
            with open(graph_html, "r", encoding="utf-8") as f:
                html = f.read()
            html = html.replace('<div id="mynetwork"', f'<div id="mynetwork" style="background:{p["bg"]};border-radius:12px;border:1px solid {p["border"]};"')
            st.components.v1.html(html, height=620)
            st.markdown("""
            <div style="display:flex;gap:1.5rem;font-size:0.8rem;color:var(--text-light);">
                <span>■ <span style="color:#60A5FA;">Concepto</span></span>
                <span>★ <span style="color:#FBBF24;">Entidad</span></span>
                <span>● <span style="color:#34D399;">Informe PDF</span></span>
            </div>""", unsafe_allow_html=True)
        else:
            st.warning("Grafo no disponible")
    except Exception as e:
        st.error(traceback.format_exc())

# DASHBOARD
elif st.session_state.page == "📊 Dashboard":
    if DB_EXISTS:
        try:
            conn = sqlite3.connect(str(DB))
            df = pd.read_sql('SELECT "AÑO" as año, SUM("TOTAL MATRÍCULA") as total FROM matricula GROUP BY "AÑO" ORDER BY "AÑO"', conn)
            conn.close()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["año"], y=df["total"], mode="lines+markers"))
            st.plotly_chart(fig)
        except Exception as e:
            st.error(traceback.format_exc())
    else:
        st.info("Base de datos no disponible en este despliegue. Chat y Grafo sí funcionan.")

# DIAGNÓSTICO
else:
    st.subheader("🔧 Diagnóstico")
    try:
        d = []
        d.append(f"**Python:** {sys.version}")
        d.append(f"**Directorio:** {APP_DIR}")
        si = Path(APP_DIR/'search_index.json')
        d.append(f"**search_index.json:** {'✅' if si.exists() else '❌'} ({si.stat().st_size/1024:.0f} KB)" if si.exists() else "❌")
        gh = Path(CHROMA_DIR/'grafo_conocimiento.html')
        d.append(f"**grafo:** {'✅' if gh.exists() else '❌'} ({gh.stat().st_size/1024:.0f} KB)" if gh.exists() else "❌")
        d.append(f"**glue.py:** {'✅' if Path(APP_DIR/'glue.py').exists() else '❌'}")
        d.append(f"**DB:** {'✅' if DB_EXISTS else '❌ No disponible'}")
        d.append(f"**lib/:** {'✅' if Path(APP_DIR/'lib/bindings/utils.js').exists() else '❌'}")
        try:
            from glue import SIESKnowledgeBase
            kb = SIESKnowledgeBase()
            d.append(f"**KB docs:** {len(kb.documents)}")
            d.append(f"**KB TF-IDF:** {'✅' if kb.tfidf_vectorizer else '❌'}")
            d.append(f"**KB DB:** {'✅' if kb.db_disponible else '❌'}")
        except Exception as e:
            d.append(f"**KB ERROR:** {str(e)[:200]}")
        st.markdown("\n".join(d))
        
        # Test de consulta
        st.subheader("Test de consulta")
        try:
            r = kb.consultar("matrícula 2025")
            st.text_area("Respuesta (primeros 500 chars)", r["respuesta"][:500])
            st.caption(f"Fuentes: {', '.join(r['fuentes'][:3])}")
        except Exception as e:
            st.error(f"Test falló: {e}")
    except Exception as e:
        st.error(f"Diagnóstico falló: {traceback.format_exc()}")
