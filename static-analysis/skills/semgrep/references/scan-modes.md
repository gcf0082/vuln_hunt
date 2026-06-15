# 扫描模式参考

## 模式：Run All

使用所有规则集和严重级别进行全面扫描。当前默认行为。不应用过滤——所有发现都被报告和分类。

## 模式：Important Only

专注于高置信度安全漏洞。排除代码质量、最佳实践和低置信度审计发现。

### 预过滤：CLI 严重性标志

为每个 `semgrep` 命令添加这些标志：

```bash
--severity MEDIUM --severity HIGH --severity CRITICAL
```

这在扫描时排除 LOW/INFO 严重性发现，在后过滤前减少输出量。

### 后过滤：元数据标准

扫描后，过滤每个 JSON 结果文件，仅保留满足**所有**以下条件的发现：

| 元数据字段 | 可接受的值 | 原因 |
|-----------|-----------|------|
| `extra.metadata.category` | `"security"` | 排除正确性、最佳实践、可维护性、性能 |
| `extra.metadata.confidence` | `"MEDIUM"`、`"HIGH"` | 排除低精度规则（高误报率） |
| `extra.metadata.impact` | `"MEDIUM"`、`"HIGH"` | 排除低影响的信息性发现 |

**第三方规则**（Trail of Bits、0xdea、Decurity 等）可能没有 `confidence`/`impact`/`category` 元数据。**没有**这些元数据字段的发现**被保留**——我们无法过滤未标注的内容，且第三方规则通常是安全导向的。

### Semgrep 元数据背景

Semgrep 安全规则具有以下元数据字段（官方注册表中 `category: security` 必填）：

| 字段 | 用途 | 值 |
|------|------|-----|
| `severity`（顶层） | 规则总体严重性，由可能性×影响得出 | `LOW`、`MEDIUM`、`HIGH`、`CRITICAL` |
| `category` | 规则类别 | `security`、`correctness`、`best-practice`、`maintainability`、`performance` |
| `confidence` | 规则的真阳性率（精度） | `LOW`、`MEDIUM`、`HIGH` |
| `impact` | 漏洞被利用时的潜在损害 | `LOW`、`MEDIUM`、`HIGH` |
| `likelihood` | 漏洞可利用的可能性 | `LOW`、`MEDIUM`、`HIGH` |
| `subcategory` | 发现类型 | `vuln`、`audit`、`secure default` |

关键关系：`severity = f(likelihood, impact)`，而 `confidence` 是独立的（描述规则质量，而非漏洞严重性）。

### 后过滤 jq 命令

扫描后应用于每个 JSON 结果文件：

```bash
# 过滤单个结果文件
jq '{
  results: [.results[] |
    ((.extra.metadata.category // "security") | ascii_downcase) as $cat |
    ((.extra.metadata.confidence // "HIGH") | ascii_upcase) as $conf |
    ((.extra.metadata.impact // "HIGH") | ascii_upcase) as $imp |
    select(
      ($cat == "security") and
      ($conf == "MEDIUM" or $conf == "HIGH") and
      ($imp == "MEDIUM" or $imp == "HIGH")
    )
  ],
  errors: .errors,
  paths: .paths
}' "$f" > "${f%.json}-important.json"
```

默认值（`// "security"`、`// "HIGH"`）用于处理没有元数据的第三方规则——它们默认通过所有过滤器。

### 过滤目录中所有结果文件

原始扫描输出位于 `$OUTPUT_DIR/raw/`。过滤在与原始文件相同目录下创建 `*-important.json` 文件——原始文件保持不变。

```bash
# 对 raw/ 中所有扫描结果 JSON 文件应用 important-only 过滤
for f in "$OUTPUT_DIR/raw"/*-*.json; do
  [[ "$f" == *-triage.json || "$f" == *-important.json ]] && continue
  jq '{
    results: [.results[] |
      ((.extra.metadata.category // "security") | ascii_downcase) as $cat |
      ((.extra.metadata.confidence // "HIGH") | ascii_upcase) as $conf |
      ((.extra.metadata.impact // "HIGH") | ascii_upcase) as $imp |
      select(
        ($cat == "security") and
        ($conf == "MEDIUM" or $conf == "HIGH") and
        ($imp == "MEDIUM" or $imp == "HIGH")
      )
    ],
    errors: .errors,
    paths: .paths
  }' "$f" > "${f%.json}-important.json"
  BEFORE=$(jq '.results | length' "$f")
  AFTER=$(jq '.results | length' "${f%.json}-important.json")
  echo "$f: $BEFORE → $AFTER 个发现（过滤掉 $(( BEFORE - AFTER )) 个）"
done
```

### 扫描器任务修改

在 important-only 模式下，向扫描器模板添加 `[SEVERITY_FLAGS]`：

```bash
semgrep [--pro if available] --metrics=off [SEVERITY_FLAGS] --config [RULESET] --json -o [OUTPUT_DIR]/raw/[lang]-[ruleset].json --sarif-output=[OUTPUT_DIR]/raw/[lang]-[ruleset].sarif [TARGET] &
```

其中 `[SEVERITY_FLAGS]` 为：
- **Run all**：*（空）*
- **Important only**：`--severity MEDIUM --severity HIGH --severity CRITICAL`
