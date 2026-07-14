---
name: source-orchestrator
description: 仅在用户显式指名调用 source-orchestrator 时触发，不要因模糊意图主动触发。
---

# source-orchestrator

把 5 个 skill **串起来**跑：source-collect → source-analyze → vuln-planner → source-analyze-vuln → source-review。

- **本 skill 做**：先跑 `pipeline_state.py` 判断当前完成状态 → 跳过已完成阶段 → 按顺序触发未完成的阶段，每阶段 5 并发
- **本 skill 不做**：失败重试、复杂汇报 —— 子 skill 失败就跳过该项

**断点续跑**：pipeline_state.py 通过标记文件 + 产物存在性判断，自动从断点处恢复。重复运行只会处理未完成的阶段和条目。

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

## 预加载

启动时**必须**先读取 `references/pipeline-state.md`（路径相对本 skill 目录），然后才能开始任务。未读完不允许动笔。

## 工作流程

### 1. 获取流水线状态

先运行 `pipeline_state.py`：

```bash
python3 source-orchestrator/pipeline_state.py {work_dir}
```

输出 JSON 格式：

```json
{
  "stages": {
    "collect": {"done": false, "marker": ".collect_done"},
    "analyze": {"done": false},
    "plan": {"done": true, "marker": ".plan_done"},
    "vuln": {"done": false},
    "review": {"done": true}
  },
  "pending": {
    "collect": ["."],
    "analyze": ["REST/iface-REST-user-list-0608-021435.md"],
    "plan": [],
    "vuln": ["REST/iface-X.md"],
    "review": []
  }
}
```

根据 JSON 决策：

- **`stages.X.done` = true** → 跳过该 stage，不进入
- **`pending.X` 为空** → 跳过该 stage
- **`pending.X` 有值** → 只处理列表中的条目
- 如果所有 stage 都已 done → 直接汇报当前计数后退出

用户调用时已携带原始任务描述。根据任务是否有明确目标入口，子 skill 可精确收集也可以全量收集。

### 2. 跑流水线

依次执行每阶段，跳过已完成 stage。每阶段从 `pending.{stage}` 获取待处理条目，用 `task` 工具派发 subagent（5 并发）：

**Stage 0 — collect**（单次，仅 `stages.collect.done=false` 时运行）：
```
subagent: source-collector
prompt: 调用 source-collect skill
        - work_dir: .
        - task: {用户原始任务描述}
        产物: .vuln_agent_output/discovered_surfaces/
        完成信号: .vuln_agent_output/.collect_done
```

**Stage 1 — analyze**（仅 `pending.analyze` 非空时运行，5 并发）：
```
对 pending.analyze 中每个相对路径同时派发：
  subagent: source-analyst
  prompt: 调用 source-analyze skill
          - work_dir: .
          - task: {用户原始任务描述}
          - surface_file: {相对路径，如 REST/iface-REST-user-list-0608-021435.md}
          产物: analyzed_surfaces/{相对路径}
```

**Stage 2 — plan**（仅 `pending.plan` 非空时运行，5 并发）：
```
对 pending.plan 中每个相对路径同时派发：
  subagent: source-vuln-planner
  prompt: 调用 vuln-planner skill
          - work_dir: .
          - task: {用户原始任务描述}
          - surface_file: {相对路径，如 REST/iface-REST-user-list-0608-021435.md}
          产物: vuln_plans/{相对路径}/
```

**Stage 3 — vuln**（仅 `pending.vuln` 非空时运行，5 并发）：
```
对 pending.vuln 中每个相对路径同时派发：
  subagent: source-vulnerability-analyst
  prompt: 调用 source-analyze-vuln skill
          - work_dir: .
          - task: {用户原始任务描述}
          - vuln_type: {vuln_type，如 cmd/sql/path_traversal}
          - input: analyzed_surfaces/{相对路径}
          - vuln_plans: vuln_plans/{相对路径}/（可选，有则读取）
          产物: vuln_findings/{子目录/}{stem}-{n}.md
```

**Stage 4 — review**（仅 `pending.review` 非空时运行，5 并发）：
```
对 pending.review 中每个相对路径同时派发：
  subagent: source-re-analyzer
  prompt: 调用 source-review skill
          - work_dir: .
          - task: {用户原始任务描述}
          - input: vuln_findings/{相对路径}
          产物: vuln_reviews/{子目录/}{stem}.md
```

**5 并发的实现**：在同一次 LLM 响应中发起 ≤5 个 `task` 调用 → 等所有返回 → 解析结果 → 进入下一批。

### 3. 汇报

跑完用一段简短的总结结束，优先从 `pipeline_state.py` 的 `counts` 字段获取数据：

```
✅ vuln_hunt 流水线完成（断点续跑）
- 暴露面: X 个
- 分析完成: A/B（失败: 失败项列表）
- 规划: X 个 / Y 个高风险
- 漏洞 finding: C 个
- 复核完成: E/F
- 产物: .vuln_agent_output/
```

**断点续跑**：因为 `pipeline_state.py` 通过标记文件 + 产物存在性判断运行状态，重复运行流水线会自动跳过已完成阶段，只处理未完成的部分。中途中断后直接重跑即可。

## 失败处理

- **子 skill 失败**：跳过该项，继续跑其他项，最终报告里列出失败项
- **整 stage 无产物**：直接进入下一 stage（输入为空就空跑）
- **不重试**：失败就失败，简化逻辑
- **断点续跑**：失败项不会自动重试。用户修复问题后重跑同一个命令，`pipeline_state.py` 会识别未完成项，只处理失败的条目

## 原则

- **不改子 skill**：不修改 5 个子 skill 的任何 `SKILL.md`
- **不动源**：本 skill 不修改被扫描项目的任何源文件
- **幂等**：重复跑会基于子 skill 自身的产物策略（覆盖 / 追加 / 清空）行为
- **不动目标分析目录**：所有产物、临时文件、临时脚本**只能**写到 `.vuln_agent_output/` 下，**不得**在被分析项目源码目录里写任何文件

