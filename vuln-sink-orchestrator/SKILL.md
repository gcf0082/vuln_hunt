---
name: vuln-sink-orchestrator
description: 仅在用户显式指名调用 vuln-sink-orchestrator 时触发，不要因模糊意图主动触发。
---

# vuln-sink-orchestrator

把 3 个 sink-based skill **串起来**跑：sink_collector → sink_vuln_analyzer → review-sink-vuln。

- **本 skill 做**：按顺序触发子 skill，每阶段 5 并发
- **本 skill 不做**：状态文件、断点续跑、失败重试、复杂汇报 —— 子 skill 失败就跳过该项

## 流水线

```
[0] sink_collector                 (单次)
   → sink_list/*.md
[1] sink_vuln_analyzer  (每条目 5 并发)
   → sink_findings/*.md
[2] review-sink-vuln   (每条目 5 并发)
   → sink_reviews/*.md
```

**产物**统一在 `.vuln_agent_output/` 下（当前工作目录视为被扫描项目根）：

```
.vuln_agent_output/
├── sink_list/
├── sink_findings/
├── sink_reviews/
└── meta/error/
```

## 工作流程

### 1. 启动

用户调用 `vuln-sink-orchestrator` 时，反问 sink 类型：

> 重点关注哪些 sink 类型？如 SQL / 命令 / 文件 / 网络 / 反序列化 / 弱加密（不选则全扫）

- 用户给了具体类型（如"SQL"）→ 透传给 sink_collector
- 用户说"全部" / 没说 → 透传 all，sink_collector 全扫

scope 隐式默认当前项目目录，**不**反问。

### 2. 跑流水线

依次执行，每阶段用 `task` 工具派发 subagent：

**Stage 0**（单次）：
```
subagent: sink-collector
prompt: 调用 sink_collector skill
        - work_dir: .
        - user_intent: {用户给的 sink 类型}
        产物: .vuln_agent_output/sink_list/
```

**Stage 1**（每 sink 一个，5 并发）：
```
读 sink_list/*.md 得到 sink 列表
对每个 sink 同时派发（一次 LLM 响应中发 ≤5 个 task）：
  subagent: sink-vulnerability-analyst
  prompt: 调用 sink_vuln_analyzer skill
          - work_dir: .
          - sink_file: sink_list/{stem}.md
          产物: sink_findings/{stem}-{n}.md
```

**Stage 2**（每 finding 一个，5 并发）：
```
读 sink_findings/*.md 得到 stem 列表
对每个 stem 同时派发：
  subagent: sink-vuln-re-analyzer
  prompt: 调用 review-sink-vuln skill
          - work_dir: .
          - sink_finding_file: sink_findings/{stem}.md
          产物: sink_reviews/{stem}.md
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

- **子 skill 失败**：跳过该项，继续跑其他项，最终报告里列出失败项
- **整 stage 无产物**：直接进入下一 stage（输入为空就空跑）
- **不重试**：失败就失败，简化逻辑

## 原则

- **不改子 skill**：不修改 sink_collector / sink_vuln_analyzer / review-sink-vuln 的任何 `SKILL.md`
- **不动源**：本 skill 不修改被扫描项目的任何源文件
- **幂等**：重复跑会基于子 skill 自身的产物策略（覆盖 / 追加 / 清空）行为
