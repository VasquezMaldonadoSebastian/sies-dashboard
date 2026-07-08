#!/usr/bin/env python3
"""
Normalizador de Entidades SIES
Alias, merge de duplicados, y limpieza de falsas clasificaciones.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent
EXTRACCIONES_DIR = BASE / "grafo" / "extracciones"

# ═══════════════════════════════════════════════════════════════════════════
# MAPA DE ALIAS Y SINÓNIMOS
# ═══════════════════════════════════════════════════════════════════════════

# Formato: "nombre_canonico" → ["alias1", "alias2", ...]
# (se aplica en ambos sentidos: si encuentro un alias, lo renombro al canónico)
ALIAS_MAP = {
    # Instituciones
    "Universidad Católica de Temuco": ["uct", "uc temuco", "universidad católica de temuco"],
    "Pontificia Universidad Católica de Chile": ["puc", "pontificia universidad católica", "uc", "universidad católica"],
    "Universidad de Chile": ["uchile", "u. de chile", "u de chile", "universidad de chile"],
    "Universidad de Santiago de Chile": ["usach", "u. de santiago", "u de santiago"],
    "Universidad de Concepción": ["u. de concepción", "u de concepción", "udeC"],
    "Universidad Andrés Bello": ["unab", "u. andrés bello", "u andrés bello"],
    "IP DUOC UC": ["duoc", "duoc uc", "instituto profesional duoc", "ip duoc"],
    "IP Latinoamericano de Comercio Exterior": ["iplacex", "instituto latinoamericano de comercio exterior"],
    
    # Tipos de institución (normalizar)
    "Centros de Formación Técnica (CFT)": ["cft", "centros de formación técnica", "cft estatales"],
    "Institutos Profesionales (IP)": ["ip", "institutos profesionales", "institutos profesionales (ip)", "ip (instituto profesional)"],
    "Universidades": ["universidad", "universidades estatales", "universidades privadas"],
    
    # Conceptos principales (unificar variantes)
    "Matrícula Total": ["matrícula total", "matricula total", "matrícula total educación superior", 
                       "matrícula total de educación superior", "total matrícula", "matrícula total 2024",
                       "matrícula total educación superior chile 2024"],
    "Participación Femenina": ["mujeres", "matrícula mujeres", "matrícula femenina", "participación femenina",
                              "porcentaje mujeres", "% mujeres", "mujeres en matrícula total"],
    "Participación Masculina": ["hombres", "matrícula hombres", "matrícula masculina", "participación masculina",
                               "porcentaje hombres", "% hombres", "hombres en matrícula total"],
    "Retención 1er Año": ["retención 1er año", "retencion 1er año", "retención de 1er año", 
                         "tasa de retención", "retención primer año", "retencion primer año",
                         "retención de 1 er año", "retención de 1er año de pregrado"],
    "Titulación Total": ["titulación total", "titulacion total", "titulación", "titulacion",
                        "total titulados", "total titulación"],
}

# Construir mapa inverso: alias → canonical
ALIAS_TO_CANONICAL = {}
for canonical, aliases in ALIAS_MAP.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower().strip()] = canonical

# Entidades que NO son regiones (falsos positivos del extractor)
FALSAS_REGIONES = {
    "chile", "cruch", "educación superior", "instituciones acreditadas",
    "instituciones bajo tutela", "no acreditadas", "no acreditadas instituciones",
    "sies", "total", "nacional",
}

# Regiones reales de Chile (para validación)
REGIONES_REALES = {
    "arica", "parinacota", "tarapacá", "antofagasta", "atacama", "coquimbo",
    "valparaíso", "metropolitana", "región metropolitana", "región metropolitana de santiago",
    "santiago", "o'higgins", "libertador general bernardo o'higgins", "maule",
    "ñuble", "biobío", "la araucanía", "araucanía", "los ríos", "los lagos",
    "aysén del general carlos ibáñez del campo", "magallanes",
}

# Áreas de conocimiento reales
AREAS_REALES = {
    "tecnología", "salud", "administración", "comercio", "derecho", "educación",
    "humanidades", "arte", "arquitectura", "ciencias sociales", "ciencias básicas",
    "ciencias", "agropecuaria", "ingeniería", "stem", "ciencias naturales",
    "matemáticas", "estadística", "periodismo", "comunicaciones",
}

# Niveles de formación reales
NIVELES_REALES = {
    "pregrado", "posgrado", "postítulo", "diplomado", "magíster", "doctorado",
    "especialidad", "técnico de nivel superior", "profesional",
    "técnico", "licenciatura", "postítulo",
}


def normalizar_entidad(nombre: str) -> str:
    """Aplica alias y normalización a un nombre de entidad."""
    key = nombre.lower().strip()
    key = re.sub(r"[.,;:\"\'!¡¿?()]", "", key)
    key = key.replace("  ", " ")
    
    if key in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[key]
    
    # También intentar match parcial para casos como
    # "Matrícula Total Educación Superior Chile 2024"
    for canonical, aliases in ALIAS_MAP.items():
        for alias in aliases:
            if alias in key or key in alias:
                return canonical
    
    return nombre


def es_region_valida(nombre: str) -> bool:
    """Verifica si un nombre corresponde a una región real de Chile."""
    key = nombre.lower().strip()
    if key in FALSAS_REGIONES:
        return False
    # Verificar si contiene alguna región real
    for region in REGIONES_REALES:
        if region in key:
            return True
    return False


def es_area_valida(nombre: str) -> bool:
    """Verifica si es un área de conocimiento real."""
    key = nombre.lower().strip()
    return any(area in key for area in AREAS_REALES)


def es_nivel_valido(nombre: str) -> bool:
    """Verifica si es un nivel de formación real."""
    key = nombre.lower().strip()
    return any(nivel in key for nivel in NIVELES_REALES)


def mergear_hechos(hechos: list[dict]) -> list[dict]:
    """Mergea hechos duplicados (misma entidad, mismo año, mismo valor)."""
    vistos = set()
    unicos = []
    for h in hechos:
        key = (h.get("entidad", ""), h.get("año"), str(h.get("valor", "")))
        if key not in vistos:
            vistos.add(key)
            unicos.append(h)
    return unicos


def procesar_archivo(ruta_json: Path) -> bool:
    """Normaliza un archivo de extracción."""
    with open(ruta_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    cambios = 0
    
    # 1. Normalizar nombres en entidades → instituciones
    for inst in data["entidades"]["instituciones"]:
        nuevo = normalizar_entidad(inst["nombre"])
        if nuevo != inst["nombre"]:
            inst["nombre"] = nuevo
            cambios += 1
    
    # 2. Limpiar regiones falsas
    regiones_limpias = []
    for reg in data["entidades"]["regiones"]:
        if es_region_valida(reg["nombre"]):
            regiones_limpias.append(reg)
    if len(regiones_limpias) != len(data["entidades"]["regiones"]):
        data["entidades"]["regiones"] = regiones_limpias
        cambios += 1
    
    # 3. Mover falsas regiones y áreas a conceptos
    areas_limpias = []
    for area in data["entidades"]["areas_conocimiento"]:
        if es_area_valida(area["nombre"]):
            areas_limpias.append(area)
    if len(areas_limpias) != len(data["entidades"]["areas_conocimiento"]):
        data["entidades"]["areas_conocimiento"] = areas_limpias
        cambios += 1
    
    # 4. Limpiar niveles de formación
    niveles_limpios = []
    for nivel in data["entidades"]["niveles_formacion"]:
        if es_nivel_valido(nivel["nombre"]):
            niveles_limpios.append(nivel)
    if len(niveles_limpios) != len(data["entidades"]["niveles_formacion"]):
        data["entidades"]["niveles_formacion"] = niveles_limpios
        cambios += 1
    
    # 5. Normalizar entidades en hechos numéricos
    for h in data["hechos_numericos"]:
        nuevo = normalizar_entidad(h["entidad"])
        if nuevo != h["entidad"]:
            h["entidad"] = nuevo
            cambios += 1
    
    # 6. Normalizar entidades en hechos cualitativos
    for h in data["hechos_cualitativos"]:
        nuevo = normalizar_entidad(h["entidad"])
        if nuevo != h["entidad"]:
            h["entidad"] = nuevo
            cambios += 1
    
    # 7. Mergear hechos duplicados
    antes = len(data["hechos_numericos"])
    data["hechos_numericos"] = mergear_hechos(data["hechos_numericos"])
    despues = len(data["hechos_numericos"])
    if antes != despues:
        cambios += 1
    
    # 8. Normalizar menciones
    menciones_normalizadas = defaultdict(list)
    for ent, m_list in data["menciones_entidades"].items():
        nuevo = normalizar_entidad(ent)
        menciones_normalizadas[nuevo].extend(m_list)
    data["menciones_entidades"] = dict(menciones_normalizadas)
    
    # Guardar si hubo cambios
    if cambios > 0:
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ {ruta_json.name}: {cambios} cambios aplicados")
        return True
    else:
        print(f"   ⏭️  {ruta_json.name}: sin cambios necesarios")
        return False


def main():
    print("=" * 60)
    print("🔧 Normalizador de Entidades SIES")
    print("=" * 60)
    
    print(f"\n📂 Procesando: {EXTRACCIONES_DIR}")
    
    total_cambios = 0
    for fpath in sorted(EXTRACCIONES_DIR.glob("*.json")):
        if procesar_archivo(fpath):
            total_cambios += 1
    
    print(f"\n📊 Archivos modificados: {total_cambios}")
    
    # Mostrar resultado
    print(f"\n📋 Resumen de alias registrados:")
    for canonical, aliases in sorted(ALIAS_MAP.items()):
        print(f"   • {canonical}")
        for a in aliases[:3]:
            print(f"      ← {a}")
        if len(aliases) > 3:
            print(f"      ... +{len(aliases)-3} más")


if __name__ == "__main__":
    main()
