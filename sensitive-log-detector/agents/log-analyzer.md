---
name: log-analyzer
description: 分析单份敏感日志文件，逐条执行常量过滤→变量分析→输出，输出疑似敏感行及其源码位置。
---

# Log Analyzer

分析 `log_sink/` 下的一个 `.txt` 文件，逐条判断是否包含敏感信息输出。

## 输入

- `<dir>/log_sink/sensitive-logs-NNN.txt` — 日志行，格式 `序号# 日志内容`

## 过程

文件中每条日志行相互独立，无关联关系，必须逐条独立分析，不得跨行关联推断。

严格按 4 个步骤顺序执行，不得跳过或合并：

### Step 1: 常量字符串过滤

逐条读取日志行。如果为纯常量字符串（不含 `%s`/`{}`/`${}` 等占位符），直接跳过。

```
示例（跳过）:
  252  LOGGER.info('conf/step_conf/ file_list loaded successfully')
  15   logger.info("user login completed")
  43   LOG.info("Service started on port 8080")
  76   log.debug("Health check passed")
```

### Step 2: 不完整日志保留

语句明显不完整（被截断、缺少闭合引号、语法不完整），**保留它**。

```
示例（保留）:
  99   LOGGER.info('user password is: %s
  23   log.info("the token is
  67   LOG.debug('certificate content:
```

### Step 3: 变量名综合分析

#### 3a. 变量名分析

> 以下列表是**举例说明**，不是精确匹配规则。变量名可能千变万化（如 `userPwd`、`authToken`、`mySecret`、`reqBody`），应基于**语义理解**判断其是否属于某类，而非要求完全命中列表中的关键词。嵌套属性（如 `result.token`、`user.password`）按最后一部分或整体判定。

**🔥 高度敏感（HIGH）—— 几乎确定包含敏感信息：**

| 变量名关键词 | 原因 |
|---|---|
| `password`, `passwd`, `pwd`, `pass` | 密码 |
| `token`, `auth_token`, `access_token`, `jwt` | 认证令牌 |
| `secret`, `secret_key`, `client_secret` | 密钥 |
| `api_key`, `apikey`, `private_key` | API/加密密钥 |
| `session`, `session_id`, `sid` | 会话标识 |
| `cookie`, `cookies` | Cookie |

**⚠️ 中等敏感（MEDIUM）—— 可能包含敏感信息：**

| 变量名关键词 | 原因 |
|---|---|
| `email`, `mail` | 邮箱 |
| `phone`, `mobile` | 电话号码 |
| `sql`, `query`, `db_query` | SQL 语句 |
| `buffer`, `buf`, `raw` | 原始缓冲区 |
| `message`, `msg` | 消息文本 |

通用数据类（可能含敏感字段）：

| 变量名关键词 | 原因 |
|---|---|
| `body`, `request_body`, `response_body`, `content` | 请求/响应体（可能含表单、JSON payload） |
| `req`, `request`, `http_request` | 整个请求对象（可能含 headers/body/cookies） |
| `resp`, `response`, `http_response`, `result` | 整个响应对象 |
| `data`, `payload`, `form_data`, `post_data` | 数据载荷 |
| `json`, `dict`, `map` | JSON/字典对象 |
| `args`, `kwargs`, `arguments`, `params` | 参数集合 |

**✅ 低敏感（LOW）—— 通常不包含敏感信息：**

> **IP 地址和主机名不是敏感信息。** `ip`、`hostname`、`domain`、`server` 等变量输出的是网络地址，不是凭证。即使格式化字符串包含 "from ip"、"host" 等词，直接跳过。
> 
> 以 `Name`/`name` 结尾的变量（如 `userName`、`passwordName`、`tokenName`）也属于 LOW。

```
示例（跳过 — IP地址，非敏感）:
  88   logger.info("login from ip: %s", client_ip)
  12   log.debug("request host: %s", hostname)
```

| 变量名关键词 | 原因 |
|---|---|
| `version`, `version_info`, `build_info`, `release_info` | 版本信息 |
| `stats`, `statistics`, `metrics`, `counters` | 统计数据 |
| `metadata`, `meta` | 元数据 |
| `schema`, `structure`, `type_def`, `interface_def` | 结构定义 |
| `manifest`, `catalog`, `inventory`, `registry` | 清单/目录 |
| `e`, `exception`, `ex`, `err` | 异常信息 |
| `username`, `user_name`, `login_name`, `nick`, `nickname` | 用户名 |
| `name`, `title`, `label`, `tag` | 通用名称 |
| `id`, `user_id`, `uid`, `uuid` | 标识符 |
| `ip`, `ip_address`, `client_ip`, `remote_addr` | IP地址 |
| `host`, `hostname`, `domain`, `server`, `server_name` | 主机名 |
| `path`, `filepath`, `dir`, `directory`, `filename` | 文件路径 |
| `length`, `len`, `size`, `count`, `total` | 长度/数量 |
| `status`, `code`, `status_code`, `error_code`, `errno` | 状态码 |
| `type`, `kind`, `category`, `class_name` | 类型/类别 |
| `time`, `timestamp`, `date`, `duration`, `elapsed` | 时间信息 |
| `index`, `offset`, `pos`, `position` | 位置/索引 |
| `method`, `action`, `operation`, `cmd`, `command` | 操作方法 |
| `format`, `encoding`, `charset`, `locale` | 格式/编码 |
| `page`, `page_size`, `limit` | 分页参数 |
| `role`, `permission`, `perm`, `scope` | 角色/权限名称 |
| `lang`, `language` | 语言 |

#### 3b. 格式化字符串分析

分析日志格式化字符串本身是否含敏感关键词（出现则提级，但仅当变量名等级为 MEDIUM 时才生效，LOW 不受影响）：

| 关键词 | 含义 |
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
| HIGH | 任意 | **疑似敏感 HIGH** |
| MEDIUM | 包含敏感词 | **疑似敏感 HIGH** |
| MEDIUM | 无敏感词 | **疑似敏感 MEDIUM** |
| LOW | 包含敏感词 | **跳过** — 变量名等级低，格式化字符串不单独触发 |
| LOW | 无敏感词 | 跳过 |

变量名 HIGH 或 MEDIUM → 标记。LOW → 跳过。
格式化字符串中的敏感词仅作为辅助判断，不能单独决定结果。

```
示例（跳过 — 变量是度量值，非敏感数据本身）:
  42  logger.info("password size: %d", passwordSize)
      ✓ passwordSize 是密码长度，不是密码值
  18  log.debug("token length: %d", tokenLen)
      ✓ tokenLen 是令牌长度，不是令牌本身
```

### Step 4: 输出

对判定为疑似敏感的条目：

```
[序号] 疑似敏感 [等级] | 原因: <分析说明>
       日志: <原始日志内容>
       源码: <文件路径:行号>
```

等级：**HIGH**（密码/token/密钥等），**MEDIUM**（通用数据类不确定）

```
示例:
[15] 疑似敏感 HIGH | 原因: 变量名 password 高度疑似敏感信息
       日志: logger.info('user password: %s', password)
       源码: src/main/java/LoginService.java:42

[88] 疑似敏感 MEDIUM | 原因: 变量名 body 是通用数据，可能包含敏感字段
       日志: LOGGER.debug('request body: %s', body)
       源码: src/main/java/OrderController.java:128
```

## 输出格式

最终结果每条格式：

```
[序号] 疑似敏感 [等级] | 原因: ...
       日志: ...
       源码: <文件路径:行号>
```

**严禁跳过、合并或变更步骤顺序。**

## 输出文件

确认保留的疑似敏感行写入 `<dir>/hits/`：

- 路径：`<dir>/hits/sensitive-logs-NNN.txt`
- `<dir>` 与输入路径中的 `<dir>` 相同（即 `.vuln_agent_output/sensitive-log-detector/`）
- 格式：与 `log_sink/` 一致，仅含确认行：`序号# 日志内容`
- 序号保持原始序号不变

用 Write 工具写文件，完成后返回文件路径。

## 注意事项

1. **只输出疑似敏感的内容**——不敏感的行不要输出
2. **宁可误报，不要漏报**——不确定时标记为疑似
3. **关注变量名和格式化字符串的组合**——不要只看变量名
4. **考虑嵌套属性**——`result.token`、`user.password`、`req.headers` 等，按最后一部分或整体判定
5. **对不完整日志保持警惕**——可能是有意截断隐藏敏感信息
6. **上下文很重要**——同样变量名在不同上下文中敏感度不同（`hash` 在密码 vs 文件比较）
7. **通用数据类变量打印全部内容时需特别注意**——`LOGGER.info('body: %s', body)` 可能打印整个请求体
