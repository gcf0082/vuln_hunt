---
name: confirm-analyzer
description: 读取 details/ 文件，打开源码确认每条疑似行的真实性，输出调用链和举证代码，降低误报。
---

# Confirm Analyzer

分析 `<dir>/details/sensitive-logs-NNN.txt` 中的每条记录，打开源码确认并输出证据。

## 输入

- `<dir>/details/sensitive-logs-NNN.txt` — 按源码文件分组的疑似敏感行：
  ```
  src/main/java/LoginService.java
    42:  logger.info("user password: %s", password)
  ```

## 举证原则

**一般情况下不要擅自移除。举证不足时默认保留疑似结论。**

必须有充足证据才能做出判定：

- **非问题** — 必须有充足证据确认变量非敏感，不确定时绝不移除。必须向上追溯，找到并输出变量的实际来源/内容，根据实际值判断是否可能包含敏感信息。找不到明确的赋值来源或无法确认实际内容时，不能下结论为误报，按疑似处理。
- **确认问题** — 必须有明确证据证明变量敏感（如变量含 password/token 字段、来自 getPassword() 方法等）。
- **疑似问题** — 举证不足或无法确认，保留结论。

## 过程

对 details 文件中的每一组（一个源码文件），打开该文件定位到所有命中行，逐一确认。

### 1. 直接确认

打开源码文件，定位到命中行，检查变量实际来源：

- 变量赋值来自**明确非敏感源**（如 `File`、`Path`、`getConfig()`、枚举常量、硬编码 SQL 等）→ 在输出中展示赋值处代码证据，标记 **[非问题]**
- 变量赋值来自**明确敏感源**（如 `getPassword()`、`"password"`、`secretKey` 等）→ 输出调用链，标记 **[确认问题]**
- 变量赋值来源既不是明确敏感也不是明确非敏感 → 标记 **[疑似问题]**
- 不能确定变量来源 → **进入数据流回溯**

### 2. 数据流回溯（最多 5 层）

沿变量赋值链向上追溯，每次只上一层，最多 5 层：

- 每层检查该行变量来源
- 发现**非敏感证据**（如 `File`、`Path`、`.separator`、`getConfig()`、硬编码 SQL 常量）→ 在输出中展示赋值处代码证据，标记 **[非问题]**
- 发现**敏感证据**（如 `getPassword()`、`"password"`、`secretKey`）→ 输出调用链，标记 **[确认问题]**
- 若变量为 SQL/body/userInput 等通用数据，必须找到实际赋值/拼接位置，输出实际内容（如 SQL 语句原文、body 数据来源、key 引用路径等），根据实际内容判断是否可能包含敏感信息。不能仅因变量名不含敏感字段就判定安全。
- 5 层后仍未找到充足证据 → 标记 **[疑似问题]**

## 输出

写入 `<dir>/confirmed/sensitive-logs-NNN.txt`。

每个条目输出格式：

```
src/main/java/LoginService.java
  42:  logger.info("user password: %s", password)  [确认问题]

  调用链:
    行38:  password = userService.getPassword(userId)    ← 源头
    行42:  logger.info("user password: %s", password)    ← 目标行

  证据: password 来自 getPassword()，返回值明确为密码
```

```
src/main/java/UserDAO.java
  55:  logger.debug("executing query: {}", sql)  [非问题]

  调用链:
    行50:  String sql = "SELECT id, name, email FROM users WHERE id = ?"  ← 硬编码常量
    行55:  logger.debug("executing query: {}", sql)                      ← 目标行

  证据: 追踪至行50，sql 赋值为硬编码常量
  "SELECT id, name, email FROM users WHERE id = ?"，
  只含表名、列名、占位符，不含用户输入，确认无敏感信息
```

**标签说明：**
- `[确认问题]` — 确认是敏感信息，保留
- `[疑似问题]` — 举证不足或无法确认，保留结论
- `[非问题]` — 确认不是敏感信息，移除

## 输出文件

用 Write 工具写文件，完成后返回文件路径。
