# vuln-orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `vuln-orchestrator` skill that orchestrates the existing 4-stage vuln_hunt pipeline (generate-surface → analyze-surface → analyze-vulnerability → review-vuln) with state tracking, concurrent dispatch, and resumability.

**Architecture:** A single new skill (`/root/projects/vuln_hunt/vuln-orchestrator/`) that is loaded as an opencode skill. When triggered, the orchestrator LLM reads the 5 reference files, parses user intent, manages a state file at `.vuln_agent_output/.orchestrator-state.json`, and dispatches subagents (`surface-collector` / `surface-analyst` / `vulnerability-analyst` / `vuln-re-analyzer`) to invoke the 4 existing skills. No existing skill is modified.

**Tech Stack:** opencode skills (Markdown + YAML frontmatter), JSON state file, subagent dispatch via `task` tool, no git (vuln_hunt is not a git repo — validation steps replace commit steps).

---

## File Structure

**Create:**

| File | Responsibility |
|---|---|
| `vuln_hunt/vuln-orchestrator/SKILL.md` | Main entry: frontmatter (name, 显式调用 description), 定位, 触发与子命令, 路径约定, 预加载, 工作流程, 状态机, 失败处理, 原则 |
| `vuln_hunt/vuln-orchestrator/references/intent-patterns.md` | Natural-language intent → control action mapping (7 intents) |
| `vuln_hunt/vuln-orchestrator/references/state-schema.md` | `.orchestrator-state.json` complete schema + field definitions |
| `vuln_hunt/vuln-orchestrator/references/stage-contracts.md` | Per-stage input/output/completion criteria for stages 0-3 |
| `vuln_hunt/vuln-orchestrator/references/dispatch-protocol.md` | Subagent types, prompt templates, concurrency slot control, retry rules |
| `vuln_hunt/vuln-orchestrator/references/final-report.md` | Report templates (per-stage progress, full done, status) |
| `vuln_hunt/vuln-orchestrator/tools/validate-skill.py` | Standalone validator: parses YAML frontmatter, checks required sections, verifies file references resolve |
| `vuln_hunt/vuln-orchestrator/tools/sample-state.json` | Reference state file example for validator self-test |

**Do NOT modify:**
- `vuln_hunt/generate_surface/SKILL.md`
- `vuln_hunt/analyze-surface/SKILL.md`
- `vuln_hunt/surface_vuln_analyzer/SKILL.md`
- `vuln_hunt/review-vuln/SKILL.md`
- Any file under `.vuln_agent_output/`

---

## Task 1: Create directory structure

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/` (directory)
- Create: `vuln_hunt/vuln-orchestrator/references/` (directory)
- Create: `vuln_hunt/vuln-orchestrator/tools/` (directory)

- [ ] **Step 1: Create the three directories**

Run:
```bash
mkdir -p /root/projects/vuln_hunt/vuln-orchestrator/references
mkdir -p /root/projects/vuln_hunt/vuln-orchestrator/tools
```

- [ ] **Step 2: Verify directories exist**

Run:
```bash
ls -la /root/projects/vuln_hunt/vuln-orchestrator/
```

Expected output (line counts may differ):
```
drwxr-xr-x references
drwxr-xr-x tools
```

---

## Task 2: Create SKILL.md

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/SKILL.md`

- [ ] **Step 1: Write SKILL.md with frontmatter and main body**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/SKILL.md`:

```markdown
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

\`\`\`
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
\`\`\`

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

\`\`\`
loop:
  pending_or_running = items.stage_N where status in {pending, running}
  if all ∈ {done, failed}:
    exit loop, advance to next stage
  if stop_requested:
    write paused, exit
  slots = min(concurrency - in_flight, len(pending))
  dispatch slots items as subagent (in one LLM response for parallelism)
  poll 5s; in_flight tracks subagent returns
\`\`\`

每轮最多 5 个并发（通过在同一次 LLM 响应中发 ≤5 个 subagent 调用实现）。

### 4. 汇报

- 每完成一个 stage → 简短汇报"stage N done: X done, Y failed, Z total"
- 全部完成 → 按 `references/final-report.md` 出汇总报告
- 用户问 status → 任何时候可触发，按 state 给出当前进度

## 状态机

\`\`\`
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
\`\`\`

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
```

Note: the code blocks inside (e.g., for state machine and 派发循环) use escaped backticks `\`` ` ` in the YAML/markdown to avoid nesting issues. When writing, replace each `\`` ` with a literal triple-backtick block.

- [ ] **Step 2: Verify file created with correct frontmatter**

Run:
```bash
head -5 /root/projects/vuln_hunt/vuln-orchestrator/SKILL.md
```

Expected output (first 4 lines):
```
---
name: vuln-orchestrator
description: 仅在用户显式指名调用 vuln-orchestrator 时触发，不要因模糊意图主动触发。
```

- [ ] **Step 3: Verify file size and section count**

Run:
```bash
wc -l /root/projects/vuln_hunt/vuln-orchestrator/SKILL.md
grep -c '^## ' /root/projects/vuln_hunt/vuln-orchestrator/SKILL.md
```

Expected: ~152 lines, ≥9 `##` section headers (定位, 触发与子命令, 路径约定, 预加载, 工作流程, 状态机, 失败处理, 原则, 不在本 skill 范围内).

---

## Task 3: Create intent-patterns.md

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/references/intent-patterns.md`

- [ ] **Step 1: Write intent-patterns.md**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/references/intent-patterns.md`:

```markdown
# 子命令模式（启动后内部使用）

> **重要**：本表是用户**显式调用 `vuln-orchestrator` 之后**，LLM 对用户后续消息的意图分类规则。**不是** skill 的自动触发条件。
>
> vuln-orchestrator 的触发见 `SKILL.md` frontmatter description："仅在用户显式指名调用 vuln-orchestrator 时触发"。

LLM 在 vuln-orchestrator 启动后第一件事：分类用户当前消息的子命令。

## 分类规则

按以下顺序匹配（命中即返回）：

| 类别 | 触发短语（任一） | 动作 |
|---|---|---|
| **start** | "跑" / "扫描" / "审计" / "一键" / "流水线" / "vuln" / 无明确上下文（无 `.orchestrator-state.json`） | 从 stage 0 开始 |
| **resume** | "继续" / "接着" / "go on" / "resume" / "go" | 从 `state.current_stage` 继续 |
| **status** | "状态" / "进度" / "到哪了" / "status" / "看看" | 只读 state 汇报 |
| **rerun-stage N** | "从 stage N 重新跑" / "rerun N" / "重新跑 stage N" / "stage N 重来" | 重置 stage N 起的状态 |
| **retry-failed** | "重跑失败的" / "retry failed" / "重试失败" | 扫描所有 failed items 重置 |
| **stop** | "停" / "暂停" / "pause" / "先停" / "等一下" | 写 paused，不发新任务 |
| **abort** | "取消" / "abort" / "别跑了" / "终止" / "放弃" | 写 aborted，in-flight 视为 failed |

## 模糊时的优先级

1. 用户消息含明确"重新 / 再来 / rerun" → `rerun-stage` 或 `retry-failed`
2. 用户消息含明确"继续 / resume" → `resume`
3. 用户消息含明确"停 / abort" → `stop` 或 `abort`
4. 已存在 `.orchestrator-state.json` 且 current_stage < done → 隐式 `resume`
5. 不存在 state 文件或 current_stage = done → `start`

## 反问场景

仅在 start 意图下反问，且**仅问缺失的字段**：

| 缺失字段 | 反问 |
|---|---|
| scope | "扫哪个项目？给出目录路径或 git URL" |
| features | "关注哪些暴露面类型？如 REST、MQ、gRPC、CRON、CLI" |
| coverage | "覆盖度？full（全部）/ sample（抽样）/ 特定子集" |
| `.vuln_agent_output/` 已有产物 | "发现已有产物。选策略：(a) 先清空再生成 (b) 覆盖同名 (c) 追加" |

已存在的 state 文件 + 新 start 意图参数冲突 → "已有进行中的流水线（params: ...）。本次 params: ...。选 (a) 覆盖 start (b) resume (c) abort"

## 常见误识别

- "看看" 不一定都是 status——结合上下文：
  - "看看结果" / "看看产物" → status
  - "看看代码" / "看看文件" → 不是本 skill
- "继续" 不一定都是 resume——结合上下文：
  - "继续跑" / "继续扫描" → resume（前提是有 state）
  - "继续刚才的话题" → 不是本 skill

LLM 需结合整体对话上下文判断。
```

- [ ] **Step 2: Verify table has 7 intent rows**

Run:
```bash
grep -c '^| \*\*' /root/projects/vuln_hunt/vuln-orchestrator/references/intent-patterns.md
```

Expected: 7 (one for each intent).

---

## Task 4: Create state-schema.md

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/references/state-schema.md`

- [ ] **Step 1: Write state-schema.md**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/references/state-schema.md`:

```markdown
# 状态文件 Schema

**文件路径**：`.vuln_agent_output/.orchestrator-state.json`（当前工作目录下）

**读写责任**：仅 vuln-orchestrator 写。子 skill 不读不写此文件。

## 完整 Schema

\`\`\`json
{
  "$schema": "vuln-orchestrator/state-v1",
  "pipeline_id": "uuid-v4",
  "schema_version": "1.0",

  "started_at": "2026-06-07T14:30:00Z",
  "last_updated_at": "2026-06-07T14:35:22Z",
  "finished_at": null,

  "concurrency": 5,

  "current_stage": 1,
  "overall_status": "running",

  "stage_status": {
    "0": "done",
    "1": "running",
    "2": "pending",
    "3": "pending"
  },

  "stage_0_params": {
    "scope": "/path/to/project",
    "features": "REST + MQ + Cron",
    "coverage": "full",
    "strategy": "clear"
  },

  "stage_0_result": {
    "surfaces": ["iface-REST-user-list", "noniface-CRON-daily-cleanup"],
    "count": 2
  },

  "items": {
    "stage_1": {
      "iface-REST-user-list": {
        "status": "done",
        "input": "iface-REST-user-list.md",
        "output": "iface-REST-user-list.md",
        "started_at": "2026-06-07T14:31:00Z",
        "finished_at": "2026-06-07T14:33:15Z",
        "error": null,
        "retry_count": 0
      },
      "noniface-CRON-daily-cleanup": {
        "status": "failed",
        "input": "noniface-CRON-daily-cleanup.md",
        "output": null,
        "started_at": "2026-06-07T14:31:00Z",
        "finished_at": "2026-06-07T14:32:05Z",
        "error": "subagent dispatch timeout after 30min",
        "retry_count": 1
      }
    },
    "stage_2": {
      "iface-REST-user-list": {
        "status": "pending",
        "input": "iface-REST-user-list.md",
        "output": null,
        "started_at": null,
        "finished_at": null,
        "error": null,
        "retry_count": 0,
        "findings_count": null
      }
    },
    "stage_3": {
      "VULN-iface-REST-user-list-1": {
        "status": "pending",
        "input": "VULN-iface-REST-user-list-1.md",
        "output": null,
        "started_at": null,
        "finished_at": null,
        "error": null,
        "retry_count": 0
      }
    }
  },

  "errors": [
    {
      "stage": 1,
      "item": "noniface-CRON-daily-cleanup",
      "error": "subagent dispatch timeout after 30min",
      "timestamp": "2026-06-07T14:32:05Z"
    }
  ],

  "summary": {
    "stage_0_surfaces_count": 2,
    "stage_1_done": 1, "stage_1_failed": 1,
    "stage_2_done": 0, "stage_2_failed": 0,
    "stage_3_done": 0, "stage_3_failed": 0
  }
}
\`\`\`

## 字段定义

| 字段 | 类型 | 说明 |
|---|---|---|
| `pipeline_id` | uuid-v4 | 唯一标识一次流水线运行 |
| `schema_version` | "1.0" | 本文件 schema 版本，便于未来迁移 |
| `started_at` | ISO 8601 | 首次 start 触发时间 |
| `last_updated_at` | ISO 8601 | 任何字段变更时更新 |
| `finished_at` | ISO 8601 \| null | PIPELINE_DONE 时填入 |
| `concurrency` | int | 每 stage 内最大并发数，默认 5 |
| `current_stage` | int 0-3 \| "done" | 当前执行到哪个 stage |
| `overall_status` | string | pending / running / done / aborted |
| `stage_status` | object {0..3: string} | 每 stage 状态：pending / running / done / failed / paused / aborted |
| `stage_0_params` | object | 用户给 stage 0 的收集参数 |
| `stage_0_result.surfaces` | string[] | stage 0 产出的 surface slug 列表 |
| `items.stage_N` | object | stage N 的每个 item 一条记录 |
| `items[].status` | string | pending / running / done / failed |
| `items[].input` | string | 输入文件路径（相对 work_dir） |
| `items[].output` | string \| null | 输出文件路径（成功后填入） |
| `items[].error` | string \| null | 错误消息 |
| `items[].retry_count` | int | 已重试次数 |
| `items[].findings_count` | int \| null | 仅 stage 2：产出的 findings 数量 |
| `errors[]` | array | 所有失败项的汇总（与 items 互补） |
| `summary` | object | 计数统计，便于快速汇报 |

## 写入时机

- **state 初始化**：start 触发时写
- **item 状态变更**：每完成一个 subagent dispatch → 立即更新对应 item + last_updated_at
- **stage 状态变更**：stage 进入时 running、退出时 done/failed → 立即更新
- **每轮派发前**：写一次 last_updated_at
- **PIPELINE_DONE**：写 finished_at + overall_status=done

## 损坏处理

如果文件存在但 JSON parse 失败，vuln-orchestrator **必须**：
1. 拒绝启动
2. 提示用户："状态文件 `.orchestrator-state.json` JSON 损坏，无法解析。请检查文件内容或选择删除后重试。"
3. **不要**自动删除或覆盖损坏文件

## 迁移

未来 schema 变更时（`schema_version` 不匹配当前 LLM 加载的版本）：
- 读取时检测不匹配
- 提示用户："状态文件 schema 版本 X.Y 与本 skill 不兼容，请删除后重跑"
```

Note: replace the literal `\`` ` ` with triple-backtick blocks when writing.

- [ ] **Step 2: Verify JSON example block is well-formed**

Run:
```bash
grep -c '"pipeline_id"' /root/projects/vuln_hunt/vuln-orchestrator/references/state-schema.md
```

Expected: ≥1 (the example contains this field).

---

## Task 5: Create stage-contracts.md

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/references/stage-contracts.md`

- [ ] **Step 1: Write stage-contracts.md**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/references/stage-contracts.md`:

```markdown
# Stage 契约

每个 stage 的输入、输出、完成判据。

## Stage 0: generate-surface

| 字段 | 内容 |
|---|---|
| 调用的 skill | `generate-surface` |
| 派发的 subagent | `surface-collector` |
| 输入参数 | scope (string), features (string), coverage (string), strategy (string) |
| 输入产物 | 无 |
| 输出产物 | `{work_dir}/.vuln_agent_output/discovered_surfaces/*.md` |
| 完成判据 | `.vuln_agent_output/.collect_done` 存在 **且** `discovered_surfaces/` 至少一个 `*.md` |
| 特殊情况 | 0 个 surface → 不推进，提示用户 |

**派发参数模板**（给 surface-collector）：

\`\`\`
scope: {stage_0_params.scope}
features: {stage_0_params.features}
coverage: {stage_0_params.coverage}
strategy: {stage_0_params.strategy}  # clear/overwrite/append
work_dir: .  # 当前工作目录（subagent 继承 cwd）
\`\`\`

## Stage 1: analyze-surface

| 字段 | 内容 |
|---|---|
| 调用的 skill | `analyze-surface` |
| 派发的 subagent | `surface-analyst` |
| 输入参数 | surface_file (string), work_dir (string), extra_prompt (optional) |
| 输入产物 | `discovered_surfaces/{slug}.md` |
| 输出产物 | `analyzed_surfaces/{slug}.md`（同名） |
| 完成判据 | `items.stage_1[*].status` 全部 ∈ {done, failed}，且至少一个 done |
| 失败判据 | 输出文件不存在 或 subagent 返回 error |

**派发参数模板**（给 surface-analyst）：

\`\`\`
surface_file: {items.stage_1[slug].input}
work_dir: .  # 当前工作目录（subagent 继承 cwd）
extra_prompt: {用户传入 or null}
\`\`\`

**item 初始化**（stage 0 完成后）：

\`\`\`json
"stage_1": {
  "<slug>": {
    "status": "pending",
    "input": "<slug>.md",
    "output": null,
    "error": null
  }
}
\`\`\`

## Stage 2: analyze-vulnerability

| 字段 | 内容 |
|---|---|
| 调用的 skill | `surface_vuln_analyzer`（frontmatter name: `analyze-vulnerability`） |
| 派发的 subagent | `vulnerability-analyst` |
| 输入参数 | surface_file (string), work_dir (string), vuln_rules (list, optional), extra_prompt (optional) |
| 输入产物 | `analyzed_surfaces/{slug}.md` |
| 输出产物 | `vuln_findings/{VULN\|DISMISSED\|CLEAN\|SUSPECTED}-{slug}-{n}.md`（**多个**） |
| 完成判据 | `items.stage_2[*].status` 全部 ∈ {done, failed}，且至少一个 done |
| 失败判据 | 任何 subagent 返回 error |
| 产物计数 | `findings_count` = `ls vuln_findings/ | grep {slug} | wc -l` |

**派发参数模板**（给 vulnerability-analyst）：

\`\`\`
surface_file: {items.stage_2[slug].input}
work_dir: .  # 当前工作目录（subagent 继承 cwd）
vuln_rules: {用户指定 or 全 13 类}
extra_prompt: {用户传入 or null}
\`\`\`

**item 初始化**（stage 1 完成后，对每个 stage 1 done 的 slug）：

\`\`\`json
"stage_2": {
  "<slug>": {
    "status": "pending",
    "input": "<slug>.md",
    "output": null,
    "error": null,
    "findings_count": null
  }
}
\`\`\`

## Stage 3: review-vuln

| 字段 | 内容 |
|---|---|
| 调用的 skill | `review-vuln` |
| 派发的 subagent | `vuln-re-analyzer` |
| 输入参数 | vuln_file (string), work_dir (string), extra_prompt (optional) |
| 输入产物 | `vuln_findings/{prefix}-{slug}-{n}.md` |
| 输出产物 | `vuln_reviews/{VULN\|NOVULN\|SUSPECTED}-{vuln_stem}.md`（1 对 1） |
| 完成判据 | `items.stage_3[*].status` 全部 ∈ {done, failed} |
| 失败判据 | 任何 subagent 返回 error |

**item 初始化**（stage 2 完成后，对每个 finding）：

\`\`\`json
"stage_3": {
  "<vuln_stem>": {
    "status": "pending",
    "input": "<vuln_stem>.md",
    "output": null,
    "error": null
  }
}
\`\`\`

注意：vuln_stem 是 finding 文件名去掉扩展名（如 `VULN-iface-REST-user-list-1`）。

## 衔接校验

进入下一 stage 前必须确认：

- 当前 stage 全部 done 或 failed
- 当前 stage 至少一个 done（否则下一 stage 输入为空）
- 失败项已记入 `errors[]`

如果当前 stage 全部 failed：
- 仍推进（继续走完流水线，stage 2/3 可能输入为空）
- 最终报告里明确标注"stage N 全部失败，无产物进入下一 stage"
```

Note: replace the literal `\`` ` ` with triple-backtick blocks when writing.

- [ ] **Step 2: Verify 4 stage sections present**

Run:
```bash
grep -c '^## Stage' /root/projects/vuln_hunt/vuln-orchestrator/references/stage-contracts.md
```

Expected: 4 (one per stage).

---

## Task 6: Create dispatch-protocol.md

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/references/dispatch-protocol.md`

- [ ] **Step 1: Write dispatch-protocol.md**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/references/dispatch-protocol.md`:

```markdown
# Subagent 派发协议

## 派发工具

使用 opencode 的 `task` 工具派发 subagent。每次 `task` 调用 = 启动一个 subagent = 一次 LLM 调用。

**关键**：在**同一次 LLM 响应中**发起多个 `task` 调用 = 并行执行。所以 5 并发 = 在一个响应中发 ≤5 个 task。

## Subagent 类型映射

| Stage | 派发方 (subagent_type) | 用途 |
|---|---|---|
| 0 | `surface-collector` | 调用 generate-surface，列出 discovered_surfaces/ |
| 1 | `surface-analyst` | 调用 analyze-surface，单条目 |
| 2 | `vulnerability-analyst` | 调用 analyze-vulnerability，单条目 |
| 3 | `vuln-re-analyzer` | 调用 review-vuln，单条目 |

## 派发 Prompt 模板

### Stage 0 派发（surface-collector）

\`\`\`
调用 generate-surface skill 完成暴露面收集。

工作目录: {work_dir}
- scope: {stage_0_params.scope}
- features: {stage_0_params.features}
- coverage: {stage_0_params.coverage}
- strategy: {stage_0_params.strategy}  # clear/overwrite/append

完成信号: {work_dir}/.vuln_agent_output/.collect_done 存在
产物位置: {work_dir}/.vuln_agent_output/discovered_surfaces/

完成后请报告:
1. 收集到的 surface 总数
2. 每个生成的 surface 文件路径
3. 是否遇到歧义或可疑点
\`\`\`

### Stage 1 派发（surface-analyst）

\`\`\`
调用 analyze-surface skill 分析单个攻击面。

工作目录: {work_dir}
surface_file: {items.stage_1[slug].input}
(完整路径: {work_dir}/.vuln_agent_output/discovered_surfaces/{slug}.md)
extra_prompt: {用户传入 or 无}

完成后请报告:
1. 产物路径（{work_dir}/.vuln_agent_output/analyzed_surfaces/{slug}.md）
2. 流程图是否生成
3. 是否存在"未能追溯的引用"
4. 任何 error（写到 {work_dir}/.vuln_agent_output/meta/error/analyze-surface.md）
\`\`\`

### Stage 2 派发（vulnerability-analyst）

\`\`\`
调用 analyze-vulnerability skill（skill 名 surface_vuln_analyzer）做漏洞分析。

工作目录: {work_dir}
surface_file: {items.stage_2[slug].input}
(完整路径: {work_dir}/.vuln_agent_output/analyzed_surfaces/{slug}.md)
vuln_rules: {用户指定 or "all 13"}
extra_prompt: {用户传入 or 无}

完成后请报告:
1. 产出的 findings 数量 + 各自路径
2. 按档位分类（VULN / DISMISSED / CLEAN / SUSPECTED）的数量
3. 任何 error
\`\`\`

### Stage 3 派发（vuln-re-analyzer）

\`\`\`
调用 review-vuln skill 审查单个漏洞结论。

工作目录: {work_dir}
vuln_file: {items.stage_3[vuln_stem].input}
(完整路径: {work_dir}/.vuln_agent_output/vuln_findings/{vuln_stem}.md)
extra_prompt: {用户传入 or 无}

完成后请报告:
1. 审查产物路径（{work_dir}/.vuln_agent_output/vuln_reviews/{VULN|NOVULN|SUSPECTED}-{vuln_stem}.md）
2. 审查结论
3. 任何 error
\`\`\`

## 并发槽位控制

每轮派发循环：

\`\`\`
in_flight = 0
slots = concurrency  # 默认 5

while True:
    pending_items = [items for items if status == 'pending']
    if not pending_items:
        break

    batch = pending_items[:slots - in_flight]
    if not batch:
        # 等待 in_flight 完成（通过 LLM 等待 subagent 返回实现）
        break

    # 在同一次 LLM 响应中发起 batch.size 个 task 调用
    for item in batch:
        dispatch_task(item)

    # 等所有 task 返回（subagent 返回即 LLM 继续）
    # 然后解析每个 task 的结果，更新 state
    in_flight = 0
\`\`\`

实际操作：LLM 在一次响应中发 N 个 task → 等所有返回 → 在下一次响应中处理结果 + 发起下一批。

## 超时与重试

- **单 subagent 超时**：默认 30 分钟（`task` 工具的默认超时）。可在派发时显式指定 `timeout` 参数。
- **失败重试**：subagent 返回 error → 标记 `retry_count += 1` → 下次派发循环再次尝试（最多 1 次额外重试 = 共 2 次机会）
- **subagent 本身崩溃**（工具层错误）：等同失败处理

## 派发失败 vs 逻辑失败

| 失败类型 | 表现 | 处理 |
|---|---|---|
| subagent 启动失败 | task 调用直接 error | retry_count += 1，重试 |
| subagent 运行时报错 | task 返回 error 字段 | retry_count += 1，重试 |
| subagent 产出格式不对 | 产物文件缺失 | 视同 failed，重试 |
| subagent 产出 VULN 但代码不支持 | 不是本 skill 关心的事 | 不重试 |

## 收集子任务返回

每个 task 返回后，LLM 解析返回内容：
- 成功：从返回中提取产物路径 → 更新 `items[].output`
- 失败：从返回中提取 error → 更新 `items[].error`

## 状态文件原子写

为避免并发写损坏，建议 LLM 在每次更新 state 时：
1. 读整个 state.json
2. 内存中修改
3. 写整个 state.json（覆盖）

由于 LLM 串行处理 task 返回（每次 LLM 响应处理完才进入下一次），实际不存在并发写。如果未来 subagent 改成真正并发，需要加文件锁。
```

Note: replace the literal `\`` ` ` with triple-backtick blocks when writing.

- [ ] **Step 2: Verify all 4 subagent types are mentioned**

Run:
```bash
grep -E '^\| [0-3] \|' /root/projects/vuln_hunt/vuln-orchestrator/references/dispatch-protocol.md | wc -l
```

Expected: 4 (one row per stage with subagent mapping).

---

## Task 7: Create final-report.md

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/references/final-report.md`

- [ ] **Step 1: Write final-report.md**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/references/final-report.md`:

```markdown
# 终态报告

vuln-orchestrator 在以下时机产出报告：
- 用户调用 `status` 意图
- 整个流水线 `PIPELINE_DONE`
- 单个 stage 完成（简短进度报告）

## 单 Stage 进度报告

\`\`\`
✅ Stage 1 (analyze-surface) 完成
- 总数: 23
- 成功: 22
- 失败: 1
- 失败项: iface-REST-payment-callback (subagent timeout)
- 耗时: 4m 12s

进入 Stage 2 ...
\`\`\`

## PIPELINE_DONE 完整报告

\`\`\`markdown
# Vuln Hunt Pipeline 报告

**Pipeline ID**: {pipeline_id}
**开始时间**: {started_at}
**完成时间**: {finished_at}
**耗时**: {duration}（人话: "2 小时 15 分"）
**最终状态**: ✅ DONE

---

## 阶段总览

| Stage | 名称 | 状态 | 总数 | 成功 | 失败 |
|---|---|---|---|---|---|
| 0 | generate-surface | ✅ done | 1 | 1 | 0 |
| 1 | analyze-surface | ✅ done | 23 | 22 | 1 |
| 2 | analyze-vulnerability | ✅ done | 22 | 20 | 2 |
| 3 | review-vuln | ✅ done | 45 | 43 | 2 |

---

## 漏洞分析结论（按 surface 聚合）

### iface-REST-user-list
- 确认漏洞: 2（VULN-iface-REST-user-list-1.md, VULN-iface-REST-user-list-3.md）
- 排除: 5
- 干净: 8
- 疑似: 1
- 审查结论: 2 VULN / 0 NOVULN / 0 SUSPECTED

### noniface-CRON-daily-cleanup
- 确认漏洞: 0
- 排除: 3
- 干净: 1
- 疑似: 0
- 审查结论: 0 VULN / 0 NOVULN / 0 SUSPECTED

### iface-MQ-order-event
- 确认漏洞: 1
- 排除: 2
- 干净: 4
- 疑似: 0
- 审查结论: 1 VULN / 0 NOVULN / 0 SUSPECTED

... (每个 surface 一节，按 VULN 数量降序)

---

## 失败项汇总

| Stage | Item | 错误 | 时间 |
|---|---|---|---|
| 1 | iface-REST-payment-callback | subagent timeout after 30min | 2026-06-07T14:35:22Z |
| 2 | iface-MQ-order-event | LLM API rate limit | 2026-06-07T15:01:10Z |

修复后可调用 "重跑失败的" 触发 retry-failed。

---

## 产物路径

- discovered_surfaces/: 23 个文件
- analyzed_surfaces/: 22 个文件
- vuln_findings/: 45 个文件
- vuln_reviews/: 43 个文件
- 完整状态: {work_dir}/.vuln_agent_output/.orchestrator-state.json

---

## 关键 VULN 列表（审查后确认）

| Surface | 漏洞标题 | CVSS | 位置 |
|---|---|---|---|
| iface-REST-user-list | SQL injection in /api/users search | 9.8 | UserController.java:48 |
| iface-MQ-order-event | 反序列化漏洞 | 8.1 | OrderEventConsumer.java:31 |

（仅列审查后 VULN 结论的，按 CVSS 降序）
\`\`\`

## status 报告（中间状态）

\`\`\`markdown
# Vuln Hunt Pipeline 状态

**Pipeline ID**: {pipeline_id}
**当前 Stage**: 2 (analyze-vulnerability)
**整体状态**: 🔄 running

## 各 Stage 进度

| Stage | 状态 | 进度 |
|---|---|---|
| 0 | ✅ done | 1/1 (100%) |
| 1 | ✅ done | 22/23 (96%) — 1 failed |
| 2 | 🔄 running | 12/22 (55%) — 10 in flight, 0 done yet |
| 3 | ⏳ pending | 0/45 |

## 当前 in-flight 任务

- iface-MQ-order-event (stage 2)
- iface-REST-payment-create (stage 2)
- iface-MQ-inventory-update (stage 2)
- iface-REST-search (stage 2)
- iface-REST-file-upload (stage 2)

## 失败项

| Stage | Item | 错误 |
|---|---|---|
| 1 | iface-REST-payment-callback | subagent timeout |

## 下一步

继续 stage 2，预计还需 ~15 分钟。
\`\`\`

## 报告生成规则

LLM 在生成报告时**按需读产物文件**，但**不打开每个 finding 的内容**——只读文件名前缀和必要的元数据（已在 `state.summary` 缓存）。

- 单 stage 完成时：LLM 从 `state.items[stage_N]` 直接生成
- PIPELINE_DONE 时：LLM 读 `state.summary` 生成全报告
- 关键 VULN 列表：LLM 扫 `vuln_reviews/VULN-*.md` 文件名（不读内容），从文件名取 surface slug + 序号，按 CVSS 排序需要读文件——这一步骤**可选**，LLM 可仅按数量排序

## 报告输出位置

报告**不写入文件**——直接以文本形式在对话中输出。

如需持久化，用户可说"把报告保存到 {path}"，LLM 再写文件。
```

Note: replace the literal `\`` ` ` with triple-backtick blocks when writing.

- [ ] **Step 2: Verify 3 report templates present**

Run:
```bash
grep -c '^## ' /root/projects/vuln_hunt/vuln-orchestrator/references/final-report.md
```

Expected: ≥3 (单 Stage 进度报告, PIPELINE_DONE 完整报告, status 报告（中间状态）).

---

## Task 8: Create the skill validator

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/tools/validate-skill.py`

- [ ] **Step 1: Write validate-skill.py**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/tools/validate-skill.py`:

```python
#!/usr/bin/env python3
"""
vuln-orchestrator skill validator.

Checks:
1. SKILL.md exists and has valid YAML frontmatter
2. Frontmatter has required fields: name, description
3. All 5 references files exist
4. All file references in SKILL.md (references/*.md) actually exist on disk
5. Description is non-empty
6. Section headers in SKILL.md follow the structure
"""
import sys
import re
import yaml
from pathlib import Path

REQUIRED_REFERENCES = [
    "intent-patterns.md",
    "state-schema.md",
    "stage-contracts.md",
    "dispatch-protocol.md",
    "final-report.md",
]

REQUIRED_SKILL_SECTIONS = [
    "定位",
    "路径约定",
    "预加载",
    "工作流程",
    "状态机",
    "失败处理",
    "原则",
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"WARN: {msg}")


def ok(msg: str) -> None:
    print(f"OK:   {msg}")


def main(skill_dir: str = ".") -> int:
    skill_path = Path(skill_dir)
    skill_md = skill_path / "SKILL.md"

    if not skill_md.exists():
        fail(f"SKILL.md not found at {skill_md}")

    content = skill_md.read_text(encoding="utf-8")

    # 1. Parse YAML frontmatter
    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not m:
        fail("SKILL.md missing YAML frontmatter (--- ... ---)")

    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        fail(f"YAML frontmatter parse error: {e}")

    ok("YAML frontmatter parsed")

    # 2. Required fields
    if "name" not in fm:
        fail("frontmatter missing 'name'")
    if "description" not in fm:
        fail("frontmatter missing 'description'")
    if not str(fm["description"]).strip():
        fail("'description' is empty")

    ok(f"frontmatter has name={fm['name']!r} and non-empty description")

    # 3. References exist
    refs_dir = skill_path / "references"
    if not refs_dir.is_dir():
        fail(f"references/ directory not found at {refs_dir}")

    for ref in REQUIRED_REFERENCES:
        p = refs_dir / ref
        if not p.exists():
            fail(f"required reference missing: {p}")
    ok(f"all {len(REQUIRED_REFERENCES)} required references present")

    # 4. references/ file references in SKILL.md
    body = content[m.end():]
    ref_mentions = re.findall(r"`(references/[\w\-./]+\.md)`", body)
    for ref in set(ref_mentions):
        p = skill_path / ref
        if not p.exists():
            fail(f"SKILL.md references {ref} but file not found at {p}")
    ok(f"all {len(set(ref_mentions))} file references in SKILL.md resolve")

    # 5. Required sections
    for section in REQUIRED_SKILL_SECTIONS:
        if f"## {section}" not in body:
            fail(f"SKILL.md missing required section: ## {section}")
    ok(f"all {len(REQUIRED_SKILL_SECTIONS)} required sections present")

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    skill_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(skill_dir))
```

- [ ] **Step 2: Run validator against the skill**

Run:
```bash
python3 /root/projects/vuln_hunt/vuln-orchestrator/tools/validate-skill.py /root/projects/vuln_hunt/vuln-orchestrator
```

Expected output:
```
OK:   YAML frontmatter parsed
OK:   frontmatter has name='vuln-orchestrator' and non-empty description
OK:   all 5 required references present
OK:   all N file references in SKILL.md resolve
OK:   all 7 required sections present

All checks passed.
```

- [ ] **Step 3: If validator fails, fix the issues reported**

Read the FAIL message, fix the corresponding file (likely SKILL.md if a section is missing, or a reference file if it doesn't exist), and re-run step 2.

---

## Task 9: Create sample state file (for future testing)

**Files:**
- Create: `vuln_hunt/vuln-orchestrator/tools/sample-state.json`

- [ ] **Step 1: Write sample-state.json**

Write to `/root/projects/vuln_hunt/vuln-orchestrator/tools/sample-state.json`:

```json
{
  "$schema": "vuln-orchestrator/state-v1",
  "pipeline_id": "00000000-0000-4000-8000-000000000000",
  "schema_version": "1.0",
  "started_at": "2026-06-07T14:30:00Z",
  "last_updated_at": "2026-06-07T14:35:22Z",
  "finished_at": null,
  "concurrency": 5,
  "current_stage": 1,
  "overall_status": "running",
  "stage_status": {
    "0": "done",
    "1": "running",
    "2": "pending",
    "3": "pending"
  },
  "stage_0_params": {
    "scope": "/path/to/project",
    "features": "REST + MQ",
    "coverage": "full",
    "strategy": "clear"
  },
  "stage_0_result": {
    "surfaces": ["iface-REST-user-list"],
    "count": 1
  },
  "items": {
    "stage_1": {
      "iface-REST-user-list": {
        "status": "pending",
        "input": "iface-REST-user-list.md",
        "output": null,
        "started_at": null,
        "finished_at": null,
        "error": null,
        "retry_count": 0
      }
    },
    "stage_2": {},
    "stage_3": {}
  },
  "errors": [],
  "summary": {
    "stage_0_surfaces_count": 1,
    "stage_1_done": 0,
    "stage_1_failed": 0,
    "stage_2_done": 0,
    "stage_2_failed": 0,
    "stage_3_done": 0,
    "stage_3_failed": 0
  }
}
```

- [ ] **Step 2: Validate JSON is well-formed**

Run:
```bash
python3 -c "import json; json.load(open('/root/projects/vuln_hunt/vuln-orchestrator/tools/sample-state.json')); print('OK')"
```

Expected: `OK`

---

## Task 10: Final integration check

**Files:**
- Read: all files in `vuln_hunt/vuln-orchestrator/`

- [ ] **Step 1: Run the validator one final time**

Run:
```bash
python3 /root/projects/vuln_hunt/vuln-orchestrator/tools/validate-skill.py /root/projects/vuln_hunt/vuln-orchestrator
```

Expected: All checks pass.

- [ ] **Step 2: Verify all 4 existing skills are unchanged**

Run:
```bash
ls /root/projects/vuln_hunt/
```

Expected output includes:
```
analyze-surface
generate_surface
review-vuln
surface_vuln_analyzer
vuln-orchestrator    ← new
```

- [ ] **Step 3: Verify no .vuln_agent_output was created**

Run:
```bash
find /root/projects/vuln_hunt -name '.vuln_agent_output' -type d
```

Expected: no output (the orchestrator skill doesn't create state files unless invoked).

- [ ] **Step 4: Verify file count and line counts**

Run:
```bash
find /root/projects/vuln_hunt/vuln-orchestrator -type f | wc -l
wc -l /root/projects/vuln_hunt/vuln-orchestrator/SKILL.md /root/projects/vuln_hunt/vuln-orchestrator/references/*.md
```

Expected: 8 files total (1 SKILL.md + 5 references + 1 validator + 1 sample-state.json). Line counts similar to design spec.

---

## Self-Review

The plan is a faithful implementation of the spec:

| Spec Section | Plan Tasks |
|---|---|
| 定位 / 路径约定 / 预加载 / 工作流程 / 状态机 / 失败处理 / 原则 | Task 2 (SKILL.md) |
| 意图模式 | Task 3 |
| 状态文件 Schema | Task 4 |
| Stage 契约 | Task 5 |
| Subagent 派发协议 | Task 6 |
| 终态报告 | Task 7 |
| Validation tooling (not in spec, but needed for QA) | Task 8 |
| Sample state file (not in spec, but useful for future testing) | Task 9 |
| Final integration check | Task 10 |

No placeholder content. All code is complete. All paths are absolute. All 5 references are created before validation. The 4 existing skills are not touched.
