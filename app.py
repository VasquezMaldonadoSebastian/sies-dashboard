"""
Dashboard SIES — Educación Superior de Chile
Chat IA + Grafo del Conocimiento + KPIs
Fuente: www.mifuturo.cl, de Mineduc.
"""

import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path
import sys
import os

# ── Añadir glue al path ─────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
CHROMA_DIR = APP_DIR / "chromadb"
sys.path.insert(0, str(APP_DIR))

# ── Configuración ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SIES Dashboard • Educación Superior Chile",
    layout="wide",
    page_icon="🎓",
)

DB = Path(__file__).parent / "mifuturo_sies.db"
DB_EXISTS = DB.exists()

# ── Session state ────────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy el asistente SIES. Pregúntame sobre matrícula, titulación, género o cualquier indicador de educación superior en Chile."}
    ]
if "kb" not in st.session_state:
    st.session_state.kb = None
if "kb_ready" not in st.session_state:
    st.session_state.kb_ready = True

# ── Paletas ──────────────────────────────────────────────────────────────
def palette(dark=False):
    if dark:
        return {
            "bg": "#0F172A", "card": "#1E293B", "card_border": "#334155",
            "primary": "#60A5FA", "primary_dark": "#93C5FD", "primary_lighter": "#1E3A5F",
            "primary_bg": "rgba(96,165,250,0.12)", "accent": "#FBBF24",
            "accent_bg": "rgba(251,191,36,0.12)", "text": "#F1F5F9", "text_light": "#94A3B8",
            "border": "#334155", "header_from": "#0B1E3A", "header_to": "#1E3A5F",
            "shadow": "rgba(0,0,0,0.3)", "grid": "#334155", "chart_bg": "#1E293B",
            "paper_bg": "rgba(30,41,59,0)", "gray_500": "#64748B", "gray_700": "#334155",
            "blue_600": "#2563EB", "blue_700": "#1D4ED8",
        }
    else:
        return {
            "bg": "#F8FAFC", "card": "#FFFFFF", "card_border": "#E2E8F0",
            "primary": "#0B4A7A", "primary_dark": "#002A55", "primary_lighter": "#E8F0FE",
            "primary_bg": "rgba(11,74,122,0.07)", "accent": "#D4951A",
            "accent_bg": "rgba(212,149,26,0.08)", "text": "#0F172A", "text_light": "#475569",
            "border": "#CBD5E1", "header_from": "#002A55", "header_to": "#0B4A7A",
            "shadow": "rgba(0,0,0,0.08)", "grid": "#E2E8F0", "chart_bg": "#FFFFFF",
            "paper_bg": "rgba(255,255,255,0)", "gray_500": "#64748B", "gray_700": "#334155",
            "blue_600": "#2563EB", "blue_700": "#1D4ED8",
        }

p = palette(st.session_state.dark_mode)

# ── CSS ──────────────────────────────────────────────────────────────────
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
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 24px var(--shadow); }}
    .header h1 {{ margin: 0; font-size: 1.5rem; font-weight: 700; color: #FFF !important; }}
    .header h1 small {{ font-size: 0.8rem; font-weight: 400; opacity: 0.75; display: block; color: rgba(255,255,255,0.8) !important; }}
    .theme-btn {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
        padding: 0.4rem 1rem; cursor: pointer; font-size: 0.8rem; font-weight: 600;
        color: var(--text); transition: all 0.2s; box-shadow: 0 1px 3px var(--shadow); }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.8rem; margin-bottom: 1.5rem; }}
    .kpi-card {{ background: var(--card); border-radius: 12px; padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px var(--shadow); border-left: 4px solid var(--primary); }}
    .kpi-card .label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.6px;
        color: var(--text-light); font-weight: 600; }}
    .kpi-card .value {{ font-size: 1.8rem; font-weight: 700; color: var(--primary) !important;
        margin: 0; line-height: 1.2; }}
    .kpi-card .sub {{ font-size: 0.75rem; color: var(--text-light); margin-top: 0.2rem; }}
    .section-title {{ font-size: 1.1rem; font-weight: 600; color: var(--primary) !important;
        margin: 1rem 0 0.8rem 0; padding-bottom: 0.4rem; border-bottom: 2px solid var(--border); }}
    .chart-card {{ background: var(--card); border-radius: 12px; padding: 0.8rem;
        box-shadow: 0 2px 8px var(--shadow); margin-bottom: 0.8rem;
        border: 1px solid var(--card-border); }}
    .chat-msg {{ background: var(--card); border-radius: 12px; padding: 1rem;
        margin-bottom: 0.5rem; border: 1px solid var(--border); }}
    [data-testid="stTab"] {{ font-size: 0.9rem; font-weight: 600; }}
    .stPlotlyChart {{ width: 100%; }}
    [data-testid="stToolbar"], #MainMenu, footer {{ display: none; }}
    .stButton > button {{ display: none; }}
</style>""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────
emoji_theme = "🌙" if st.session_state.dark_mode else "☀️"
st.markdown(f"""
<div class="header">
    <div>
        <h1>🎓 SIES Dashboard <small>Educación Superior • Chile • www.mifuturo.cl</small></h1>
    </div>
    <div style="display:flex;align-items:center;gap:0.8rem;">
        <span style="color:rgba(255,255,255,0.8);font-size:0.78rem;">SIES — MINEDUC</span>
    </div>
</div>
""", unsafe_allow_html=True)

col_t, _ = st.columns([1, 5])
with col_t:
    if st.button(f"{emoji_theme} {'Claro' if st.session_state.dark_mode else 'Oscuro'}", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# ── Tabs ─────────────────────────────────────────────────────────────────
tab_dash, tab_chat, tab_graph = st.tabs(["📊 Dashboard", "💬 Chat IA", "🧠 Grafo del Conocimiento"])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════
with tab_dash:
    @st.cache_data(ttl=3600, show_spinner="Cargando datos...")
    def load_data():
        if not DB_EXISTS:
            return None
        conn = sqlite3.connect(str(DB))
        df_mat = pd.read_sql("""
            SELECT "AÑO" as año, SUM("TOTAL MATRÍCULA") as total_matricula,
                   SUM("TOTAL MATRÍCULA PRIMER AÑO") as primer_anio,
                   SUM("TOTAL MATRÍCULA MUJERES") as mujeres,
                   SUM("TOTAL MATRÍCULA HOMBRES") as hombres
            FROM matricula GROUP BY "AÑO" ORDER BY "AÑO"
        """, conn)
        df_mat["año_num"] = df_mat["año"].str.replace("MAT_", "").astype(int)
        df_mat_tipo = pd.read_sql("""
            SELECT "CLASIFICACIÓN INSTITUCIÓN NIVEL 1" as tipo, SUM("TOTAL MATRÍCULA") as total
            FROM matricula WHERE "AÑO" = 'MAT_2025' GROUP BY tipo ORDER BY total DESC
        """, conn)
        df_mat_area = pd.read_sql("""
            SELECT "ÁREA DEL CONOCIMIENTO" as area, SUM("TOTAL MATRÍCULA") as total
            FROM matricula WHERE "AÑO" = 'MAT_2025' GROUP BY area ORDER BY total DESC
        """, conn)
        df_mat_region = pd.read_sql("""
            SELECT REGIÓN as region, SUM("TOTAL MATRÍCULA") as total
            FROM matricula WHERE "AÑO" = 'MAT_2025' GROUP BY region ORDER BY total DESC
        """, conn)
        df_tit = pd.read_sql("""
            SELECT "AÑO" as año, SUM("TOTAL TITULACIONES") as total_titulados,
                   SUM("TITULACIONES MUJERES POR PROGRAMA") as mujeres
            FROM titulacion GROUP BY "AÑO" ORDER BY "AÑO"
        """, conn)
        df_tit["año_num"] = df_tit["año"].str.replace("TIT_", "").astype(int)
        df_ret = pd.read_sql("""
            SELECT anio, tipo_ies, AVG(tasa_retencion) as retencion
            FROM retencion WHERE tipo_ies IN ('CFT', 'IP', 'Universidad')
            GROUP BY anio, tipo_ies ORDER BY anio, tipo_ies
        """, conn)
        conn.close()
        return {"mat": df_mat, "mat_tipo": df_mat_tipo, "mat_area": df_mat_area,
                "mat_region": df_mat_region, "tit": df_tit, "ret": df_ret}

    data = load_data()
    if data is None:
        st.info("""
        ### 🗄️ Base de datos no disponible

        La base SQLite (563 MB) no está incluida en esta versión desplegada.
        
        **Para ver los datos completos:**
        1. Clona el repo y descarga la DB desde tu máquina local
        2. O ejecuta `etl_build_db.py` para reconstruirla desde los CSVs
        3. O visita el [repositorio](https://github.com/VasquezMaldonadoSebastian/sies-dashboard) para instrucciones

        Mientras tanto, puedes explorar **Chat IA** y **Grafo** que funcionan con la base vectorial.
        """)
        st.stop()

    df_mat = data["mat"]; df_tit = data["tit"]; df_ret = data["ret"]
    df_mat_tipo = data["mat_tipo"]; df_mat_area = data["mat_area"]; df_mat_region = data["mat_region"]

    # KPIs
    ult_mat = df_mat[df_mat["año_num"] == df_mat["año_num"].max()]
    ult_tit = df_tit[df_tit["año_num"] == df_tit["año_num"].max()]
    total_mat = int(ult_mat["total_matricula"].values[0])
    total_primer = int(ult_mat["primer_anio"].values[0])
    pct_mujeres = round(100 * ult_mat["mujeres"].values[0] / total_mat, 1)

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="label">Matrícula 2025</div>
            <div class="value">{total_mat:,}</div>
            <div class="sub">{total_primer:,} primer año</div></div>
        <div class="kpi-card"><div class="label">Titulados 2025</div>
            <div class="value">{int(ult_tit['total_titulados'].values[0]):,}</div>
            <div class="sub">+8% vs 2024</div></div>
        <div class="kpi-card"><div class="label">Mujeres en Matrícula</div>
            <div class="value">{pct_mujeres}%</div>
            <div class="sub">Participación femenina</div></div>
        <div class="kpi-card"><div class="label">Cobertura</div>
            <div class="value">1.46M</div>
            <div class="sub">Estudiantes ES 2025</div></div>
    </div>
    """, unsafe_allow_html=True)

    def make_fig(title):
        fig = go.Figure()
        fig.update_layout(title=dict(text=title, font=dict(size=14, color=p["primary"]), x=0),
            font=dict(family="Segoe UI, Arial", size=11, color=p["text"]),
            plot_bgcolor=p["card"], paper_bgcolor=p["paper_bg"],
            hovermode="x unified", margin=dict(l=40, r=20, t=40, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor=p["grid"], zeroline=False),
            yaxis=dict(gridcolor=p["grid"], zeroline=False))
        return fig

    # Fila 1: Evolución + Titulación
    st.markdown(f'<div class="section-title">📈 Evolución 2007–2025</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = make_fig("Evolución Matrícula Total")
        fig.add_trace(go.Scatter(x=df_mat["año_num"], y=df_mat["total_matricula"], mode="lines+markers",
            name="Total", line=dict(color=p["primary"], width=3), fill="tozeroy", fillcolor=p["primary_bg"]))
        fig.add_trace(go.Scatter(x=df_mat["año_num"], y=df_mat["mujeres"], mode="lines+markers",
            name="Mujeres", line=dict(color=p["accent"], width=2)))
        fig.add_trace(go.Scatter(x=df_mat["año_num"], y=df_mat["hombres"], mode="lines+markers",
            name="Hombres", line=dict(color=p["gray_500"], width=2)))
        fig.update_yaxes(tickformat=",")
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        fig = make_fig("Evolución Titulación")
        fig.add_trace(go.Scatter(x=df_tit["año_num"], y=df_tit["total_titulados"], mode="lines+markers",
            name="Titulados", line=dict(color=p["primary"], width=3), fill="tozeroy", fillcolor=p["primary_bg"]))
        fig.add_trace(go.Scatter(x=df_tit["año_num"], y=df_tit["mujeres"], mode="lines+markers",
            name="Mujeres", line=dict(color=p["accent"], width=2)))
        fig.update_yaxes(tickformat=",")
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Fila 2: Tipo + Área
    st.markdown(f'<div class="section-title">🏛️ Estructura 2025</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = make_fig("Matrícula por Tipo de Institución")
        fig.add_trace(go.Bar(x=df_mat_tipo["total"], y=df_mat_tipo["tipo"], orientation="h",
            marker=dict(color=[p["primary"], p["blue_600"], p["blue_700"]]),
            text=df_mat_tipo["total"].apply(lambda x: f"{x/1e6:.1f}M"), textposition="outside"))
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        fig = make_fig("Matrícula por Región")
        fig.add_trace(go.Bar(x=df_mat_region["total"], y=df_mat_region["region"], orientation="h",
            marker=dict(color=p["primary_lighter"]),
            text=df_mat_region["total"].apply(lambda x: f"{x/1e3:.0f}K"), textposition="outside"))
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Fila 3: Retención + Género
    st.markdown(f'<div class="section-title">📊 Indicadores Clave</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = make_fig("Retención 1er Año por Tipo")
        for tipo, color in [("Universidad", p["primary"]), ("IP", p["accent"]), ("CFT", p["gray_500"])]:
            df_t = df_ret[df_ret["tipo_ies"] == tipo]
            fig.add_trace(go.Scatter(x=df_t["anio"], y=df_t["retencion"]*100, mode="lines+markers",
                name=tipo, line=dict(color=color, width=2.5)))
        fig.update_yaxes(ticksuffix="%", range=[40, 90])
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        df_pct = df_mat.copy()
        df_pct["pct_mujeres"] = 100 * df_pct["mujeres"] / df_pct["total_matricula"]
        fig = make_fig("% Mujeres en Matrícula")
        fig.add_trace(go.Scatter(x=df_pct["año_num"], y=df_pct["pct_mujeres"], mode="lines+markers",
            name="% Mujeres", line=dict(color=p["accent"], width=3), fill="tozeroy", fillcolor=p["accent_bg"]))
        fig.update_yaxes(ticksuffix="%", range=[48, 56])
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""<div style="margin-top:2rem;padding:1rem;text-align:center;font-size:0.8rem;
        color:var(--text-light);border-top:1px solid var(--border);">
        <strong>FUENTE:</strong> www.mifuturo.cl, de Mineduc. Datos SIES 2007–2025.</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 2: CHAT IA
# ══════════════════════════════════════════════════════════════════════════
with tab_chat:
    # Inicializar KB perezosamente
    if st.session_state.kb is None:
        with st.spinner("Inicializando base de conocimiento SIES..."):
            try:
                from glue import SIESKnowledgeBase
                try:
                    st.session_state.kb = SIESKnowledgeBase()
                    st.session_state.kb_ready = True
                except Exception as e:
                    st.session_state.kb_ready = False
                    st.warning(f"No se pudo cargar la base de conocimiento completa. El modelo de embeddings puede estar descargándose aún. Detalle: {str(e)[:200]}")
            except ImportError as e:
                st.session_state.kb_ready = False
                st.warning(f"Error de importación: {e}")

    if not st.session_state.get("kb_ready", True):
        st.info("💡 Puedes explorar el **Grafo del Conocimiento** (tercer tab) mientras tanto.")
        st.stop()

    kb = st.session_state.kb

    st.markdown(f"""<div style="margin-bottom:1rem;">
        <p style="color:var(--text-light);font-size:0.85rem;">
        Consulta en lenguaje natural sobre educación superior chilena.
        Ej: <em>"¿Cuántas mujeres hay en la educación superior?", "Evolución de la matrícula", "Top universidades"</em></p>
    </div>""", unsafe_allow_html=True)

    # Historial de chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input de chat
    if prompt := st.chat_input("Escribe tu pregunta sobre educación superior..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando base de conocimiento..."):
                try:
                    resultado = kb.consultar(prompt)
                    respuesta = resultado["respuesta"]
                    fuentes = resultado.get("fuentes", [])

                    # Mostrar respuesta
                    st.markdown(respuesta)

                    # Mostrar fuentes si hay
                    if fuentes:
                        st.markdown(f"""<div style="margin-top:0.5rem;font-size:0.75rem;color:var(--text-light);">
                        📎 <strong>Fuentes:</strong> {', '.join(fuentes[:3])}</div>""", unsafe_allow_html=True)

                    st.session_state.messages.append({"role": "assistant", "content": respuesta})
                except Exception as e:
                    err = f"⚠️ Error al consultar: {str(e)}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})

    # Botón limpiar chat
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "¡Hola! Soy el asistente SIES. Pregúntame sobre matrícula, titulación, género o cualquier indicador de educación superior en Chile."}
        ]
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TAB 3: GRAFO DEL CONOCIMIENTO
# ══════════════════════════════════════════════════════════════════════════
with tab_graph:
    st.markdown(f"""<p style="color:var(--text-light);font-size:0.85rem;">
    Visualización del cerebro de conocimiento SIES. Cada nodo es un documento (wiki, informe).
    Las conexiones representan similitud semántica. Arrastra, zoom, y haz clic en nodos.</p>
    """, unsafe_allow_html=True)

    graph_html = CHROMA_DIR / "grafo_conocimiento.html"

    if not graph_html.exists() or st.button("🔄 Regenerar grafo", use_container_width=True):
        with st.spinner("Construyendo grafo de conocimiento desde ChromaDB..."):
            try:
                import chromadb
                from pyvis.network import Network
                import json

                client = chromadb.PersistentClient(path=str(CHROMA_DIR))
                # La primera carga puede demorar (descarga modelo ONNX ~79 MB)
                try:
                    collection = client.get_collection("sies-matricula")
                except Exception as e:
                    st.error(f"No se pudo cargar ChromaDB. En el primer inicio puede demorar ~1 minuto descargando el modelo de embeddings. Intenta regenerar en unos minutos. Detalle: {str(e)[:200]}")
                    st.stop()

                # Obtener todos los documentos
                all_docs = collection.get()
                doc_ids = all_docs["ids"]
                metas = all_docs["metadatas"]
                count = len(doc_ids)

                # Crear red
                net = Network(height="600px", width="100%", bgcolor=p["bg"], font_color=p["text"])
                net.set_options("""
                {
                    "physics": { "stabilization": { "iterations": 100 }, 
                                "barnesHut": { "gravitationalConstant": -3000, "springConstant": 0.04 } },
                    "edges": { "color": { "inherit": true, "opacity": 0.3 }, "width": 1 },
                    "nodes": { "borderWidth": 1, "size": 15, "font": { "size": 11 } }
                }
                """)

                # Colores por tipo
                type_colors = {
                    "concept": "#60A5FA",
                    "entity": "#FBBF24",
                    "meta": "#94A3B8",
                    "raw_pdf": "#34D399",
                }
                type_shapes = {
                    "concept": "box",
                    "entity": "star",
                    "meta": "ellipse",
                    "raw_pdf": "dot",
                }

                # Agregar nodos
                node_labels = {}
                for i, (doc_id, meta) in enumerate(zip(doc_ids, metas)):
                    doc_type = meta.get("type", "raw_pdf")
                    label = doc_id.replace("wiki/", "").replace("raw/", "").replace("_", " ").replace("-", " ").title()
                    if len(label) > 30:
                        label = label[:30] + "…"
                    color = type_colors.get(doc_type, "#64748B")
                    shape = type_shapes.get(doc_type, "dot")
                    title = f"<b>{doc_id}</b><br>Tipo: {doc_type}<br>Fuente: {meta.get('source', '')}"
                    net.add_node(doc_id, label=label, title=title, color=color, shape=shape, size=18 if doc_type != "raw_pdf" else 10)
                    node_labels[doc_id] = label

                # Agregar aristas basadas en similitud (cada nodo consulta sus top-k similares)
                edges_added = set()
                for doc_id in doc_ids[:count]:
                    try:
                        similar = collection.query(query_texts=[doc_id.replace("wiki/", " ").replace("raw/", " ").replace("_", " ")], n_results=4)
                        if similar["ids"][0]:
                            for sim_id, dist in zip(similar["ids"][0], similar["distances"][0]):
                                if sim_id != doc_id and dist < 0.6:
                                    edge_key = tuple(sorted([doc_id, sim_id]))
                                    if edge_key not in edges_added:
                                        weight = max(1, int((1 - dist) * 5))
                                        net.add_edge(doc_id, sim_id, value=weight, title=f"sim: {1-dist:.2f}")
                                        edges_added.add(edge_key)
                    except:
                        pass

                # Guardar
                net.save_graph(str(graph_html))
                st.success(f"✅ Grafo generado: {count} nodos, {len(edges_added)} conexiones")
            except Exception as e:
                st.error(f"Error generando grafo: {e}")

    # Mostrar grafo
    if graph_html.exists():
        with open(graph_html, "r", encoding="utf-8") as f:
            html_content = f.read()
        # Inyectar color de fondo según modo
        html_content = html_content.replace(
            '<div id="mynetwork"',
            f'<div id="mynetwork" style="background:{p["bg"]};border-radius:12px;border:1px solid {p["border"]};"'
        )
        st.components.v1.html(html_content, height=620)

        # Leyenda
        st.markdown(f"""
        <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:0.5rem;font-size:0.8rem;color:var(--text-light);">
            <span>■ <span style="color:#60A5FA;font-weight:bold;">Concepto</span> (wiki)</span>
            <span>★ <span style="color:#FBBF24;font-weight:bold;">Entidad</span> (institución)</span>
            <span>● <span style="color:#34D399;font-weight:bold;">Informe</span> (PDF convertido)</span>
            <span>● <span style="color:#94A3B8;">Meta</span> (schema/index)</span>
        </div>
        <p style="font-size:0.75rem;color:var(--text-light);margin-top:0.3rem;">
        Las aristas conectan documentos semánticamente similares (modelo all-MiniLM-L6-v2). Más grueso = mayor similitud.</p>
        """, unsafe_allow_html=True)

        # Estadísticas
        st.markdown(f"""
        <div style="background:var(--card);border-radius:12px;padding:1rem;margin-top:0.5rem;
            border:1px solid var(--card-border);">
            <strong style="color:var(--text);">🧠 El Cerebro SIES</strong>
            <p style="color:var(--text-light);font-size:0.82rem;margin-top:0.3rem;">
            Este grafo representa la base de conocimiento vectorial. Cada nodo es un documento indexado en ChromaDB.
            Las aristas se generan consultando los vecinos semánticos más cercanos (distancia coseno &lt; 0.6).
            </p>
            <ul style="color:var(--text-light);font-size:0.8rem;">
                <li>📄 <strong>9 páginas wiki</strong> (conceptos, entidades, schema)</li>
                <li>📑 <strong>23 informes PDF</strong> convertidos a markdown</li>
                <li>🔗 <strong>Similitud semántica</strong> como conexiones entre documentos</li>
                <li>⚡ <strong>Streamlit + ChromaDB + DuckDB</strong> — todo open-source, local, sin nube</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Haz clic en 'Regenerar grafo' para construir la visualización por primera vez.")
