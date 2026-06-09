#!/usr/bin/env python3
import argparse, pathlib, subprocess, sys

parser = argparse.ArgumentParser()
parser.add_argument("--code-file", required=True)
parser.add_argument("--prompt-file", required=True)
parser.add_argument("--output-dir", default=".")
args = parser.parse_args()

code_path = pathlib.Path(args.code_file).resolve()
prompt_path = pathlib.Path(args.prompt_file).resolve()
cli = pathlib.Path(__file__).parent / "llm_prompt_cli.py"

lines = code_path.read_text(encoding="utf-8").splitlines(keepends=True)
numbered = "".join(f"{i+1:6d}  {l}" for i, l in enumerate(lines))

stdin_input = f"文件路径：{code_path}\n\n{numbered}"

try:
    rel = code_path.relative_to(pathlib.Path.cwd())
except ValueError:
    rel = code_path.name
out = pathlib.Path(args.output_dir) / f"{rel}.txt"

r = subprocess.run(
    [sys.executable, str(cli), "--stdin", "--prompt-file", str(prompt_path)],
    input=stdin_input, capture_output=True, text=True)

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(r.stdout or r.stderr)
sys.exit(r.returncode)
