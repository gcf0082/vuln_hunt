---
name: callchain-trace
description: 仅在用户显式指名调用 callchain-trace 时触发。
---

# 核心任务

从入口出发，沿调用链只追踪业务强相关函数，输出调用链直达外部函数边界，用于快速理解核心业务逻辑。get/set/put 等纯数据传递不体现。

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
| 标准库函数 / 三方库函数 | 非核心 | 不追进标准库 |
| 只有一行返回/抛异常的包装函数 | 非核心 | 纯转发 |

### 语境再判断

名称启发无法确定的（如 validate/check）结合业务上下文判定。合规系统中 `validateCompliance` 是核心业务，普通空值校验则不是。

## 叶子定义

叶子是**项目中找不到定义的函数**（标准库/三方库/外部 SDK）。项目拥有的配置文件/脚本不是终点，须继续解析到具体操作：

- **MyBatis**: 搜索 XML mapper 定位 SQL 行号和内容；注解 SQL 直接提取
- **Shell 脚本**: 找到脚本文件，提取每条命令作为链的下一跳，嵌套脚本继续追踪
- **其他**: Spring Data JPA @Query 提取 SQL；Dockerfile/CI 配置标注执行的命令

## 跟踪流程

被调函数必须尽可能找到其定义，调用链的准确性取决于此。搜不到定义就停止是最后手段，在此之前应尝试：

- 接口/抽象方法 → 搜索项目内实现类
- 跨模块调用 → 在相关模块中搜索
- 框架入口（MyBatis Mapper 等）→ 搜索 XML 配置

核心的递归展开，搜不到定义的停止。

预期链形：入口 → 核心 → ... → 核心 → 外部函数

### 接口/抽象方法处理

遇到接口或抽象方法调用（如 `service.process(request)`、`List.add()`）：

1. 在同一项目中搜索该接口/父类的具体实现类
2. 如果找到**唯一实现** → 按具体实现继续追踪
3. 如果找到**多个实现** → 分几个情况处理：
   - 能通过上下文（类型判断、配置）确定实际实现 → 追该实现
   - 无法确定 → 每个实现分别展开为不同子树
   - 实现数量过多（>5） → 选取最可能的 1-2 个并标注

## 输出格式

### 调用链

按层级缩进展示每个函数的调用顺序：

```
### 树 1：主流程
processOrder (OrderController.java:32)
├── calculateAmount (OrderService.java:58)
│   └── OrderMapper.xml:47 — SELECT * FROM orders WHERE id = #{id}
├── paymentService.charge (PaymentService.java:21)
│   └── okhttp3:execute
└── notifyUser (NotificationService.java:15)
    └── sendEmail
```

- 每个节点标注 `文件名:行号`，外部库函数只标函数名
- 只展示核心路径，非核心函数不出现；纯 getter/setter、简单 put 转发、HashMap.get 等标准库数据访问、空实现等自动跳过
- 默认一棵树，特别复杂时才拆多棵树

## 质量纪律

- **准确性**：被调函数尽可能找到定义再展开，不因搜索麻烦就过早停止
- **环必检**：路径中检测到重复函数立即停止
