# 终态报告

vuln-orchestrator 在以下时机产出报告：
- 用户调用 `status` 意图
- 整个流水线 `PIPELINE_DONE`
- 单个 stage 完成（简短进度报告）

## 单 Stage 进度报告

```
✅ Stage 1 (analyze-surface) 完成
- 总数: 23
- 成功: 22
- 失败: 1
- 失败项: iface-REST-payment-callback (subagent timeout)
- 耗时: 4m 12s

进入 Stage 2 ...
```

## PIPELINE_DONE 完整报告

```markdown
# Vuln Hunt Pipeline 报告

**Pipeline ID**: {pipeline_id}
**开始时间**: {started_at}
**完成时间**: {finished_at}
**耗时**: {duration}（人话: "2 小时 15 分"）
**最终状态**: ✅ DONE

---

## 阶段总览

| Stage | 名称 | 状态 | 总数 | 成功 | 失败 |
|---|---|---|---|---|---|
| 0 | generate-surface | ✅ done | 1 | 1 | 0 |
| 1 | analyze-surface | ✅ done | 23 | 22 | 1 |
| 2 | analyze-vulnerability | ✅ done | 22 | 20 | 2 |
| 3 | review-vuln | ✅ done | 45 | 43 | 2 |

---

## 漏洞分析结论（按 surface 聚合）

### iface-REST-user-list
- 确认漏洞: 2（VULN-iface-REST-user-list-1.md, VULN-iface-REST-user-list-3.md）
- 排除: 5
- 干净: 8
- 疑似: 1
- 审查结论: 2 VULN / 0 NOVULN / 0 SUSPECTED

### noniface-CRON-daily-cleanup
- 确认漏洞: 0
- 排除: 3
- 干净: 1
- 疑似: 0
- 审查结论: 0 VULN / 0 NOVULN / 0 SUSPECTED

### iface-MQ-order-event
- 确认漏洞: 1
- 排除: 2
- 干净: 4
- 疑似: 0
- 审查结论: 1 VULN / 0 NOVULN / 0 SUSPECTED

... (每个 surface 一节，按 VULN 数量降序)

---

## 失败项汇总

| Stage | Item | 错误 | 时间 |
|---|---|---|---|
| 1 | iface-REST-payment-callback | subagent timeout after 30min | 2026-06-07T14:35:22Z |
| 2 | iface-MQ-order-event | LLM API rate limit | 2026-06-07T15:01:10Z |

修复后可调用 "重跑失败的" 触发 retry-failed。

---

## 产物路径

- discovered_surfaces/: 23 个文件
- analyzed_surfaces/: 22 个文件
- vuln_findings/: 45 个文件
- vuln_reviews/: 43 个文件
- 完整状态: {work_dir}/.vuln_agent_output/.orchestrator-state.json

---

## 关键 VULN 列表（审查后确认）

| Surface | 漏洞标题 | CVSS | 位置 |
|---|---|---|---|
| iface-REST-user-list | SQL injection in /api/users search | 9.8 | UserController.java:48 |
| iface-MQ-order-event | 反序列化漏洞 | 8.1 | OrderEventConsumer.java:31 |

（仅列审查后 VULN 结论的，按 CVSS 降序）
```

## status 报告（中间状态）

```markdown
# Vuln Hunt Pipeline 状态

**Pipeline ID**: {pipeline_id}
**当前 Stage**: 2 (analyze-vulnerability)
**整体状态**: 🔄 running

## 各 Stage 进度

| Stage | 状态 | 进度 |
|---|---|---|
| 0 | ✅ done | 1/1 (100%) |
| 1 | ✅ done | 22/23 (96%) — 1 failed |
| 2 | 🔄 running | 12/22 (55%) — 10 in flight, 0 done yet |
| 3 | ⏳ pending | 0/45 |

## 当前 in-flight 任务

- iface-MQ-order-event (stage 2)
- iface-REST-payment-create (stage 2)
- iface-MQ-inventory-update (stage 2)
- iface-REST-search (stage 2)
- iface-REST-file-upload (stage 2)

## 失败项

| Stage | Item | 错误 |
|---|---|---|
| 1 | iface-REST-payment-callback | subagent timeout |

## 下一步

继续 stage 2，预计还需 ~15 分钟。
```

## 报告生成规则

LLM 在生成报告时**按需读产物文件**，但**不打开每个 finding 的内容**——只读文件名前缀和必要的元数据（已在 `state.summary` 缓存）。

- 单 stage 完成时：LLM 从 `state.items[stage_N]` 直接生成
- PIPELINE_DONE 时：LLM 读 `state.summary` 生成全报告
- 关键 VULN 列表：LLM 扫 `vuln_reviews/VULN-*.md` 文件名（不读内容），从文件名取 surface slug + 序号，按 CVSS 排序需要读文件——这一步骤**可选**，LLM 可仅按数量排序

## 报告输出位置

报告**不写入文件**——直接以文本形式在对话中输出。

如需持久化，用户可说"把报告保存到 {path}"，LLM 再写文件。
