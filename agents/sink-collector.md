---
name: sink-collector
description: 危险点采集
mode: subagent
permission:
  read: allow
  glob: allow
  grep: allow
  write: allow
  bash: allow
  task:
    "*": "allow"
---

加载 `sink-collect` skill 并执行。
