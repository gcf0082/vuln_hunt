# 差异审查方法论

安全导向代码审查的详细逐步工作流。

## Pre-Analysis：基线上下文构建

**首要操作——建立完整的基线理解：**

### 切换至基线版本
```bash
git checkout <baseline_commit>
```

### 分析基线代码库
手动或通过工具分析以下内容：

**捕获基线上下文：**
- 系统级不变量（在所有代码中必须**始终**成立的条件）
- 信任边界和权限级别（谁能做什么）
- 验证模式（检查点在哪些位置——纵深防御）
- 关键函数的完整调用图（谁调用什么）
- 状态流转方式
- 外部依赖和信任假设

**为什么这很重要：**
- 理解代码在变更前**应该**做什么
- 识别基线中的隐式安全假设
- 检测变更何时违反基线不变量
- 了解哪些模式是系统级的 vs 局部性的
- 捕捉变更何时破坏纵深防御

**存储基线上下文以便在差异分析期间引用。**

基线分析后，切回到 head commit 来分析变更：

```bash
git checkout <head_commit>
```

---

## Phase 0：输入与分类

**提取变更：**
```bash
# 获取 commit 范围
git diff <base>..<head> --stat
git log <base>..<head> --oneline

# 获取 PR
gh pr view <number> --json files,additions,deletions

# 获取所有变更文件
git diff <base>..<head> --name-only
```

**评估代码库规模：**
```bash
find . -name "*.py" -o -name "*.java" -o -name "*.go" -o -name "*.js" -o -name "*.ts" | wc -l
```

**分类复杂度：**
- **小**：<20 个文件 → 深度分析（读取所有依赖）
- **中**：20-200 个文件 → 聚焦分析（1 跳依赖）
- **大**：200+ 个文件 → 外科手术（仅关键路径）

**对每个文件进行风险评分：**
- **HIGH**：认证/授权、加密、外部调用、值传递、校验移除
- **MEDIUM**：业务逻辑、状态变更、新的公开 API
- **LOW**：注释、测试、UI、日志

---

## Phase 1：变更代码分析

对每个变更文件：

### 1. 读取两个版本（基线和变更后）

### 2. 分析每个 diff 区域
```
BEFORE: [变更前代码]
AFTER: [变更后代码]
CHANGE: [行为影响]
SECURITY: [安全影响]
```

### 3. Git blame 被移除的代码
```bash
# 何时添加的？为什么？
git log -S "removed_code" --all --oneline
git blame <baseline> -- file.py | grep "pattern"
```

**红旗标志：**
- 从 "fix"、"security"、"CVE" 提交中移除代码 → CRITICAL
- 最近添加（<1 个月）又被移除 → HIGH

### 4. 检查回归（重新添加的代码）
```bash
git log -S "added_code" --all -p
```

模式：代码被添加 → 因安全问题被移除 → 现在被重新添加 = 回归

### 5. 对每个变更进行微观对抗分析
- 被移除的代码阻止了什么攻击？
- 新代码暴露了什么新攻击面？
- 被修改的逻辑可以被绕过吗？
- 检查是否变弱了？边界情况是否覆盖？

### 6. 生成具体攻击场景
```
SCENARIO: [攻击目标]
PRECONDITIONS: [所需状态]
STEPS:
  1. [具体操作]
  2. [预期结果]
  3. [利用]
WHY IT WORKS: [引用代码变更]
IMPACT: [严重性 + 范围]
```

---

## Phase 2：测试覆盖分析

**识别覆盖缺口：**
```bash
# 生产代码变更（排除测试）
git diff <range> --name-only | grep -v "test"

# 测试变更
git diff <range> --name-only | grep "test"

# 对每个变更函数，搜索测试
grep -r "test.*functionName" test/ --include="*.py" --include="*.java"
```

**风险升级规则：**
- **新函数** + **无测试** → 风险 MEDIUM→HIGH 升级
- **修改了校验** + **测试未更新** → HIGH RISK
- **复杂逻辑（>20 行）** + **无测试** → HIGH RISK

---

## Phase 3：爆炸半径分析

**计算影响：**
```bash
# 统计每个被修改函数的调用方数量
grep -r "functionName(" --include="*.py" --include="*.java" . | wc -l
```

**分类爆炸半径：**
- 1-5 个调用：LOW
- 6-20 个调用：MEDIUM
- 21-50 个调用：HIGH
- 50+ 个调用：CRITICAL

**优先级矩阵：**

| 变更风险 | 爆炸半径 | 优先级 | 分析深度 |
|----------|----------|--------|----------|
| HIGH | CRITICAL | P0 | 深度 + 所有依赖 |
| HIGH | HIGH/MEDIUM | P1 | 深度 |
| HIGH | LOW | P2 | 标准 |
| MEDIUM | CRITICAL/HIGH | P1 | 标准 + 调用方 |

---

## Phase 4：深度上下文分析

对每个 HIGH RISK 的变更函数，回答以下问题：

### 1. 映射完整函数流
- 入口条件（前置条件、参数验证）
- 状态读取（访问了哪些变量/数据库）
- 状态写入（修改了哪些变量/数据库）
- 外部调用（API、服务、系统调用）
- 返回值和副作用

### 2. 追踪内部调用
- 列出所有被调用的函数
- 递归映射它们的流程
- 构建完整调用图

### 3. 追踪外部调用
- 识别跨越的信任边界
- 列出关于外部行为的假设
- 检查 SSRF 或请求伪造风险

### 4. 识别不变量
- 什么必须**始终**为真？
- 什么必须**永不**发生？
- 变更后不变量是否仍然保持？

### 5. 五个为什么根因分析
- 为什么这个代码被**更改**？
- 为什么原始代码**存在**？
- 为什么这可能会**出问题**？
- 为什么选择这个**方案**？
- 为什么这会在生产环境**失败**？

### 交叉模式检测：
```bash
# 查找重复的验证模式
grep -r "check\|validate\|assert" --include="*.py" .
grep -r "@PreAuthorize\|@Secured\|hasRole" --include="*.java" .

# 检查是否有任何在 diff 中被移除
git diff <range> | grep "^-.*check\|^-.*validate\|^-.*hasRole"
```

**标记移除是否破坏了纵深防御。**

---

**后续步骤：**
- HIGH RISK 变更，继续进行 [adversarial.md](adversarial.md)
- 报告生成，参见 [reporting.md](reporting.md)
