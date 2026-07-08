"""
Dashboard SIES — Rediseño Open Design
Paleta cálida: terracota, crema, ámbar, tierra
Tipografía: DM Sans · JetBrains Mono
"""
import traceback
import json
import sqlite3, pandas as pd, streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

st.set_page_config(page_title="Analista SIES", layout="wide", page_icon="🎓",
                   initial_sidebar_state="collapsed")

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

# ── Paleta cálida SIES (parametrizada) ──────────────────────────────────────
P = {
    "bg": "#F5F0EB",
    "surface": "#FCFAFA",
    "fg": "#2B2520",
    "muted": "#6B6560",
    "border": "#D9D4CF",
    "sidebar": "#1E1A17",
    "sidebar_fg": "#C5BEB8",
    "accent": "#B8552E",
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
  
  .stApp, .main, .block-container {{ background: {P['bg']} !important; }}
  #MainMenu, footer, header, .stAppToolbar, [data-testid="stToolbar"] {{ display: none !important; }}
  
  /* No sobreescribir font-family en todo — respetar Material Icons */
  body, .stMarkdown, p, li, h1, h2, h3, h4, h5, h6, .stButton, .stSelectbox, .stRadio, .stTextInput {{
    font-family: 'DM Sans', -apple-system, system-ui, sans-serif;
  }}
  code, pre, .stCodeBlock {{
    font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace;
  }}
  /* Restaurar Material Icons para avatares de Streamlit */
  .material-icons, .material-symbols-outlined, [class*="material"] {{
    font-family: 'Material Icons' !important;
  }}

  /* Brand header */
  .top-brand {{
    display: flex; align-items: center; gap: 10px; margin-bottom: 4px; padding: 4px 0;
  }}
  .top-brand .logo {{
    width: 28px; height: 28px; background: {P['accent']}; border-radius: 8px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 14px; color: white;
  }}
  .top-brand h1 {{ font-size: 18px; font-weight: 600; letter-spacing: -0.3px; color: {P['fg']}; margin: 0; }}
  .top-brand .sub {{ font-size: 11px; color: {P['muted']}; margin-left: 4px; }}

  /* Navbar */
  div[data-testid="column"] + div[data-testid="column"] {{ margin-left: 6px; }}
  div[data-testid="column"] .stButton button {{
    padding: 7px 16px; border-radius: 8px; font-size: 13px; font-weight: 500;
    font-family: inherit; white-space: nowrap; transition: all 0.15s;
  }}
  div[data-testid="column"] .stButton button[kind="secondary"] {{
    background: {P['surface']}; color: {P['muted']}; border: 1px solid {P['border']};
  }}
  div[data-testid="column"] .stButton button[kind="secondary"]:hover {{
    border-color: {P['accent_soft']}; color: {P['accent']}; background: {P['surface']};
  }}
  div[data-testid="column"] .stButton button[kind="primary"] {{
    background: {P['accent']}; color: #FFF; border: 1px solid {P['accent']};
  }}
  div[data-testid="column"] .stButton button[kind="primary"]:hover {{
    background: {P['accent_soft']}; border-color: {P['accent_soft']};
  }}
  .navbar-divider {{ height: 1px; background: {P['border']}; margin: 0 0 16px 0; }}

  /* KPI cards */
  .kpi-row {{ display: flex; gap: 12px; margin: 16px 0; }}
  .kpi-card {{
    flex: 1; background: {P['surface']}; border: 1px solid {P['border']};
    border-radius: 14px; padding: 16px 18px;
    transition: box-shadow 0.2s, transform 0.2s;
  }}
  .kpi-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.06); transform: translateY(-1px); }}
  .kpi-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; color: {P['muted']}; margin-bottom: 3px; }}
  .kpi-value {{ font-size: 26px; font-weight: 600; letter-spacing: -0.5px;
    color: {P['fg']}; line-height: 1.1; }}
  .kpi-footnote {{ font-size: 11px; color: {P['muted']}; margin-top: 3px; }}

  .stChatMessage {{ background: transparent !important; }}
  .stChatMessage [data-testid="chatMessageContent"] {{
    background: {P['surface']} !important; border: 1px solid {P['border']} !important;
    border-radius: 14px !important; padding: 14px 18px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    color: {P['fg']} !important;
  }}
  .stChatMessage [data-testid="chatMessageAvatar"] {{
    background: {P['accent_bg']} !important; color: {P['accent']} !important;
    border-radius: 50%; width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
  }}
  .stChatMessage [data-testid="chatMessageContent"] strong, 
  .stChatMessage [data-testid="chatMessageContent"] em,
  .stChatMessage [data-testid="chatMessageContent"] p,
  .stChatMessage [data-testid="chatMessageContent"] li,
  .stChatMessage [data-testid="chatMessageContent"] span {{
    color: {P['fg']} !important;
  }}
  .stChatMessage [data-testid="chatMessageContent"] table th,
  .stChatMessage [data-testid="chatMessageContent"] table td {{
    color: {P['fg']} !important;
  }}
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageContent"],
  div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarCol"]:has(div[data-testid="userAvatar"])) [data-testid="chatMessageContent"] {{
    background: {P['accent']} !important; border-color: {P['accent']} !important;
  }}
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageContent"],
  div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarCol"]:has(div[data-testid="userAvatar"])) [data-testid="chatMessageContent"],
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageContent"] strong,
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageContent"] em,
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageContent"] p,
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageContent"] span,
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageContent"] td {{
    color: #FFFFFF !important;
  }}
  div[data-testid="stChatMessage"][aria-label*="user"] [data-testid="chatMessageAvatar"],
  div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarCol"]:has(div[data-testid="userAvatar"])) [data-testid="chatMessageAvatar"] {{
    background: {P['sidebar']} !important; color: white !important;
  }}

  /* Chat input */
  .stChatInputContainer {{
    border: 1px solid {P['border']} !important; border-radius: 999px !important; background: {P['surface']} !important;
  }}
  .stChatInputContainer:focus-within {{
    border-color: {P['accent']} !important; box-shadow: 0 0 0 2px {P['accent_bg']} !important;
  }}
  .stChatInputContainer input, .stChatInputContainer textarea {{
    color: {P['fg']} !important;
  }}
  .stChatInputContainer input::placeholder, .stChatInputContainer textarea::placeholder {{
    color: {P['muted']} !important;
  }}

  /* Spinner */
  .stSpinner > div > div {{ color: {P['fg']} !important; }}

  /* Captions, info, warning, error */
  .stCaption {{ color: {P['muted']} !important; }}
  .stInfo, .stAlert {{
    background: {P['accent_bg']} !important; color: {P['fg']} !important; border: 1px solid {P['accent_soft']} !important;
  }}
  .stWarning {{ background: {P['amber_bg']} !important; color: {P['fg']} !important; border: 1px solid {P['amber']} !important; }}
  .stError {{ background: #FDE8E8 !important; color: #991B1B !important; }}
  .stSuccess {{ background: {P['success_bg']} !important; color: {P['success']} !important; }}

  /* Tablas en chat */
  .stChatMessage table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 13px; }}
  .stChatMessage th {{ background: {P['accent_bg']}; padding: 6px 10px; text-align: left; font-weight: 500; font-size: 12px; color: {P['fg']}; }}
  .stChatMessage td {{ padding: 5px 10px; border-bottom: 1px solid {P['border']}; color: {P['fg']}; }}
  .stChatMessage td:last-child {{ text-align: right; font-weight: 500; }}

  /* Entity cards */
  .entity-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 16px; }}
  .entity-card {{
    background: {P['surface']}; border: 1px solid {P['border']}; border-radius: 10px;
    padding: 14px 16px; cursor: pointer; transition: all 0.15s;
  }}
  .entity-card:hover {{ border-color: {P['accent_soft']}; box-shadow: 0 2px 8px rgba(184,85,46,0.08); }}
  .entity-card .name {{ font-size: 13px; font-weight: 500; color: {P['fg']}; }}
  .entity-card .meta {{ font-size: 11px; color: {P['muted']}; display: flex; justify-content: space-between; margin-top: 4px; }}
  .entity-card .bar {{ height: 3px; border-radius: 2px; background: {P['border']}; margin-top: 8px; overflow: hidden; }}
  .entity-card .bar .fill {{ height: 100%; border-radius: 2px; background: {P['accent']}; }}

  .page-header h1 {{ font-size: 22px; font-weight: 600; letter-spacing: -0.3px; color: {P['fg']}; }}
  .page-header p {{ font-size: 13px; color: {P['muted']}; }}

  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: {P['border']}; border-radius: 3px; }}

  /* Tabs en Dashboard */
  .stTabs [data-baseweb="tab-list"] {{ gap: 4px; background: transparent; }}
  .stTabs [data-baseweb="tab"] {{
    padding: 6px 16px; border-radius: 8px; font-size: 13px; font-weight: 500;
    color: {P['muted']};
  }}
  .stTabs [aria-selected="true"] {{
    background: {P['accent_bg']}; color: {P['accent']};
  }}
</style>
""", unsafe_allow_html=True)

# ── Brand + Navbar ─────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-brand">
  <span class="logo">📊</span>
  <h1>SIES</h1>
  <span class="sub">Educación Superior Chile</span>
</div>
""", unsafe_allow_html=True)

nav_items = [
    ("💬 Chat IA", "💬 Chat IA"),
    ("🧠 Grafo", "🧠 Grafo"),
    ("📊 Dashboard", "📊 Dashboard"),
    ("🔧 Diagnóstico", "🔧 Diagnóstico"),
]
current = st.session_state.page
cols = st.columns(len(nav_items))
for i, (label, key) in enumerate(nav_items):
    with cols[i]:
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if current == key else "secondary"):
            st.session_state.page = key
st.markdown('<div class="navbar-divider"></div>', unsafe_allow_html=True)

# ── Helper: KPIs ───────────────────────────────────────────────────────────
def show_kpis(docs=5, hechos=506, entidades=89, categorias=4):
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card"><div class="kpi-label">📄 Documentos</div><div class="kpi-value">{docs}</div><div class="kpi-footnote">informes SIES procesados</div></div>
      <div class="kpi-card"><div class="kpi-label">📊 Hechos</div><div class="kpi-value">{hechos}</div><div class="kpi-footnote">afirmaciones extraídas</div></div>
      <div class="kpi-card"><div class="kpi-label">🏷️ Entidades</div><div class="kpi-value">{entidades}</div><div class="kpi-footnote">instituciones, regiones, áreas</div></div>
      <div class="kpi-card"><div class="kpi-label">📂 Categorías</div><div class="kpi-value">{categorias}</div><div class="kpi-footnote">matrícula · retención · género · titulación</div></div>
    </div>
    """, unsafe_allow_html=True)

def query_df(sql):
    """Ejecuta SQL y retorna DataFrame. Si no hay DB, usa datos estáticos."""
    if DB_EXISTS:
        try:
            conn = sqlite3.connect(str(DB))
            df = pd.read_sql(sql, conn)
            conn.close()
            return df
        except:
            return None
    return None

# ── Datos estáticos precargados ────────────────────────────────────────────
STATIC_PATH = APP_DIR / "dashboard_data.json"
if STATIC_PATH.exists():
    with open(STATIC_PATH, "r", encoding="utf-8") as f:
        STATIC = json.load(f)
else:
    STATIC = {}

def plot_line(df, x, y, title, color="#B8552E"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines+markers",
                             line=dict(color=color, width=3),
                             marker=dict(color=color, size=8)))
    fig.update_layout(title=title, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="DM Sans", size=13, color="#2B2520"),
                      xaxis=dict(gridcolor="#D9D4CF"), yaxis=dict(gridcolor="#D9D4CF"),
                      margin=dict(l=20, r=20, t=30, b=20), height=350)
    return fig

def plot_bar(df, x, y, title, color="#B8552E"):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y], marker_color=color, text=df[y].apply(lambda v: f"{v:,.0f}"), textposition="outside"))
    fig.update_layout(title=title, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="DM Sans", size=13, color="#2B2520"),
                      xaxis=dict(gridcolor="#D9D4CF"), yaxis=dict(gridcolor="#D9D4CF"),
                      margin=dict(l=20, r=20, t=30, b=20), height=400)
    return fig

def plot_pie(df, names, values, title):
    fig = go.Figure(data=[go.Pie(labels=df[names], values=df[values], hole=0.4,
                                  marker=dict(colors=["#B8552E","#C8933C","#D47A5A","#EDDDD4","#6B6560"]))])
    fig.update_layout(title=title, paper_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans", size=13, color="#2B2520"),
                      margin=dict(l=20, r=20, t=30, b=20), height=400, showlegend=True)
    return fig

# ── PÁGINAS ────────────────────────────────────────────────────────────────

# 💬 CHAT IA
if st.session_state.page == "💬 Chat IA":
    st.markdown('<div class="page-header"><h1>💬 Chat IA · SIES</h1><p>Consulta sobre educación superior chilena</p></div>', unsafe_allow_html=True)
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
    show_kpis()
    cards = '<div class="entity-grid">'
    for name, tipo, hechos, pct in [
        ("📊 Matrícula Total", "concepto", "9 hechos", 100),
        ("🏫 U. Católica de Temuco", "institución", "72 hechos", 80),
        ("👤 Participación Femenina", "concepto", "12 hechos", 60),
        ("🔄 Retención 1er Año", "concepto", "15 hechos", 70),
    ]:
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
            st.markdown("""<div style="display:flex;gap:1.5rem;font-size:0.8rem;color:#6B6560;">
                <span>■ <span style="color:#B8552E;">Concepto</span></span>
                <span>★ <span style="color:#C8933C;">Entidad</span></span>
                <span>● <span style="color:#3A7D5C;">Informe PDF</span></span></div>""", unsafe_allow_html=True)
        else:
            st.warning("Grafo no disponible")
    except Exception as e:
        st.error(traceback.format_exc())

# 📊 DASHBOARD
elif st.session_state.page == "📊 Dashboard":
    st.markdown('<div class="page-header"><h1>📊 Dashboard SIES</h1><p>Indicadores clave de educación superior chilena</p></div>', unsafe_allow_html=True)

    def kpi_static():
        evo = STATIC.get("matricula_evolucion", [])
        if evo:
            ult = evo[-1]
            ant = evo[-2] if len(evo) > 1 else ult
            crec = f"+{((ult['total_millones']-ant['total_millones'])/ant['total_millones']*100):.1f}% vs {ant['año']}" if ant['total_millones'] else "—"
            show_kpis(docs=f"{ult['año']}", hechos=f"{ult['total_millones']:.2f}M",
                      entidades=f"{ult['pct_mujeres']:.1f}%", categorias=crec)
        else:
            show_kpis()

    def df_from_static(key):
        return pd.DataFrame(STATIC.get(key, []))

    # KPIs
    if DB_EXISTS:
        df_evo = query_df("""
            SELECT CAST(REPLACE("AÑO", 'MAT_', '') AS INTEGER) as año,
                   ROUND(SUM("TOTAL MATRÍCULA")/1000000.0, 2) as total_millones,
                   ROUND(100.0 * SUM("TOTAL MATRÍCULA MUJERES") / SUM("TOTAL MATRÍCULA"), 1) as pct_mujeres
            FROM matricula GROUP BY año ORDER BY año
        """)
        if df_evo is not None and len(df_evo) > 0:
            ult = df_evo.iloc[-1]
            ant = df_evo.iloc[-2] if len(df_evo) > 1 else ult
            show_kpis(docs=f"{ult['año']:.0f}", hechos=f"{ult['total_millones']:.2f}M",
                      entidades=f"{ult['pct_mujeres']:.1f}%",
                      categorias=f"+{((ult['total_millones']-ant['total_millones'])/ant['total_millones']*100):.1f}% vs {ant['año']:.0f}")
        else:
            kpi_static()
    else:
        kpi_static()

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Matrícula", "🎓 Titulación", "🏫 Por Tipo IES", "📚 Áreas"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            df = query_df("SELECT CAST(REPLACE(\"AÑO\", 'MAT_', '') AS INTEGER) as año, ROUND(SUM(\"TOTAL MATRÍCULA\")/1000000.0, 2) as total_millones FROM matricula GROUP BY año ORDER BY año") if DB_EXISTS else df_from_static("matricula_evolucion")[["año","total_millones"]]
            if df is not None and len(df): st.plotly_chart(plot_line(df, "año", "total_millones", "Matrícula Total (millones)"), use_container_width=True)
        with c2:
            df = query_df("SELECT CAST(REPLACE(\"AÑO\", 'MAT_', '') AS INTEGER) as año, ROUND(100.0*SUM(\"TOTAL MATRÍCULA MUJERES\")/SUM(\"TOTAL MATRÍCULA\"),1) as pct_mujeres FROM matricula GROUP BY año ORDER BY año") if DB_EXISTS else df_from_static("matricula_evolucion")[["año","pct_mujeres"]]
            if df is not None and len(df): st.plotly_chart(plot_line(df, "año", "pct_mujeres", "% Mujeres en Matrícula", color="#C8933C"), use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            df = query_df("SELECT CAST(REPLACE(\"AÑO\", 'MAT_', '') AS INTEGER) as año, ROUND(SUM(\"TOTAL MATRÍCULA PRIMER AÑO\")/1000000.0,2) as primer_anio FROM matricula WHERE \"TOTAL MATRÍCULA PRIMER AÑO\" IS NOT NULL AND \"TOTAL MATRÍCULA PRIMER AÑO\" != '' GROUP BY año ORDER BY año") if DB_EXISTS else df_from_static("matricula_evolucion")[["año","primer_anio_millones"]].rename(columns={"primer_anio_millones":"primer_anio"})
            if df is not None and len(df): st.plotly_chart(plot_line(df, "año", "primer_anio", "Matrícula 1er Año (millones)", color="#D47A5A"), use_container_width=True)
        with c2:
            st.markdown("##### Matrícula por Nivel (2024)")
            df = query_df("""SELECT "NIVEL GLOBAL" as nivel, ROUND(SUM("TOTAL MATRÍCULA")/1000000.0,2) as total_millones FROM matricula WHERE CAST(REPLACE("AÑO",'MAT_','') AS INTEGER)=2024 AND "NIVEL GLOBAL" IS NOT NULL AND "NIVEL GLOBAL" != '' GROUP BY nivel ORDER BY SUM("TOTAL MATRÍCULA") DESC""") if DB_EXISTS else df_from_static("matricula_por_nivel_2024")
            if df is not None and len(df): st.plotly_chart(plot_pie(df, "nivel", "total_millones", ""), use_container_width=True)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            df = query_df("""SELECT CAST(REPLACE("AÑO",'TIT_','') AS INTEGER) as año, ROUND(SUM("TOTAL TITULACIONES")/1000.0,1) as total_miles FROM titulacion GROUP BY año ORDER BY año""") if DB_EXISTS else df_from_static("titulacion_evolucion")[["año","total_miles"]]
            if df is not None and len(df): st.plotly_chart(plot_line(df, "año", "total_miles", "Titulación Total (miles)"), use_container_width=True)
        with c2:
            df = query_df("""SELECT CAST(REPLACE("AÑO",'TIT_','') AS INTEGER) as año, ROUND(100.0*SUM("TITULACIONES MUJERES POR PROGRAMA")/SUM("TOTAL TITULACIONES"),1) as pct_mujeres FROM titulacion GROUP BY año ORDER BY año""") if DB_EXISTS else df_from_static("titulacion_evolucion")[["año","pct_mujeres"]]
            if df is not None and len(df): st.plotly_chart(plot_line(df, "año", "pct_mujeres", "% Mujeres Tituladas", color="#C8933C"), use_container_width=True)

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            df = query_df("""SELECT "CLASIFICACIÓN INSTITUCIÓN NIVEL 1" as tipo, ROUND(SUM("TOTAL MATRÍCULA")/1000000.0,2) as total_millones FROM matricula WHERE CAST(REPLACE("AÑO",'MAT_','') AS INTEGER)=2025 GROUP BY tipo ORDER BY SUM("TOTAL MATRÍCULA") DESC""") if DB_EXISTS else df_from_static("matricula_por_tipo_2025")
            if df is not None and len(df): st.plotly_chart(plot_bar(df, "tipo", "total_millones", "Matrícula 2025 por Tipo IES (millones)"), use_container_width=True)
        with c2:
            st.markdown("##### Distribución por Nivel y Tipo (2024)")
            df = query_df("""SELECT "CLASIFICACIÓN INSTITUCIÓN NIVEL 1" as tipo, "NIVEL GLOBAL" as nivel, ROUND(SUM("TOTAL MATRÍCULA")/1000.0,0) as total_miles FROM matricula WHERE CAST(REPLACE("AÑO",'MAT_','') AS INTEGER)=2024 AND "NIVEL GLOBAL" IS NOT NULL AND "NIVEL GLOBAL" != '' GROUP BY tipo, nivel ORDER BY tipo, nivel""") if DB_EXISTS else df_from_static("matricula_tipo_nivel_2024")
            if df is not None and len(df):
                fig = go.Figure()
                for nivel in df["nivel"].unique():
                    subset = df[df["nivel"]==nivel]
                    fig.add_trace(go.Bar(name=nivel, x=subset["tipo"], y=subset["total_miles"]))
                fig.update_layout(barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font=dict(family="DM Sans", size=12, color="#2B2520"),
                                  margin=dict(l=20, r=20, t=10, b=20), height=400, legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig, use_container_width=True)

    with tab4:
        col_a, col_b = st.columns(2)
        with col_a:
            df = query_df("""SELECT "ÁREA DEL CONOCIMIENTO" as area, ROUND(SUM("TOTAL MATRÍCULA")/1000.0,0) as total_miles FROM matricula WHERE CAST(REPLACE("AÑO",'MAT_','') AS INTEGER)=2025 AND "ÁREA DEL CONOCIMIENTO" IS NOT NULL AND "ÁREA DEL CONOCIMIENTO" != '' GROUP BY area ORDER BY SUM("TOTAL MATRÍCULA") DESC LIMIT 8""") if DB_EXISTS else df_from_static("matricula_por_area_2025")
            if df is not None and len(df): st.plotly_chart(plot_bar(df, "area", "total_miles", "Matrícula 2025 por Área (miles)"), use_container_width=True)
        with col_b:
            st.markdown("##### Top 10 Instituciones (2024)")
            df = query_df("""SELECT "NOMBRE INSTITUCIÓN" as inst, ROUND(SUM("TOTAL MATRÍCULA")/1000.0,0) as total_miles FROM matricula WHERE CAST(REPLACE("AÑO",'MAT_','') AS INTEGER)=2024 AND "NOMBRE INSTITUCIÓN" IS NOT NULL AND "NOMBRE INSTITUCIÓN" != '' GROUP BY inst ORDER BY SUM("TOTAL MATRÍCULA") DESC LIMIT 10""") if DB_EXISTS else df_from_static("top_instituciones_2024")
            if df is not None and len(df):
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df["total_miles"], y=df["inst"], orientation="h", marker_color="#B8552E",
                                     text=df["total_miles"].apply(lambda v: f"{v:,.0f}K"), textposition="outside"))
                fig.update_layout(title="", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font=dict(family="DM Sans", size=12, color="#2B2520"),
                                  xaxis=dict(gridcolor="#D9D4CF"),
                                  margin=dict(l=20, r=80, t=10, b=20), height=400)
                st.plotly_chart(fig, use_container_width=True)

# 🔧 DIAGNÓSTICO
elif st.session_state.page == "🔧 Diagnóstico":
    st.markdown('<div class="page-header"><h1>🔧 Diagnóstico</h1></div>', unsafe_allow_html=True)
    try:
        d = [f"**Python:** {sys.version}", f"**Directorio:** {APP_DIR}"]
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
        st.subheader("Test de consulta")
        try:
            r = kb.consultar("matrícula 2025")
            st.text_area("Respuesta (primeros 500 chars)", r["respuesta"][:500])
            st.caption(f"Fuentes: {', '.join(r['fuentes'][:3])}")
        except Exception as e:
            st.error(f"Test falló: {e}")
    except Exception as e:
        st.error(f"Diagnóstico falló: {traceback.format_exc()}")
