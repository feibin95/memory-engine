import re
import uuid
import chromadb
from pathlib import Path
import embedder

DATA_DIR = Path(__file__).parent / "data"
CHROMA_DIR = DATA_DIR / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))


def _get_collection(user_id: str):
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id.replace('/', '_'))
    return _client.get_or_create_collection(
        name=f"user_{safe}",
        metadata={"hnsw:space": "cosine"}
    )


def add(user_id: str, content: str, embedding=None) -> str:
    col = _get_collection(user_id)
    mem_id = str(uuid.uuid4())
    if embedding is None:
        embedding = embedder.encode([content])[0]
    col.add(ids=[mem_id], documents=[content], embeddings=[embedding.tolist()])
    return mem_id


def update(user_id: str, memory_id: str, new_content: str, embedding=None) -> bool:
    col = _get_collection(user_id)
    if not col.get(ids=[memory_id])["ids"]:
        return False
    if embedding is None:
        embedding = embedder.encode([new_content])[0]
    col.update(ids=[memory_id], documents=[new_content], embeddings=[embedding.tolist()])
    return True


def delete(user_id: str, memory_id: str) -> bool:
    col = _get_collection(user_id)
    if not col.get(ids=[memory_id])["ids"]:
        return False
    col.delete(ids=[memory_id])
    return True


def search(user_id: str, query: str, top_k: int = 5, threshold: float = 0.0) -> list[dict]:
    col = _get_collection(user_id)
    count = col.count()
    if count == 0:
        return []
    k = min(top_k, count)
    vec = embedder.encode([query])[0]
    return _query(col, vec, k, threshold)


def search_with_vec(user_id: str, query_vec, top_k: int = 5, threshold: float = 0.0) -> list[dict]:
    col = _get_collection(user_id)
    count = col.count()
    if count == 0:
        return []
    k = min(top_k, count)
    return _query(col, query_vec, k, threshold)


def _query(col, vec, k: int, threshold: float) -> list[dict]:
    results = col.query(
        query_embeddings=[vec.tolist()],
        n_results=k,
        include=["documents", "distances"]
    )
    output = []
    for doc_id, doc, dist in zip(results["ids"][0], results["documents"][0], results["distances"][0]):
        score = 1.0 - dist
        if score >= threshold:
            output.append({"id": doc_id, "content": doc, "score": score})
    return output
