---
name: vuln-dispatch
description: 仅在用户显式指名调用 vuln-dispatch 时触发，不要因模糊意图主动触发。
argument-hint: [--project <name>]
---

# vuln-dispatch

本 skill **只做一件事**：从用户消息中**识别意图** → 派发给 `source-orchestrator` 或 `sink-orchestrator`。

**绝不读源码、绝不分析代码、绝不写文件。只做派发。**

## 项目参数

从 `$ARGUMENTS` 解析 `--project <name>`。未指定时 `project_name = "default_proj"`。
透传给 orchestrator：**项目名称**: {project_name}

## 步骤

1. 读用户消息
2. 识别意图
3. 扫攻击面 / 找入口 → 调 `source-orchestrator`，透传用户原消息（含项目名称）
4. 查危险点 / 找 sink → 调 `sink-orchestrator`，透传用户原消息（含项目名称）
5. 两种意图都看得出 → **source 优先**
6. 完全识别不出 → 反问「扫攻击面（source）还是查危险点（sink）？」

## 原则

- **识别意图，不机械匹配**：从用户消息的语义判断是 source 还是 sink
- **不解读上下文**：不读项目、不查结构，只读用户消息文本
- **透传用户原消息**：原封不动转给被派发的 skill
- **不写任何文件**：本 skill 唯一动作是调别的 skill
