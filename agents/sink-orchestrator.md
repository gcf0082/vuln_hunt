---
name: sink-orchestrator
description: sink 流水线编排
mode: primary
permission:
  read: allow
  glob: allow
  grep: allow
  write: allow
  bash: allow
  task:
    "sink-collector": "allow"
    "sink-vulnerability-analyst": "allow"
    "sink-re-analyzer": "allow"
---

加载 `sink-orchestrator` skill 并执行。
