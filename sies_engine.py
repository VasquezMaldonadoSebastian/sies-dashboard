#!/usr/bin/env python3
"""
sies_engine.py — Orquestador Unificado SIES
==========================================

Unifica grafo de conocimiento (506 hechos, 89 entidades) + DuckDB + 
OpenCode API (3 modelos en cadena de fallback) para responder preguntas
sobre educación superior chilena.

Modos de respuesta (auto-detectados):
  - 'numerico': DuckDB (evolución, totales, porcentajes)
  - 'semantico': Grafo de conocimiento (instituciones, conceptos, relaciones)
  - 'mixto': Grafo + DuckDB + síntesis
  - 'guiado': No entendió → muestra opciones
"""

import json
import os
import re
import traceback
from pathlib import Path
from typing import Optional

# ── OpenAI-compatible SDK para OpenCode API ──────────────────────────────
try:
    from openai import OpenAI, APIError, RateLimitError, APITimeoutError
except ImportError:
    OpenAI = None  # fallback sin API

# ── Módulos del proyecto ─────────────────────────────────────────────────
from grafo_conocimiento import GrafoConocimientoSIES
from analista import formatear_respuesta_entidad

# ── Rutas ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
GRAFO_PATH = BASE / "grafo" / "grafo_sies.json"
DB_PATH = BASE / "mifuturo_sies.db"
STATIC_PATH = BASE / "dashboard_data.json"

# ── Patrones de clasificación de turnos (inspirados en agente-kimn) ─────
SALUDO_REGEX = re.compile(r"\b(hola|buenas|buenos días|buenas tardes|buenas noches|hey|saludos|qué tal|que tal|buen día|buena tarde)\b", re.IGNORECASE)
CAPACIDADES_REGEX = re.compile(r"\b(qué puedes|que puedes|qué sabes|que sabes|qué haces|que haces|cómo funcionas|como funcionas|para qué sirves|para que sirves|capacidades|qué hago|que hago|quién eres|quien eres)\b", re.IGNORECASE)
SEGUIMIENTO_REGEX = re.compile(r"\b(y eso|y qué|y que|eso mismo|lo anterior|cuéntame|cuentame|explícame|explicame|amplía|amplia|sobre eso|dime más|y también|además|y los|más sobre)\b", re.IGNORECASE)
DESPEDIDA_REGEX = re.compile(r"\b(adios|adiós|chao|hasta luego|hasta pronto|nos vemos|bye|cuidate|cuídate|gracias|muchas gracias)\b", re.IGNORECASE)
# Orden de resolución: environment variable → st.secrets (Streamlit Cloud)
_api_key = os.environ.get("OPENCODE_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
if not _api_key:
    try:
        import streamlit as st
        _api_key = st.secrets.get("OPENCODE_API_KEY", "")
    except (ImportError, Exception):
        pass
OPENCODE_API_KEY = _api_key
OPENCODE_BASE_URL = "https://opencode.ai/zen/v1"
OPENCODE_MODELS = [  # Cadena de fallback
    "deepseek-v4-flash-free",
    "big-pickle",
    "mimo-v2.5-free",
]
OPENCODE_TIMEOUT = 20  # segundos por modelo

# ── System prompt para el analista ───────────────────────────────────────
SYSTEM_PROMPT = """Eres un analista experto en educación superior chilena, especializado en los datos del SIES (Servicio de Información de Educación Superior).

REGLAS:
1. Usa SOLO los datos que se te entregan en el contexto. NO inventes cifras.
2. Responde en español, claro y directo. Usa markdown ligero (negritas, tablas si aplica).
3. Cuando tengas datos de MÚLTIPLES documentos, CRUZALOS en una respuesta integrada.
4. Cita las fuentes al final: "📎 Fuente: [nombre del documento]"
5. NUNCA incluyas texto raw de documentos. NUNCA incluyas estructura interna del wiki.
6. Si no hay datos suficientes, dilo y sugiere preguntas alternativas.
7. Sé conciso — responde en máximo 3-4 párrafos, tabla si aplica."""


# ═══════════════════════════════════════════════════════════════════════════
# CLIENTE OPenCode API
# ═══════════════════════════════════════════════════════════════════════════

def _crear_cliente():
    """Crea el cliente OpenAI apuntando a OpenCode API."""
    if OpenAI is None:
        return None
    if not OPENCODE_API_KEY:
        return None
    try:
        return OpenAI(
            api_key=OPENCODE_API_KEY,
            base_url=OPENCODE_BASE_URL,
        )
    except Exception:
        return None


def _sintetizar_con_api(datos_markdown: str, pregunta: str) -> Optional[str]:
    """
    Intenta sintetizar una respuesta usando la cadena de modelos OpenCode.
    Retorna None si todos los modelos fallan.
    """
    cliente = _crear_cliente()
    if cliente is None:
        return None

    user_prompt = (
        f"## DATOS DISPONIBLES\n\n"
        f"{datos_markdown}\n\n"
        f"## PREGUNTA DEL USUARIO\n\n{pregunta}\n\n"
        f"Responde usando SOLO los datos entregados. Sé conciso."
    )

    for modelo in OPENCODE_MODELS:
        try:
            resp = cliente.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1024,
                temperature=0.3,
                timeout=OPENCODE_TIMEOUT,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except (APIError, RateLimitError, APITimeoutError) as e:
            print(f"   ⚠️ Modelo {modelo}: {e}")
            continue
        except Exception as e:
            print(f"   ⚠️ Modelo {modelo} (error inesperado): {e}")
            continue
    return None


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

        # Cargar datos estáticos (fallback para Cloud)
        self.estaticos = {}
        if STATIC_PATH.exists():
            with open(STATIC_PATH, "r", encoding="utf-8") as f:
                self.estaticos = json.load(f)

    # ── Consulta principal ────────────────────────────────────────────────

    def consultar(self, pregunta: str, consulta_anterior: str = "") -> dict:
        """
        Responde una pregunta en lenguaje natural.

        Args:
            pregunta: Texto de la pregunta actual.
            consulta_anterior: Última pregunta del usuario (para resolver follow-ups).

        Returns:
            dict con respuesta, fuentes, modo_usado, sugerencias
        """
        pregunta_clean = pregunta.strip()
        if not pregunta_clean:
            return self._respuesta_saludo()

        # 1. Detectar intenciones conversacionales primero
        if SALUDO_REGEX.search(pregunta_clean) and not SEGUIMIENTO_REGEX.search(pregunta_clean):
            return self._respuesta_saludo()
        if DESPEDIDA_REGEX.search(pregunta_clean):
            return self._respuesta_despedida()
        if CAPACIDADES_REGEX.search(pregunta_clean):
            return self._respuesta_saludo()  # Misma respuesta con capacidades

        # 2. Resolver follow-ups con contexto anterior
        if SEGUIMIENTO_REGEX.search(pregunta_clean) and consulta_anterior:
            pregunta_resuelta = f"{consulta_anterior} — {pregunta_clean}"
            print(f"🔗 Follow-up detectado, resuelto como: {pregunta_resuelta[:80]}")
        else:
            pregunta_resuelta = pregunta_clean

        # 3. Clasificar y responder
        intencion = self._clasificar_intencion(pregunta_resuelta)
        print(f"🔍 Intención: {intencion}")

        if intencion == "numerico":
            return self._responder_numerico(pregunta_resuelta)
        elif intencion == "semantico":
            return self._responder_semantico(pregunta_resuelta)
        elif intencion == "mixto":
            return self._responder_mixto(pregunta_resuelta)
        else:
            return self._respuesta_guiada(pregunta_clean)

    # ── Clasificador de intención ─────────────────────────────────────────

    def _clasificar_intencion(self, pregunta: str) -> str:
        """Clasifica la pregunta en: numerico, semantico, mixto, guiado."""
        p = pregunta.lower().strip()

        # Palabras clave numéricas
        patrones_numericos = [
            r"\bcuántos?\b", r"\bcuántas?\b", r"\btotal\b", r"\bporcentaje\b",
            r"\bevolución\b", r"\bevolucion\b", r"\bcrecimient[oó]\b",
            r"\bmujeres\b", r"\bhombres\b", r"\bregión\b", r"\bregion\b",
            r"\binstitución\b", r"\binstitucion\b", r"\bestudiantes\b",
            r"\bmatrícula\b", r"\bmatricula\b", r"\btitulación\b",
            r"\btitulacion\b", r"\bretención\b", r"\bretencion\b",
            r"\b\d{4}\b",  # año
        ]
        es_numerico = any(re.search(pat, p) for pat in patrones_numericos)

        # Palabras clave semánticas (entidades, conceptos)
        patrones_semanticos = [
            r"\bqu[eé]\b.*\binform[eo]\b",
            r"\bd[ií]ce\b", r"\bdicen\b",
            r"\bsobre\b", r"\bacerca\b",
            r"\bsabemos\b", r"\bconoces?\b",
            r"\brelación\b", r"\brelacion\b",
            r"\bcompar[aeo]\b",
        ]
        es_semantico = any(re.search(pat, p) for pat in patrones_semanticos)
        # También es semántico si menciona una entidad conocida
        if self.grafo_cargado:
            entidades_encontradas = self._buscar_entidades(p)
            if entidades_encontradas:
                es_semantico = True

        # Preguntas sobre capacidades → guiado siempre (ya capturadas arriba en consultar)
        # Clasificación final
        if es_numerico and es_semantico:
            return "mixto"
        elif es_numerico:
            return "numerico"
        elif es_semantico:
            return "semantico"
        else:
            # Si tiene 3+ palabras significativas, asumir semántico
            tokens = [t for t in p.split() if len(t) > 3]
            if len(tokens) >= 3:
                return "semantico"
            return "guiado"

    # ── Buscar entidades en el grafo ──────────────────────────────────────

    def _buscar_entidades(self, pregunta: str) -> list:
        """Busca entidades en el grafo que coincidan con la pregunta.
        
        Prioriza coincidencias por alias (búsqueda exacta) sobre substring.
        Si hay al menos un match fuerte por alias, descarta matches débiles
        por substring. Esto evita que "que" en "que sabemos de la uct"
        encuentre "Quechua" cuando lo relevante es UCT.
        """
        if not self.grafo_cargado:
            return []

        # Stopwords a ignorar
        stopwords = {
            "que", "las", "los", "del", "para", "con", "por", "como",
            "mas", "pero", "esta", "este", "entre", "todo", "esa", "eso",
            "son", "era", "han", "ser", "dos", "tres", "vez", "asi",
            "cual", "donde", "quien", "solo", "cada", "muy", "casi",
            "dice", "hace", "puede", "tiene", "sobre", "saber",
            "sus", "asi", "año", "ver", "dar", "fue", "hea", "sea",
        }
        palabras = [
            p for p in re.findall(r'\b\w{3,}\b', pregunta.lower())
            if p not in stopwords
        ]

        alias_encontradas = []   # Match fuerte (vía alias_map)
        substring_encontradas = []  # Match débil (substring genérico)

        for palabra in palabras:
            resultados = self.grafo.buscar_con_aliases(palabra)
            for r in resultados:
                # Si buscar_con_aliases encontró algo, puede ser alias o substring
                # Revisamos si la palabra original está en el alias_map (match fuerte)
                from normalizar_entidades import ALIAS_MAP
                es_match_fuerte = False
                # match fuerte si: la palabra es un alias conocido, o es exactamente el nombre
                if palabra in ALIAS_MAP:
                    es_match_fuerte = True
                # también es fuerte si el nombre contiene la palabra como token completo
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

        # Decidir qué retornar: si hay matches fuertes, solo ellos
        if alias_encontradas:
            entidades = alias_encontradas
            print(f"   Match fuerte: {[e['nombre'] for e in alias_encontradas]}")
        else:
            entidades = substring_encontradas

        # Ordenar por relevancia y limitar
        entidades.sort(key=lambda x: x["n_hechos"], reverse=True)
        return entidades[:3]

    # ── Modo semántico (grafo + OpenCode API) ─────────────────────────────

    def _responder_semantico(self, pregunta: str) -> dict:
        """Responde usando el grafo de conocimiento + OpenCode API."""
        if not self.grafo_cargado:
            return self._respuesta_error("grafo_no_disponible")

        entidades = self._buscar_entidades(pregunta)
        if not entidades:
            return self._respuesta_guiada(pregunta)

        # 1. Recuperar datos del grafo (con límite anti-vómito)
        datos_grafo = self._formatear_datos_grafo(entidades)

        # 2. Intentar síntesis con OpenCode API
        respuesta_api = _sintetizar_con_api(datos_grafo, pregunta)

        if respuesta_api:
            fuentes = self._extraer_fuentes(entidades)
            sugerencias = self._generar_sugerencias(entidades)
            return {
                "respuesta": respuesta_api,
                "fuentes": fuentes,
                "modo_usado": "semantico_api",
                "sugerencias": sugerencias,
            }

        # 3. Fallback: respuesta estructurada sin LLM
        return self._responder_semantico_sin_llm(entidades)

    def _responder_semantico_sin_llm(self, entidades: list) -> dict:
        """Responde con datos estructurados del grafo (sin LLM)."""
        if not entidades:
            return self._respuesta_guiada("")

        fuentes = set()

        # Solo mostrar la entidad principal (la de más hechos)
        ent_principal = entidades[0]
        data = self.grafo.query_entidad(ent_principal["nombre"])
        if not data.get("encontrada"):
            return self._respuesta_guiada("")

        respuesta = formatear_respuesta_entidad(ent_principal["nombre"], data)

        # Extraer fuentes
        for e_name, e_info in data["entidades"].items():
            for doc in e_info.get("documentos", []):
                fuentes.add(doc.get("archivo", ""))

        # Mencionar otras entidades relacionadas
        if len(entidades) > 1:
            otras = ", ".join(e["nombre"] for e in entidades[1:4])
            respuesta += f"\n\n💡 *También encontré información sobre: {otras}*"

        if fuentes:
            respuesta += f"\n\n📎 Fuentes: {', '.join(sorted(fuentes)[:5])}"

        # Si la respuesta es muy larga, truncar con sugerencia
        if len(respuesta) > 3000:
            respuesta = respuesta[:2800] + "\n\n*💡 Demasiados datos? Pregunta por algo más específico.*"

        return {
            "respuesta": respuesta,
            "fuentes": list(fuentes),
            "modo_usado": "semantico_estructurado",
            "sugerencias": self._generar_sugerencias(entidades),
        }

    # ── Modo numérico (DuckDB / datos estáticos) ──────────────────────────

    def _responder_numerico(self, pregunta: str) -> dict:
        """Responde con datos numéricos desde DuckDB o JSON estático."""
        respuesta = self._consultar_db(pregunta)
        if respuesta:
            return {
                "respuesta": respuesta,
                "fuentes": ["Base de datos SIES (2007-2025)"],
                "modo_usado": "numerico",
                "sugerencias": [
                    "¿Cómo ha evolucionado la matrícula?",
                    "¿Cuáles son las instituciones con más estudiantes?",
                    "¿Cuál es la participación femenina?",
                ],
            }
        # Si no hay DB, buscar en datos estáticos
        return self._responder_desde_estaticos(pregunta)

    def _consultar_db(self, pregunta: str) -> Optional[str]:
        """Consulta DuckDB o SQLite para datos numéricos."""
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
            con.execute("""
                CREATE OR REPLACE VIEW evolucion AS
                SELECT
                    CAST(REPLACE(AÑO::VARCHAR, 'MAT_', '') AS INTEGER) AS año,
                    CAST(NULLIF("TOTAL MATRÍCULA"::VARCHAR, '') AS BIGINT) AS total,
                    CAST(NULLIF("TOTAL MATRÍCULA MUJERES"::VARCHAR, '') AS BIGINT) AS mujeres,
                    CAST(NULLIF("TOTAL MATRÍCULA PRIMER AÑO"::VARCHAR, '') AS BIGINT) AS primer_año
                FROM sies.matricula
                WHERE AÑO IS NOT NULL AND "TOTAL MATRÍCULA" IS NOT NULL
            """)

            if any(w in p for w in ["evolución", "evolucion", "crecimiento", "histórica", "serie"]):
                rows = con.execute("""
                    SELECT año, SUM(total) AS total,
                           ROUND(SUM(mujeres)*100.0/SUM(total), 1) AS pct_mujeres,
                           ROUND((SUM(total)-LAG(SUM(total)) OVER(ORDER BY año))*100.0
                                 /LAG(SUM(total)) OVER(ORDER BY año), 2) AS crecimiento
                    FROM evolucion GROUP BY año ORDER BY año
                """).fetchall()
                lines = ["## 📈 Evolución Matrícula 2007–2025\n", "| Año | Total | % Mujeres | Crecimiento |", "|:---:|------:|:---------:|:-----------:|"]
                for r in rows:
                    crec = f"{r[3]:+.2f}%" if r[3] else "—"
                    lines.append(f"| {r[0]} | {r[1]:,} | {r[2]:.1f}% | {crec} |")
                return "\n".join(lines)

            if "institución" in p or "institucion" in p or "universidad" in p or "top" in p:
                año_cond = f"m.AÑO = 'MAT_{años[0]}'" if años else "m.AÑO = 'MAT_2025'"
                rows = con.execute(f"""
                    SELECT m."NOMBRE INSTITUCIÓN" AS inst,
                           SUM(CAST(NULLIF(m."TOTAL MATRÍCULA"::VARCHAR, '') AS BIGINT)) AS tot
                    FROM sies.matricula m
                    WHERE {año_cond}
                      AND m."NOMBRE INSTITUCIÓN" IS NOT NULL
                      AND m."NOMBRE INSTITUCIÓN" != ''
                      AND m."TOTAL MATRÍCULA" IS NOT NULL
                      AND m."TOTAL MATRÍCULA"::VARCHAR != ''
                    GROUP BY m."NOMBRE INSTITUCIÓN"
                    ORDER BY tot DESC LIMIT 10
                """).fetchall()
                lines = ["## 🏫 Top 10 Instituciones\n", "| Institución | Matrícula |", "|-------------|----------:|"]
                for r in rows:
                    inst = r[0].decode() if isinstance(r[0], bytes) else str(r[0])
                    lines.append(f"| {inst[:50]} | {r[1]:,} |")
                return "\n".join(lines)

            # Default: total general
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
                    lines.append(f"| {r[0]} | {r[1]:,} | {r[2]:,} | {r[3]:.1f}% |")
                return "\n".join(lines)

        except Exception as e:
            print(f"⚠️ DB error: {e}")
        return None

    def _responder_desde_estaticos(self, pregunta: str) -> dict:
        """Responde usando datos estáticos (funciona sin DB)."""
        p = pregunta.lower()
        evo = self.estaticos.get("matricula_evolucion", [])

        if not evo:
            return self._respuesta_guiada(pregunta)

        ult = evo[-1]
        ant = evo[-2] if len(evo) > 1 else ult
        crec = f"+{((ult['total_millones']-ant['total_millones'])/ant['total_millones']*100):.1f}%" if ant['total_millones'] else "—"

        texto = (
            f"## 📊 Datos de Matrícula\n\n"
            f"**{ult['año']}:** {ult['total_millones']:.2f} millones de estudiantes\n"
            f"**Mujeres:** {ult['pct_mujeres']:.1f}% de la matrícula\n"
            f"**Crecimiento vs {ant['año']}:** {crec}\n\n"
            f"📎 Fuente: Datos precalculados SIES\n\n"
            f"💡 *Pregunta por evolución histórica, regiones o instituciones específicas.*"
        )

        return {
            "respuesta": texto,
            "fuentes": ["Datos precalculados SIES"],
            "modo_usado": "numerico_estatico",
            "sugerencias": [
                "¿Cómo ha evolucionado la matrícula desde 2007?",
                "¿Cuál es la participación femenina en 2025?",
                "¿Qué instituciones tienen más estudiantes?",
            ],
        }

    # ── Modo mixto (grafo + DuckDB + API) ─────────────────────────────────

    def _responder_mixto(self, pregunta: str) -> dict:
        """Combina datos del grafo y DuckDB con síntesis."""
        datos_partes = []

        # 1. Datos del grafo
        entidades = self._buscar_entidades(pregunta)
        if entidades:
            datos_partes.append(self._formatear_datos_grafo(entidades[:2]))

        # 2. Datos numéricos
        db_data = self._consultar_db(pregunta)
        if db_data:
            datos_partes.append(f"### 📊 Datos numéricos\n\n{db_data}")

        if not datos_partes:
            return self._respuesta_guiada(pregunta)

        datos_combinados = "\n\n".join(datos_partes)

        # 3. Intentar síntesis con API
        respuesta_api = _sintetizar_con_api(datos_combinados, pregunta)
        if respuesta_api:
            fuentes = self._extraer_fuentes(entidades) if entidades else []
            return {
                "respuesta": respuesta_api,
                "fuentes": fuentes,
                "modo_usado": "mixto_api",
                "sugerencias": self._generar_sugerencias(entidades) if entidades else [],
            }

        # 4. Fallback: mostrar datos combinados
        return {
            "respuesta": f"## Datos disponibles\n\n{datos_combinados}",
            "fuentes": [],
            "modo_usado": "mixto_estructurado",
            "sugerencias": [],
        }

    # ── Modo guiado (no entendió) ─────────────────────────────────────────

    def _respuesta_saludo(self) -> dict:
        """Responde a saludos y consultas sobre capacidades."""
        texto = (
            "¡Hola! 😊 Soy tu **Analista SIES**. Puedo consultar **506 datos** extraídos de **5 informes** oficiales del SIES.\n\n"
            "📊 **Matrícula** — totales, evolución, por región\n"
            "👤 **Brechas de Género** — participación femenina\n"
            "🎓 **Titulación** — titulados por año\n"
            "📈 **Retención** — permanencia 1er año\n\n"
            "💡 *Prueba preguntando: \"¿Cuántos estudiantes en 2025?\" o \"¿Qué sabemos de la UCT?\"*"
        )
        return {
            "respuesta": texto,
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
        """Responde a despedidas y agradecimientos."""
        return {
            "respuesta": "¡De nada! 😊 Si necesitas algo más sobre educación superior chilena, aquí estaré. ¡Que tengas un excelente día!",
            "fuentes": [],
            "modo_usado": "despedida",
            "sugerencias": [],
        }

    def _respuesta_guiada(self, pregunta: str = "") -> dict:
        """Guía al usuario cuando no se entiende la pregunta."""
        # Si la pregunta tiene contenido pero no se encontró nada
        if pregunta and len(pregunta) > 3:
            intro = (
                f"No encontré información específica para **\"{pregunta[:80]}\"**. "
                "Aquí lo que SÍ puedo consultar:\n\n"
            )
        else:
            intro = ""

        texto = (
            f"{intro}"
            "📊 **Matrícula** — evolución, totales, por región, por tipo de IES\n"
            "👤 **Brechas de Género** — participación femenina, % por área\n"
            "🎓 **Titulación** — totales, % mujeres\n"
            "📈 **Retención** — tasas de permanencia\n\n"
            "💡 **Prueba con preguntas como:**\n"
            "• \"¿Cuántos estudiantes había en 2025?\"\n"
            "• \"¿Qué sabemos de la UCT?\"\n"
            "• \"¿Cómo ha evolucionado la matrícula?\"\n"
            "• \"¿Qué dice el informe de Brechas de Género 2024?\"\n"
            "• \"¿Qué instituciones tienen más estudiantes?\""
        )

        return {
            "respuesta": texto,
            "fuentes": [],
            "modo_usado": "guiado",
            "sugerencias": [
                "¿Cuántos estudiantes había en 2025?",
                "¿Qué sabemos de la UCT?",
                "¿Cómo ha evolucionado la matrícula?",
                "¿Qué dice el informe de Brechas de Género 2024?",
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

    # ── Helpers ───────────────────────────────────────────────────────────

    def _formatear_datos_grafo(self, entidades: list) -> str:
        """Formatea datos del grafo para el prompt de la API (con límites)."""
        partes = []

        for ent in entidades[:2]:
            data = self.grafo.query_entidad(ent["nombre"])
            if not data.get("encontrada"):
                continue

            for nombre_ent, info in data["entidades"].items():
                partes.append(f"**{nombre_ent}** ({info['tipo']})\n")

                # Documentos: max 3
                if info["documentos"]:
                    docs = [f"- {d['archivo'][:40]} ({d.get('año', '')})" for d in info["documentos"][:3]]
                    partes.append("Documentos:\n" + "\n".join(docs) + "\n")

                # Hechos numéricos: max 8
                num_hechos = [h for h in info["hechos"] if isinstance(h.get("valor"), (int, float))]
                if num_hechos:
                    partes.append("Datos:\n")
                    for h in num_hechos[:8]:
                        valor = f"{h['valor']:,.0f}" if isinstance(h['valor'], float) else str(h['valor'])
                        año = f"({h['año']})" if h.get('año') else ""
                        ctx = f" — {h['contexto'][:80]}" if h.get('contexto') else ""
                        partes.append(f"- {h['entidad']}: {valor}{año}{ctx}\n")

                # Hechos cualitativos: max 3
                cualitativos = [h for h in info["hechos"] if not isinstance(h.get("valor"), (int, float))]
                if cualitativos:
                    partes.append("Hallazgos cualitativos:\n")
                    for h in cualitativos[:3]:
                        ctx = h.get("contexto", h.get("afirmacion", ""))[:120]
                        if ctx:
                            partes.append(f"- {ctx}\n")

                # Relaciones: max 4
                if info["relaciones"]:
                    partes.append("Conexiones:\n")
                    for r in info["relaciones"][:4]:
                        partes.append(f"- {r['origen']} → {r['destino']}\n")

        return "\n".join(partes)[:4000]  # Límite total para el prompt

    def _extraer_fuentes(self, entidades: list) -> list:
        """Extrae nombres de documentos fuente de las entidades."""
        fuentes = set()
        for ent in entidades[:3]:
            data = self.grafo.query_entidad(ent["nombre"])
            if data.get("encontrada"):
                for e_name, e_info in data["entidades"].items():
                    for doc in e_info.get("documentos", []):
                        fuentes.add(doc.get("archivo", ""))
        return sorted(fuentes)[:5]

    def _generar_sugerencias(self, entidades: list) -> list:
        """Genera preguntas de seguimiento basadas en entidades encontradas."""
        if not entidades:
            return [
                "¿Cuántos estudiantes había en 2025?",
                "¿Qué instituciones tienen más estudiantes?",
                "¿Cómo ha evolucionado la matrícula?",
            ]
        nombre = entidades[0]["nombre"]
        # Usar versión corta si existe un alias conocido
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
