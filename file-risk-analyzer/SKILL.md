---
name: file-risk-analyzer
description: "Subagent 用技能：对一批文件逐一进行安全风险分析并定级。只要被分配分析文件的安全风险（审文件、文件级审计、风险定级），无论主流程是 source 分析还是 sink 分析，都要使用本技能。检测命令执行、代码执行、路径拼接文件操作、SQL 拼接、网络请求、端口监听的外部变量注入，以及证书绕过、硬编码凭据、ReDoS、敏感信息日志。"
allowed-tools: Read Bash Task Write
---

# 文件风险分析 (File Risk Analyzer)

你收到一批文件路径，需要逐一进行安全风险分析并定级。每个文件独立分析，互不干扰。

本 skill 仅负责解析文件列表、准备输出路径、派发 subagent 进行分析。**所有分析逻辑在 agents/file-analyzer.md 中，本文件不执行任何分析。**

## 输出目录

分析结果写入当前目录下的 `.vuln_agent_output/file_rksk/` 中，按源文件的全路径生成子目录结构：

```
源文件: /opt/myproject/Main.java
输出:   .vuln_agent_output/file_rksk/opt/myproject/Main.java.md
```

**路径解析规则：**
- 若收到的是相对路径，基于当前工作目录将其解析为绝对路径
- 从绝对路径去掉前导 `/`，再追加 `.md` 作为输出文件路径
- 输出根目录为当前目录下的 `.vuln_agent_output/file_rksk/`
- 确保输出文件的所有父目录存在（不存在则创建）
- 输出文件已存在则直接覆盖

## 分析流程

### Step 0：解析文件列表，准备输出路径

遍历每个输入文件：
1. 将其解析为绝对路径（结合当前工作目录）
2. 构造输出路径：`{当前目录}/.vuln_agent_output/file_rksk/{去掉前导/的绝对路径}.md`
3. 创建该输出文件所需的所有父目录

### Step 1：派发 subagent 分析

遍历每个文件，使用 `<skill_dir>/agents/file-analyzer.md` subagent 进行分析：

```
- Subagent 类型：general
- 子任务内容：按 agents/file-analyzer.md 分析该文件
- 传递参数：{文件路径, 输出路径}
- 每个文件启动一个独立的 subagent 任务
```

确保所有 subagent 任务启动后等待其完成。

### Step 2：汇总确认

所有文件分析完成后，输出汇总确认信息。
