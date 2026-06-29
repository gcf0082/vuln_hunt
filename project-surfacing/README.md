# Project Surfacing（项目暴露面映射）

在漏洞分析之前，通过识别外部可达的跨信任边界入口来构建项目的攻击面模型。

## 何时使用

- 在安全审计之前需要理解项目的对外暴露面
- 需要区分"外部入口"和"内部模块调用"
- 为后续的 source 或 sink 分析提供聚焦范围

## 核心原则

- **只收集跨信任边界的入口**——内部模块间调用不算暴露面
- **只做发现和分类，不做漏洞分析**
- **结果用于指导后续分析方向**（推荐走 source 还是 sink）

## 三阶段

1. **项目全貌侦察** - 语言/框架/结构摸底
2. **跨信任边界暴露面发现** - HTTP/RPC/MQ/CLI/Cron/文件 I/O/HTTP 外呼
3. **攻击面模型输出** - 分类汇总 + 可疑点标记

## 与其他技能的关系

- `source-collect`：本技能的产物可作为 source-collect 的输入
- `sink-collect`：本技能识别的外部文件 I/O / HTTP 外呼点可喂给 sink-collect
- `audit-context-building`：本技能做广度暴露面识别，audit-context-building 做深度函数分析
