# memory-engine 协作规范

## Commit 规范

每个 commit 只解决一个问题，不要把多件事混在一起。

message 格式：
```
<type>: 一句话说做了什么

为什么这么做，或踩了什么坑（踩坑必须写）
```

type 取值：`feat` / `fix` / `refactor` / `chore`

## 验收流程

每次改动 engine.py / store.py / main.py 后，必须重启服务再跑验收测试才能提交。
**已在跑的服务不会自动加载新代码，跳过重启会测到旧版本。**

**步骤：**

```bash
# 1. 重启服务（每次改代码后必须重启）
kill $(lsof -ti:8000) 2>/dev/null && sleep 1
source .venv/bin/activate
TRANSFORMERS_OFFLINE=1 uvicorn main:app --host 0.0.0.0 --port 8000 &

# 2. 等服务就绪后跑测试
sleep 8 && python3 test.py
```

全部 PASS 才能提交。有 FAIL 必须修复后重新跑。

## 敏感信息

代码里不允许出现 token、URL、路径等环境相关的硬编码值。
一律放 `.env`，模板放 `.env.example`（值用占位符）。
