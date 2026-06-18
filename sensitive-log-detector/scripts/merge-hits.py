#!/usr/bin/env python3
"""
Merge all hits/ files into details/, grouped by source file path.

For each source file, shows all its suspicious log lines together.
100 lines per output file (file groups are kept intact).

Usage:
  python3 merge-hits.py [output-dir]
"""

import os
import sys
import re
from collections import OrderedDict

SEQ_RE = re.compile(r'^(\d+)#')
LINES_PER_FILE = 100


def load_index(idx_path):
    index = {}
    if not os.path.exists(idx_path):
        return index
    with open(idx_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = SEQ_RE.match(line)
            if m:
                seq = int(m.group(1))
                rest = line[m.end():].strip()
                index[seq] = rest
    return index


def parse_source(src):
    if ':' in src:
        idx = src.rfind(':')
        filepath = src[:idx]
        lineno = src[idx+1:]
        return filepath, lineno
    return src, '?'


def main():
    if len(sys.argv) > 1:
        root = os.path.abspath(sys.argv[1])
    else:
        root = os.path.join(os.getcwd(), '.vuln_agent_output', 'sensitive-log-detector')

    hits_dir = os.path.join(root, 'hits')
    idx_dir = os.path.join(root, 'idx')
    details_dir = os.path.join(root, 'details')
    os.makedirs(details_dir, exist_ok=True)

    if not os.path.isdir(hits_dir):
        print("No files found in hits/ directory.")
        print(f"  (looked in: {hits_dir})")
        sys.exit(0)

    hits_files = sorted(os.listdir(hits_dir))

    all_entries = []
    for fname in hits_files:
        if not fname.endswith('.txt'):
            continue
        txt_path = os.path.join(hits_dir, fname)
        idx_path = os.path.join(idx_dir, fname.replace('.txt', '.idx.txt'))
        index = load_index(idx_path)
        with open(txt_path, 'r', encoding='utf-8') as fin:
            for line in fin:
                m = SEQ_RE.match(line)
                if not m:
                    continue
                seq = int(m.group(1))
                log_line = line[m.end():].strip()
                src = index.get(seq, ':?')
                filepath, lineno = parse_source(src)
                all_entries.append((filepath, int(lineno) if lineno.isdigit() else 0, seq, log_line))

    if not all_entries:
        print("No entries found in hits/ files.")
        sys.exit(0)

    all_entries.sort(key=lambda x: (x[0], x[1], x[2]))

    groups = OrderedDict()
    for filepath, lineno, seq, log_line in all_entries:
        groups.setdefault(filepath, []).append((lineno, seq, log_line))

    total = 0
    files_written = 0
    current_lines = 0
    out_file = None
    out_path = None
    part = 0

    for filepath, entries in groups.items():
        if out_file is None or current_lines >= LINES_PER_FILE:
            if out_file:
                out_file.close()
            part += 1
            out_path = os.path.join(details_dir, f'sensitive-logs-{part:03d}.txt')
            out_file = open(out_path, 'w', encoding='utf-8')
            current_lines = 0

        out_file.write(f'{filepath}\n')
        current_lines += 1

        for lineno, seq, log_line in entries:
            out_file.write(f'  {lineno}:  {log_line}\n')
            current_lines += 1
            total += 1

        out_file.write('\n')
        current_lines += 1

    if out_file:
        out_file.close()
        files_written = part

    print(f"Done. {total} lines, {files_written} file(s) written to {details_dir}")
    for i in range(1, part + 1):
        fp = os.path.join(details_dir, f'sensitive-logs-{i:03d}.txt')
        print(f"  {os.path.abspath(fp)}")


if __name__ == '__main__':
    main()
