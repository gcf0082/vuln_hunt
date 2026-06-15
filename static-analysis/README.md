# Static Analysis（静态分析）

一套静态分析工具包，使用 Semgrep 进行安全扫描，并通过 SARIF 处理已有的 CodeQL 及其他工具的分析结果。

## 包含的 Skill

| Skill | 用途 |
|-------|------|
| `semgrep` | 快速的基于模式的安全扫描 |
| `codeql` | 分析已有 CodeQL SARIF 输出（**不**运行扫描） |
| `sarif-parsing` | 解析和处理来自静态分析工具的结果 |

## 何时使用

在以下场景使用本插件：
- 使用 Semgrep 进行安全漏洞检测
- 分析已有的 CodeQL SARIF 输出，无需重新运行扫描
- 解析来自安全扫描器的 SARIF 输出
- 聚合和去重来自多个工具的结果

## 功能说明

### Semgrep
- 使用内置规则集（OWASP、CWE、Trail of Bits）进行快速安全扫描
- 编写自定义 YAML 规则，支持模式匹配
- 污点模式，追踪从 source 到 sink 的数据流
- CI/CD 集成，支持基线扫描

### CodeQL（仅输出分析）
- **不**构建数据库或运行查询
- 汇总、过滤和评估已有 CodeQL SARIF 输出
- 仅重要结果过滤（中等精度，严重级别 < 6.0）
- 零发现调查（对已有数据库进行质量检查）

### SARIF 解析
- 理解 SARIF 2.1.0 结构
- 使用 jq 进行 CLI 快速查询
- 使用 pysarif 和 sarif-tools 进行 Python 脚本处理
- 聚合和去重来自多个文件的结果
- CI/CD 集成模式

## 包含的 Agent

| Agent | 工具 | 用途 |
|-------|------|------|
| `semgrep-scanner` | Bash | 为指定语言类别并行执行 Semgrep 扫描 |
| `semgrep-triager` | Read、Grep、Glob、Write | 通过阅读源码将结果分类为真实漏洞/误报 |

## 安装

```
/plugin install trailofbits/skills/plugins/static-analysis
```

## 资源

- [Semgrep 测试手册](https://appsec.guide/docs/static-analysis/semgrep/)
