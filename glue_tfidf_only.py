#!/usr/bin/env python3
"""
glue.py — Capa de consulta SIES (TF-IDF + DuckDB opcional).

Usa un índice JSON pre-construido para búsqueda semántica (sin modelos externos).
DuckDB/SQLite es opcional: si no hay DB, responde con el contexto de los documentos.

Uso:
    from glue import SIESKnowledgeBase
    kb = SIESKnowledgeBase()
    rta = kb.consultar("¿Cuántas mujeres había matriculadas en 2025?")
"""

import re
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
SQLITE_DB = BASE / "mifuturo_sies.db"
CHROMA_DIR = BASE / "chromadb"
SEARCH_INDEX = BASE / "search_index.json"


class SIESKnowledgeBase:
    """Capa de consulta con TF-IDF + DuckDB opcional."""

    def __init__(self, sqlite_path=None, search_index=None):
        self.sqlite_path = Path(sqlite_path or SQLITE_DB)
        self.db_disponible = self.sqlite_path.exists()
        self.duckdb = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.documents = []
        self.doc_metadatas = []
        self.doc_ids = []

        # ── Cargar índice de búsqueda ────────────────────────────────────
        idx_path = Path(search_index or SEARCH_INDEX)
        if idx_path.exists():
            with open(idx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                self.documents.append(item["text"])
                self.doc_metadatas.append(item["metadata"])
                self.doc_ids.append(item["id"])
            self._preparar_tfidf()
        else:
            print(f"Índice no encontrado: {idx_path}")

        # ── DuckDB (opcional) ────────────────────────────────────────────
        if self.db_disponible:
            import duckdb
            self.duckdb = duckdb.connect(":memory:")
            self.duckdb.execute("INSTALL sqlite; LOAD sqlite;")
            self.duckdb.execute(f"ATTACH '{self.sqlite_path}' AS sies (TYPE SQLITE)")
            self._crear_vistas()

    def _preparar_tfidf(self):
        """Prepara TF-IDF vectorizer con los documentos."""
        if not self.documents:
            return
        from sklearn.feature_extraction.text import TfidfVectorizer
        stop_words = ["de", "la", "el", "en", "y", "a", "los", "las", "del",
                      "por", "con", "para", "un", "una", "que", "es", "se",
                      "su", "al", "lo", "como", "más", "no", "o", "este",
                      "esta", "entre", "todo", "esta", "s"]
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words=stop_words,
            lowercase=True,
            norm="l2"
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.documents)

    def consultar(self, pregunta: str) -> dict:
        """
        Responde combinando TF-IDF (contexto documentos) + DuckDB (datos).

        Args:
            pregunta: Texto libre en español.

        Returns:
            dict con "respuesta" (str), "fuentes" (list)
        """
        años = self._extraer_años(pregunta)
        respuesta_partes = []
        fuentes = []

        # 1. Búsqueda TF-IDF (independiente de modelos externos)
        ctx_parts = []
        if self.tfidf_vectorizer is not None and self.documents:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = self.tfidf_vectorizer.transform([pregunta.lower()])
            sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            top_indices = sims.argsort()[-5:][::-1]

            for idx in top_indices:
                if sims[idx] > 0.05:
                    src = self.doc_metadatas[idx].get("source", self.doc_ids[idx])
                    fuentes.append(src)
                    clean = self.documents[idx].strip()[:800]
                    ctx_parts.append(f"📄 **{src}**\n{clean}")

        if ctx_parts:
            respuesta_partes.append(
                "**Contexto de los informes SIES:**\n\n" +
                "\n\n---\n\n".join(ctx_parts[:3])
            )

        # 2. DuckDB (si disponible y la pregunta pide datos numéricos)
        if self.db_disponible and self.duckdb and any(
            p in pregunta.lower() for p in
            ["cuántos", "cuántas", "total", "matrícula", "porcentaje",
             "mujeres", "hombres", "evolución", "crecimiento", "región"]
        ):
            datos = self._consultar_datos(años, pregunta)
            if datos:
                respuesta_partes.append(f"\n📊 **Datos (SQLite):**\n{datos}")

        if not respuesta_partes:
            respuesta_partes.append(
                "No encontré información en los documentos disponibles. "
                "Intenta reformular tu pregunta sobre matrícula, instituciones "
                "o educación superior en Chile."
            )

        return {
            "respuesta": "\n\n".join(respuesta_partes),
            "fuentes": list(set(fuentes)),
        }

    def _crear_vistas(self):
        """Crea vistas DuckDB sobre la SQLite adjunta."""
        self.duckdb.execute("""
            CREATE OR REPLACE VIEW matricula_base AS
            SELECT
                CAST(REPLACE(AÑO::VARCHAR, 'MAT_', '') AS INTEGER) AS año,
                CAST(NULLIF("TOTAL MATRÍCULA"::VARCHAR, '') AS BIGINT) AS total,
                CAST(NULLIF("TOTAL MATRÍCULA MUJERES"::VARCHAR, '') AS BIGINT) AS mujeres,
                "CLASIFICACIÓN INSTITUCIÓN NIVEL 1"::VARCHAR AS tipo_ies,
                "NOMBRE INSTITUCIÓN"::VARCHAR AS institucion,
                REGIÓN::VARCHAR AS region
            FROM sies.matricula
            WHERE AÑO IS NOT NULL AND "TOTAL MATRÍCULA" IS NOT NULL
              AND "TOTAL MATRÍCULA"::VARCHAR != ''
        """)

        self.duckdb.execute("""
            CREATE OR REPLACE VIEW evolucion AS
            SELECT año, SUM(total) AS total, SUM(mujeres) AS mujeres,
                   ROUND(SUM(mujeres) * 100.0 / SUM(total), 2) AS pct_mujeres,
                   LAG(SUM(total)) OVER (ORDER BY año) AS anterior,
                   ROUND((SUM(total) - LAG(SUM(total)) OVER (ORDER BY año)) * 100.0
                         / LAG(SUM(total)) OVER (ORDER BY año), 2) AS crecimiento
            FROM matricula_base GROUP BY año ORDER BY año
        """)

    # ── Métodos internos ──────────────────────────────────────────────────

    def _extraer_años(self, texto: str) -> list:
        return [int(m) for m in re.findall(r'\b(20[0-2]\d)\b', texto)
                if 2007 <= int(m) <= 2025]

    def _consultar_datos(self, años: list, pregunta: str) -> str:
        p = pregunta.lower()

        if any(w in p for w in ["evolución", "evolucion", "crecimiento", "histórica", "serie"]):
            rows = self.duckdb.execute(
                "SELECT año, total, pct_mujeres, crecimiento FROM evolucion ORDER BY año"
            ).fetchall()
            lines = ["| Año | Total | % Mujeres | Crecimiento |",
                     "|:---:|------:|:---------:|:-----------:|"]
            for r in rows:
                crec = f"{r[3]:+.2f}%" if r[3] else "—"
                lines.append(f"| {r[0]} | {r[1]:,} | {r[2]:.1f}% | {crec} |")
            return "\n".join(lines)

        if "institución" in p or "institucion" in p or "universidad" in p:
            rows = self.duckdb.execute(f"""
                SELECT institucion, tipo_ies, SUM(total) AS total
                FROM matricula_base
                {f'WHERE año IN ({",".join(map(str, años))})' if años else 'WHERE año = 2025'}
                GROUP BY institucion, tipo_ies ORDER BY total DESC LIMIT 10
            """).fetchall()
            lines = ["| Institución | Tipo | Matrícula |",
                     "|-------------|------|----------:|"]
            for r in rows:
                inst = r[0].decode() if isinstance(r[0], bytes) else str(r[0])
                tipo = r[1].decode() if isinstance(r[1], bytes) else str(r[1])
                lines.append(f"| {inst[:45]} | {tipo} | {r[2]:,} |")
            return "\n".join(lines)

        if "región" in p or "region" in p:
            rows = self.duckdb.execute(f"""
                SELECT region, SUM(total) AS total,
                       ROUND(SUM(mujeres) * 100.0 / SUM(total), 2) AS pct_mujeres
                FROM matricula_base
                WHERE {'año IN (' + ",".join(map(str, años)) + ')' if años else 'año = 2025'}
                  AND region IS NOT NULL AND region != ''
                GROUP BY region ORDER BY total DESC
            """).fetchall()
            lines = ["| Región | Matrícula | % Mujeres |",
                     "|--------|----------:|:---------:|"]
            for r in rows:
                reg = r[0].decode() if isinstance(r[0], bytes) else str(r[0])
                lines.append(f"| {reg} | {r[1]:,} | {r[2]:.1f}% |")
            return "\n".join(lines)

        if años:
            rows = self.duckdb.execute(f"""
                SELECT año, SUM(total) AS total, SUM(mujeres) AS mujeres,
                       ROUND(SUM(mujeres) * 100.0 / SUM(total), 2) AS pct_mujeres
                FROM matricula_base
                WHERE año IN ({",".join(map(str, años))})
                GROUP BY año ORDER BY año
            """).fetchall()
        else:
            rows = self.duckdb.execute(
                "SELECT año, total, mujeres, pct_mujeres FROM evolucion ORDER BY año DESC LIMIT 1"
            ).fetchall()

        if not rows:
            return ""
        lines = ["| Año | Total | Mujeres | % Mujeres |",
                 "|:---:|------:|--------:|:---------:|"]
        for r in rows:
            lines.append(f"| {r[0]} | {r[1]:,} | {r[2]:,} | {r[3]:.1f}% |")
        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    kb = SIESKnowledgeBase()
    if len(sys.argv) > 1:
        pregunta = " ".join(sys.argv[1:])
        print(kb.consultar(pregunta)["respuesta"])
    else:
        tests = [
            "¿Cuántos estudiantes hay en 2025?",
            "¿Cómo ha sido la evolución de la matrícula?",
            "¿Cuántas mujeres hay en la educación superior?",
            "¿Cuáles son las instituciones con más matrícula?",
        ]
        for p in tests:
            print(f"\n❓ {p}")
            print("=" * 40)
            print(kb.consultar(p)["respuesta"][:500])
