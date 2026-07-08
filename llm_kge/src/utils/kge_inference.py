"""
Inferencia con modelos KGE entrenados (link prediction).

Librería de inferencia sobre los modelos de embeddings: carga de un modelo
entrenado, predicción de colas (tail) y cabezas (head), y el adaptador
``KGEScorer`` que inyecta el KGE en el motor de razonamiento basado en casos
(``utils/cbr_engine``).

Es simétrica a los demás motores de ``utils/`` (``rule_engine``, ``cbr_engine``,
``llm_inference``) y no depende de ninguna fase del pipeline. La importan la
fase de creación de incidencias, la de evaluación y la fase de minería de
relaciones implícitas.
"""
from __future__ import annotations

import torch

import config as cfg


# ---------------------------------------------------------------------------
# Caches por-factory (evitan reconstruir id_to_ent y diccionarios inversos
# en cada llamada a predict_tails / predict_heads).
# ---------------------------------------------------------------------------

_FACTORY_CACHE: dict[int, dict] = {}


def _factory_cache(training_factory) -> dict:
    key = id(training_factory)
    cache = _FACTORY_CACHE.get(key)
    if cache is None:
        cache = {
            "ent2id":   training_factory.entity_to_id,
            "rel2id":   training_factory.relation_to_id,
            "id_to_ent": {v: k for k, v in training_factory.entity_to_id.items()},
            "id_to_rel": {v: k for k, v in training_factory.relation_to_id.items()},
        }
        _FACTORY_CACHE[key] = cache
    return cache


# ---------------------------------------------------------------------------
# Carga del modelo y fábrica de tripletas
# ---------------------------------------------------------------------------

def load_model_by_name(model_name: str = 'DistMult', device: str | None = None):
    """
    Carga un modelo KGE entrenado por nombre desde out/models/<model_name>/.
    Retorna (model, training_factory).

    El factory se carga del directorio del modelo (guardado por PyKEEN durante
    el entrenamiento), garantizando que entity_to_id coincide exactamente con
    el vocabulario con el que se entrenó el modelo.

    device: "cuda" | "cpu" | None.
      - None  → CUDA si está disponible (usado en evaluación del sistema).
      - "cpu" → fuerza CPU. Útil en create_incident, donde la GPU la ocupa vLLM
                y compartirla provoca el fallo NVML del allocator de PyTorch en
                score_t. El scoring de unos pocos proxies en CPU es trivial.
    """
    import pickle
    from pykeen.triples import TriplesFactory

    model_dir = cfg.model_dir(model_name)
    model_path = model_dir / "trained_model.pkl"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Modelo no encontrado: {model_path}\n"
            f"Ejecuta primero:  python src/phase3_kge_train.py --model {model_name}"
        )

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model  = torch.load(model_path, map_location=device, weights_only=False)
    model  = model.to(device)
    model.eval()
    print(f"[KGE] modelo {model_name} cargado en {device}")

    # Intentar cargar el factory guardado durante el entrenamiento.
    # PyKEEN lo guarda en training_triples_factory.pkl (o training.pkl).
    factory_loaded = False
    for fname in ("training_triples_factory.pkl", "training.pkl"):
        fpath = model_dir / fname
        if fpath.exists():
            with open(fpath, "rb") as fh:
                training_factory = pickle.load(fh)
            factory_loaded = True
            break

    if not factory_loaded:
        # Fallback: recrear desde TSV (puede haber mismatch de vocabulario)
        training_factory = TriplesFactory.from_path(cfg.TRAIN_TSV)

    return model, training_factory


def load_model_and_factory():
    """Carga el modelo DistMult (backward compatibility)."""
    return load_model_by_name('DistMult')


# ---------------------------------------------------------------------------
# Predicción de cola (tail prediction)
# ---------------------------------------------------------------------------

def predict_tails(
    model,
    training_factory,
    head_label: str,
    relation_label: str,
    top_k: int = cfg.TOP_K_PREDICT,
) -> list[tuple[str, float]]:
    """
    Dado (head, relation, ?), devuelve las top_k entidades tail más probables.

    Usa model.score_t directamente para evitar incompatibilidades de versión
    entre el factory guardado en el modelo y el factory reconstruido desde TSV.
    """
    try:
        cache    = _factory_cache(training_factory)
        head_id  = cache["ent2id"].get(head_label)
        rel_id   = cache["rel2id"].get(relation_label)
        if head_id is None or rel_id is None:
            return []

        device = next(model.parameters()).device
        hr = torch.tensor([[head_id, rel_id]], dtype=torch.long, device=device)
        with torch.no_grad():
            scores = model.score_t(hr).squeeze(0).cpu()  # [num_entities]

        n = min(top_k, scores.shape[0])
        top_scores, top_ids = torch.topk(scores, n)

        id_to_ent = cache["id_to_ent"]
        return [
            (id_to_ent[i.item()], s.item())
            for i, s in zip(top_ids, top_scores)
            if i.item() in id_to_ent
        ]
    except Exception:
        return []


def predict_tails_batch(
    model,
    training_factory,
    head_labels: list[str],
    relation_label: str,
    top_k: int = cfg.TOP_K_PREDICT,
) -> list[list[tuple[str, float]]]:
    """
    Versión batched de predict_tails: una sola pasada por el KGE para B cabezas
    con la misma relación. Devuelve [top_k_de_head_1, top_k_de_head_2, …].
    Mucho más rápido que llamar predict_tails B veces (elimina B-1 overheads).
    """
    if not head_labels:
        return []
    try:
        cache  = _factory_cache(training_factory)
        ent2id = cache["ent2id"]
        rel_id = cache["rel2id"].get(relation_label)
        if rel_id is None:
            print(f"[KGE][diag] La relación '{relation_label}' no está en el "
                  f"vocabulario del modelo ({len(cache['rel2id'])} relaciones). "
                  f"Sin predicción de cola.")
            return [[] for _ in head_labels]

        rows: list[list[int]] = []
        keep: list[int] = []   # índices originales que pudieron mapearse
        for i, h in enumerate(head_labels):
            hid = ent2id.get(h)
            if hid is not None:
                rows.append([hid, rel_id])
                keep.append(i)
        if not rows:
            print(f"[KGE][diag] Ninguno de los {len(head_labels)} proxies CBR "
                  f"existe en el vocabulario del modelo ({len(ent2id)} entidades). "
                  f"Probablemente train.tsv se regeneró tras entrenar el modelo: "
                  f"los IDs de incidencia ya no coinciden. Reentrena el KGE o usa "
                  f"el train.tsv original.")
            return [[] for _ in head_labels]

        device = next(model.parameters()).device
        hr = torch.tensor(rows, dtype=torch.long, device=device)
        with torch.no_grad():
            scores = model.score_t(hr).cpu()        # [B, num_entities]

        n = min(top_k, scores.shape[1])
        top_scores, top_ids = torch.topk(scores, n, dim=1)

        id_to_ent = cache["id_to_ent"]
        out: list[list[tuple[str, float]]] = [[] for _ in head_labels]
        for j, orig_i in enumerate(keep):
            out[orig_i] = [
                (id_to_ent[i.item()], s.item())
                for i, s in zip(top_ids[j], top_scores[j])
                if i.item() in id_to_ent
            ]
        return out
    except Exception as e:
        import traceback
        print(f"[KGE][diag] predict_tails_batch falló: {type(e).__name__}: {e}")
        traceback.print_exc()
        return [[] for _ in head_labels]


def predict_heads(
    model,
    training_factory,
    relation_label: str,
    tail_label: str,
    top_k: int = cfg.TOP_K_PREDICT,
) -> list[tuple[str, float]]:
    """
    Dado (?, relation, tail), devuelve las top_k entidades head más probables.
    """
    try:
        cache    = _factory_cache(training_factory)
        tail_id  = cache["ent2id"].get(tail_label)
        rel_id   = cache["rel2id"].get(relation_label)
        if tail_id is None or rel_id is None:
            return []

        device = next(model.parameters()).device
        rt = torch.tensor([[rel_id, tail_id]], dtype=torch.long, device=device)
        with torch.no_grad():
            scores = model.score_h(rt).squeeze(0).cpu()  # [num_entities]

        n = min(top_k, scores.shape[0])
        top_scores, top_ids = torch.topk(scores, n)

        id_to_ent = cache["id_to_ent"]
        return [
            (id_to_ent[i.item()], s.item())
            for i, s in zip(top_ids, top_scores)
            if i.item() in id_to_ent
        ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Adaptador de scoring para el motor CBR (inyección de dependencia)
# ---------------------------------------------------------------------------

class KGEScorer:
    """Envuelve un modelo KGE entrenado (model + training_factory) y expone las
    operaciones de scoring que necesita el motor CBR (``utils/cbr_engine``).

    Permite inyectar el KGE en ``recommend_property`` sin que el motor CBR
    conozca ni dependa del modelo concreto.
    """

    def __init__(self, model, training_factory):
        self.model = model
        self.factory = training_factory

    def tails(self, head_labels, relation_label, top_k=cfg.TOP_K_PREDICT):
        return predict_tails_batch(self.model, self.factory, head_labels,
                                   relation_label, top_k)

    def heads(self, relation_label, tail_label, top_k=cfg.TOP_K_PREDICT):
        return predict_heads(self.model, self.factory, relation_label,
                             tail_label, top_k)
