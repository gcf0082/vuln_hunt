---
name: sec-pattern-scanner
description: 针对单个文件快速分析，识别不安全协议/弱加密/TLS绕过/硬编码凭证等无需跨文件数据流即可确认的问题。
---

# sec-pattern-scanner

给一个文件路径，读取全文，凭安全知识识别不安全的代码模式，落盘结果。

## 执行流程

### 1. 确定目标文件

从用户消息提取文件路径。没给则反问。

### 2. 读取检测模式

读取同目录下的 `patterns.md`，作为风险类别**方向参考**，**不用于正则匹配**。

### 3. 读取文件

```
工具: Read
参数: filePath={目标文件}
```

通读全文。

### 4. 全文分析

以 `patterns.md` 中的风险类别作为指引方向，凭安全知识识别文件中所有不安全模式。

**识别范围**不限于 patterns.md 的精确写法，包括其变体：
- 同类别不同 API：`TrustAllCertManager` → 自定义 TrustManager 空实现、匿名类 `checkServerTrusted` 空方法体
- 语言/框架特有等价写法：Spring `.csrf(c -> c.disable())`、`.csrf(csrf -> csrf.disable())`
- 命名变体：`password` → `passwd` → `pwd` → `pwdSecret` → `passCode`
- 配置开关不同形式：`enabled: false` → `disable: true` → `off` → `0`
- 特定框架的配置：`ssl.verify=false`、`strictSSL=false`、`NODE_TLS_REJECT_UNAUTHORIZED=0`
- 注释中遗留的 TODO/FIXME/HACK 涉及安全操作的
- 其他明显有风险的自定义实现：自定义 HostnameVerifier 恒定返回 true、`Permission.all()` 覆盖等

**输出规则**：
- 每个独立行一个条目（含行号）
- 同类别连续配置块（如多行的 TLS 配置）可合并为一条，行号取起始行
- 注释行中明确标注安全风险的也纳入

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

- [ ] 以 `patterns.md` 所有类别为方向全部过了一遍
- [ ] 常见的变体写法也考虑到了
- [ ] 所有匹配全部列出，不抽样
- [ ] 结果已落盘到 `.vuln_agent_output/sec-pattern-scanner/` 对应路径
