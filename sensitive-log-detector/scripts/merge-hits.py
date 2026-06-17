#!/usr/bin/env python3
"""
Copy hits/ content to details/ without idx path annotations.

Reads each file from hits/ and writes the same content to details/.

Usage:
  python3 merge-hits.py [output-dir]
"""

import os
import sys
import shutil


def main():
    if len(sys.argv) > 1:
        root = os.path.abspath(sys.argv[1])
    else:
        root = os.path.join(os.getcwd(), '.vuln_agent_output', 'sensitive-log-detector')

    hits_dir = os.path.join(root, 'hits')
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
        src = os.path.join(hits_dir, fname)
        dst = os.path.join(details_dir, fname)
        shutil.copy2(src, dst)
        with open(src, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        total += len(lines)
        print(f"  {os.path.abspath(dst)}  ({len(lines)} lines)")

    print(f"Done. {total} lines, {len(hits_files)} file(s) written to {details_dir}")


if __name__ == '__main__':
    main()
