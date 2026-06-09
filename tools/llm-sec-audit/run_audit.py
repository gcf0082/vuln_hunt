#!/usr/bin/env python3
import argparse, os, pathlib, subprocess, sys

parser = argparse.ArgumentParser()
parser.add_argument("--code-file")
parser.add_argument("--stdin-file-list", action="store_true", help="从 stdin 读取文件路径列表（一行一个）")
parser.add_argument("--prompt-file", required=True)
parser.add_argument("--output-dir", default=".")
parser.add_argument("--thinking", action="store_true", help="显示 LLM 思考过程")
args = parser.parse_args()

if not args.code_file and not args.stdin_file_list:
    parser.error("必须指定 --code-file 或 --stdin-file-list")
if args.code_file and args.stdin_file_list:
    parser.error("--code-file 和 --stdin-file-list 互斥")

prompt_path = pathlib.Path(args.prompt_file).resolve()
cli = pathlib.Path(__file__).parent / "llm_prompt_cli.py"

files = [args.code_file] if args.code_file else [line.strip() for line in sys.stdin if line.strip()]
if not files:
    sys.exit(0)

for f in files:
    code_path = pathlib.Path(f).resolve()
    lines = code_path.read_text(encoding="utf-8").splitlines(keepends=True)
    numbered = "".join(f"{i+1:6d}  {l}" for i, l in enumerate(lines))
    stdin_input = f"文件路径：{code_path}\n\n{numbered}"

    safe_name = str(code_path).replace("/", "_")
    out = pathlib.Path(args.output_dir) / f"{safe_name}.txt"

    if args.thinking:
        env = os.environ.copy()
        env["showThinking"] = "true"
        env["enableThinking"] = "true"
        r = subprocess.run(
            [sys.executable, str(cli), "--stdin", "--prompt-file", str(prompt_path)],
            input=stdin_input, stdout=subprocess.PIPE, stderr=None, text=True, env=env)
    else:
        r = subprocess.run(
            [sys.executable, str(cli), "--stdin", "--prompt-file", str(prompt_path)],
            input=stdin_input, capture_output=True, text=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"处理文件：{code_path}\n\n{r.stdout or (r.stderr if not args.thinking else '')}")
    print(f"\n处理文件：{code_path}\n")
    print(r.stdout)
    if r.returncode != 0:
        sys.exit(r.returncode)
