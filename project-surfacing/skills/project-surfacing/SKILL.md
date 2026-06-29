---
name: project-surfacing
description: 扫描项目识别外部可触达的跨信任边界入口，输出暴露面清单。
---

# 项目暴露面映射

自顶向下扫描项目，找出所有**外部攻击者可直接触达**的入口。内部模块间调用不算。

## 扫描分类（5 类）

### HTTP

搜 route 注册：`@RequestMapping`、`@PostMapping`、`@GetMapping`、`@PutMapping`、`@DeleteMapping`、`@PatchMapping`、`app.get()`、`app.post()`、`router.HandleFunc`、`router.Handle`、`Route::get()`、`@app.route()`、OpenAPI/Swagger spec。

排除：filter、interceptor、middleware、`@ControllerAdvice`。

### RPC

搜 proto 文件 `service` 定义、Thrift IDL `service`、Dubbo `@Service`。

排除：内部 rpc helper、utility 函数、内部微服务间调用。

### MQ

搜从外部队列消费的注解/代码：`@KafkaListener`、`@RabbitListener`、`@JmsListener`、`@PulsarListener`、Spring Cloud Stream `@Input`、Celery `@app.task`、sarama consumer、pika consumer、amqplib consumer。

排除：内部 EventBus（Guava/Spring `@EventListener`/Vert.x EventBus/Node EventEmitter）、同进程 message channel、Akka actor 消息。

### CLI

搜命令注册：cobra `AddCommand`、Spring Shell `@ShellMethod`、click `@click.command()`、argparse `add_parser`、picocli `@Command`、artisan command。

排除：被 CLI handler 调用的业务函数。

### CRON

搜定时注册：Spring `@Scheduled`、Celery beat、`schedule`、`APScheduler`、`robfig/cron`、`crontab` 文件、Quartz。

排除：被 cron job 调用的业务函数。

## 排除总原则

只有攻击者能**直接触达**的算暴露面。A 调用 B → A 是暴露面，B 不是。

## 输出格式

每个暴露面一条，字段显式标明，条目间 `---` 分隔：

```
---
类别: HTTP
文件路径: src/main/java/com/acme/AuthController.java
行号: 34
函数: login()
URL: GET /api/login
---
类别: HTTP
文件路径: src/main/java/com/acme/UserController.java
行号: 48
函数: listUsers()
URL: GET /api/users
---
类别: RPC
文件路径: src/main/java/com/acme/UserServiceImpl.java
行号: 42
函数: getUser()
方法: UserService.GetUser
---
类别: MQ
文件路径: src/main/java/com/acme/OrderHandler.java
行号: 15
函数: onMessage()
队列: order.created
---
类别: CLI
文件路径: src/cli/user.go
行号: 102
函数: CreateUserCmd()
命令: user:create
---
类别: CRON
文件路径: src/main/java/com/acme/CleanupTask.java
行号: 22
函数: run()
表达式: 0 3 * * *
```

## 不遗漏检查

输出前确认：
- [ ] 5 个分类**都检查过**（即使某类没有发现也过一遍）
- [ ] 框架已知的所有入口注册模式都搜索了
- [ ] 内部调用都已排除
- [ ] 每个条目都有具体文件:行号
- [ ] 不确定的标记了 `[?]`
