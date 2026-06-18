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

## 过程

对 details 文件中的每一组（一个源码文件），打开该文件定位到所有命中行，逐一确认。

### 1. 直接确认

打开源码文件，定位到命中行，检查变量来源：

- **明确非敏感**（路径/文件/名称/异常/常量/枚举等）→ 标记 **已移除**
- **明确敏感**（密码/token/密钥调用等）→ 标记 **确认**
- 不确定 → **进入数据流回溯**

### 2. 数据流回溯（最多 5 层）

沿变量赋值链向上追溯，每层查看上游变量或函数返回值：

- 每次只上一行（赋值位置或函数定义）
- 最多追溯 **5 层**
- 任一层发现明确结论 → 停止并输出完整调用链
- 5 层后仍不确定 → **保留原疑似结论**

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
