---
name: sec-pattern-scanner
description: 单文件级快速漏洞模式扫描，识别不安全协议/弱加密/TLS绕过/硬编码凭证等无需跨文件数据流即可确认的问题。
---

# sec-pattern-scanner

单文件可确定的漏洞模式扫描。不跨文件追踪数据流，仅靠当前文件内容即可判定。

## 执行流程

### 1. 确定目标目录

从用户消息提取目标目录。没给则反问。

### 2. 读取检测模式

读取同目录下的 `patterns.md`，逐条提取 grep 模式。

### 3. 逐条搜索

对每条模式执行：

```bash
grep -rn --include="*.java" --include="*.py" --include="*.go" --include="*.js" \
  --include="*.ts" --include="*.php" --include="*.rb" --include="*.rs" \
  --include="*.yml" --include="*.yaml" --include="*.properties" \
  --include="*.xml" --include="*.conf" --include="*.cfg" --include="*.env" \
  --include="Dockerfile*" --include="*.sh" --include="*.bash" \
  -E "{grep_pattern}" {target_dir} \
  | grep -v "/test/" | grep -v "/tests/" | grep -v "/__tests__/" \
  | grep -v "/spec/" | grep -v "/node_modules/" | grep -v "/vendor/"
```

排除路径和语言可按项目实际结构调整。

### 4. 整理输出

每个匹配结果一条记录，`---` 分隔，按风险高→中排序，同风险按类别集中。

```
---
风险: 高
类别: 不安全协议
文件路径: src/main/java/com/acme/HttpUtil.java
行号: 45
代码: return conn.openConnection(new URL("http://api.internal.com/"))
理由: 使用明文 HTTP 协议，数据未加密传输，可被中间人窃取或篡改
---
```

每行代码需**去除首尾空白**（`sed 's/^[[:space:]]*//;s/[[:space:]]*$//'`），过长（>120 字符）则截断至 120 字符后加 `...`。

### 5. 无匹配时

```
---
风险: -
类别: -
文件路径: (无匹配项)
行号: -
代码: -
理由: 目标目录中未发现单文件可识别的安全模式
---
```

## 不遗漏检查

- [ ] `patterns.md` 中所有模式均已搜索完毕
- [ ] 每条结果包含 风险 + 类别 + 文件路径 + 行号 + 代码 + 理由
- [ ] 所有结果全部列出，不抽样
- [ ] 排除路径（test/node_modules/vendor 等）已过滤
- [ ] 代码行已去空白、截断处理
