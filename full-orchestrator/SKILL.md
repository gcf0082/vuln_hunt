---
name: full-orchestrator
description: 仅在用户显式指名调用 full-orchestrator 时触发，不要因模糊意图主动触发。
---

# full-orchestrator

默认先跑 sink 管道再跑 source 管道，最后合并结果。支持 `--order source-first` 切换为先 source 后 sink。

- **本 skill 做**：按顺序触发 sink-orchestrator → source-orchestrator → vuln-merge（或 source-first 变体）
- **本 skill 不做**：状态文件、断点续跑、失败重试、复杂汇报 —— 子 skill 失败就跳过该项

## 流水线

默认（sink → source）：
```
[0] sink-orchestrator
    → sink_list/ → sink_findings/ → sink_reviews/
[1] source-orchestrator
    → discovered_surfaces/ → analyzed_surfaces/ → vuln_findings/ → vuln_reviews/
[2] vuln-merge
    → merged_findings/
```

`--order source-first` 变体：
```
[0] source-orchestrator
    → discovered_surfaces/ → analyzed_surfaces/ → vuln_findings/ → vuln_reviews/
[1] sink-orchestrator
    → sink_list/ → sink_findings/ → sink_reviews/
[2] vuln-merge
    → merged_findings/
```

**产物**统一在 `.vuln_agent_output/` 下：

```
.vuln_agent_output/
├── sink_list/
├── sink_findings/
├── sink_reviews/
├── discovered_surfaces/
├── analyzed_surfaces/
├── vuln_findings/
├── vuln_reviews/
├── merged_findings/          ← 合并结果
├── meta/error/
└── temp/
    └── scripts/
```

## 工作流程

### 1. 启动

用户调用 `full-orchestrator` 时，已携带用户原始任务描述。从 `$ARGUMENTS` 解析 `--order source-first` 切换为先 source 后 sink。直接进入流水线，不反问。

### 2. 跑流水线

默认顺序（sink → source）。当 `--order source-first` 指定时，交换 Stage 0 和 Stage 1 的顺序。

依次执行，每阶段用 `task` 工具派发 subagent：

**Stage 0**（单次，默认 sink / source-first 时 source）：
```
subagent: {sink-orchestrator | source-orchestrator}
prompt: 调用 {sink-orchestrator | source-orchestrator} skill
        - work_dir: .
        - task: {用户原始任务描述}
        - vuln_type: {vuln_type，如 cmd/sql}
        产物: .vuln_agent_output/{sink_list/ | discovered_surfaces/} + ...
```

**Stage 1**（单次，另一个管道）：
```
subagent: {source-orchestrator | sink-orchestrator}
prompt: 调用 {source-orchestrator | sink-orchestrator} skill
        - work_dir: .
        - task: {用户原始任务描述}
        - vuln_type: {vuln_type，如 cmd/sql}
        产物: .vuln_agent_output/{discovered_surfaces/ | sink_list/} + ...
```

**Stage 2**（单次）：
```
subagent: vuln-merger
prompt: 调用 vuln-merge skill
        - work_dir: .
        - task: {用户原始任务描述}
        输入: .vuln_agent_output/vuln_findings/ + .vuln_agent_output/sink_findings/
        产物: .vuln_agent_output/merged_findings/
```

### 3. 汇报

跑完用一段简短的总结结束：

```
✅ 全量安全分析完成
- sink 分析: X 个 finding
- source 分析: Y 个 finding
- 合并去重后: Z 个唯一漏洞
- 产物: .vuln_agent_output/merged_findings/
```

不写状态文件，不做断点续跑 —— 中途断了用户重跑即可。

## 失败处理

- **子 skill 失败**：跳过该项，继续跑其他项，最终报告里列出失败项
- **不重试**：失败就失败，简化逻辑

## 原则

- **不改子 skill**：不修改 sink-orchestrator / source-orchestrator / vuln-merge 的任何 `SKILL.md`
- **不动源**：本 skill 不修改被扫描项目的任何源文件
- **不动目标分析目录**：所有产物、临时文件、临时脚本**只能**写到 `.vuln_agent_output/` 下，**不得**在被分析项目源码目录里写任何文件
