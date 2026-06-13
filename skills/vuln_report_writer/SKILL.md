---
name: vuln_report_writer
description: 按统一模板生成详细漏洞分析报告（Markdown）。仅当用户显式指名调用本 skill 时触发，不要因模糊意图主动触发。用户说"用 vuln_report_writer"、"帮我出报告"、"生成分析报告"等显式提及本 skill 名称时才激活。
---

# vuln_report_writer

将用户的分析任务→结构化 Markdown 漏洞报告。**不负责漏洞发现**——分析逻辑完全按用户描述执行，本 skill 只负责按模板组织内容。

## 触发条件

**仅当用户明确提及本 skill 名称时触发**，如：
- "用 vuln_report_writer 分析 xxx"
- "调用 vuln_report_writer 出报告"
- "vuln_report_writer 看一下 xxx"
- 其他包含 "vuln_report_writer" 字样的指令

不因用户说"分析 xx 漏洞"、"检查安全"等模糊意图自动触发。

## 工作流

### Step 1：收集必要信息

分析用户描述，提取目标组件/代码/接口信息。检查是否已指定保存路径：

- **已指定** → 跳过，直接使用
- **未指定** → 反问"报告保存到哪个目录？（默认 `.vuln_agent_output/reports/`）"

从任务描述中能推断出的信息不得反问。例如用户说"分析 src/handler.go 的命令注入"，不要反问目标是什么。

### Step 2：按用户描述执行分析

完全按照用户的任务描述进行安全分析，但需遵循下方的**分析纪律**。

可以读源码、追调用链、构造 Payload。分析方式由任务需求决定——可能涉及手动追踪数据流、阅读多文件上下文等。

### Step 3：按模板生成报告

读取 `references/template.md` 中的模板结构，将分析结果填入对应字段。

### Step 4：保存文件

- 文件命名：`{漏洞类型简写}-{slug}-{MMDD-HHMMSS}.md`
  - 例：`cmd-injection-api-query-0610-143022.md`
- 保存到用户指定的目录（或默认 `.vuln_agent_output/reports/`）
- 若同秒冲突，文件名追加 `-2`、`-3`…
- 保存后向用户返回文件路径 + 报告摘要

## 分析纪律

为满足模板字段要求，分析时须遵守以下规则：

1. **读源码，不推测**。所有调用链信息、行号、函数签名必须来自实际文件读取。不得仅凭经验或推测填写。

2. **追踪完整调用链**。从外部可控入口开始，逐跳追踪到危险调用点（sink）。每跳标注 `file:line` 和数据传递方式（字符串拼接、反序列化、参数透传等）。调用链不完整时，在调用链字段标注缺失环节。

3. **PoC/Payload 必须可执行**。不得使用 `...`、`YOUR_PAYLOAD_HERE` 等占位符。构造的 Payload 应在明确给定的假设条件下可直接用于复现。

4. **基于证据判定置信度**：

   | 证据完整度 | 置信度 |
   |---|---|
   | 完整调用链 + 可执行 PoC + 无需额外假设 | High |
   | 完整调用链，但 PoC 依赖特定条件/配置 | Medium |
   | 调用链部分可推断但缺少关键跳跃，或无法构造可执行 PoC | Low |

   置信度为 Low 时，必须在报告中标注"此发现需人工进一步确认"并说明缺失证据。

5. **不伪造数据**。当无法满足某字段要求时，在该字段写明 "需进一步确认：..." 并说明原因。不得编造调用链、行号或 Payload。

## 使用示例

```
用户：用 vuln_report_writer 分析项目中的 src/cmd/run.go 是否存在命令注入漏洞

助手（本 skill）：
  分析：
   - 目标：src/cmd/run.go, 命令注入
   - 保存路径：未指定
   （反问）报告保存到哪个目录？回车用默认 `.vuln_agent_output/reports/`

用户：.vuln_agent_output/reports/

助手（本 skill）：
  1. 读取 src/cmd/run.go，追踪数据流
  2. 定位入口参数 → 中间处理 → 危险调用
  3. 构造 PoC
  4. 生成 Markdown 并按模板填充
  5. 保存到 .vuln_agent_output/reports/cmd-injection-run-0610-143022.md
  → 返回：报告已保存至 xxx，摘要：xxx
```

## 参考

报告模板见 `references/template.md`，生成时必须严格遵循其结构和字段填写指南。
