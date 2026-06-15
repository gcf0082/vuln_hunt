---
name: trailofbits:diff-review
description: 对代码变更执行安全导向的差异审查
argument-hint: "<pr-url|commit-sha|diff-path> [--baseline <ref>]"
allowed-tools: Read Write Grep Glob Bash
---

# 差异安全审查

**参数：** $ARGUMENTS

解析参数：
1. **目标**（必需）：PR URL、commit SHA 或 diff 路径
2. **基线**（可选）：`--baseline <ref>` 用于比较参考

使用这些参数调用 `differential-review` skill 以执行完整工作流。
