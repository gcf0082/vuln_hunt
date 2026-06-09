#!/usr/bin/env python3
import argparse, os, pathlib, subprocess, sys
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--code-file")
parser.add_argument("--stdin-file-list", action="store_true", help="从 stdin 读取文件路径列表（一行一个）")
parser.add_argument("--prompt-file")
parser.add_argument("--prompt")
parser.add_argument("--output-dir", default=".")
parser.add_argument("--thinking", action="store_true", help="显示 LLM 思考过程")
args = parser.parse_args()

if not args.code_file and not args.stdin_file_list:
    parser.error("必须指定 --code-file 或 --stdin-file-list")
if args.code_file and args.stdin_file_list:
    parser.error("--code-file 和 --stdin-file-list 互斥")
if not args.prompt_file and not args.prompt:
    parser.error("必须指定 --prompt-file 或 --prompt")
if args.prompt_file and args.prompt:
    parser.error("--prompt-file 和 --prompt 互斥")

cli = pathlib.Path(__file__).parent / "llm_prompt_cli.py"
prompt_arg = ["--prompt-file", str(pathlib.Path(args.prompt_file).resolve())] if args.prompt_file else ["--prompt", args.prompt]

files = [args.code_file] if args.code_file else [line.strip() for line in sys.stdin if line.strip()]
if not files:
    sys.exit(0)

for f in files:
    code_path = pathlib.Path(f).resolve()
    lines = code_path.read_text(encoding="utf-8").splitlines(keepends=True)
    numbered = "".join(f"{i+1:6d}  {l}" for i, l in enumerate(lines))
    stdin_input = f"文件路径：{code_path}\n\n{numbered}"

    ts = datetime.now().strftime("%m%d-%H%M%S")
    stem = code_path.stem
    suffix = code_path.suffix
    out = pathlib.Path(args.output_dir) / f"{ts}_{code_path.name}.txt"
    n = 2
    while out.exists():
        out = pathlib.Path(args.output_dir) / f"{ts}_{stem}-{n}{suffix}.txt"
        n += 1

    if args.thinking:
        env = os.environ.copy()
        env["showThinking"] = "true"
        env["enableThinking"] = "true"
        r = subprocess.run(
            [sys.executable, str(cli), "--stdin", *prompt_arg],
            input=stdin_input, stdout=subprocess.PIPE, stderr=None, text=True, env=env)
    else:
        r = subprocess.run(
            [sys.executable, str(cli), "--stdin", *prompt_arg],
            input=stdin_input, capture_output=True, text=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"处理文件：{code_path}\n\n{r.stdout or (r.stderr if not args.thinking else '')}")
    print(f"\n处理文件：{code_path}\n")
    print(r.stdout)
    if r.returncode != 0:
        sys.exit(r.returncode)
