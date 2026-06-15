---
name: differential-review
description: >
  Performs security-focused differential review of code changes (PRs, commits, diffs).
  Adapts analysis depth to codebase size, uses git history for context, calculates
  blast radius, checks test coverage, and generates comprehensive markdown reports.
  Automatically detects and prevents security regressions.
allowed-tools: Read Write Grep Glob Bash
---

# 差异安全审查

对 PR、commit 和 diff 执行安全导向的代码审查。

## 核心原则

1. **风险优先**：聚焦认证、加密、外部调用、值传递
2. **基于证据**：每个发现都必须有 git 历史、行号、攻击场景作为支撑
3. **自适应**：根据代码库规模调整分析深度（小/中/大）
4. **诚实**：明确说明覆盖范围限制和置信度
5. **产出驱动**：始终生成完整的 Markdown 报告文件

---

## 需拒绝的合理化借口

| 借口 | 为什么错 | 需执行的操作 |
|------|----------|------------|
| "小 PR，快速审一下" | Heartbleed 只有 2 行代码 | 按风险分类，而非按大小 |
| "我熟悉这个代码库" | 熟悉会导致盲点 | 建立显式的基线上下文 |
| "git 历史太费时" | 历史能揭示回归 | 绝不跳过 Phase 1 |
| "爆炸半径很明显" | 你会遗漏传递调用方 | 定量计算 |
| "没测试不关我的事" | 缺少测试=风险升级 | 在报告中标记，提升严重性 |
| "只是重构，没有安全影响" | 重构会破坏不变量 | 按 HIGH 分析，直到证明为 LOW |
| "我口头解释就行" | 没有产物=发现丢失 | 始终写报告 |

---

## 快速参考

### 代码库规模策略

| 代码库规模 | 策略 | 方法 |
|-----------|------|------|
| 小（<20 文件） | 深度分析 | 读取所有依赖，完整 git blame |
| 中（20-200） | 聚焦分析 | 1 跳依赖，优先文件 |
| 大（200+） | 外科手术 | 仅关键路径 |

### 风险级别触发器

| 风险级别 | 触发条件 |
|----------|----------|
| HIGH | 认证/授权变更、加密修改、外部调用、校验移除、敏感数据暴露 |
| MEDIUM | 业务逻辑变更、状态变化、新的公开 API |
| LOW | 注释、测试、UI、日志 |

---

## 工作流概览

```
Pre-Analysis → Phase 0: 分类 → Phase 1: 代码分析 → Phase 2: 测试覆盖
    ↓              ↓                    ↓                        ↓
Phase 3: 爆炸半径 → Phase 4: 深度上下文 → Phase 5: 对抗分析 → Phase 6: 报告
```

---

## 决策树

**开始审查？**

```
├─ 需要详细的逐步方法论？
│  └─ 阅读: methodology.md
│     (Pre-Analysis + Phases 0-4: 分类、代码分析、测试覆盖、爆炸半径)
│
├─ 分析 HIGH RISK 变更？
│  ├─ 阅读: adversarial.md
│  │  (Phase 5: 攻击者建模、利用场景、可利用性评级)
│  └─ 或委托给: adversarial-modeler agent
│     (自动攻击者建模，生成具体利用场景)
│
├─ 撰写最终报告？
│  └─ 阅读: reporting.md
│     (Phase 6: 报告结构、模板、格式指南)
│
├─ 查找特定漏洞模式？
│  └─ 阅读: patterns.md
│     (OWASP Top 10 模式：注入、授权失效、SSRF 等)
│
└─ 仅快速分类？
   └─ 使用上面的快速参考，跳过详细文档
```

---

## Agent

**`adversarial-modeler`** — 对 HIGH RISK 代码变更进行攻击者建模和利用场景构建。
遵循 5 步方法论（攻击者模型、攻击向量、可利用性评级、利用场景、基线交叉引用），
输出结构化漏洞报告。当需要对高风险变更进行 Phase 5 分析时，委托给此 agent。

---

## 质量检查清单

交付前确认：

- [ ] 所有变更文件已分析
- [ ] 对已移除的安全代码执行 git blame
- [ ] HIGH RISK 变更已计算爆炸半径
- [ ] 攻击场景是具体的（非泛泛而谈）
- [ ] 发现引用具体的行号+提交
- [ ] 报告文件已生成
- [ ] 已通知用户摘要

---



---

## 使用示例

### 快速分类（小 PR）
```
输入: 5 文件 PR，2 个 HIGH RISK 文件
策略: 使用快速参考
1. 按文件分类风险级别（2 HIGH, 3 LOW）
2. 仅聚焦 2 个 HIGH 文件
3. Git blame 被移除的代码
4. 生成最小报告
时间: ~30 分钟
```

### 标准审查（中等代码库）
```
输入: 80 个文件，12 个 HIGH RISK 变更
策略: 聚焦（参见 methodology.md）
1. 对 HIGH RISK 文件执行完整工作流
2. 对 MEDIUM 进行表面扫描
3. 跳过 LOW 风险文件
4. 生成包含所有章节的完整报告
时间: ~3-4 小时
```

---

## 不使用场景

- **全新的代码库**（没有基线可比较）
- **仅文档变更**（无安全影响）
- **格式化/代码风格**（无实质变更）
- **用户明确要求仅快速摘要**（他们承担风险）

这些情况请使用标准代码审查而非本 skill。

---

## 红旗标志（停下并调查）

**需要立即升级的触发器：**
- 从 "security"、"CVE" 或 "fix" 提交中移除代码
- 移除授权/认证检查
- 移除输入校验未加替代
- 增加外部调用但未加安全检查
- HIGH RISK 变更 + 高爆炸半径（50+ 调用方）

即使在快速分类中，这些模式也需要进行对抗分析。

---

## 最佳实践

**应该做：**
- 对被移除的代码先做 git blame
- 尽早计算爆炸半径以确定优先级
- 生成具体的攻击场景
- 引用具体的行号和提交
- 诚实说明覆盖范围的限制
- 始终生成输出文件

**不应该做：**
- 跳过 git 历史分析
- 做出没有证据的通用发现
- 在时间有限时声称完整分析
- 忘记检查测试覆盖
- 遗漏高爆炸半径变更
- 仅在聊天中输出报告（需要文件）

---

## 支持文档

- **[methodology.md](methodology.md)** — 详细的逐步工作流（Phases 0-4）
- **[adversarial.md](adversarial.md)** — 攻击者建模和利用场景（Phase 5）
- **[reporting.md](reporting.md)** — 报告结构和格式（Phase 6）
- **[patterns.md](patterns.md)** — 通用漏洞模式参考（OWASP Top 10）
