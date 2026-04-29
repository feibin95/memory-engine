# memory-engine

本地 Memory 基础设施，独立于 LLM，支持语义存取和多轮对话。

## 架构

```
chat.py（对话入口）
    ↓ HTTP
Memory Engine（FastAPI）
    ↓
FAISS + bge-small-zh（本地向量检索）
```

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入实际值：

```
ANTHROPIC_BASE_URL=your_base_url_here
ANTHROPIC_API_KEY=your_token_here
ANTHROPIC_WORKING_DIR=/your/working/dir
ANTHROPIC_MODEL=claude-sonnet-4-6
MEMORY_API_URL=http://localhost:8000
```

### 3. 启动 Memory Engine

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

首次启动会自动下载 bge-small-zh-v1.5 模型（约 90MB），需要联网。

### 4. 启动对话

另开一个终端：

```bash
source .venv/bin/activate
python chat.py <user_id>
```

加 `--verbose` 可查看每轮召回的记忆和拼接的 user message：

```bash
python chat.py alice --verbose
```

## API

Memory Engine 提供 HTTP 接口，可独立使用：

```bash
# 写入记忆
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "content": "我喜欢喝黑咖啡"}'

# 召回记忆
curl -X POST http://localhost:8000/recall \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "query": "早餐习惯", "top_k": 3}'
```

## 数据存储

记忆持久化在 `data/` 目录，每个用户两个文件：

```
data/
├── alice.faiss   # 向量索引
└── alice.json    # 原文
```
