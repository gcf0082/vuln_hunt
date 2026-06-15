---
name: semgrep
description: >-
  Run Semgrep static analysis scan on a codebase using parallel subagents.
  Supports two scan modes — "run all" (full ruleset coverage) and "important
  only" (high-confidence security vulnerabilities). Automatically detects and
  uses Semgrep Pro for cross-file taint analysis when available. Use when asked
  to scan code for vulnerabilities, run a security audit with Semgrep, find
  bugs, or perform static analysis. Spawns parallel workers for multi-language
  codebases.
allowed-tools: Bash Read Glob Task AskUserQuestion TaskCreate TaskList TaskUpdate
---

# Semgrep 安全扫描

使用自动语言检测、Task 子代理并行执行和合并 SARIF 输出来运行 Semgrep 扫描。

## 核心原则

1. **始终使用 `--metrics=off`** ——Semgrep 默认发送遥测数据；`--config auto` 也会回传数据。每个 `semgrep` 命令必须包含 `--metrics=off` 以防止安全审计期间的数据泄露。
2. **用户必须批准扫描计划（第 3 步是硬关卡）** ——原始的"扫描此代码库"请求不是批准。展示确切的规则集、目标、引擎和模式；等待明确的"是"/"继续"后再启动扫描器。
3. **第三方规则集是必须的，不是可选的** ——Trail of Bits、0xdea 和 Decurity 的规则能捕获官方注册表中没有的漏洞。当检测到的语言匹配时务必包含。
4. **在单条消息中生成所有扫描 Task** ——并行执行是核心性能优势。切勿顺序生成 Task；始终在一次响应中发出所有 Task 工具调用。
5. **扫描前始终检查 Semgrep Pro** ——Pro 支持跨文件污点追踪，多捕获约 250% 的真实漏洞。跳过检查意味着静默遗漏关键的跨文件漏洞。

## 使用场景

- 代码库的安全审计
- 在代码审查前查找漏洞
- 扫描已知的 Bug 模式
- 初次静态分析

## 不使用场景

- 二进制分析→请使用二进制分析工具
- 已有 Semgrep CI 配置→使用现有流水线
- 需要跨文件分析但无 Pro 许可证→考虑 CodeQL
- 创建自定义 Semgrep 规则→使用 `semgrep-rule-creator` skill
- 将现有规则移植到其他语言→使用 `semgrep-rule-variant-creator` skill

## 输出目录

所有扫描结果、SARIF 文件和临时数据存放在一个输出目录中。

- **如果用户在提示中指定了输出目录**，将其用作 `OUTPUT_DIR`。
- **如果未指定**，默认为 `./static_analysis_semgrep_1`。如果已存在，递增为 `_2`、`_3` 等。

两种情况下，**始终使用 `mkdir -p` 创建目录**后再写入任何文件。

```bash
# 解析输出目录
if [ -n "$USER_SPECIFIED_DIR" ]; then
  OUTPUT_DIR="$USER_SPECIFIED_DIR"
else
  BASE="static_analysis_semgrep"
  N=1
  while [ -e "${BASE}_${N}" ]; do
    N=$((N + 1))
  done
  OUTPUT_DIR="${BASE}_${N}"
fi
mkdir -p "$OUTPUT_DIR/raw" "$OUTPUT_DIR/results"
```

输出目录在**第 1 步开始时解析一次**，之后在后续所有步骤中使用。

```
$OUTPUT_DIR/
├── rulesets.txt                 # 已批准的规则集（第 3 步后记录）
├── raw/                         # 每次扫描的原始输出（未过滤）
│   ├── python-python.json
│   ├── python-python.sarif
│   ├── python-django.json
│   ├── python-django.sarif
│   └── ...
└── results/                     # 最终合并输出
    └── results.sarif
```

## 前提条件

**必需：** Semgrep CLI（`semgrep --version`）。如果未安装，参见 [Semgrep 安装文档](https://semgrep.dev/docs/getting-started/)。

**可选：** Semgrep Pro——支持跨文件污点追踪、过程间分析以及额外语言（Apex、C#、Elixir）。检查：

```bash
semgrep --pro --validate --config p/default 2>/dev/null && echo "Pro 可用" || echo "仅 OSS"
```

**限制：** OSS 模式无法跨文件追踪数据流。Pro 模式使用 `-j 1` 进行跨文件分析（每个规则集较慢，但并行规则集可弥补）。

## 扫描模式

在第 2 步中选择模式。模式影响扫描器标志和后处理。

| 模式 | 覆盖范围 | 报告的发现 |
|------|----------|-----------|
| **Run all** | 所有规则集、所有严重级别 | 全部 |
| **Important only** | 所有规则集，预过滤和后过滤 | 仅安全漏洞，中高置信度/影响 |

**Important only** 应用两层过滤：
1. **预过滤**：`--severity MEDIUM --severity HIGH --severity CRITICAL`（CLI 标志）
2. **后过滤**：JSON 元数据——仅保留 `category=security`、`confidence∈{MEDIUM,HIGH}`、`impact∈{MEDIUM,HIGH}`

参见 [scan-modes.md](references/scan-modes.md) 了解元数据标准和 jq 过滤命令。

## 编排架构

```
┌──────────────────────────────────────────────────────────────────┐
│ 主代理（本 skill）                                                │
│ 第 1 步：检测语言 + 检查 Pro 可用性                                │
│ 第 2 步：选择扫描模式 + 规则集（参考：rulesets.md）                 │
│ 第 3 步：展示计划 + 规则集，获取批准 [⛔ 硬关卡]                   │
│ 第 4 步：生成并行扫描 Task（已批准的规则集 + 模式）                │
│ 第 5 步：合并结果并报告                                           │
└──────────────────────────────────────────────────────────────────┘
         │ 第 4 步
         ▼
┌─────────────────┐
│ 扫描 Task       │
│ （并行）        │
├─────────────────┤
│ Python 扫描器   │
│ JS/TS 扫描器    │
│ Go 扫描器       │
│ Docker 扫描器   │
└─────────────────┘
```

## 工作流

**按照 [scan-workflow.md](workflows/scan-workflow.md) 中的详细工作流执行。** 摘要：

| 步骤 | 操作 | 关卡 | 关键参考 |
|------|------|------|----------|
| 1 | 解析输出目录，检测语言 + Pro 可用性 | — | 使用 Glob，非 Bash |
| 2 | 选择扫描模式 + 规则集 | — | [rulesets.md](references/rulesets.md) |
| 3 | 展示计划，获取明确批准 | ⛔ 硬关卡 | AskUserQuestion |
| 4 | 生成并行扫描 Task | — | [scanner-task-prompt.md](references/scanner-task-prompt.md) |
| 5 | 合并结果并报告 | — | 合并脚本（下方） |

**Task 强制：** 调用时创建 5 个任务，使用 blockedBy 依赖（每个步骤阻塞前一个）。第 3 步是硬关卡——仅在用户明确批准后才标记完成。

**合并命令（第 5 步）：**

```bash
uv run {baseDir}/scripts/merge_sarif.py $OUTPUT_DIR/raw $OUTPUT_DIR/results/results.sarif
```

## 代理

| 代理 | 工具 | 用途 |
|------|------|------|
| `static-analysis:semgrep-scanner` | Bash | 为某语言类别执行并行 semgrep 扫描 |

在第 4 步生成 Task 子代理时使用 `subagent_type: static-analysis:semgrep-scanner`。

## 需要拒绝的合理化借口

| 借口 | 为什么错 |
|------|----------|
| "用户要求扫描，那就是批准" | 原始请求≠计划批准。展示计划，使用 AskUserQuestion，等待明确的"是" |
| "第 3 步任务在阻塞，直接标记完成" | 对任务状态撒谎会破坏强制机制。仅在真正批准后标记完成 |
| "我已经知道他们想要什么" | 假设会导致扫描错误的目录/规则集。展示计划进行验证 |
| "只用默认规则集" | 用户必须在扫描前看到并批准确切的规则集 |
| "不询问就添加额外规则集" | 未经同意修改已批准的列表会破坏信任 |
| "第三方规则集是可选的" | Trail of Bits、0xdea、Decurity 捕获官方注册表中没有的漏洞——**必须包含** |
| "使用 --config auto" | 发送遥测；对规则集的控制较少 |
| "一次一个 Task" | 破坏并行性；一起生成所有 Task |
| "Pro 太慢了，跳过 --pro" | 跨文件分析捕获 250% 更多的真实漏洞；值得花时间 |
| "Semgrep 原生支持 GitHub URL" | URL 处理在非标准 YAML 的仓库上会失败；始终先克隆 |
| "清理是可选的" | 克隆的仓库会污染用户的工作空间并跨运行累积 |
| "使用 . 或相对路径作为目标" | 子代理需要绝对路径以避免歧义 |
| "让用户稍后选择输出目录" | 输出目录必须在第 1 步解析，在任何文件创建之前 |

## 参考索引

| 文件 | 内容 |
|------|------|
| [rulesets.md](references/rulesets.md) | 完整规则集目录和选择算法 |
| [scan-modes.md](references/scan-modes.md) | 预/后过滤标准和 jq 命令 |
| [scanner-task-prompt.md](references/scanner-task-prompt.md) | 生成扫描子代理的模板 |

| 工作流 | 用途 |
|--------|------|
| [scan-workflow.md](workflows/scan-workflow.md) | 完整的 5 步扫描执行流程 |

## 成功标准

- [ ] 输出目录已解析（用户指定或自动递增默认值）
- [ ] 所有生成的文件存储在 `$OUTPUT_DIR` 内
- [ ] 语言已检测并统计文件数；Pro 状态已检查
- [ ] 用户已选择扫描模式（run all / important only）
- [ ] 规则集包含所有检测到的语言的第三方规则
- [ ] 用户已明确批准扫描计划（第 3 步关卡已通过）
- [ ] 所有扫描 Task 在一条消息中生成并完成
- [ ] 每个 `semgrep` 命令都使用了 `--metrics=off`
- [ ] 已批准的规则集记录到 `$OUTPUT_DIR/rulesets.txt`
- [ ] 每次扫描的原始输出存储在 `$OUTPUT_DIR/raw/`
- [ ] `results.sarif` 存在于 `$OUTPUT_DIR/results/` 且为有效的 JSON
- [ ] Important-only 模式：合并前应用后过滤；未过滤的结果保留在 `raw/` 中
- [ ] 结果摘要已按严重性和类别分类报告
- [ ] 克隆的仓库（如有）已从 `$OUTPUT_DIR/repos/` 清理
