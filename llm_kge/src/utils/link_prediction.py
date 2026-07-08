"""
Link prediction: minería de relaciones latentes del grafo.

Utilidad de carácter diagnóstico/exploratorio que, a partir de un modelo KGE
entrenado, infiere los enlaces (relaciones) más plausibles que el grafo no
contiene de forma explícita. Se apoya en las operaciones de inferencia de
``utils/kge_inference`` (``predict_tails`` / ``predict_heads``).

NOTA: su salida NO la consume la cascada de creación de incidencias ni la
evaluación, que obtienen la predicción de enlaces en vivo a través de
``KGEScorer``. Se mantiene como herramienta de análisis del espacio aprendido.
"""
from __future__ import annotations

import config as cfg
from utils.kge_inference import predict_tails, predict_heads


def mine_implicit_relations(
    model,
    training_factory,
    top_k: int = cfg.TOP_K_PREDICT,
    max_per_relation: int = 20,
) -> dict:
    """
    Para cada relación del grafo, muestrea entidades representativas y predice
    las entidades tail más probables. Permite descubrir patrones latentes como
    "¿qué técnico suele resolver incidencias de typeIncident__1?".

    Retorna un dict estructurado por relación.
    """
    entity_to_id   = training_factory.entity_to_id
    relation_to_id = training_factory.relation_to_id

    results = {}

    # Predicciones head→tail por relación
    for rel_label in relation_to_id:
        print(f"  Prediciendo tails para relación: {rel_label}")
        head_candidates = [
            e for e in entity_to_id
            if e.startswith("incident_")
        ][:max_per_relation]

        rel_predictions = []
        for head in head_candidates:
            preds = predict_tails(model, training_factory, head, rel_label, top_k=5)
            if preds:
                rel_predictions.append({
                    "head": head,
                    "relation": rel_label,
                    "top_tails": [{"entity": e, "score": round(s, 4)} for e, s in preds],
                })
        results[rel_label] = rel_predictions

    # Caso de uso clave: ¿qué técnico resuelve cada tipo de incidencia?
    print("  Prediciendo técnicos por tipo de incidencia ...")
    tech_by_type = {}
    for type_label in [e for e in entity_to_id if e.startswith("typeIncident__")]:
        preds = predict_heads(model, training_factory, "hasTechnician", type_label, top_k=top_k)
        employee_preds = [(e, s) for e, s in preds if e.startswith("employee__")]
        tech_by_type[type_label] = [
            {"technician": e, "score": round(s, 4)} for e, s in employee_preds[:5]
        ]
    results["_techniciansByIncidentType"] = tech_by_type

    return results
