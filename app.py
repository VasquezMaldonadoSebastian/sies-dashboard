"""
Dashboard SIES — Rediseño Open Design
Paleta cálida: terracota, crema, ámbar, tierra
Tipografía: DM Sans · JetBrains Mono
"""
import traceback
import sqlite3, pandas as pd, streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import sys

st.set_page_config(page_title="Analista SIES", layout="wide", page_icon="🎓",
                   initial_sidebar_state="expanded")

APP_DIR = Path(__file__).resolve().parent
CHROMA_DIR = APP_DIR / "chromadb"
sys.path.insert(0, str(APP_DIR))
DB = APP_DIR / "mifuturo_sies.db"
DB_EXISTS = DB.exists()

# ── Sesión ─────────────────────────────────────────────────────────────────
for key, default in [
    ("page", "💬 Chat IA"),
    ("messages", [{"role": "assistant",
                   "content": "¡Hola! Soy tu analista de datos SIES. Puedo consultar **506 hechos** extraídos de **5 informes** oficiales. ¿Qué te gustaría saber sobre la educación superior chilena?"}]),
    ("kb", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Paleta cálida SIES ─────────────────────────────────────────────────────
P = {
    "bg": "#F5F0EB",           # crema cálido
    "surface": "#FCFAFA",      # casi blanco
    "fg": "#2B2520",           # texto oscuro tierra
    "muted": "#6B6560",        # texto secundario
    "border": "#D9D4CF",       # borde
    "sidebar": "#1E1A17",      # sidebar oscuro
    "sidebar_hover": "#322C27",
    "sidebar_fg": "#C5BEB8",   # texto sidebar
    "sidebar_active": "#C8633D", # terracota activo
    "accent": "#B8552E",       # terracota principal
    "accent_soft": "#D47A5A",
    "accent_bg": "#EDDDD4",
    "amber": "#C8933C",
    "amber_bg": "#F2E8D4",
    "success": "#3A7D5C",
    "success_bg": "#DCEBE2",
}

# ── CSS inyectado ───────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap');

  * {{ font-family: 'DM Sans', -apple-system, system-ui, sans-serif !important; }}

  /* Fondo general */
  .stApp, .main, .block-container {{ background: {P['bg']} !important; }}
  section[data-testid="stSidebar"] > div:first-child {{
    background: {P['sidebar']} !important;
  }}
  section[data-testid="stSidebar"] * {{
    color: {P['sidebar_fg']} !important;
  }}

  /* Ocultar defaults */
  #MainMenu, footer, header {{ display: none !important; }}
  .stAppToolbar, [data-testid="stToolbar"] {{ display: none !important; }}

  /* Sidebar personalizada */
  section[data-testid="stSidebar"] {{
    width: 264px !important; min-width: 264px !important;
  }}
  .sidebar-brand {{
    padding: 24px 20px 12px; border-bottom: 1px solid rgba(255,255,255,0.06);
  }}
  .sidebar-brand h1 {{
    font-size: 20px; font-weight: 600; letter-spacing: -0.3px;
    color: #FFF !important; display: flex; align-items: center; gap: 10px;
  }}
  .sidebar-brand .logo {{
    width: 28px; height: 28px; background: {P['accent']};
    border-radius: 8px; display: inline-flex; align-items: center;
    justify-content: center; font-size: 14px; color: white !important;
  }}
  .sidebar-brand .sub {{
    font-size: 12px; color: {P['muted']} !important;
    padding-left: 38px; margin-top: -2px;
  }}
  .sidebar-profile {{
    padding: 16px 20px; border-top: 1px solid rgba(255,255,255,0.06);
    margin-top: auto; display: flex; align-items: center; gap: 10px;
  }}
  .sidebar-profile .avatar {{
    width: 32px; height: 32px; border-radius: 50%;
    background: {P['accent']}; display: inline-flex; align-items: center;
    justify-content: center; font-size: 13px; color: white !important;
  }}
  .sidebar-profile .name {{ font-size: 13px; font-weight: 500; color: #FFF !important; }}
  .sidebar-profile .role {{ font-size: 11px; color: {P['muted']} !important; }}

  /* Nav items */
  .nav-section {{
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 1px; color: rgba(255,255,255,0.3) !important;
    padding: 20px 20px 8px;
  }}
  .nav-item {{
    display: flex; align-items: center; gap: 10px;
    padding: 8px 20px; margin: 1px 8px; border-radius: 8px;
    font-size: 13px; font-weight: 500; cursor: pointer;
    transition: background 0.15s; text-decoration: none;
    color: {P['sidebar_fg']} !important;
  }}
  .nav-item:hover {{ background: {P['sidebar_hover']}; }}
  .nav-item.active {{
    background: rgba(200,99,61,0.15); color: {P['sidebar_active']} !important;
  }}
  .nav-item .badge {{
    margin-left: auto; font-size: 10px; font-weight: 500;
    background: rgba(255,255,255,0.08); padding: 1px 7px;
    border-radius: 999px; color: rgba(255,255,255,0.4) !important;
  }}
  .nav-item.active .badge {{
    background: rgba(200,99,61,0.25); color: {P['sidebar_active']} !important;
  }}

  /* KPI cards */
  .kpi-row {{ display: flex; gap: 12px; margin: 24px 0; }}
  .kpi-card {{
    flex: 1; background: {P['surface']}; border: 1px solid {P['border']};
    border-radius: 14px; padding: 18px 20px;
    transition: box-shadow 0.2s, transform 0.2s;
  }}
  .kpi-card:hover {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.06); transform: translateY(-1px);
  }}
  .kpi-label {{
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; color: {P['muted']}; margin-bottom: 4px;
  }}
  .kpi-value {{
    font-size: 28px; font-weight: 600; letter-spacing: -0.5px;
    color: {P['fg']}; line-height: 1.1;
  }}
  .kpi-footnote {{
    font-size: 11px; color: {P['muted']}; margin-top: 4px;
  }}

  /* Chat */
  .stChatMessage {{ background: transparent !important; }}
  .stChatMessage [data-testid="chatMessageContent"] {{
    background: {P['surface']} !important;
    border: 1px solid {P['border']} !important;
    border-radius: 14px !important; padding: 14px 18px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }}
  .stChatMessage [data-testid="chatMessageAvatar"] {{
    background: {P['accent_bg']} !important; color: {P['accent']} !important;
    border-radius: 50%; width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
  }}
  .stChatMessage[data-testid="userChatMessage"] [data-testid="chatMessageContent"] {{
    background: {P['accent']} !important; border-color: {P['accent']} !important;
    color: white !important;
  }}
  .stChatMessage[data-testid="userChatMessage"] [data-testid="chatMessageAvatar"] {{
    background: {P['sidebar']} !important; color: white !important;
  }}

  /* Chat input */
  .stChatInputContainer {{
    border: 1px solid {P['border']} !important;
    border-radius: 999px !important; background: {P['surface']} !important;
  }}
  .stChatInputContainer:focus-within {{
    border-color: {P['accent']} !important;
    box-shadow: 0 0 0 2px {P['accent_bg']} !important;
  }}

  /* Botones radio sidebar */
  .stRadio [role="radiogroup"] {{
    background: transparent !important; gap: 2px !important;
  }}
  .stRadio label {{
    background: transparent !important; border: none !important;
    padding: 8px 20px !important; border-radius: 8px !important;
    font-size: 13px !important; font-weight: 500 !important;
    color: {P['sidebar_fg']} !important; transition: background 0.15s;
    display: flex !important; align-items: center; gap: 10px;
  }}
  .stRadio label:hover {{ background: {P['sidebar_hover']} !important; }}
  .stRadio label[data-selected="true"] {{
    background: rgba(200,99,61,0.15) !important;
    color: {P['sidebar_active']} !important;
  }}

  /* Entity cards */
  .entity-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 20px;
  }}
  .entity-card {{
    background: {P['surface']}; border: 1px solid {P['border']};
    border-radius: 10px; padding: 14px 16px; cursor: pointer;
    transition: all 0.15s;
  }}
  .entity-card:hover {{
    border-color: {P['accent_soft']};
    box-shadow: 0 2px 8px rgba(184,85,46,0.08);
  }}
  .entity-card .name {{ font-size: 13px; font-weight: 500; color: {P['fg']}; }}
  .entity-card .meta {{
    font-size: 11px; color: {P['muted']}; display: flex; justify-content: space-between; margin-top: 4px;
  }}
  .entity-card .bar {{
    height: 3px; border-radius: 2px; background: {P['border']}; margin-top: 8px; overflow: hidden;
  }}
  .entity-card .bar .fill {{
    height: 100%; border-radius: 2px; background: {P['accent']};
  }}

  /* Page header */
  .page-header {{ margin-bottom: 8px; }}
  .page-header h1 {{
    font-size: 22px; font-weight: 600; letter-spacing: -0.3px;
    color: {P['fg']}; margin: 0;
  }}
  .page-header p {{ font-size: 13px; color: {P['muted']}; margin-top: 2px; }}

  /* Tables dentro del chat */
  .stChatMessage table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 13px; }}
  .stChatMessage th {{
    background: {P['accent_bg']}; padding: 6px 10px; text-align: left;
    font-weight: 500; font-size: 12px; color: {P['fg']};
  }}
  .stChatMessage td {{ padding: 5px 10px; border-bottom: 1px solid {P['border']}; }}
  .stChatMessage td:last-child {{ text-align: right; font-weight: 500; }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: {P['border']}; border-radius: 3px; }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar con marca ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-brand">
      <h1><span class="logo">📊</span> SIES</h1>
      <div class="sub">Educación Superior Chile</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-section">Principal</div>', unsafe_allow_html=True)
    st.session_state.page = st.radio("nav", ["💬 Chat IA", "🧠 Grafo", "📊 Dashboard"],
                                      index=["💬 Chat IA", "🧠 Grafo", "📊 Dashboard"].index(st.session_state.page),
                                      label_visibility="collapsed")

    st.markdown('<div class="nav-section">Sistema</div>', unsafe_allow_html=True)
    if st.button("🔧 Diagnóstico", use_container_width=True, type="secondary"):
        st.session_state.page = "🔧 Diagnóstico"

    # Perfil
    st.markdown(f"""
    <div class="sidebar-profile">
      <span class="avatar">SV</span>
      <div><div class="name">Sebastián V.</div><div class="role">Consultor Datos</div></div>
    </div>
    """, unsafe_allow_html=True)

# ── Helper: KPIs ───────────────────────────────────────────────────────────
def show_kpis():
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card"><div class="kpi-label">📄 Documentos</div><div class="kpi-value">5</div><div class="kpi-footnote">informes SIES procesados</div></div>
      <div class="kpi-card"><div class="kpi-label">📊 Hechos</div><div class="kpi-value">506</div><div class="kpi-footnote">afirmaciones extraídas</div></div>
      <div class="kpi-card"><div class="kpi-label">🏷️ Entidades</div><div class="kpi-value">89</div><div class="kpi-footnote">instituciones, regiones, áreas</div></div>
      <div class="kpi-card"><div class="kpi-label">📂 Categorías</div><div class="kpi-value">4</div><div class="kpi-footnote">matrícula · retención · género · titulación</div></div>
    </div>
    """, unsafe_allow_html=True)

# ── PÁGINAS ────────────────────────────────────────────────────────────────

# 💬 CHAT IA
if st.session_state.page == "💬 Chat IA":
    st.markdown('<div class="page-header"><h1>💬 Chat IA · SIES</h1><p>Consulta sobre educación superior chilena con datos de 5 documentos indexados</p></div>', unsafe_allow_html=True)
    show_kpis()

    try:
        if st.session_state.kb is None:
            with st.spinner("Cargando base de conocimiento..."):
                from glue import SIESKnowledgeBase
                st.session_state.kb = SIESKnowledgeBase()

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
                        st.error(f"⚠️ {traceback.format_exc()}")
    except Exception as e:
        st.error(f"Error: {traceback.format_exc()}")

# 🧠 GRAFO
elif st.session_state.page == "🧠 Grafo":
    st.markdown('<div class="page-header"><h1>🧠 Grafo de Conocimiento</h1><p>89 entidades conectadas por 506 hechos</p></div>', unsafe_allow_html=True)

    # Entity cards
    entidades = [
        ("📊 Matrícula Total", "concepto", "9 hechos", 100),
        ("🏫 U. Católica de Temuco", "institución", "72 hechos", 80),
        ("👤 Participación Femenina", "concepto", "12 hechos", 60),
        ("🔄 Retención 1er Año", "concepto", "15 hechos", 70),
    ]
    cards = '<div class="entity-grid">'
    for name, tipo, hechos, pct in entidades:
        cards += f'<div class="entity-card"><div class="name">{name}</div><div class="meta"><span>{tipo}</span><span>{hechos}</span></div><div class="bar"><div class="fill" style="width:{pct}%"></div></div></div>'
    cards += '</div>'
    st.markdown(cards, unsafe_allow_html=True)

    try:
        graph_html = CHROMA_DIR / "grafo_conocimiento.html"
        if graph_html.exists():
            with open(graph_html, "r", encoding="utf-8") as f:
                html = f.read()
            html = html.replace('<div id="mynetwork"', '<div id="mynetwork" style="background:#FCFAFA;border-radius:12px;border:1px solid #D9D4CF;"')
            st.components.v1.html(html, height=620)
            st.markdown("""
            <div style="display:flex;gap:1.5rem;font-size:0.8rem;color:#6B6560;">
                <span>■ <span style="color:#B8552E;">Concepto</span></span>
                <span>★ <span style="color:#C8933C;">Entidad</span></span>
                <span>● <span style="color:#3A7D5C;">Informe PDF</span></span>
            </div>""", unsafe_allow_html=True)
        else:
            st.warning("Grafo no disponible")
    except Exception as e:
        st.error(traceback.format_exc())

# 📊 DASHBOARD
elif st.session_state.page == "📊 Dashboard":
    st.markdown('<div class="page-header"><h1>📊 Dashboard</h1><p>Indicadores clave de educación superior chilena</p></div>', unsafe_allow_html=True)

    if DB_EXISTS:
        try:
            conn = sqlite3.connect(str(DB))
            df = pd.read_sql('SELECT "AÑO" as año, SUM("TOTAL MATRÍCULA") as total FROM matricula GROUP BY "AÑO" ORDER BY "AÑO"', conn)
            conn.close()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["año"], y=df["total"], mode="lines+markers",
                                     line=dict(color="#B8552E", width=3),
                                     marker=dict(color="#B8552E", size=8)))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="DM Sans", size=13, color="#2B2520"),
                xaxis=dict(gridcolor="#D9D4CF"),
                yaxis=dict(gridcolor="#D9D4CF"),
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(traceback.format_exc())
    else:
        st.info("Base de datos no disponible en este despliegue. Chat y Grafo sí funcionan.")

# 🔧 DIAGNÓSTICO
elif st.session_state.page == "🔧 Diagnóstico":
    st.markdown('<div class="page-header"><h1>🔧 Diagnóstico</h1></div>', unsafe_allow_html=True)
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
        st.markdown("\\n".join(d))

        st.subheader("Test de consulta")
        try:
            r = kb.consultar("matrícula 2025")
            st.text_area("Respuesta (primeros 500 chars)", r["respuesta"][:500])
            st.caption(f"Fuentes: {', '.join(r['fuentes'][:3])}")
        except Exception as e:
            st.error(f"Test falló: {e}")
    except Exception as e:
        st.error(f"Diagnóstico falló: {traceback.format_exc()}")
