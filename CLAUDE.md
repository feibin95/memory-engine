# memory-engine 协作规范

## Commit 规范

每个 commit 只解决一个问题，不要把多件事混在一起。

message 格式：
```
<type>: 一句话说做了什么

为什么这么做，或踩了什么坑（踩坑必须写）
```

type 取值：`feat` / `fix` / `refactor` / `chore`

## 敏感信息

代码里不允许出现 token、URL、路径等环境相关的硬编码值。
一律放 `.env`，模板放 `.env.example`（值用占位符）。
