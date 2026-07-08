#!/usr/bin/env python3
"""Análisis estructural del grafo de conocimiento de incidencias.

Calcula las métricas relevantes para caracterizar la densidad y la
conectividad del grafo, pensadas para el capítulo de Evaluación del TFM:

  - Nodos (|V|), aristas (|E|) y tipos de relación.
  - Grado medio, mediano, máximo y % de nodos de grado 1.
  - Densidad clásica (informativa solo como referencia).
  - Frecuencia de cada relación.
  - Cardinalidad media por relación (tph / hpt) y clasificación
    1-1 / 1-N / N-1 / N-N segun el umbral 1.5 (convencion de
    Bordes et al. 2013 / Wang et al. 2014).  <-- la mas relevante
  - (Opcional) componentes conexas y complejidad ciclomatica.

Uso:
    python src/utils/analyze_graph.py                         # data/triples/train.tsv
    python src/utils/analyze_graph.py --input otra/ruta.tsv
    python src/utils/analyze_graph.py --components            # + componentes conexas
    python src/utils/analyze_graph.py --latex                 # imprime tablas LaTeX

Entrada: un TSV de tripletas (cabeza<TAB>relacion<TAB>cola).
"""
from __future__ import annotations

import argparse
import statistics
from collections import Counter, defaultdict
from pathlib import Path

CARD_THRESHOLD = 1.5  # umbral 1-N segun Bordes et al. (2013)
DEFAULT_INPUT = Path("data/triples/train.tsv")


def load_triples(path: Path):
    """Itera las tripletas (h, r, t) del TSV, ignorando lineas mal formadas."""
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3:
                yield parts[0], parts[1], parts[2]


def classify_relation(tph: float, hpt: float) -> str:
    """Clasifica una relacion en 1-1 / 1-N / N-1 / N-N."""
    many_tails = tph >= CARD_THRESHOLD   # un head -> muchos tails
    many_heads = hpt >= CARD_THRESHOLD   # muchos heads -> un tail
    if not many_tails and not many_heads:
        return "1-1"
    if many_tails and not many_heads:
        return "1-N"
    if not many_tails and many_heads:
        return "N-1"
    return "N-N"


def analyze(path: Path, with_components: bool = False):
    rel_count: Counter = Counter()
    rel_heads: dict[str, set] = defaultdict(set)
    rel_tails: dict[str, set] = defaultdict(set)
    degree: Counter = Counter()
    nodes: set = set()
    n_triples = 0

    # Para componentes conexas (union-find), solo si se pide.
    parent: dict = {}

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # compresion de caminos
            parent[x], x = root, parent[x]
        return root

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for h, r, t in load_triples(path):
        n_triples += 1
        rel_count[r] += 1
        rel_heads[r].add(h)
        rel_tails[r].add(t)
        degree[h] += 1
        degree[t] += 1
        nodes.add(h)
        nodes.add(t)
        if with_components:
            for n in (h, t):
                if n not in parent:
                    parent[n] = n
            union(h, t)

    n_nodes = len(nodes)
    n_rels = len(rel_count)
    degs = list(degree.values())

    # --- Metricas globales ---
    avg_degree = 2 * n_triples / n_nodes if n_nodes else 0.0
    density = (
        2 * n_triples / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0.0
    )
    leaves = sum(1 for d in degs if d == 1)

    print("=" * 70)
    print(f"  Analisis estructural del grafo  ({path})")
    print("=" * 70)
    print(f"  Tripletas (aristas) |E|        : {n_triples:,}")
    print(f"  Nodos (entidades)   |V|        : {n_nodes:,}")
    print(f"  Tipos de relacion              : {n_rels}")
    print(f"  Grado medio (2|E|/|V|)         : {avg_degree:.2f}")
    print(f"  Grado mediano                  : {statistics.median(degs):.0f}")
    print(f"  Grado maximo                   : {max(degs):,}")
    print(f"  Nodos de grado 1               : {leaves:,} ({100*leaves/n_nodes:.1f}%)")
    print(f"  Densidad (2|E|/(|V|(|V|-1)))   : {density:.2e}")

    # --- Cardinalidad por relacion ---
    print("\n" + "-" * 70)
    print("  Cardinalidad media por relacion (tph = tails/head, hpt = heads/tail)")
    print("-" * 70)
    header = (f"  {'relacion':<26}{'#triples':>11}{'#tails':>9}"
              f"{'tph':>8}{'hpt':>11}  tipo")
    print(header)
    card_rows = []
    type_counter: Counter = Counter()
    for r, c in rel_count.most_common():
        n_t = len(rel_tails[r])
        tph = c / len(rel_heads[r])
        hpt = c / n_t
        kind = classify_relation(tph, hpt)
        type_counter[kind] += 1
        card_rows.append((r, c, tph, hpt, kind))
        print(f"  {r:<26}{c:>11,}{n_t:>9,}{tph:>8.2f}{hpt:>11.1f}  {kind}")

    print("\n  Reparto de relaciones por tipo de cardinalidad:")
    for kind in ("1-1", "1-N", "N-1", "N-N"):
        print(f"    {kind}: {type_counter.get(kind, 0)}")

    # --- Componentes conexas / ciclomatica (opcional) ---
    if with_components:
        roots = {find(n) for n in parent}
        n_comp = len(roots)
        comp_size = Counter(find(n) for n in parent)
        largest = max(comp_size.values())
        # Complejidad ciclomatica M = E - V + 2P (no estandar en KGs).
        cyclomatic = n_triples - n_nodes + 2 * n_comp
        print("\n" + "-" * 70)
        print("  Conectividad")
        print("-" * 70)
        print(f"  Componentes conexas            : {n_comp:,}")
        print(f"  Mayor componente               : {largest:,} nodos "
              f"({100*largest/n_nodes:.1f}%)")
        print(f"  Complejidad ciclomatica E-V+2P : {cyclomatic:,}  "
              f"(no estandar en KGs; solo referencia)")

    return card_rows


# ---------------------------------------------------------------------------
# Análisis de conectividad (bipartito / mediado por hubs)
# ---------------------------------------------------------------------------

def _components(edge_pairs):
    """Componentes conexas (no dirigidas) por union-find. Recibe iterable de
    (cabeza, cola). Devuelve (n_componentes, tamaño_mayor, nodos_implicados)."""
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for h, t in edge_pairs:
        ra, rb = find(h), find(t)
        if ra != rb:
            parent[ra] = rb
    sizes = Counter(find(x) for x in parent)
    n = len(sizes)
    big = max(sizes.values()) if sizes else 0
    return n, big, len(parent)


def analyze_connectivity(path: Path, head_prefix: str = "incident_",
                         n_hubs: int = 5):
    """Caracteriza la conectividad: aristas directas entre cabezas, robustez a
    los hubs y componentes manteniendo una sola relación (estructura de estrellas).
    """
    edges = list(load_triples(path))
    deg: Counter = Counter()
    by_rel: dict[str, list] = defaultdict(list)
    head_head = 0
    for h, r, t in edges:
        deg[h] += 1
        deg[t] += 1
        by_rel[r].append((h, t))
        if h.startswith(head_prefix) and t.startswith(head_prefix):
            head_head += 1

    print("=" * 70)
    print("  Análisis de conectividad")
    print("=" * 70)

    n, big, V = _components((h, t) for h, r, t in edges)
    print(f"  Aristas '{head_prefix}*'->'{head_prefix}*' directas : {head_head:,}"
          + ("   (grafo bipartito)" if head_head == 0 else ""))
    print(f"  Componentes (grafo completo)           : {n:,}  "
          f"(mayor {100*big/V:.1f}%)")

    hubs = {x for x, _ in deg.most_common(n_hubs)}
    n, big, V = _components((h, t) for h, r, t in edges
                            if h not in hubs and t not in hubs)
    print(f"  Sin los {n_hubs} nodos de mayor grado          : {n:,}  "
          f"(mayor {100*big/V:.1f}%)")

    print("\n  Componentes manteniendo UNA sola relación (estrellas por valor):")
    rows = []
    for r, pairs in by_rel.items():
        n, big, V = _components(pairs)
        rows.append((r, n, big, V))
    for r, n, big, V in sorted(rows, key=lambda x: -x[1]):
        print(f"    {r:<26} {n:>6,} comp.  (mayor {100*big/V:4.1f}% de {V:,})")

    print("\n  Incidencias que comparten cada valor (vecindad media por relación):")
    for r in sorted(by_rel):
        vals: dict = defaultdict(int)
        for h, t in by_rel[r]:
            if h.startswith(head_prefix):
                vals[t] += 1
        if not vals:
            continue
        sz = sorted(vals.values())
        media = sum(sz) / len(sz)
        mediana = sz[len(sz) // 2]
        print(f"    {r:<26} {len(vals):>6,} valores  "
              f"media={media:7.0f}  mediana={mediana:>6}  max={max(sz):,}")


def print_latex(card_rows):
    """Imprime la tabla de cardinalidad lista para pegar en LaTeX."""
    print("\n% --- tabla LaTeX (cardinalidad por relacion) ---")
    print(r"\begin{tabular}{l r r r l}")
    print(r"  \hline")
    print(r"  \textbf{Relación} & \textbf{Tripletas} & \textbf{tph} & "
          r"\textbf{hpt} & \textbf{Tipo} \\")
    print(r"  \hline")
    for r, c, tph, hpt, kind in card_rows:
        rel = r.replace("_", r"\_")
        print(f"  \\texttt{{{rel}}} & {c:,} & {tph:.2f} & {hpt:.2f} & {kind} \\\\"
              .replace(",", "\\,"))
    print(r"  \hline")
    print(r"\end{tabular}")


def main():
    ap = argparse.ArgumentParser(description="Analisis estructural del grafo KG.")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                    help="TSV de tripletas (por defecto data/triples/train.tsv)")
    ap.add_argument("--components", action="store_true",
                    help="calcula componentes conexas y ciclomatica (mas lento)")
    ap.add_argument("--connectivity", action="store_true",
                    help="analiza la conectividad (bipartito, hubs, estrellas por relacion)")
    ap.add_argument("--latex", action="store_true",
                    help="imprime la tabla de cardinalidad en formato LaTeX")
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(f"No existe el fichero de entrada: {args.input}")

    card_rows = analyze(args.input, with_components=args.components)
    if args.connectivity:
        print()
        analyze_connectivity(args.input)
    if args.latex:
        print_latex(card_rows)


if __name__ == "__main__":
    main()
