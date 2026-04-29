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


def build_system(memories: list[str]) -> str:
    if not memories:
        return "你是一个有记忆的助手。"
    mem_text = "\n".join(f"- {m}" for m in memories)
    return f"你是一个有记忆的助手。\n\n以下是与当前话题相关的记忆：\n{mem_text}"


def chat(user_id: str, verbose: bool = False) -> None:
    print(f"Memory Chat (user: {user_id})，输入 quit 退出\n")
    while True:
        user_input = input("你: ").strip()
        if not user_input or user_input.lower() == "quit":
            break

        memories = recall(user_id, user_input)

        if verbose:
            print(f"[recall] 召回 {len(memories)} 条记忆:")
            for m in memories:
                print(f"  - {m}")

        system = build_system(memories)

        if verbose:
            print(f"[system prompt]\n{system}\n")

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_input}],
        )
        reply = response.content[0].text
        print(f"助手: {reply}\n")

        write(user_id, user_input)
        if verbose:
            print(f"[write] 已存入记忆: {user_input!r}\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    verbose = "--verbose" in args
    args = [a for a in args if a != "--verbose"]
    user_id = args[0] if args else "default"
    chat(user_id, verbose=verbose)
