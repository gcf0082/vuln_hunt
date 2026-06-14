---
name: fp-check
description: "Systematically verifies suspected security bugs to eliminate false positives. Produces TRUE POSITIVE or FALSE POSITIVE verdicts with documented evidence for each bug."
allowed-tools: Read Grep Glob LSP Bash Task Write Edit AskUserQuestion TaskCreate TaskUpdate TaskList TaskGet
---

# 误报检查 (False Positive Check)

## 使用场景

- "这个 Bug 是真的吗？"或"这是真实漏洞吗？"
- "这是误报吗？"或"验证这个发现"
- "检查这个漏洞是否可利用"
- 任何验证或确认特定可疑 Bug 的请求

## 不使用场景

- 发现或寻找 Bug（"找 Bug"、"安全分析"、"审计代码"）
- 针对代码风格、性能或可维护性的一般性代码审查
- 功能开发、重构或非安全任务
- 用户明确要求快速扫描而不做验证时

## 需要拒绝的合理化借口

如果你发现自己产生以下任何想法，请立即停止。

| 合理化借口 | 错误原因 | 应采取的应对措施 |
|---|---|---|
| "快速分析剩余 Bug" | 每个 Bug 都需要完整验证 | 返回任务列表，逐个完成所有阶段的验证 |
| "这个模式看起来很危险，所以它是漏洞" | 模式识别不等于分析 | 完成数据流追溯后再做结论 |
| "为了效率跳过完整验证" | 不允许部分分析 | 按所选验证路径执行所有步骤 |
| "代码看起来不安全，不追溯数据流就直接报告" | 看起来不安全的代码可能有上游验证 | 追溯从 source 到 sink 的完整路径 |
| "类似的代码在其他地方就是漏洞" | 每个上下文有不同的验证、调用者和保护措施 | 独立验证当前实例 |
| "这明显是严重漏洞" | LLM 倾向于看到 Bug 并夸大严重性 | 完成魔鬼代言人审查；用证据证明 |

---

## 第 0 步：理解漏洞主张和上下文

在进行分析之前，用自己的话复述该 Bug。如果你无法清晰地做到这一点，请使用 AskUserQuestion 向用户请求澄清。一半的误报在这一步就会瓦解——当精确复述时，漏洞主张本身就不合逻辑。

记录：

- **确切的漏洞主张是什么？**（例如："当 `content_length` 超过 4096 时，`parse_header()` 中存在堆缓冲区溢出"）
- **声称的根本原因是什么？**（例如："第 142 行 `memcpy` 之前缺少边界检查"）
- **假设的触发方式是什么？**（例如："攻击者发送带有超大 Content-Length 头的 HTTP 请求"）
- **声称的影响是什么？**（例如："通过受控的堆破坏实现远程代码执行"）
- **威胁模型是什么？** 代码运行的权限级别是什么？是否在沙箱中？攻击者在触发此 Bug 之前已经能做什么？（例如："未经认证的远程攻击者 vs 有权限的本地用户"；"运行在 Chrome 渲染沙箱内" vs "以 root 身份运行，无沙箱"）
- **漏洞类别是什么？** 对漏洞进行分类，并查阅 [bug-class-verification.md]({baseDir}/references/bug-class-verification.md) 以获取类特定的验证要求，这些要求补充了下面的通用阶段。
- **执行上下文**：正常执行期间何时以及如何到达此代码路径？
- **调用者分析**：哪些函数调用此代码，它们施加了什么输入约束？
- **架构上下文**：这是否是拥有多层保护的更大安全系统的一部分？
- **历史上下文**：此代码区域是否有最近的更改、已知问题或以前的安全审查？

## 路径选择：标准验证 vs 深度验证

第 0 步之后，选择验证路径。

### 标准验证

当以下所有条件成立时使用：

- 清晰、具体的漏洞主张（非模糊或歧义）
- 单个组件——漏洞路径中无跨组件交互
- 熟知的安全漏洞类别（缓冲区溢出、SQL 注入、XSS、整数溢出等）
- 触发机制中无并发或异步
- 从 source 到 sink 的直截了当的数据流

按照 [standard-verification.md]({baseDir}/references/standard-verification.md) 执行。无需创建任务——按线性检查表逐步工作，内联记录发现。

### 深度验证

当以下任一条件成立时使用：

- 歧义的主张，可以以多种方式解释
- 跨组件的漏洞路径（数据流经 3 个以上模块或服务）
- 触发机制中的竞态条件、TOCTOU 或并发
- 没有明确规范可对照验证的逻辑漏洞
- 标准验证无定论或已升级
- 用户明确请求完整验证

按照 [deep-verification.md]({baseDir}/references/deep-verification.md) 执行。创建完整的任务依赖图并使用插件的代理执行各个阶段。

### 默认

从标准开始。标准验证有两个内置的升级检查点，当复杂性超出线性检查表时转入深度验证。

## 批量分类

当同时验证多个 Bug 时：

1. 首先对所有 Bug 执行第 0 步——复述主张通常会立即消除明显的误报
2. 独立为每个 Bug 选择验证路径（有些可能是标准，有些是深度）
3. 先处理所有标准路径的 Bug，再处理深度路径的 Bug
4. 所有 Bug 验证完成后，检查**利用链**——单独未通过门控审查的发现可能组合形成可行的攻击

## 最终总结

处理完所有可疑 Bug 后，提供：

1. **计数**：X 个真实漏洞，Y 个误报
2. **真实漏洞列表**：每个附带简短的漏洞描述
3. **误报列表**：每个附带简要的拒绝原因

## 参考资料

- [标准验证]({baseDir}/references/standard-verification.md) — 针对简单 Bug 的线性单遍检查表
- [深度验证]({baseDir}/references/deep-verification.md) — 针对复杂 Bug 的完整基于任务的工作流
- [门控审查]({baseDir}/references/gate-reviews.md) — 六个必经门控和裁定格式
- [漏洞类别验证]({baseDir}/references/bug-class-verification.md) — 针对内存破坏、逻辑漏洞、竞态条件、整数问题、密码学、注入、信息泄露、DoS 和反序列化的类特定验证要求
- [误报模式]({baseDir}/references/false-positive-patterns.md) — 13 项检查表和常见误报模式的红旗标志
- [证据模板]({baseDir}/references/evidence-templates.md) — 数据流、数学证明、攻击者控制和魔鬼代言人审查的文档模板
