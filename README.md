# 🎓 Analista SIES — Chat + Dashboard + Grafo de Conocimiento

Asistente inteligente para consultar datos del **Servicio de Información de Educación Superior (SIES)** de Chile. Procesa informes PDF oficiales y bases de datos históricas para responder preguntas sobre matrícula, brechas de género, titulación y retención en la educación superior chilena.

**URL:** https://sies-dashboard.streamlit.app/

---

## 🚀 Stack

| Componente | Tecnología |
|------------|-----------|
| Frontend | Streamlit + Plotly |
| Conocimiento | Grafo JSON (89 entidades, 506 hechos extraídos de PDFs) |
| Datos históricos | DuckDB / SQLite (563 MB, 2007–2025) |
| Síntesis LLM | OpenCode API (deepseek-v4-flash-free → big-pickle → mimo-v2.5) |
| Extracción | Docling → Ollama 3B |
| Deploy | Streamlit Cloud |

## ✨ Funcionalidades

### 💬 Chat IA
Responde preguntas en lenguaje natural sobre educación superior chilena:
- *"¿Cuántos estudiantes había en 2025?"* → **1.455.639**
- *"¿Qué sabemos de la UCT?"* → Matrícula, género, retención, titulación
- *"¿Cómo ha evolucionado la matrícula?"* → Tabla 2007–2025
- *"¿Qué dice el informe de Brechas de Género 2024?"* → Síntesis con fuentes

Usa **grafo de conocimiento** + **OpenCode API** para síntesis, con fallback a respuestas estructuradas sin LLM.

### 🧠 Grafo de Conocimiento
Visualización interactiva (pyvis) de 89 entidades conectadas por 506 hechos extraídos de 5 informes oficiales.

### 📊 Dashboard
4 tabs con indicadores clave:
- 📈 Matrícula (evolución 19 años, % mujeres, 1er año, niveles)
- 🎓 Titulación (totales, % mujeres)
- 🏫 Por tipo de IES (U, IP, CFT)
- 📚 Áreas del conocimiento + Top 10 instituciones

### 🔧 Diagnóstico
Estado del sistema, componentes, y test de consulta en vivo.

---

## 🏗️ Arquitectura

```
Usuario → app.py → sies_engine.py
                        │
                        ├─ ¿Saludo? → Respuesta directa
                        ├─ ¿Numérico? → DuckDB / JSON estático
                        ├─ ¿Semántico? → Grafo + OpenCode API
                        ├─ ¿Mixto? → Grafo + DuckDB + API
                        └─ ¿No sé? → Guía con categorías
```

### Pipeline de extracción
```
PDF SIES → Docling → Markdown → Ollama 3B → Entidades + Hechos → Grafo JSON
```

### Modelos LLM (cadena de fallback)
1. `deepseek-v4-flash-free`
2. `big-pickle`  
3. `mimo-v2.5-free`
4. *(Fallback final: respuestas estructuradas sin LLM)*

---

## 🛠️ Desarrollo local

```bash
# Clonar
git clone https://github.com/VasquezMaldonadoSebastian/sies-dashboard.git
cd sies-dashboard

# Dependencias
pip install -r requirements.txt

# Variables de entorno
export OPENCODE_API_KEY="sk-..."

# Ejecutar
streamlit run app.py
```

### Procesar nuevos PDFs
```bash
# 1. Convertir PDF a markdown con Docling
python extractor_v2.py --pdf ruta/informe.pdf

# 2. Reconstruir grafo
python grafo_conocimiento.py
```

---

## 🗂️ Estructura del proyecto

```
├── app.py                     ← Streamlit app
├── sies_engine.py             ← Orquestador (chat + grafo + API)
├── grafo_conocimiento.py      ← Grafo de conocimiento
├── analista.py                ← Respuestas estructuradas (fallback)
├── normalizar_entidades.py    ← Aliases (UCT, DUOC, etc.)
├── extractor_v2.py            ← Pipeline extracción PDF→grafo
│
├── grafo/
│   ├── grafo_sies.json        ← Grafo serializado (241 KB)
│   └── extracciones/          ← JSONs por informe
│
├── dashboard_data.json        ← KPIs estáticos
├── search_index.json          ← Índice TF-IDF (29 docs)
├── glue_tfidf_only.py         ← Respaldo del motor anterior
│
├── chromadb/                  ← Grafo pyvis HTML
├── wiki-sies/                 ← Wiki Obsidian
├── lib/                       ← vis.js
└── .streamlit/config.toml     ← Tema
```

---

## 📄 Fuentes

- [Portal SIES - mifuturo.cl](https://www.mifuturo.cl/sies/)
- [Bases de datos de matriculados](https://www.mifuturo.cl/bases-de-datos-de-matriculados/)
- Informes: Matrícula, Brechas de Género, Titulación, Retención (2019–2025)

---

## 📎 Licencia

Datos públicos del Estado de Chile. Consulta términos en [mifuturo.cl](https://www.mifuturo.cl).

> *"FUENTE: www.mifuturo.cl, de Mineduc."*
