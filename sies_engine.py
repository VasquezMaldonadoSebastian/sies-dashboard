#!/usr/bin/env python3
"""
sies_engine.py — Orquestador Unificado SIES v3
===========================================
Unifica grafo de conocimiento (506 hechos, 89 entidades) + DuckDB +
OpenRouter API / OpenCode API para responder preguntas en lenguaje natural
sobre educación superior chilena.

Modos de respuesta:
  - 'numerico': DuckDB o datos estáticos, con síntesis NL
  - 'semantico': Grafo de conocimiento, con síntesis NL
  - 'mixto': Grafo + DuckDB + síntesis NL
  - 'guiado': No entendió → muestra opciones
"""

import json
import os
import re
import traceback
from pathlib import Path
from typing import Optional

# ── OpenAI-compatible SDK ──────────────────────────────────────────────
try:
    from openai import OpenAI, APIError, RateLimitError, APITimeoutError
except ImportError:
    OpenAI = None

# ── Módulos del proyecto ─────────────────────────────────────────────────
from grafo_conocimiento import GrafoConocimientoSIES

# ── Rutas ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
GRAFO_PATH = BASE / "grafo" / "grafo_sies.json"
DB_PATH = BASE / "mifuturo_sies.db"
STATIC_PATH = BASE / "dashboard_data.json"

# ── Clasificación de turnos ─────────────────────────────────────────────
SALUDO_REGEX = re.compile(
    r"\b(hola|buenas|buenos días|buenas tardes|buenas noches|hey|saludos|qué tal|que tal|buen día|buena tarde)\b",
    re.IGNORECASE,
)
CAPACIDADES_REGEX = re.compile(
    r"\b(qué puedes|que puedes|qué sabes|que sabes|qué haces|que haces|cómo funcionas|como funcionas|"
    r"para qué sirves|para que sirves|capacidades|quién eres|quien eres)\b",
    re.IGNORECASE,
)
SEGUIMIENTO_REGEX = re.compile(
    r"\b(y eso|y qué|y que|eso mismo|lo anterior|cuéntame|cuentame|explícame|explicame|"
    r"amplía|amplia|sobre eso|dime más|y también|además|y los|más sobre)\b|"
    r"^(y en |y para |y de |y la |y el |y las |y los )",
    re.IGNORECASE,
)
DESPEDIDA_REGEX = re.compile(
    r"\b(adios|adiós|chao|hasta luego|hasta pronto|nos vemos|bye|cuidate|cuídate|gracias|muchas gracias)\b",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN OpenCode API
# ═══════════════════════════════════════════════════════════════════════════

# Leer API key: env var → .env → st.secrets
_api_key = os.environ.get("OPENCODE_API_KEY", "")
if not _api_key:
    try:
        with open(BASE / ".env") as f:
            for line in f:
                if line.startswith("OPENCODE_API_KEY="):
                    _api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except (FileNotFoundError, IOError):
        pass
if not _api_key:
    try:
        import streamlit as st
        _api_key = st.secrets.get("OPENCODE_API_KEY", "")
    except Exception:
        pass

OPENCODE_API_KEY = _api_key
OPENCODE_BASE_URL = "https://opencode.ai/zen/v1"
OPENCODE_MODELS = [  # Modelos free — cadena de fallback
    "deepseek-v4-flash-free",
    "big-pickle",
    "mimo-v2.5-free",
]
OPENCODE_TIMEOUT = 30  # segundos por modelo

# ── System prompt para el analista ───────────────────────────────────────
SYSTEM_PROMPT = """Eres un analista experto en educación superior chilena, especializado en los datos del SIES (Servicio de Información de Educación Superior).

REGLAS:
1. Usa SOLO los datos que se te entregan en el contexto. NO inventes cifras.
2. Responde en español, claro y conversacional, como un experto hablando con un colega.
3. NO uses tablas markdown a menos que sean 3+ filas de datos comparativos.
4. Prefiere frases como "En 2025 hubo 1.455.639 estudiantes" sobre tablas.
5. Cuando tengas datos de MÚLTIPLES documentos, CRUZALOS en una respuesta integrada.
6. Cita las fuentes al final con un 📎 breve.
7. NUNCA incluyas raw text de documentos ni estructura interna.
8. Sé conciso: máximo 3-4 párrafos.
9. Si la pregunta anterior y la actual están relacionadas, úsalas para dar contexto."""

# ═══════════════════════════════════════════════════════════════════════════
# SÍNTESIS CON LLM
# ═══════════════════════════════════════════════════════════════════════════

def _sintetizar_con_api(datos_markdown: str, pregunta: str, historial: list = None) -> Optional[str]:
    """
    Intenta sintetizar una respuesta usando la cadena de modelos OpenCode free.
    Retorna None si todos los modelos fallan.
    """
    if OpenAI is None:
        return None
    if not OPENCODE_API_KEY:
        return None
    try:
        cliente = OpenAI(api_key=OPENCODE_API_KEY, base_url=OPENCODE_BASE_URL)
    except Exception:
        return None

    # Construir mensajes con historial
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if historial:
        for msg in historial[-4:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content[:1500]})

    user_prompt = (
        f"## DATOS DISPONIBLES\n\n"
        f"{datos_markdown}\n\n"
        f"## PREGUNTA DEL USUARIO\n\n{pregunta}\n\n"
        f"Responde en español conversacional, usando SOLO los datos entregados."
    )
    messages.append({"role": "user", "content": user_prompt})

    for modelo in OPENCODE_MODELS:
        try:
            resp = cliente.chat.completions.create(
                model=modelo,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
                timeout=OPENCODE_TIMEOUT,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except Exception as e:
            print(f"   ⚠️ {modelo}: {e}")
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
# GENERADOR DE LENGUAJE NATURAL (FALLBACK SIN LLM)
# ═══════════════════════════════════════════════════════════════════════════

def _formatear_como_texto_natural(datos: dict, pregunta: str) -> str:
    """
    Convierte datos estructurados en texto conversacional.
    Se usa cuando la API no está disponible.
    """
    modo = datos.get("modo", "general")
    partes = []

    if modo == "numerico":
        evo = datos.get("evolucion", [])
        if evo:
            ult = evo[-1]
            ant = evo[-2] if len(evo) > 1 else ult
            año = ult.get("año", "")
            total = ult.get("total", "")
            pct_m = ult.get("pct_mujeres", "")
            partes.append(f"En **{año}** había **{total:,}** estudiantes matriculados en educación superior en Chile.")
            if pct_m:
                partes.append(f"De ellos, **{pct_m:.1f}%** son mujeres.")
            if ant and ant.get("total"):
                crec = ((ult["total"] - ant["total"]) / ant["total"]) * 100
                if crec > 0:
                    partes.append(f"Esto representa un aumento del **{crec:.1f}%** respecto a {ant['año']}.")
                else:
                    partes.append(f"Esto es una disminución del **{abs(crec):.1f}%** respecto a {ant['año']}.")
            partes.append("\n📎 *Fuente: Base de datos SIES 2007–2025*")

    elif modo == "top_instituciones":
        insts = datos.get("instituciones", [])
        if insts:
            partes.append(f"Las instituciones con mayor matrícula son:")
            for i, inst in enumerate(insts[:5], 1):
                nombre = inst.get("nombre", "")
                total = inst.get("total", 0)
                partes.append(f"  {i}. **{nombre}** — {total:,} estudiantes")
            partes.append("\n📎 *Fuente: Base de datos SIES*")

    elif modo == "entidad":
        nombre = datos.get("nombre", "")
        tipo = datos.get("tipo", "")
        hechos = datos.get("hechos", [])
        docs = datos.get("documentos", 0)

        icono = {"institucion": "🏫", "region": "📍", "concepto": "📊"}.get(tipo, "🏷️")
        partes.append(f"{icono} **{nombre}**")

        if hechos:
            for h in hechos[:4]:
                valor = h.get("valor", "")
                año = h.get("año", "")
                ctx = h.get("contexto", "")
                linea = f"  • {h.get('entidad', '')}: **{valor}**"
                if año:
                    linea += f" ({año})"
                if ctx:
                    linea += f" — {ctx[:80]}"
                partes.append(linea)

        if docs:
            partes.append(f"\n📄 Información extraída de {docs} documentos oficiales del SIES.")
        partes.append("\n📎 *Fuente: Informes SIES procesados*")

    elif modo == "evolucion":
        evo = datos.get("evolucion", [])
        if evo:
            primero = evo[0]
            ultimo = evo[-1]
            crecimiento = ((ultimo["total"] - primero["total"]) / primero["total"]) * 100
            partes.append(
                f"La matrícula en educación superior pasó de **{primero['total']:,}** estudiantes "
                f"en **{primero['año']}** a **{ultimo['total']:,}** en **{ultimo['año']}**, "
                f"un crecimiento del **{crecimiento:.1f}%** en {len(evo)} años."
            )
            # Hitos
            pct_m_ini = primero.get("pct_mujeres", 0)
            pct_m_fin = ultimo.get("pct_mujeres", 0)
            if pct_m_ini and pct_m_fin:
                delta_m = pct_m_fin - pct_m_ini
                tendencia = "aumentado" if delta_m > 0 else "disminuido"
                partes.append(
                    f"La participación femenina ha {tendencia} de {pct_m_ini:.1f}% a {pct_m_fin:.1f}% "
                    f"en el mismo período."
                )
            partes.append("\n📎 *Fuente: Base de datos SIES 2007–2025*")

    else:
        partes.append("No encontré información específica para tu consulta.")
        partes.append("Puedes preguntar sobre matrícula, instituciones, titulación o retención.")

    return "\n".join(partes)


# ═══════════════════════════════════════════════════════════════════════════
# ORQUESTADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

class SIESEngine:
    """Orquestador unificado de consultas SIES."""

    def __init__(self):
        self.grafo = GrafoConocimientoSIES()
        self.grafo_cargado = self.grafo.cargar_desde_json(GRAFO_PATH)
        if self.grafo_cargado:
            r = self.grafo.resumen()
            print(f"📂 Grafo: {r['entidades']} entidades, {r['hechos_totales']} hechos, {r['documentos']} docs")
        else:
            print("⚠️ Grafo no encontrado — algunas consultas no funcionarán")

        self.db_disponible = DB_PATH.exists()
        self.modelos_api = [f"opencode:{m}" for m in OPENCODE_MODELS] if OPENCODE_API_KEY and OpenAI else []
        if self.modelos_api:
            print(f"🤖 API OpenCode activa: {', '.join(m.split(':')[1] for m in self.modelos_api)}")
        else:
            print("⚠️ Sin API key — usando solo generación de lenguaje natural (fallback)")

        # Cargar datos estáticos
        self.estaticos = {}
        if STATIC_PATH.exists():
            with open(STATIC_PATH, "r", encoding="utf-8") as f:
                self.estaticos = json.load(f)

    # ── Consulta principal ────────────────────────────────────────────────

    def consultar(self, pregunta: str, consulta_anterior: str = "", historial: list = None) -> dict:
        """Responde una pregunta en lenguaje natural."""
        pregunta_clean = pregunta.strip()
        if not pregunta_clean:
            return self._respuesta_saludo()

        # 1. Detectar intenciones conversacionales
        # Si es SOLO saludo (≤3 palabras o solo palabras de saludo), responder saludo
        # Si tiene "hola" + pregunta real, SEGUIR a clasificación
        if SALUDO_REGEX.search(pregunta_clean) and not SEGUIMIENTO_REGEX.search(pregunta_clean):
            solo_saludo = set(pregunta_clean.lower().split()) - {"hola", "buenas", "hey", "saludos", "buenos", "buen", "día", "dias", "tardes", "noches", "qué", "tal", "que"}
            if len(pregunta_clean.split()) <= 3 or len(solo_saludo) <= 1:
                return self._respuesta_saludo()
        if DESPEDIDA_REGEX.search(pregunta_clean):
            return self._respuesta_despedida()
        if CAPACIDADES_REGEX.search(pregunta_clean):
            return self._respuesta_saludo()

        # 2. Resolver follow-ups
        if SEGUIMIENTO_REGEX.search(pregunta_clean) and consulta_anterior:
            pregunta_resuelta = f"{consulta_anterior} — {pregunta_clean}"
            print(f"🔗 Follow-up: {pregunta_resuelta[:80]}")
        else:
            pregunta_resuelta = pregunta_clean

        # 3. Clasificar y responder
        intencion = self._clasificar_intencion(pregunta_resuelta)
        print(f"🔍 Intención: {intencion}")

        if intencion == "numerico":
            return self._responder_numerico(pregunta_resuelta, historial=historial)
        elif intencion == "semantico":
            return self._responder_semantico(pregunta_resuelta, historial=historial)
        elif intencion == "mixto":
            return self._responder_mixto(pregunta_resuelta, historial=historial)
        else:
            return self._respuesta_guiada(pregunta_clean)

    # ── Clasificador de intención ─────────────────────────────────────────

    def _clasificar_intencion(self, pregunta: str) -> str:
        p = pregunta.lower().strip()

        patrones_numericos = [
            r"\bcuántos?\b", r"\bcuántas?\b", r"\btotal\b", r"\bporcentaje\b",
            r"\bevolución\b", r"\bevolucion\b", r"\bcrecimient[oó]\b",
            r"\bmujeres\b", r"\bhombres\b", r"\bregión\b", r"\bregion\b",
            r"\binstitución\b", r"\binstitucion\b", r"\bestudiantes\b",
            r"\bmatrícula\b", r"\bmatricula\b", r"\btitulación\b",
            r"\btitulacion\b", r"\bretención\b", r"\bretencion\b",
            r"\b\d{4}\b",
        ]
        es_numerico = any(re.search(pat, p) for pat in patrones_numericos)

        patrones_semanticos = [
            r"\bqu[eé]\b.*\binform[eo]\b",
            r"\bd[ií]ce\b", r"\bdicen\b",
            r"\bsobre\b", r"\bacerca\b",
            r"\bsabemos\b", r"\bconoces?\b",
            r"\brelación\b", r"\brelacion\b",
            r"\bcompar[aeo]\b",
        ]
        es_semantico = any(re.search(pat, p) for pat in patrones_semanticos)
        if self.grafo_cargado:
            entidades_encontradas = self._buscar_entidades(p)
            if entidades_encontradas:
                es_semantico = True

        if es_numerico and es_semantico:
            return "mixto"
        elif es_numerico:
            return "numerico"
        elif es_semantico:
            return "semantico"
        else:
            tokens = [t for t in p.split() if len(t) > 3]
            if len(tokens) >= 3:
                return "semantico"
            return "guiado"

    # ── Buscar entidades ──────────────────────────────────────────────────

    def _buscar_entidades(self, pregunta: str) -> list:
        if not self.grafo_cargado:
            return []

        stopwords = {
            "que", "las", "los", "del", "para", "con", "por", "como",
            "mas", "pero", "esta", "este", "entre", "todo", "esa", "eso",
            "son", "era", "han", "ser", "dos", "tres", "vez", "asi",
            "cual", "donde", "quien", "solo", "cada", "muy", "casi",
            "dice", "hace", "puede", "tiene", "sobre", "saber",
            "sus", "asi", "año", "ver", "dar", "fue", "hea", "sea",
        }
        palabras = [p for p in re.findall(r'\b\w{3,}\b', pregunta.lower()) if p not in stopwords]

        alias_encontradas = []
        substring_encontradas = []

        for palabra in palabras:
            resultados = self.grafo.buscar_con_aliases(palabra)
            for r in resultados:
                from normalizar_entidades import ALIAS_MAP
                es_match_fuerte = False
                if palabra in ALIAS_MAP:
                    es_match_fuerte = True
                nombre_normalizado = r["nombre"].lower()
                if palabra in nombre_normalizado.split():
                    es_match_fuerte = True

                ent_dup = r["nombre"] not in [e["nombre"] for e in alias_encontradas]
                if es_match_fuerte:
                    if ent_dup:
                        alias_encontradas.append(r)
                else:
                    if ent_dup and r["nombre"] not in [e["nombre"] for e in alias_encontradas]:
                        substring_encontradas.append(r)

        if alias_encontradas:
            entidades = alias_encontradas
        else:
            entidades = substring_encontradas

        entidades.sort(key=lambda x: x["n_hechos"], reverse=True)
        return entidades[:3]

    # ── Generar síntesis NL (API primero, fallback conversacional) ────────

    def _sintetizar_respuesta(self, datos_md: str, pregunta: str, historial: list = None) -> Optional[str]:
        """Intenta API, si falla retorna None (quien llama decide el fallback)."""
        return _sintetizar_con_api(datos_md, pregunta, historial)

    # ── Modo numérico ─────────────────────────────────────────────────────

    def _responder_numerico(self, pregunta: str, historial: list = None) -> dict:
        """Responde con datos numéricos, con síntesis NL."""
        # 1. Intentar DB
        db_data = self._consultar_db(pregunta)
        if db_data:
            # Intentar síntesis con API
            respuesta_api = self._sintetizar_respuesta(db_data, pregunta, historial)
            if respuesta_api:
                return {
                    "respuesta": respuesta_api,
                    "fuentes": ["Base de datos SIES (2007-2025)"],
                    "modo_usado": "numerico_api",
                    "sugerencias": [
                        "¿Cómo ha evolucionado la matrícula?",
                        "¿Cuáles son las instituciones con más estudiantes?",
                        "¿Cuál es la participación femenina?",
                    ],
                }
            # Fallback NL sin API
            datos_nl = self._datos_numerico_a_nl(db_data, pregunta)
            return {
                "respuesta": datos_nl,
                "fuentes": ["Base de datos SIES (2007-2025)"],
                "modo_usado": "numerico_nl",
                "sugerencias": [
                    "¿Cómo ha evolucionado la matrícula?",
                    "¿Cuáles son las instituciones con más estudiantes?",
                    "¿Cuál es la participación femenina?",
                ],
            }

        # 2. Fallback: datos estáticos
        return self._responder_desde_estaticos(pregunta, historial=historial)

    def _datos_numerico_a_nl(self, db_data: str, pregunta: str) -> str:
        """Convierte datos numéricos SQL en texto natural."""
        # Extraer año y total de la tabla markdown
        lineas = db_data.strip().split("\n")
        partes = []

        # Buscar la última fila de datos (después del encabezado)
        filas_datos = [l for l in lineas if l.startswith("| ") and not l.startswith("|:") and not l.startswith("| Año")]
        if not filas_datos:
            return db_data  # fallback a tabla

        # Última fila
        ult = filas_datos[-1]
        cols = [c.strip() for c in ult.split("|")[1:-1]]

        if len(cols) >= 2:
            año = cols[0]
            total = cols[1]
            partes.append(f"En **{año}** hay **{total}** estudiantes matriculados en educación superior en Chile.")

            if len(cols) >= 4:
                pct_m = cols[3].replace("%", "")
                partes.append(f"Las mujeres representan el **{pct_m}%** de la matrícula.")

        # Crecimiento si hay al menos 2 filas
        if len(filas_datos) >= 2:
            ant = filas_datos[-2]
            ant_cols = [c.strip() for c in ant.split("|")[1:-1]]
            if len(ant_cols) >= 2 and len(cols) >= 2:
                try:
                    total_act = int(total.replace(",", ""))
                    total_ant = int(ant_cols[1].replace(",", ""))
                    delta = total_act - total_ant
                    if delta > 0:
                        partes.append(f"Son **{delta:,}** más que el año anterior, lo que muestra una tendencia al alza en el acceso a la educación superior.")
                    else:
                        partes.append(f"Son **{abs(delta):,}** menos que el año anterior.")
                except ValueError:
                    pass

        if not partes:
            return db_data

        partes.append("\n📎 *Fuente: Datos SIES — mifuturo.cl*")
        return "\n".join(partes)

    # ── Modo semántico ────────────────────────────────────────────────────

    def _responder_semantico(self, pregunta: str, historial: list = None) -> dict:
        if not self.grafo_cargado:
            return self._respuesta_error("grafo_no_disponible")

        entidades = self._buscar_entidades(pregunta)
        if not entidades:
            return self._respuesta_guiada(pregunta)

        datos_grafo = self._formatear_datos_grafo(entidades)

        # Intentar API
        respuesta_api = self._sintetizar_respuesta(datos_grafo, pregunta, historial)
        if respuesta_api:
            fuentes = self._extraer_fuentes(entidades)
            return {
                "respuesta": respuesta_api,
                "fuentes": fuentes,
                "modo_usado": "semantico_api",
                "sugerencias": self._generar_sugerencias(entidades),
            }

        # Fallback NL sin API
        return self._responder_semantico_nl(entidades)

    def _responder_semantico_nl(self, entidades: list) -> dict:
        """Respuesta semántica en lenguaje natural, sin LLM."""
        if not entidades:
            return self._respuesta_guiada("")

        fuentes = set()
        ent_principal = entidades[0]
        data = self.grafo.query_entidad(ent_principal["nombre"])
        if not data.get("encontrada"):
            return self._respuesta_guiada("")

        nombre = ent_principal["nombre"]
        tipo = ent_principal["tipo"]
        partes = []

        icono = {"institucion": "🏫", "region": "📍", "concepto": "📊"}.get(tipo, "🏷️")
        partes.append(f"{icono} **{nombre}**")

        for ent_nombre, info in data["entidades"].items():
            n_docs = len(info["documentos"])
            hechos_num = [h for h in info.get("hechos", []) if isinstance(h.get("valor"), (int, float))]
            hechos_cuali = [h for h in info.get("hechos", []) if not isinstance(h.get("valor"), (int, float))]

            if hechos_num:
                # Tomar los más relevantes (ordenados por año descendente)
                hechos_num.sort(key=lambda x: str(x.get("año", "")), reverse=True)
                for h in hechos_num[:5]:
                    valor = f"{h['valor']:,.0f}" if isinstance(h['valor'], float) else str(h['valor'])
                    año = f" ({h['año']})" if h.get("año") else ""
                    ctx = h.get("contexto", "")[:80]
                    linea = f"  • {h.get('entidad', '')}: **{valor}**{año}"
                    if ctx:
                        linea += f" — {ctx}"
                    partes.append(linea)

            if hechos_cuali:
                for h in hechos_cuali[:2]:
                    ctx = h.get("contexto", h.get("afirmacion", ""))[:120]
                    if ctx:
                        partes.append(f"  💡 {ctx}")

            if n_docs:
                partes.append(f"\n📄 Información presente en {n_docs} informes oficiales del SIES.")

            for doc in info.get("documentos", [])[:3]:
                archivo = doc.get("archivo", "")
                if archivo:
                    fuentes.add(archivo.replace("Informe_", "").replace("_SIES.md", "").replace("_.md", ""))

        if fuentes:
            partes.append(f"\n📎 *Fuentes: {', '.join(sorted(fuentes)[:3])}*")

        return {
            "respuesta": "\n".join(partes),
            "fuentes": list(fuentes),
            "modo_usado": "semantico_nl",
            "sugerencias": self._generar_sugerencias(entidades),
        }

    # ── Modo mixto ────────────────────────────────────────────────────────

    def _responder_mixto(self, pregunta: str, historial: list = None) -> dict:
        datos_partes = []

        entidades = self._buscar_entidades(pregunta)
        if entidades:
            datos_partes.append(self._formatear_datos_grafo(entidades[:2]))

        db_data = self._consultar_db(pregunta)
        if db_data:
            datos_partes.append(f"### 📊 Datos numéricos\n\n{db_data}")

        if not datos_partes:
            return self._respuesta_guiada(pregunta)

        datos_combinados = "\n\n".join(datos_partes)

        respuesta_api = self._sintetizar_respuesta(datos_combinados, pregunta, historial)
        if respuesta_api:
            fuentes = self._extraer_fuentes(entidades) if entidades else []
            return {
                "respuesta": respuesta_api,
                "fuentes": fuentes,
                "modo_usado": "mixto_api",
                "sugerencias": self._generar_sugerencias(entidades) if entidades else [],
            }

        # Fallback NL: armar respuesta combinada
        respuesta_partes = []

        # Si hay entidades, formatear NL
        if entidades:
            nl_resp = self._responder_semantico_nl(entidades)
            respuesta_partes.append(nl_resp["respuesta"])

        # Si hay datos DB, formatear NL
        if db_data:
            nl_db = self._datos_numerico_a_nl(db_data, pregunta)
            if nl_db:
                respuesta_partes.append(nl_db)

        respuesta_final = "\n\n".join(respuesta_partes) if respuesta_partes else datos_combinados

        return {
            "respuesta": respuesta_final,
            "fuentes": [],
            "modo_usado": "mixto_nl",
            "sugerencias": [],
        }

    # ── Modo guiado ───────────────────────────────────────────────────────

    def _respuesta_saludo(self) -> dict:
        return {
            "respuesta": (
                "¡Hola! 😊 Soy tu **Analista SIES**. Puedo consultar **506 datos** extraídos de **5 informes** oficiales del SIES.\n\n"
                "📊 **Matrícula** — totales, evolución, por región\n"
                "👤 **Brechas de Género** — participación femenina\n"
                "🎓 **Titulación** — titulados por año\n"
                "📈 **Retención** — permanencia 1er año\n\n"
                "💡 *Prueba preguntando: \"¿Cuántos estudiantes en 2025?\" o \"¿Qué sabemos de la UCT?\"*"
            ),
            "fuentes": [],
            "modo_usado": "saludo",
            "sugerencias": [
                "¿Cuántos estudiantes en 2025?",
                "¿Qué sabemos de la UCT?",
                "¿Cómo ha evolucionado la matrícula?",
                "¿Qué instituciones tienen más estudiantes?",
            ],
        }

    def _respuesta_despedida(self) -> dict:
        return {
            "respuesta": "¡De nada! 😊 Si necesitas algo más sobre educación superior chilena, aquí estaré. ¡Que tengas un excelente día!",
            "fuentes": [],
            "modo_usado": "despedida",
            "sugerencias": [],
        }

    def _respuesta_guiada(self, pregunta: str = "") -> dict:
        if pregunta and len(pregunta) > 3:
            intro = f"No encontré información específica para **\"{pregunta[:80]}\"**. Pero esto es lo que puedo consultar:\n\n"
        else:
            intro = ""

        return {
            "respuesta": (
                f"{intro}"
                "📊 **Matrícula** — evolución, totales, por región, por tipo de IES\n"
                "👤 **Brechas de Género** — participación femenina, % por área\n"
                "🎓 **Titulación** — totales, % mujeres\n"
                "📈 **Retención** — tasas de permanencia\n\n"
                "💡 **Prueba con preguntas como:**\n"
                "• \"¿Cuántos estudiantes había en 2025?\"\n"
                "• \"¿Qué sabemos de la UCT?\"\n"
                "• \"¿Cómo ha evolucionado la matrícula?\"\n"
                "• \"¿Qué instituciones tienen más estudiantes?\""
            ),
            "fuentes": [],
            "modo_usado": "guiado",
            "sugerencias": [
                "¿Cuántos estudiantes había en 2025?",
                "¿Qué sabemos de la UCT?",
                "¿Cómo ha evolucionado la matrícula?",
                "¿Qué instituciones tienen más estudiantes?",
            ],
        }

    def _respuesta_error(self, codigo: str) -> dict:
        return {
            "respuesta": "⚠️ El grafo de conocimiento no está disponible. Algunas consultas pueden no funcionar.",
            "fuentes": [],
            "modo_usado": "error",
            "sugerencias": [],
        }

    # ── Consulta DB ──────────────────────────────────────────────────────

    def _consultar_db(self, pregunta: str) -> Optional[str]:
        """Retorna datos en markdown desde DuckDB o SQLite."""
        if not self.db_disponible:
            return None
        try:
            import duckdb
            con = duckdb.connect(":memory:")
            con.execute("INSTALL sqlite; LOAD sqlite;")
            con.execute(f"ATTACH '{DB_PATH}' AS sies (TYPE SQLITE)")

            p = pregunta.lower()
            años = [int(m) for m in re.findall(r'\b(20[0-2]\d)\b', pregunta) if 2007 <= int(m) <= 2025]

            # Vista evolucion
            try:
                con.execute("""
                    CREATE OR REPLACE VIEW evolucion AS
                    SELECT CAST(REPLACE(AÑO::VARCHAR, 'MAT_', '') AS INTEGER) AS año,
                           CAST(NULLIF("TOTAL MATRÍCULA"::VARCHAR, '') AS BIGINT) AS total,
                           CAST(NULLIF("TOTAL MATRÍCULA MUJERES"::VARCHAR, '') AS BIGINT) AS mujeres,
                           CAST(NULLIF("TOTAL MATRÍCULA PRIMER AÑO"::VARCHAR, '') AS BIGINT) AS primer_año
                    FROM sies.matricula
                    WHERE AÑO IS NOT NULL
                      AND CAST(NULLIF("TOTAL MATRÍCULA"::VARCHAR, '') AS BIGINT) IS NOT NULL
                """)
            except Exception as e:
                print(f"⚠️ Error vista: {e}")
                return None

            # Evolución histórica
            if any(w in p for w in ["evolucion", "crecimiento", "histórica", "serie"]):
                try:
                    rows = con.execute("""
                        SELECT año, SUM(total) AS total,
                               ROUND(SUM(mujeres)*100.0/SUM(total), 1) AS pct_mujeres,
                               ROUND((SUM(total)-LAG(SUM(total)) OVER(ORDER BY año))*100.0
                                     /LAG(SUM(total)) OVER(ORDER BY año), 2) AS crecimiento
                        FROM evolucion GROUP BY año ORDER BY año
                    """).fetchall()
                    if rows:
                        lines = ["## 📈 Evolución Matrícula 2007–2025\n", "| Año | Total | % Mujeres | Crecimiento |", "|:---:|------:|:---------:|:-----------:|"]
                        for r in rows:
                            crec = f"{r[3]:+.2f}%" if r[3] else "—"
                            lines.append(f"| {r[0]} | {r[1]:,} | {r[2]:.1f}% | {crec} |")
                        return "\n".join(lines)
                except Exception as e:
                    print(f"⚠️ Error evolucion: {e}")

            # Top instituciones
            if any(w in p for w in ["institución", "institucion", "universidad", "top", "mayores"]):
                try:
                    año_filtro = f"m.AÑO = 'MAT_{años[0]}'" if años else "m.AÑO = 'MAT_2025'"
                    rows = con.execute(f"""
                        SELECT m."NOMBRE INSTITUCIÓN" AS inst,
                               SUM(CAST(NULLIF(m."TOTAL MATRÍCULA"::VARCHAR, '') AS BIGINT)) AS tot
                        FROM sies.matricula m
                        WHERE {año_filtro}
                          AND m."NOMBRE INSTITUCIÓN" IS NOT NULL
                          AND m."TOTAL MATRÍCULA" IS NOT NULL
                        GROUP BY m."NOMBRE INSTITUCIÓN"
                        ORDER BY tot DESC LIMIT 10
                    """).fetchall()
                    if rows:
                        lines = ["## 🏫 Top 10 Instituciones\n", "| Institución | Matrícula |", "|-------------|----------:|"]
                        for r in rows:
                            inst = r[0].decode() if isinstance(r[0], bytes) else str(r[0])
                            lines.append(f"| {inst[:55]} | {int(r[1]):,} |")
                        return "\n".join(lines)
                except Exception as e:
                    print(f"⚠️ Error inst: {e}")

            # Consulta general
            try:
                if años:
                    rows = con.execute(f"""
                        SELECT año, SUM(total) AS total, SUM(mujeres) AS mujeres,
                               ROUND(SUM(mujeres)*100.0/SUM(total), 1) AS pct_mujeres
                        FROM evolucion WHERE año IN ({','.join(map(str, años))})
                        GROUP BY año ORDER BY año
                    """).fetchall()
                else:
                    rows = con.execute("""
                        SELECT año, SUM(total) AS total, SUM(mujeres) AS mujeres,
                               ROUND(SUM(mujeres)*100.0/SUM(total), 1) AS pct_mujeres
                        FROM evolucion GROUP BY año ORDER BY año DESC LIMIT 1
                    """).fetchall()

                if rows:
                    lines = ["| Año | Total | Mujeres | % Mujeres |", "|:---:|------:|--------:|:---------:|"]
                    for r in rows:
                        total_v = int(r[1]) if r[1] is not None else 0
                        mujeres_v = int(r[2]) if r[2] is not None else 0
                        pct_v = float(r[3]) if r[3] is not None else 0.0
                        lines.append(f"| {r[0]} | {total_v:,} | {mujeres_v:,} | {pct_v:.1f}% |")
                    return "\n".join(lines)
            except Exception as e:
                print(f"⚠️ Error general: {e}")

        except Exception as e:
            print(f"⚠️ DB error: {e}")
        return None

    # ── Estáticos ─────────────────────────────────────────────────────────

    def _responder_desde_estaticos(self, pregunta: str, historial: list = None) -> dict:
        """Respuesta desde datos estáticos, con síntesis NL."""
        p = pregunta.lower()
        evo = self.estaticos.get("matricula_evolucion", [])

        if not evo:
            return self._respuesta_guiada(pregunta)

        ult = evo[-1]
        ant = evo[-2] if len(evo) > 1 else ult
        crec = f"+{((ult['total_millones']-ant['total_millones'])/ant['total_millones']*100):.1f}%" if ant['total_millones'] else "—"

        # Datos para NL
        datos_nl = {
            "modo": "numerico",
            "evolucion": [{"año": e["año"], "total": int(e["total_millones"] * 1000000), "pct_mujeres": e["pct_mujeres"]} for e in evo[-5:]],
        }
        respuesta_nl = _formatear_como_texto_natural(datos_nl, pregunta)

        return {
            "respuesta": respuesta_nl,
            "fuentes": ["Datos precalculados SIES"],
            "modo_usado": "numerico_nl",
            "sugerencias": [
                "¿Cómo ha evolucionado la matrícula desde 2007?",
                "¿Cuál es la participación femenina en 2025?",
                "¿Qué instituciones tienen más estudiantes?",
            ],
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    def _formatear_datos_grafo(self, entidades: list) -> str:
        partes = []
        for ent in entidades[:2]:
            data = self.grafo.query_entidad(ent["nombre"])
            if not data.get("encontrada"):
                continue
            for nombre_ent, info in data["entidades"].items():
                partes.append(f"**{nombre_ent}** ({info['tipo']})\n")
                if info["documentos"]:
                    docs = [f"- {d['archivo'][:40]} ({d.get('año', '')})" for d in info["documentos"][:3]]
                    partes.append("Documentos:\n" + "\n".join(docs) + "\n")
                num_hechos = [h for h in info["hechos"] if isinstance(h.get("valor"), (int, float))]
                if num_hechos:
                    partes.append("Datos:\n")
                    for h in num_hechos[:8]:
                        valor = f"{h['valor']:,.0f}" if isinstance(h['valor'], float) else str(h['valor'])
                        año = f"({h['año']})" if h.get("año") else ""
                        ctx = f" — {h['contexto'][:80]}" if h.get("contexto") else ""
                        partes.append(f"- {h['entidad']}: {valor}{año}{ctx}\n")
                cualitativos = [h for h in info["hechos"] if not isinstance(h.get("valor"), (int, float))]
                if cualitativos:
                    partes.append("Hallazgos:\n")
                    for h in cualitativos[:3]:
                        ctx = h.get("contexto", h.get("afirmacion", ""))[:120]
                        if ctx:
                            partes.append(f"- {ctx}\n")
                if info["relaciones"]:
                    partes.append("Conexiones:\n")
                    for r in info["relaciones"][:4]:
                        partes.append(f"- {r['origen']} → {r['destino']}\n")
        return "\n".join(partes)[:4000]

    def _extraer_fuentes(self, entidades: list) -> list:
        fuentes = set()
        for ent in entidades[:3]:
            data = self.grafo.query_entidad(ent["nombre"])
            if data.get("encontrada"):
                for e_name, e_info in data["entidades"].items():
                    for doc in e_info.get("documentos", []):
                        fuentes.add(doc.get("archivo", ""))
        return sorted(fuentes)[:5]

    def _generar_sugerencias(self, entidades: list) -> list:
        if not entidades:
            return [
                "¿Cuántos estudiantes había en 2025?",
                "¿Qué instituciones tienen más estudiantes?",
                "¿Cómo ha evolucionado la matrícula?",
            ]
        nombre = entidades[0]["nombre"]
        alias_corto = {"Universidad Católica de Temuco": "la UCT"}
        ref = alias_corto.get(nombre, nombre)
        return [
            f"¿Qué sabemos de {ref}?",
            f"Datos numéricos de {ref}",
            "¿Cuántos estudiantes había en 2025?",
            "¿Qué instituciones tienen más estudiantes?",
        ]


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import sys
    engine = SIESEngine()
    if len(sys.argv) > 1:
        pregunta = " ".join(sys.argv[1:])
        print(f"\n❓ {pregunta}\n")
        r = engine.consultar(pregunta)
        print(r["respuesta"])
        if r.get("fuentes"):
            print(f"\n📎 {', '.join(r['fuentes'])}")
        print(f"\n🔧 Modo: {r['modo_usado']}")
    else:
        tests = [
            "¿Cuántos estudiantes hay en 2025?",
            "¿Qué sabemos de la UCT?",
            "sobre matricula",
            "¿Cómo ha evolucionado la matrícula?",
        ]
        for p in tests:
            print(f"\n{'='*60}")
            print(f"❓ {p}")
            print(f"{'='*60}")
            r = engine.consultar(p)
            print(r["respuesta"][:500])
            print(f"\n🔧 Modo: {r['modo_usado']}")


if __name__ == "__main__":
    main()
