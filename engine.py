import os
import logging
import anthropic
from dotenv import load_dotenv
import store

logger = logging.getLogger("engine")

load_dotenv()

_client = anthropic.Anthropic(
    base_url=os.environ["ANTHROPIC_BASE_URL"],
    api_key=os.environ["ANTHROPIC_API_KEY"],
    default_headers={"X-Working-Dir": os.environ["ANTHROPIC_WORKING_DIR"]},
)
_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_RETRIES = 3

_EXTRACT_PROMPT = """判断对话中是否包含值得长期记忆的事实（偏好、习惯、个人信息、状态等）。
如果有，提取成独立的事实列表，每条一句话。
如果没有（问句、闲聊、指令），返回空列表。"""

_EXTRACT_TOOL = {
    "name": "extract_facts",
    "description": "提取对话中值得长期记忆的事实，无事实则返回空数组",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "facts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "事实列表，无事实则为空数组"
            }
        },
        "required": ["facts"],
        "additionalProperties": False
    }
}

_CONFLICT_PROMPT = """你是一个记忆管理器。

输入：
- 已有记忆：若干条，每条有 id 和内容
- 新事实：一条新的信息

规则：
- 必须对每一条已有记忆给出决策（NONE/UPDATE/DELETE）
- NONE：与新事实无关，保持不变
- UPDATE：描述同一件事但新的更丰富，合并更新（保留原 ID）
- DELETE：描述同类信息但已过时或矛盾（城市变了、职业变了、喜好反转等）
- ADD：新事实是全新信息，id 固定用 "new"
- DELETE + ADD 是常见组合（旧的过时了，新的加进来）

示例：
已有记忆：- id=abc: 职业是软件工程师
新事实：换了工作，现在是数据工程师
输出：[{id:abc, event:DELETE, text:职业是软件工程师}, {id:new, event:ADD, text:职业是数据工程师}]"""

_CONFLICT_TOOL = {
    "name": "resolve_conflicts",
    "description": "对每条已有记忆给出决策，并决定新事实是否加入",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "memory": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":    {"type": "string", "description": "已有记忆的原始 id，或新增时用 'new'"},
                        "text":  {"type": "string", "description": "记忆内容"},
                        "event": {"type": "string", "enum": ["ADD", "UPDATE", "DELETE", "NONE"]}
                    },
                    "required": ["id", "text", "event"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["memory"],
        "additionalProperties": False
    }
}


def _extract_facts(text: str) -> list[str]:
    resp = _client.messages.create(
        model=_MODEL,
        max_tokens=256,
        system=_EXTRACT_PROMPT,
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_facts"},
        messages=[{"role": "user", "content": text}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            facts = block.input.get("facts", [])
            logger.debug("extract_facts input=%r facts=%r", text, facts)
            return facts
    return []


def _resolve_conflicts(fact: str, related: list[dict]) -> list[dict]:
    if not related:
        logger.debug("resolve_conflicts fact=%r no related → ADD", fact)
        return [{"id": "new", "text": fact, "event": "ADD"}]

    required_ids = {r["id"] for r in related}
    hint = ""

    for attempt in range(MAX_RETRIES):
        existing_str = "\n".join(f'- id={r["id"]}: {r["content"]}' for r in related)
        user_content = f"已有记忆：\n{existing_str}\n\n新事实：{fact}"
        if hint:
            user_content += f"\n\n注意：{hint}"

        resp = _client.messages.create(
            model=_MODEL,
            max_tokens=512,
            system=_CONFLICT_PROMPT,
            tools=[_CONFLICT_TOOL],
            tool_choice={"type": "tool", "name": "resolve_conflicts"},
            messages=[{"role": "user", "content": user_content}],
        )

        decisions = []
        for block in resp.content:
            if block.type == "tool_use":
                decisions = block.input.get("memory", [])
                break

        returned_ids = {d["id"] for d in decisions if d["id"] != "new"}
        missing = required_ids - returned_ids

        if not missing:
            logger.debug("resolve_conflicts fact=%r attempt=%d decisions=%r", fact, attempt, decisions)
            return decisions

        logger.warning("resolve_conflicts attempt=%d missing=%r, retrying", attempt, missing)
        hint = f"上次漏掉了这些 id 的决策：{missing}，必须对每条已有记忆都给出 NONE/UPDATE/DELETE 决策。"

    logger.error("resolve_conflicts failed after %d retries for fact=%r, fallback ADD", MAX_RETRIES, fact)
    return [{"id": "new", "text": fact, "event": "ADD"}]


class MemoryEngine:

    def write(self, user_id: str, content: str) -> dict:
        facts = _extract_facts(content)
        if not facts:
            logger.debug("write user=%r content=%r → skipped", user_id, content)
            return {"status": "skipped", "reason": "no facts"}

        results = []
        for fact in facts:
            related = store.search(user_id, fact, top_k=5)
            logger.debug("write fact=%r related=%r", fact, [r["content"] for r in related])
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
                    old_text = related_map[d["id"]]
                    store.delete(user_id, d["id"])
                    results.append({"event": "DELETE", "text": old_text})

        return {"status": "ok", "user_id": user_id, "operations": results}

    def recall(self, user_id: str, query: str, top_k: int = 5, threshold: float = 0.0) -> dict:
        results = store.search(user_id, query, top_k, threshold)
        logger.debug("recall user=%r query=%r threshold=%s results=%r",
                     user_id, query, threshold,
                     [(r["content"], round(r["score"], 3)) for r in results])
        return {"user_id": user_id, "query": query, "results": results}

    def update(self, user_id: str, memory_id: str, content: str) -> dict:
        ok = store.update(user_id, memory_id, content)
        return {"status": "ok" if ok else "not_found"}

    def forget(self, user_id: str, memory_id: str) -> dict:
        ok = store.delete(user_id, memory_id)
        return {"status": "ok" if ok else "not_found"}


engine = MemoryEngine()
