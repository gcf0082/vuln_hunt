---
name: behavior-analyzer
description: "Subagent 用技能：对一批文件逐一进行关键行为分析。识别文件中的命令执行、文件操作、SQL 操作、网络操作、日志记录等关键行为，并追溯操作数据的变量是否来自外部。只要被分配分析文件中的行为（识别行为、分析代码行为、检查文件行为），无论主流程是什么，都要使用本技能。"
allowed-tools: Read Bash Task Write
---

# 关键行为分析 (Behavior Analyzer)

你收到一批文件路径，需要逐一分析其中的关键行为。每个文件独立分析，互不干扰。

本 skill 仅负责解析文件列表、准备输出路径、派发 subagent。**所有分析逻辑由 subagent 内部加载 agents/file-analyzer.md 执行，本文件不执行任何分析。**

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

### Step 0：解析文件列表，准备输出路径

遍历每个输入文件：
1. 将其解析为绝对路径（结合当前工作目录）
2. 构造输出路径：`{当前目录}/.vuln_agent_output/behavior/{去掉前导/的绝对路径}.md`
3. 创建该输出文件所需的所有父目录

### Step 1：派发 subagent

遍历每个文件，启动一个独立的 subagent 任务，传递 `{文件路径, 输出路径}`。subagent 内部会加载 file-analyzer.md 执行全部分析。

### Step 2：汇总确认

所有 subagent 完成后，输出汇总确认信息。
