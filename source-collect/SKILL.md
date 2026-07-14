---
name: source-collect
description: 按用户指令收集并落盘暴露面。
---

# source-collect

## 定位

- **用户负责**："怎么收集"——给范围（目录/项目）、给特征（注解、文件后缀、Cron 文件路径等）、给覆盖度（全量还是抽样）
- **skill 负责**：按用户给的方法主动去收集、识别、分类、生成规范文件

skill 不是"输入→文件"的转换器，而是**带收集能力的执行器**。它会读代码、列文件、看注解、查配置，按用户的指令去把暴露面**找出来**，再按规范落盘。

## 路径约定

本 skill 涉及的所有目录**统一在 `.vuln_agent_output/` 下**，当前工作目录视为被分析项目根：

```
.vuln_agent_output/
├── discovered_surfaces/                  ← 输出
├── meta/
│   ├── excluded-paths.md                 ← 排除的非目标路径记录
│   └── error/source-collect.md           ← 失败日志
└── temp/
    └── scripts/                          ← 临时脚本
```

若目录不存在，先递归创建。

**目录里已有文件时**：开始收集前**必须先询问用户**，让用户在三选一里挑一种处理方式，**不要替用户决定**。三种选项：

1. **先清空再重新生成**：删掉 `discovered_surfaces/` 下所有 `*.md`（保留目录本身），本次按当前收集结果重新落盘
2. **覆盖已有同名文件**：本次生成的同名 slug 直接覆盖原文件；其它不同名文件保留
3. **追加（不同名才生成）**：本次只生成不冲突的新文件；同名跳过

用户**没有显式选择**时停下来等用户回复，不要默认走任何一种。

## 任务澄清

### 何时反问

用户显式调用 `source-collect` 但**未指定 scope** 时，先反问：

> 扫哪个项目？给出目录路径

- 用户给了路径 → 直接进入收集流程
- 用户说"当前目录" / 没给 → scope = 当前工作目录

用户消息中包含了**具体业务入口**（如"修改密码接口"、"订单导出"）时，自动提取为目标做精确匹配，**不再反问 scope/features/coverage**。

其他参数（features / coverage）由用户消息中的意图推断，**缺失则反问**。

## 预加载

启动时**必须**先读取以下文件（路径相对本 skill 目录），然后才能开始任务：

1. `references/constraints.md`（项目分析约束：非分析目标、临时脚本位置）
2. `references/recon-principles.md`（八荣八耻）

未读完不允许动笔。

## 智能分层浏览（三阶段）

从目标目录开始，逐层浏览，不要一次性读完所有文件。

### 阶段 0：识别项目类型

在深入浏览目录之前，先识别项目的**业务类型**，不同业务类型的攻击面形态不同：

**判断依据**（快速扫描根目录下的标志性文件）：
- `package.json` 含 `main`/`exports`/`module` 字段但无 `scripts.start` → **SDK/库**
- `setup.py`/`pyproject.toml` 有包定义但无 `[project.scripts]` / entry_points → **SDK/库**
- `go.mod` 存在但无 `cmd/` 目录含 `main()` → **SDK/库**
- `Cargo.toml` 有 `[lib]` 但无 `[[bin]]` → **SDK/库**
- 存在 `controller/`/`routes/`/`api/` → **Web 服务**
- 存在 `cmd/`/`cli/`/`main.go`/`app.js`/`cli.py` → **CLI 工具或独立应用**
- 同时具备多种特征 → **混合型**，分别识别

**不同项目类型的攻击面重点**：

| 项目类型 | 攻击面重点 |
|----------|-----------|
| Web 服务 | Controller/Handler/Route/Servlet 方法、MQ Consumer、gRPC handler |
| **SDK/库** | **对外导出的公共 API 函数/方法** |
| CLI 工具 | main 入口、子命令处理函数 |
| 独立应用 | main 入口、事件监听器、消息消费者 |
| 混合型 | 各类型分别覆盖 |

> **SDK/库攻击面说明**：当项目本身是 SDK 时，攻击者以 SDK 调用方的身份，通过 API 参数传递恶意输入。每个**导出的公共 API 函数**都是一个独立攻击面。各语言的导出标志：
> - **Python**：`__init__.py` 的 `__all__` 导出、`setup.py`/`pyproject.toml` 定义的包 API
> - **JavaScript/TypeScript**：`package.json` 的 `exports`/`main` 字段对应文件中的导出函数
> - **Go**：首字母大写的导出函数（`go.mod` module 对应包中）
> - **Java**：`public` 类的 `public` 方法（特别是 API/Provider/SPI 包中）
> - **C/C++**：头文件（`.h`/`.hpp`）中声明的导出函数、`__declspec(dllexport)` / `__attribute__((visibility("default")))` 标记的函数

### 阶段 1：逐层浏览，智能跳过

从根目录开始，用 `ls` 逐层查看目录内容。根据目录名决定是否深入：

**跳过（不深入）的目录**：
- `node_modules/`、`.git/`、`__pycache__/`、`venv/`、`.venv/`
- `target/`、`build/`、`dist/`、`out/`、`obj/`
- `test/`、`tests/`、`__test__/`、`spec/`、`__tests__/`
- `vendor/`、`third_party/`（仅第三方库时跳过）
- `lib/`：仅当是外部依赖缓存（如 jar 包、node_modules 外的第三方包）时跳过；**项目自身代码的 `lib/` 必须深入**（SDK/库项目的代码常在此目录）
- `docs/`、`doc/`、`static/`、`public/`、`assets/`、`images/`、`css/`、`js/`（前端静态资源）
- `config/`、`conf/`、`migration/`、`migrations/`、`sql/`、`db/`（仅配置/数据库时跳过）
- `docker/`、`.docker/`、`helm/`、`k8s/`、`deploy/`、`ci/`、`.github/`

**优先深入（高价值）的目录**：
- `controller/`、`controllers/`、`api/`、`apis/`、`routes/`、`router/`、`endpoint/`
- `handler/`、`handlers/`、`listener/`、`listeners/`、`consumer/`、`consumers/`
- `cmd/`、`cli/`、`command/`、`commands/`、`console/`
- `script/`、`scripts/`、`bin/`（可执行脚本）
- `src/lib/`、`lib/`（项目自身库代码，SDK 项目重点关注）
- `include/`、`pkg/`（C/C++ 头文件、Go 包目录）
- `service/`、`services/`（含业务逻辑的 service）
- `action/`、`actions/`、`task/`、`tasks/`、`job/`、`jobs/`
- `web/`、`websocket/`、`grpc/`、`graphql/`、`mq/`

**判断依据**：仅根据目录名和文件名推测，不要深入读取文件内容。文件名模式参考：
- `*Controller.java`、`*Controller.py`、`*Controller.ts`、`*Controller.go`
- `*Handler.java`、`*Handler.py`、`*Handler.ts`
- `*Route.ts`、`*Route.py`、`*Route.go`
- `*Servlet.java`、`*Filter.java`、`*Interceptor.java`
- `*Service.java`（如果含入口方法）
- `main.go`、`main.py`、`app.js`、`index.ts`、`cli.py`、`cmd.go`
- `*.sh`、`*.bat`、`*.ps1`（可执行脚本）
- `*Application.java`（Spring Boot 启动类，排除）
- `__init__.py`（Python 模块导出入口）
- `index.ts`、`index.js`（JS/TS 模块导出入口）
- `*.h`、`*.hpp`（C/C++ 公共 API 头文件）
- `package.json` 中 `exports`/`main` 字段指向的文件（JS/TS SDK 模块入口）

### 阶段 2：推测潜在攻击面

根据阶段 1 浏览到的文件名和路径，**推测**哪些文件可能是攻击面：

- 接口类：Controller、Handler、Route、Servlet、Listener、Consumer、WebSocket、gRPC、RPC/RMI
- 非接口类：main 入口、CLI 命令、独立脚本、任务处理
- **SDK 类（当阶段 0 识别为 SDK/库时）**：`__init__.py` 导出的函数、`package.json` exports 对应模块的导出函数、首字母大写的 Go 导出函数、Java public API 类的 public 方法、C/C++ 头文件中的导出函数声明

记录推测结果，准备验证。

### 阶段 3：验证

只读取阶段 2 推测出的文件代码，确认是否为真正的攻击面：
- 确认有外部可访问的入口（HTTP 路由、MQ 监听、main 函数等）
- 确认有外部输入或用户可控数据
- 确认后生成 surface 文件

**不要读取未推测的文件代码，不要无谓扩大读取范围。**

## 识别范围

收集所有攻击面（接口 + 非接口）：

- **接口**：web（REST / JAX-RS / Servlet / GraphQL）、外部 MQ 消费者、gRPC、WebSocket / SSE、RPC/RMI、Webhook 回调、自定义协议服务端（TCP/UDP）
- **非接口**：独立可执行脚本、独立工具（含 main 入口的可执行程序）、接收外部输入的任务/消息处理、CLI 命令入口、SDK/库导出的公共 API 函数

每条目必须提取精确的**来源信息**（完整文件路径:行号、函数名），路径必须是完整的相对项目根路径，供后续分析步骤直接使用。**REST 接口必须找到实际的 Controller 入口代码位置（文件路径:行号:函数名），而非路由配置或接口文档来源。**

### Swagger/OpenAPI YAML 文件提取 REST 接口

REST 接口可能定义在 Swagger/OpenAPI 的 YAML 文件中。查找项目中的 `*.yaml` / `*.yml` 文件，读取其内容判断是否为 OpenAPI spec（包含 `openapi` 或 `swagger` 版本号 + `paths` 字段）：

- **tags** → 类名推定：`tags` 列表第一个值一般为对应 controller 类名。如果类名以 `Api`/`Controller` 结尾则直接使用，否则尝试追加 `DelegateImpl` 后缀（如 tag=`user` → `UserDelegateImpl`）
- **operationId** → 函数名
- **参数提取**：通过 spec 文件发现的暴露面，**参数校验配置必须完整提取到 `**参数**` 字段，不可省略**。格式为 `{位置}: {参数名}({约束})`，含以下约束：
  - `required`（必填）
  - 类型（`string`/`integer`/`boolean` 等）
  - 数值范围：`minimum=值`、`maximum=值`
  - 长度范围：`minLength=值`、`maxLength=值`
  - 正则：`pattern=表达式`
  - 枚举值：`enum=val1|val2...`
  - `x-example` 及相关 `x-*` 扩展字段**不作为**约束范围，必须忽略
- **校验注解说明**：spec 中的参数约束通常经代码生成自动转为运行时校验注解（如 `@Min`/`@Pattern`），对入参自动拦截。完整提取这些约束到暴露面文件中，使后续漏洞分析能感知已有校验逻辑，避免因未发现校验而误判为漏洞。
- **接口定义**：在补充字段中加入 `**接口定义**` 指向该 YAML 文件的完整相对路径

### "独立工具"的判定

"独立工具"指有 main 函数作为入口的可独立执行的程序，不是编译产物分析也不是工具类/工具函数。

### 识别排除项

- Spring Boot `@SpringBootApplication` main 入口类不计为攻击面（仅框架启动入口，无业务逻辑）
- 纯工具类/工具函数不计为攻击面（无独立入口）
- 配置文件（YAML/JSON/properties/XML 等）不计为攻击面（不是入口函数，不含接收外部输入的处理逻辑）
- 内部定时任务不计为攻击面（不接收外部输入，无用户可控数据入口）
- 内部 Filter/Interceptor 不计为攻击面（被 Controller 调用，非独立入口）
- 内部 Event Bus / 领域事件监听器不计为攻击面（仅系统内部发布，无外部数据入口）
- **内部 Service 不计为攻击面**（在 Web 服务中 Service 被 Controller 调用，非独立入口）——**但注意**：当项目本身是 SDK/库时，Service/Provider/API 类的 public 方法就是对外入口，必须识别为攻击面

## 文件命名

```
{type}-{category}-{slug}.md
```

- `{type}` = `iface`（接口类） | `noniface`（非接口类）
- `{category}` = `REST` | `MQ` | `gRPC` | `WebSocket` | `GraphQL` | `SCRIPT` | `TOOL` | `CRON` | `CLI` | `SDK` 等
- `{slug}` = 简短英文标识，小写字母 + 连字符，建议 `动词-名词` 或 `名词-动作`，如 `user-list`、`send-order-message`、`daily-cleanup`

文件名内 `{type}` 和 `{category}` 必须与文件内 `**类型**` 和 `**分类**` 完全一致。

## 暴露面分类（type）判断

| 归为 `iface` | 归为 `noniface` |
|---|---|
| HTTP 路由、RPC 方法、消息监听、GraphQL 字段、SDK 公开方法 | 部署脚本、可执行工具、Cron 定时任务、CLI 命令 |

**判断核心**：是否提供"被外部主动调用的入口"。被远程/其他模块调用的 → `iface`；靠人工触发、Cron、部署环境启动的 → `noniface`。

## 输出 schema

每个暴露面一个独立文件，由**通用字段** + **按分类的补充字段**组成。

### 通用字段（所有文件必填）

```markdown
# 攻击面条目

- **类型**：iface（或 noniface）
- **分类**：REST（或 SCRIPT 等）
- **URL**：（能取到时必填）接口访问路径，如 `GET /api/users/{id}`、`/ws/chat`；非接口类型无 URL 时不填
- **参数**：（有参数时必填）格式为 `{位置}: {参数名}({约束})`；从 Swagger/OpenAPI YAML 发现时必须完整提取全部校验约束（required/类型/min/maxLength/pattern/enum 等），不可省略
- **来源**：`src/main/java/com/acme/UserController.java:48 listUsers()`
- **描述**：
  查询用户列表，接收 query 参数 page、size。
- **发现**：
  方法上没有鉴权注解。
  返回字段含手机号、邮箱。
```

| 字段 | 必填 | 说明 |
|---|---|---|
| 类型 | 是 | 与文件名 `{type}` 一致 |
| 分类 | 是 | 与文件名 `{category}` 一致 |
| URL | 否（接口类必填） | 接口访问路径，非接口类型不填 |
| 参数 | 否（有参数时必填） | `{位置}: {参数名}({约束})`，约束含 required/类型/min/maxLength/pattern/enum |
| 来源 | 是 | **从当前工作目录起的完整相对路径**：`文件路径:行号 函数名`。**禁止**只写文件名、**禁止**用 `./` / `../` / `...` 截断。**只有 SCRIPT/CRON 等本身就是源码或纯配置的场景**才退化为 `文件路径`（无行号）。如果一个暴露面同时涉及配置和实现类，**优先写实现类**，配置信息可在分类补充字段里带 |
| 描述 | 是 | **可多行**。先写本分类的基本信息（REST 写 URL+入口、CRON 写表达式+命令等），其它从源码直接可见的（参数、注解、注释、函数体可见逻辑）能写就写；看不到就停，**不为了详细去挖** |
| 发现 | 否 | **可多行**。源码直接可见的值得注意信息（注解缺失、可见的字符串字面量、签名暴露等）。**没有就整行省略**，不要写"无" |

### 按分类的补充字段

每个分类都有几条**基本信息**（识别到就该写），其它字段是可选的（能从源码直接看到就写，看不到就空）。**不为了写全而去挖**。

| 分类 | 补充字段 |
|---|---|
| REST | `**URL**`（基本）<br>`**入口**`（基本）<br>`**参数**`（可选，含约束）<br>`**接口定义**`（可选，spec 文件完整相对路径，如 `api/swagger.yaml`） |
| MQ | `**队列/Topic**`（基本）<br>`**消费者**`（基本，完整相对路径 + 行号 + 函数名）<br>`**接口定义**`（可选，队列配置完整相对路径 + 行号） |
| gRPC | `**服务**`（基本）<br>`**方法**`（基本）<br>`**Proto**`（可选，完整相对路径） |
| WebSocket | `**端点**`（基本）<br>`**处理器**`（基本，完整相对路径 + 行号 + 函数名） |
| GraphQL | `**字段**`（基本）<br>`**类型**`（可选）<br>`**Resolver**`（可选，完整相对路径）<br>`**Schema**`（可选，`.graphqls` 完整相对路径） |
| SCRIPT | `**脚本名**`（基本）<br>`**语言**`（可选）<br>`**入口**`（可选，完整相对路径） |
| TOOL | `**工具名**`（基本）<br>`**语言**`（可选）<br>`**入口**`（可选，完整相对路径） |
| CRON | `**表达式**`（基本）<br>`**命令**`（基本）<br>`**文件**`（可选，完整相对路径） |
| CLI | `**命令名**`（基本）<br>`**入口**`（可选，完整相对路径） |
| SDK | `**SDK 名**`（基本）<br>`**语言**`（可选）<br>`**入口**`（可选，完整相对路径） |

补充字段写在通用字段之后，每个字段独占一行。**所有文件路径都从当前工作目录起的完整相对路径，不省略、不截断**。

### 完整文件示例

文件名：`iface-REST-user-list.md`

```markdown
# 攻击面条目

- **类型**：iface
- **分类**：REST
- **URL**：`GET /api/users`
- **参数**：`query: page(int, required)`, `query: size(int, min=1, max=100)`
- **来源**：`src/main/java/com/acme/UserController.java:48 listUsers()`
- **描述**：
  查询用户列表，接收 query 参数 page、size。
- **入口**：`src/main/java/com/acme/UserController.java:48 listUsers()`
- **发现**：
  方法上没有鉴权注解。
  返回字段含手机号、邮箱。
```

## 工作流程

1. **预加载**：读 `references/constraints.md` 和 `references/recon-principles.md`
2. **理解收集指令**：从用户输入里提取
   - **目标**（可选）：用户指定的具体业务入口
   - **范围**：要扫哪个目录/项目/服务
   - **特征**：找什么类型的暴露面
   - **覆盖度**：有明确目标时精确匹配；无目标时全量
   - **输出偏好**（可选）
3. **检查输出目录**：先看 `discovered_surfaces/` 下是否已有 `*.md`；有就按「输出位置」小节的策略先问用户
4. **执行收集**：按三阶段浏览（阶段 0 项目类型识别 → 阶段 1 逐层浏览 → 阶段 2 推测 → 阶段 3 验证）
5. **逐个分类**：对每个候选对象确定 `type`、`category`、`slug`
6. **抽取字段**：填通用字段 + 分类补充字段；缺信息就省略（不要编）
7. **生成文件**：每个对象一个独立文件
8. **记录排除路径**：将跳过/排除的非目标路径追加写入 `.vuln_agent_output/meta/excluded-paths.md`
9. **汇报**：暴露面总数 + 分类分布 + 每个文件路径
10. **写入完成信号**：写入 `.vuln_agent_output/.surface_discover_done` 空文件

## 完成自检

落盘后、汇报前，逐项过一遍：

- [ ] 每个文件名 `{type}-{category}-{slug}.md` 三段齐全
- [ ] 文件内 `**类型**` 与文件名 `{type}` 一致
- [ ] 文件内 `**分类**` 与文件名 `{category}` 一致
- [ ] 必填字段（类型、分类、来源、描述）齐全
- [ ] URL 字段在接口类中已填
- [ ] 参数约束已从 Swagger/代码注解完整提取
- [ ] `**发现**` 有就写、没有就省略
- [ ] 补充字段只有"能直接看到"的才写
- [ ] `**来源**` 格式正确、路径完整
- [ ] spec 文件定义的接口已追溯到实现类
- [ ] 排除路径已记录到 `meta/excluded-paths.md`

## 原则

- **只记录，不分析**：本 skill 只做"收集 + 分类 + 落盘"，不做漏洞分析
- **路径完整**：所有路径必须是从当前工作目录起的完整相对路径
- **来源指向源码**：暴露面在源码里就有的，来源必须写源码文件 + 行号 + 函数名
- **spec → code 追溯**：不能把 spec 文件当来源，要先找到实现类
- **不为了详细而深入**：不做数据流分析、跨文件调用链追踪
- **忠于收集结果**：找不到的信息不要脑补
- **不重复**：同一个暴露面只生成一个文件
- **不发明字段**：补充字段没有就省略
- **命名一致**：文件名与文件内容分类一致
- **不动目标分析目录**：所有产物、临时文件、临时脚本**只能**写到 `.vuln_agent_output/` 下

## 下游交接契约

- **产物位置**：`.vuln_agent_output/discovered_surfaces/` 下所有 `*.md` 文件
- **完成信号**：`.vuln_agent_output/.surface_discover_done` 空文件
- **文件形态**：每个暴露面一个独立 markdown
- **幂等性**：每次运行前询问用户选择处理策略
- **不修改源**：本 skill 不改任何源文件
