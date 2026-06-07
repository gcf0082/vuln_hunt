# vuln_hunt

漏洞扫描工具集 —— 一条 4 阶段的流水线：**攻击面收集 → 攻击面分析 → 漏洞分析 → 漏洞复核**。

## Skill 总览

```
[0] generate-surface     ─┐
                          │  按用户指令触发
                          ▼
[1] analyze-surface      ─┐  每条目 5 并发
                          ▼
[2] analyze-vulnerability─┐  每条目 5 并发
                          ▼
[3] review-vuln          ─┘  每条目 5 并发

       [★ vuln-orchestrator]  编排整条流水线
```

| Skill | 触发 | 作用 |
|---|---|---|
| `generate_surface/` | 显式调用 | 收集攻击面（REST / MQ / gRPC / CRON / CLI / SDK 等）|
| `analyze-surface/` | 显式调用 | 跟踪调用链 + 画 mermaid 流程图（单条目）|
| `surface_vuln_analyzer/` | 显式调用 | 漏洞分析（单条目，4 档结论：VULN / DISMISSED / CLEAN / SUSPECTED）|
| `review-vuln/` | 显式调用 | 复核漏洞结论（VULN / NOVULN / SUSPECTED）|
| `vuln-orchestrator/` | 显式调用 | 编排整条流水线，含状态跟踪、断点续跑、并发派发 |

## 产物目录

所有产物统一落在 `.vuln_agent_output/`（在被扫描项目根目录下）：

```
.vuln_agent_output/
├── .orchestrator-state.json   ← 编排器状态（仅 vuln-orchestrator 写）
├── .collect_done              ← generate-surface 完成信号
├── discovered_surfaces/       ← 阶段 0 产物
├── analyzed_surfaces/         ← 阶段 1 产物
├── vuln_findings/             ← 阶段 2 产物
├── vuln_reviews/              ← 阶段 3 产物
└── meta/error/                ← 各 skill 错误日志
```

## 快速开始

### 方式一：手动串联

1. `generate_surface` —— 收集攻击面
2. `analyze-surface` —— 分析每条攻击面
3. `surface_vuln_analyzer` —— 找漏洞
4. `review-vuln` —— 复核漏洞

### 方式二：编排器一键跑

```
@vuln-orchestrator
```

子命令：`start` / `resume` / `status` / `stop`

## License

Apache License 2.0 —— 见 [LICENSE](LICENSE)。
