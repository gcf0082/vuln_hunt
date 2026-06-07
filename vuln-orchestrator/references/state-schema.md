# 状态文件 Schema

**文件路径**：`.vuln_agent_output/.orchestrator-state.json`（当前工作目录下）

**读写责任**：仅 vuln-orchestrator 写。子 skill 不读不写此文件。

## 完整 Schema

```json
{
  "$schema": "vuln-orchestrator/state-v1",
  "pipeline_id": "uuid-v4",
  "schema_version": "1.0",

  "started_at": "2026-06-07T14:30:00Z",
  "last_updated_at": "2026-06-07T14:35:22Z",
  "finished_at": null,

  "concurrency": 5,

  "current_stage": 1,
  "overall_status": "running",

  "stage_status": {
    "0": "done",
    "1": "running",
    "2": "pending",
    "3": "pending"
  },

  "stage_0_params": {
    "scope": "/path/to/project",
    "features": "REST + MQ + Cron",
    "coverage": "full",
    "strategy": "clear"
  },

  "stage_0_result": {
    "surfaces": ["iface-REST-user-list", "noniface-CRON-daily-cleanup"],
    "count": 2
  },

  "items": {
    "stage_1": {
      "iface-REST-user-list": {
        "status": "done",
        "input": "iface-REST-user-list.md",
        "output": "iface-REST-user-list.md",
        "started_at": "2026-06-07T14:31:00Z",
        "finished_at": "2026-06-07T14:33:15Z",
        "error": null,
        "retry_count": 0
      },
      "noniface-CRON-daily-cleanup": {
        "status": "failed",
        "input": "noniface-CRON-daily-cleanup.md",
        "output": null,
        "started_at": "2026-06-07T14:31:00Z",
        "finished_at": "2026-06-07T14:32:05Z",
        "error": "subagent dispatch timeout after 30min",
        "retry_count": 1
      }
    },
    "stage_2": {
      "iface-REST-user-list": {
        "status": "pending",
        "input": "iface-REST-user-list.md",
        "output": null,
        "started_at": null,
        "finished_at": null,
        "error": null,
        "retry_count": 0,
        "findings_count": null
      }
    },
    "stage_3": {
      "VULN-iface-REST-user-list-1": {
        "status": "pending",
        "input": "VULN-iface-REST-user-list-1.md",
        "output": null,
        "started_at": null,
        "finished_at": null,
        "error": null,
        "retry_count": 0
      }
    }
  },

  "errors": [
    {
      "stage": 1,
      "item": "noniface-CRON-daily-cleanup",
      "error": "subagent dispatch timeout after 30min",
      "timestamp": "2026-06-07T14:32:05Z"
    }
  ],

  "summary": {
    "stage_0_surfaces_count": 2,
    "stage_1_done": 1, "stage_1_failed": 1,
    "stage_2_done": 0, "stage_2_failed": 0,
    "stage_3_done": 0, "stage_3_failed": 0
  }
}
```

## 字段定义

| 字段 | 类型 | 说明 |
|---|---|---|
| `pipeline_id` | uuid-v4 | 唯一标识一次流水线运行 |
| `schema_version` | "1.0" | 本文件 schema 版本，便于未来迁移 |
| `started_at` | ISO 8601 | 首次 start 触发时间 |
| `last_updated_at` | ISO 8601 | 任何字段变更时更新 |
| `finished_at` | ISO 8601 \| null | PIPELINE_DONE 时填入 |
| `concurrency` | int | 每 stage 内最大并发数，默认 5 |
| `current_stage` | int 0-3 \| "done" | 当前执行到哪个 stage |
| `overall_status` | string | pending / running / done / aborted |
| `stage_status` | object {0..3: string} | 每 stage 状态：pending / running / done / failed / paused / aborted |
| `stage_0_params` | object | 用户给 stage 0 的收集参数 |
| `stage_0_result.surfaces` | string[] | stage 0 产出的 surface slug 列表 |
| `items.stage_N` | object | stage N 的每个 item 一条记录 |
| `items[].status` | string | pending / running / done / failed |
| `items[].input` | string | 输入文件路径（相对 work_dir） |
| `items[].output` | string \| null | 输出文件路径（成功后填入） |
| `items[].error` | string \| null | 错误消息 |
| `items[].retry_count` | int | 已重试次数 |
| `items[].findings_count` | int \| null | 仅 stage 2：产出的 findings 数量 |
| `errors[]` | array | 所有失败项的汇总（与 items 互补） |
| `summary` | object | 计数统计，便于快速汇报 |

## 写入时机

- **state 初始化**：start 触发时写
- **item 状态变更**：每完成一个 subagent dispatch → 立即更新对应 item + last_updated_at
- **stage 状态变更**：stage 进入时 running、退出时 done/failed → 立即更新
- **每轮派发前**：写一次 last_updated_at
- **PIPELINE_DONE**：写 finished_at + overall_status=done

## 损坏处理

如果文件存在但 JSON parse 失败，vuln-orchestrator **必须**：
1. 拒绝启动
2. 提示用户："状态文件 `.orchestrator-state.json` JSON 损坏，无法解析。请检查文件内容或选择删除后重试。"
3. **不要**自动删除或覆盖损坏文件

## 迁移

未来 schema 变更时（`schema_version` 不匹配当前 LLM 加载的版本）：
- 读取时检测不匹配
- 提示用户："状态文件 schema 版本 X.Y 与本 skill 不兼容，请删除后重跑"
