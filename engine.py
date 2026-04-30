import json
import os
import anthropic
from dotenv import load_dotenv
import store

load_dotenv()

_client = anthropic.Anthropic(
    base_url=os.environ["ANTHROPIC_BASE_URL"],
    api_key=os.environ["ANTHROPIC_API_KEY"],
    default_headers={"X-Working-Dir": os.environ["ANTHROPIC_WORKING_DIR"]},
)
_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

_EXTRACT_PROMPT = """判断对话中是否包含值得长期记忆的事实（偏好、习惯、个人信息、状态等）。
如果有，提取成独立的事实列表，每条一句话。
如果没有（问句、闲聊、指令），返回空列表。
只返回 JSON，格式：{"facts": ["事实1", "事实2"]}，不要解释。"""

_CONFLICT_PROMPT = """你是一个记忆管理器。

输入格式：
- 已有记忆：若干条，每条有 id 和内容
- 新事实：一条新的信息

你的任务：
1. 对每一条已有记忆，判断它与新事实的关系，给出操作
2. 判断新事实是否需要 ADD 进记忆

操作定义：
- NONE：已有记忆与新事实无关，保持不变
- UPDATE：已有记忆与新事实描述同一件事，但新的信息更丰富，合并更新（保留原 ID）
- DELETE：已有记忆与新事实描述同一类信息但已过时或矛盾（职业变了、城市变了、喜好反转等），删除旧的
- ADD：新事实是全新信息（id 用 "new"）

规则：
- 必须对输入中每一条已有记忆都给出决策（NONE/UPDATE/DELETE）
- 如果新事实需要加入，额外追加一条 id="new" 的 ADD
- DELETE + ADD 是常见组合（旧的过时了，新的加进来）

示例：
输入：
  已有记忆：- id=abc: 职业是软件工程师
  新事实：换了工作，现在是数据工程师

输出：
{"memory": [{"id": "abc", "text": "职业是软件工程师", "event": "DELETE"}, {"id": "new", "text": "职业是数据工程师", "event": "ADD"}]}

只返回 JSON，不要解释。"""


def _extract_facts(text: str) -> list[str]:
    resp = _client.messages.create(
        model=_MODEL,
        max_tokens=256,
        system=_EXTRACT_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    try:
        return json.loads(resp.content[0].text).get("facts", [])
    except Exception:
        return []


def _resolve_conflicts(fact: str, related: list[dict]) -> list[dict]:
    if not related:
        return [{"id": "new", "text": fact, "event": "ADD"}]

    existing_str = "\n".join(f'- id={r["id"]}: {r["content"]}' for r in related)
    prompt = f"已有记忆：\n{existing_str}\n\n新事实：{fact}\n\n请对每条已有记忆给出 NONE/UPDATE/DELETE 决策，并决定新事实是否需要 ADD。"
    resp = _client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_CONFLICT_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(resp.content[0].text).get("memory", [])
    except Exception:
        return [{"id": "new", "text": fact, "event": "ADD"}]


class MemoryEngine:

    def write(self, user_id: str, content: str) -> dict:
        facts = _extract_facts(content)
        if not facts:
            return {"status": "skipped", "reason": "no facts"}

        results = []
        for fact in facts:
            related = store.search(user_id, fact, top_k=5)
            decisions = _resolve_conflicts(fact, related)

            related_map = {r["id"]: r["content"] for r in related}
            for d in decisions:
                event = d.get("event")
                if event == "ADD":
                    store.add(user_id, d["text"])
                    results.append({"event": "ADD", "text": d["text"]})
                elif event == "UPDATE":
                    store.update(user_id, d["id"], d["text"])
                    results.append({"event": "UPDATE", "id": d["id"], "text": d["text"]})
                elif event == "DELETE":
                    old_text = related_map.get(d["id"], d["id"])
                    store.delete(user_id, d["id"])
                    results.append({"event": "DELETE", "text": old_text})

        return {"status": "ok", "user_id": user_id, "operations": results}

    def recall(self, user_id: str, query: str, top_k: int = 5) -> dict:
        results = store.search(user_id, query, top_k)
        return {"user_id": user_id, "query": query, "results": results}

    def update(self, user_id: str, memory_id: str, content: str) -> dict:
        ok = store.update(user_id, memory_id, content)
        return {"status": "ok" if ok else "not_found"}

    def forget(self, user_id: str, memory_id: str) -> dict:
        ok = store.delete(user_id, memory_id)
        return {"status": "ok" if ok else "not_found"}


engine = MemoryEngine()
