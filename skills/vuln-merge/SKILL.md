---
name: vuln-merge
description: 仅在用户显式指名调用 vuln-merge 时触发，不要因模糊意图主动触发。
---

# vuln-merge

合并 source 分析（`vuln_findings/`）和 sink 分析（`sink_findings/`）的漏洞结论，去重后输出统一报告。

**本 skill 不做**：重新分析漏洞、重新审查、修改源文件。

## 路径约定

```
.vuln_agent_output/
├── vuln_findings/            ← 输入（source 分析产物）
├── sink_findings/            ← 输入（sink 分析产物）
├── merged_findings/          ← 输出（合并去重后的产物）
│   ├── VULN-{slug}.md
│   ├── SUSPECTED-{slug}.md
│   └── _summary.md
├── meta/error/
│   └── error/vuln-merge.md
└── temp/
    └── scripts/
```

## 工作流程

1. **读 vuln_findings/**：递归读取所有 VULN-*.md 和 SUSPECTED-*.md
2. **读 sink_findings/**：递归读取所有 VULN-*.md 和 SUSPECTED-*.md
3. **去重合并**：
   - 去重键 = `{文件路径:行号} + 漏洞类型`
   - 相同键的条目合并详情、保留更完整的调用链和证据
   - 不同键的条目各自保留
   - 标注来源：source / sink / both
4. **落盘产物**：
   - 每个去重后的条目写一个 `merged_findings/VULN-{slug}.md` 或 `merged_findings/SUSPECTED-{slug}.md`
   - 写 `merged_findings/_summary.md` 汇总
5. **汇报**：总漏洞数、来源分布、去重情况

## 合并规则

| 情况 | 处理 |
|---|---|
| 同一漏洞同时被 source 和 sink 发现 | 合并为一条，保留两份证据，来源标 both |
| 同一漏洞仅被 source 发现 | 原样保留，来源标 source |
| 同一漏洞仅被 sink 发现 | 原样保留，来源标 sink |
| 描述同一漏洞但位置不同 | 按更精确的位置合并，标注两处位置 |
| CLEAN / DISMISSED | 不纳入合并结果 |

## 输出格式

### VULN-{slug}.md

```
# {漏洞名称}

**来源**：source / sink / both
**类型**：{漏洞分类}
**位置**：{文件:行号}
**CVSS 评分**：{X.X} **严重性**：{无/低/中/高/严重}
**触发条件**：{如何触发}
**影响**：{可能造成的危害}
**Payload**：{具体攻击 payload 或 PoC}
**调用链**：{入口 → ... → 敏感操作}
**建议**：{修复建议}
**事实依据**：{关键代码片段 + 分析说明}
```

### SUSPECTED-{slug}.md

```
# {漏洞名称}

**来源**：source / sink / both
**类型**：{漏洞分类}
**位置**：{文件:行号}
**信息缺口**：{具体哪段信息缺失}
**尝试**：{已做的分析尝试}
```

### _summary.md

```
# 安全分析汇总

**分析范围**：{项目路径}
**分析时间**：{ISO 8601}

## 统计

| 类别 | 数量 |
|---|---|
| 确认漏洞 | X |
| 疑似漏洞 | Y |
| 合计 | Z |

## 来源分布

| 来源 | 漏洞数 |
|---|---|
| source 分析 | A |
| sink 分析 | B |
| 两者同时发现 | C |

## 漏洞列表

- VULN-{slug}.md — {标题}（来源: {source/sink/both}）
- ...
```

## 原则

- **只合并，不分析**：不做新漏洞发现、不做审查
- **保留来源标记**：每条结论标注来自 source / sink / both
- **不动源**：不修改任何源文件、不修改 vuln_findings/ 和 sink_findings/ 产物
- **不动目标分析目录**：所有产物**只能**写到 `.vuln_agent_output/merged_findings/` 下
