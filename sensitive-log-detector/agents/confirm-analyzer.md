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

- **已移除** — 必须有明确证据证明变量非敏感（如变量确认是文件路径、配置常量等）。不确定时绝不移除。
- **确认** — 必须有明确证据证明变量敏感（如变量含 password/token 字段、来自 getPassword() 方法等）。
- **举证不足 / 无法确认** — 保留原疑似结论，不加标签，按疑似问题处理。

## 过程

对 details 文件中的每一组（一个源码文件），打开该文件定位到所有命中行，逐一确认。

### 1. 直接确认

打开源码文件，定位到命中行，检查变量实际来源：

- 变量赋值来自**明确非敏感源**（如 `File`、`Path`、`getConfig()`、枚举常量等）→ **已移除**，输出调用链
- 变量赋值来自**明确敏感源**（如 `getPassword()`、`"password"`、`secretKey` 等）→ **确认**，输出调用链
- 不能确定 → **进入数据流回溯**

### 2. 数据流回溯（最多 5 层）

沿变量赋值链向上追溯，每次只上一层，最多 5 层：

- 每层检查该行变量来源
- 发现**非敏感证据**（如 `File`、`Path`、`.separator`、`getConfig()`）→ 输出调用链，标记 **已移除**
- 发现**敏感证据**（如 `getPassword()`、`"password"`、`secretKey`）→ 输出调用链，标记 **确认**
- 5 层后仍未找到充足证据 → **保留原结论，不加标签**

## 输出

写入 `<dir>/confirmed/sensitive-logs-NNN.txt`。

每个条目输出格式：

```
src/main/java/LoginService.java
  42:  logger.info("user password: %s", password)  [确认]

  调用链:
    行38:  password = userService.getPassword(userId)    ← 源头
    行42:  logger.info("user password: %s", password)    ← 目标行

  证据: password 来自 getPassword()，返回值明确为密码
```

```
src/main/java/OrderController.java
  128:  LOGGER.debug("request body: %s", body)  [已移除]

  调用链:
    行120:  body = request.getBody()                      ← 源头
    行128:  LOGGER.debug("request body: %s", body)        ← 目标行

  证据: body 来自 HTTP request.getBody()，但已在前端脱敏处理，不含 PII
```

**标签说明：**
- `[确认]` — 确认是敏感信息，保留
- `[已移除]` — 确认不是敏感信息，移除
- 不带标签 — 5 层回溯后仍不确定，保留原结论

## 输出文件

用 Write 工具写文件，完成后返回文件路径。
