#!/usr/bin/env python3
"""
Fase 2 — Grafo de Conocimiento SIES
Construye un grafo en memoria desde los JSONs de extracción.
Permite consultar entidades, cruzar documentos y descubrir relaciones.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Any, Optional


BASE = Path(__file__).resolve().parent
EXTRACCIONES_DIR = BASE / "grafo" / "extracciones"
GRAFO_PATH = BASE / "grafo" / "grafo_sies.json"


class GrafoConocimientoSIES:
    """Grafo de conocimiento que conecta entidades, hechos y documentos SIES."""

    def __init__(self):
        # Entidades: nombre → metadata
        self.entidades: dict[str, dict] = {}
        
        # Hechos por entidad
        self.hechos: dict[str, list[dict]] = defaultdict(list)
        
        # Relaciones: (origen, tipo, destino) → metadata
        self.relaciones: list[dict] = []
        
        # Documentos procesados
        self.documentos: dict[str, dict] = {}
        
        # Índice inverso: entidad → lista de documentos que la mencionan
        self.menciones: dict[str, list[dict]] = defaultdict(list)

    # ── Carga ───────────────────────────────────────────────────────────────

    def cargar_extraccion(self, ruta_json: Path) -> None:
        """Carga un archivo JSON de extracción al grafo."""
        with open(ruta_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        archivo = data.get("archivo", ruta_json.name)
        categoria = data.get("categoria", "desconocida")
        año = data.get("año")
        metadata = data.get("_metadata", {})

        # Registrar documento
        self.documentos[archivo] = {
            "categoria": categoria,
            "año": año,
            "resumen": data.get("resumen_ejecutivo", ""),
            "modelo": metadata.get("modelo", ""),
        }

        # 1. Registrar entidades
        entidades_raw = data.get("entidades", {})
        
        # Instituciones
        for inst in entidades_raw.get("instituciones", []):
            nombre = inst.get("nombre", "").strip()
            if nombre:
                self._add_entidad(nombre, "institucion", {
                    "tipo": inst.get("tipo", ""),
                    "region": inst.get("region", ""),
                })

        # Regiones
        for region in entidades_raw.get("regiones", []):
            if isinstance(region, str):
                self._add_entidad(region, "region", {})
            elif isinstance(region, dict):
                self._add_entidad(region.get("nombre", ""), "region", region)

        # Áreas de conocimiento
        for area in entidades_raw.get("areas_conocimiento", []):
            if isinstance(area, str):
                self._add_entidad(area, "area_conocimiento", {})

        # Niveles de formación
        for nivel in entidades_raw.get("niveles_formacion", []):
            if isinstance(nivel, str):
                self._add_entidad(nivel, "nivel_formacion", {})

        # Tipos de IES
        for tipo in entidades_raw.get("tipos_ies", []):
            if isinstance(tipo, str):
                self._add_entidad(tipo, "tipo_ies", {})

        # 2. Registrar hechos numéricos
        for hecho in data.get("hechos_numericos", []):
            entidad = hecho.get("entidad", "").strip()
            if entidad:
                self._add_entidad(entidad, "concepto", {})
                hecho["_documento"] = archivo
                self.hechos[entidad].append(hecho)

        # 3. Registrar hechos cualitativos
        for hecho in data.get("hechos_cualitativos", []):
            entidad = hecho.get("entidad", "").strip()
            if entidad:
                self._add_entidad(entidad, "concepto", {})
                hecho["_documento"] = archivo
                self.hechos[entidad].append(hecho)

        # 4. Registrar relaciones
        for rel in data.get("relaciones", []):
            origen = rel.get("origen", "").strip()
            destino = rel.get("destino", "").strip()
            tipo = rel.get("tipo", "relacionado_con").strip()
            if origen and destino:
                self.relaciones.append({
                    "origen": origen,
                    "tipo": tipo,
                    "destino": destino,
                    "valor": rel.get("valor", ""),
                    "_documento": archivo,
                })
                self._add_entidad(origen, "concepto", {})
                self._add_entidad(destino, "concepto", {})

        # 5. Registrar menciones
        for entidad, menciones in data.get("menciones_entidades", {}).items():
            if isinstance(entidad, str) and entidad.strip():
                for m in menciones:
                    if isinstance(m, dict):
                        m["_documento"] = archivo
                        self.menciones[entidad].append(m)

    def _add_entidad(self, nombre: str, tipo: str, metadata: dict = None) -> None:
        """Registra una entidad si no existe."""
        nombre = nombre.strip()
        if not nombre:
            return
        if nombre not in self.entidades:
            self.entidades[nombre] = {"tipo": tipo, "metadata": metadata or {}}

    def cargar_desde_directorio(self, directorio: Optional[Path] = None) -> int:
        """Carga todas las extracciones JSON de un directorio."""
        dir_path = directorio or EXTRACCIONES_DIR
        if not dir_path.exists():
            print(f"❌ Directorio no encontrado: {dir_path}")
            return 0

        json_files = sorted(dir_path.glob("*.json"))
        count = 0
        for fpath in json_files:
            try:
                self.cargar_extraccion(fpath)
                count += 1
                print(f"  ✅ {fpath.name}")
            except Exception as e:
                print(f"  ⚠️  {fpath.name}: {e}")
        return count

    # ── Consultas ───────────────────────────────────────────────────────────

    def query_entidad(self, nombre: str) -> dict:
        """Retorna todos los datos de una entidad."""
        # Búsqueda flexible
        nombre = self._normalize(nombre)
        candidatos = [e for e in self.entidades if nombre in self._normalize(e)]
        
        if not candidatos:
            return {"encontrada": False, "mensaje": f"No se encontró '{nombre}'"}
        
        resultados = {}
        for cand in candidatos:
            info = {
                "tipo": self.entidades[cand]["tipo"],
                "documentos": [],
                "hechos": [],
                "relaciones": [],
                "menciones": [],
            }
            
            # Documentos que la mencionan
            if cand in self.menciones:
                docs_vistos = set()
                for m in self.menciones[cand]:
                    doc = m.get("_documento", "")
                    if doc not in docs_vistos:
                        docs_vistos.add(doc)
                        info["documentos"].append({
                            "archivo": doc,
                            "categoria": self.documentos.get(doc, {}).get("categoria", ""),
                            "año": self.documentos.get(doc, {}).get("año", ""),
                        })
            
            # Hechos
            if cand in self.hechos:
                for h in self.hechos[cand]:
                    info["hechos"].append(h)
            
            # Relaciones como origen
            for r in self.relaciones:
                if cand in (r["origen"], r["destino"]):
                    info["relaciones"].append(r)
            
            # Menciones con contexto
            if cand in self.menciones:
                info["menciones"] = self.menciones[cand][:5]
            
            resultados[cand] = info
        
        return {"encontrada": True, "entidades": resultados}

    def cruzar(self, entidad_a: str, entidad_b: str) -> dict:
        """Encuentra conexiones entre dos entidades."""
        na = self._normalize(entidad_a)
        nb = self._normalize(entidad_b)
        
        data_a = self.query_entidad(entidad_a)
        data_b = self.query_entidad(entidad_b)
        
        if not data_a["encontrada"] or not data_b["encontrada"]:
            return {"conectadas": False, "mensaje": "Una o ambas entidades no encontradas"}
        
        # Relaciones directas
        conexiones_directas = []
        for r in self.relaciones:
            if (na in self._normalize(r["origen"]) and nb in self._normalize(r["destino"])) or \
               (na in self._normalize(r["destino"]) and nb in self._normalize(r["origen"])):
                conexiones_directas.append(r)
        
        # Documentos compartidos
        ent_a_nombres = list(data_a["entidades"].keys())
        ent_b_nombres = list(data_b["entidades"].keys())
        
        docs_compartidos = []
        for ea in ent_a_nombres:
            if ea not in self.menciones:
                continue
            docs_ea = {m.get("_documento") for m in self.menciones[ea]}
            for eb in ent_b_nombres:
                if eb not in self.menciones:
                    continue
                docs_eb = {m.get("_documento") for m in self.menciones[eb]}
                compartidos = docs_ea & docs_eb
                for d in compartidos:
                    docs_compartidos.append({
                        "documento": d,
                        "entidad_a": ea,
                        "entidad_b": eb,
                    })
        
        return {
            "conectadas": len(conexiones_directas) > 0 or len(docs_compartidos) > 0,
            "conexiones_directas": conexiones_directas,
            "documentos_compartidos": docs_compartidos,
        }

    def buscar(self, texto: str) -> list[dict]:
        """Búsqueda flexible por nombre de entidad."""
        texto = self._normalize(texto)
        resultados = []
        for nombre, info in self.entidades.items():
            if texto in self._normalize(nombre):
                resultados.append({
                    "nombre": nombre,
                    "tipo": info["tipo"],
                    "n_hechos": len(self.hechos.get(nombre, [])),
                    "n_relaciones": sum(1 for r in self.relaciones if nombre in (r["origen"], r["destino"])),
                    "n_menciones": len(self.menciones.get(nombre, [])),
                    "n_documentos": len({m.get("_documento") for m in self.menciones.get(nombre, [])}),
                })
        return sorted(resultados, key=lambda x: x["n_menciones"], reverse=True)

    def resumen(self) -> dict:
        """Estadísticas del grafo."""
        tipos = defaultdict(int)
        for e in self.entidades.values():
            tipos[e["tipo"]] += 1
        
        return {
            "entidades": len(self.entidades),
            "tipos_entidades": dict(tipos),
            "hechos_totales": sum(len(h) for h in self.hechos.values()),
            "relaciones": len(self.relaciones),
            "documentos": len(self.documentos),
            "menciones": sum(len(m) for m in self.menciones.values()),
        }

    def cargar_desde_json(self, ruta: Path) -> bool:
        """Carga el grafo desde un archivo JSON serializado."""
        if not ruta.exists():
            return False
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.entidades = data.get("entidades", {})
        self.hechos = {k: v for k, v in data.get("hechos", {}).items()}
        self.relaciones = data.get("relaciones", [])
        self.documentos = data.get("documentos", {})
        self.menciones = {k: v for k, v in data.get("menciones", {}).items()}
        return True

    def guardar(self, ruta: Optional[Path] = None) -> None:
        """Serializa el grafo a JSON."""
        path = ruta or GRAFO_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "resumen": self.resumen(),
            "entidades": {k: v for k, v in sorted(self.entidades.items())},
            "hechos": {k: v for k, v in sorted(self.hechos.items())},
            "relaciones": self.relaciones,
            "documentos": self.documentos,
            "menciones": {k: v for k, v in sorted(self.menciones.items())},
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Grafo guardado: {path} ({path.stat().st_size/1024:.0f} KB)")

    @staticmethod
    def _normalize(s: str) -> str:
        """Normaliza texto para búsqueda."""
        import unicodedata
        s = s.lower().strip()
        s = unicodedata.normalize("NFKD", s)
        s = s.encode("ascii", "ignore").decode("ascii")
        return s
    
    def buscar_con_aliases(self, texto: str) -> list[dict]:
        """Búsqueda que incluye alias de entidades (desde normalizar_entidades.py)."""
        resultados = self.buscar(texto)
        if resultados:
            return resultados

        # Si no encontró, probar con alias desde el mapa centralizado
        try:
            from normalizar_entidades import ALIAS_MAP
            key = texto.lower().strip()
            for canonico, alias_list in ALIAS_MAP.items():
                if key in [a.lower().strip() for a in alias_list]:
                    return self.buscar(canonico)
        except ImportError:
            pass
        return []


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("🧠 Grafo de Conocimiento SIES — Fase 2")
    print("=" * 60)

    grafo = GrafoConocimientoSIES()

    # Cargar extracciones
    print(f"\n📂 Cargando extracciones desde: {EXTRACCIONES_DIR}")
    count = grafo.cargar_desde_directorio()
    print(f"\n   → {count} archivos cargados")

    # Mostrar resumen
    resumen = grafo.resumen()
    print(f"\n📊 Resumen del grafo:")
    print(f"   🏷️  {resumen['entidades']} entidades")
    for tipo, n in sorted(resumen['tipos_entidades'].items()):
        print(f"      ├─ {tipo}: {n}")
    print(f"   📊 {resumen['hechos_totales']} hechos")
    print(f"   🔗 {resumen['relaciones']} relaciones")
    print(f"   📄 {resumen['documentos']} documentos")
    print(f"   📝 {resumen['menciones']} menciones")

    # Guardar
    grafo.guardar()

    # Demo de consultas
    print("\n" + "=" * 60)
    print("🔍 Demo de consultas")
    print("=" * 60)

    for test in ["Matrícula Total", "Mujeres", "Región Metropolitana", "UCT", "Cft", "Duoc"]:
        print(f"\n--- Buscando: '{test}' ---")
        resultados = grafo.buscar_con_aliases(test)
        if resultados:
            for r in resultados[:5]:
                print(f"   🏷️  {r['nombre']} ({r['tipo']})")
                print(f"      📊 {r['n_hechos']} hechos, 🔗 {r['n_relaciones']} rels, 📄 {r['n_documentos']} docs")
        else:
            print(f"   ❌ No encontrado")


if __name__ == "__main__":
    main()
