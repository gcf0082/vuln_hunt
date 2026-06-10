---
name: callchain-trace
description: 仅在用户显式指名调用 callchain-trace 时触发，不要因模糊意图主动触发。调用链追踪技能——根据入口函数/接口生成核心向下调用链，只跟踪与业务强相关的函数，忽略判空/校验/日志等非核心函数，必须跟踪到最底层。遇分支复杂可拆为多棵树表示。
---

# callchain-trace

根据入口函数生成核心向下调用链。

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

每个函数名先用**两轮判定**确定是否追踪：

### 第一轮：名称启发

| 特征 | 初步分类 | 说明 |
|---|---|---|
| 含领域术语 `processOrder` / `calculatePremium` / `approveLoan` | 核心嫌疑 | 看起来在做业务 |
| 含 `log` / `print` / `debug` / `tracing` | 非核心 | 日志 |
| 含 `validate` / `check` / `assert` / `require` / `isValid` | 需看体 | 可能是核心也可能是普通校验 |
| 含 `get` / `set` / `to` / `from` / `format` / `convert` / `parse` | 非核心 | 纯工具转换 |
| 含 `save` / `persist` / `store` / `delete` / `update` | 核心 | IO/数据库 |
| 含 `send` / `fetch` / `request` / `call` / `invoke` | 核心嫌疑 | 网络/外部调用 |
| 标准库函数 / 三方库函数 | 非核心 | 不追进标准库 |
| 只有一行返回/抛异常的包装函数 | 非核心 | 纯转发 |

### 第二轮：体检查

对"需看体"的调用阅读函数体判定：

- **核心**：函数体内涉及 DB 操作、文件 I/O、网络请求、命令执行、业务决策（if 条件含领域含义）、调用其他已被判定核心的函数
- **非核心**：函数体仅包含 return / 抛异常 / 日志 / getter-setter / 仅调用标准库工具函数

### 语境再判断

考虑系统整体目的。例如合规系统中 `validateCompliance` 虽然名含 validate，但它是核心业务。

## 叶子定义

本 skill 的叶子是**无法在项目中找到定义的函数和配置**——标准库、三方库、外部 SDK、远程服务接口。但**项目拥有的配置文件和脚本不算终点**（MyBatis XML、shell 脚本、Dockerfile、CI 配置等），必须继续追踪到其中定义的具体操作。

每一条核心路径持续追踪直到抵达无法继续的信息边界。

## 深度追踪：配置文件与脚本

"找不到定义"不包括项目拥有的配置文件。以下场景必须继续追踪到配置/脚本层面：

### MyBatis / MyBatis-Plus

遇到 MyBatis API 调用时，解析到对应的 SQL 语句：

| 代码模式 | 追踪方式 |
|---|---|
| `SqlSession.select("namespace.id", param)` | 搜索 XML mapper，按 namespace.id 定位 `<select>` 标签和行号 |
| `Mapper.findByXXX(param)` | 按 Mapper 接口名 + 方法名定位 XML 中对应 `<select/sql>` |
| `@Select("SELECT ...")` / `@Update` 等注解 | 注解本身已含 SQL 正文，直接提取 |
| `LambdaQueryWrapper` / `QueryWrapper` | 标注构造出的 SQL 特征（表名 + 条件字段） |

XML mapper 中的 SQL 标注到 `{MapperXml}:{lineNumber}`：

```
Mapper.findOrderById(id)
  └── OrderMapper.selectByPrimaryKey(id)
      └── OrderMapper.xml:47  →  SELECT * FROM orders WHERE id = #{id}
```

### Shell 脚本

遇到脚本执行调用时，找到对应脚本文件并继续追踪内部命令链：

| 代码模式 | 追踪方式 |
|---|---|
| `Runtime.exec("bash deploy.sh " + param)` | 搜索 `deploy.sh`，读取其内容 |
| `ProcessBuilder("bash", "backup.sh")` | 搜索 `backup.sh`，读取其内容 |
| 脚本本身 | 提取脚本中所有外部命令作为链的下一跳 |
| 脚本中调用另一个脚本 | 继续追踪该脚本 |

脚本内容以**命令为单位**纳入调用树：

```
deploy.sh:5  →  git pull origin main
deploy.sh:8  →  mvn clean package -DskipTests
deploy.sh:12 →  cp target/app.jar /usr/local/app/
```

### 其他配置驱动的框架

| 框架/场景 | 追踪方式 |
|---|---|
| Spring Data JPA `@Query` | 提取注解中的 JPQL/SQL |
| Freemarker / Thymeleaf | 标注模板路径和变量来源 |
| Dockerfile | 标注 RUN/CMD/ENTRYPOINT 命令 |
| CI 配置（`.github/workflows/`、`.gitlab-ci.yml`） | 标注实际执行的步骤命令 |

## 跟踪流程

```
trace(func, depth=0, path=[], visited=set()):
  if func in visited → 闭环，记叶子(状态=闭环)
    return
  if depth > 15 → 超深，记叶子(状态=超深)
    return
  if func 在项目中找不到定义 → 真正叶子，记叶子(状态=外部函数)
    return

  visited.add(func)
  读 func 函数体
  提取所有函数调用 callees[]
  每个 callee 分类
  搜索 callee 在项目中是否存在定义

  if callee 在项目中找不到定义:
    记叶子(状态=外部函数)
  elif callee 是核心:
    trace(callee, depth+1, path+[func], visited)
  else:
    记叶子(状态=跳过)
```

预期链形：

```
入口 → 核心 → 核心 → ... → 核心 → 外部函数（真正的叶子）
                               ↳ 跳过（源码存在但非核心）
```

### 接口/抽象方法处理

遇到接口或抽象方法调用（如 `service.process(request)`、`List.add()`）：

1. 在同一项目中搜索该接口/父类的具体实现类
2. 如果找到**唯一实现** → 按具体实现继续追踪
3. 如果找到**多个实现** → 分几个情况处理：
   - 能通过上下文（类型判断、配置）确定实际实现 → 追该实现
   - 无法确定 → 每个实现分别展开为不同子树
   - 实现数量过多（>5） → 选取最可能的 1-2 个并标注

## 分支分树

| 场景 | 处理 |
|---|---|
| 单一主路径 | 一棵树完整展示 |
| if/switch 分支业务语义不同 | 每条独立成树，节点标注分叉条件 |
| 某条分支深度远超其他 | 单独成树避免嵌套过深 |
| 分支间有交叉调用 | 保持交叉标注，优先逻辑完整性 |

## 终止条件

| 条件 | 标记 | 说明 |
|---|---|---|---|
| 找不到定义（标准库/三方库/外部服务） | 外部函数 🔗 | 默认叶子状态；MyBatis XML / shell 脚本 / Dockerfile 等有项目配置可追踪的不算 |
| 源码存在但判定为非核心 | 跳过 ⛔ | 如 `log.info()` / `getTime()`，标记可追但选择跳过 |
| 检测到环 | 闭环 🔄 | 标注循环引用关系 |
| 接口多实现 | 多态 ⚡ | 标注找到几个实现 |
| 深度 > 15 | 超深 ⚠ | 标注已追踪层级 |

## 输出格式

```
## 调用树

### 树 1：{标题（如"主流程"）}
{分叉条件说明}
{entry_func}
├── {func_a}（核心）
│   ├── {func_a1}（核心）
│   │   └── OrderMapper.xml:47 — `SELECT * FROM orders WHERE id = #{id}`
│   └── {func_a2}（多态 ⚡ — 找到 2 个实现，见子树）
├── {func_b}（跳过 ⛔ — 日志记录）
├── {func_c}（核心）
│   └── deploy.sh
│       ├── deploy.sh:5 — `git pull origin main`
│       ├── deploy.sh:8 — `mvn clean package`
│       └── deploy.sh:12 — `cp target/app.jar /usr/local/app/`
└── {func_d}（核心）
    └── okhttp3:call.execute — `POST https://api.payment.com/charge`

### 树 2：{标题（如"退款分支，if refundFlag"）}
...

### 叶子核心目标

只汇总量终涉及**文件/命令/SQL/网络**的核心操作：

| 核心目标 | 所在树 | 说明 |
|---|---|---|
| `OrderMapper.xml:47` | 树1 | `SELECT * FROM orders WHERE id = #{id}` |
| `deploy.sh:5` | 树1 | `git pull origin main` |
| `deploy.sh:12` | 树1 | `cp target/app.jar /usr/local/app/` |
| `okhttp3:execute` → `POST /charge` | 树1 | 调用支付网关 |
```

不列入汇总的举例：`String.format()` / `DateTime.now()` / `log.info()` / `JSON.parse()`。

- 调用树上保留完整结构（含外部函数标记），汇总表只提取文件/命令/SQL/网络四类核心操作
- 每个核心目标标注操作对象（文件路径、命令、SQL 特征、URL/接口名）
- 同一条核心分支以最外层操作为准，避免链上重复

## 质量纪律

- **不编造**：搜不到定义的调用标记边界，不臆测实现体
- **不漏记**：函数体中每个出现的外部调用要么展开到底，要么在调用树上标注状态；仅在叶子汇总中筛选核心路径终点
- **环必检**：路径中检测到重复函数立即停止并标注
- **签名完整**：每个函数标注 `{文件名:行号}`，便于验证
- **多态不静默**：接口/抽象方法调用必须有去向说明（具体实现 / 边界 / 标注无法确定）
- **不追过高**：适当控制深度（默认 15 跳），给用户解释截断的原因和位置
