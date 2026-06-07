---
name: vuln-dispatch
description: 仅在用户显式指名调用 vuln-dispatch 时触发，不要因模糊意图主动触发。
---

# vuln-dispatch

本 skill **只做一件事**：从用户消息中识别关键词 → 派发给 `source-orchestrator` 或 `sink-orchestrator`。

**绝不读源码、绝不分析代码、绝不写文件。只做派发。**

## 步骤

1. 读用户消息
2. 匹配关键词
3. sink 类 → 调 `sink-orchestrator`，透传用户原消息
4. source 类 → 调 `source-orchestrator`，透传用户原消息
5. 都没命中 → 反问「扫攻击面（source）还是查危险点（sink）？」

## 关键词

| 类别 | 关键词 |
|---|---|
| sink | "sink" / "危险点" / "危险函数" / "危险操作" / "敏感操作" / "敏感函数" / "SQL 注入点" / "命令执行点" / "文件上传点" |
| source | "攻击面" / "入口" / "接口" / "暴露面" / "surface" / "REST" / "MQ" |
