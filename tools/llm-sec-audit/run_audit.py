#!/usr/bin/env python3
import argparse, os, pathlib, subprocess, sys

parser = argparse.ArgumentParser()
parser.add_argument("--code-file", required=True)
parser.add_argument("--prompt-file", required=True)
parser.add_argument("--output-dir", default=".")
parser.add_argument("--thinking", action="store_true", help="显示 LLM 思考过程")
args = parser.parse_args()

code_path = pathlib.Path(args.code_file).resolve()
prompt_path = pathlib.Path(args.prompt_file).resolve()
cli = pathlib.Path(__file__).parent / "llm_prompt_cli.py"

lines = code_path.read_text(encoding="utf-8").splitlines(keepends=True)
numbered = "".join(f"{i+1:6d}  {l}" for i, l in enumerate(lines))

stdin_input = f"文件路径：{code_path}\n\n{numbered}"

safe_name = str(code_path).replace("/", "_")
out = pathlib.Path(args.output_dir) / f"{safe_name}.txt"

if args.thinking:
    env = os.environ.copy()
    env["showThinking"] = "true"
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
sys.exit(r.returncode)
