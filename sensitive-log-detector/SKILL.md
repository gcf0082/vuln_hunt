---
name: sensitive-log-detector
description: >
  分析日志输出中的变量，识别可疑行供审查。适用于代码审计、安全审查场景。
  当用户给你一段或多段包含变量的日志打印语句，或者日志文件，要求你分析其中
  是否打印了敏感信息时，务必使用此 skill。注意：即使用户只是贴了一段日志说
  "帮我看看"，没有明确说"分析敏感信息"，但只要涉及日志中的变量内容分析，
  就应该触发。
compatibility:
  - Shell
  - Python
---

# Sensitive Log Detector - 敏感日志检测

## 核心目标

扫描日志打印语句，识别可疑行输出供审查。

---

## 执行纪律

本 skill 所有阶段均**禁止直接读取源码文件**。分析基于 `log_sink/` 内容，不得打开源文件。

按以下步骤严格顺序执行，**不得跳过、合并或变更顺序**：

1. **Step 0** — 运行脚本，分派 agent（仅执行脚本 + 错误处理 + 分派）
2. **Steps 1-4** — 由 log-analyzer agent 按 `<skill_dir>/agents/log-analyzer.md` 执行分析
3. **Step 6** — 合并详情（所有 agent 完成后运行 merge-hits.py）

---

## Step 0: 日志采集

**Step 0 仅允许执行脚本和分派 agent。禁止读取 `log_sink/`。所有分析由 agent 在 Steps 1-4 中完成。**

### 0.1 执行脚本

```bash
python3 <skill_dir>/scripts/scan-logs.py [代码目录] [输出目录]
```

- `<skill_dir>`: 本 skill 根目录（`sensitive-log-detector/`）
- `[代码目录]`: 可选，默认当前目录
- `[输出目录]`: 可选，默认 `.vuln_agent_output/sensitive-log-detector/`

**输出结构：**

```
.vuln_agent_output/sensitive-log-detector/
  log_sink/                         ← 日志内容
    sensitive-logs-001.txt          ← 序号# 日志内容
  hits/                             ← agent 分析结果
    sensitive-logs-001.txt
  details/                          ← 合并详情（所有 hits 合并，100 条/文件）
    sensitive-logs-001.txt          ← 序号# 日志内容 + 源码路径
    sensitive-logs-002.txt
```

### 0.2 错误处理

| 错误 | 处理方式 |
|---|---|
| 脚本不存在 | **报错停止** |
| 脚本执行失败 | **报错停止** |
| 无输出文件 | **报错停止** |
| 成功 | **进入分析分派** |

### 0.3 分析分派（必须执行）

**每个文件必须分配独立的 log-analyzer agent，严禁将多个文件交给同一个 agent 处理。**

遍历 `log_sink/` 下每个文件，逐一分配 **log-analyzer** agent：

```
使用 <skill_dir>/agents/log-analyzer.md agent 分析 <path>/log_sink/sensitive-logs-NNN.txt
```

每个 agent 将分析结果写入 `hits/`（格式同 `log_sink/`，仅保留确认行）。

**结果聚合：** 父会话收集所有 agent 完成通知，确认 `hits/` 下文件数量。每个 agent 只处理一个文件，不可合并。

---

## Step 6: 合并详情

所有 agent 完成后，运行 merge-hits.py：

```bash
python3 <skill_dir>/scripts/merge-hits.py [输出目录]
```

输出到 `<输出目录>/details/`，每条日志附带源码路径。
