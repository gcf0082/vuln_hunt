---
name: callchain-trace
description: 从入口函数追踪调用链直达外部函数边界，输出带不确定性标注的树形调用链用于漏洞分析。仅在用户显式指名调用本 skill 时触发。
---

# 核心任务

从入口出发，沿调用链只追踪业务强相关函数，输出调用链直达外部函数边界，用于快速理解核心业务逻辑。get/set/put 等纯数据传递不体现。

调用链将用于后续漏洞分析，涉及文件操作、命令执行、网络请求的函数必须出现在链中，遗漏会导致分析错误。

**关键原则：不确定性必须标注。** 当无法精确定位调用目标时，列出所有候选而非猜测。一条标注了不确定性的不完整链，比一条自信但错误或遗漏了关键路径的链更有价值。

## 输入处理

用户入口描述**形式不限**，按需自适应：

| 输入形式 | 处理方式 |
|---|---|
| 函数名（如 `processOrder`） | 搜索代码查找函数定义 |
| REST 路径（如 `/api/order/create`）| 搜索 route 映射定位 handler |
| `文件:行号` | 直接读取该位置 |
| 代码片段 | 提取入口目标再定位 |
| 以上均未命中 | 告知用户无法定位 |

## 核心 vs 非核心分类

### 名称启发

| 特征 | 初步分类 | 说明 |
|:---|:---|:---|
| 含领域术语 `processOrder` / `calculatePremium` / `approveLoan` | 核心 | 业务逻辑 |
| 含 `log` / `print` / `debug` / `tracing` | 非核心 | 日志 |
| 含 `validate` / `check` / `assert` / `require` / `isValid` | 看语境 | 结合业务上下文判断 |
| 含 `get` / `set` / `to` / `from` / `format` / `convert` / `parse` | 非核心 | 工具转换 |
| 含 `save` / `persist` / `store` / `delete` / `update` | 核心 | IO/数据库 |
| 含 `send` / `fetch` / `request` / `call` / `invoke` | 核心 | 网络/外部调用 |
| 标准库函数 / 三方库函数 | 看语境 | 工具类不追；涉及文件/命令/网络的是漏洞分析关键路径，不能跳过 |
| 只有一行返回/抛异常的包装函数 | 非核心 | 纯转发 |

### 语境再判断

名称启发无法确定的（如 validate/check）结合业务上下文判定。合规系统中 `validateCompliance` 是核心业务，普通空值校验则不是。

## 叶子定义

叶子是**项目中找不到定义的函数**（标准库/三方库/外部 SDK）。项目拥有的配置文件/脚本不是终点，须继续解析到具体操作：

- **MyBatis**: 搜索 XML mapper 定位 SQL 行号和内容；注解 SQL 直接提取
- **Shell 脚本**: 找到脚本文件，提取每条命令作为链的下一跳，嵌套脚本继续追踪
- **其他**: Spring Data JPA @Query 提取 SQL；Dockerfile/CI 配置标注执行的命令

# 跟踪流程

调用链的准确性取决于每条调用是否找到了真正的实现。花时间把定义找清楚，比快速出个不准确的链更有价值：

- 接口/抽象方法 → 搜索项目内实现类
- 跨模块调用 → 在相关模块中搜索
- 框架入口（MyBatis Mapper 等）→ 搜索 XML 配置

重要业务的函数名往往不直接匹配（如 processOrder 背后可能叫 handlePurchaseRequest），多试几组关键词搜索能找到真实路径，调用链才有意义。

预期链形：入口 → 核心 → ... → 核心 → 外部函数

## 多实现候选解析

接口或抽象方法有多个实现类时，不猜测——列出所有候选并附上选择逻辑的依据：

| 框架机制 | 处理方式 |
|---|---|
| Spring `@Profile("dev")` | 搜索配置文件确定激活的 profile，缩小候选 |
| Spring `@ConditionalOnProperty` / `@ConditionalOnMissingBean` | 搜索 `application.yml` 或 `@Configuration` 中该属性是否存在 |
| Spring `@Qualifier` / `@Primary` | 检查注入点的注解，标注哪个实现被选中 |
| 手动 `if/else` / 策略模式 | 列出所有分支，标注条件表达式的判断依据 |
| 测试 mock/stub | 排除测试目录（`src/test/`、`*Test.java`）中的候选，除非审计目标是测试代码 |

输出时标注 `[? 2 candidates: StripePG|PaypalPG]`，如果无法确定则列出所有候选并附加选择依据的说明。

## 反射/动态调用追踪

以下调用模式无法通过静态分析直接确定目标。必须执行降级追踪：

| 模式 | 降级策略 |
|---|---|
| `method.invoke(target, args)` / `clazz.getMethod(name)` | 追踪 `name`/`methodName` 变量的赋值链；如果源自常量则直接解析，如果源自用户输入则标注 `[REF: user_input]`，如果源自枚举/映射表则列出所有可能值 |
| `getattr(obj, action + "_handler")` / `__getattr__` | 搜索 `action` 赋值链；提取所有可能的 handler 命名模式并搜索 |
| `routingTable[req.path]` / 动态路由表 | 搜索路由表的定义；列出所有注册的 key |
| `invokeDynamic()` / Java `MethodHandles` | 与方法名搜索相同的策略；查找 `lookup` 调用附近的字符串常量 |
| JS `eval(code)` / `new Function(body)` | 标注 `[EVAL]`，搜索 `code` 的赋值链；如能提取源码字符串则将其内容作为链的下一跳 |

标注输出格式：`handler (dispatch.js:25) [REF: action → user_input → HTTP params]`。

## 异步/事件驱动追踪

同步调用树无法准确表示异步控制流。按以下规则标记异步边界：

| 模式 | 标注 | 说明 |
|---|---|---|
| `await fn()` / `Promise.then(cb)` | `[ASYNC]` | 调用返回后回调在将来执行 |
| `Promise.all([p1, p2])` | `[ASYNC: PARALLEL]` | 多个路径并发执行 |
| `eventEmitter.emit("evt", data)` | `[ASYNC: EVENT → evt]` | 搜索所有 `on("evt", ...)` / `addListener("evt", ...)` 注册的监听器 |
| `kafka.send(record)` / `rabbit.publish()` | `[MQ: topic]` | 消息队列；标注 topic/queue 名称，消费者在另一进程中 |
| `fs.readFile(path, cb)` / `setTimeout(fn, 0)` | `[ASYNC: callback]` | 回调稍后执行 |
| `dispatch_async()` / Go `go func()` | `[ASYNC: GOROUTINE]` | 并发执行 |
| `Thread.start()` / `ExecutorService.submit()` | `[ASYNC: THREAD]` | 新线程执行 |

异步节点的子树前标注异步边界类型，并在树末尾汇总所有独立执行分支。

## AOP/框架魔法识别

框架在源代码不可见的位置注入行为。按以下规则识别并标注：

| 机制 | 标注 | 说明 |
|---|---|---|
| Spring `@Transactional` | `[AOP: TX]` | 函数被事务包裹；标注 commit/rollback 位置 |
| Spring `@Cacheable` | `[AOP: CACHE]` | 方法可能直接返回缓存结果，不执行业务代码 |
| Spring `@PreAuthorize` / `@Secured` | `[AOP: AUTH]` | 执行前有权限检查；提取 SpEL 表达式 |
| `@Around` / `@Before` / `@After` | `[AOP: @Around ...]` | 搜索切面类中对应的通知逻辑并展开 |
| Hibernate `entity.getX()` (lazy load) | `[LAZY: SQL]` | 标注 `getX` 调用的具体 SQL（需提前查找 ORM 映射） |
| Django `@login_required` / `@permission_required` | `[AOP: AUTH]` | 标注装饰器的具体权限检查逻辑 |
| Express `app.use(middleware)` | `[AOP: MW]` | 搜索中间件注册顺序；在树中标注包裹层 |
| Python `@contextmanager` / `with` 语句 | `[AOP: CTX]` | 标注 __enter__/__exit__ 逻辑 |

AOP 标注必须出现在被包裹函数的上层，以树状层级体现"外层包裹内层"的关系。

# 不确定性管理

**这是本 skill 最重要的原则。** 输出中必须反映所有无法确定的信息：

## 标注符号

| 符号 | 含义 |
|---|---|
| `[? N 候选: A\|B]` | 调用有多个候选目标，无法精确确定 |
| `[? 条件: expr]` | 路径取决于运行时条件（配置/特性标志/环境变量） |
| `[REF: var → source]` | 反射/动态调用；变量追踪至源头 |
| `[ASYNC ...]` | 异步边界（详见异步追踪节） |
| `[AOP: ...]` | 框架注入行为（详见 AOP 节） |
| `[MQ: topic]` | 消息队列，消费者在另一进程 |
| `[EXT: service]` | 外部服务，当前仓库无法追踪 |
| `[LAZY: SQL]` | ORM 懒加载触发的 SQL |
| `[EVAL]` | eval/动态代码生成 |
| `[UNTRACKED]` | 因无法定位而终止，后续链缺失 |
| `[CYCLE → 函数名]` | 检测到循环调用，终止此分支展开 |

**规则：** 宁可多标不确定性，不要假装确定。后续漏洞分析阶段会根据这些标注判断是否值得深入。

# 输出格式

## 调用链

按层级缩进展示每个函数的调用顺序。每个节点标注 `文件名:行号` 及所有适用的不确定性符号：

```
### 树 1：主流程
processOrder (OrderController.java:32)
├── [AOP: AUTH] @PreAuthorize("hasRole('ADMIN')")
│   └── SecurityUtils.checkRole (SecurityAspect.java:15)
├── calculateAmount (OrderService.java:58) [AOP: TX]
│   ├── OrderMapper.xml:47 — SELECT * FROM orders WHERE id = #{id}
│   └── applyDiscount (OrderService.java:72) [? 2 candidates: PercentageDiscount|FixedDiscount]
├── paymentService.charge (PaymentService.java:21) [EXT: payment-gateway]
│   └── okhttp3:execute — POST https://api.payment.com/charge
├── [ASYNC: EVENT → orderPlaced]
│   ├── inventoryService.decrement (InventoryService.java:10) [? @Profile("prod") → ProdInventory]
│   │   └── InventoryMapper.xml:12 — UPDATE stock SET qty = qty - 1
│   └── NotificationService.sendAsync (NotificationService.java:8) [ASYNC]
│       └── sendEmail — SMTP
└── notifyUser (NotificationService.java:15)
    └── kafka.send("order-notification") [MQ: order-notification]
```

- 只展示核心路径，非核心函数不出现；纯数据传递（HashMap.get、String.format 等）自动跳过
- 涉及文件操作、命令执行、网络请求的函数必须保留——无论是否标准库调用，这些是漏洞分析的关键路径
- 默认一棵树，特别复杂时才拆多棵树
- 每个不确定性符号必须有含义，不得为空泛标注
- 当一条路径有 3 个以上候选时，只列出入选概率最高的 3 个并以 `...` 表示

## 智能分派

入口函数调用的核心分支可以独立追踪时（如 if/switch 各分支业务语义不同），并发派发子任务各自完成调用链追踪，最后合并结果。分支间有交叉依赖的不拆分。

# 质量自检流程

每条调用链输出后，附加如下自检清单：

```
[自检]
✅ 所有不确定性已按标注符号表标注
✅ 多实现候选已列出并附选择依据
✅ 反射/动态调用已追踪变量赋值链或标注 REF
✅ 异步/事件边界已标注 ASYNC/EVENT/MQ
✅ AOP 注入行为已标注
✅ 已知外部服务已标注 EXT
⚠️ 跨服务调用 inventory-service: 未追踪（仓库外）
⚠️ 配置条件 newAuth feature flag: 未解析（运行时决定）
```

# 质量纪律

- 一条链中间断了后续全白费，找到定义再展开比停在半路有价值
- 重复函数说明走回了老路，继续展开只会无限循环 — 标注 `[CYCLE → 函数名]` 并停止展开
- 不确定性标注不是失败的标志，是专业性的体现
- 如果一个调用经过多步分析仍无法定位，标注 `[UNTRACKED]` 并记录原因
