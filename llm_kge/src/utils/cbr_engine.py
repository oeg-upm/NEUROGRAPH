"""
Motor de razonamiento basado en casos (CBR) para la compleción de incidencias.

Este módulo encapsula la lógica CBR del sistema, de forma simétrica al motor
simbólico (``utils/rule_engine.py``).  Es independiente del modelo KGE: la
puntuación por *embeddings* se recibe mediante inyección de dependencia a
través de un objeto ``kge_scorer`` (cualquier objeto que exponga los métodos
``tails(...)`` y ``heads(...)``; véase ``KGEScorer`` en
``utils/kge_inference``).  Así el CBR puede combinarse con cualquier modelo
de scoring sin acoplarse a ninguna fase del pipeline.

Lo importan tanto la fase 4 (``phase4_incident_creator``) como la fase 5
(``phase5_eval_incident_creator``).
"""
from __future__ import annotations

from collections import Counter

import config as cfg


# ---------------------------------------------------------------------------
# Pool de casos: carga e indexado
# ---------------------------------------------------------------------------

def build_incidents_map_from_tsv(incident_props) -> dict:
    """
    Construye incidents_map = {incident_id: {predicate: [values]}} leyendo
    cfg.TRAIN_TSV (data/triples/train.tsv) directamente, sin pasar por rdflib.

    Solo incluye triples cuya cabeza sea una incidencia (empieza por 'incident_')
    y cuya relación pertenezca a `incident_props` (el esquema de incidencia).

    El pool CBR usa únicamente train.tsv (el 95% de entrenamiento). Las
    incidencias de test_eval.ttl se mantienen fuera para no contaminar las
    métricas de la fase 6.
    """
    if not cfg.TRAIN_TSV.exists():
        raise FileNotFoundError(
            f"No se encontró {cfg.TRAIN_TSV}. "
            "Ejecuta primero la fase 2 del pipeline."
        )

    prop_set = set(incident_props)
    incidents: dict = {}
    with open(cfg.TRAIN_TSV, "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            head, rel, tail = parts
            if not head.startswith("incident_"):
                continue
            if rel not in prop_set:
                continue
            incidents.setdefault(head, {}).setdefault(rel, []).append(tail)
    return incidents


def build_incidents_index(incidents_map: dict) -> dict[str, dict[str, set]]:
    """
    Construye un índice inverso {prop: {value: set(inc_ids)}} a partir de
    incidents_map = {inc_id: {prop: [values]}}. Permite que
    find_matching_incidents pase de un O(N·P) por consulta a una unión de
    conjuntos (≈100× sobre un pool de cientos de miles de incidencias).

    Construir el índice es O(N·P) una sola vez; luego cada consulta es
    proporcional al nº de incidencias que comparten algún valor con
    known_props, no al pool completo.
    """
    index: dict[str, dict[str, set]] = {}
    for inc_id, props in incidents_map.items():
        for prop, values in props.items():
            if not values:
                continue
            bucket = index.setdefault(prop, {})
            if isinstance(values, list):
                for v in values:
                    bucket.setdefault(v, set()).add(inc_id)
            else:
                bucket.setdefault(values, set()).add(inc_id)
    return index


# ---------------------------------------------------------------------------
# Recuperación de casos similares (CBR)
# ---------------------------------------------------------------------------

def find_matching_incidents(
    known_props: dict,
    incidents_map: dict,
    index: dict | None = None,
    exclude_id: str | None = None,
) -> list[str]:
    """
    Devuelve las incident_ids cuyas propiedades coinciden con known_props.
    Empieza exigiendo que TODAS las propiedades conocidas coincidan; si
    obtiene menos de 3 resultados, relaja el umbral en 1 hasta mínimo 1.

    Si se pasa `index` (construido con build_incidents_index) se usa la ruta
    rápida basada en intersección de conjuntos; en caso contrario hace el
    barrido O(N) sobre `incidents_map`.
    `exclude_id` permite descartar una incidencia (típicamente la objetivo
    en evaluación) sin tener que copiar el pool.
    """
    filled = {k: v for k, v in known_props.items() if v is not None}
    if not filled:
        return []

    # --- Ruta rápida con índice inverso -----------------------------------
    if index is not None:
        counter: Counter = Counter()
        for k, v in filled.items():
            ids = index.get(k, {}).get(v)
            if ids:
                counter.update(ids)
        if exclude_id is not None:
            counter.pop(exclude_id, None)
        matches: list[str] = []
        for threshold in range(len(filled), 0, -1):
            matches = [iid for iid, c in counter.items() if c >= threshold]
            if len(matches) >= 3:
                return matches
        return matches

    # --- Ruta original (escaneo lineal) -----------------------------------
    matches = []
    for threshold in range(len(filled), 0, -1):
        matches = [
            inc_id for inc_id, props in incidents_map.items()
            if inc_id != exclude_id
            and sum(1 for k, v in filled.items() if v in props.get(k, [])) >= threshold
        ]
        if len(matches) >= 3:
            return matches
    return matches


# ---------------------------------------------------------------------------
# Recomendación: CBR + KGE fusionados por WRRF
# ---------------------------------------------------------------------------

def recommend_property(
    known_props: dict,
    target_prop: str,
    incidents_map: dict,
    kge_scorer,
    top_k: int = 5,
    rrf_k: float = cfg.RRF_K,
    w_kge: float = cfg.W_KGE,
    w_cbr: float = cfg.W_CBR,
    index: dict | None = None,
    exclude_id: str | None = None,
) -> tuple[list[tuple[str, int, float, float]], int]:
    """
    Genera recomendaciones para target_prop combinando CBR + KGE mediante
    Weighted Reciprocal Rank Fusion (WRRF).

    El scoring KGE se inyecta a través de `kge_scorer`, un objeto que expone:
      - kge_scorer.tails(head_labels, relation_label, top_k) -> [[(ent, score)]]
      - kge_scorer.heads(relation_label, tail_label, top_k)  -> [(ent, score)]
    El CBR queda así desacoplado del modelo de embeddings concreto.

    1. Encuentra proxies CBR (incidencias históricas con propiedades similares)
    2. Para cada proxy, puntúa candidatos con kge_scorer.tails(...)
    3. Para cada candidato calcula:
         - rank_cbr: posición al ordenar por frecuencia CBR (DESC)
         - rank_kge: posición al ordenar por score KGE medio (DESC)
       y fusiona: WRRF(o) = w_kge/(rrf_k + rank_kge) + w_cbr/(rrf_k + rank_cbr)
    4. Fallback si no hay proxies: kge_scorer.heads(...) sobre la primera prop conocida

    Devuelve (lista de (entity_label, cbr_freq, kge_score, wrrf_score), n_proxies)
    ordenada por WRRF DESC.
    """
    proxies = find_matching_incidents(known_props, incidents_map,
                                      index=index, exclude_id=exclude_id)

    if not proxies:
        first_prop = next((k for k, v in known_props.items() if v is not None), None)
        if first_prop:
            heads = kge_scorer.heads(first_prop, known_props[first_prop], top_k=20)
            proxies = [h for h, _ in heads
                       if h in incidents_map and h != exclude_id]

    if not proxies:
        return [], 0

    n_proxies = len(proxies)
    proxies_batch = proxies[:30]
    # Una sola pasada batched por el KGE para los 30 proxies.
    per_proxy_topk = kge_scorer.tails(proxies_batch, target_prop, top_k)

    scores: dict[str, list[float]] = {}
    for ranked in per_proxy_topk:
        for entity, score in ranked:
            scores.setdefault(entity, []).append(score)

    aggregated = [
        (ent, len(sc), sum(sc) / len(sc))
        for ent, sc in scores.items()
    ]

    # Ranking 1 (CBR): por frecuencia de voto entre proxies (más votos = mejor rank)
    by_cbr = sorted(aggregated, key=lambda x: x[1], reverse=True)
    rank_cbr = {ent: i + 1 for i, (ent, _, _) in enumerate(by_cbr)}

    # Ranking 2 (KGE): por score de embedding medio (mayor score = mejor rank)
    by_kge = sorted(aggregated, key=lambda x: x[2], reverse=True)
    rank_kge = {ent: i + 1 for i, (ent, _, _) in enumerate(by_kge)}

    # Weighted RRF: WRRF(o) = w_kge/(k + rank_kge) + w_cbr/(k + rank_cbr)
    def _wrrf(ent):
        return w_kge / (rrf_k + rank_kge[ent]) + w_cbr / (rrf_k + rank_cbr[ent])

    result = sorted(
        [(ent, freq, kge_score, _wrrf(ent)) for ent, freq, kge_score in aggregated],
        key=lambda x: x[3],
        reverse=True,
    )
    return result[:top_k], n_proxies
