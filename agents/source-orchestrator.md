---
name: source-orchestrator
description: source 流水线编排
mode: primary
permission:
  read: allow
  glob: allow
  grep: allow
  write: allow
  bash: allow
  task:
    "surface-collector": "allow"
    "surface-analyst": "allow"
    "vulnerability-analyst": "allow"
    "source-re-analyzer": "allow"
---

加载 `source-orchestrator` skill 并执行。
