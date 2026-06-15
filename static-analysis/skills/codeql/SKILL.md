---
name: codeql
description: >-
  Analyzes existing CodeQL SARIF output without triggering new scans. Processes
  results from CodeQL databases, summarizes findings by severity and rule, filters
  important-only results, and assesses output quality. Does NOT build databases or
  run queries — use with pre-existing CodeQL SARIF output.
allowed-tools: Bash Read Grep Glob
---

# CodeQL SARIF 分析

分析和处理已有的 CodeQL SARIF 输出。本 skill **不运行 CodeQL 扫描**——它用于处理之前 CodeQL 分析生成的 SARIF 文件。

## 使用场景

- 你有 CodeQL SARIF 文件，需要分析、过滤或汇总结果
- 需要对现有 SARIF 输出应用 CodeQL 特定的质量评估
- 需要按严重性、精度或规则类别筛选结果

## 不使用场景

- **运行 CodeQL 扫描**——请使用专门的 CodeQL 扫描环境
- **通用 SARIF 处理**——请使用 `sarif-parsing` skill 处理工具无关的 SARIF 操作
- **快速模式扫描**——请使用 `semgrep` 进行基于模式的快速分析

## 工作流

1. **接收 SARIF 输入**——用户提供 CodeQL SARIF 文件路径（可选提供数据库路径）
2. **汇总结果**——统计发现数量，按严重性/规则/级别聚合
3. **筛选/处理**——应用过滤（重要-only、特定规则、特定路径）
4. **评估质量**——评估 SARIF 输出质量（如果提供数据库）
5. **报告**——输出结构化的分析摘要

## SARIF 处理

所有 SARIF 处理任务使用 [references/sarif-processing.md](references/sarif-processing.md)。命令适用于用户提供的任何 CodeQL SARIF 文件。

用户提供 SARIF 文件路径。处理后的输出文件存放在原始文件旁，使用 `_processed.sarif` 后缀约定：

```bash
INPUT_SARIF="/path/to/user/results.sarif"
PROCESSED_SARIF="${INPUT_SARIF%.sarif}_processed.sarif"
```

## 质量评估

如果用户同时提供了 CodeQL 数据库目录和 SARIF 文件，使用 [references/quality-assessment.md](references/quality-assessment.md) 评估数据库质量——这有助于对 SARIF 发现进行上下文分析（零发现可能表示数据库质量问题而非代码无误）。

## 输出格式

生成结构化的 markdown 报告：

```markdown
# CodeQL SARIF 分析

**输入**: `/path/to/results.sarif`
**工具**: [来自 SARIF 元数据的 CodeQL 版本]
**数据库**: [路径，如提供]

## 汇总

| 指标 | 数值 |
|------|------|
| 总发现数 | X |
| 按级别：error | X |
| 按级别：warning | X |
| 按级别：note | X |
| 唯一规则数 | X |

## 按安全严重性排序的发现

| 严重性 | 规则 | 文件:行号 | 消息 |
|--------|------|-----------|------|
| 9.8 | `cpp/unbounded-write` | `src/main.cpp:L42` | ... |

## 按规则统计排名

| 规则 | 数量 | 最高严重性 |
|------|------|-----------|

## 结论

[重要发现、质量关注点、建议]
```

## 需要拒绝的合理化借口

- **"零发现意味着代码干净"**——零结果可能表示数据库质量低下、缺少模型或错误的查询包。在报告干净之前需要调查。
- **"我需要重建数据库"**——本 skill 不运行 CodeQL 扫描。请使用专门的 CodeQL 环境或 `sarif-parsing` skill。

## 成功标准

- [ ] 用户提供的 SARIF 文件存在且有效
- [ ] 发现已按数量、级别、严重性和规则汇总
- [ ] 重要-only 过滤已应用（如请求）
- [ ] 质量问题已记录（如提供数据库）
- [ ] 处理后的输出已保存
