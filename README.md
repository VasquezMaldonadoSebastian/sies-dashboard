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

## 🧪 Casos de prueba — Chat IA

### Consultas semánticas (grafo + OpenCode API)

| # | Consulta | Comportamiento esperado | Modo |
|:-:|----------|------------------------|:----:|
| 1 | `uct` | "Universidad Católica de Temuco" con datos de matrícula, retención, género. Sin mención a "Quechua". | `semantico_api` |
| 2 | `¿Qué sabemos de la UCT?` | Respuesta integrada: matrícula, retención, género, titulación. | `semantico_api` |
| 3 | `¿qué dice el informe de retención 2021?` | Hechos de retención + fuente: "Informe_Retencion_SIES_2021.md" | `semantico_api` |
| 4 | `quechua` | "Quechua — 1.654" (pueblos originarios, matrícula 2024) | `semantico_api` |
| 5 | `pueblos originarios` | Entidades de pueblos originarios con datos de matrícula | `semantico_api` |
| 6 | `duoc` | Respuesta guiada (DUOC no está en grafo, solo en DB) | `guiado` |

### Consultas numéricas (DuckDB / datos estáticos)

| # | Consulta | Comportamiento esperado | Modo |
|:-:|----------|------------------------|:----:|
| 7 | `¿Cuántos estudiantes en 2025?` | "1.455.639 estudiantes" + tabla año/total/mujeres/% | `numerico` |
| 8 | `¿Cómo ha evolucionado la matrícula?` | Tabla evolución 2007–2025 con % crecimiento | `numerico` |
| 9 | `¿Qué instituciones tienen más estudiantes?` | Top 10: DUOC UC (108.955), AIEP (81.655), UNAB (72.385)... | `numerico` |
| 10 | `matrícula 2024` | Total 2024: 1.386.099, mujeres: 738.799 (53,3%) | `numerico` |

### Consultas mixtas (grafo + DB + API)

| # | Consulta | Comportamiento esperado | Modo |
|:-:|----------|------------------------|:----:|
| 11 | `¿cómo le fue a la UCT en 2024?` | Datos UCT del grafo + totales nacionales de DB | `mixto_api` |
| 12 | `¿qué dice el informe de retención?` | Hechos del grafo + tasas numéricas de DB | `mixto_api` |

### Conversación y navegación

| # | Consulta | Comportamiento esperado | Modo |
|:-:|----------|------------------------|:----:|
| 13 | `hola` | Saludo con categorías y ejemplos | `saludo` |
| 14 | `¿qué sabes hacer?` | Muestra capacidades (matrícula, género, titulación, retención) | `saludo` |
| 15 | `gracias` | Despedida amistosa | `despedida` |
| 16 | `¿Qué puedes responder?` | Menú guiado con categorías + ejemplos | `guiado` |
| 17 | `sobre matricula` | Respuesta con datos numéricos (no volcado de wiki) | `numerico` o `mixto_api` |

### Follow-ups

| # | Consulta | Contexto previo | Comportamiento esperado |
|:-:|----------|:---------------:|------------------------|
| 18 | `¿y qué más?` | "¿Qué sabemos de la UCT?" | Sigue hablando de UCT |
| 19 | `¿y las mujeres?` | "¿cómo le fue a la UCT?" | Matrícula femenina de UCT |
| 20 | `cuéntame más` | "matrícula 2025" | Más detalle sobre matrícula |

### Anti-vómito (regresiones que nunca deben fallar)

| # | Consulta | ❌ **NUNCA debe:** |
|:-:|----------|-------------------|
| 21 | `sobre matricula` | Devolver el índice del wiki (wiki-sies/index.md) |
| 22 | `que sabemos de la uct` | Mencionar "Quechua" en la respuesta |
| 23 | `¿qué dice el informe 2024?` | Incluir bloques de código ``` o raw document text |
| 24 | (cualquier consulta) | Exponer estructura interna del wiki (wikilinks [[...]]) |

---

## 📎 Licencia

Datos públicos del Estado de Chile. Consulta términos en [mifuturo.cl](https://www.mifuturo.cl).

> *"FUENTE: www.mifuturo.cl, de Mineduc."*
