#!/bin/bash
set -e

echo "=== 重启服务 ==="
kill $(lsof -ti:8000) 2>/dev/null || true
sleep 1
source .venv/bin/activate
TRANSFORMERS_OFFLINE=1 uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/memory-engine.log 2>&1 &

echo "等待服务就绪..."
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "服务已就绪"
        break
    fi
    sleep 1
done

echo ""
echo "=== 跑验收测试 ==="
python3 test.py
