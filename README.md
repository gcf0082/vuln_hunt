# vuln_hunt

漏洞扫描工具集 —— source-based 与 sink-based 两条流水线，基于 OpenCode Agent + Skill 体系。

## 目录结构

```
agents/                              ← OpenCode Agent 定义
├── surface-collector.md             ← 暴露面采集（加载 source-collect skill）
├── surface-analyst.md               ← 调用链追踪（加载 source-analyze skill）
├── vulnerability-analyst.md         ← 漏洞分析（加载 source-analyze-vuln skill）
├── source-re-analyzer.md            ← 漏洞复核（加载 source-review skill）
├── sink-collector.md                ← 危险点采集（加载 sink-collect skill）
├── sink-vulnerability-analyst.md    ← 危险点漏洞分析（加载 sink-analyze-vuln skill）
├── sink-re-analyzer.md              ← 危险点复核（加载 sink-review skill）
├── vuln-merger.md                   ← 合并去重（加载 vuln-merge skill）
├── vuln-report-writer.md            ← 报告生成（加载 vuln_report_writer skill）
├── source-orchestrator.md           ← source 流水线编排（primary agent）
├── sink-orchestrator.md             ← sink 流水线编排（primary agent）
└── full-orchestrator.md             ← 全量流水线编排（primary agent）

skills/                              ← SKILL.md 详细指令
├── source-collect/                  ← 暴露面采集指令
├── source-analyze/                  ← 调用链追踪指令
├── source-analyze-vuln/             ← 漏洞分析指令
├── source-review/                   ← 漏洞复核指令
├── sink-collect/                    ← 危险点采集指令
├── sink-analyze-vuln/               ← 危险点漏洞分析指令
├── sink-review/                     ← 危险点复核指令
├── vuln-merge/                      ← 合并去重指令
├── vuln_report_writer/              ← 报告生成指令
├── source-orchestrator/             ← source 流水线编排指令
├── sink-orchestrator/               ← sink 流水线编排指令
├── full-orchestrator/               ← 全量流水线编排指令
├── vuln-dispatch/                   ← 意图识别路由（skill 保留）
└── callchain-trace/                 ← 调用链追踪方法参考
```

## Source-based 流水线

```
[0] surface-collector        ─┐
                              │  按用户指令触发
                              ▼
[1] surface-analyst          ─┐  每条目 5 并发
                              ▼
[2] vulnerability-analyst    ─┐  每条目 5 并发
                              ▼
[3] source-re-analyzer       ─┘  每条目 5 并发

      [★ source-orchestrator]  编排整条流水线
```

## Sink-based 流水线

```
[0] sink-collector                ─┐
                                   │  按用户指令触发
                                   ▼
[1] sink-vulnerability-analyst    ─┐  每条目 5 并发
                                   ▼
[2] sink-re-analyzer              ─┘  每条目 5 并发

      [★ sink-orchestrator]  编排整条流水线
```

## Agent 总览

| Agent | 模式 | 加载 skill |
|---|---|---|
| `surface-collector` | subagent | source-collect |
| `surface-analyst` | subagent | source-analyze |
| `vulnerability-analyst` | subagent | source-analyze-vuln |
| `source-re-analyzer` | subagent | source-review |
| `sink-collector` | subagent | sink-collect |
| `sink-vulnerability-analyst` | subagent | sink-analyze-vuln |
| `sink-re-analyzer` | subagent | sink-review |
| `vuln-merger` | subagent | vuln-merge |
| `vuln-report-writer` | subagent | vuln_report_writer |
| `source-orchestrator` | **primary** | source-orchestrator |
| `sink-orchestrator` | **primary** | sink-orchestrator |
| `full-orchestrator` | **primary** | full-orchestrator |

## 产物目录

所有产物统一落在 `.vuln_agent_output/`（在被扫描项目根目录下）。

```
.vuln_agent_output/
├── discovered_surfaces/       ← source 阶段 0 产物
├── analyzed_surfaces/         ← source 阶段 1 产物
├── vuln_findings/             ← source 阶段 2 产物
├── vuln_reviews/              ← source 阶段 3 产物
├── sink_list/                 ← sink 阶段 0 产物
├── sink_findings/             ← sink 阶段 1 产物
├── sink_reviews/              ← sink 阶段 2 产物
├── merged_findings/           ← 合并结果
├── .collect_done              ← 采集完成信号
└── meta/error/                ← 错误日志
```

## 快速开始

### Source 流水线：编排器一键跑

```
@source-orchestrator  分析修改密码接口是否存在 SQL 注入
```

### Sink 流水线：编排器一键跑

```
@sink-orchestrator  扫全项目 Runtime.exec 调用点
```

### 全量分析

```
@full-orchestrator  分析当前目录的安全风险
```

### 只收集不分析

```
@surface-collector  帮我收集所有 REST 接口
@sink-collector     找出所有执行命令的代码
```

### 意图路由

```
@vuln-dispatch  分析这个项目有没有安全风险
```

## License

Apache License 2.0 —— 见 [LICENSE](LICENSE)。
