#!/usr/bin/env python3
"""
Merge all hits/ files into details/ with source paths, 100 lines per file.

Reads all hits/*.txt, looks up source paths from idx/, sorts by seq,
and writes to details/sensitive-logs-NNN.txt (100 lines per file).

Usage:
  python3 merge-hits.py [output-dir]
"""

import os
import sys
import re

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
                rest = line[m.end():].strip()
                src = index.get(seq, '(unknown source)')
                all_entries.append((seq, rest, src))

    if not all_entries:
        print("No entries found in hits/ files.")
        sys.exit(0)

    all_entries.sort(key=lambda x: x[0])

    total = 0
    files_written = 0
    for batch_idx in range(0, len(all_entries), LINES_PER_FILE):
        batch = all_entries[batch_idx:batch_idx + LINES_PER_FILE]
        part = batch_idx // LINES_PER_FILE + 1
        out_path = os.path.join(details_dir, f'sensitive-logs-{part:03d}.txt')
        with open(out_path, 'w', encoding='utf-8') as fout:
            for seq, rest, src in batch:
                fout.write(f'{seq}#  {rest}\n')
                fout.write(f'    {src}\n')
        total += len(batch)
        files_written += 1
        print(f"  {os.path.abspath(out_path)}  ({len(batch)} lines)")

    print(f"Done. {total} lines, {files_written} file(s) written to {details_dir}")


if __name__ == '__main__':
    main()
