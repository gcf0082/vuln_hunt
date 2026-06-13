---
name: full-orchestrator
description: 全量流水线编排
mode: primary
permission:
  read: allow
  glob: allow
  grep: allow
  write: allow
  bash: allow
  task:
    "source-orchestrator": "allow"
    "sink-orchestrator": "allow"
    "vuln-merger": "allow"
---

加载 `full-orchestrator` skill 并执行。
