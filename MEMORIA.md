# MEMORIA DEL PROYECTO — mifuturo-datos (Dashboard + Deploy)

> Dashboard SIES desplegado en Streamlit Cloud
> Fuente: https://www.mifuturo.cl/sies/
> GitHub: https://github.com/VasquezMaldonadoSebastian/sies-dashboard

---

## Despliegue

| Componente | Detalle |
|------------|---------|
| **URL** | https://sies-dashboard.streamlit.app/ |
| **Repo** | https://github.com/VasquezMaldonadoSebastian/sies-dashboard |
| **Rama** | `main` |
| **File principal** | `app.py` |
| **Python** | 3.14.6 |
| **Dependencias** | streamlit 1.59.1, pandas 3.0.3, plotly 6.8.0, scikit-learn 1.9.0 |
| **Estado** | 🟢 Online (app privada, requiere login) |

### Archivos en git

| Archivo | Tamaño | Función |
|---------|:------:|---------|
| `app.py` | 7.6 KB | Dashboard con navegación sidebar (Chat, Grafo, Dashboard, Diagnóstico) |
| `glue.py` | 11 KB | SIESKnowledgeBase con TF-IDF + DuckDB opcional |
| `search_index.json` | 254 KB | 32 documentos pre-indexados para búsqueda TF-IDF |
| `chromadb/chroma.sqlite3` | — | Metadatos de ChromaDB (32 docs) |
| `chromadb/grafo_conocimiento.html` | 24 KB | Grafo pre-generado (pyvis, 32 nodos, 76 aristas) |
| `lib/` | — | Dependencias vis.js para el grafo |
| `requirements.txt` | — | streamlit, pandas, plotly, scikit-learn |
| `.streamlit/config.toml` | — | Tema y configuración |

### NO en git (solo local)

| Archivo | Tamaño | Razón |
|---------|:------:|-------|
| `mifuturo_sies.db` | 563 MB | Excluido por .gitignore (demasiado grande) |
| Datasets (CSV, XLSX, ZIP) | ~500 MB | Excluidos por .gitignore |
| `venv/`, `__pycache__/` | — | Excluidos por .gitignore |

---

## Decisiones de implementación

### Por qué TF-IDF y no ChromaDB en cloud

ChromaDB usa all-MiniLM-L6-v2 (ONNX) que requiere descargar ~79 MB en cada inicio frío de Streamlit Cloud. Esto puede exceder el timeout/memoria del tier gratuito. 

Solución: extraer los documentos desde chroma.sqlite3 a `search_index.json` (254 KB) y usar `TfidfVectorizer` de scikit-learn. TF-IDF es más simple, no tiene dependencias externas de modelos, y funciona aceptablemente para búsqueda semántica básica sobre ~32 documentos.

### Por qué sidebar en vez de tabs

En Streamlit 1.59+, `st.chat_input` no funciona correctamente dentro de `st.tabs`. La solución fue reemplazar tabs con `st.sidebar.radio`.

---

## Arquitectura del Dashboard

```
app.py
  ├── Sidebar: radio (Chat, Grafo, Dashboard, Diagnóstico)
  │
  ├── 💬 Chat IA
  │   └── glue.SIESKnowledgeBase
  │       ├── search_index.json (32 docs)
  │       ├── TfidfVectorizer + cosine_similarity
  │       └── DuckDB opcional (si existe mifuturo_sies.db)
  │
  ├── 🧠 Grafo
  │   └── chromadb/grafo_conocimiento.html (pre-generado, pyvis)
  │
  ├── 📊 Dashboard
  │   └── SQLite directo (solo si existe mifuturo_sies.db)
  │
  └── 🔧 Diagnóstico
      └── Estado de archivos, imports, test de consulta
```

---

## Sesiones

| Fecha | Resumen |
|-------|---------|
| 2026-06-22 | Descarga inicial de datasets SIES (matrícula, titulación, oferta académica) |
| 2026-06-22 | Investigación de indicadores y KPIs de educación superior chilena |
| 2026-06-23 | ETL: construcción de SQLite con 13 tablas desde CSVs |
| 2026-07-01 | app.py inicial con KPIs, Plotly, modo oscuro |
| 2026-07-08 | **Refactorización completa:** glue layer, chat IA, grafo, deploy Streamlit Cloud. Se reemplazó ChromaDB por TF-IDF para cloud. Sidebar en vez de tabs. |

---

*Última actualización: 2026-07-08*
