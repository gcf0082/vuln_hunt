# 质量评估

如何评估 CodeQL SARIF 输出质量。重点关注结果集的评估，而非构建过程。

## 分析结果分布

评估 SARIF 输出是否全面或可能遗漏发现。

```bash
INPUT_SARIF="/path/to/results.sarif"

# 1. 统计结果数量
TOTAL=$(jq '.runs[].results | length' "$INPUT_SARIF")
echo "总发现数: $TOTAL"

# 2. 触发的唯一规则数
UNIQUE_RULES=$(jq -r '.runs[].results[] | .ruleId' "$INPUT_SARIF" | sort -u | wc -l)
echo "触发的唯一规则数: $UNIQUE_RULES"

# 3. 覆盖的语言
LANGUAGES=$(jq -r '.runs[].tool.driver.name' "$INPUT_SARIF" | sort -u)
echo "语言: $LANGUAGES"
```

## 零发现调查

如果 SARIF 输出为零结果，调查可能的原因：

| 原因 | 如何检测 | 缓解措施 |
|------|----------|----------|
| 数据库质量 | 检查数据库元数据是否显示低提取量 | 在适当时重建 |
| 缺少模型 | 项目使用了 CodeQL 未建模的自定义封装 | 添加数据扩展 |
| 错误的查询包 | 仅使用了基础套件 | 使用更广泛的查询包重新运行 |
| 静默过滤 | 套件模板过滤掉了所有查询 | 检查套件组成 |
| 语言不匹配 | 数据库语言与预期代码不符 | 验证数据库选择 |

## CodeQL 版本检查

使用的 CodeQL 版本影响查询可用性：

```bash
jq -r '.runs[].tool.driver.version' "$INPUT_SARIF"
```

与当前发布说明对比，检查已知问题或缺失查询。
