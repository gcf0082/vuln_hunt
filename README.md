# vuln_hunt

漏洞扫描工具集 —— source-based 与 sink-based 两条流水线，基于 OpenCode Agent 体系。

## 目录结构

```
agents/                              ← OpenCode Agent 定义（主入口）
├── surface-collector.md             ← 暴露面采集
├── surface-analyst.md               ← 调用链追踪
├── vulnerability-analyst.md         ← 漏洞分析
├── source-re-analyzer.md            ← source 复核
├── sink-collector.md                ← sink 采集
├── sink-vulnerability-analyst.md    ← sink 漏洞分析
├── sink-re-analyzer.md              ← sink 复核
├── vuln-merger.md                   ← 合并去重
├── vuln-report-writer.md            ← 报告生成
├── source-orchestrator.md           ← source 流水线编排（primary agent）
├── sink-orchestrator.md             ← sink 流水线编排（primary agent）
└── full-orchestrator.md             ← 全量流水线编排（primary agent）

skills/                              ← 保留的 Skill（参考/路由）
├── vuln-dispatch/                   ← 意图识别路由
├── callchain-trace/                 ← 调用链追踪方法参考
└── vuln-analysis-method/            ← 通用分析方法论
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

| Agent | 模式 | 角色 |
|---|---|---|
| `surface-collector` | subagent | 收集暴露面（REST / MQ / gRPC / CRON / CLI / SDK 等）|
| `surface-analyst` | subagent | 跟踪调用链 + 画 mermaid 流程图 |
| `vulnerability-analyst` | subagent | 漏洞分析（4 档：VULN / DISMISSED / CLEAN / SUSPECTED）|
| `source-re-analyzer` | subagent | 复核漏洞结论（VULN / NOVULN / SUSPECTED）|
| `sink-collector` | subagent | 采集 sink 列表 |
| `sink-vulnerability-analyst` | subagent | sink-based 反向数据流漏洞分析 |
| `sink-re-analyzer` | subagent | 复核 sink-based 漏洞结论 |
| `vuln-merger` | subagent | 合并 source + sink 结果去重 |
| `vuln-report-writer` | subagent | 按模板生成漏洞报告 |
| `source-orchestrator` | **primary** | 编排 source 流水线（4 stage，5 并发）|
| `sink-orchestrator` | **primary** | 编排 sink 流水线（3 stage，5 并发）|
| `full-orchestrator` | **primary** | 全量分析：sink → source → merge |

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
