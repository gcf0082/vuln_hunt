---
name: project-surfacing
description: 在漏洞分析之前，通过识别跨信任边界的外部入口来映射项目攻击面。仅暴露面识别，不做漏洞分析。
---

# 项目暴露面映射技能

## 1. 目的

本技能定义了对一个项目进行暴露面映射的流程——在漏洞分析之前，识别所有**外部可达的跨信任边界入口**，构建攻击面模型。

启用时将会：
- 通过项目侦察理解技术栈和架构
- 按分类识别所有外部入口（HTTP/RPC/MQ/CLI/Cron/文件I/O/HTTP外呼）
- **严格排除内部模块间调用**
- 标记可疑点（无鉴权、参数直接流入危险操作）
- 输出攻击面模型，为后续 source 或 sink 分析提供范围

---

## 2. 何时使用

适用场景：
- 审计前需要了解项目的对外暴露面
- 需要决定后续分析是走 source 方向还是 sink 方向
- 需要快速定位"攻击者能从哪里进来"

不适用场景：
- 漏洞发现和利用分析
- 逐函数深度代码审计（那是 `audit-context-building`）
- 单个暴露面的详细分析（那是 `source-analyze`）

---

## 3. 核心原则

### 3.1 跨信任边界定义

只有**来自外部攻击者模型可触及**的入口才算暴露面：

| 是暴露面 | 不是暴露面 |
|---|---|
| 用户 HTTP 请求触达的 route | 内部模块间的 RPC 调用 |
| 从外部队列（Kafka/RabbitMQ topic）消费消息 | 内部 EventBus 发布/订阅 |
| 用户在终端执行的 CLI 命令 | 被 CLI 命令调用的业务函数 |
| Cron 表达式定义的定时任务 | 被 Cron job 调用的业务函数 |
| 用户指定路径的文件读/写 | 固定路径的日志写入 |
| URL 来自外部参数的 HTTP 外呼 | 固定 URL 的健康检查上报 |

### 3.2 只发现，不分析

本技能只做"发现+分类+记录"，不做：
- 漏洞判断
- 数据流跟踪
- 调用链展开
- 利用验证

### 3.3 实事求是

- 能看到什么就写什么
- 不确定是否外部可达时标注"不明确"
- 不编造路由/入口

---

## 4. 阶段 1 — 项目全貌侦察

在逐类扫描之前，先建立对项目的基本理解：

1. **语言识别**：读构建文件（`pom.xml` / `build.gradle` / `package.json` / `go.mod` / `Cargo.toml` / `Gemfile` / `requirements.txt` / `composer.json` 等）
2. **框架识别**：从依赖和源码模式推断（Spring Boot / Flask / Express / Gin / Rails / Actix / Laravel 等）
3. **目录结构摸底**：理解模块划分（`src/main/java/com/acme/controller/`、`routes/`、`handlers/` 等）
4. **入口注册模式预判**：确定框架的路由注册方式（注解驱动 / 配置文件 / 代码注册 / 约定路由）
5. **鉴权模式识别**：找出鉴权框架和典型用法（Spring Security filter chain / JWT middleware / before_action 等）

**产物**：一段代码库概要描述（语言/框架/模块/入口模式/鉴权模式），不单独落盘，作为后续扫描的上下文。

---

## 5. 阶段 2 — 跨信任边界暴露面发现

按分类逐一扫描，每个分类独立进行。**只收集外部可达的入口，排除内部调用**。

### 5.1 HTTP 路由

**搜索方法**：
- 找框架 route 注册注解：`@RequestMapping`、`@PostMapping`、`@GetMapping`、`@PutMapping`、`@DeleteMapping`、`@PatchMapping`
- 找代码 route 注册：`app.get()`、`app.post()`、`router.HandleFunc`、`Route::get()`、`router.Handle`、`@app.route()`
- 找 spec 文件：OpenAPI/Swagger yaml 或 json

**排除**：
- filter / interceptor / middleware 类（不是入口，是入口间的处理层）
- `@ControllerAdvice`（异常处理，不是入口）

**记录内容**：
- URL pattern + HTTP method
- handler 函数所在文件:行号
- 是否显式鉴权（从注解/middleware 判断）

### 5.2 RPC 端点

**搜索方法**：
- proto 文件中的 `service` 定义（gRPC）
- Thrift IDL 文件中的 `service`
- Dubbo `@Service` 注解
- JSON-RPC / XML-RPC 端点

**排除**：
- 内部 rpc helper、utility 函数
- 同进程 IPC（Unix socket 等，除非外部可达）

### 5.3 消息消费（外部队列）

**搜索方法**：
- Spring：`@KafkaListener`、`@RabbitListener`、`@JmsListener`、`@PulsarListener`、Spring Cloud Stream `@Input`/`@Output`
- Python：kombu consumer、pika consumer、celery task（`@app.task`）
- Go：sarama consumer、nsq consumer
- Node：amqplib consumer、Bull/BullMQ worker

**排除**：
- 内部 EventBus（Guava EventBus、Spring `@EventListener`、Vert.x EventBus、Node EventEmitter）
- 同进程 message channel（Akka actor 消息、Erlang actor 消息）
- 只在相同微服务内部使用的队列

**判断依据**：队列/listener 是否由外部系统/其他服务推送消息。Spring `@EventListener` 是内部事件，不算。

### 5.4 CLI 命令

**搜索方法**：
- cobra `cmd.AddCommand`、`rootCmd.AddCommand`
- Spring Shell `@ShellMethod`
- Python click `@click.command()`、argparse `add_parser`
- Picocli `@Command`
- symfony console、artisan command

**排除**：
- 被 CLI handler 调用的业务函数（那不是独立的暴露面）

### 5.5 Cron / 定时任务

**搜索方法**：
- Spring `@Scheduled`（`cron` / `fixedRate` / `fixedDelay`）
- Python Celery beat、`schedule` 库、`APScheduler`
- Go `robfig/cron` 注册
- `crontab` 文件
- Quartz 调度器配置和注解
- 配置文件中的 cron 表达式

**排除**：
- 被 Cron job 调用的业务函数
- 非定时触发的延迟任务

### 5.6 外部文件 I/O

**搜索方法**：
- grep 找文件路径来自请求参数的读写：`@RequestParam` + 附近文件操作、`req.file` + 写盘、`MultipartFile.transferTo()`、`req.files`、`req.body` + `fs.writeFile`
- 上传处理：上传路径从参数/header 拼接
- 导入/导出：路径参数来自 URL 参数

**排除**：
- 固定路径的日志文件写入（logback/log4j 配置路径）
- 读固定路径的配置文件（如 `application.yml`）
- 内部缓存文件写入

### 5.7 HTTP 外呼（外部可控 URL）

**搜索方法**：
- grep 找 HTTP 请求库调用且 URL 不是硬编码常量：
  - Java：`RestTemplate`、`WebClient`、`OkHttp`、`HttpClient`、`FeignClient`
  - Python：`requests`、`aiohttp`、`urllib`、`httpx`
  - Go：`http.Get`、`http.Post`、`http.Client.Do`
  - Node：`axios`、`fetch`、`got`、`request`
- 确认 URL 是否由外部参数影响（从请求参数、header、配置中心动态获取）

**排除**：
- 固定 URL 的健康检查（`/health`、`/actuator/health`）
- 固定 URL 的监控上报
- 内部服务发现调用（如 Eureka 注册）

---

## 6. 阶段 3 — 攻击面模型输出

汇总所有发现，输出结构化结果。

### 6.1 输出结构

```
# 项目暴露面映射报告

## 项目概览
- **语言**：{语言}
- **框架**：{框架}
- **模块**：{模块列表}
- **入口模式**：{route 注册方式}
- **鉴权框架**：{如有}

## 暴露面列表

### HTTP（{n} 个）
| URL | Method | Handler | 文件:行号 | 鉴权 | 发现 |
|---|---|---|---|---|---|

### RPC（{n} 个）
| Service | Method | Handler | 文件:行号 | 鉴权 | 发现 |
|---|---|---|---|---|---|

### MQ（{n} 个）
| Queue/Topic | Consumer | 文件:行号 | 发现 |
|---|---|---|---|

### CLI（{n} 个）
| 命令 | Handler | 文件:行号 | 发现 |
|---|---|---|---|

### CRON（{n} 个）
| 表达式 | Handler | 文件:行号 | 发现 |
|---|---|---|---|

### FILE_IO（{n} 个）
| 操作 | 路径来源 | 文件:行号 | 发现 |
|---|---|---|---|

### OUTBOUND_HTTP（{n} 个）
| URL 构造方式 | 库 | 文件:行号 | 发现 |
|---|---|---|---|

## 可疑点
- {文件:行号} — {问题描述}

## 分析建议
- 推荐分析方向（source / sink / 两者）
- 优先级建议
```

### 6.2 质量检查

输出前逐项确认：
- [ ] 每条暴露面引用了具体文件:行号
- [ ] 内部调用已被排除
- [ ] 可疑点已标记
- [ ] 不确定处已标注"不明确"
- [ ] 没有漏洞结论（本技能不做漏洞分析）

---

## 7. 子代理使用

对于以下场景可派发子代理（使用 `surface-mapper` agent）：
- 大型项目（多模块）
- 某一分类集中扫描（如全项目扫 HTTP 路由）
- 被分析目录不在当前工作目录

子代理必须：
- 遵循相同的"只收集跨信任边界入口"原则
- 返回结构化的暴露面列表
- 不输出漏洞结论

---

## 8. 与非目标的关系

本技能**不做**：
- 漏洞发现
- 数据流分析
- 调用链追踪
- 告警分级
- 修复建议

它是纯暴露面发现工具。其结果可输入给：
- `source-collect`：作为暴露面汇总参考
- `sink-collect`：标记外部可控的文件 I/O 和 HTTP 外呼点
- `source-analyze`：对重点暴露面做深入分析
