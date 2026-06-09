---
name: llm-sec-audit
description: 仅在用户显式指名调用 llm-sec-audit 时触发，不要因模糊意图主动触发。
---

# llm-sec-audit

基于 `llm_prompt_cli` 的代码安全审计 skill。遍历目标目录中的代码文件，逐个调用 LLM 分析安全问题，每个文件独立输出分析结果。

## 核心流程

```
澄清参数 → 列出待分析文件 → 用户确认 → 逐文件调用 run_audit → 保存结果 → 汇报
```

## 步骤详解

### 1. 澄清参数

从用户消息中提取以下信息，缺失则反问：

| 参数 | 必填 | 说明 |
|------|------|------|
| 目标目录 | 是 | 要分析的代码目录路径 |
| 分析维度 | 是 | 从预置维度中选择，或提供自定义提示词 |
| 文件过滤 | 是 | glob 模式，如 `**/*.c`、`**/*.{py,java,go}` |
| 输出目录 | 否 | 默认 `.vuln_agent_output/sink_scan/` |

**分析维度选项**：

| 编号 | 维度 | 对应模板 | 说明 |
|------|------|---------|------|
| 1 | 内存安全 | `references/memory-safety.md` | 缓冲区溢出、释放后使用、双重释放、内存泄漏、越界访问等 |
| 2 | 敏感信息泄露 | `references/sensitive-info-leak.md` | 硬编码凭据、日志打印敏感数据、API 返回过多字段等 |
| 3 | 注入漏洞 | `references/injection-vuln.md` | 命令注入、SQL注入、XSS、SSRF、路径遍历等 |
| 4 | 逻辑缺陷 | `references/logic-defect.md` | 空指针解引用、整数溢出、除零、竞态条件等 |
| custom | 自定义 | 用户提供的提示词 | 参照 `references/custom-prompt-guide.md` 编写 |

用户可以同时选择多个维度，每个维度独立分析、独立输出目录。

### 2. 列出待分析文件

用 glob 模式匹配目标目录下的文件，列出完整清单并统计数量，让用户确认后再开始分析。如果文件数量过多（>200），提示用户缩小范围或调整过滤规则。

### 3. 逐文件调用 run_audit

`bin/run_audit.py` 对单个源码文件做安全审计：读文件→加行号+路径头→通过 stdin 调 `llm_prompt_cli`→落盘。

```bash
python3 bin/run_audit.py \
  --code-file <源码文件路径> \
  --prompt-file <提示词模板路径> \
  --output-dir .vuln_agent_output/sink_scan/<维度名>
```

**串行执行**，一个文件完成后再处理下一个。示例：

```python
import subprocess, pathlib

prompt = "references/memory-safety.md"
out_dir = ".vuln_agent_output/sink_scan/memory-safety"

for f in sorted(pathlib.Path("src").rglob("*.c")):
    subprocess.run([
        "python3", "bin/run_audit.py",
        "--code-file", str(f),
        "--prompt-file", prompt,
        "--output-dir", out_dir,
    ])
```

`--output-dir` 默认 `.vuln_agent_output/sink_scan`，也可指定按维度分目录。每个输出文件保持源码的相对路径结构，如 `src/main.c` → `{output_dir}/src/main.c.txt`。

### 4. 保存结果

输出目录结构：

```
.vuln_agent_output/sink_scan/
├── memory-safety/           ← 按维度分目录
│   ├── src/main.c.txt
│   └── src/utils.c.txt
├── sensitive-info-leak/
│   ├── src/main.c.txt
│   └── src/utils.c.txt
├── injection-vuln/
│   └── ...
├── logic-defect/
│   └── ...
├── custom-<N>/              ← 自定义维度按序编号
│   └── ...
└── errors.log               ← 失败记录
```

每个输出文件保持源码的相对路径结构。例如源文件 `src/main.c` 的分析结果输出到 `<维度目录>/src/main.c.txt`。如果相对路径包含深层目录，先创建对应子目录。

### 5. 错误处理

- 单个文件调用失败时，将错误信息追加到 `errors.log`，继续处理下一个文件
- `errors.log` 格式：`<时间戳> | <文件路径> | <错误信息>`
- 如果所有文件都失败，汇报后停止

### 6. 汇报

分析完成后向用户汇报：

- 分析维度
- 总文件数 / 成功数 / 失败数
- 输出目录路径
- 如有失败，提示查看 `errors.log`
- 列出失败文件清单（如有）

## 提示词模板

预置四种分析维度模板，位于 `references/` 目录。使用时通过 `--prompt-file` 参数传递给 `llm_prompt_cli`。

| 维度 | 模板路径 |
|------|---------|
| 内存安全 | `references/memory-safety.md` |
| 敏感信息泄露 | `references/sensitive-info-leak.md` |
| 注入漏洞 | `references/injection-vuln.md` |
| 逻辑缺陷 | `references/logic-defect.md` |

自定义提示词编写指南：`references/custom-prompt-guide.md`

## 参数澄清示例

用户消息不够明确时，按以下方式反问：

**缺少目标目录**：
> 请指定要分析的代码目录路径。

**缺少分析维度**：
> 请选择分析维度（可多选）：1-内存安全 2-敏感信息泄露 3-注入漏洞 4-逻辑缺陷，或提供自定义提示词。

**缺少文件过滤规则**：
> 请指定要分析的文件类型，如 `**/*.c`、`**/*.{py,java,go}`。

## 原则

- **逐文件串行**：一个文件分析完再处理下一个，不做并发
- **独立输出**：每个源文件的分析结果独立保存，不做汇总合并
- **路径完整**：输出文件保持源码的相对路径结构，便于定位
- **失败不中断**：单个文件失败不影响整体流程，记录错误后继续
- **用户确认后再执行**：列出文件清单让用户确认，避免误扫或浪费 token
- **不修改源码**：本 skill 只读取源文件，不做任何修改
- **输出与源码隔离**：分析结果写到 `.vuln_agent_output/sink_scan/` 目录下，不在源码目录里散落文件
