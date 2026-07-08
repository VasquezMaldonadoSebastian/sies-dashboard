"""
Dashboard SIES — Educación Superior de Chile
Chat IA + Grafo del Conocimiento + KPIs
Fuente: www.mifuturo.cl, de Mineduc.
"""
import traceback
import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import sys

# ── Configuración ────────────────────────────────────────────────────────
st.set_page_config(page_title="SIES Dashboard", layout="wide", page_icon="🎓")

APP_DIR = Path(__file__).resolve().parent
CHROMA_DIR = APP_DIR / "chromadb"
sys.path.insert(0, str(APP_DIR))

DB = APP_DIR / "mifuturo_sies.db"
DB_EXISTS = DB.exists()

# ── Session state ────────────────────────────────────────────────────────
for key, default in [
    ("dark_mode", False),
    ("messages", [{"role": "assistant", "content": "¡Hola! Soy el asistente SIES. Pregúntame sobre matrícula, instituciones o indicadores de educación superior en Chile."}]),
    ("kb", None),
    ("diag", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Paletas ──────────────────────────────────────────────────────────────
def palette(dark=False):
    if dark:
        return {"bg":"#0F172A","card":"#1E293B","card_border":"#334155","primary":"#60A5FA",
                "primary_dark":"#93C5FD","primary_lighter":"#1E3A5F","primary_bg":"rgba(96,165,250,0.12)",
                "accent":"#FBBF24","accent_bg":"rgba(251,191,36,0.12)","text":"#F1F5F9",
                "text_light":"#94A3B8","border":"#334155","header_from":"#0B1E3A",
                "header_to":"#1E3A5F","shadow":"rgba(0,0,0,0.3)","grid":"#334155",
                "chart_bg":"#1E293B","paper_bg":"rgba(30,41,59,0)","gray_500":"#64748B",
                "gray_700":"#334155","blue_600":"#2563EB","blue_700":"#1D4ED8"}
    else:
        return {"bg":"#F8FAFC","card":"#FFFFFF","card_border":"#E2E8F0","primary":"#0B4A7A",
                "primary_dark":"#002A55","primary_lighter":"#E8F0FE","primary_bg":"rgba(11,74,122,0.07)",
                "accent":"#D4951A","accent_bg":"rgba(212,149,26,0.08)","text":"#0F172A",
                "text_light":"#475569","border":"#CBD5E1","header_from":"#002A55",
                "header_to":"#0B4A7A","shadow":"rgba(0,0,0,0.08)","grid":"#E2E8F0",
                "chart_bg":"#FFFFFF","paper_bg":"rgba(255,255,255,0)","gray_500":"#64748B",
                "gray_700":"#334155","blue_600":"#2563EB","blue_700":"#1D4ED8"}

p = palette(st.session_state.dark_mode)

# ── UI ───────────────────────────────────────────────────────────────────
st.markdown(f"""<style>
    :root {{ --bg: {p['bg']}; --card: {p['card']}; --card-border: {p['card_border']};
        --primary: {p['primary']}; --primary-dark: {p['primary_dark']};
        --primary-lighter: {p['primary_lighter']}; --primary-bg: {p['primary_bg']};
        --accent: {p['accent']}; --accent-bg: {p['accent_bg']};
        --text: {p['text']}; --text-light: {p['text_light']};
        --border: {p['border']}; --header-from: {p['header_from']};
        --header-to: {p['header_to']}; --shadow: {p['shadow']}; }}
    .stApp, .main, .block-container {{ background: var(--bg) !important; }}
    .block-container {{ max-width: 1400px; padding-top: 0.5rem; }}
    p, li, span, div, h1, h2, h3 {{ color: var(--text); }}
    .header {{ background: linear-gradient(135deg, var(--header-from), var(--header-to));
        padding: 1.2rem 2rem; border-radius: 14px; margin-bottom: 1rem;
        display: flex; justify-content: space-between; align-items: center; }}
    .header h1 {{ margin: 0; font-size: 1.5rem; font-weight: 700; color: #FFF !important; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.8rem; }}
    .kpi-card {{ background: var(--card); border-radius: 12px; padding: 1rem;
        border-left: 4px solid var(--primary); box-shadow: 0 2px 8px var(--shadow); }}
    .kpi-card .value {{ font-size: 1.8rem; font-weight: 700; color: var(--primary) !important; }}
    [data-testid="stToolbar"], #MainMenu, footer {{ display: none; }}
</style>""", unsafe_allow_html=True)

st.markdown(f"""<div class="header"><div><h1>🎓 SIES Dashboard <span style="font-size:0.9rem;font-weight:400;opacity:0.75;">Educación Superior • Chile</span></h1></div></div>""", unsafe_allow_html=True)

if st.button(f"{'🌙' if st.session_state.dark_mode else '☀️'} Modo {'Claro' if st.session_state.dark_mode else 'Oscuro'}"):
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO (siempre visible en sidebar o expander)
# ══════════════════════════════════════════════════════════════════════════
with st.expander("🔧 Diagnóstico del sistema", expanded=False):
    try:
        diag_lines = []
        diag_lines.append(f"**Python:** {sys.version}")
        diag_lines.append(f"**Directorio app:** {APP_DIR}")
        diag_lines.append(f"**search_index.json:** {Path(APP_DIR/'search_index.json').exists()} ({Path(APP_DIR/'search_index.json').stat().st_size/1024:.0f} KB)" if Path(APP_DIR/'search_index.json').exists() else "❌ search_index.json NO ENCONTRADO")
        diag_lines.append(f"**grafo_conocimiento.html:** {Path(CHROMA_DIR/'grafo_conocimiento.html').exists()} ({Path(CHROMA_DIR/'grafo_conocimiento.html').stat().st_size/1024:.0f} KB)" if Path(CHROMA_DIR/'grafo_conocimiento.html').exists() else "❌ grafo NO ENCONTRADO")
        diag_lines.append(f"**mifuturo_sies.db:** {'✅' if DB_EXISTS else '❌ No disponible'}")
        diag_lines.append(f"**glue.py:** {Path(APP_DIR/'glue.py').exists()}")
        # Intentar importar glue
        try:
            from glue import SIESKnowledgeBase
            diag_lines.append("**glue import:** ✅")
            try:
                kb_test = SIESKnowledgeBase()
                diag_lines.append(f"**KB docs:** {len(kb_test.documents)}")
                diag_lines.append(f"**KB DB:** {'✅' if kb_test.db_disponible else '❌ No disponible'}")
            except Exception as e:
                diag_lines.append(f"**KB init ERROR:** {str(e)[:200]}")
        except Exception as e:
            diag_lines.append(f"**glue import ERROR:** {str(e)[:200]}")
        st.markdown("\n".join(diag_lines))
    except Exception as e:
        st.error(f"Error en diagnóstico: {e}")

# ══════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════
tab_dash, tab_chat, tab_graph = st.tabs(["📊 Dashboard", "💬 Chat IA", "🧠 Grafo del Conocimiento"])

# ── TAB 1: DASHBOARD ──────────────────────────────────────────────────
with tab_dash:
    try:
        if not DB_EXISTS:
            st.info("""
            ### 🗄️ Base de datos local no disponible
            La base SQLite (563 MB) no está incluida en este despliegue.
            Los tabs **Chat IA** y **Grafo** sí funcionan con los documentos incluidos.
            """)
        else:
            @st.cache_data(ttl=3600)
            def load_data():
                conn = sqlite3.connect(str(DB))
                df = pd.read_sql('SELECT "AÑO" as año, SUM("TOTAL MATRÍCULA") as total_matricula FROM matricula GROUP BY "AÑO" ORDER BY "AÑO"', conn)
                conn.close()
                return df
            data = load_data()
            st.dataframe(data)
    except Exception as e:
        st.error(f"Error en Dashboard: {traceback.format_exc()}")

# ── TAB 2: CHAT IA ─────────────────────────────────────────────────────
with tab_chat:
    try:
        if st.session_state.kb is None:
            with st.spinner("Cargando base de conocimiento..."):
                from glue import SIESKnowledgeBase
                st.session_state.kb = SIESKnowledgeBase()
                st.success(f"✅ Base cargada: {len(st.session_state.kb.documents)} documentos")

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
                        resultado = kb.consultar(prompt)
                        st.markdown(resultado["respuesta"])
                        if resultado.get("fuentes"):
                            st.caption(f"📎 {', '.join(resultado['fuentes'][:3])}")
                        st.session_state.messages.append({"role": "assistant", "content": resultado["respuesta"]})
                    except Exception as e:
                        err = f"⚠️ Error: {traceback.format_exc()}"
                        st.error(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
    except Exception as e:
        st.error(f"Error inicializando Chat: {traceback.format_exc()}")

# ── TAB 3: GRAFO ───────────────────────────────────────────────────────
with tab_graph:
    try:
        graph_html = CHROMA_DIR / "grafo_conocimiento.html"
        if graph_html.exists():
            with open(graph_html, "r", encoding="utf-8") as f:
                html_content = f.read()
            html_content = html_content.replace(
                '<div id="mynetwork"',
                f'<div id="mynetwork" style="background:{p["bg"]};border-radius:12px;border:1px solid {p["border"]};"'
            )
            st.components.v1.html(html_content, height=620)
            st.markdown("""
            <div style="display:flex;gap:1.5rem;font-size:0.8rem;color:var(--text-light);">
                <span>■ <span style="color:#60A5FA;">Concepto</span></span>
                <span>★ <span style="color:#FBBF24;">Entidad</span></span>
                <span>● <span style="color:#34D399;">Informe PDF</span></span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"Grafo no encontrado en: {graph_html}")
    except Exception as e:
        st.error(f"Error cargando grafo: {traceback.format_exc()}")
