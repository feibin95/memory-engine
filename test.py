"""
验收测试脚本。运行前确保 memory engine 服务在跑：
    TRANSFORMERS_OFFLINE=1 uvicorn main:app --host 0.0.0.0 --port 8000
"""
import requests
import sys
import uuid

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0


def uid():
    return f"test_{uuid.uuid4().hex[:6]}"


def write(user_id, content):
    return requests.post(f"{BASE}/write", json={"user_id": user_id, "content": content}).json()


def recall(user_id, query, top_k=3):
    return requests.post(f"{BASE}/recall", json={"user_id": user_id, "query": query, "top_k": top_k}).json()


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        FAIL += 1


def events(result):
    return [op["event"] for op in result.get("operations", [])]


def texts(result):
    return [op.get("text", "") for op in result.get("operations", [])]


# ── 测试用例 ──────────────────────────────────────────

print("\n[ 1. 写入有事实的内容 ]")
u = uid()
r = write(u, "我在北京工作，是软件工程师")
check("status ok", r.get("status") == "ok")
check("有 ADD 操作", "ADD" in events(r), str(r))

print("\n[ 2. 写入无事实内容（问句）]")
u = uid()
r = write(u, "我早上喜欢干什么？")
check("status skipped", r.get("status") == "skipped", str(r))

print("\n[ 3. 冲突覆盖 — 换城市 ]")
u = uid()
write(u, "我在上海工作")
r = write(u, "我搬去北京工作了")
check("有 DELETE 操作", "DELETE" in events(r), str(r))
check("有 ADD 操作", "ADD" in events(r), str(r))
memories = [m["content"] for m in recall(u, "我在哪工作")["results"]]
check("上海已不在记忆库", not any("上海" in m for m in memories), str(memories))
check("北京在记忆库", any("北京" in m for m in memories), str(memories))

print("\n[ 4. 冲突覆盖 — 换职业 ]")
u = uid()
write(u, "我是一名软件工程师")
r = write(u, "我换工作了，现在是数据工程师")
check("有 DELETE 操作", "DELETE" in events(r), str(r))
check("有 ADD 操作", "ADD" in events(r), str(r))
memories = [m["content"] for m in recall(u, "我的职业")["results"]]
check("软件工程师已不在记忆库", not any("软件工程师" in m for m in memories), str(memories))
check("数据工程师在记忆库", any("数据工程师" in m for m in memories), str(memories))

print("\n[ 5. 用户隔离 ]")
u1, u2 = uid(), uid()
write(u1, "我有一只猫叫小橘")
r = recall(u2, "宠物")
check("u2 召回为空", r["results"] == [], str(r))

print("\n[ 6. 语义召回 ]")
u = uid()
write(u, "我有一只猫叫小橘")
write(u, "我早上喜欢喝黑咖啡")
memories = [m["content"] for m in recall(u, "你有宠物吗")["results"]]
check("宠物问题召回猫相关记忆", any("猫" in m or "小橘" in m for m in memories), str(memories))

print("\n[ 7. Recall threshold 过滤低分记忆 ]")
u = uid()
write(u, "我有一只猫叫小橘")

# 完全不相关的查询，score 应该很低，threshold=0.5 应过滤掉
results_high = requests.post(f"{BASE}/recall", json={
    "user_id": u, "query": "股票市场今天行情如何", "top_k": 3, "threshold": 0.5
}).json()["results"]
check("threshold=0.5 过滤不相关记忆", len(results_high) == 0, str(results_high))

# threshold=0.0 不过滤，应能召回
results_low = requests.post(f"{BASE}/recall", json={
    "user_id": u, "query": "你有宠物吗", "top_k": 3, "threshold": 0.0
}).json()["results"]
check("threshold=0.0 不过滤，能召回", len(results_low) > 0, str(results_low))

# ── 汇总 ─────────────────────────────────────────────

print(f"\n{'='*40}")
print(f"结果：{PASS} passed, {FAIL} failed")
if FAIL > 0:
    sys.exit(1)
