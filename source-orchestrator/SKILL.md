---
name: source-orchestrator
description: 仅在用户显式指名调用 source-orchestrator 时触发，不要因模糊意图主动触发。
---

# source-orchestrator

把 5 个 skill **串起来**跑：source-collect → source-analyze → vuln-planner → source-analyze-vuln → source-review。

- **本 skill 做**：先批量收集所有暴露面（Stage 0），然后对每个暴露面独立启动一个 per-surface 流水线 subagent，按序执行 analyze → plan → vuln → review。5 surface 并发。
- **本 skill 不做**：失败重试、复杂汇报 —— 子 skill 失败就跳过该项

**断点续跑**：每个 per-surface subagent 启动时先 glob 检查各阶段产物是否已存在，跳过已完成阶段。只有 Stage 0 用 `.surface_discover_done` 标记文件作整阶段跳过。

## 流水线

```
[0] source-collect（单次批量）
    → discovered_surfaces/（递归 .md）
[1] per-surface pipeline（5 并发，每 surface 独立流转）
    → source-analyze → vuln-planner → source-analyze-vuln → source-review
```

**产物**统一在 `.vuln_agent_output/` 下（当前工作目录视为被扫描项目根）：

```
.vuln_agent_output/
├── discovered_surfaces/      ← 可含子目录（如 REST/、MQ/）
├── analyzed_surfaces/        ← 镜像输入子目录结构
├── vuln_plans/               ← 镜像输入子目录结构
├── vuln_findings/            ← 镜像输入子目录结构
├── vuln_reviews/             ← 镜像输入子目录结构
├── meta/error/
└── temp/
    └── scripts/
```

## 工作流程

### 1. 启动

用户调用 `source-orchestrator` 时，已携带用户原始任务描述。根据任务是否有明确目标入口，子 skill 可精确收集也可以全量收集。直接进入流水线，不反问。

### 2. 跑流水线

#### Stage 0 — collect（单次批量）

检查 `.surface_discover_done` 标记：

```
if [ -f .vuln_agent_output/.surface_discover_done ]; then
  跳过（已完成）
else
  派发 subagent 执行 source-collect
  subagent: source-collector
  prompt: 调用 source-collect skill
          - work_dir: .
          - task: {用户原始任务描述}
          产物: .vuln_agent_output/discovered_surfaces/
          完成信号: .vuln_agent_output/.surface_discover_done
fi
```

#### Stage 1 — per-surface pipeline（5 并发）

先列出所有 surface 和已完成（有 review 产物）的 surface，差集 = 待处理：

```
glob: .vuln_agent_output/discovered_surfaces/**/*.md
→ 全部 surface 列表（含子目录路径，如 REST/iface-REST-user-list-0608-021435.md）

glob: .vuln_agent_output/vuln_reviews/**/*.md
→ 已复核 surface 列表

对比：已复核 dir 中无对应文件的 surface = 待处理

若全部已复核 → 跳过 Stage 1
```

对每个待处理 surface，派发 per-surface pipeline subagent（一次 LLM 响应中 ≤5 个 task）。每个 subagent 执行以下完整流程：

```
subagent: source-pipeline-runner  （每 surface 一个）
prompt:
你是单条目漏洞分析流水线执行器。先 glob 检查各阶段产物，
跳过已完成阶段，只跑未完成的。

目标 surface: {surface 相对路径，如 REST/iface-REST-user-list-0608-021435.md}
工作目录: .

== 产物存在性检查（跳过逻辑） ==

检查各阶段产物：

[a] .vuln_agent_output/analyzed_surfaces/{surface 相对路径}
    存在 → 跳过 source-analyze
    不存在 → 需要跑

[b] .vuln_agent_output/vuln_plans/{stem}/*-risk-*.md
    存在 → 跳过 vuln-planner
    不存在 → 需要跑

[c] .vuln_agent_output/vuln_findings/ 下包含 {stem} 的 VULN-/NOVULN-/SUSPECTED-*.md
    存在 → 跳过 source-analyze-vuln
    不存在 → 需要跑（但只有 high/medium/low risk plan 才跑，none-risk 跳过）

[d] .vuln_agent_output/vuln_reviews/ 下包含 {stem} 的 VULN-/NOVULN-/SUSPECTED-*.md
    存在 → 跳过 source-review
    不存在 → 需要跑

（{stem} = 从文件名去掉 .md 扩展名，如 iface-REST-user-list-0608-021435）

== 阶段执行 ==

按需执行未完成的阶段，按顺序：

1. 【source-analyze】需要时调用：
   task subagent: source-analyst
   prompt: 调用 source-analyze skill
           - work_dir: .
           - surface_file: {surface 相对路径}
           产物: analyzed_surfaces/{surface 相对路径}

2. 【vuln-planner】需要时调用：
   task subagent: source-vuln-planner
   prompt: 调用 vuln-planner skill
           - work_dir: .
           - surface_file: {surface 相对路径}
           产物: vuln_plans/{stem}/

3. 【source-analyze-vuln】需要时调用：
   task subagent: source-vulnerability-analyst
   prompt: 调用 source-analyze-vuln skill
           - work_dir: .
           - input: analyzed_surfaces/{surface 相对路径}
           - vuln_plans: vuln_plans/{stem}/（有则读取）
           产物: vuln_findings/{子目录/}{stem}-{n}.md

4. 【source-review】需要时调用：
   task subagent: source-re-analyzer
   prompt: 调用 source-review skill
           - work_dir: .
           - input: vuln_findings/{对应 finding}
           产物: vuln_reviews/{子目录/}{stem}.md

每阶段完成后，不必等所有子任务结束再汇报。该 surface 全部完成后即视为完成。
```

**5 并发的实现**：在同一次 LLM 响应中发起 ≤5 个 `task` 调用（每个 surface 一个 pipeline subagent）→ 等所有返回 → 找到下一个待处理 surface 再发下一批。

### 3. 汇报

跑完用一段简短的总结结束（计数从各产物目录的 glob 结果获取）：

```
✅ vuln_hunt 流水线完成
- 暴露面: X 个
- 分析完成: A/B（失败: 失败项列表）
- 规划: X 个 / Y 个高风险
- 漏洞 finding: C 个
- 复核完成: E/F
- 产物: .vuln_agent_output/
```

**断点续跑**：重复运行会自动跳过已完成 surface（每 surface 启动时 glob 检查各阶段产物存在性）。Stage 0 额外检查 `.surface_discover_done` 标记文件。中途中断后直接重跑即可。

## 失败处理

- **子 skill 失败**：跳过该项，继续跑其他项，最终报告里列出失败项
- **整 stage 无产物**：直接进入下一 stage（输入为空就空跑）
- **不重试**：失败就失败，简化逻辑
- **断点续跑**：失败项不会自动重试。用户修复问题后重跑，per-surface subagent 启动时会 glob 检查到已完成的阶段并跳过，只处理失败的阶段

## 原则

- **不改子 skill**：不修改 5 个子 skill 的任何 `SKILL.md`
- **不动源**：本 skill 不修改被扫描项目的任何源文件
- **幂等**：重复跑会基于子 skill 自身的产物策略（覆盖 / 追加 / 清空）行为
- **不动目标分析目录**：所有产物、临时文件、临时脚本**只能**写到 `.vuln_agent_output/` 下，**不得**在被分析项目源码目录里写任何文件
