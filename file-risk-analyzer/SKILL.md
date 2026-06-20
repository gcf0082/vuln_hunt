---
name: file-risk-analyzer
description: "Subagent 用技能：对单个文件进行安全风险分析并定级。只要被分配分析单个文件的风险（审文件、文件级审计、风险定级），无论主流程是 source 分析还是 sink 分析，都要使用本技能。检测命令执行、代码执行、路径拼接文件操作、SQL 拼接、URL 拼接的外部变量注入，以及证书绕过、硬编码凭据、ReDoS、敏感信息日志。"
allowed-tools: Read Grep Glob Bash Write
---

# 文件风险分析 (File Risk Analyzer)

你收到一个文件路径，需要对该文件进行风险分析并定级。

## 输出目录

分析结果写入当前目录下的 `.vuln_agent_output/file_rksk/` 中，按源文件的全路径生成子目录结构：

```
源文件: /opt/myproject/Main.java
输出:   .vuln_agent_output/file_rksk/opt/myproject/Main.java.md
```

**路径解析规则：**
- 若收到的是相对路径，先用 `realpath` 或 `readlink -f` 解析为绝对路径
- 从绝对路径去掉前导 `/`，再追加 `.md` 作为输出文件路径
- 输出路径 = `{CWD}/.vuln_agent_output/file_rksk/{去掉前导/的路径}.md`
- 父目录不存在则自动 `mkdir -p` 创建
- 输出文件已存在则直接覆盖

## 分析流程

### Step 0：确定输出路径

1. 用 `realpath` 或 `readlink -f` 将输入的路径解析为绝对路径（已是则跳过）
2. 构造输出路径：`{CWD}/.vuln_agent_output/file_rksk/{绝对路径去掉前导/}.md`
3. 用 `mkdir -p "$(dirname "$输出路径")"` 创建父目录

### Step 1：读取文件

用 Read 工具读取文件全文，了解文件整体功能。

### Step 2：扫描六类风险

对以下六类风险逐类扫描，每类用 Grep 搜索关键词，然后读取命中行附近的上下文确认。

**关键原则：** 对每个疑似风险点，必须追溯所有涉及的变量来源，确认是外部可控还是内部硬编码。**"外部"指当前文件之外**——函数参数、全局变量、import 的模块变量、网络/DB 读取的值、环境变量、用户输入等都属于外部变量。文件内部字面量/常量定义属于内部变量。

#### ① 命令/代码执行
搜索关键词：`os.system`、`os.popen`、`subprocess`、`exec`、`eval`、`popen`、`Popen`、`run(`、`call(`、`Runtime.exec`、`ProcessBuilder`、`execScript`、`new Function`、`child_process`、`spawn`、`execFile`

#### ② 路径类文件操作
搜索关键词：`open(`、`os.path.join`、`Path(`、`pathlib`、`file_get_contents`、`File.Open`、`file_put_contents`、`fopen`、`fwrite`、`os.remove`、`shutil`、`upload`、`download`、`save`、`read(` 且参数含拼接/插值

#### ③ SQL 拼接
搜索关键词：`SELECT`、`INSERT`、`UPDATE`、`DELETE`、`WHERE` 附近出现字符串拼接 `+`、`f"`、`f'`、`format(`、`%`、`$"`、`$'`、字符串插值，且操作对象是数据库调用（`execute`、`query`、`cursor`、`mysqli_query`、`pg_query`、`raw`、`sql`）

#### ④ URL 拼接
搜索关键词：`requests`、`urllib`、`httpx`、`fetch`、`axios`、`HttpClient`、`URL(` 附近出现字符串拼接/插值

#### ⑤ 直接安全漏洞
- **证书校验绕过：** `verify=False`、`check_hostname=False`、`ssl._create_unverified_context`、`CERT_NONE`
- **硬编码认证凭据：** 变量名含 `password`/`secret`/`token`/`api_key`/`apikey`/`client_secret`/`auth` 且值为字面量字符串
- **ReDoS：** 正则表达式 `re.compile(`/`re.match(`/`re.search(`/`re.sub(` 中模式含有嵌套量词 `(a+)+`、`(a|b)*` 等易导致 catastrophic backtracking 的模式

#### ⑥ 敏感信息日志
搜索关键词：日志输出语句（`logging`、`print`、`logger`、`console.log`、`fmt.Println`、`System.out`）中变量名包含 `password`、`secret`、`token`、`key`、`credential`、`private`、`certificate`、`jwt`、`session`、`credit`、`ssn`、`pwd`

### Step 3：定级

对每个确认的风险点，按以下规则定级：

| 条件 | 评级 |
|---|---|
| ①-④ 类存在**外部变量注入**（变量来自文件之外） | **高** |
| ⑤ 类任意命中 | **高** |
| ⑥ 类任意命中 | **高** |
| ①-④ 类命中但**所有变量均来自文件内部**（硬编码/常量） | **中** |
| ①-④ 类仅定义了字符串/命令模板但**没有任何实际执行/调用** | **信息** |

**优先级规则：** 一个代码片段如果同时命中多条规则，取最高评级。

### Step 4：写入文件

将分析结果写入输出文件。无风险则写入"**该文件未发现风险点。**"

每条风险点使用以下格式：

```
**N. 风险类型 · 行号 X-Y**
**风险评级：** 高/中/信息
**代码片段：**
```language
code here
```
**数据来源：** `变量名` ← 追溯链（外部直连 / 外部间接 / 内部）
```

**字段说明：**
- **风险类型：** 命令注入 / 代码注入 / 路径遍历 / SQL 注入 / URL 注入 / 证书校验绕过 / 硬编码凭据 / ReDoS / 敏感信息泄漏
- **行号：** 风险代码的起始行-结束行
- **评级：** 高 / 中 / 信息
- **代码片段：** 关键代码块（无需整段，突出风险部分即可）
- **数据来源：** 标明每个外部变量的来源类型：
  - `外部直连` — 直接来自用户输入/网络请求/文件上传等（最危险）
  - `外部间接` — 来自函数参数、全局变量、import 模块、环境变量、数据库读取等
  - `内部` — 文件内硬编码字面量或常量

**示例：**
```
**1. 命令注入 · 行号 85-90**
**风险评级：** 高
**代码片段：**
```python
cmd = f"ffmpeg -i {video_path} -vcodec libx265 output.mp4"
os.system(cmd)
```
**数据来源：** `video_path` ← `request.files['video'].filename`（外部直连）
```

写入完成后，在 stdout 输出确认：`分析结果已写入: {输出路径}`

## 纪律

- **不遗漏：** 六类风险都要扫一遍，不要只看命中的就停
- **不猜测：** 追溯变量来源必须以代码行级证据为准，不能凭文件名猜测
- **不重复：** 同一段代码命中多个风险类型时合并为一条输出，评级取最高
- **不输出无关信息：** 只输出风险点列表，不需要额外说明、总结或建议
