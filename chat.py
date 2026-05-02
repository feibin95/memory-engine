import os
import anthropic
import requests
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.text import Text
from prompt_toolkit import prompt

load_dotenv()

BASE_URL = os.environ["ANTHROPIC_BASE_URL"]
TOKEN = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
WORKING_DIR = os.environ["ANTHROPIC_WORKING_DIR"]
MEMORY_API = os.getenv("MEMORY_API_URL", "http://localhost:8000")
RECALL_THRESHOLD = float(os.getenv("RECALL_THRESHOLD", "0.3"))

client = anthropic.Anthropic(
    base_url=BASE_URL,
    api_key=TOKEN,
    default_headers={"X-Working-Dir": WORKING_DIR},
)

console = Console()
SYSTEM_PROMPT = "你是一个有记忆的助手。"


def dim(text: str) -> None:
    console.print(Text(text, style="dim"))


def recall(user_id: str, query: str) -> list[str]:
    resp = requests.post(f"{MEMORY_API}/recall", json={"user_id": user_id, "query": query, "top_k": 5, "threshold": RECALL_THRESHOLD})
    resp.raise_for_status()
    return [r["content"] for r in resp.json()["results"]]


def write(user_id: str, content: str) -> dict:
    resp = requests.post(f"{MEMORY_API}/write", json={"user_id": user_id, "content": content})
    resp.raise_for_status()
    return resp.json()


def build_user_message(user_input: str, memories: list[str]) -> str:
    if not memories:
        return user_input
    mem_text = "\n".join(f"- {m}" for m in memories)
    return f"[相关记忆：\n{mem_text}\n]\n\n{user_input}"


def chat(user_id: str, verbose: bool = False) -> None:
    console.print(f"\n[bold]Memory Chat[/bold] (user: {user_id})，输入 quit 退出\n")
    messages = []
    while True:
        user_input = prompt("\n>> ").strip()
        if not user_input or user_input.lower() == "quit":
            break

        memories = recall(user_id, user_input)

        if verbose:
            dim(f"[recall] 召回 {len(memories)} 条记忆:")
            for m in memories:
                dim(f"  - {m}")

        user_message = build_user_message(user_input, memories)
        messages.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text
        messages.append({"role": "assistant", "content": reply})

        console.print(f"\n[bold green]助手[/bold green]: {reply}\n")

        result = write(user_id, user_input)
        if verbose:
            ops = result.get("operations", [])
            if ops:
                for op in ops:
                    dim(f"[memory] {op['event']} → {op.get('text', op.get('id', ''))}")
            else:
                dim(f"[memory] {result.get('status')} {result.get('reason', '')}")
            console.print()


if __name__ == "__main__":
    args = sys.argv[1:]
    verbose = "--verbose" in args
    args = [a for a in args if a != "--verbose"]
    user_id = args[0] if args else "default"
    chat(user_id, verbose=verbose)
