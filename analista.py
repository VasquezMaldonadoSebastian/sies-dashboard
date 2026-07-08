#!/usr/bin/env python3
"""
Analista SIES v2 — Presentación estructurada de hechos.
No usa LLM para síntesis (evita alucinaciones).
Usa el grafo directamente y presenta los hechos formateados.
"""

import json
import sys
from pathlib import Path
from grafo_conocimiento import GrafoConocimientoSIES

BASE = Path(__file__).resolve().parent
GRAFO_PATH = BASE / "grafo" / "grafo_sies.json"

# ── Presentación de categorías SIES ────────────────────────────────────────
CATEGORIAS = {
    "matricula": {"icono": "📊", "nombre": "Matrícula", "color": "🟦"},
    "brechas-genero": {"icono": "👤", "nombre": "Brechas de Género", "color": "🟪"},
    "titulacion": {"icono": "🎓", "nombre": "Titulación", "color": "🟩"},
    "retencion": {"icono": "📈", "nombre": "Retención", "color": "🟧"},
}


def formatear_respuesta_entidad(entidad: str, data: dict) -> str:
    """Formatea los datos de una entidad como texto legible."""
    if not data.get("encontrada"):
        return f"❓ No encontré información sobre '{entidad}' en los documentos procesados."
    
    partes = []
    
    for nombre_ent, info in data["entidades"].items():
        partes.append(f"## 🏷️ {nombre_ent}")
        partes.append(f"**Tipo:** {info['tipo']}")
        
        # Documentos donde aparece
        if info["documentos"]:
            partes.append(f"\n### 📄 Presente en {len(info['documentos'])} documentos:")
            for doc in info["documentos"]:
                cat = CATEGORIAS.get(doc.get("categoria", ""), {})
                icono = cat.get("icono", "📄")
                año = doc.get("año", "")
                partes.append(f"- {icono} {doc['archivo'][:50]} ({año})")
        
        # Hechos numéricos agrupados por año y documento
        if info["hechos"]:
            partes.append(f"\n### 📊 Datos numéricos:")
            
            # Agrupar por año
            por_año = {}
            for h in info["hechos"]:
                año = h.get("año", "s/f")
                if año not in por_año:
                    por_año[año] = []
                por_año[año].append(h)
            
            for año in sorted(por_año.keys(), key=lambda x: str(x), reverse=True):
                hechos_año = por_año[año]
                partes.append(f"\n**{año}:**")
                for h in hechos_año[:10]:  # Máximo 10 por año
                    valor = h.get("valor", "?")
                    if isinstance(valor, float):
                        if h.get("unidad") == "%":
                            valor_str = f"{valor:.1f}%"
                        else:
                            valor_str = f"{valor:,.0f}"
                    else:
                        valor_str = str(valor)
                    
                    ctx = h.get("contexto", "")
                    doc = h.get("_documento", "")[:30]
                    var = h.get("variacion", "")
                    linea = f"  • {h['entidad']}: **{valor_str}**"
                    if var:
                        linea += f" ({var})"
                    if ctx:
                        linea += f" — {ctx[:80]}"
                    partes.append(linea)
        
        # Hechos cualitativos
        cualitativos = [h for h in info["hechos"] if not isinstance(h.get("valor", ""), (int, float))]
        # En realidad los cualitativos están en info["hechos"] mezclados. 
        # Los cualitativos no tienen "valor" numérico.
        
        # Relaciones
        if info["relaciones"]:
            partes.append(f"\n### 🔗 Conexiones:")
            for r in info["relaciones"][:8]:
                arrow = "↔" if r.get("tipo") == "relacionado_con" else "→"
                val = f" ({r['valor']})" if r.get("valor") else ""
                partes.append(f"  • {r['origen']} {arrow} {r['destino']}{val}")
        
        # Menciones textuales
        if info["menciones"]:
            partes.append(f"\n### 📝 Contexto textual:")
            for m in info["menciones"][:5]:
                ctx = m.get("contexto", "")
                doc = m.get("_documento", "")[:30]
                if ctx:
                    partes.append(f"  • *\"{ctx[:120]}...\"* — {doc}")
    
    return "\n".join(partes)


def main():
    print("=" * 60)
    print("📊 Analista SIES v2 — Presentación estructurada")
    print("=" * 60)
    
    # Cargar grafo
    grafo = GrafoConocimientoSIES()
    if GRAFO_PATH.exists():
        with open(GRAFO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Cargar desde dict
        grafo.entidades = data.get("entidades", {})
        grafo.hechos = {k: v for k, v in data.get("hechos", {}).items()}
        grafo.relaciones = data.get("relaciones", [])
        grafo.documentos = data.get("documentos", {})
        grafo.menciones = {k: v for k, v in data.get("menciones", {}).items()}
        r = grafo.resumen()
        print(f"📂 Grafo cargado: {r['entidades']} entidades, {r['hechos_totales']} hechos, {r['documentos']} docs")
    else:
        print("❌ No hay grafo. Ejecuta grafo_conocimiento.py primero")
        sys.exit(1)
    
    # Si hay argumento, responder
    if len(sys.argv) > 1:
        consulta = " ".join(sys.argv[1:])
        print(f"\n🔍 Consulta: {consulta}\n")
        
        # Buscar entidades
        resultados = grafo.buscar_con_aliases(consulta)
        
        if resultados:
            for r in resultados[:3]:
                print(f"   → Encontrado: {r['nombre']} ({r['tipo']}) — {r['n_hechos']} hechos, {r['n_documentos']} docs")
            
            print()
            entidad = resultados[0]["nombre"]
            data = grafo.query_entidad(entidad)
            respuesta = formatear_respuesta_entidad(entidad, data)
            print(respuesta)
        else:
            print("❓ No encontré información relacionada con tu consulta.")
            print("   Prueba con: UCT, Matrícula, Retención, Región Metropolitana, etc.")
        
        return
    
    # Demo
    consultas = ["UCT", "Matrícula Total", "Retención", "Región Metropolitana"]
    for q in consultas:
        print(f"\n{'=' * 60}")
        print(f"🔍 Consulta: {q}")
        print(f"{'=' * 60}")
        
        resultados = grafo.buscar_con_aliases(q)
        if resultados:
            entidad = resultados[0]["nombre"]
            data = grafo.query_entidad(entidad)
            print(formatear_respuesta_entidad(entidad, data))
        else:
            print("❓ No encontrado")


if __name__ == "__main__":
    main()
