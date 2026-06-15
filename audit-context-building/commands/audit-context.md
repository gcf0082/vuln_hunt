---
name: trailofbits:audit-context
description: 在漏洞挖掘之前构建深层架构上下文
argument-hint: "<codebase-path> [--focus <module>]"
allowed-tools: Read Grep Glob Bash Task
---

# 构建审计上下文

**参数：** $ARGUMENTS

解析参数：
1. **代码库路径**（必填）：要分析的代码库路径
2. **聚焦模块**（可选）：`--focus <module>` 指定特定模块分析

使用这些参数调用 `audit-context-building` 技能以执行完整工作流。
