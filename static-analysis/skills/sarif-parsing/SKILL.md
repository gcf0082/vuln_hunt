---
name: sarif-parsing
description: >-
  Parses and processes SARIF files from static analysis tools like CodeQL, Semgrep, or other
  scanners. Triggers on "parse sarif", "read scan results", "aggregate findings", "deduplicate
  alerts", or "process sarif output". Handles filtering, deduplication, format conversion, and
  CI/CD integration of SARIF data. Does NOT run scans — use the Semgrep or CodeQL skills for that.
allowed-tools: Bash Read Glob Grep
---

# SARIF 解析最佳实践

你是 SARIF 解析专家。你的职责是帮助用户有效地读取、分析和处理来自静态分析工具的 SARIF 文件。

## 使用场景

在以下情况下使用本 skill：
- 读取或解释静态分析扫描结果（SARIF 格式）
- 聚合来自多个安全工具的发现
- 去重或过滤安全告警
- 从 SARIF 文件中提取特定漏洞
- 将 SARIF 数据集成到 CI/CD 流水线
- 将 SARIF 输出转换为其他格式

## 不使用场景

不要使用本 skill 进行：
- 运行静态分析扫描（使用 CodeQL 或 Semgrep skill）
- 编写 CodeQL 或 Semgrep 规则（使用各自的 skill）
- 直接分析源代码（SARIF 用于处理现有的扫描结果）
- 在没有 SARIF 输入的情况下对发现进行分类（使用 variant-analysis 或审计 skill）

## SARIF 结构概述

SARIF 2.1.0 是当前的 OASIS 标准。每个 SARIF 文件具有以下层次结构：

```
sarifLog
├── version: "2.1.0"
├── $schema:（可选，启用 IDE 验证）
└── runs[]（分析运行数组）
    ├── tool
    │   ├── driver
    │   │   ├── name（必需）
    │   │   ├── version
    │   │   └── rules[]（规则定义）
    │   └── extensions[]（插件）
    ├── results[]（发现）
    │   ├── ruleId
    │   ├── level（error/warning/note）
    │   ├── message.text
    │   ├── locations[]
    │   │   └── physicalLocation
    │   │       ├── artifactLocation.uri
    │   │       └── region（startLine、startColumn 等）
    │   ├── fingerprints{}
    │   └── partialFingerprints{}
    └── artifacts[]（扫描的文件元数据）
```

### 为什么指纹很重要

没有稳定的指纹，你无法跨运行追踪发现：

- **基线比较**："这是新发现还是之前见过？"
- **回归检测**："这个 PR 引入了新漏洞吗？"
- **抑制**："在未来的运行中忽略这个已知误报"

工具报告不同的路径（`/path/to/project/` vs `/github/workspace/`），因此基于路径的匹配会失败。指纹哈希*内容*（代码片段、规则 ID、相对位置）以创建独立于环境的稳定标识符。

## 工具选择指南

| 使用场景 | 工具 | 安装 |
|----------|------|------|
| 快速 CLI 查询 | jq | `brew install jq` / `apt install jq` |
| Python 脚本（简单） | pysarif | `pip install pysarif` |
| Python 脚本（高级） | sarif-tools | `pip install sarif-tools` |
| .NET 应用程序 | SARIF SDK | NuGet 包 |
| JavaScript/Node.js | sarif-js | npm 包 |
| Go 应用程序 | garif | `go get github.com/chavacava/garif` |
| 验证 | SARIF Validator | sarifweb.azurewebsites.net |

## 策略 1：使用 jq 快速分析

用于快速探索和一次性查询：

```bash
# 美化打印文件
jq '.' results.sarif

# 统计总发现数
jq '[.runs[].results[]] | length' results.sarif

# 列出所有触发的规则 ID
jq '[.runs[].results[].ruleId] | unique' results.sarif

# 仅提取错误
jq '.runs[].results[] | select(.level == "error")' results.sarif

# 获取带文件位置的发现
jq '.runs[].results[] | {
  rule: .ruleId,
  message: .message.text,
  file: .locations[0].physicalLocation.artifactLocation.uri,
  line: .locations[0].physicalLocation.region.startLine
}' results.sarif

# 按严重性过滤并按规则统计数量
jq '[.runs[].results[] | select(.level == "error")] | group_by(.ruleId) | map({rule: .[0].ruleId, count: length})' results.sarif

# 提取特定文件的发现
jq --arg file "src/auth.py" '.runs[].results[] | select(.locations[].physicalLocation.artifactLocation.uri | contains($file))' results.sarif
```

## 策略 2：使用 pysarif 的 Python 方法

用于带有完整对象模型的编程式访问：

```python
from pysarif import load_from_file, save_to_file

# 加载 SARIF 文件
sarif = load_from_file("results.sarif")

# 遍历运行和结果
for run in sarif.runs:
    tool_name = run.tool.driver.name
    print(f"工具: {tool_name}")

    for result in run.results:
        print(f"  [{result.level}] {result.rule_id}: {result.message.text}")

        if result.locations:
            loc = result.locations[0].physical_location
            if loc and loc.artifact_location:
                print(f"    文件: {loc.artifact_location.uri}")
                if loc.region:
                    print(f"    行号: {loc.region.start_line}")

# 保存修改后的 SARIF
save_to_file(sarif, "modified.sarif")
```

## 策略 3：使用 sarif-tools 的 Python 方法

用于聚合、报告和 CI/CD 集成：

```python
from sarif import loader

# 加载单个文件
sarif_data = loader.load_sarif_file("results.sarif")

# 或加载多个文件
sarif_set = loader.load_sarif_files(["tool1.sarif", "tool2.sarif"])

# 获取摘要报告
report = sarif_data.get_report()

# 按严重性获取直方图
errors = report.get_issue_type_histogram_for_severity("error")
warnings = report.get_issue_type_histogram_for_severity("warning")

# 过滤结果
high_severity = [r for r in sarif_data.get_results()
                 if r.get("level") == "error"]
```

**sarif-tools CLI 命令：**

```bash
# 发现摘要
sarif summary results.sarif

# 列出所有结果及详情
sarif ls results.sarif

# 按严重性获取结果
sarif ls --level error results.sarif

# 比较两个 SARIF 文件（查找新增/修复的问题）
sarif diff baseline.sarif current.sarif

# 转换为其他格式
sarif csv results.sarif > results.csv
sarif html results.sarif > report.html
```

## 策略 4：聚合多个 SARIF 文件

当组合来自多个工具的结果时：

```python
import json
from pathlib import Path

def aggregate_sarif_files(sarif_paths: list[str]) -> dict:
    """将多个 SARIF 文件合并为一个。"""
    aggregated = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": []
    }

    for path in sarif_paths:
        with open(path) as f:
            sarif = json.load(f)
            aggregated["runs"].extend(sarif.get("runs", []))

    return aggregated

def deduplicate_results(sarif: dict) -> dict:
    """基于指纹移除重复发现。"""
    seen_fingerprints = set()

    for run in sarif["runs"]:
        unique_results = []
        for result in run.get("results", []):
            # 使用 partialFingerprints 或从位置创建 key
            fp = None
            if result.get("partialFingerprints"):
                fp = tuple(sorted(result["partialFingerprints"].items()))
            elif result.get("fingerprints"):
                fp = tuple(sorted(result["fingerprints"].items()))
            else:
                # 回退：从规则 + 位置创建指纹
                loc = result.get("locations", [{}])[0]
                phys = loc.get("physicalLocation", {})
                fp = (
                    result.get("ruleId"),
                    phys.get("artifactLocation", {}).get("uri"),
                    phys.get("region", {}).get("startLine")
                )

            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                unique_results.append(result)

        run["results"] = unique_results

    return sarif
```

## 策略 5：提取可操作的数据

```python
import json
from dataclasses import dataclass
from typing import Optional

@dataclass
class Finding:
    rule_id: str
    level: str
    message: str
    file_path: Optional[str]
    start_line: Optional[int]
    end_line: Optional[int]
    fingerprint: Optional[str]

def extract_findings(sarif_path: str) -> list[Finding]:
    """从 SARIF 文件中提取结构化发现。"""
    with open(sarif_path) as f:
        sarif = json.load(f)

    findings = []
    for run in sarif.get("runs", []):
        for result in run.get("results", []):
            loc = result.get("locations", [{}])[0]
            phys = loc.get("physicalLocation", {})
            region = phys.get("region", {})

            findings.append(Finding(
                rule_id=result.get("ruleId", "unknown"),
                level=result.get("level", "warning"),
                message=result.get("message", {}).get("text", ""),
                file_path=phys.get("artifactLocation", {}).get("uri"),
                start_line=region.get("startLine"),
                end_line=region.get("endLine"),
                fingerprint=next(iter(result.get("partialFingerprints", {}).values()), None)
            ))

    return findings

# 过滤和优先级排序
def prioritize_findings(findings: list[Finding]) -> list[Finding]:
    """按严重性排序发现。"""
    severity_order = {"error": 0, "warning": 1, "note": 2, "none": 3}
    return sorted(findings, key=lambda f: severity_order.get(f.level, 99))
```

## 常见陷阱及解决方案

### 1. 路径归一化问题

不同工具报告路径的方式不同（绝对路径、相对路径、URI 编码）：

```python
from urllib.parse import unquote
from pathlib import Path

def normalize_path(uri: str, base_path: str = "") -> str:
    """将 SARIF 工件 URI 归一化为一致路径。"""
    # 如果存在，移除 file:// 前缀
    if uri.startswith("file://"):
        uri = uri[7:]

    # URL 解码
    uri = unquote(uri)

    # 处理相对路径
    if not Path(uri).is_absolute() and base_path:
        uri = str(Path(base_path) / uri)

    # 归一化分隔符
    return str(Path(uri))
```

### 2. 跨运行指纹不匹配

如果以下情况，指纹可能不匹配：
- 不同环境中的文件路径不同
- 工具版本改变了指纹算法
- 代码被重新格式化（改变行号）

**解决方案：** 使用多种指纹策略：

```python
def compute_stable_fingerprint(result: dict, file_content: str = None) -> str:
    """计算与环境无关的指纹。"""
    import hashlib

    components = [
        result.get("ruleId", ""),
        result.get("message", {}).get("text", "")[:100],  # 前 100 个字符
    ]

    # 如果可用，添加代码片段
    if file_content and result.get("locations"):
        region = result["locations"][0].get("physicalLocation", {}).get("region", {})
        if region.get("startLine"):
            lines = file_content.split("\n")
            line_idx = region["startLine"] - 1
            if 0 <= line_idx < len(lines):
                # 归一化空白
                components.append(lines[line_idx].strip())

    return hashlib.sha256("".join(components).encode()).hexdigest()[:16]
```

### 3. 缺失或不完整的数据

SARIF 允许许多可选字段。始终使用防御性访问：

```python
def safe_get_location(result: dict) -> tuple[str, int]:
    """安全地从结果中提取文件和行号。"""
    try:
        loc = result.get("locations", [{}])[0]
        phys = loc.get("physicalLocation", {})
        file_path = phys.get("artifactLocation", {}).get("uri", "unknown")
        line = phys.get("region", {}).get("startLine", 0)
        return file_path, line
    except (IndexError, KeyError, TypeError):
        return "unknown", 0
```

### 4. 大文件性能

对于非常大的 SARIF 文件（100MB+）：

```python
import ijson  # pip install ijson

def stream_results(sarif_path: str):
    """流式处理结果，无需加载整个文件。"""
    with open(sarif_path, "rb") as f:
        # 流式处理 results 数组
        for result in ijson.items(f, "runs.item.results.item"):
            yield result
```

### 5. Schema 验证

在处理之前验证，以捕获格式错误的文件：

```bash
# 使用 ajv-cli
npm install -g ajv-cli
ajv validate -s sarif-schema-2.1.0.json -d results.sarif

# 使用 Python jsonschema
pip install jsonschema
```

```python
from jsonschema import validate, ValidationError
import json

def validate_sarif(sarif_path: str, schema_path: str) -> bool:
    """根据 schema 验证 SARIF 文件。"""
    with open(sarif_path) as f:
        sarif = json.load(f)
    with open(schema_path) as f:
        schema = json.load(f)

    try:
        validate(sarif, schema)
        return True
    except ValidationError as e:
        print(f"验证错误: {e.message}")
        return False
```

## CI/CD 集成模式

### GitHub Actions

```yaml
- name: 上传 SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif

- name: 检查高严重性问题
  run: |
    HIGH_COUNT=$(jq '[.runs[].results[] | select(.level == "error")] | length' results.sarif)
    if [ "$HIGH_COUNT" -gt 0 ]; then
      echo "找到 $HIGH_COUNT 个高严重性问题"
      exit 1
    fi
```

### 失败于新问题

```python
from sarif import loader

def check_for_regressions(baseline: str, current: str) -> int:
    """返回不在基线中的新问题数量。"""
    baseline_data = loader.load_sarif_file(baseline)
    current_data = loader.load_sarif_file(current)

    baseline_fps = {get_fingerprint(r) for r in baseline_data.get_results()}
    new_issues = [r for r in current_data.get_results()
                  if get_fingerprint(r) not in baseline_fps]

    return len(new_issues)
```

## 关键原则

1. **先验证**：处理前检查 SARIF 结构
2. **处理可选字段**：许多字段是可选的；使用防御性访问
3. **归一化路径**：工具报告路径的方式不同；尽早归一化
4. **明智地使用指纹**：结合多种策略实现稳定的去重
5. **流式处理大文件**：对 100MB+ 文件使用 ijson 或类似工具
6. **谨慎聚合**：合并文件时保留工具元数据

## Skill 资源

现成的查询模板，参见 [{baseDir}/resources/jq-queries.md]({baseDir}/resources/jq-queries.md)：
- 40+ 个常用 SARIF 操作的 jq 查询
- 严重性过滤、规则提取、聚合模式

Python 工具，参见 [{baseDir}/resources/sarif_helpers.py]({baseDir}/resources/sarif_helpers.py)：
- `normalize_path()`——处理工具特定路径格式
- `compute_fingerprint()`——忽略路径的稳定指纹
- `deduplicate_results()`——跨运行移除重复

## 参考链接

- [OASIS SARIF 2.1.0 规范](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Microsoft SARIF 教程](https://github.com/microsoft/sarif-tutorials)
- [SARIF SDK (.NET)](https://github.com/microsoft/sarif-sdk)
- [sarif-tools (Python)](https://github.com/microsoft/sarif-tools)
- [pysarif (Python)](https://github.com/Kjeld-P/pysarif)
- [GitHub SARIF 支持](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)
- [SARIF Validator](https://sarifweb.azurewebsites.net/)
