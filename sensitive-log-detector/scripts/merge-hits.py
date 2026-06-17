#!/usr/bin/env python3
"""
Merge hits/ with idx/ to produce detailed output with source paths.

For each file in hits/, look up each line's sequence number in the
corresponding idx/ file and produce a combined output in details/.

Usage:
  python3 merge-hits.py [output-dir]
"""

import os
import sys
import re

SEQ_RE = re.compile(r'^(\d+)#')


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


def merge_file(txt_path, idx_path, out_path):
    index = load_index(idx_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    count = 0
    with open(txt_path, 'r', encoding='utf-8') as fin, \
         open(out_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            m = SEQ_RE.match(line)
            if not m:
                continue
            seq = int(m.group(1))
            rest = line[m.end():].strip()
            fout.write(f'{seq}#  {rest}\n')
            if seq in index:
                fout.write(f'    {index[seq]}\n')
            else:
                fout.write(f'    (unknown source)\n')
            count += 1
    return count


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
        hits_files = []
    else:
        hits_files = sorted(os.listdir(hits_dir))

    if not hits_files:
        print("No files found in hits/ directory.")
        print(f"  (looked in: {hits_dir})")
        sys.exit(0)

    total = 0
    for fname in hits_files:
        if not fname.endswith('.txt'):
            continue
        txt_path = os.path.join(hits_dir, fname)
        idx_path = os.path.join(idx_dir, fname.replace('.txt', '.idx.txt'))
        out_path = os.path.join(details_dir, fname)
        cnt = merge_file(txt_path, idx_path, out_path)
        total += cnt
        print(f"  {os.path.abspath(out_path)}  ({cnt} lines)")

    print(f"Done. {total} lines, {len(hits_files)} file(s) written to {details_dir}")


if __name__ == '__main__':
    main()
