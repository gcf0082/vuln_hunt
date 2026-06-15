# 扫描器子代理任务提示

在第 4 步生成扫描器 Task 时使用此提示模板。使用 `subagent_type: static-analysis:semgrep-scanner`。

## 模板

```
你是 [LANGUAGE_CATEGORY] 的 Semgrep 扫描器。

## 任务
为 [LANGUAGE] 文件运行 Semgrep 扫描并将结果保存到 [OUTPUT_DIR]/raw。

## Pro 引擎状态：[PRO_AVAILABLE: true/false]

## 扫描模式：[SCAN_MODE: run-all/important-only]

## 已批准的规则集（来自用户确认的计划）
[列出用户确切批准的规则集 - 请勿替换]

示例：
- p/python
- p/django
- p/security-audit
- p/secrets
- https://github.com/trailofbits/semgrep-rules

## 要运行的命令（并行）

### 先克隆 GitHub URL 规则集：
```bash
mkdir -p [OUTPUT_DIR]/repos
# 对每个 GitHub URL 规则集，克隆到 [OUTPUT_DIR]/repos/[名称]：
git clone --depth 1 https://github.com/org/repo [OUTPUT_DIR]/repos/repo-name
```

### 为每个已批准的规则集生成命令：
```bash
semgrep [--pro if available] --metrics=off [SEVERITY_FLAGS] [INCLUDE_FLAGS] --config [RULESET] --json -o [OUTPUT_DIR]/raw/[lang]-[ruleset].json --sarif-output=[OUTPUT_DIR]/raw/[lang]-[ruleset].sarif [TARGET] &
```

等待所有完成：
```bash
wait
```

### 清理克隆的仓库：
```bash
[ -n "[OUTPUT_DIR]" ] && rm -rf [OUTPUT_DIR]/repos
```

## 关键规则
- 只使用上面列出的规则集——不要添加或删除任何规则集
- 始终使用 --metrics=off（防止向 Semgrep 服务器发送遥测）
- 当 Pro 可用时使用 --pro（启用跨文件污点追踪）
- 如果扫描模式是 **important-only**，为每个命令添加 `--severity MEDIUM --severity HIGH --severity CRITICAL`
- 如果扫描模式是 **run-all**，不要添加严重性标志
- 使用 & 和 wait 并行运行所有规则集
- 对于 GitHub URL 规则集，始终克隆到 [OUTPUT_DIR]/repos/ 并使用本地路径作为 --config（不要直接传递 URL 给 semgrep——它对非标准 YAML 的仓库 URL 处理不可靠）
- 对语言特定的规则集添加 `--include` 标志（例如 p/python 使用 `--include="*.py"`）。**不要**对跨语言规则集如 p/security-audit、p/secrets 或第三方仓库添加 `--include`
- 所有扫描完成后，删除 [OUTPUT_DIR]/repos/ 以避免遗留克隆的仓库

## 输出
报告：
- 每个规则集的发现数量
- 任何扫描错误
- JSON 结果的文件路径（在 [OUTPUT_DIR]/raw/ 中）
- [如果使用 Pro] 注意检测到的任何跨文件发现
```

## 变量替换

| 变量 | 描述 | 示例 |
|------|------|------|
| `[LANGUAGE_CATEGORY]` | 正在扫描的语言组 | Python、JavaScript、Docker |
| `[LANGUAGE]` | 特定语言 | Python、TypeScript、Go |
| `[OUTPUT_DIR]` | 输出目录（绝对路径，在第 1 步解析） | /path/to/static_analysis_semgrep_1 |
| `[PRO_AVAILABLE]` | Pro 引擎是否可用 | true、false |
| `[SEVERITY_FLAGS]` | 严重性预过滤标志 | *（空）* 用于 run-all，`--severity MEDIUM --severity HIGH --severity CRITICAL` 用于 important-only |
| `[INCLUDE_FLAGS]` | 语言特定规则集的文件扩展名过滤器 | Python 规则集使用 `--include="*.py"`，跨语言规则集如 p/security-audit、p/secrets 或第三方仓库使用 *（空）* |
| `[RULESET]` | Semgrep 规则集标识符或本地克隆路径 | p/python、[OUTPUT_DIR]/repos/semgrep-rules |
| `[TARGET]` | 要扫描的目录的绝对路径 | /path/to/codebase |

## 示例：Python 扫描器任务

```
你是 Python 的 Semgrep 扫描器。

## 任务
为 Python 文件运行 Semgrep 扫描并将结果保存到 /path/to/static_analysis_semgrep_1/raw。

## Pro 引擎状态：true

## 扫描模式：run-all

## 已批准的规则集（来自用户确认的计划）
- p/python
- p/django
- p/security-audit
- p/secrets
- https://github.com/trailofbits/semgrep-rules

## 要运行的命令（并行）

### 先克隆 GitHub URL 规则集：
```bash
mkdir -p /path/to/static_analysis_semgrep_1/repos
git clone --depth 1 https://github.com/trailofbits/semgrep-rules /path/to/static_analysis_semgrep_1/repos/trailofbits
```

### 运行扫描：
```bash
semgrep --pro --metrics=off --include="*.py" --config p/python --json -o /path/to/static_analysis_semgrep_1/raw/python-python.json --sarif-output=/path/to/static_analysis_semgrep_1/raw/python-python.sarif /path/to/codebase &
semgrep --pro --metrics=off --include="*.py" --config p/django --json -o /path/to/static_analysis_semgrep_1/raw/python-django.json --sarif-output=/path/to/static_analysis_semgrep_1/raw/python-django.sarif /path/to/codebase &
semgrep --pro --metrics=off --config p/security-audit --json -o /path/to/static_analysis_semgrep_1/raw/python-security-audit.json --sarif-output=/path/to/static_analysis_semgrep_1/raw/python-security-audit.sarif /path/to/codebase &
semgrep --pro --metrics=off --config p/secrets --json -o /path/to/static_analysis_semgrep_1/raw/python-secrets.json --sarif-output=/path/to/static_analysis_semgrep_1/raw/python-secrets.sarif /path/to/codebase &
semgrep --pro --metrics=off --config /path/to/static_analysis_semgrep_1/repos/trailofbits --json -o /path/to/static_analysis_semgrep_1/raw/python-trailofbits.json --sarif-output=/path/to/static_analysis_semgrep_1/raw/python-trailofbits.sarif /path/to/codebase &
wait
```

### 清理克隆的仓库：
```bash
rm -rf /path/to/static_analysis_semgrep_1/repos
```

## 关键规则
- 只使用上面列出的规则集——不要添加或删除任何规则集
- 始终使用 --metrics=off
- 当 Pro 可用时使用 --pro
- 使用 & 和 wait 并行运行所有规则集
- 将 GitHub URL 规则集克隆到输出目录的 repos/ 子文件夹中，使用本地路径作为 --config
- 对语言特定的规则集（p/python、p/django）添加 --include="*.py"，但**不要**对 p/security-audit、p/secrets 或第三方仓库添加
- 扫描后删除 repos/

## 输出
报告：
- 每个规则集的发现数量
- 任何扫描错误
- JSON 结果的文件路径（在 raw/ 子目录中）
- 注意检测到的任何跨文件发现
```
