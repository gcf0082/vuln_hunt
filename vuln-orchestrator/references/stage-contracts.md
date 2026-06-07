# Stage 契约

每个 stage 的输入、输出、完成判据。

## Stage 0: generate-surface

| 字段 | 内容 |
|---|---|
| 调用的 skill | `generate-surface` |
| 派发的 subagent | `surface-collector` |
| 输入参数 | scope (string), features (string), coverage (string), strategy (string) |
| 输入产物 | 无 |
| 输出产物 | `{work_dir}/.vuln_agent_output/discovered_surfaces/*.md` |
| 完成判据 | `.vuln_agent_output/.collect_done` 存在 **且** `discovered_surfaces/` 至少一个 `*.md` |
| 特殊情况 | 0 个 surface → 不推进，提示用户 |

**派发参数模板**（给 surface-collector）：

```
scope: {stage_0_params.scope}
features: {stage_0_params.features}
coverage: {stage_0_params.coverage}
strategy: {stage_0_params.strategy}  # clear/overwrite/append
work_dir: .  # 当前工作目录（subagent 继承 cwd）
```

## Stage 1: analyze-surface

| 字段 | 内容 |
|---|---|
| 调用的 skill | `analyze-surface` |
| 派发的 subagent | `surface-analyst` |
| 输入参数 | surface_file (string), work_dir (string), extra_prompt (optional) |
| 输入产物 | `discovered_surfaces/{slug}.md` |
| 输出产物 | `analyzed_surfaces/{slug}.md`（同名） |
| 完成判据 | `items.stage_1[*].status` 全部 ∈ {done, failed}，且至少一个 done |
| 失败判据 | 输出文件不存在 或 subagent 返回 error |

**派发参数模板**（给 surface-analyst）：

```
surface_file: {items.stage_1[slug].input}
work_dir: .  # 当前工作目录（subagent 继承 cwd）
extra_prompt: {用户传入 or null}
```

**item 初始化**（stage 0 完成后）：

```json
"stage_1": {
  "<slug>": {
    "status": "pending",
    "input": "<slug>.md",
    "output": null,
    "error": null
  }
}
```

## Stage 2: analyze-vulnerability

| 字段 | 内容 |
|---|---|
| 调用的 skill | `surface_vuln_analyzer`（frontmatter name: `analyze-vulnerability`） |
| 派发的 subagent | `vulnerability-analyst` |
| 输入参数 | surface_file (string), work_dir (string), vuln_rules (list, optional), extra_prompt (optional) |
| 输入产物 | `analyzed_surfaces/{slug}.md` |
| 输出产物 | `vuln_findings/{VULN\|DISMISSED\|CLEAN\|SUSPECTED}-{slug}-{n}.md`（**多个**） |
| 完成判据 | `items.stage_2[*].status` 全部 ∈ {done, failed}，且至少一个 done |
| 失败判据 | 任何 subagent 返回 error |
| 产物计数 | `findings_count` = `ls vuln_findings/ | grep {slug} | wc -l` |

**派发参数模板**（给 vulnerability-analyst）：

```
surface_file: {items.stage_2[slug].input}
work_dir: .  # 当前工作目录（subagent 继承 cwd）
vuln_rules: {用户指定 or 全 13 类}
extra_prompt: {用户传入 or null}
```

**item 初始化**（stage 1 完成后，对每个 stage 1 done 的 slug）：

```json
"stage_2": {
  "<slug>": {
    "status": "pending",
    "input": "<slug>.md",
    "output": null,
    "error": null,
    "findings_count": null
  }
}
```

## Stage 3: review-vuln

| 字段 | 内容 |
|---|---|
| 调用的 skill | `review-vuln` |
| 派发的 subagent | `vuln-re-analyzer` |
| 输入参数 | vuln_file (string), work_dir (string), extra_prompt (optional) |
| 输入产物 | `vuln_findings/{prefix}-{slug}-{n}.md` |
| 输出产物 | `vuln_reviews/{VULN\|NOVULN\|SUSPECTED}-{vuln_stem}.md`（1 对 1） |
| 完成判据 | `items.stage_3[*].status` 全部 ∈ {done, failed} |
| 失败判据 | 任何 subagent 返回 error |

**item 初始化**（stage 2 完成后，对每个 finding）：

```json
"stage_3": {
  "<vuln_stem>": {
    "status": "pending",
    "input": "<vuln_stem>.md",
    "output": null,
    "error": null
  }
}
```

注意：vuln_stem 是 finding 文件名去掉扩展名（如 `VULN-iface-REST-user-list-1`）。

## 衔接校验

进入下一 stage 前必须确认：

- 当前 stage 全部 done 或 failed
- 当前 stage 至少一个 done（否则下一 stage 输入为空）
- 失败项已记入 `errors[]`

如果当前 stage 全部 failed：
- 仍推进（继续走完流水线，stage 2/3 可能输入为空）
- 最终报告里明确标注"stage N 全部失败，无产物进入下一 stage"
