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
