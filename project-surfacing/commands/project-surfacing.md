---
name: vuln_hunt:project-surfacing
description: 在漏洞分析之前，识别项目的外部暴露面（跨信任边界入口）
argument-hint: "<codebase-path> [--focus <module>]"
allowed-tools: Read Grep Glob Bash Task
---

# 项目暴露面映射

**参数：** $ARGUMENTS

解析参数：
1. **代码库路径**（必填）：要分析的项目路径
2. **聚焦模块**（可选）：`--focus <module>` 指定特定模块分析

使用这些参数调用 `project-surfacing` 技能以执行暴露面映射工作流。
