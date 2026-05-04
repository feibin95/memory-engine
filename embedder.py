from sentence_transformers import SentenceTransformer
import numpy as np
import threading

_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(_MODEL_NAME)
    return _model


def encode(texts: list[str]) -> np.ndarray:
    vecs = get_model().encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vecs.astype("float32")
