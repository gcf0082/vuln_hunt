# Pipeline 状态机

## 标记文件

| 标记文件 | 含义 | 写入者 |
|---|---|---|
| `.vuln_agent_output/.collect_done` | 暴露面采集完成 | source-collect |
| `.vuln_agent_output/.plan_done` | 漏洞规划完成 | vuln-planner |

## 阶段完成判定

| 阶段 | 完成条件 | 检测方式 |
|---|---|---|
| collect | `.collect_done` 存在 **或** `discovered_surfaces/` 无 `.md` 文件 | 标记文件 + 目录扫描 |
| analyze | `analyze_pending` 为空（所有 discovered surface 都有对应 analyzed surface） | stem 匹配 |
| plan | `plan_pending` 为空（所有 analyzed surface 都有对应 vuln_plans/ 子目录） | stem 匹配 |
| vuln | `vuln_pending` 为空（所有 analyzed surface 的 risk plan 都已产出 vuln finding） | stem 匹配 + none-risk 跳过 |
| review | `review_pending` 为空（所有 vuln finding 都有对应 review 文件） | stem 匹配 |

## Stem 匹配规则

产物文件名的 stem（不含扩展名）用于跨阶段匹配：

- **discovered**: `iface-REST-user-list-0608-021435.md` → stem=`iface-REST-user-list-0608-021435`
- **analyzed**: 文件名 stem 同 discovered（保留时间戳）
- **planned**: `vuln_plans/iface-REST-user-list-0608-021435/` 子目录名
- **vuln_finding**: `VULN-iface-REST-user-list-0608-021435-1.md` → 去掉前缀 `VULN-` 和后缀 `-{n}` → stem=`iface-REST-user-list-0608-021435`
- **review**: 同上

## 边缘情况

- **空输出目录**：所有阶段 pending，从 collect 开始
- **部分完成**：已完成阶段跳过，只跑 pending 项
- **none-risk 计划**：只有 `none-risk-*.md` 的 surface 跳过 vuln 和 review 阶段（无漏洞可分析）
- **子目录结构**：`REST/iface-X.md` 等子目录中的文件，relative path 包含子目录名
- **整阶段无产物**：直接进入下一 stage（输入为空就空跑）
