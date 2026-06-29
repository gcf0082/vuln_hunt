---
name: sec-pattern-scanner
description: 针对单个文件快速分析，识别不安全协议/弱加密/TLS绕过/硬编码凭证等无需跨文件数据流即可确认的问题。
---

# sec-pattern-scanner

给一个文件路径，读取文件内容，逐行比对检测模式，落盘结果。

## 执行流程

### 1. 确定目标文件

从用户消息提取文件路径。没给则反问。

### 2. 读取检测模式

读取同目录下的 `patterns.md`，得到所有风险/类别/正则模式/理由。

### 3. 读取文件

```
工具: Read
参数: filePath={目标文件}
```

### 4. 逐行检查

逐行读文件内容，对每一行比对 `patterns.md` 中的正则模式：

- 匹配 → 记录：风险/类别/行号/代码行/理由
- 注释行跳过（行内容以 `//` `#` `<!--` 开头）

**代码行处理**：
- 去除首尾空白
- 超过 120 字符截断加 `...`

### 5. 落盘

结果写入 `.vuln_agent_output/sec-pattern-scanner/` 下，子路径镜像源文件路径。

**路径规则**：
```
源文件: /root/target/src/main/java/com/acme/HttpUtil.java
输出:   .vuln_agent_output/sec-pattern-scanner/src/main/java/com/acme/HttpUtil.java.md
```

```
工具: Write
参数: filePath={.vuln_agent_output/sec-pattern-scanner/相对路径.md}
参数: content={分析结果}
```

**输出格式**（有匹配时）：

```
文件: src/main/java/com/acme/HttpUtil.java
结果: 2 个匹配

---
风险: 高
类别: 不安全协议
行号: 45
代码: return conn.openConnection(new URL("http://api.internal.com/"))
理由: 使用明文 HTTP 协议，数据未加密传输，可被中间人窃取或篡改
---
风险: 中
类别: 信息泄露
行号: 102
代码: e.printStackTrace();
理由: 打印完整堆栈跟踪到标准输出，可能泄露内部路径和逻辑
```

无匹配时：

```
文件: src/main/java/com/acme/HttpUtil.java
结果: 0 个匹配
```

### 6. 回复确认

落盘后用一句简短汇报：

```
src/main/java/com/acme/HttpUtil.java → 2 个匹配 (.vuln_agent_output/sec-pattern-scanner/)
```

## 不遗漏检查

- [ ] `patterns.md` 中所有模式均已比对过
- [ ] 注释行已跳过
- [ ] 所有匹配全部列出，不抽样
- [ ] 结果已落盘到 `.vuln_agent_output/sec-pattern-scanner/` 对应路径
