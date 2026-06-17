---
name: sensitive-log-detector
description: >
  分析日志输出中的变量，快速识别是否可能包含敏感信息（如密码、token、密钥等）。
  适用于代码审计、安全审查场景。当用户给你一段或多段包含变量的日志打印语句，
  或者日志文件，要求你分析其中是否打印了敏感信息时，务必使用此 skill。
  注意：即使用户只是贴了一段日志说"帮我看看"，没有明确说"分析敏感信息"，
  但只要涉及日志中的变量内容分析，就应该触发。
compatibility:
  - Shell
  - Python
---

# Sensitive Log Detector - 敏感日志检测

## 核心目标

分析日志打印语句，识别出**可能**打印了敏感信息的日志行。输出疑似敏感信息的内容供人工审查。

**核心原则：宁可误报（false positive）也不要漏报（false negative）。** 安全审查场景下，漏掉真正的敏感信息比多报几条严重得多。如果对某个变量不确定，把它标记为疑似敏感。

## 分析策略

按以下优先级依次分析每一条日志语句：

### Step 1: 常量字符串过滤

如果日志打印的内容是**纯常量字符串**（没有变量插值、没有 `%s`/`{}`/`${}` 等格式化占位符），则**一定不会包含敏感信息**，直接跳过。

```
示例（跳过 — 常量字符串，无变量）:
  252     LOGGER.info('conf/step_conf/ file_list loaded successfully')
  15      logger.info("user login completed")
  43      LOG.info("Service started on port 8080")
  76      log.debug("Health check passed")
```

### Step 2: 不完整日志保留

如果日志语句明显不完整（被截断、语法不完整、缺少闭合引号等），**保留它**——无法判断是否包含敏感信息，宁可信其有。

```
示例（保留 — 不完整，无法判断）:
  99      LOGGER.info('user password is: %s
  23      log.info("the token is 
  67      LOG.debug('certificate content: 
```

### Step 3: 变量名综合分析

这是核心步骤。对于包含变量输出的日志语句，通过以下维度综合分析：

#### 3a. 变量名分析

根据变量名（包括函数参数名、字典 key 名、对象属性名等）推断其含义。

**🔥 高度敏感（HIGH）—— 几乎确定包含敏感信息：**

| 变量名关键词 | 原因 |
|---|---|
| `password`, `passwd`, `pwd`, `pass` | 密码 |
| `token`, `auth_token`, `access_token`, `jwt` | 认证令牌 |
| `secret`, `secret_key`, `client_secret` | 密钥 |
| `api_key`, `apikey`, `private_key` | API/加密密钥 |
| `session`, `session_id`, `sid` | 会话标识 |
| `cookie`, `cookies` | Cookie |

**⚠️ 中等敏感（MEDIUM）—— 可能包含敏感信息，需要看上下文：**

**PII 类：**

| 变量名关键词 | 原因 |
|---|---|
| `email`, `mail` | 邮箱（PII） |
| `phone`, `mobile` | 电话号码（PII） |
| `sql`, `query`, `db_query` | SQL 语句 |
| `buffer`, `buf`, `raw` | 原始缓冲区 |

**容器类（内容不确定，可能包含敏感字段）：**

| 变量名关键词 | 原因 |
|---|---|
| `body`, `request_body`, `response_body`, `content` | 请求/响应体（可能含表单数据、JSON payload） |
| `req`, `request`, `http_request` | 整个请求对象（可能含 headers/body/cookies） |
| `resp`, `response`, `http_response`, `result` | 整个响应对象（可能含敏感数据） |
| `data`, `payload`, `form_data`, `post_data` | 数据载荷（可能含提交的敏感字段） |
| `json`, `dict`, `map` | JSON/字典对象（内容不确定） |
| `args`, `kwargs`, `arguments`, `params` | 参数集合（可能含密码等） |

**✅ 低敏感（LOW）—— 通常不包含敏感信息：**

| 变量名关键词 | 原因 |
|---|---|
| `username`, `user_name`, `login_name`, `nick`, `nickname` | 用户名（非敏感） |
| `name`, `title`, `label`, `tag` | 通用名称 |
| `id`, `user_id`, `uid`, `uuid` | 标识符（非敏感） |
| `ip`, `ip_address`, `client_ip`, `remote_addr` | IP地址（非敏感） |
| `path`, `filepath`, `dir`, `directory`, `filename` | 文件路径 |
| `length`, `len`, `size`, `count`, `total` | 长度/数量 |
| `status`, `code`, `status_code`, `error_code`, `errno` | 状态码 |
| `message`, `msg`, `error_msg`, `err_msg` | 消息文本 |
| `type`, `kind`, `category`, `class_name` | 类型/类别 |
| `time`, `timestamp`, `date`, `duration`, `elapsed` | 时间信息 |
| `version`, `ver`, `build_number` | 版本号 |
| `index`, `offset`, `pos`, `position` | 位置/索引 |
| `method`, `action`, `operation`, `cmd`, `command` | 操作方法 |
| `format`, `encoding`, `charset`, `locale` | 格式/编码 |
| `page`, `page_size`, `limit`, `offset` | 分页参数 |
| `role`, `permission`, `perm`, `scope` | 角色/权限（名称本身非敏感） |
| `lang`, `language` | 语言 |
| `description`, `desc`, `note`, `comment`, `remark` | 描述/备注 |

#### 3b. 日志格式化字符串分析

除了变量名，还要分析日志的**格式化字符串（format string）** 本身。格式化字符串中如果包含敏感关键词，会提高这条日志的敏感等级。

格式化字符串中的敏感关键词（出现则提级）：

| 格式化字符串关键词 | 含义 |
|---|---|
| `password`, `passwd`, `pwd` | 密码 |
| `token`, `jwt` | 令牌 |
| `secret`, `key` | 密钥 |
| `session`, `cookie` | 会话/Cookie |
| `header` | HTTP 头 |
| `body`, `content`, `payload` | 请求体内容 |

#### 3c. 敏感等级组合规则

| 变量名等级 | 格式化字符串 | 最终判定 |
|---|---|---|
| HIGH | 任意 | 🔴 **疑似敏感 HIGH** |
| MEDIUM | 包含敏感词 | 🔴 **疑似敏感 HIGH** |
| MEDIUM | 无敏感词 | 🟡 **疑似敏感 MEDIUM** |
| LOW | 包含敏感词 | 🔴 **疑似敏感 HIGH** |
| LOW | 无敏感词 | ✅ 跳过 |

**即：只要变量名是 HIGH 或 MEDIUM，或者格式化字符串包含敏感关键词，就标记为疑似敏感。只有变量名是 LOW 且格式化字符串无敏感词时才跳过。**

### Step 4: 输出格式

对于每条被判定为**疑似敏感**的日志，按以下格式输出：

```
[行号] 疑似敏感 [等级] 原因: <分析说明>
       日志: <原始日志内容>
```

等级说明：
- **HIGH** - 高度疑似敏感（密码、token、密钥等）
- **MEDIUM** - 中等疑似敏感（PII 信息、容器类内容不确定等）

示例输出：

```
[252] 疑似敏感 MEDIUM | 原因: 变量名 custom_json 是容器类（JSON数据），内容不确定
       日志: 252     LOGGER.info('conf/step_conf/ file_list: %s', custom_json)

[15] 疑似敏感 HIGH | 原因: 变量名 password 高度疑似敏感信息
       日志: 15      logger.info('user password: %s', password)

[88] 疑似敏感 MEDIUM | 原因: 变量名 body 是容器类，可能包含请求/响应体中的敏感字段
       日志: 88      LOGGER.debug('request body: %s', body)

[67] 疑似敏感 HIGH | 原因: 变量名 headers 是容器类，且格式字符串含 header
       日志: 67      LOGGER.info('request headers: %s', headers)

[99] 疑似敏感 HIGH | 原因: 不完整的日志语句，无法判断是否包含敏感信息
       日志: 99      LOGGER.info('the token is
```

## 输入格式

### 方式一：粘贴日志文本

用户直接粘贴日志内容，按行分析。每行格式如：
```
252     LOGGER.info('conf/step_conf/ file_list: %s', custom_json)
```

### 方式二：读取日志文件

用户提供文件路径，读取后逐行分析。

## 注意事项

1. **只输出疑似敏感的内容**——不敏感的行不要输出，避免信息噪音
2. **宁可误报，不要漏报**——不确定时标记为疑似
3. **关注变量名和格式化字符串的组合**——不要只看变量名
4. **考虑嵌套属性**——如 `result.token`、`user.password`、`req.headers` 等，按最后一部分或整体判定
5. **对不完整日志保持警惕**——可能是有意截断来隐藏敏感信息
6. **上下文很重要**——同样的变量名在不同上下文中敏感度不同（如 `hash` 在存储密码时敏感，在比较文件时不一定）
7. **容器类变量打印全部内容时需要特别注意**——`LOGGER.info('body: %s', body)` 可能打印整个请求体
