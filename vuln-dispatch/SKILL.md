---
name: vuln-dispatch
description: 仅在用户显式指名调用 vuln-dispatch 时触发，不要因模糊意图主动触发。
---

# vuln-dispatch

本 skill **只做一件事**：从用户消息中**识别意图** → 派发给 `source-orchestrator`、`sink-orchestrator`、`full-orchestrator` 或直接调子 skill。

**绝不读源码、绝不分析代码、绝不写文件。只做派发。**

## 规划示例

| 任务 | 规划 | 理由 |
|---|---|---|
| 分析修改密码的 REST 接口是否存在 SQL 注入 | source | 从接口入口追踪调用链，覆盖参数校验、SQL 拼接的全路径 |
| 找所有文件上传接口并分析路径穿越风险 | source | 从接口入口追踪文件写入路径，看是否可被 ../ 绕过 |
| 扫全项目 Runtime.exec 调用点 | sink | 从危险函数出发反向追踪调用方，寻找外部可控入参 |
| 看看用户登录接口有没有鉴伪绕过 | source | 从接口入口分析认证逻辑的完整流程 |
| 查一下所有 Statement 拼接的 SQL 查询 | sink | 从危险 API 出发反向追调用链，定位外部入参来源 |
| 检查订单导出功能是否存在 SSRF | source | 从导出接口追踪 HTTP 外呼的目标 URL 构造过程 |
| 全项目找反序列化漏洞 | sink | 从 readObject/readUnshared 等危险函数出发反向追踪 |
| 分析管理员后台的 API 是否存在命令注入 | source | 从接口入口追踪命令构造的完整路径 |
| 找所有 MyBatis `${}` 拼接入参的地方 | sink | 从 $ 拼接的特征出发反向定位入参来源 |
| 分析当前目录的安全风险 | sink + source | 先 sink 从危险函数反向追踪已知风险点，再 source 从入口正向覆盖完整攻击面，最后合并汇总 |
| 帮我收集这个项目的所有 REST 接口 | 只收集 | 只做暴露面采集，不做分析 |
| 先扫接口，再根据接口里的危险操作追 sink | source → sink | 先 source 收集分析入口，再 sink 反向追踪接口中发现的危险操作 |
| 分析用户登录接口是否存在命令注入 | source（vuln_type=cmd） | 从接口入口追踪调用链，只关注命令注入，不做其他类型分析 |
| 扫全项目有没有命令执行漏洞 | sink（vuln_type=cmd） | 从危险函数出发反向追踪，只关注命令执行，不做其他类型分析 |

## 步骤

1. 读用户消息
2. 识别意图，提取 `vuln_type`（漏洞类型：命令注入→cmd、SQL注入→sql、路径穿越→path_traversal 等）。透传给下游 orchestrator
3. 扫攻击面 / 找入口 → 调 `source-orchestrator`，透传用户原消息
4. 查危险点 / 找 sink → 调 `sink-orchestrator`，透传用户原消息
5. 两种意图都看得出 → 调 `full-orchestrator`，透传用户原消息
6. 全面安全评估 / 安全风险 / 安全检查 → 调 `full-orchestrator`，透传用户原消息
7. 只收集 / 只采集 → 调 `source-collect` 或 `sink-collect`（根据用户说的是入口还是危险点），透传用户原消息
8. 先 source 后 sink → 调 `full-orchestrator --order source-first`，透传用户原消息
9. 完全识别不出 → 反问「扫攻击面（source）还是查危险点（sink）？」

## 原则

- **识别意图，不机械匹配**：从用户消息的语义判断是 source 还是 sink
- **不解读上下文**：不读项目、不查结构，只读用户消息文本
- **透传用户原消息**：原封不动转给被派发的 skill
- **不写任何文件**：本 skill 唯一动作是调别的 skill
