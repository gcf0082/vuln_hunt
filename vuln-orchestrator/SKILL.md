---
name: vuln-orchestrator
description: 仅在用户显式指名调用 vuln-orchestrator 时触发，不要因模糊意图主动触发。
---

# vuln-orchestrator

## 定位

- **用户负责**：给出意图（跑/续/停/状态/重跑某 stage/重跑失败项），如选 start 还需提供扫扫描参数（scope/features/coverage）
- **skill 负责**：按意图解析、读 / 写 `.orchestrator-state.json`、按并发度派发 4 个子 skill、跟踪每个条目状态、汇总报告

本 skill **不**写子 skill 逻辑——子 skill 仍按各自 `SKILL.md` 工作，本 skill 只做"派发 + 状态机 + 汇报"。

## 触发与子命令

- **触发**：仅在用户显式指名调用 `vuln-orchestrator` 时启动（如 `vuln-orchestrator` / `vuln-orchestrator start` / `@vuln-orchestrator`）。**不**因"跑漏洞扫描/审计"等模糊意图自动触发
- **子命令**：启动后按 `references/intent-patterns.md` 解析用户消息的具体意图（start / resume / status / rerun-stage N / retry-failed / stop / abort）执行相应动作

## 路径约定

本 skill 涉及的所有目录**统一在 `.vuln_agent_output/` 下**（当前工作目录视为被分析项目根）：

```
.vuln_agent_output/
├── .orchestrator-state.json        ← 本 skill 状态（真理之源）
├── .collect_done                   ← generate-surface 写的完成信号
├── discovered_surfaces/            ← stage 0 产物
├── analyzed_surfaces/              ← stage 1 产物
├── vuln_findings/                  ← stage 2 产物
├── vuln_reviews/                   ← stage 3 产物
├── meta/                           ← 子 skill 错误日志
│   ├── excluded-paths.md
│   └── error/{skill-name}.md
└── temp/scripts/                   ← 临时脚本（子 skill 用）
```

## 预加载

启动时**必须**先按顺序读取（路径相对本 skill 目录 `references/`）：

1. `references/intent-patterns.md`（意图 → 动作）
2. `references/state-schema.md`（状态文件结构）
3. `references/stage-contracts.md`（各 stage 输入/输出/完成判据）
4. `references/dispatch-protocol.md`（subagent 派发、并发槽位、失败处理）
5. `references/final-report.md`（终态报告模板）

`references/vuln_rules/*.md` **不在加载范围**——子 skill 自己按需加载。

未读完这 5 个 references 不允许动笔。

## 工作流程

### 0. 解析意图

按 `references/intent-patterns.md` 把用户消息分类为：start / resume / status / rerun-stage N / retry-failed / stop / abort。

模糊时优先 `resume`（存在 `.orchestrator-state.json` 时）/ `start`（无 state 时）。

### 1. 检查状态

- 不存在 `.orchestrator-state.json`：
  - intent=start → 初始化 state（pipeline_id, current_stage=0, items 全部空）
  - intent=resume/status → 报错"无运行中的流水线，可发起 start"
- 已存在 `.orchestrator-state.json` 且 JSON 损坏 → 拒绝启动，提示用户检查或删除
- 已存在且 stage_0_params 与新 intent 的 start 参数冲突 → 反问"覆盖 start / resume / abort"

### 2. 执行动作

按 `references/dispatch-protocol.md` 派发子任务。

- **start**：
  1. 反问缺失的 stage 0 参数（scope / features / coverage / 产物策略）
  2. 初始化 state
  3. 派发 `surface-collector`（调用 `generate-surface`），参数含 scope/features/coverage/strategy
  4. 等 `.collect_done` + 列出 `discovered_surfaces/*.md`
  5. 初始化 `items.stage_1`（所有 surface 状态=pending）
  6. 进入 stage 1 派发循环
- **resume**：从 `state.current_stage` 继续；pending 和 failed 的 items 都会重跑
- **rerun-stage N**：清空 stage N 起所有 stage 的 items 状态为 pending、stage_status 为 pending
- **retry-failed**：扫描所有 stage 的 failed items，重置为 pending
- **stop**：写 `stage_status[current_stage]=paused`；orchestrator 不再发起新派发
- **abort**：写 `stage_status[*]=aborted`；当前 in-flight 视为失败
- **status**：只读 state，按 `references/final-report.md` 模板汇报

### 3. stage 1/2/3 派发循环

```
loop:
  pending_or_running = items.stage_N where status in {pending, running}
  if all ∈ {done, failed}:
    exit loop, advance to next stage
  if stop_requested:
    write paused, exit
  slots = min(concurrency - in_flight, len(pending))
  dispatch slots items as subagent (in one LLM response for parallelism)
  poll 5s; in_flight tracks subagent returns
```

每轮最多 5 个并发（通过在同一次 LLM 响应中发 ≤5 个 subagent 调用实现）。

### 4. 汇报

- 每完成一个 stage → 简短汇报"stage N done: X done, Y failed, Z total"
- 全部完成 → 按 `references/final-report.md` 出汇总报告
- 用户问 status → 任何时候可触发，按 state 给出当前进度

## 状态机

```
(no state)         → start → STAGE_0_COLLECTING
                              ↓ (.collect_done 存在 + 至少一个 .md)
                            STAGE_1_ANALYZING
                              ↓ (items 全部 ∈ {done, failed} 且 ≥1 done)
                            STAGE_2_VULN_ANALYZING
                              ↓
                            STAGE_3_REVIEWING
                              ↓
                            PIPELINE_DONE

任意 stage 收到 stop → 写 paused 标记
收到 abort → 写 aborted 标记，所有 in-flight 视为 failed
resume → 从 current_stage 继续
```

## 失败处理

- **单 item 失败**：subagent 返回 error → 重试 1 次，仍失败则 `items[stage][item].status=failed`，记 `errors[]`，继续其他 item
- **整 stage 无 done**（全部 failed）：仍推进到下一 stage（可能 stage 2 输入为空，整 stage 标 done，stage 3 同理）
- **subagent 本身调用失败**（工具层错误）：等同 item 失败处理
- **状态文件损坏**：拒绝启动，要求用户介入

## 原则

- **不改子 skill**：不修改 `generate-surface` / `analyze-surface` / `analyze-vulnerability` / `review-vuln` 任何 SKILL.md
- **状态文件是真理之源**：所有恢复/重跑/汇报都基于 `.orchestrator-state.json`
- **幂等**：重复触发"继续" / "状态" / "重跑失败"不会出问题
- **不替用户决策**：stage 0 的"清空/覆盖/追加"策略仍由用户回答（透传给 generate-surface）
- **可观测**：任何时刻用户问"状态"都能从 state 给出明确答案
- **不动源**：本 skill 不修改任何源文件、配置文件、子 skill 产物
- **失败显式标注**：每个失败项都进 `errors[]`，不静默跳过

## 不在本 skill 范围内

- 漏洞分析、风险评级、利用验证 → 子 skill 负责
- 修改源代码、加防护、加固建议 → 不在本 skill 范围
- 调度其他安全工具（如 SAST、SCA）→ 不在本 skill 范围
