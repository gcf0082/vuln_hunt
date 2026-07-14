---
name: source-orchestrator
description: 仅在用户显式指名调用 source-orchestrator 时触发，不要因模糊意图主动触发。
---

# source-orchestrator

把 5 个 skill **串起来**跑：source-collect → source-analyze → vuln-planner → source-analyze-vuln → source-review。

- **本 skill 做**：按顺序触发子 skill，每阶段用 `glob`/`ls` 检查已完成项，跳过已完成的条目，只处理未完成部分。每阶段 5 并发。
- **本 skill 不做**：失败重试、复杂汇报 —— 子 skill 失败就跳过该项

**断点续跑**：每个阶段通过检查产物目录中文件是否存在来判断哪些条目已完成，自动跳过已完成的条目。只有 Stage 0（collect）用 `.surface_discover_done` 标记文件作整阶段跳过。

## 流水线

```
[0] source-collect
    → discovered_surfaces/（递归 .md）
[1] source-analyze  (每条目 5 并发)
    → analyzed_surfaces/（递归 .md）
[2] vuln-planner  (每条目 5 并发)
    → vuln_plans/（递归 .md 子目录）
[3] source-analyze-vuln  (每条目 5 并发)
    → vuln_findings/（递归 .md）
[4] source-review  (每条目 5 并发)
    → vuln_reviews/（递归 .md）
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

依次执行每阶段，用 `glob` 工具检查产物目录，跳过已完成条目：

**Stage 0 — collect**（单次，检查 `.surface_discover_done` 标记）：
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

**Stage 1 — analyze**（5 并发，跳过已分析 surface）：
```
glob: .vuln_agent_output/discovered_surfaces/**/*.md  → 全部 surface 列表（含子目录路径）
glob: .vuln_agent_output/analyzed_surfaces/**/*.md    → 已分析列表（子目录结构镜像）

对比两个列表：只用已分析目录中没有的文件（按相对路径匹配）
对每个未分析 surface 同时派发（一次 LLM 响应中发 ≤5 个 task）：
  subagent: source-analyst
  prompt: 调用 source-analyze skill
          - work_dir: .
          - task: {用户原始任务描述}
          - surface_file: {相对路径，如 REST/iface-REST-user-list-0608-021435.md}
          产物: analyzed_surfaces/{相对路径}
```

**Stage 2 — plan**（5 并发，跳过已规划 surface）：
```
glob: .vuln_agent_output/analyzed_surfaces/**/*.md  → 全部 analyzed stem 列表
对每个 stem（从文件名去掉 .md 扩展名）：
  检查 .vuln_agent_output/vuln_plans/{stem}/ 是否存在且包含 *-risk-*.md 文件
  存在 → 跳过（已规划）
  不存在 → 待规划

对每个待规划 stem 同时派发：
  subagent: source-vuln-planner
  prompt: 调用 vuln-planner skill
          - work_dir: .
          - task: {用户原始任务描述}
          - surface_file: {相对路径}
          产物: vuln_plans/{相对路径}/
```

**Stage 3 — vuln**（5 并发，跳过已分析 + 无风险跳过）：
```
glob: .vuln_agent_output/analyzed_surfaces/**/*.md  → 全部 analyzed stem 列表
对每个 stem：
  1. 检查 .vuln_agent_output/vuln_plans/{stem}/ 是否有 high/medium/low-risk-*.md
     - 只有 none-risk-*.md → 跳过（vuln-planner 判定无需分析）
     - 无任何 plan → 跳过（等待规划完成后再跑）
  2. 检查 .vuln_agent_output/vuln_findings/ 下是否存在包含该 stem 的 VULN-/NOVULN-/SUSPECTED-*.md 文件
     - 存在 → 跳过（已分析）
     - 不存在 → 待分析

对每个待分析 stem 同时派发：
  subagent: source-vulnerability-analyst
  prompt: 调用 source-analyze-vuln skill
          - work_dir: .
          - task: {用户原始任务描述}
          - vuln_type: {vuln_type，如 cmd/sql/path_traversal}
          - input: analyzed_surfaces/{相对路径}
          - vuln_plans: vuln_plans/{相对路径}/（有则读取）
          产物: vuln_findings/{子目录/}{stem}-{n}.md
```

**Stage 4 — review**（5 并发，跳过已复核 finding）：
```
glob: .vuln_agent_output/vuln_findings/**/*.md  → 全部 finding 列表
glob: .vuln_agent_output/vuln_reviews/**/*.md    → 已复核列表

对比两个列表：只用已复核目录中没有的文件（按同名匹配）
对每个未复核 finding 同时派发：
  subagent: source-re-analyzer
  prompt: 调用 source-review skill
          - work_dir: .
          - task: {用户原始任务描述}
          - input: vuln_findings/{相对路径}
          产物: vuln_reviews/{子目录/}{stem}.md
```

**5 并发的实现**：在同一次 LLM 响应中发起 ≤5 个 `task` 调用 → 等所有返回 → 解析结果 → 进入下一批。

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

**断点续跑**：重复运行会自动跳过已完成条目（通过 glob 检查产物存在性），只处理未完成的部分。Stage 0 额外检查 `.surface_discover_done` 标记文件。中途中断后直接重跑即可。

## 失败处理

- **子 skill 失败**：跳过该项，继续跑其他项，最终报告里列出失败项
- **整 stage 无产物**：直接进入下一 stage（输入为空就空跑）
- **不重试**：失败就失败，简化逻辑
- **断点续跑**：失败项不会自动重试。用户修复问题后重跑，LLM 会通过 glob 检查到未完成项，只处理失败的条目

## 原则

- **不改子 skill**：不修改 5 个子 skill 的任何 `SKILL.md`
- **不动源**：本 skill 不修改被扫描项目的任何源文件
- **幂等**：重复跑会基于子 skill 自身的产物策略（覆盖 / 追加 / 清空）行为
- **不动目标分析目录**：所有产物、临时文件、临时脚本**只能**写到 `.vuln_agent_output/` 下，**不得**在被分析项目源码目录里写任何文件

