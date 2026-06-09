# llm-sec-audit

基于 `llm_prompt_cli` 的代码安全审计工具。遍历目标目录中的代码文件，逐个调用 LLM 分析安全问题，每个文件独立输出分析结果。

## 安装

```bash
pip install -r tools/llm-sec-audit/requirements.txt
```

## 配置

复制 `.env.example` 为 `.env`，填入 API 信息：

```ini
baseURL=https://ark.cn-beijing.volces.com/api/coding/v3
apiKey=your-api-key
model=deepseek-v4-flash
verifyTLS=false
```

支持 OpenAI 兼容 API，自定义 model、headers、timeout 等参数见 `.env.example`。

## 使用

### 单文件审计

```bash
python3 tools/llm-sec-audit/run_audit.py \
  --code-file src/main.c \
  --prompt-file tools/llm-sec-audit/prompts/injection-vuln.md \
  --output-dir audit_results
```

### 批量审计

```python
import subprocess, pathlib
from pathlib import Path

prompt = "tools/llm-sec-audit/prompts/memory-safety.md"
out_dir = "audit_results/memory-safety"

for f in sorted(Path("src").rglob("*.c")):
    subprocess.run([
        "python3", "tools/llm-sec-audit/run_audit.py",
        "--code-file", str(f),
        "--prompt-file", prompt,
        "--output-dir", out_dir,
    ])
```

### 输出

每个源码文件的审计结果按相对路径镜像落盘：

```
{output-dir}/
├── src/main.c.txt
├── src/utils.c.txt
└── lib/helper.c.txt
```

每条结果带文件路径和行号引用，例如：

```
### 问题 1
- **类型**：缓冲区溢出
- **位置**：第6行 strcpy(buf, input);
- **严重度**：高
- **描述**：buf 为 64 字节，input 来自 argv[1] 未做长度检查
```

## 分析维度

| 维度 | 提示词模板 | 检查范围 |
|------|-----------|---------|
| 内存安全 | `prompts/memory-safety.md` | 缓冲区溢出、UAF、双重释放、内存泄漏、越界访问等 |
| 敏感信息泄露 | `prompts/sensitive-info-leak.md` | 硬编码凭据、日志泄露、错误信息泄露、API 过度暴露等 |
| 注入漏洞 | `prompts/injection-vuln.md` | OS 命令注入、SQL 注入、XSS、SSRF、路径遍历等 |
| 逻辑缺陷 | `prompts/logic-defect.md` | 空指针解引用、整数溢出、除零、竞态条件等 |
| 自定义 | 用户自定 | 参照 `prompts/custom-prompt-guide.md` 编写提示词 |

## 参数

### run_audit.py

| 参数 | 必填 | 说明 |
|------|------|------|
| `--code-file` | 是 | 待审计的源码文件路径 |
| `--prompt-file` | 是 | 分析维度提示词模板路径 |
| `--output-dir` | 否 | 输出目录，默认当前目录 |

### llm_prompt_cli.py（底层工具）

| 参数 | 说明 |
|------|------|
| `--prompt <text>` 或 `--prompt-file <path>` | 提示词（二选一） |
| `--input <text>` / `--input-file <path>` / `--stdin` | 输入（三选一） |
| `--config <path>` | 配置文件路径，默认 `.env` |
| `--prompt-json` | 提示词为 JSON messages 数组 |

## 文件结构

```
tools/llm-sec-audit/
├── run_audit.py             # 二次封装：加行号+路径头 → stdin → 落盘
├── llm_prompt_cli.py        # 底层 LLM 调用工具
├── prompts/                 # 分析维度提示词模板
│   ├── memory-safety.md
│   ├── sensitive-info-leak.md
│   ├── injection-vuln.md
│   ├── logic-defect.md
│   └── custom-prompt-guide.md
├── requirements.txt
├── .env.example
└── README.md
```

## 原理

`run_audit.py` 读取源码文件，添加文件路径头和行号（类似 `cat -n`），通过 stdin 传给 `llm_prompt_cli`，LLM 在分析结果中自然引用文件路径和行号。
