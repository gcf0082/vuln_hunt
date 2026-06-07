# vuln-orchestrator — 设计文档

**日期**：2026-06-07
**状态**：已获批，待实施
**范围**：单个 skill（vuln-orchestrator）

## 背景

`/root/projects/vuln_hunt` 现包含 4 个串联的安全分析 skill：

```
[0] generate-surface      → discovered_surfaces/*.md       + .collect_done
[1] analyze-surface       → analyzed_surfaces/*.md          (每 surface)
[2] analyze-vulnerability → vuln_findings/*-{slug}-{n}.md   (每 surface)
[3] review-vuln           → vuln_reviews/*-{vuln_stem}.md   (每 finding)
```

每个 stage 1-3 的 SKILL.md 都明确写明"每次调用只处理一个条目；多条目由调用方并发派发"。目前**没有"调用方"**——用户必须自己手工串联 4 个 skill、手工并发派发、手工跟踪状态、手工处理失败。本 spec 设计一个**整条流水线的编排器**填补这个角色。

## 核心决策

| # | 维度 | 决策 |
|---|---|---|
| 1 | 范围 | 整条 4 阶段流水线编排器 |
| 2 | Stage 0 | 包含，作为前门 |
| 3 | Stage 推进 | 全自动 + 中途可中断（隐式"停/续"） |
| 4 | 失败策略 | Skip+汇总，失败项可重跑 |
| 5 | 并发度 | 5 |
| 6 | 控制面 | 纯隐式自然语言 |

## 架构

orchestrator 是 LLM 协调者，**不写子 skill 逻辑**，只负责"派发 + 状态机 + 汇报"。子 skill 仍然按各自 SKILL.md 工作，orchestrator 通过 subagent 系统派发任务。

```
用户消息
   ↓
[vuln-orchestrator] ─── SKILL.md + references/ 约束
   ├─ 解析意图：start / status / resume / retry-failed / rerun-stage N / stop / abort
   ├─ 读/写 .vuln_agent_output/.orchestrator-state.json
   └─ 派发子任务到 4 个 skill（不修改它们的 SKILL.md）：
       ├─ generate-surface    (stage 0, 1 次)
       ├─ analyze-surface     (stage 1, 每 surface 一个, 5 并发)
       ├─ analyze-vulnerability (stage 2, 每 surface 一个, 5 并发)
       └─ review-vuln         (stage 3, 每 finding 一个, 5 并发)
```

## 文件结构

```
/root/projects/vuln_hunt/vuln-orchestrator/
├── SKILL.md                  ← 200-300 行
└── references/
    ├── intent-patterns.md    ← 自然语言 → 控制动作
    ├── state-schema.md       ← .orchestrator-state.json 完整 schema
    ├── stage-contracts.md    ← 各 stage 输入/输出 + 完成判据
    ├── dispatch-protocol.md  ← subagent 派发协议、并发槽位
    └── final-report.md       ← 收尾报告模板
```

## Subagent 映射

| Stage | 调用的 skill | 派发的 subagent |
|---|---|---|
| 0 | generate-surface | `surface-collector` |
| 1 | analyze-surface | `surface-analyst` |
| 2 | surface_vuln_analyzer（skill 名 `analyze-vulnerability`） | `vulnerability-analyst` |
| 3 | review-vuln | `vuln-re-analyzer` |

## 状态机

```
(no state)         → start → STAGE_0_COLLECTING
                              ↓ (.collect_done 存在 + 至少一个 .md)
                            STAGE_1_ANALYZING
                              ↓ (stage_1 items 全部 ∈ {done, failed} 且 ≥1 done)
                            STAGE_2_VULN_ANALYZING
                              ↓ (stage_2 items 同上)
                            STAGE_3_REVIEWING
                              ↓ (stage_3 items 同上)
                            PIPELINE_DONE

任意 stage 收到"停" → 写 paused 标记 → resume 时从 current_stage 继续
abort → 写 aborted 标记，in-flight 任务视为失败
```

## 状态文件

**位置**：`.vuln_agent_output/.orchestrator-state.json`（当前工作目录下）

**核心字段**（完整 schema 见 `references/state-schema.md`）：

```json
{
  "pipeline_id": "uuid-v4",
  "started_at": "2026-06-07T14:30:00Z",
  "last_updated_at": "2026-06-07T14:35:22Z",
  "concurrency": 5,
  "current_stage": 1,
  "stage_status": {"0": "done", "1": "running", "2": "pending", "3": "pending"},
  "stage_0_params": {"scope": "/path", "features": "REST + MQ", "coverage": "full"},
  "stage_0_result": {"surfaces": ["iface-REST-user-list", ...]},
  "items": {
    "stage_1": {"<slug>": {"status": "done|failed|pending|running", "input": "...", "output": "...", "error": null, "started_at": "...", "finished_at": "..."}},
    "stage_2": {...},
    "stage_3": {...}
  },
  "errors": [{"stage": 1, "item": "...", "error": "...", "timestamp": "..."}]
}
```

## Stage 完成判据

| Stage | 完成判据 |
|---|---|
| 0 | `.vuln_agent_output/.collect_done` 存在 **且** `discovered_surfaces/` 至少一个 `*.md` |
| 1 | `items.stage_1[*].status` 全部 ∈ {done, failed}，且至少一个 done |
| 2 | `items.stage_2[*].status` 全部 ∈ {done, failed}，且至少一个 done |
| 3 | `items.stage_3[*].status` 全部 ∈ {done, failed} |

## 7 类意图 → 控制动作

| 意图 | 触发短语 | 动作 |
|---|---|---|
| start | "跑" / "扫描" / "审计" / "一键" / 无明确上下文 | 从 stage 0 开始 |
| resume | "继续" / "接着" / "go on" / "resume" | 从 state.current_stage 继续 |
| status | "状态" / "进度" / "到哪了" / "status" | 只读 state 汇报 |
| rerun-stage N | "从 stage N 重新跑" / "rerun N" | 重置 stage N 起的状态 |
| retry-failed | "重跑失败的" / "retry failed" | 扫描所有 failed items 重置 |
| stop | "停" / "暂停" / "pause" | 写 paused，不发新任务 |
| abort | "取消" / "abort" / "别跑了" | 写 aborted，所有 in-flight 视为失败 |

模糊时优先 `resume`（已存在 state 时）/ `start`（无 state 时）。

## 触发描述（最终版）

```yaml
description: 仅在用户显式指名调用 vuln-orchestrator 时触发，不要因模糊意图主动触发。
```

## 触发与子命令分层

与 3 个 sub-skill（analyze-surface / analyze-vulnerability / review-vuln）保持完全一致的"显式调用"约定：

```
┌─ 触发层（外部，自动加载判定）──────────────────────────────┐
│ frontmatter description                                      │
│ → 仅在用户显式指名调用 vuln-orchestrator 时启动               │
│ → 不因"跑漏洞扫描/审计"等模糊意图自动触发                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─ 子命令层（内部，启动后解析）─────────────────────────────┐
│ references/intent-patterns.md                                │
│ → 启动后解析 7 类子命令                                       │
│   start / resume / status / rerun-stage N /                   │
│   retry-failed / stop / abort                                 │
└─────────────────────────────────────────────────────────────┘
```

**修正说明**：早期设计曾把"跑漏洞扫描/审计"等列为自动触发短语；现已统一为显式调用约定，与同项目其他 3 个 sub-skill 完全一致。子命令分类逻辑（`intent-patterns.md`）保留，作为启动后**内部**的子命令解析。

## 边界场景

| 场景 | 处理 |
|---|---|
| Stage 0 产出 0 个 surface | 提示用户"未发现暴露面，是否调整收集参数？"，不进入 stage 1 |
| 状态文件已存在且 stage 0 params 与新调用不一致 | 提示冲突，让用户选"覆盖 start" / "resume" / "abort" |
| 状态文件 JSON 损坏 | 拒绝启动，提示用户检查；提供"删除状态文件"指令 |
| 用户多次连发"继续" | 幂等：检查是否有 in-flight，没有就按 state 走 |
| 同一 surface 在 stage 1 失败多次 | 仍按 retry-failed 走，不自动无限重试 |
| 子 skill 写入状态文件外的目录 | 视为越界，记 warning，不阻止 |
| 用户说"重新跑"（没说 stage） | 默认 rerun-stage 0（清空所有产物 + 状态） |
| LLM dispatch 本身失败（subagent 返回 error） | 重试 1 次，仍失败记 error，状态置 failed |

## 与现有 4 个 skill 的边界

| 边界点 | orchestrator 负责 | 子 skill 负责 |
|---|---|---|
| 状态跟踪 | ✅ | ❌ |
| 派发策略 | ✅ | ❌ |
| 产物格式 | ❌ | ✅ |
| 完成信号 | orchestrator 写自己的 `.orchestrator-state.json` | generate-surface 写 `.collect_done` |
| 错误日志 | orchestrator 收集汇总 | 子 skill 写自己的 `meta/error/` |

## 关键设计原则

- **不改子 skill**：orchestrator 是 LLM 协调者，不修改任何 `*/SKILL.md`
- **状态文件是真理之源**：所有恢复/重跑/汇报都基于 `.orchestrator-state.json`
- **幂等**："继续"重复触发不会出问题
- **不替用户决策**：stage 0 的"清空/覆盖/追加"策略仍由用户回答（透传给 generate-surface）
- **可观测**：任何时刻用户问"状态"都能从 state 给出明确答案

## 实施风险

| 风险 | 缓解 |
|---|---|
| Subagent 派发协议可能因 opencode 版本不同而不同 | dispatch-protocol.md 集中定义，LLM 启动时按最新协议加载 |
| LLM dispatch 失败难以区分"网络错误"和"逻辑错误" | 统一记 error 字段，由用户人工判断是否 retry |
| 状态文件并发写（理论上多 subagent 写同一文件） | 实际中只有 orchestrator 写状态文件，subagent 只读 |
| 大型项目（>100 surface）stage 1 耗时过长 | status 命令可中断查看进度；stop 暂停后 resume |
