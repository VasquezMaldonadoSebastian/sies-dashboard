#!/usr/bin/env python3
"""
Fase 1 — Extractor de Entidades y Hechos SIES (v2)
Estrategia: chunking por secciones + modelo rápido (3B) + post-procesamiento.
Cada sección del documento se procesa por separado con formato de salida simple.
"""

import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import Optional
import ollama

# ── Config ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
RAW_DIR = BASE / "raw"
OUT_DIR = BASE / "grafo" / "extracciones"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODELO = "llama3.2:3b"  # Rápido para muchas llamadas pequeñas

ARCHIVOS = [
    "Informe_matricula_2024_SIES_.md",
    "Informe_Brechas_de_Genero_2024_SIES.md",
    "Informe_Titulacion_2023_SIES.md",
]

# ── Normalización de instituciones ─────────────────────────────────────────
SINONIMOS = {
    "uct": "Universidad Católica de Temuco",
    "uc temuco": "Universidad Católica de Temuco",
    "universidad católica de temuco": "Universidad Católica de Temuco",
    "puc": "Pontificia Universidad Católica de Chile",
    "pontificia universidad católica": "Pontificia Universidad Católica de Chile",
    "u. de chile": "Universidad de Chile",
    "uchile": "Universidad de Chile",
    "duoc": "IP DUOC UC",
    "duoc uc": "IP DUOC UC",
    "iplacex": "IP Latinoamericano de Comercio Exterior",
    "u. andrés bello": "Universidad Andrés Bello",
    "u. de concepción": "Universidad de Concepción",
    "u. de santiago": "Universidad de Santiago de Chile",
    "usach": "Universidad de Santiago de Chile",
}


def normalizar_entidad(nombre: str) -> str:
    """Normaliza nombre de entidad usando sinónimos conocidos."""
    key = nombre.strip().lower()
    # Quitar puntuación
    key = re.sub(r"[.,;:\"\'!¡¿?]", "", key)
    if key in SINONIMOS:
        return SINONIMOS[key]
    return nombre.strip()


# ── Chunking ────────────────────────────────────────────────────────────────
def chunk_by_sections(texto: str, max_chars: int = 4000) -> list[dict]:
    """
    Divide el documento en chunks por secciones (##).
    Cada chunk tiene nombre de sección + contenido.
    """
    # Buscar todas las secciones principales
    lines = texto.split("\n")
    chunks = []
    current_section = "Encabezado"
    current_lines = []

    for line in lines:
        # Detectar secciones markdown
        if line.startswith("## ") and line.strip() != "##":
            # Guardar chunk anterior
            if current_lines:
                content = "\n".join(current_lines).strip()
                if len(content) > 100:  # Ignorar secciones muy cortas
                    chunks.append({
                        "seccion": current_section,
                        "contenido": content,
                    })
            current_section = line.replace("## ", "").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # Último chunk
    if current_lines:
        content = "\n".join(current_lines).strip()
        if len(content) > 100:
            chunks.append({
                "seccion": current_section,
                "contenido": content,
            })

    # Si hay muy pocas secciones o ninguna, chunkear por tamaño
    if len(chunks) <= 2:
        chunks = []
        parts = [texto[i:i+max_chars] for i in range(0, len(texto), max_chars)]
        for i, part in enumerate(parts):
            chunks.append({
                "seccion": f"Parte {i+1}",
                "contenido": part,
            })

    return chunks


# ── Prompt simplificado para el 3B ──────────────────────────────────────────
SECTION_PROMPT = """Eres un extractor de datos de informes educativos SIES (Chile).

Extrae SOLO los datos relevantes de esta sección del informe.
Usa este formato SIMPLE por línea:

ENTIDAD|tipo|valor|año|contexto

Tipos permitidos: institucion, region, area_conocimiento, concepto, cifra, hecho_cualitativo

Ejemplos:
Universidad Católica de Temuco|institucion|8432 estudiantes|2024|Matrícula total UCT en 2024
Matrícula Total|cifra|1385828|2024|Matrícula total educación superior Chile 2024
Mujeres|cifra|53.3%|2024|Porcentaje de mujeres en matrícula total
Región Metropolitana|region|728168 estudiantes|2024|Matrícula RM 2024
Brecha de género en STEM|hecho_cualitativo|Las mujeres representan solo el 23% en carreras de ingeniería|2024|...

REGLAS:
- SOLO líneas con el formato ENTIDAD|tipo|valor|año|contexto
- Una línea por cada dato relevante
- Si no hay datos relevantes, responde solo: SIN DATOS
- NO agregues explicaciones ni markdown
- Prioriza: cifras, instituciones, regiones, áreas de conocimiento"""


# ── Extracción por chunk ────────────────────────────────────────────────────
def extraer_chunk(seccion: str, contenido: str) -> list[str]:
    """Extrae datos de un chunk usando el modelo."""
    if len(contenido) < 50:
        return []

    user = f"SECCIÓN: {seccion}\n\n{contenido[:3500]}"

    try:
        response = ollama.chat(
            model=MODELO,
            messages=[
                {"role": "system", "content": SECTION_PROMPT},
                {"role": "user", "content": user},
            ],
            options={"temperature": 0.1, "num_predict": 1024},
        )
        texto = response["message"]["content"].strip()
        if texto == "SIN DATOS":
            return []
        return [l.strip() for l in texto.split("\n") if "|" in l and l.strip()]
    except Exception as e:
        print(f"      ⚠️  Error en chunk '{seccion[:30]}': {e}")
        return []


# ── Post-procesamiento ──────────────────────────────────────────────────────
def procesar_lineas(lineas: list[str], archivo: str) -> dict:
    """Convierte líneas extraídas en el JSON estructurado."""
    entidades = {
        "instituciones": [],
        "regiones": [],
        "areas_conocimiento": [],
        "niveles_formacion": [],
        "tipos_ies": [],
    }
    hechos_numericos = []
    hechos_cualitativos = []
    relaciones = []
    menciones = defaultdict(list)

    # Mapa de tipos de entidad
    tipo_a_categoria = {
        "institucion": "instituciones",
        "region": "regiones",
        "area_conocimiento": "areas_conocimiento",
        "nivel_formacion": "niveles_formacion",
        "tipo_ies": "tipos_ies",
    }

    for linea in lineas:
        partes = [p.strip() for p in linea.split("|")]
        if len(partes) < 3:
            continue

        entidad = normalizar_entidad(partes[0])
        tipo = partes[1].lower().strip()
        valor = partes[2] if len(partes) > 2 else ""
        año = partes[3] if len(partes) > 3 else ""
        contexto = "|".join(partes[4:]) if len(partes) > 4 else ""

        # Registrar entidad
        if tipo in tipo_a_categoria:
            cat = tipo_a_categoria[tipo]
            if entidad not in [e.get("nombre") if isinstance(e, dict) else e for e in entidades[cat]]:
                entry = {"nombre": entidad}
                if tipo == "institucion":
                    entry["tipo"] = "desconocido"
                entidades[cat].append(entry)

        # Registrar hecho o cifra
        hecho_id = f"h-{len(hechos_numericos) + 1:03d}"
        
        # Detectar si es cifra numérica
        valor_num = None
        valor_limpio = valor.replace(",", "").replace(".", "")
        if valor_limpio.replace(" ", "").isdigit():
            valor_num = int(valor_limpio)
        
        if tipo == "cifra" or (tipo == "concepto" and valor_num is not None):
            hecho = {
                "id": hecho_id,
                "entidad": entidad,
                "valor": valor_num if valor_num else valor,
                "unidad": "estudiantes" if valor_num else "",
                "contexto": contexto,
                "categoria": _detectar_categoria(archivo),
            }
            if año and año.isdigit():
                hecho["año"] = int(año)
            hechos_numericos.append(hecho)
            
            # Extraer variación si está en el contexto
            var_match = re.search(r"([+-]?\d+[.,]?\d*%)", contexto)
            if var_match:
                hecho["variacion"] = var_match.group(1)
        else:
            hecho_cual = {
                "id": f"q-{len(hechos_cualitativos) + 1:03d}",
                "entidad": entidad,
                "afirmacion": valor or contexto,
                "categoria": _detectar_categoria(archivo),
                "seccion": "",
            }
            hechos_cualitativos.append(hecho_cual)

        # Registrar mención
        if contexto:
            menciones[entidad].append({
                "seccion": "",
                "contexto": contexto[:200],
            })

    return {
        "entidades": entidades,
        "hechos_numericos": hechos_numericos,
        "hechos_cualitativos": hechos_cualitativos,
        "menciones_entidades": dict(menciones),
    }


def _detectar_categoria(nombre_archivo: str) -> str:
    """Detecta la categoría SIES desde el nombre del archivo."""
    nombre = nombre_archivo.lower()
    if "matricula" in nombre:
        return "matricula"
    if "brecha" in nombre or "genero" in nombre or "género" in nombre:
        return "brechas-genero"
    if "titulacion" in nombre or "titulación" in nombre or "titulado" in nombre:
        return "titulacion"
    return "desconocida"


def _detectar_año(nombre_archivo: str) -> Optional[int]:
    """Detecta el año principal del informe desde el nombre."""
    años = re.findall(r"\b(20[0-2]\d)\b", nombre_archivo)
    return int(años[-1]) if años else None


# ── Procesamiento completo ──────────────────────────────────────────────────
def procesar_archivo(ruta_md: Path) -> Optional[dict]:
    """Procesa un archivo completo: chunking → extracción → merge."""
    nombre = ruta_md.name
    salida = OUT_DIR / f"{ruta_md.stem}.json"

    if salida.exists():
        with open(salida, "r", encoding="utf-8") as f:
            data = json.load(f)
            h = len(data.get("hechos_numericos", []))
            q = len(data.get("hechos_cualitativos", []))
            print(f"⏭️  {nombre}: {h} hechos, {q} cualitativos")
            return data

    print(f"\n📄 {nombre}")
    with open(ruta_md, "r", encoding="utf-8") as f:
        contenido = f.read()
    print(f"   {len(contenido):,} caracteres")

    # Chunkear
    chunks = chunk_by_sections(contenido)
    print(f"   📑 {len(chunks)} chunks")

    # Extraer cada chunk
    todas_lineas = []
    for i, chunk in enumerate(chunks):
        print(f"   🔍 Chunk {i+1}/{len(chunks)}: '{chunk['seccion'][:40]}'...", end=" ", flush=True)
        t0 = time.time()
        lineas = extraer_chunk(chunk["seccion"], chunk["contenido"])
        elapsed = time.time() - t0
        print(f"{len(lineas)} líneas ({elapsed:.1f}s)")
        todas_lineas.extend(lineas)

    print(f"   📊 Total: {len(todas_lineas)} líneas extraídas")

    # Post-procesar a JSON
    data_raw = procesar_lineas(todas_lineas, nombre)

    # Armar JSON final
    data = {
        "archivo": nombre,
        "categoria": _detectar_categoria(nombre),
        "año": _detectar_año(nombre),
        "resumen_ejecutivo": f"Informe de {_detectar_categoria(nombre)} SIES {_detectar_año(nombre) or ''}",
        "entidades": data_raw["entidades"],
        "hechos_numericos": data_raw["hechos_numericos"],
        "hechos_cualitativos": data_raw["hechos_cualitativos"],
        "relaciones": _generar_relaciones(data_raw),
        "menciones_entidades": data_raw["menciones_entidades"],
        "secciones_detectadas": [c["seccion"] for c in chunks],
        "_metadata": {
            "modelo": MODELO,
            "chunks": len(chunks),
            "lineas_extraidas": len(todas_lineas),
            "procesado": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    # Guardar
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    h = len(data["hechos_numericos"])
    q = len(data["hechos_cualitativos"])
    r = len(data.get("relaciones", []))
    e_inst = len(data["entidades"]["instituciones"])
    e_reg = len(data["entidades"]["regiones"])
    print(f"\n   ✅ {h} hechos numéricos, {q} cualitativos, {r} relaciones")
    print(f"   🏫 {e_inst} instituciones, {e_reg} regiones")
    return data


def _generar_relaciones(data: dict) -> list:
    """Genera relaciones automáticas desde las entidades y hechos."""
    relaciones = []
    
    # Instituciones → regiones
    for inst in data["entidades"]["instituciones"]:
        if inst.get("region"):
            relaciones.append({
                "origen": inst["nombre"],
                "tipo": "esta_en",
                "destino": inst["region"],
            })
    
    # Hechos → entidades principales
    for h in data["hechos_numericos"][:20]:
        for inst in data["entidades"]["instituciones"]:
            if inst["nombre"].lower() in h.get("contexto", "").lower():
                relaciones.append({
                    "origen": inst["nombre"],
                    "tipo": "tiene_matricula" if "matric" in h.get("entidad", "").lower() else "relacionado_con",
                    "destino": h["entidad"],
                    "valor": str(h.get("valor", "")),
                })
    
    return relaciones


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🧠 Extractor SIES v2 — Chunking + 3B")
    print("=" * 60)

    try:
        ollama.list()
        print(f"✅ Ollama OK — modelo: {MODELO}")
    except Exception as e:
        print(f"❌ Ollama no responde: {e}")
        sys.exit(1)

    resultados = []
    for nombre in ARCHIVOS:
        ruta = RAW_DIR / nombre
        if not ruta.exists():
            print(f"⚠️  NO ENCONTRADO: {nombre}")
            continue
        data = procesar_archivo(ruta)
        if data:
            resultados.append(nombre)

    print(f"\n{'=' * 60}")
    print(f"✅ RESUMEN: {len(resultados)}/{len(ARCHIVOS)} archivos procesados")
    for nombre in resultados:
        ruta_json = OUT_DIR / f"{Path(nombre).stem}.json"
        if ruta_json.exists():
            kb = ruta_json.stat().st_size / 1024
            print(f"   • {nombre}: {kb:.0f} KB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
