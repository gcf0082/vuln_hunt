# vuln_hunt

漏洞扫描工具集 —— source-based 与 sink-based 两条流水线。

## Source-based 流水线

```
[0] source-collect        ─┐
                          │  按用户指令触发
                          ▼
[1] source-analyze       ─┐  每条目 5 并发
                          ▼
[2] source-analyze-vuln  ─┐  每条目 5 并发
                          ▼
[3] source-review        ─┘  每条目 5 并发

      [★ source-orchestrator]  编排整条流水线
```

## Sink-based 流水线

```
[0] sink-collect         ─┐
                          │  按用户指令触发
                          ▼
[1] sink-analyze-vuln    ─┐  每条目 5 并发
                          ▼
[2] sink-review          ─┘  每条目 5 并发

      [★ sink-orchestrator]  编排整条流水线
```

### 通用辅助

- `source-plan-vuln-tasks`：基于攻击面分析结果规划漏洞分析任务（可选中间层）

## Skill 总览

| Skill | 模式 | 触发 | 作用 |
|---|---|---|---|
| `source-collect/` | source | 显式调用 | 收集攻击面（REST / MQ / gRPC / CRON / CLI / SDK 等）|
| `source-analyze/` | source | 显式调用 | 跟踪调用链 + 画 mermaid 流程图 |
| `source-analyze-vuln/` | source | 显式调用 | 漏洞分析（4 档：VULN / DISMISSED / CLEAN / SUSPECTED）|
| `source-review/` | source | 显式调用 | 复核漏洞结论（VULN / NOVULN / SUSPECTED）|
| `source-orchestrator/` | source 编排 | 显式调用 | 编排 source 流水线（4 stage，5 并发）|
| `source-plan-vuln-tasks/` | source | 显式调用 | 基于攻击面分析结果规划漏洞分析任务 |
| `sink-collect/` | sink | 显式调用 | 采集 sink 列表，按统一格式落盘 |
| `sink-analyze-vuln/` | sink | 显式调用 | sink-based 反向数据流漏洞分析 |
| `sink-review/` | sink | 显式调用 | 复核 sink-based 漏洞结论 |
| `sink-orchestrator/` | sink 编排 | 显式调用 | 编排 sink 流水线（3 stage，5 并发）|

## 产物目录

所有产物统一落在 `.vuln_agent_output/`（在被扫描项目根目录下）。采集阶段的产物文件名始终带 `-{MMDD-HHMMSS}` 时间戳（如 `iface-REST-user-list-0608-021435.md`），后续阶段沿用同一 stem 保持一一对应。

```
.vuln_agent_output/
├── discovered_surfaces/       ← source 阶段 0 产物
├── analyzed_surfaces/         ← source 阶段 1 产物
├── planned_vuln_tasks/        ← source-plan-vuln-tasks 产物
├── vuln_findings/             ← source 阶段 2 产物
├── vuln_reviews/              ← source 阶段 3 产物
├── sink_list/                 ← sink 阶段 0 产物
├── sink_findings/             ← sink 阶段 1 产物
├── sink_reviews/              ← sink 阶段 2 产物
├── .collect_done              ← source-collect 完成信号
└── meta/error/                ← 各 skill 错误日志
```

## 默认行为约定

后续每个下游分析 skill（source-analyze / source-analyze-vuln / source-review / sink-analyze-vuln / sink-review / source-plan-vuln-tasks）遵循同一默认约定：

- **用户没指定文件** → 默认处理上一 stage 产物目录下所有 `*.md`，无需反问
- **用户指定了文件** → 处理指定文件
- **同名产物** → 默认覆盖
- **多文件** → 由 orchestrator 5 并发派发
- **保留时间戳** → 上一 stage 文件名带的 MMDD-HHMMSS 时间戳在所有下游 stage 产物中保持不变

入口采集 skill（source-collect / sink-collect）除外——它们没有"上一 stage"，需要用户给 scope/type。

## 快速开始

### Source 流水线：手动串联

1. `source-collect` —— 收集攻击面
2. `source-analyze` —— 分析每条攻击面
3. `source-analyze-vuln` —— 找漏洞
4. `source-review` —— 复核漏洞

### Source 流水线：编排器一键跑

```
@source-orchestrator
```

### Sink 流水线：手动串联

1. `sink-collect` —— 采集 sink 列表
2. `sink-analyze-vuln` —— 反向追踪漏洞
3. `sink-review` —— 复核 sink-based 漏洞

### Sink 流水线：编排器一键跑

```
@sink-orchestrator
```

## License

Apache License 2.0 —— 见 [LICENSE](LICENSE)。
