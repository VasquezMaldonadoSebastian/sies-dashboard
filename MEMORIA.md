# MEMORIA DEL PROYECTO — SIES Unificado

**Estado:** 🟢 En producción
**URL:** https://sies-dashboard.streamlit.app/
**Repo:** https://github.com/VasquezMaldonadoSebastian/sies-dashboard
**Rama:** `main`
**Stack:** DuckDB + Streamlit + OpenCode API + Grafo JSON + Ollama (local)

---

## 🏗️ Estructura del proyecto (Julio 2026)

```
sies/mifuturo-datos/            ← Raíz del proyecto (git: sies-dashboard)
├── app.py                      ← Streamlit: Chat IA + Grafo + Dashboard + Diagnóstico
├── sies_engine.py              ★ Orquestador unificado (reemplaza glue.py)
├── grafo_conocimiento.py       ← Grafo de conocimiento (89 entidades, 506 hechos)
├── analista.py                 ← Query engine: formateo estructurado (fallback sin LLM)
├── normalizar_entidades.py     ← Aliases y merge de entidades (UCT, DUOC, UChile...)
├── glue_tfidf_only.py          ← Respaldo del glue.py original (TF-IDF puro)
├── search_index.json           ← 29 docs wiki (limpio, sin meta)
├── dashboard_data.json         ← KPIs precalculados (5 KB, funciona sin DB)
├── requirements.txt            ← streamlit, pandas, plotly, scikit-learn, openai
│
├── grafo/
│   ├── grafo_sies.json         ← Grafo serializado (241 KB, incluido en git)
│   └── extracciones/           ← 5 JSONs de extracción (matrícula, género, titulación, retención)
│
├── chromadb/                   ← Pyvis HTML graph pre-generado
├── wiki-sies/                  ← Wiki Obsidian (conceptos + entidades)
├── raw/                        ← PDFs convertidos a markdown por Docling
├── lib/                        ← Dependencias vis.js
│
├── MEMORIA.md                  ← Este archivo
├── README.md                   ← Documentación del proyecto
└── .streamlit/config.toml      ← Tema terracota cálido
```

---

## 🔄 Pipeline de Extracción

```
PDF → Docling → Markdown → Chunking por secciones → Ollama 3B por chunk
→ Líneas ENTIDAD|tipo|valor|año|contexto
→ Normalización (sinónimos, merge, limpieza)
→ Grafo consolidado (grafo_sies.json)
→ 89 entidades, 506 hechos, 5 documentos, 4 categorías
```

### Documentos procesados (5)

| Archivo | Categoría | Hechos nums | Cualitativos |
|---------|:---------:|:-----------:|:------------:|
| Matrícula 2024 | matricula | 43 | 85 |
| Brechas Género 2024 | brechas-genero | 64 | 86 |
| Titulación 2023 | titulacion | 8 | 50 |
| Retención 2025 | retencion | 78 | 16 |
| Retención 2021 | retencion | 80 | 10 |
| **Total** | **4 cat.** | **273** | **247** |

---

## 🧠 Arquitectura del Chat IA (sies_engine.py)

### Flujo de consulta
```
Pregunta del usuario
    │
    ├─ ¿Saludo/despedida/capacidades? → Respuesta directa (sin grafo)
    │
    ├─ ¿Follow-up? → Resuelve con consulta_anterior
    │
    ├─ Clasificar intención: numérico / semántico / mixto / guiado
    │
    ├─ Modo semántico:
    │   → Buscar entidades (alias > substring, stopwords filtradas)
    │   → Recuperar hechos del grafo (max 10 hechos)
    │   → Llamar OpenCode API: deepseek → big-pickle → mimo-v2.5
    │   → Si API falla: formateo estructurado (analista.py)
    │
    ├─ Modo numérico:
    │   → DuckDB (si existe DB local) o dashboard_data.json
    │
    └─ Modo guiado:
       → Muestra categorías y ejemplos de preguntas
```

### Anti-vómito (reglas estrictas)
- **Prohibido:** exponer raw context de documentos, estructura interna del wiki, contenido de index.md
- **Límite:** máximo 10 hechos numéricos + 5 cualitativos por respuesta
- **Síntesis obligatoria:** toda respuesta pasa por formateo (LLM o estructurado)

### Modelos OpenCode API (cadena de fallback)
| Orden | Modelo | ID |
|:-----:|--------|:---:|
| 1° | DeepSeek V4 Flash Free | `deepseek-v4-flash-free` |
| 2° | Big Pickle | `big-pickle` |
| 3° | MiMo V2.5 Free | `mimo-v2.5-free` |
| — | Fallback final | Estructurado sin LLM |

**Endpoint:** `https://opencode.ai/zen/v1/chat/completions`
**API Key:** `st.secrets["OPENCODE_API_KEY"]`

---

## 📊 Dashboard

| Componente | Estado |
|------------|:------:|
| **URL** | https://sies-dashboard.streamlit.app/ |
| **Estilo** | Paleta cálida terracota (#B8552E), crema, ámbar |
| **Tipografía** | DM Sans + JetBrains Mono |
| **Navegación** | Navbar superior (Chat, Grafo, Dashboard, Diagnóstico) |
| **Sidebar** | ❌ Eliminado |
| **Chat IA** | ✅ Grafo + OpenCode API + DuckDB |
| **Grafo** | ✅ pyvis, 32 nodos/76 aristas |
| **Dashboard** | ✅ 4 tabs con datos estáticos (funciona sin DB en cloud) |

---

## 📝 Decisiones técnicas

### Por qué OpenCode API y no Ollama en Cloud
Ollama requiere GPU/CPU local. Streamlit Cloud no provee GPU. OpenCode API permite usar LLM desde cloud sin infraestructura extra.

### Por qué grafo + DuckDB y no solo RAG
El grafo estructura los datos extraídos de PDFs (506 hechos). DuckDB almacena la serie histórica (563 MB, 13 tablas). Juntos permiten responder tanto "¿qué dice el informe?" (grafo) como "¿cuántos estudiantes en 2025?" (DB).

### Por qué el grafo va en git (241 KB)
El grafo serializado es pequeño, no contiene datos sensibles, y permite que el chat funcione sin necesidad de ejecutar el pipeline de extracción. Se actualiza cuando se procesan nuevos PDFs.

### Por qué se respaldó glue.py como glue_tfidf_only.py
El glue.py original con TF-IDF puro fue reemplazado por sies_engine.py. Se mantiene como respaldo por si se necesita el enfoque anterior.

---

## ⚙️ Secrets de Streamlit Cloud

```toml
# .streamlit/secrets.toml (NO subir a git)
OPENCODE_API_KEY = "sk-..."
```

---

## 📋 Pendientes

- [ ] Extraer más documentos (titulación, oferta académica, docentes)
- [ ] Mejorar precisión del extractor 3B (entidades duplicadas)
- [ ] Agregar más aliases al normalizador
- [ ] Subir SQLite DB a GitHub Releases para descarga
- [ ] Evaluar si se requiere autenticación en el dashboard
- [ ] Agregar consultas DuckDB por institución + año + sexo

---

## 📅 Historial de cambios relevantes

| Fecha | Cambio |
|-------|--------|
| 2026-07-08 | **Unificación:** grafo + analista movidos a mifuturo-datos. Creación de sies_engine.py. Integración OpenCode API con 3 modelos. Fix stopwords + entity matching. Clasificación de turnos tipo agente-kimn. |

---

*Última actualización: 2026-07-08*
