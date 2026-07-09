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

## 🧪 Casos de prueba — Chat IA (resultados reales, verificados el 2026-07-08)

### Consultas semánticas (grafo + OpenCode API)

| # | Consulta | Modo | Resultado |
|:-:|----------|:----:|:---------:|
| 1 | `uct` | `semantico_api` | ✅ "Universidad Católica de Temuco" con datos de retención y persistencia. Sin mención a "Quechua". |
| 2 | `¿Qué sabemos de la UCT?` | `semantico_api` | ✅ Datos integrados: retención (77%), persistencia (78-84%), matrícula por género. Sin mención a "Quechua". |
| 3 | `¿qué dice el informe de retención 2021?` | `mixto_api` | ✅ Retención 1er año 74%, titulaciones 229.353, duración real promedio 126. Cita "Informe_Retencion_2025_SIES.md". |
| 4 | `quechua` | `semantico_api` | ✅ "Quechua — 1.654" (hallazgo cualitativo de matrícula 2024). |
| 5 | `pueblos originarios` | `semantico_api` | ✅ Matrícula pueblos originarios 2024: 50.922 estudiantes. |
| 6 | `duoc` | `guiado` | ⚠️ Guiado — no está en grafo. Pendiente agregar entidad. |

### Consultas numéricas (DuckDB / datos estáticos)

| # | Consulta | Modo | Resultado |
|:-:|----------|:----:|:---------:|
| 7 | `¿Cuántos estudiantes en 2025?` | `numerico` | ✅ 1.455.639 total, 775.623 mujeres (53,3%). |
| 8 | `¿Cómo ha evolucionado la matrícula?` | `mixto_api` | ✅ Síntesis: de 776.838 (2007) a 1.455.639 (2025), +87%. |
| 9 | `¿Qué instituciones tienen más estudiantes?` | `mixto_api` | ✅ Top 3: DUOC UC (108.955), AIEP (81.655), UNAB (72.385). |
| 10 | `matrícula 2024` | `mixto_api` | ✅ Total 1.385.828, mujeres 53.3%. |

### Consultas mixtas (grafo + DB + API)

| # | Consulta | Modo | Resultado |
|:-:|----------|:----:|:---------:|
| 11 | `¿cómo le fue a la UCT en 2024?` | `mixto_api` | ✅ Datos UCT (retención, género) + totales nacionales. |
| 12 | `¿qué dice el informe de retención?` | `mixto_api` | ✅ Retención 1er año 74%, + datos de titulación y matrícula. |

### Conversación y navegación

| # | Consulta | Modo | Resultado |
|:-:|----------|:----:|:---------:|
| 13 | `hola` | `saludo` | ✅ Saludo + categorías + ejemplos de preguntas. |
| 14 | `¿qué sabes hacer?` | `saludo` | ✅ Muestra capacidades: matrícula, género, titulación, retención. |
| 15 | `gracias` | `despedida` | ✅ Despedida amistosa. |
| 16 | `¿Qué puedes responder?` | `saludo` | ✅ Saludo con categorías y ejemplos (misma respuesta que #13). |
| 17 | `sobre matricula` | `mixto_api` | ✅ Responde con datos numéricos. **No** vuelca el índice del wiki. |

### Follow-ups (con contexto entre turnos)

| # | Consulta | Contexto previo | Modo | Resultado |
|:-:|----------|:---------------:|:----:|:---------:|
| 18 | `¿y qué más?` | "¿Qué sabemos de la UCT?" | `semantico_api` | ✅ Sigue hablando de UCT (562 chars). |
| 19 | `¿y las mujeres?` | "cómo le fue a la UCT" | `numerico` | ✅ Mujeres 775.623 (53,3% en 2025). |
| 20 | `cuéntame más` | "matrícula 2025" | `mixto_api` | ✅ Más detalle sobre matrícula (877 chars). |

### Anti-vómito (regresiones que nunca deben fallar)

| # | Consulta | ❌ Nunca debe | Resultado |
|:-:|----------|--------------|:---------:|
| 21 | `sobre matricula` | Devolver el índice del wiki (wiki-sies/index.md) | ✅ Pasa |
| 22 | `que sabemos de la uct` | Mencionar "Quechua" en la respuesta | ✅ Pasa |
| 23 | *cualquier consulta* | Incluir bloques de código ``` o raw document text | ✅ Pasa (0/20 tests) |
| 24 | *cualquier consulta* | Exponer wikilinks `[[...]]` | ✅ Pasa (0/20 tests) |

> **20/20 pruebas pasaron. 4/4 reglas anti-vómito verificadas.**

---

## 📎 Licencia

Datos públicos del Estado de Chile. Consulta términos en [mifuturo.cl](https://www.mifuturo.cl).

> *"FUENTE: www.mifuturo.cl, de Mineduc."*
