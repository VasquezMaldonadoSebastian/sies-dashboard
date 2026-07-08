#!/usr/bin/env python3
"""
glue.py — Capa de conexión wiki + DuckDB para el prototipo Matrícula SIES.

Uso:
    from glue import SIESKnowledgeBase
    kb = SIESKnowledgeBase()
    rta = kb.consultar("¿Cuántas mujeres había matriculadas en 2025?")
    print(rta["respuesta"])
    print(rta["fuentes"])
"""

import re
import duckdb
import chromadb
from pathlib import Path


# ── Rutas (relativas a este archivo) ─────────────────────────────────────
BASE = Path(__file__).resolve().parent  # mifuturo-datos/
SQLITE_DB = BASE / "mifuturo_sies.db"
CHROMA_DIR = BASE / "chromadb"


class SIESKnowledgeBase:
    """Capa glue que conecta ChromaDB (wiki semántico) + DuckDB (datos numéricos).

    DuckDB es opcional: si el archivo SQLite no existe, responde solo
    con el contexto semántico de ChromaDB (informes PDF + wiki).

    Si ChromaDB falla (modelo no disponible), usa fallback TF-IDF.
    """

    def __init__(self, sqlite_path=None, chroma_dir=None):
        self.sqlite_path = Path(sqlite_path or SQLITE_DB)
        self.chroma_dir = Path(chroma_dir or CHROMA_DIR)
        self.db_disponible = self.sqlite_path.exists()
        self.chroma_activo = False

        # ── DuckDB (opcional) ─────────────────────────────────────────────
        if self.db_disponible:
            self.duckdb = duckdb.connect(":memory:")
            self.duckdb.execute("INSTALL sqlite; LOAD sqlite;")
            self.duckdb.execute(f"ATTACH '{self.sqlite_path}' AS sies (TYPE SQLITE)")
            self._crear_vistas()

        # ── ChromaDB (intentar, con fallback) ─────────────────────────────
        self.documents = []  # para fallback
        self.doc_metadatas = []
        self.doc_ids_list = []
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None

        try:
            self.chroma = chromadb.PersistentClient(path=str(self.chroma_dir))
            self.collection = self.chroma.get_collection("sies-matricula")
            self.chroma_activo = True
            # Precargar documentos para fallback
            all_docs = self.collection.get()
            self.documents = all_docs["documents"]
            self.doc_metadatas = all_docs["metadatas"]
            self.doc_ids_list = all_docs["ids"]
        except Exception as e:
            # Fallback: cargar documentos directamente + TF-IDF
            self._iniciar_fallback()
            print(f"ChromaDB no disponible, usando fallback TF-IDF: {e}")

    def _iniciar_fallback(self):
        """Carga documentos desde archivos markdown y prepara TF-IDF."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from pathlib import Path

        docs = []
        metas = []
        ids_list = []

        # Buscar en chromadb (los textos ya están en sqlite)
        import sqlite3
        chroma_sqlite = list(self.chroma_dir.glob("chroma.sqlite3"))
        if chroma_sqlite:
            try:
                conn = sqlite3.connect(str(chroma_sqlite[0]))
                rows = conn.execute(
                    "SELECT id, document FROM embeddings ORDER BY id"
                ).fetchall()
                for row in rows:
                    ids_list.append(row[0])
                    docs.append(row[1] if row[1] else "")
                    metas.append({"source": row[0], "type": "fallback"})
                conn.close()
            except Exception:
                pass

        if not docs:
            # Último recurso: cargar desde los archivos .md en chromadb
            for f in sorted(self.chroma_dir.parent.rglob("*.md")):
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    if len(text) > 50:
                        docs.append(text)
                        ids_list.append(str(f.relative_to(self.chroma_dir.parent)))
                        metas.append({"source": str(f), "type": "wiki" if "wiki" in str(f) else "raw_pdf"})
                except Exception:
                    pass

        self.documents = docs
        self.doc_metadatas = metas
        self.doc_ids_list = ids_list

        if docs:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000, stop_words=["de", "la", "el", "en", "y", "a", "los", "las", "del", "por", "con", "para", "un", "una", "que", "es"]
            )
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(docs)
            print(f"Fallback TF-IDF listo: {len(docs)} documentos")

    def _crear_vistas(self):
        """Crea las vistas analíticas sobre la SQLite adjunta."""
        base = """
        CREATE OR REPLACE VIEW matricula_base AS
        SELECT
            CAST(REPLACE(AÑO::VARCHAR, 'MAT_', '') AS INTEGER) AS año,
            CAST(NULLIF("TOTAL MATRÍCULA"::VARCHAR, '') AS BIGINT) AS total,
            CAST(NULLIF("TOTAL MATRÍCULA MUJERES"::VARCHAR, '') AS BIGINT) AS mujeres,
            CAST(NULLIF("TOTAL MATRÍCULA HOMBRES"::VARCHAR, '') AS BIGINT) AS hombres,
            CAST(NULLIF("TOTAL MATRÍCULA PRIMER AÑO"::VARCHAR, '') AS BIGINT) AS primer_año,
            "CLASIFICACIÓN INSTITUCIÓN NIVEL 1"::VARCHAR AS tipo_ies,
            "NOMBRE INSTITUCIÓN"::VARCHAR AS institucion,
            REGIÓN::VARCHAR AS region,
            "NIVEL GLOBAL"::VARCHAR AS nivel
        FROM sies.matricula
        WHERE AÑO IS NOT NULL AND "TOTAL MATRÍCULA" IS NOT NULL
          AND "TOTAL MATRÍCULA"::VARCHAR != ''
        """
        self.duckdb.execute(base)

        evol = """
        CREATE OR REPLACE VIEW evolucion AS
        SELECT año, SUM(total) AS total, SUM(mujeres) AS mujeres,
               ROUND(SUM(mujeres) * 100.0 / SUM(total), 2) AS pct_mujeres,
               LAG(SUM(total)) OVER (ORDER BY año) AS anterior,
               ROUND((SUM(total) - LAG(SUM(total)) OVER (ORDER BY año)) * 100.0
                     / LAG(SUM(total)) OVER (ORDER BY año), 2) AS crecimiento
        FROM matricula_base GROUP BY año ORDER BY año
        """
        self.duckdb.execute(evol)

    # ── Métodos públicos ──────────────────────────────────────────────────

    def consultar(self, pregunta: str) -> dict:
        """
        Responde una pregunta combinando contexto semántico + datos numéricos.

        Cuando la base SQLite no está disponible, responde solo con el
        contexto de los documentos (informes PDF + wiki) desde ChromaDB.

        Args:
            pregunta: Texto libre en español.

        Returns:
            dict con "respuesta" (str), "fuentes" (list)
        """
        años = self._extraer_años(pregunta)
        respuesta_partes = []
        fuentes = []

        # 1. Buscar contexto semántico (ChromaDB o fallback TF-IDF)
        if self.chroma_activo:
            docs = self.collection.query(
                query_texts=[pregunta],
                n_results=5
            )
            resultados = list(zip(
                docs["documents"][0] if docs["documents"] else [],
                docs["metadatas"][0] if docs["metadatas"] else [],
                docs["distances"][0] if docs["distances"] else []
            ))
        elif self.tfidf_vectorizer is not None and self.documents:
            # Fallback TF-IDF
            query_vec = self.tfidf_vectorizer.transform([pregunta])
            from sklearn.metrics.pairwise import cosine_similarity
            sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            top_indices = sims.argsort()[-5:][::-1]
            resultados = []
            for idx in top_indices:
                if sims[idx] > 0.05:
                    resultados.append((
                        self.documents[idx][:2000],
                        self.doc_metadatas[idx],
                        1.0 - sims[idx]
                    ))
        else:
            resultados = []

        if resultados:
            ctx_parts = []
            for doc, meta, dist in resultados:
                if dist < 0.6:
                    src = meta.get("source", "desconocido")
                    fuentes.append(src)
                    clean = doc.strip()[:800]
                    ctx_parts.append(f"📄 **{src}**\n{clean}")

            if ctx_parts:
                respuesta_partes.append(
                    "**Contexto de los informes SIES:**\n\n" +
                    "\n\n---\n\n".join(ctx_parts[:3])
                )

        # 2. Si la DB está disponible y la pregunta pide datos numéricos
        if self.db_disponible and any(p in pregunta.lower() for p in
               ["cuántos", "cuántas", "total", "matrícula", "porcentaje",
                "mujeres", "hombres", "evolución", "crecimiento", "región"]):
            datos = self._consultar_datos(años, pregunta)
            if datos:
                respuesta_partes.append(f"\n📊 **Datos (SQLite):**\n{datos}")

        if not respuesta_partes:
            respuesta_partes.append(
                "No encontré información específica en los documentos disponibles. "
                "Intenta reformular tu pregunta sobre matrícula, instituciones o "
                "educación superior en Chile."
            )

        return {
            "respuesta": "\n\n".join(respuesta_partes),
            "fuentes": list(set(fuentes)),
        }

    def evolucion_anual(self) -> list:
        """Retorna la serie histórica completa como lista de dicts."""
        if not self.db_disponible:
            return []
        rows = self.duckdb.execute(
            "SELECT * FROM evolucion ORDER BY año"
        ).fetchall()
        cols = ["año", "total", "mujeres", "pct_mujeres", "anterior", "crecimiento"]
        return [dict(zip(cols, r)) for r in rows]

    def top_instituciones(self, año: int = 2025, limite: int = 10) -> list:
        """Retorna el top N de instituciones por año."""
        if not self.db_disponible:
            return []
        rows = self.duckdb.execute(f"""
            SELECT institucion, tipo_ies, SUM(total) AS total
            FROM matricula_base
            WHERE año = {año}
            GROUP BY institucion, tipo_ies
            ORDER BY total DESC LIMIT {limite}
        """).fetchall()
        cols = ["institucion", "tipo_ies", "total"]
        return [dict(zip(cols, r)) for r in rows]

    def por_region(self, año: int = 2025) -> list:
        """Matrícula por región para un año."""
        if not self.db_disponible:
            return []
        rows = self.duckdb.execute(f"""
            SELECT region, SUM(total) AS total,
                   ROUND(SUM(mujeres) * 100.0 / SUM(total), 2) AS pct_mujeres
            FROM matricula_base
            WHERE año = {año} AND region IS NOT NULL AND region != ''
            GROUP BY region ORDER BY total DESC
        """).fetchall()
        cols = ["region", "total", "pct_mujeres"]
        return [dict(zip(cols, r)) for r in rows]

    # ── Métodos internos ──────────────────────────────────────────────────

    def _extraer_años(self, texto: str) -> list:
        """Extrae años (2007-2025) del texto."""
        return [int(m) for m in re.findall(r'\b(20[0-2]\d)\b', texto)
                if 2007 <= int(m) <= 2025]

    def _consultar_datos(self, años: list, pregunta: str) -> str:
        """Ejecuta la consulta DuckDB apropiada según la pregunta."""
        p = pregunta.lower()

        # Evolución / crecimiento
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

        # Por institución
        if any(w in p for w in ["institución", "institucion", "universidad", "top", "mayor"]):
            rows = self.duckdb.execute(f"""
                SELECT institucion, tipo_ies, SUM(total) AS total
                FROM matricula_base
                {f'WHERE año IN ({",".join(map(str, años))})' if años else 'WHERE año = 2025'}
                GROUP BY institucion, tipo_ies
                ORDER BY total DESC LIMIT 10
            """).fetchall()
            lines = ["| Institución | Tipo | Matrícula |",
                     "|-------------|------|----------:|"]
            for r in rows:
                inst = r[0].decode() if isinstance(r[0], bytes) else str(r[0])
                tipo = r[1].decode() if isinstance(r[1], bytes) else str(r[1])
                lines.append(f"| {inst} | {tipo} | {r[2]:,} |")
            return "\n".join(lines)

        # Por región
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

        # Por tipo de IES
        if any(w in p for w in ["universidad", "ip ", "cft", "instituto", "tipo de institución"]):
            rows = self.duckdb.execute(f"""
                SELECT tipo_ies, SUM(total) AS total,
                       ROUND(SUM(mujeres) * 100.0 / SUM(total), 2) AS pct_mujeres,
                       ROUND(SUM(total) * 100.0 / SUM(SUM(total)) OVER (), 2) AS participacion
                FROM matricula_base
                WHERE {'año IN (' + ",".join(map(str, años)) + ')' if años else 'año = 2025'}
                  AND tipo_ies IS NOT NULL AND tipo_ies != ''
                GROUP BY tipo_ies ORDER BY total DESC
            """).fetchall()
            lines = ["| Tipo | Matrícula | % Mujeres | % Total |",
                     "|------|----------:|:---------:|:-------:|"]
            for r in rows:
                tipo = r[0].decode() if isinstance(r[0], bytes) else str(r[0])
                lines.append(f"| {tipo} | {r[1]:,} | {r[2]:.1f}% | {r[3]:.1f}% |")
            return "\n".join(lines)

        # Por defecto: datos agregados del/los año(s)
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
            return "No se encontraron datos para esa consulta."

        lines = ["| Año | Total | Mujeres | % Mujeres |",
                 "|:---:|------:|--------:|:---------:|"]
        for r in rows:
            lines.append(f"| {r[0]} | {r[1]:,} | {r[2]:,} | {r[3]:.1f}% |")
        return "\n".join(lines)


# ── CLI de prueba ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    kb = SIESKnowledgeBase()

    if len(sys.argv) > 1:
        pregunta = " ".join(sys.argv[1:])
        resultado = kb.consultar(pregunta)
        print(resultado["respuesta"])
        print("\n---\n**Fuentes:** " + ", ".join(resultado["fuentes"]))
    else:
        # Demo interactivo
        preguntas = [
            "¿Cuántos estudiantes hay en 2025?",
            "¿Cómo ha sido la evolución de la matrícula?",
            "¿Cuántas mujeres hay en la educación superior?",
            "¿Cuáles son las instituciones con más matrícula?",
            "¿Cómo se distribuye la matrícula por región?",
        ]
        for p in preguntas:
            print(f"\n{'='*60}")
            print(f"❓ {p}")
            print(f"{'='*60}")
            r = kb.consultar(p)
            print(r["respuesta"][:400])
            print(f"\n📎 Fuente: {r['fuentes'][0] if r['fuentes'] else 'N/A'}")
