import json
import uuid
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


def _load(user_id: str) -> tuple[faiss.IndexFlatIP, list[dict]]:
    idx_path, txt_path = _paths(user_id)
    if idx_path.exists():
        index = faiss.read_index(str(idx_path))
        records = json.loads(txt_path.read_text(encoding="utf-8"))
    else:
        index = faiss.IndexFlatIP(DIM)
        records = []
    return index, records


def _save(user_id: str, index: faiss.IndexFlatIP, records: list[dict]) -> None:
    idx_path, txt_path = _paths(user_id)
    faiss.write_index(index, str(idx_path))
    txt_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def add(user_id: str, content: str) -> str:
    index, records = _load(user_id)
    memory_id = str(uuid.uuid4())[:8]
    vec = embedder.encode([content])
    index.add(vec)
    records.append({"id": memory_id, "content": content})
    _save(user_id, index, records)
    return memory_id


def update(user_id: str, memory_id: str, new_content: str) -> bool:
    index, records = _load(user_id)
    for i, rec in enumerate(records):
        if rec["id"] == memory_id:
            # 重建 index：更新对应位置的向量
            all_contents = [r["content"] for r in records]
            all_contents[i] = new_content
            new_index = faiss.IndexFlatIP(DIM)
            vecs = embedder.encode(all_contents)
            new_index.add(vecs)
            records[i]["content"] = new_content
            _save(user_id, new_index, records)
            return True
    return False


def delete(user_id: str, memory_id: str) -> bool:
    index, records = _load(user_id)
    new_records = [r for r in records if r["id"] != memory_id]
    if len(new_records) == len(records):
        return False
    # 重建 index
    new_index = faiss.IndexFlatIP(DIM)
    if new_records:
        vecs = embedder.encode([r["content"] for r in new_records])
        new_index.add(vecs)
    _save(user_id, new_index, new_records)
    return True


def search(user_id: str, query: str, top_k: int = 5, threshold: float = 0.0) -> list[dict]:
    index, records = _load(user_id)
    if index.ntotal == 0:
        return []
    vec = embedder.encode([query])
    k = min(top_k, index.ntotal)
    scores, indices = index.search(vec, k)
    return [
        {"id": records[idx]["id"], "content": records[idx]["content"], "score": float(score)}
        for score, idx in zip(scores[0], indices[0])
        if idx != -1 and float(score) >= threshold
    ]
