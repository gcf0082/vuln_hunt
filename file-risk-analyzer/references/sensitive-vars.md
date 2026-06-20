# 敏感变量名三级分类

> 以下列表是**举例说明**，不是精确匹配规则。变量名可能千变万化（如 `userPwd`、`authToken`、`mySecret`、`reqBody`），应基于**语义理解**判断其是否属于某类，而非要求完全命中列表中的关键词。嵌套属性（如 `result.token`、`user.password`）按最后一部分或整体判定。

## 🔥 HIGH（高度敏感）—— 几乎确定包含敏感信息

| 变量名关键词 | 原因 |
|---|---|
| `password`, `passwd`, `pwd`, `pass` | 密码 |
| `token`, `auth_token`, `access_token`, `jwt` | 认证令牌 |
| `secret`, `secret_key`, `client_secret` | 密钥 |
| `api_key`, `apikey`, `private_key` | API/加密密钥 |
| `session`, `session_id`, `sid` | 会话标识 |
| `cookie`, `cookies` | Cookie |

## ⚠️ MEDIUM（中等敏感）—— 可能包含敏感信息

| 变量名关键词 | 原因 |
|---|---|
| `email`, `mail` | 邮箱 |
| `phone`, `mobile` | 电话号码 |
| `sql`, `query`, `db_query` | SQL 语句 |
| `buffer`, `buf`, `raw` | 原始缓冲区 |
| `message`, `msg` | 消息文本 |

## 通用数据类（MEDIUM）—— 无法预判内容，必须标记

这类变量是常见的"容器"型变量名，其内容因场景而异，无法预先判断是否包含敏感数据。同一个变量名在不同代码中可能完全不同：`data` 可能只含一个 ID，也可能包含完整的用户信息。因为不确定里面有什么，所以必须标记为 MEDIUM 交由人工判断。

| 变量名关键词 | 原因 |
|---|---|
| `body`, `request_body`, `response_body`, `content` | 请求/响应体 |
| `req`, `request`, `http_request` | 整个请求对象 |
| `resp`, `response`, `http_response`, `result` | 整个响应对象 |
| `data`, `payload`, `form_data`, `post_data` | 数据载荷 |
| `json`, `dict`, `map` | JSON/字典对象 |
| `args`, `kwargs`, `arguments`, `params` | 参数集合 |
| `header`, `headers` | HTTP 头 |
| `input`, `output` | 输入/输出数据 |
| `item`, `items`, `entry`, `entries` | 数据条目 |
| `file`, `files`, `upload` | 文件内容 |
| `object`, `obj` | 通用对象 |
| `record`, `records`, `row`, `rows` | 数据记录 |
| `field`, `fields`, `value`, `values` | 数据字段 |
| `event`, `events` | 事件数据 |
| `transaction`, `txn` | 事务数据 |
| `attribute`, `attributes`, `property`, `properties` | 属性集合 |
| `list`, `array`, `collection` | 集合数据 |
| `blob`, `clob` | 大对象数据 |

## ✅ LOW（通常不敏感）

> IP 地址和主机名不是敏感信息。`ip`、`hostname`、`domain`、`server` 等变量输出的是网络地址，不是凭证。
>
> 以 `Name`/`name` 结尾的变量（如 `userName`、`passwordName`、`tokenName`）也属于 LOW。
>
> 如果能推断变量类型属于路径、文件、目录、名称等非敏感类别（如 `configPath`、`outputDir`、`logFile`），即使不在表内也归为 LOW。

| 变量名关键词 | 原因 |
|---|---|
| `version`, `version_info`, `build_info`, `release_info` | 版本信息 |
| `stats`, `statistics`, `metrics`, `counters` | 统计数据 |
| `metadata`, `meta` | 元数据 |
| `schema`, `structure`, `type_def`, `interface_def` | 结构定义 |
| `manifest`, `catalog`, `inventory`, `registry` | 清单/目录 |
| `e`, `exception`, `ex`, `err` | 异常信息（通常不含敏感数据） |
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

## 格式化字符串敏感关键词

格式化字符串中的敏感词仅作为辅助判断，当变量名为 MEDIUM 时提级使用。**不能单独决定结果。**

| 关键词 | 含义 |
|---|---|
| `password`, `passwd`, `pwd` | 密码 |
| `token`, `jwt` | 令牌 |
| `secret`, `key` | 密钥 |
| `session`, `cookie` | 会话/Cookie |
| `header` | HTTP 头 |
| `body`, `content`, `payload` | 请求体内容 |

## 敏感等级组合规则

| 变量名等级 | 格式化字符串 | 最终判定 |
|---|---|---|
| HIGH | 任意 | **疑似敏感 HIGH** |
| MEDIUM | 包含敏感词 | **疑似敏感 HIGH** |
| MEDIUM | 无敏感词 | **疑似敏感 MEDIUM** |
| LOW | 包含敏感词 | **跳过** |
| LOW | 无敏感词 | 跳过 |

> 度量值不敏感：`passwordSize`（密码长度）、`tokenLen`（令牌长度）等属于 LOW。
