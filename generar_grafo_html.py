#!/usr/bin/env python3
"""
Genera visualización HTML del grafo de conocimiento SIES con pyvis.
Lee grafo_sies.json y produce chromadb/grafo_conocimiento.html
"""
import json
from pathlib import Path
from collections import defaultdict

import networkx as nx
from pyvis.network import Network

BASE = Path(__file__).resolve().parent
GRAFO_PATH = BASE / "grafo" / "grafo_sies.json"
OUTPUT = BASE / "chromadb" / "grafo_conocimiento.html"

# Paleta SIES
COLORS = {
    "institucion": {"bg": "#B8552E", "border": "#8C4220", "font": "#FFFFFF"},
    "region": {"bg": "#3A7D5C", "border": "#2A5E42", "font": "#FFFFFF"},
    "concepto": {"bg": "#5B8FA8", "border": "#3D6E85", "font": "#FFFFFF"},
    "tipo_ies": {"bg": "#C8933C", "border": "#A07128", "font": "#FFFFFF"},
    "area_conocimiento": {"bg": "#7B5EA7", "border": "#5E4288", "font": "#FFFFFF"},
}

def cargar_grafo():
    with open(GRAFO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def contar_hechos(data, entidad):
    """Cuenta hechos numéricos + cualitativos para una entidad."""
    hechos = data.get("hechos", {}).get(entidad, [])
    return len(hechos)

def generar_edges_co_mention(data):
    """Genera edges entre entidades que aparecen en el mismo documento."""
    doc_entities = defaultdict(set)
    for ent, menciones in data.get("menciones", {}).items():
        for m in menciones:
            doc = m.get("_documento", "")
            if doc:
                doc_entities[doc].add(ent)

    co_mention_pairs = defaultdict(int)
    for doc, entities in doc_entities.items():
        ents = list(entities)
        for i in range(len(ents)):
            for j in range(i + 1, len(ents)):
                # Normalize pair ordering
                pair = tuple(sorted([ents[i], ents[j]]))
                co_mention_pairs[pair] += 1

    return co_mention_pairs

def generar_grafo():
    data = cargar_grafo()
    entidades = data.get("entidades", {})
    relaciones = data.get("relaciones", [])
    co_mentions = generar_edges_co_mention(data)

    G = nx.Graph()
    total_types = data.get("resumen", {}).get("tipos_entidades", {})

    print(f"📂 Entidades: {len(entidades)}")
    print(f"📊 Tipos: {total_types}")
    print(f"🔗 Relaciones directas: {len(relaciones)}")
    print(f"🔗 Co-menciones: {len(co_mentions)}")

    # ── Nodos ──
    for nombre, info in entidades.items():
        tipo = info.get("tipo", "concepto")
        n_hechos = contar_hechos(data, nombre)

        # Tamaño: entre 15 y 45, proporcional a n_hechos
        size = min(45, max(15, 10 + n_hechos * 2))
        if n_hechos > 20:
            size = 45
        elif n_hechos > 10:
            size = 35

        color = COLORS.get(tipo, COLORS["concepto"])
        title = (
            f"<b>{nombre}</b><br>"
            f"<small>Tipo: {tipo} | Hechos: {n_hechos}</small>"
        )

        # Shape: star for instituciones, diamond for regions, dot for concepts
        if tipo == "institucion":
            shape = "star"
        elif tipo == "region":
            shape = "diamond"
        else:
            shape = "dot"

        G.add_node(
            nombre,
            label=nombre[:25],
            title=title,
            color=color["bg"],
            size=size,
            shape=shape,
            font={"color": "#2B2520", "size": 11, "face": "DM Sans"},
            borderWidth=2 if tipo == "institucion" else 1,
            border_color=color["border"],
        )

    # ── Edges (relaciones directas) ──
    for rel in relaciones:
        origen = rel["origen"]
        destino = rel["destino"]
        if origen in G and destino in G and origen != destino:
            label = rel.get("valor", "")
            G.add_edge(
                origen,
                destino,
                title=label,
                value=3,
                color={"color": "#B8552E", "opacity": 0.6},
                width=2,
                label=label,
                font={"size": 10, "color": "#6B6560", "strokeWidth": 0},
            )

    # ── Edges (co-menciones) — solo las más significativas ──
    # Filtro: mínimo 2 documentos compartidos, o peso relativo alto
    min_weight = 2  # mínimo de documentos compartidos para crear edge
    co_mention_edges = [(pair, w) for pair, w in co_mentions.items() if w >= min_weight]
    co_mention_edges.sort(key=lambda x: -x[1])

    # Además, limitar edges por entidad para evitar que unas pocas dominen
    edge_count_per_entity = defaultdict(int)
    MAX_EDGES_PER_ENTITY = 8

    for (ent_a, ent_b), weight in co_mention_edges:
        if ent_a in G and ent_b in G and ent_a != ent_b:
            # Skip if already has direct edge
            if G.has_edge(ent_a, ent_b):
                continue
            # Limit per-entity degree to keep graph readable
            if edge_count_per_entity[ent_a] >= MAX_EDGES_PER_ENTITY or \
               edge_count_per_entity[ent_b] >= MAX_EDGES_PER_ENTITY:
                continue
            opacity = min(0.4, 0.15 + weight * 0.03)
            G.add_edge(
                ent_a,
                ent_b,
                title=f"{weight} documento(s) compartido(s)",
                value=max(1, min(3, weight)),
                color={"color": "#94A3B8", "opacity": opacity},
                width=max(0.3, weight * 0.2),
            )
            edge_count_per_entity[ent_a] += 1
            edge_count_per_entity[ent_b] += 1

    # ── Pyvis config ──
    net = Network(height="620px", width="100%", directed=False, bgcolor="#FCFAFA", font_color="#2B2520")

    # Import nodes and edges from nx
    net.from_nx(G)

    # Override physics
    net.set_options("""
    {
      "physics": {
        "stabilization": {"iterations": 150},
        "barnesHut": {
          "gravitationalConstant": -3500,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.5
        }
      },
      "edges": {
        "smooth": {"type": "continuous"}
      },
      "nodes": {
        "borderWidth": 1,
        "font": {"face": "DM Sans, sans-serif", "size": 11}
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200,
        "navigationButtons": true,
        "zoomView": true,
        "dragView": true
      },
      "configure": {
        "enabled": false
      }
    }
    """)

    # Override background and node style
    html = net.generate_html()

    # Inject custom CSS on top of pyvis output
    custom_css = """
    <style>
      #mynetwork {
        background: #FCFAFA !important;
        border-radius: 12px;
        border: 1px solid #D9D4CF;
      }
      .vis-network:focus { outline: none; }
      .vis-tooltip {
        background: #FCFAFA !important;
        border: 1px solid #D9D4CF !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 12px !important;
        color: #2B2520 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
      }
      .vis-button {
        background: #FCFAFA !important;
        border: 1px solid #D9D4CF !important;
        border-radius: 6px !important;
        color: #6B6560 !important;
        font-size: 11px !important;
        padding: 4px 8px !important;
      }
      .vis-button:hover {
        border-color: #B8552E !important;
        color: #B8552E !important;
      }
    </style>
    """

    # Inject CSS after <head> or before </head>
    html = html.replace("</head>", f"{custom_css}</head>", 1)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    n_nodes = len(G.nodes)
    n_edges = len(G.edges)
    print(f"\n✅ Grafo generado: {OUTPUT}")
    print(f"   {n_nodes} nodos, {n_edges} aristas")
    print(f"   Tamaño: {OUTPUT.stat().st_size / 1024:.0f} KB")

    return n_nodes, n_edges


if __name__ == "__main__":
    generar_grafo()
