#!/usr/bin/env python3
"""
Scan code directory for log printing statements (.info/.error/.debug/.warn/.trace),
output flat files without function grouping.

Output structure:
  log_sink/sensitive-logs-NNN.txt     (序号 + 日志内容)
  idx/sensitive-logs-NNN.idx.txt      (序号 + 文件路径:行号)

Usage:
  python3 scan-logs.py <code-dir> [output-dir]
"""

import re
import os
import sys

LOG_RE = re.compile(r'\.(info|error|debug|warn|trace)\(')
SCAN_EXTS = {'.py', '.java', '.kt', '.groovy', '.scala'}
BINARY_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf',
               '.class', '.jar', '.zip', '.tar', '.gz', '.bz2', '.o', '.so',
               '.dll', '.dylib', '.exe', '.bin', '.dat', '.pyc', '.pyo'}
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.svn', 'target',
             'build', 'dist', '.gradle', '.idea', 'venv', '.tox'}


def scan_directory(root):
    entries = []

    for dirpath, _, filenames in os.walk(root):
        parts = set(dirpath.replace('\\', '/').split('/'))
        if parts & SKIP_DIRS:
            continue
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            _, ext = os.path.splitext(fname)
            if ext.lower() not in SCAN_EXTS:
                continue
            if ext.lower() in BINARY_EXTS:
                continue

            relpath = os.path.relpath(fpath, root)
            try:
                with open(fpath, 'r', errors='ignore') as fh:
                    for lineno, raw in enumerate(fh, 1):
                        line = raw.rstrip('\n').rstrip('\r')
                        if LOG_RE.search(line):
                            entries.append((relpath, lineno, line))
            except Exception:
                pass

    return entries


def write_output(entries, output_dir, lines_per_file=100):
    if not entries:
        print("No log statements found.")
        return

    log_sink_dir = os.path.join(output_dir, 'log_sink')
    idx_dir = os.path.join(output_dir, 'idx')
    os.makedirs(log_sink_dir, exist_ok=True)
    os.makedirs(idx_dir, exist_ok=True)

    for batch_idx in range(0, len(entries), lines_per_file):
        batch = entries[batch_idx:batch_idx + lines_per_file]
        part = batch_idx // lines_per_file + 1
        base = f'sensitive-logs-{part:03d}'

        txt_path = os.path.join(log_sink_dir, f'{base}.txt')
        idx_path = os.path.join(idx_dir, f'{base}.idx.txt')

        with open(txt_path, 'w', encoding='utf-8') as ft, \
             open(idx_path, 'w', encoding='utf-8') as fi:
            for offset, (relpath, lineno, line) in enumerate(batch):
                seq = batch_idx + offset + 1
                ft.write(f'{seq}#  {line}\n')
                fi.write(f'{seq}#  {relpath}:{lineno}\n')

    print(f"Done. {len(entries)} log lines written to {output_dir}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    code_dir = os.path.abspath(sys.argv[1])
    if not os.path.isdir(code_dir):
        print(f"Error: not a directory: {code_dir}")
        sys.exit(1)

    output_dir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else \
        os.path.join(os.getcwd(), '.vuln_agent_output', 'sensitive-log-detector')

    print(f"Scanning {code_dir} ...")
    entries = scan_directory(code_dir)
    write_output(entries, output_dir)
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    main()
