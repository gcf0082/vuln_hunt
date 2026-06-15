# Semgrep 扫描工作流

完整的 5 步扫描执行流程。从头到尾阅读并按顺序执行每一步。

## Task 系统强制

调用时创建以下带依赖关系的任务：

```
TaskCreate: "检测语言和 Pro 可用性"（第 1 步）
TaskCreate: "选择扫描模式和规则集"（第 2 步）- blockedBy: 第 1 步
TaskCreate: "展示包含规则集的计划，获取批准"（第 3 步）- blockedBy: 第 2 步
TaskCreate: "使用已批准的规则集和模式执行扫描"（第 4 步）- blockedBy: 第 3 步
TaskCreate: "合并结果并报告"（第 5 步）- blockedBy: 第 4 步
```

### 强制关卡

| 任务 | 关卡类型 | 之前不能继续 |
|------|----------|-------------|
| 第 3 步 | **硬关卡** | 用户明确批准规则集 + 计划 |

仅在用户说出"是"、"继续"、"批准"或等效确认后标记第 3 步为 `completed`。

---

## 第 1 步：解析输出目录，检测语言和 Pro 可用性

> **入口：** 用户已指定或确认了目标目录。
> **出口：** `OUTPUT_DIR` 已解析并创建；生成了带文件数的语言列表；确定了 Pro 可用性。

### 解析输出目录

如果用户在提示中指定了输出目录，将其用作 `OUTPUT_DIR`。否则自动递增。两种情况下，**始终 `mkdir -p`** 以确保目录存在。

```bash
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
echo "输出目录: $OUTPUT_DIR"
```

`$OUTPUT_DIR` 由后续所有步骤使用。将其**绝对路径**传递给扫描子代理。扫描器将原始输出写入 `$OUTPUT_DIR/raw/`；合并/过滤后的结果放入 `$OUTPUT_DIR/results/`。

**检测 Pro 可用性**（需要 Bash）：

```bash
if ! command -v semgrep >/dev/null 2>&1; then
  echo "错误: semgrep 未安装。请从 https://semgrep.dev/docs/getting-started/ 安装"
  exit 1
fi
semgrep --version
semgrep --pro --validate --config p/default 2>/dev/null && echo "Pro: 可用" || echo "Pro: 不可用"
```

**检测语言**使用 Glob（而非 Bash）。对目标目录运行以下模式并统计匹配数：

`**/*.py`、`**/*.js`、`**/*.ts`、`**/*.tsx`、`**/*.jsx`、`**/*.go`、`**/*.rb`、`**/*.java`、`**/*.php`、`**/*.c`、`**/*.cpp`、`**/*.rs`、`**/Dockerfile`、`**/*.tf`

同时检查框架标记：`package.json`、`pyproject.toml`、`Gemfile`、`go.mod`、`Cargo.toml`、`pom.xml`。使用 Read 检查这些文件的框架依赖（例如读取 `package.json` 检测 React、Express、Next.js；读取 `pyproject.toml` 检测 Django、Flask、FastAPI）。

将发现映射到类别：

| 检测项 | 类别 |
|--------|------|
| `.py`、`pyproject.toml` | Python |
| `.js`、`.ts`、`package.json` | JavaScript/TypeScript |
| `.go`、`go.mod` | Go |
| `.rb`、`Gemfile` | Ruby |
| `.java`、`pom.xml` | Java |
| `.php` | PHP |
| `.c`、`.cpp` | C/C++ |
| `.rs`、`Cargo.toml` | Rust |
| `Dockerfile` | Docker |
| `.tf` | Terraform |
| k8s 清单 | Kubernetes |

---

## 第 2 步：选择扫描模式和规则集

> **入口：** 第 1 步完成——语言已检测，Pro 状态已知。
> **出口：** 扫描模式已选择；所有检测到的语言的结构化规则集 JSON 已编译。

**首先，选择扫描模式**使用 `AskUserQuestion`：

```
header: "扫描模式"
question: "应该使用哪种扫描模式？"
multiSelect: false
options:
  - label: "Run all（推荐）"
    description: "全覆盖——所有规则集、所有严重级别"
  - label: "Important only"
    description: "仅安全漏洞——中高置信度和影响，无代码质量"
```

记录所选模式。它影响第 4 步和第 5 步。

**然后，选择规则集。** 使用第 1 步检测到的语言和框架，遵循 [rulesets.md](../references/rulesets.md) 中的**规则集选择算法**。

该算法涵盖：
1. 安全基线（始终包含）
2. 语言特定的规则集
3. 框架规则集（如检测到）
4. 基础设施规则集
5. **必需的**第三方规则集（Trail of Bits、0xdea、Decurity——非可选）
6. 注册表验证

**输出：** 传递给第 3 步供用户审查的结构化 JSON：

```json
{
  "baseline": ["p/security-audit", "p/secrets"],
  "python": ["p/python", "p/django"],
  "javascript": ["p/javascript", "p/react", "p/nodejs"],
  "docker": ["p/dockerfile"],
  "third_party": ["https://github.com/trailofbits/semgrep-rules"]
}
```

---

## 第 3 步：关键关卡——展示计划并获取批准

> **入口：** 第 2 步完成——扫描模式和规则集已选择。
> **出口：** 用户已明确批准计划（引用确认）。

> **⛔ 强制检查点——请勿跳过**
>
> 此步骤需要用户明确批准后才能继续。
> 用户可能会在批准前修改规则集。

向用户展示带有**明确规则集列表**的计划：

```
## Semgrep 扫描计划

**目标：** /path/to/codebase
**输出目录：** $OUTPUT_DIR
**引擎：** Semgrep Pro（跨文件分析）| Semgrep OSS（单文件）
**扫描模式：** Run all | Important only（安全漏洞，中高置信度/影响）

### 检测到的语言/技术：
- Python（1,234 个文件）——检测到 Django 框架
- JavaScript（567 个文件）——检测到 React
- Dockerfile（3 个文件）

### 要运行的规则集：

**安全基线（始终包含）：**
- [x] `p/security-audit`——综合安全规则
- [x] `p/secrets`——硬编码凭证、API 密钥

**Python（1,234 个文件）：**
- [x] `p/python`——Python 安全模式
- [x] `p/django`——Django 特定漏洞

**JavaScript（567 个文件）：**
- [x] `p/javascript`——JavaScript 安全模式
- [x] `p/react`——React 特定问题
- [x] `p/nodejs`——Node.js 服务端模式

**Docker（3 个文件）：**
- [x] `p/dockerfile`——Dockerfile 最佳实践

**第三方（自动包含在检测到的语言中）：**
- [x] Trail of Bits 规则——https://github.com/trailofbits/semgrep-rules

**想修改规则集？** 告诉我添加或删除哪些。
**准备好扫描了？** 说"继续"或"是"。
```

**⛔ 停止：等待用户明确批准。**

1. **如果用户想修改规则集：** 按要求添加/删除，重新展示更新后的计划，返回等待。
2. **如果用户没有回应，使用 AskUserQuestion：**
   ```
   "我已准备好包含 N 个规则集（包括 Trail of Bits）的扫描计划。继续扫描？"
   选项：["是，运行扫描", "先修改规则集"]
   ```
3. **有效的批准：** "是"、"继续"、"批准"、"开始"、"看起来不错"、"运行"
4. **不是批准：** 用户的原始请求（"扫描此代码库"）、沉默、关于计划的疑问

### 扫描前检查清单

在标记第 3 步完成之前：
- [ ] 目标目录已向用户展示
- [ ] 引擎类型（Pro/OSS）已显示
- [ ] 语言已检测并列出
- [ ] **所有规则集已用复选框明确列出**
- [ ] 用户有机会修改规则集
- [ ] 用户已明确批准（引用其确认）
- [ ] **最终规则集列表已为第 4 步捕获**
- [ ] 代理类型已列出：`static-analysis:semgrep-scanner`

### 记录已批准的规则集

批准后，将已批准的规则集写入 `$OUTPUT_DIR/rulesets.txt`：

```bash
cat > "$OUTPUT_DIR/rulesets.txt" << RULESETS
# Semgrep 扫描——已批准的规则集
# 生成时间：$(date -Iseconds)
# 扫描模式：<run-all|important-only>

## 规则集：
<每行一个规则集，例如：>
p/security-audit
p/secrets
p/python
p/django
https://github.com/trailofbits/semgrep-rules
RULESETS
```

---

## 第 4 步：生成并行扫描 Task

> **入口：** 第 3 步已批准——用户明确确认了计划。
> **出口：** 所有扫描 Task 已完成；结果文件已存在于 `$OUTPUT_DIR/raw/`。

**使用第 1 步中解析的 `$OUTPUT_DIR`。** 它已存在，无需再次创建。扫描器将所有输出写入 `$OUTPUT_DIR/raw/`。

**在单条消息中生成 N 个 Task**（每个语言类别一个），使用 `subagent_type: static-analysis:semgrep-scanner`。

使用 [scanner-task-prompt.md](../references/scanner-task-prompt.md) 中的扫描器任务提示模板。

**依赖模式的扫描器标志：**
- **Run all**：无附加标志
- **Important only**：为每个 `semgrep` 命令添加 `--severity MEDIUM --severity HIGH --severity CRITICAL`

**示例——3 语言扫描（使用已批准的规则集）：**

在**单条消息**中生成这 3 个 Task：

1. **Task：Python 扫描器**——规则集：p/python、p/django、p/security-audit、p/secrets、trailofbits → `$OUTPUT_DIR/raw/python-*.json`
2. **Task：JavaScript 扫描器**——规则集：p/javascript、p/react、p/nodejs、p/security-audit、p/secrets、trailofbits → `$OUTPUT_DIR/raw/js-*.json`
3. **Task：Docker 扫描器**——规则集：p/dockerfile → `$OUTPUT_DIR/raw/docker-*.json`

### 操作说明

- 始终使用**绝对路径**作为 `[TARGET]`——子代理无法解析相对路径
- 将 GitHub URL 规则集克隆到 `$OUTPUT_DIR/repos/`——切勿直接传递 URL 给 `--config`（semgrep 的 URL 处理在非标准 YAML 的仓库上会失败）
- 所有扫描完成后删除 `$OUTPUT_DIR/repos/`
- 使用 `&` 和 `wait` 并行运行规则集，而非顺序执行
- 对语言特定的规则集使用 `--include="*.py"`，但对跨语言规则集（p/security-audit、p/secrets、第三方仓库）**不要**使用

---

## 第 5 步：合并结果并报告

> **入口：** 第 4 步完成——所有扫描 Task 已完成。
> **出口：** `results.sarif` 存在于 `$OUTPUT_DIR/results/` 且为有效 JSON。

**Important-only 模式：合并前进行后过滤。** 将 [scan-modes.md](../references/scan-modes.md) 中的过滤（"过滤目录中所有结果文件"部分）应用于 `$OUTPUT_DIR/raw/` 中的每个 JSON 结果。过滤在与原始文件相同目录下创建 `*-important.json` 文件——原始文件保持不变。

**生成合并的 SARIF** 使用合并脚本。SKILL.md 的"合并命令"部分有已解析的路径——使用该确切路径：

```bash
uv run {baseDir}/scripts/merge_sarif.py $OUTPUT_DIR/raw $OUTPUT_DIR/results/results.sarif
```

- **Run-all 模式：** 脚本合并 `$OUTPUT_DIR/raw/` 中所有 `*.sarif` 文件。
- **Important-only 模式：** 先运行后过滤（在 `raw/` 中创建 `*-important.json`），然后运行合并脚本。原始 SARIF 文件不受 JSON 后过滤影响，因此合并操作在未过滤的 SARIF 上执行。如需 SARIF 级别的过滤，在合并后将 scan-modes.md 中的 jq 后过滤应用到 `$OUTPUT_DIR/results/results.sarif`。

**验证合并的 SARIF 是否有效：**

```bash
python -c "import json; d=json.load(open('$OUTPUT_DIR/results/results.sarif')); print(f'合并 SARIF 中共 {sum(len(r.get(\"results\",[]))for r in d.get(\"runs\",[]))} 个发现')"
```

如果验证失败，合并脚本产生了无效输出——在报告前进行调查。

**向用户报告：**

```
## Semgrep 扫描完成

**扫描了：** 1,804 个文件
**使用的规则集：** 9 个（包括 Trail of Bits）
**总发现数：** 156

### 按严重性：
- ERROR：5
- WARNING：18
- INFO：9

### 按类别：
- SQL 注入：3
- XSS：7
- 硬编码密钥：2
- 不安全配置：12
- 代码质量：8

结果写入到：
- $OUTPUT_DIR/results/results.sarif（合并后的 SARIF）
- $OUTPUT_DIR/raw/（每次扫描的原始结果，未过滤）
- $OUTPUT_DIR/rulesets.txt（已批准的规则集）
```

**验证**在报告前：确认 `results.sarif` 存在且为有效 JSON。
