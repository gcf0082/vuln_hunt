# SARIF jq 查询参考

用于常见 SARIF 解析任务的即用型 jq 查询。

## 基础探索

```bash
# 美化打印
jq '.' results.sarif

# 获取 SARIF 版本
jq '.version' results.sarif

# 列出所有运行的工具名称
jq '.runs[].tool.driver.name' results.sarif

# 统计运行数
jq '.runs | length' results.sarif
```

## 结果查询

```bash
# 总结果数
jq '[.runs[].results[]] | length' results.sarif

# 按严重级别统计数量
jq 'reduce .runs[].results[] as $r ({}; .[$r.level] += 1)' results.sarif

# 列出唯一规则 ID
jq '[.runs[].results[].ruleId] | unique | sort' results.sarif

# 按规则统计数量
jq '[.runs[].results[]] | group_by(.ruleId) | map({rule: .[0].ruleId, count: length}) | sort_by(-.count)' results.sarif
```

## 过滤结果

```bash
# 仅错误
jq '.runs[].results[] | select(.level == "error")' results.sarif

# 仅警告
jq '.runs[].results[] | select(.level == "warning")' results.sarif

# 按特定规则 ID
jq --arg rule "SQL_INJECTION" '.runs[].results[] | select(.ruleId == $rule)' results.sarif

# 按文件路径（包含）
jq --arg file "auth" '.runs[].results[] | select(.locations[].physicalLocation.artifactLocation.uri | contains($file))' results.sarif

# 按文件扩展名
jq '.runs[].results[] | select(.locations[].physicalLocation.artifactLocation.uri | test("\\.py$"))' results.sarif

# 多条件
jq '.runs[].results[] | select(.level == "error" and (.ruleId | startswith("SEC")))' results.sarif
```

## 提取位置信息

```bash
# 每个结果的文件和行号
jq '.runs[].results[] | {
  rule: .ruleId,
  file: .locations[0].physicalLocation.artifactLocation.uri,
  line: .locations[0].physicalLocation.region.startLine
}' results.sarif

# 唯一致命文件
jq '[.runs[].results[].locations[].physicalLocation.artifactLocation.uri] | unique | sort' results.sarif

# 按文件分组的结果
jq '[.runs[].results[] | {file: .locations[0].physicalLocation.artifactLocation.uri, result: .}] | group_by(.file) | map({file: .[0].file, count: length})' results.sarif
```

## 规则信息

```bash
# 列出所有规则及严重级别
jq '.runs[].tool.driver.rules[] | {id: .id, name: .name, level: .defaultConfiguration.level}' results.sarif

# 按 ID 获取规则描述
jq --arg id "RULE001" '.runs[].tool.driver.rules[] | select(.id == $id)' results.sarif

# 带帮助 URL 的规则
jq '.runs[].tool.driver.rules[] | select(.helpUri) | {id: .id, help: .helpUri}' results.sarif
```

## 指纹

```bash
# 带指纹的结果
jq '.runs[].results[] | select(.fingerprints or .partialFingerprints) | {rule: .ruleId, fp: (.fingerprints // .partialFingerprints)}' results.sarif

# 提取所有部分指纹
jq '[.runs[].results[].partialFingerprints] | add' results.sarif
```

## 聚合与报告

```bash
# 按严重级别和规则的摘要
jq '[.runs[].results[]] | group_by(.level) | map({level: .[0].level, rules: (group_by(.ruleId) | map({rule: .[0].ruleId, count: length}))})' results.sarif

# 最常见的 10 个规则
jq '[.runs[].results[]] | group_by(.ruleId) | map({rule: .[0].ruleId, count: length}) | sort_by(-.count) | .[0:10]' results.sarif

# 问题最多的文件
jq '[.runs[].results[] | .locations[0].physicalLocation.artifactLocation.uri] | group_by(.) | map({file: .[0], count: length}) | sort_by(-.count) | .[0:10]' results.sarif
```

## 输出格式化

```bash
# CSV 格式输出
jq -r '.runs[].results[] | [.ruleId, .level, .locations[0].physicalLocation.artifactLocation.uri, .locations[0].physicalLocation.region.startLine, .message.text] | @csv' results.sarif

# 制表符分隔
jq -r '.runs[].results[] | [.ruleId, .level, .locations[0].physicalLocation.artifactLocation.uri // "N/A"] | @tsv' results.sarif

# Markdown 表格
echo "| 规则 | 级别 | 文件 | 行号 |"
echo "|------|-------|------|------|"
jq -r '.runs[].results[] | "| \(.ruleId) | \(.level) | \(.locations[0].physicalLocation.artifactLocation.uri // "N/A") | \(.locations[0].physicalLocation.region.startLine // "N/A") |"' results.sarif
```

## 比较与差分

```bash
# 查找 file1 中有但 file2 中没有的规则
comm -23 <(jq -r '[.runs[].results[].ruleId] | unique | sort[]' file1.sarif) <(jq -r '[.runs[].results[].ruleId] | unique | sort[]' file2.sarif)

# 比较结果数量
echo "文件 1: $(jq '[.runs[].results[]] | length' file1.sarif)"
echo "文件 2: $(jq '[.runs[].results[]] | length' file2.sarif)"
```

## 转换

```bash
# 提取最小 SARIF（仅结果）
jq '{version: .version, runs: [.runs[] | {tool: {driver: {name: .tool.driver.name}}, results: .results}]}' results.sarif

# 过滤并创建仅包含错误的新 SARIF
jq '.runs[].results = [.runs[].results[] | select(.level == "error")]' results.sarif > errors-only.sarif

# 合并多个 SARIF 文件
jq -s '{version: "2.1.0", runs: [.[].runs[]]}' file1.sarif file2.sarif > merged.sarif
```

## 校验检查

```bash
# 检查版本是否为 2.1.0
jq -e '.version == "2.1.0"' results.sarif && echo "版本有效" || echo "版本无效"

# 检查是否为空结果
jq -e '[.runs[].results[]] | length > 0' results.sarif && echo "有结果" || echo "无结果"

# 验证所有结果都有位置信息
jq '[.runs[].results[] | select(.locations | length == 0)] | length' results.sarif
```
