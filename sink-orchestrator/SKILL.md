---
name: sink-orchestrator
description: 仅在用户显式指名调用 sink-orchestrator 时触发，不要因模糊意图主动触发。
---

# sink-orchestrator

把 3 个 sink-based agent **串起来**跑：sink-collector → sink-vulnerability-analyst → sink-re-analyzer。

- **本 skill 做**：按顺序触发子 agent，每阶段 5 并发
- **本 skill 不做**：状态文件、断点续跑、失败重试、复杂汇报 —— 子 agent 失败就跳过该项

## 流水线

```
[0] sink-collector                 (单次)
    → sink_list/（递归 .md）
[1] sink-vulnerability-analyst  (每条目 5 并发)
    → sink_findings/（递归 .md）
[2] sink-re-analyzer   (每条目 5 并发)
    → sink_reviews/（递归 .md）
```

**产物**统一在 `.vuln_agent_output/` 下（当前工作目录视为被扫描项目根）：

```
.vuln_agent_output/
├── sink_list/                 ← 可含子目录（如 sql/、cmd/）
├── sink_findings/             ← 镜像输入子目录结构
├── sink_reviews/              ← 镜像输入子目录结构
├── meta/error/
└── temp/
    └── scripts/
```

## 工作流程

### 1. 启动

用户调用 `sink-orchestrator` 时，从用户消息中识别 sink 类型。**已包含的不反问，只反问确实缺失的**：

- 调用方已指定 `vuln_type`（如 cmd/sql）→ 直接透传给 sink-collector，不反问
- 用户已指明 sink 类型（如"扫 SQL 和命令执行"）→ 透传给 sink-collector
- 用户没说具体类型 → 反问"重点关注哪些 sink 类型？如 SQL / 命令 / 文件 / 网络 / 反序列化 / 弱加密（不选则全扫）"，选后透传
- 用户说"全部" / 没说且反问后仍没选 → 透传 all，sink-collector 全扫

scope 隐式默认当前项目目录，**不**反问。

### 2. 跑流水线

依次执行，每阶段用 `task` 工具派发 subagent：

**Stage 0**（单次）：
```
  subagent: sink-collector
prompt: 按 sink-collector agent 的职责执行
        - work_dir: .
        - user_intent: {用户给的 sink 类型}
        - vuln_type: {vuln_type，如 cmd/sql}
        产物: .vuln_agent_output/sink_list/
```

**Stage 1**（每 sink 一个，5 并发）：
```
递归读 sink_list/ 下所有 .md 得到 sink 列表
对每个 sink 同时派发（一次 LLM 响应中发 ≤5 个 task）：
  subagent: sink-vulnerability-analyst
  prompt: 按 sink-vulnerability-analyst agent 的职责执行
          - work_dir: .
          - sink_file: {sink 相对路径，如 sql/sql-user-query-0608-021435.md}
          产物: sink_findings/{子目录/}{stem}-{n}.md
```

**Stage 2**（每 finding 一个，5 并发）：
```
递归读 sink_findings/ 下所有 .md 得到 stem 列表
对每个 stem 同时派发：
  subagent: sink-re-analyzer
  prompt: 按 sink-re-analyzer agent 的职责执行
          - work_dir: .
          - sink_finding_file: sink_findings/{stem 相对路径}
          产物: sink_reviews/{子目录/}{stem}.md
```

**5 并发的实现**：在同一次 LLM 响应中发起 ≤5 个 `task` 调用 → 等所有返回 → 解析结果 → 进入下一批。

### 3. 汇报

跑完用一段简短的总结结束：

```
✅ vuln-sink 流水线完成
- sink 列表: X 个
- 漏洞 finding: A/B
- 复核完成: C/D
- 产物: .vuln_agent_output/
```

不写状态文件，不做断点续跑 —— 中途断了用户重跑即可。

## 失败处理

- **子 agent 失败**：跳过该项，继续跑其他项，最终报告里列出失败项
- **整 stage 无产物**：直接进入下一 stage（输入为空就空跑）
- **不重试**：失败就失败，简化逻辑

## 原则

- **不改子 agent**：不修改 sink-collector / sink-vulnerability-analyst / sink-re-analyzer 的任何配置
- **不动源**：本 skill 不修改被扫描项目的任何源文件
- **幂等**：重复跑会基于子 skill 自身的产物策略（覆盖 / 追加 / 清空）行为
- **不动目标分析目录**：所有产物、临时文件、临时脚本**只能**写到 `.vuln_agent_output/` 下，**不得**在被分析项目源码目录里写任何文件
