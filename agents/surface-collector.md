---
name: surface-collector
description: 暴露面采集
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

加载 `source-collect` skill 并执行。
