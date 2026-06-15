# SARIF 处理

用于处理 CodeQL SARIF 输出的 jq 命令。适用于用户提供的任何 SARIF 文件路径。

> **SARIF 结构说明：** `security-severity` 和 `level` 存储在规则定义中（`.runs[].tool.driver.rules[]`），而非单个结果对象上。结果通过 `ruleIndex` 引用规则。下面的 jq 命令将结果与其规则元数据关联。
>
> **可移植性说明：** 这些 jq 模式假定 CodeQL SARIF 输出中 `ruleIndex` 已填充。对于来自其他工具（如 Semgrep）的 SARIF，请改用基于 `ruleId` 的查找。

**用法：** 将 `INPUT_SARIF` 设置为用户的 SARIF 文件路径，然后运行相关命令。处理后的输出文件使用 `_processed.sarif` 后缀。

```bash
# 设置输入 SARIF 文件路径（用户提供）
INPUT_SARIF="/path/to/results.sarif"
```

## 统计发现数量

```bash
jq '.runs[].results | length' "$INPUT_SARIF"
```

## 按 SARIF 级别汇总

```bash
jq -r '
  .runs[] |
  . as $run |
  .results[] |
  ($run.tool.driver.rules[.ruleIndex].defaultConfiguration.level // "unknown")
' "$INPUT_SARIF" \
  | sort | uniq -c | sort -rn
```

## 按安全严重性汇总（最适用于分类）

```bash
jq -r '
  .runs[] |
  . as $run |
  .results[] |
  ($run.tool.driver.rules[.ruleIndex].properties["security-severity"] // "none") + " | " +
  .ruleId + " | " +
  (.locations[0].physicalLocation.artifactLocation.uri // "?") + ":" +
  ((.locations[0].physicalLocation.region.startLine // 0) | tostring) + " | " +
  (.message.text // "no message" | .[0:80])
' "$INPUT_SARIF" | sort -rn | head -20
```

## 按规则汇总

```bash
jq -r '.runs[].results[] | .ruleId' "$INPUT_SARIF" \
  | sort | uniq -c | sort -rn
```

## 重要-only 后过滤

过滤掉 `security-severity` < 6.0 的中等精度结果。当用户只需要高置信度发现时使用。

```bash
INPUT_SARIF="/path/to/results.sarif"
OUTPUT_SARIF="${INPUT_SARIF%.sarif}_processed.sarif"

jq '
  .runs[] |= (
    . as $run |
    .results = [
      .results[] |
      ($run.tool.driver.rules[.ruleIndex].properties.precision // "unknown") as $prec |
      ($run.tool.driver.rules[.ruleIndex].properties["security-severity"] // null) as $raw_sev |
      (if $prec == "medium" then ($raw_sev // "0" | tonumber) else 10 end) as $sev |
      select(
        ($prec == "high") or ($prec == "very-high") or ($prec == "unknown") or
        ($prec == "medium" and $sev >= 6.0)
      )
    ]
  )
' "$INPUT_SARIF" > "$OUTPUT_SARIF"
```

## 按文件筛选结果

提取特定文件的所有发现：

```bash
TARGET_FILE="src/sensitive/path.java"
jq -r --arg target "$TARGET_FILE" '
  .runs[].results[] |
  select(.locations[0].physicalLocation.artifactLocation.uri | endswith($target))
  | (.ruleId) + ":" + (.locations[0].physicalLocation.region.startLine | tostring) +
    " (" + (.message.text // "no message") + ")"
' "$INPUT_SARIF"
```
