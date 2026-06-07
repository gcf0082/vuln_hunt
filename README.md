# vuln_hunt

Vulnerability hunting toolkit — a 5-skill pipeline for **attack surface collection → surface analysis → vulnerability detection → review → orchestration**.

## Skills Overview

```
[0] generate-surface     ─┐
                          │  user-instruction triggered
                          ▼
[1] analyze-surface      ─┐  per surface, 5 concurrent
                          ▼
[2] analyze-vulnerability─┐  per surface, 5 concurrent
                          ▼
[3] review-vuln          ─┘  per finding, 5 concurrent

      [★ vuln-orchestrator]  (NEW) 整条流水线编排器，含 stage 0 入口、并发派发、断点续跑
```

| Skill | Trigger | Purpose |
|---|---|---|
| `generate_surface/` | user instruction | Collect attack surfaces (REST/MQ/gRPC/CRON/CLI/SDK/...) |
| `analyze-surface/` | explicit | Trace call chain + draw mermaid flowchart for one surface |
| `surface_vuln_analyzer/` | explicit | Detect vulnerabilities in one analyzed surface (4-档: VULN/DISMISSED/CLEAN/SUSPECTED) |
| `review-vuln/` | explicit | Re-review first-round findings with challenger mindset (VULN/NOVULN/SUSPECTED) |
| `vuln-orchestrator/` | explicit | Orchestrate the entire 4-stage pipeline with state tracking and resume support |

## Pipeline Data Flow

All artifacts live in `.vuln_agent_output/` under the target project root:

```
.vuln_agent_output/
├── .orchestrator-state.json        ← vuln-orchestrator state (source of truth)
├── .collect_done                   ← generate-surface completion signal
├── discovered_surfaces/            ← stage 0 output
├── analyzed_surfaces/              ← stage 1 output
├── vuln_findings/                  ← stage 2 output
├── vuln_reviews/                   ← stage 3 output
└── meta/error/                     ← per-skill error logs
```

## Quick Start

### Manual flow (call skills one by one)

1. `generate_surface` — give it a target project and collect attack surfaces
2. `analyze-surface` — for each surface file, get call chain + flowchart
3. `surface_vuln_analyzer` — for each analyzed surface, get vulnerability findings
4. `review-vuln` — for each finding, re-verify with challenger posture

### Orchestrated flow (one call runs all)

```
@vuln-orchestrator start
```

Subcommands: `start` / `resume` / `status` / `rerun-stage N` / `retry-failed` / `stop` / `abort`

## Design

See [`docs/superpowers/specs/2026-06-07-vuln-orchestrator-design.md`](docs/superpowers/specs/2026-06-07-vuln-orchestrator-design.md) for the full vuln-orchestrator design and [`docs/superpowers/plans/2026-06-07-vuln-orchestrator.md`](docs/superpowers/plans/2026-06-07-vuln-orchestrator.md) for the implementation plan.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
