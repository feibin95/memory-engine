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
        records = json.loads(txt_path.read_text(encoding="utf-8"))
    else:
        index = faiss.IndexFlatIP(DIM)
        records = []
    return index, records


def _save(user_id: str, index: faiss.IndexFlatIP, records: list[str]) -> None:
    idx_path, txt_path = _paths(user_id)
    faiss.write_index(index, str(idx_path))
    txt_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def add(user_id: str, content: str) -> None:
    index, records = _load(user_id)
    vec = embedder.encode([content])
    index.add(vec)
    records.append(content)
    _save(user_id, index, records)


def update(user_id: str, memory_id: str, new_content: str) -> bool:
    index, records = _load(user_id)
    i = int(memory_id)
    if i < 0 or i >= len(records):
        return False
    records[i] = new_content
    new_index = faiss.IndexFlatIP(DIM)
    vecs = embedder.encode(records)
    new_index.add(vecs)
    _save(user_id, new_index, records)
    return True


def delete(user_id: str, memory_id: str) -> bool:
    index, records = _load(user_id)
    i = int(memory_id)
    if i < 0 or i >= len(records):
        return False
    records.pop(i)
    new_index = faiss.IndexFlatIP(DIM)
    if records:
        vecs = embedder.encode(records)
        new_index.add(vecs)
    _save(user_id, new_index, records)
    return True


def search(user_id: str, query: str, top_k: int = 5, threshold: float = 0.0) -> list[dict]:
    index, records = _load(user_id)
    if index.ntotal == 0:
        return []
    vec = embedder.encode([query])
    k = min(top_k, index.ntotal)
    scores, indices = index.search(vec, k)
    return [
        {"id": str(idx), "content": records[idx], "score": float(score)}
        for score, idx in zip(scores[0], indices[0])
        if idx != -1 and float(score) >= threshold
    ]
