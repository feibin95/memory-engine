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
./verify.sh
```

`verify.sh` 会自动重启服务、等待就绪、再跑测试，全部 PASS 才能提交。有 FAIL 必须修复后重新跑。

## GitHub Release

`gh release` 需要走代理，否则 api.github.com 连不上：

```bash
HTTPS_PROXY=http://127.0.0.1:7897 gh release create ...
```

## 敏感信息

代码里不允许出现 token、URL、路径等环境相关的硬编码值。
一律放 `.env`，模板放 `.env.example`（值用占位符）。
