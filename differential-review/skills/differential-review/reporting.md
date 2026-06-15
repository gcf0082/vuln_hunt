# 报告生成（Phase 6）

完整的 Markdown 报告结构和格式指南。

---

## 报告结构

生成包含以下必要章节的 Markdown 报告：

### 1. 执行摘要

- 严重性分布表
- 风险评估（CRITICAL/HIGH/MEDIUM/LOW）
- 最终建议（APPROVE/REJECT/CONDITIONAL）
- 关键指标（测试缺口、爆炸半径、红旗标志）

**模板：**
```markdown
# 执行摘要

| 严重性 | 数量 |
|--------|------|
| 🔴 CRITICAL | X |
| 🟠 HIGH | Y |
| 🟡 MEDIUM | Z |
| 🟢 LOW | W |

**总体风险：** CRITICAL/HIGH/MEDIUM/LOW
**建议：** APPROVE/REJECT/CONDITIONAL

**关键指标：**
- 分析的文件：X/Y（Z%）
- 测试覆盖缺口：N 个函数
- 高爆炸半径变更：M 个函数
- 检测到的安全回归：P
```

---

### 2. 变更内容

- Commit 时间线
- 文件汇总表
- 行数变更统计

**模板：**
```markdown
## 变更内容

**Commit 范围：** `base..head`
**Commits：** X
**时间线：** YYYY-MM-DD 至 YYYY-MM-DD

| 文件 | +行数 | -行数 | 风险 | 爆炸半径 |
|------|--------|--------|------|----------|
| app.py | +50 | -20 | HIGH | CRITICAL |
| config.py | +10 | -5 | MEDIUM | LOW |

**总计：** +N, -M 行，共 K 个文件
```

---

### 3. 关键发现

对每个 HIGH/CRITICAL 问题：

```markdown
### [严重性] 标题

**文件：** path/to/file.py:行号
**Commit：** hash
**爆炸半径：** N 个调用方（HIGH/MEDIUM/LOW）
**测试覆盖：** 有/无/部分

**描述：** [清晰说明]

**历史上下文：**
- Git blame：在 commit X（日期）中添加
- 消息："[原始 commit 消息]"
- [为什么这个代码存在]

**攻击场景：**
[来自 adversarial.md 的具体利用步骤]

**概念证明：**
```python
# 展示问题的代码
```

**建议：**
[具体修复方案与代码]
```

**示例：**
```markdown
### 🔴 CRITICAL：DELETE /api/users/{id} 授权绕过

**文件：** UserController.java:156
**Commit：** abc123def
**爆炸半径：** 23 个调用方（HIGH）
**测试覆盖：** 无

**描述：**
移除了 `@PreAuthorize("hasRole('ADMIN')")` 检查，允许任何已认证用户删除任意账户。

**历史上下文：**
- Git blame：2024-06-15 添加（commit def456）
- 消息："按审计结果添加角色检查"
- 代码用于防止未授权用户删除操作

**攻击场景：**
1. 攻击者使用普通用户 JWT 调用 `DELETE /api/users/42`
2. 无授权检查（被移除）
3. 用户 42 的账户被永久删除
4. 系统数据丢失

**概念证明：**
```python
# 以任意已认证用户身份
requests.delete("https://api.example.com/users/42",
    headers={"Authorization": "Bearer user_jwt"})
# 成功 - 账户被删
```

**建议：**
```java
@PreAuthorize("hasRole('ADMIN')")
@DeleteMapping("/api/users/{id}")
public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
    // ... rest of function
}
```
```

---

### 4. 测试覆盖分析

- 覆盖统计
- 未测试的变更列表
- 风险评估

**模板：**
```markdown
## 测试覆盖分析

**覆盖：** 变更代码的 X%

**未测试的变更：**
| 函数 | 风险 | 影响 |
|------|------|------|
| deleteUser() | HIGH | 无授权测试 |
| processPayment() | MEDIUM | 逻辑未测试 |

**风险评估：**
N 个 HIGH 风险函数无测试 → 建议阻止合并
```

---

### 5. 爆炸半径分析

- 高影响函数表
- 依赖关系图
- 影响量化

**模板：**
```markdown
## 爆炸半径分析

**高影响变更：**
| 函数 | 调用方 | 风险 | 优先级 |
|------|--------|------|--------|
| deleteUser() | 89 | HIGH | P0 |
| validateToken() | 45 | MEDIUM | P1 |
```

---

### 6. 历史上下文

- 安全相关的移除
- 回归风险
- Commit 消息红旗标志

**模板：**
```markdown
## 历史上下文

**安全相关的移除：**
- 第 45 行：`@PreAuthorize` 被移除（2024-03 添加，针对 CVE-2024-1234）
- 第 78 行：输入校验被移除（2023-12 添加，"安全加固"）

**回归风险：**
- commit X 中移除的代码模式，在 commit Y 中重新添加
```

---

### 7. 建议

- 即时操作（阻塞性）
- 上线前（跟踪性）
- 技术债务（未来）

**模板：**
```markdown
## 建议

### 即时（阻塞性）
- [ ] 修复 UserController.java:156 的 CRITICAL 问题
- [ ] 为 deleteUser() 添加测试

### 上线前
- [ ] 对授权变更进行安全审计
- [ ] 对高爆炸半径函数进行性能测试

### 技术债务
- [ ] 重构验证模式，保证一致性
```

---

### 8. 分析方法论

- 使用的策略（DEEP/FOCUSED/SURGICAL）
- 分析的文件
- 覆盖估计
- 应用的技术
- 局限性
- 置信度

**模板：**
```markdown
## 分析方法论

**策略：** FOCUSED（80 个文件，中等代码库）

**分析范围：**
- 审查的文件：45/80（56%）
- HIGH RISK：100% 覆盖
- MEDIUM RISK：60% 覆盖
- LOW RISK：已排除

**技术：**
- 对所有移除代码执行 git blame
- 爆炸半径计算
- 测试覆盖分析
- 对 HIGH RISK 进行对抗建模

**局限性：**
- 未分析外部依赖
- 仅限于 1 跳调用方分析

**置信度：** 已分析范围 HIGH，总体 MEDIUM
```

---

### 9. 附录

- Commit 参考表
- 关键定义
- 联系方式

---

## 格式指南

**表格：** 使用 Markdown 表格展示结构化数据

**代码块：** 始终包含语法高亮
```python
# Python 代码
```
```java
// Java 代码
```

**状态指示器：**
- ✅ 完成
- ⚠️ 警告
- ❌ 失败/阻塞

**严重性：**
- 🔴 CRITICAL
- 🟠 HIGH
- 🟡 MEDIUM
- 🟢 LOW

**前后对比：**
```markdown
**BEFORE:**
```python
old code
```

**AFTER:**
```python
new code
```
```

**行号引用：** 始终包含
- 格式：`app.py:L123`
- 链接到 commit：`app.py:L123（commit abc123）`

---

## 文件命名和位置

**输出位置优先级：**
1. 当前工作目录（如果是项目仓库）
2. 用户桌面
3. `~/.claude/skills/differential-review/output/`

**文件名格式：**
```
<PROJECT>_DIFFERENTIAL_REVIEW_<DATE>.md

示例: MyProject_DIFFERENTIAL_REVIEW_2025-12-26.md
```

---

## 生成后用户通知模板

```markdown
报告生成成功！

📄 文件：[文件名]
📁 位置：[路径]
📏 大小：XX KB
⏱️ 审查耗时：~X 小时

摘要：
- X 个发现（Y 个 CRITICAL，Z 个 HIGH）
- 最终建议：APPROVE/REJECT/CONDITIONAL
- 置信度：HIGH/MEDIUM/LOW

后续步骤：
- 详细审查发现
- 在合并前处理 CRITICAL/HIGH 问题
- 考虑在 issue 管理系统中创建任务跟踪
```

---

## 错误处理

如果文件写入失败：
1. 尝试桌面位置
2. 尝试临时目录
3. 作为最后手段，在聊天中输出完整报告
4. 通知用户手动保存

**始终优先选择持久化产物，而非临时聊天输出。**
