# Subagent 派发协议

## 派发工具

使用 opencode 的 `task` 工具派发 subagent。每次 `task` 调用 = 启动一个 subagent = 一次 LLM 调用。

**关键**：在**同一次 LLM 响应中**发起多个 `task` 调用 = 并行执行。所以 5 并发 = 在一个响应中发 ≤5 个 task。

## Subagent 类型映射

| Stage | 派发方 (subagent_type) | 用途 |
|---|---|---|
| 0 | `surface-collector` | 调用 generate-surface，列出 discovered_surfaces/ |
| 1 | `surface-analyst` | 调用 analyze-surface，单条目 |
| 2 | `vulnerability-analyst` | 调用 analyze-vulnerability，单条目 |
| 3 | `vuln-re-analyzer` | 调用 review-vuln，单条目 |

## 派发 Prompt 模板

### Stage 0 派发（surface-collector）

```
调用 generate-surface skill 完成暴露面收集。

工作目录: {work_dir}
- scope: {stage_0_params.scope}
- features: {stage_0_params.features}
- coverage: {stage_0_params.coverage}
- strategy: {stage_0_params.strategy}  # clear/overwrite/append

完成信号: {work_dir}/.vuln_agent_output/.collect_done 存在
产物位置: {work_dir}/.vuln_agent_output/discovered_surfaces/

完成后请报告:
1. 收集到的 surface 总数
2. 每个生成的 surface 文件路径
3. 是否遇到歧义或可疑点
```

### Stage 1 派发（surface-analyst）

```
调用 analyze-surface skill 分析单个攻击面。

工作目录: {work_dir}
surface_file: {items.stage_1[slug].input}
(完整路径: {work_dir}/.vuln_agent_output/discovered_surfaces/{slug}.md)
extra_prompt: {用户传入 or 无}

完成后请报告:
1. 产物路径（{work_dir}/.vuln_agent_output/analyzed_surfaces/{slug}.md）
2. 流程图是否生成
3. 是否存在"未能追溯的引用"
4. 任何 error（写到 {work_dir}/.vuln_agent_output/meta/error/analyze-surface.md）
```

### Stage 2 派发（vulnerability-analyst）

```
调用 analyze-vulnerability skill（skill 名 surface_vuln_analyzer）做漏洞分析。

工作目录: {work_dir}
surface_file: {items.stage_2[slug].input}
(完整路径: {work_dir}/.vuln_agent_output/analyzed_surfaces/{slug}.md)
vuln_rules: {用户指定 or "all 13"}
extra_prompt: {用户传入 or 无}

完成后请报告:
1. 产出的 findings 数量 + 各自路径
2. 按档位分类（VULN / DISMISSED / CLEAN / SUSPECTED）的数量
3. 任何 error
```

### Stage 3 派发（vuln-re-analyzer）

```
调用 review-vuln skill 审查单个漏洞结论。

工作目录: {work_dir}
vuln_file: {items.stage_3[vuln_stem].input}
(完整路径: {work_dir}/.vuln_agent_output/vuln_findings/{vuln_stem}.md)
extra_prompt: {用户传入 or 无}

完成后请报告:
1. 审查产物路径（{work_dir}/.vuln_agent_output/vuln_reviews/{VULN|NOVULN|SUSPECTED}-{vuln_stem}.md）
2. 审查结论
3. 任何 error
```

## 并发槽位控制

每轮派发循环：

```
in_flight = 0
slots = concurrency  # 默认 5

while True:
    pending_items = [items for items if status == 'pending']
    if not pending_items:
        break

    batch = pending_items[:slots - in_flight]
    if not batch:
        # 等待 in_flight 完成（通过 LLM 等待 subagent 返回实现）
        break

    # 在同一次 LLM 响应中发起 batch.size 个 task 调用
    for item in batch:
        dispatch_task(item)

    # 等所有 task 返回（subagent 返回即 LLM 继续）
    # 然后解析每个 task 的结果，更新 state
    in_flight = 0
```

实际操作：LLM 在一次响应中发 N 个 task → 等所有返回 → 在下一次响应中处理结果 + 发起下一批。

## 超时与重试

- **单 subagent 超时**：默认 30 分钟（`task` 工具的默认超时）。可在派发时显式指定 `timeout` 参数。
- **失败重试**：subagent 返回 error → 标记 `retry_count += 1` → 下次派发循环再次尝试（最多 1 次额外重试 = 共 2 次机会）
- **subagent 本身崩溃**（工具层错误）：等同失败处理

## 派发失败 vs 逻辑失败

| 失败类型 | 表现 | 处理 |
|---|---|---|
| subagent 启动失败 | task 调用直接 error | retry_count += 1，重试 |
| subagent 运行时报错 | task 返回 error 字段 | retry_count += 1，重试 |
| subagent 产出格式不对 | 产物文件缺失 | 视同 failed，重试 |
| subagent 产出 VULN 但代码不支持 | 不是本 skill 关心的事 | 不重试 |

## 收集子任务返回

每个 task 返回后，LLM 解析返回内容：
- 成功：从返回中提取产物路径 → 更新 `items[].output`
- 失败：从返回中提取 error → 更新 `items[].error`

## 状态文件原子写

为避免并发写损坏，建议 LLM 在每次更新 state 时：
1. 读整个 state.json
2. 内存中修改
3. 写整个 state.json（覆盖）

由于 LLM 串行处理 task 返回（每次 LLM 响应处理完才进入下一次），实际不存在并发写。如果未来 subagent 改成真正并发，需要加文件锁。
