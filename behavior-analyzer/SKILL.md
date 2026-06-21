---
name: behavior-analyzer
description: "Subagent 用技能：对一批文件逐一进行关键行为分析。识别文件中的命令执行、文件操作、SQL 操作、网络操作等关键行为，并追溯操作数据的变量是否来自外部。只要被分配分析文件中的行为（识别行为、分析代码行为、检查文件行为），无论主流程是什么，都要使用本技能。"
allowed-tools: Read Bash Task Write
---

# 关键行为分析 (Behavior Analyzer)

你收到一批文件路径，需要逐一分析其中的关键行为。每个文件独立分析，互不干扰。

本 skill 仅负责收集文件列表、生成 tudo、派发 subagent 并校验完成度。**所有分析逻辑由 subagent 内部加载 agents/file-analyzer.md 执行，本文件不执行任何分析。**

## 输出目录

分析结果写入当前目录下的 `.vuln_agent_output/behavior/` 中，按源文件的全路径生成子目录结构：

```
源文件: /opt/myproject/Main.java
输出:   .vuln_agent_output/behavior/opt/myproject/Main.java.md
```

**路径解析规则：**
- 若收到的是相对路径，基于当前工作目录将其解析为绝对路径
- 从绝对路径去掉前导 `/`，再追加 `.md` 作为输出文件路径
- 输出根目录为当前目录下的 `.vuln_agent_output/behavior/`
- 确保输出文件的所有父目录存在（不存在则创建）
- 输出文件已存在则直接覆盖

## 分析流程

### Step 0：收集文件列表，生成 tudo

若输入是目录路径：
  1. 递归扫描该目录，智能识别所有文本格式的文件
  2. 生成文件列表

若输入是文件路径列表：
  1. 直接使用传入的文件列表

合并后：
  1. 将当前时间戳格式化为 `YYMMDD-HHMMSS`
  2. 在 `.vuln_agent_output/behavior/` 下创建 `tudo-{时间戳}.txt`
  3. 每行格式：`[待处理] <文件绝对路径>`
  4. 同时为每个文件准备好输出路径，创建所需父目录

### Step 1：派发 subagent 并更新 tudo

遍历 tudo 中状态为 `[待处理]` 的文件：
  1. 启动一个独立的 subagent 任务，传递 `{文件路径, 输出路径}`
  2. subagent 完成后，将 tudo 中对应行的 `[待处理]` 改为 `[已完成]`

**严禁：** 安全风险分析和跨文件分析。

### Step 2：校验完成度

读取 tudo 文件：
  - 若还有 `[待处理]` 条目，重新派发直至全部完成
  - 全部为 `[已完成]` 后，输出确认信息
