# Differential Review（差异审查）

安全导向的代码差异审查工具，包含 git 历史分析和爆炸半径评估。

## 使用场景

以下情况使用本 skill：
- 审查 PR、commit 或 diff 中的安全漏洞
- 检测安全回归（重新引入的漏洞）
- 分析代码变更的爆炸半径
- 检查变更代码的测试覆盖缺口

## 功能说明

- **风险优先分析** — 优先关注认证、加密、外部调用、值传递
- **Git 历史分析** — 使用 blame 理解代码存在的原因，检测回归
- **爆炸半径计算** — 通过计数调用方来量化影响
- **测试覆盖缺口** — 识别未测试的变更
- **自适应深度** — 根据代码库规模调整分析（小/中/大）

## 文档结构

### 核心入口
- **[SKILL.md](skills/differential-review/SKILL.md)** — 主入口，含快速参考、决策树、质量清单

### 支持文档
- **[methodology.md](skills/differential-review/methodology.md)** — 详细的逐步工作流
  - Pre-Analysis: 基线上下文构建
  - Phase 0: 输入与分类
  - Phase 1: 变更代码分析
  - Phase 2: 测试覆盖分析
  - Phase 3: 爆炸半径分析
  - Phase 4: 深度上下文分析

- **[adversarial.md](skills/differential-review/adversarial.md)** — 攻击者建模和利用场景
  - Phase 5: 对抗性漏洞分析
  - 攻击者模型定义（WHO/ACCESS/INTERFACE）
  - 可利用性评级框架
  - 完整利用场景模板

- **[reporting.md](skills/differential-review/reporting.md)** — 报告结构和格式
  - Phase 6: 报告生成
  - 9 段式报告模板
  - 格式指南和约定
  - 文件命名和通知模板

- **[patterns.md](skills/differential-review/patterns.md)** — 通用漏洞模式
  - OWASP Top 10 模式（注入、授权失效、SSRF 等）
  - 安全回归检测
  - 快速检测 bash 命令

## 工作流

完整的 Pre-Analysis + Phases 0-6 流程：

1. **Pre-Analysis** — 构建基线上下文
2. **Phase 0: 输入** — 提取变更、评估规模、风险评分
3. **Phase 1: 变更代码** — 分析 diff、git blame、检查回归
4. **Phase 2: 测试覆盖** — 识别覆盖缺口
5. **Phase 3: 爆炸半径** — 计算变更影响
6. **Phase 4: 深度上下文** — 五个为什么根因分析
7. **Phase 5: 对抗分析** — 使用攻击者模型挖掘漏洞
8. **Phase 6: 报告** — 生成综合 Markdown 报告

**导航：** 使用 SKILL.md 中的决策树直接跳转到所需阶段。

## 输出

生成 Markdown 报告，包含：
- 附严重性分布的执行摘要
- 带攻击场景和 PoC 的关键发现
- 测试覆盖分析
- 爆炸半径分析
- 历史上下文和回归风险
- 可操作的建议

## 使用示例

```
审查此 PR 的安全影响：
git diff main..feature/auth-changes
```
