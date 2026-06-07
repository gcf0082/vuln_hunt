---
name: sink-collect
description: 仅在用户显式指名调用 sink-collect 时触发，不要因模糊意图主动触发。
---

# sink-collect

## 定位

- **用户负责**：给一句自然语言意图（如"找所有 SQL 查询点" / "找命令执行" / "找文件上传处理"）
- **skill 负责**：从意图中**智能推断**要找的 sink 类型与范围 → 派发扫描 subagent → 按统一格式落盘到 `sink_list/`

skill 是 sink 列表的**采集与落盘**执行器——一次调用处理一次采集意图，输出 `sink_list/` 下的若干 sink 描述文件。

## 路径约定

本 skill 涉及的所有目录**统一在 `.vuln_agent_output/` 下**，当前工作目录视为被分析项目根：

```
.vuln_agent_output/
└── sink_list/                            ← 输出（sink 描述文件）
    ├── meta/
    │   └── error/sink-collect.md        ← 失败日志
    └── temp/
        └── scripts/                      ← 临时脚本（用完即弃）
```

## 任务澄清

### 何时反问

用户显式调用 `sink-collect` 但**未指定 sink 类型**时，**必须**先反问：

> 想找什么类型的 sink？（SQL / 命令 / 文件 / 网络 / 反序列化 / 弱加密 / ...）

- 用户给了具体类型 → 直接进入工作流程
- 用户说"全部" / 没说具体 → 派 subagent 扫描全部危险函数类

## 智能规划子任务

进入采集前，根据意图复杂度智能规划子任务（单一类型 / 多类型 / 按模块分组），由 LLM 自主判断。

## 智能推断

从用户消息中**智能抽取**采集参数：

| 维度 | 抽取自 | 示例 |
|---|---|---|
| `type` | 危险操作类型 | sql / cmd / fileio / net / deserialize / crypto / xxe / redirect / ... |
| `scope` | 范围 | 当前项目 / 指定目录 / 全部 / 某个模块 |
| `focus` | 关注点（可选） | 特定文件 / 函数 / 注解 / 配置 |

**意图关键词 → type 映射**（仅供参考，LLM 应结合上下文判断）：

| 意图关键词 | 推断 type |
|---|---|
| "SQL / 数据库 / 注入 / query / 数据库查询" | sql |
| "命令 / shell / exec / 系统命令" | cmd |
| "文件 / 上传 / 路径 / 文件 I/O" | fileio |
| "网络 / HTTP 外呼 / SSRF / 请求" | net |
| "反序列化 / 序列化 / readObject" | deserialize |
| "加解密 / 弱加密 / 哈希" | crypto |
| "XXE / XML 解析" | xxe |
| "重定向 / redirect" | redirect |

**示例**：

| 用户消息 | 推断结果 |
|---|---|
| "找所有 SQL 查询点" | type=sql scope=当前项目 |
| "看看命令执行" | type=cmd scope=当前项目 |
| "扫一下文件上传" | type=fileio scope=当前项目 |
| "找 Runtime.exec 调用" | type=cmd scope=当前项目 |
| "扫整个项目" | type=all scope=当前项目 |

## 预加载

本 skill **无 references/ 子目录**——所有规则在本文档内完整表达，启动时**直接进入工作流程**。

## 工作流程

1. **解析意图**：从用户调用消息中抽取：
   - `type`（sink 类型）
   - `scope`（范围）
   - `focus`（关注点，可选）
2. **派发扫描 subagent**（`subagent_type=code-scanner`）：
   ```
   在 {scope} 范围内扫描 {type} 类型的危险操作
   危险函数清单：{type → 已知危险函数 / API 映射}
   输出：每个调用点的 {文件:行号, 函数名, 操作描述, 上下文}
   ```
3. **解析扫描结果**：从 subagent 返回中提取候选 sink 列表
4. **落盘产物**：每个 sink 写一个 `sink_list/{type}-{slug}-{MMDD-HHMMSS}.md`
5. **汇报**：sink 总数 + 分类统计

## 输出格式

### 文件命名规则

`{type}-{slug}-{MMDD-HHMMSS}.md`，其中：

- `type`：危险操作类型（sql / cmd / fileio / net / deserialize / crypto / xxe / redirect / ...）
- `slug`：简短英文标识（小写字母 + 连字符，描述该 sink 含义，如 `user-query` / `build-script` / `upload`）
- `{MMDD-HHMMSS}` = 生成时的时间戳（月日-时分秒），如 `0608-021435`

所有采集产物文件名**始终**带时间戳。同一秒内产生同名 type+slug 时，时间戳后追加 `-{n}`（n 从 2 起），如 `sql-user-query-0608-021435-2.md`。

示例：
- `sql-user-query-0608-021435.md`
- `cmd-build-script-0608-021435.md`
- `fileio-upload-0608-021435.md`

### 文件模板

```markdown
# {sink 标题}

**类型**：{sql / cmd / fileio / net / deserialize / crypto / xxe / redirect / ...}
**位置**：{文件路径:行号}
**函数**：{函数名}
**危险操作**：{具体描述}
**建议排查**：{sink-analyze-vuln 应关注的方向}
```

例：

```markdown
# User 查询接口

**类型**：sql
**位置**：`src/main/java/com/acme/UserDao.java:48`
**函数**：`findUserById(String id)`
**危险操作**：使用 Statement 拼接 SQL `SELECT * FROM users WHERE id = '` + id + `'`
**建议排查**：是否所有调用方都对 `id` 做了参数化绑定 / 校验
```

## 原则

- **意图推断为主**：用户一句话 → 智能解析
- **采集逻辑外包**：不内置规则，交给 subagent 扫描
- **格式统一**：所有 sink 文件格式一致
- **不重复**：同一 sink 不重复落盘
- **不动源**：不修改任何源文件、配置文件
- **不替调用方决策**：幂等策略由调用方负责
- **失败显式标注**：写进 `.vuln_agent_output/meta/error/sink-collect.md`
- **不动目标分析目录**：所有产物、临时文件、临时脚本**只能**写到 `.vuln_agent_output/` 下，**不得**在被分析项目源码目录里写任何文件

