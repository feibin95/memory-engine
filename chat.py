import os
import anthropic
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["ANTHROPIC_BASE_URL"]
TOKEN = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
WORKING_DIR = os.environ["ANTHROPIC_WORKING_DIR"]
MEMORY_API = os.getenv("MEMORY_API_URL", "http://localhost:8000")

client = anthropic.Anthropic(
    base_url=BASE_URL,
    api_key=TOKEN,
    default_headers={"X-Working-Dir": WORKING_DIR},
)


def recall(user_id: str, query: str) -> list[str]:
    resp = requests.post(f"{MEMORY_API}/recall", json={"user_id": user_id, "query": query, "top_k": 5})
    resp.raise_for_status()
    return [r["content"] for r in resp.json()["results"]]


def write(user_id: str, content: str) -> None:
    requests.post(f"{MEMORY_API}/write", json={"user_id": user_id, "content": content}).raise_for_status()


def extract(text: str) -> str | None:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=128,
        system="""判断用户这句话是否包含值得长期记忆的事实（偏好、习惯、个人信息等）。
如果有，提取核心事实返回一句话。
如果没有（问句、闲聊、指令），只返回 null。
只返回提取结果或 null，不要解释。""",
        messages=[{"role": "user", "content": text}],
    )
    result = resp.content[0].text.strip()
    return None if result.lower() == "null" else result


SYSTEM_PROMPT = "你是一个有记忆的助手。"


def build_user_message(user_input: str, memories: list[str]) -> str:
    if not memories:
        return user_input
    mem_text = "\n".join(f"- {m}" for m in memories)
    return f"[相关记忆：\n{mem_text}\n]\n\n{user_input}"


def chat(user_id: str, verbose: bool = False) -> None:
    print(f"Memory Chat (user: {user_id})，输入 quit 退出\n")
    messages = []
    while True:
        user_input = input("你: ").strip()
        if not user_input or user_input.lower() == "quit":
            break

        memories = recall(user_id, user_input)

        if verbose:
            print(f"[recall] 召回 {len(memories)} 条记忆:")
            for m in memories:
                print(f"  - {m}")

        user_message = build_user_message(user_input, memories)

        if verbose:
            print(f"[user message]\n{user_message}\n")

        messages.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text
        messages.append({"role": "assistant", "content": reply})
        print(f"助手: {reply}\n")

        fact = extract(user_input)
        if fact:
            write(user_id, fact)
            if verbose:
                print(f"[write] 已存入记忆: {fact!r}\n")
        else:
            if verbose:
                print(f"[write] 无事实，跳过存储\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    verbose = "--verbose" in args
    args = [a for a in args if a != "--verbose"]
    user_id = args[0] if args else "default"
    chat(user_id, verbose=verbose)
