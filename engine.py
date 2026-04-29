import store


class MemoryEngine:

    def write(self, user_id: str, content: str) -> dict:
        store.add(user_id, content)
        return {"status": "ok", "user_id": user_id}

    def recall(self, user_id: str, query: str, top_k: int = 5) -> dict:
        results = store.search(user_id, query, top_k)
        return {"user_id": user_id, "query": query, "results": results}

    def update(self, user_id: str, memory_id: str, content: str) -> dict:
        raise NotImplementedError

    def forget(self, user_id: str, memory_id: str) -> dict:
        raise NotImplementedError


engine = MemoryEngine()
