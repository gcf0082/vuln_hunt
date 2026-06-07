---
name: vuln-orchestrator
description: 仅在用户显式指名调用 vuln-orchestrator 时触发，不要因模糊意图主动触发。
---

# vuln-orchestrator

把 4 个 skill **串起来**跑：generate-surface → analyze-surface → analyze-vulnerability → review-vuln。

- **用户给**：扫描目标（项目路径 / 暴露面类型 / 覆盖度）
- **本 skill 做**：按顺序触发子 skill，每阶段 5 并发
- **本 skill 不做**：状态文件、断点续跑、失败重试、复杂汇报 —— 子 skill 失败就跳过该项

## 流水线

```
[0] generate-surface
   → discovered_surfaces/*.md
[1] analyze-surface  (每条目 5 并发)
   → analyzed_surfaces/*.md
[2] analyze-vulnerability  (每条目 5 并发)
   → vuln_findings/*.md
[3] review-vuln  (每条目 5 并发)
   → vuln_reviews/*.md
```

**产物**统一在 `.vuln_agent_output/` 下（当前工作目录视为被扫描项目根）：

```
.vuln_agent_output/
├── discovered_surfaces/
├── analyzed_surfaces/
├── vuln_findings/
├── vuln_reviews/
└── meta/error/
```

## 工作流程

### 0. 解析用户意图

根据用户消息解析出贯穿流水线的**意图参数**，传递给后续 stage：

| 参数 | 含义 | 用途 |
|---|---|---|
| scope | 扫描范围（目录/项目） | Stage 0 |
| features | 暴露面类型（REST / MQ / gRPC / CRON / CLI / 全部） | Stage 0 |
| coverage | 覆盖度（full / sample / 指定子集） | Stage 0 |
| focus | 关注方向（漏洞类型 / 参数 / 模块） | Stage 1/2/3 可选限定 |

**解析示例**：

| 用户消息 | 解析结果 |
|---|---|
| "分析当前目录rest接口" | scope=. features=REST coverage=full |
| "扫一下MQ和Cron" | scope=. features=MQ+CRON coverage=full |
| "看看有没有命令注入" | scope=. features=all coverage=full focus=命令注入 |
| "分析 /tmp/foo 的 REST 接口有没有文件上传漏洞" | scope=/tmp/foo features=REST coverage=full focus=文件上传 |

### 1. 启动

用户调用 `vuln-orchestrator` 时，先按「解析用户意图」节检查 scope / features / coverage 是否已在用户消息中包含。**已包含的不反问，只反问确实缺失的**：

| 字段 | 反问时机 |
|---|---|
| scope | 用户没说扫哪个项目时 |
| features | 用户没说关注哪些暴露面时 |
| coverage | 用户没说覆盖度时 |

三个参数都齐了 → 直接进入流水线，不反问。

### 2. 跑流水线

依次执行，每阶段用 `task` 工具派发 subagent：

**Stage 0**（单次）：
```
subagent: surface-collector
prompt: 调用 generate-surface skill
        - work_dir: .
        - scope / features / coverage: <用户给的>
        产物: .vuln_agent_output/discovered_surfaces/
        完成信号: .vuln_agent_output/.collect_done
```

**Stage 1**（每 surface 一个，5 并发）：
```
读 discovered_surfaces/*.md 得到 slug 列表
对每个 slug 同时派发（一次 LLM 响应中发 ≤5 个 task）：
  subagent: surface-analyst
  prompt: 调用 analyze-surface skill
          - work_dir: .
          - surface_file: discovered_surfaces/{slug}.md
          - 关注方向: {focus（可选），无则省略}
          产物: analyzed_surfaces/{slug}.md
```

**Stage 2**（每 analyzed surface 一个，5 并发）：
```
读 analyzed_surfaces/*.md 得到 slug 列表
对每个 slug 同时派发：
  subagent: vulnerability-analyst
  prompt: 调用 analyze-vulnerability skill (surface_vuln_analyzer)
          - work_dir: .
          - input: analyzed_surfaces/{slug}.md
          - task_content: {focus（用户关注方向），无则省略}
          产物: vuln_findings/*.md
```

**Stage 3**（每 finding 一个，5 并发）：
```
读 vuln_findings/*.md 得到 stem 列表
对每个 stem 同时派发：
  subagent: vuln-re-analyzer
  prompt: 调用 review-vuln skill
          - work_dir: .
          - input: vuln_findings/{stem}.md
          - 关注方向: {focus（可选），无则省略}
          产物: vuln_reviews/{stem}.md
```

**5 并发的实现**：在同一次 LLM 响应中发起 ≤5 个 `task` 调用 → 等所有返回 → 解析结果 → 进入下一批。

### 3. 汇报

跑完用一段简短的总结结束：

```
✅ vuln_hunt 流水线完成
- 攻击面: X 个
- 分析完成: A/B（失败: 失败项列表）
- 漏洞 finding: C/D
- 复核完成: E/F
- 产物: .vuln_agent_output/
```

不写状态文件，不做断点续跑 —— 中途断了用户重跑即可。

## 失败处理

- **子 skill 失败**：跳过该项，继续跑其他项，最终报告里列出失败项
- **整 stage 无产物**：直接进入下一 stage（输入为空就空跑）
- **不重试**：失败就失败，简化逻辑

## 原则

- **不改子 skill**：不修改 4 个子 skill 的任何 `SKILL.md`
- **不动源**：本 skill 不修改被扫描项目的任何源文件
- **幂等**：重复跑会基于子 skill 自身的产物策略（覆盖 / 追加 / 清空）行为

## 不在本 skill 范围内

- 漏洞分析、风险评级、利用验证 → 子 skill 负责
- 修改源代码、加防护、加固建议 → 不在本 skill 范围
