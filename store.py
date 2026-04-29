import json
import faiss
import numpy as np
from pathlib import Path
import embedder

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DIM = 512  # bge-small-zh-v1.5 输出维度


def _paths(user_id: str) -> tuple[Path, Path]:
    safe = user_id.replace("/", "_")
    return DATA_DIR / f"{safe}.faiss", DATA_DIR / f"{safe}.json"


def _load(user_id: str) -> tuple[faiss.IndexFlatIP, list[str]]:
    idx_path, txt_path = _paths(user_id)
    if idx_path.exists():
        index = faiss.read_index(str(idx_path))
        texts = json.loads(txt_path.read_text(encoding="utf-8"))
    else:
        index = faiss.IndexFlatIP(DIM)
        texts = []
    return index, texts


def _save(user_id: str, index: faiss.IndexFlatIP, texts: list[str]) -> None:
    idx_path, txt_path = _paths(user_id)
    faiss.write_index(index, str(idx_path))
    txt_path.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")


def add(user_id: str, content: str) -> None:
    index, texts = _load(user_id)
    vec = embedder.encode([content])
    index.add(vec)
    texts.append(content)
    _save(user_id, index, texts)


def search(user_id: str, query: str, top_k: int = 5) -> list[dict]:
    index, texts = _load(user_id)
    if index.ntotal == 0:
        return []
    vec = embedder.encode([query])
    k = min(top_k, index.ntotal)
    scores, indices = index.search(vec, k)
    return [
        {"content": texts[idx], "score": float(score)}
        for score, idx in zip(scores[0], indices[0])
        if idx != -1
    ]
