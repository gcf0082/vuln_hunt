#!/usr/bin/env python3
"""
Scan code directory for log printing statements (.info/.error/.debug/.warn/.trace),
group by function name, output to files under .vuln_agent_output/sensitive-log-detector/.

For each function, two files are created per 100 log lines:
  - sensitive-logs-NNN.txt      (序号 + 日志内容)
  - sensitive-logs-NNN.idx.txt  (序号 + 文件路径:行号)

Usage:
  python3 scan-logs.py <code-dir> [output-dir]
"""

import re
import os
import sys
from collections import defaultdict

LOG_RE = re.compile(r'\.(info|error|debug|warn|trace)\(')
SCAN_EXTS = {'.py', '.java', '.kt', '.groovy', '.scala'}

# ── Python function tracking ──────────────────────────────────────────
PY_FUNC_RE = re.compile(r'^\s*(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\(')
PY_CLASS_RE = re.compile(r'^\s*class\s+([a-zA-Z_]\w*)\s*[:\(]')


def _py_track(line, state):
    stripped = line.rstrip()
    if not stripped or stripped.lstrip().startswith('#'):
        return state['current']

    indent = len(line) - len(line.lstrip())

    # Pop closed functions (non-empty, non-comment lines only)
    if stripped:
        while state['func_stack'] and indent <= state['func_stack'][-1][1]:
            state['func_stack'].pop()
        while state['class_stack'] and indent <= state['class_stack'][-1][1]:
            state['class_stack'].pop()

    cm = PY_CLASS_RE.match(line)
    if cm:
        state['class_stack'].append((cm.group(1), indent))
        state['current'] = '__module__'
        return state['current']

    fm = PY_FUNC_RE.match(line)
    if fm:
        prefix = state['class_stack'][-1][0] + '.' if state['class_stack'] else ''
        full = prefix + fm.group(1)
        state['func_stack'].append((full, indent))
        state['current'] = full
        return full

    return state['current']


# ── Java / Kotlin / Groovy / Scala function tracking ──────────────────
# Matches method declarations: optional modifiers + name(params) {
# Avoids matching control flow keywords.
_CTRL = {'if', 'else', 'for', 'while', 'switch', 'try', 'catch', 'finally',
         'synchronized', 'when'}  # 'when' is Kotlin's switch
_JAVA_FUNC_RE = re.compile(
    r'^\s*(?:'                                 # start + optional modifiers
    r'(?:public|private|protected|static|final|abstract|synchronized|native|'
    r'transient|volatile|default|open|override|suspend|inline|operator)\s+)*'
    r'(?:<[^>]+>\s*)?'                         # generic type params (optional)
    r'(?:[A-Za-z_]\w*(?:\[\])*(?:\s*<[^>]+>)?\s+)?'  # return type (optional)
    r'(?:suspend\s+)?'                         # Kotlin suspend
    r'(?:fun\s+)?'                             # Kotlin fun keyword
    r'([a-zA-Z_]\w*)\s*\([^)]*\)\s*'          # name(params)
    r'(?:\{|:\s*)'                             # opening brace or return type
)
_JAVA_CLASS_RE = re.compile(
    r'^\s*(?:public|private|protected|static|abstract|final|open|sealed|data|inner|'
    r'value|object)\s+'
    r'(?:class|interface|enum|object|record|trait)\s+'
    r'([a-zA-Z_]\w*)'
)
# For Scala: object/trait
_JAVA_CLASS_RE2 = re.compile(
    r'^\s*(?:class|interface|enum|object|record|trait)\s+'
    r'([a-zA-Z_]\w*)'
)


def _java_track(line, state):
    stripped = line.strip()
    if not stripped:
        return state['current']

    # Skip comments
    if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
        return state['current']

    cls = None
    m1 = _JAVA_CLASS_RE.match(line)
    if m1:
        cls = m1.group(1)
    else:
        m2 = _JAVA_CLASS_RE2.match(line)
        if m2:
            cls = m2.group(1)
    if cls:
        state['class_stack'].append(cls)
        state['current'] = '__module__'

    # Check for method declaration before counting braces on this line
    func = None
    for brace_pos in [i for i, ch in enumerate(line) if ch == '{']:
        before = line[:brace_pos].strip()
        m = _JAVA_FUNC_RE.match(before + ' {')
        if m and m.group(1) not in _CTRL:
            prefix = state['class_stack'][-1] + '.' if state['class_stack'] else ''
            func = prefix + m.group(1)
            state['func_stack'].append(func)
            state['current'] = func

    # Track brace depth
    for ch in line:
        if ch == '{':
            state['depth'] += 1
        elif ch == '}':
            state['depth'] -= 1

    # Pop functions when depth returns to class level
    # Class body is depth 1, method body is depth 2+
    while state['func_stack'] and state['depth'] <= 1:
        state['func_stack'].pop()
        state['current'] = state['func_stack'][-1] if state['func_stack'] else '__module__'

    # Pop classes when depth returns to 0
    while state['class_stack'] and state['depth'] <= 0:
        state['class_stack'].pop()

    return state['current']


# ── Scanner ───────────────────────────────────────────────────────────

def _new_state():
    return {
        'current': '__module__',
        'func_stack': [],
        'class_stack': [],
        'depth': 0,
    }


def _is_binary(path):
    BINARY_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf',
                   '.class', '.jar', '.zip', '.tar', '.gz', '.bz2', '.o', '.so',
                   '.dll', '.dylib', '.exe', '.bin', '.dat', '.pyc', '.pyo'}
    _, ext = os.path.splitext(path)
    return ext.lower() in BINARY_EXTS


def scan_directory(root):
    log_lines = defaultdict(list)

    for dirpath, _, filenames in os.walk(root):
        # Skip common non-source dirs
        parts = set(dirpath.replace('\\', '/').split('/'))
        if parts & {'.git', '__pycache__', 'node_modules', '.svn', 'target',
                    'build', 'dist', '.gradle', '.idea', 'venv', '.tox'}:
            continue
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            _, ext = os.path.splitext(fname)
            if ext.lower() not in SCAN_EXTS:
                continue
            if _is_binary(fpath):
                continue

            relpath = os.path.relpath(fpath, root)
            lang = 'py' if ext == '.py' else 'java'
            track_fn = _py_track if lang == 'py' else _java_track
            state = _new_state()

            try:
                with open(fpath, 'r', errors='ignore') as fh:
                    for lineno, raw in enumerate(fh, 1):
                        line = raw.rstrip('\n').rstrip('\r')
                        func = track_fn(line, state)
                        if LOG_RE.search(line):
                            log_lines[func].append((relpath, lineno, line))
            except Exception:
                pass  # skip unreadable files

    return log_lines


# ── Output ────────────────────────────────────────────────────────────

def write_output(log_lines, output_dir, lines_per_file=100):
    total_lines = sum(len(v) for v in log_lines.values())
    if total_lines == 0:
        print("No log statements found.")
        return

    # Sort functions by total line count (most first)
    sorted_funcs = sorted(log_lines.items(), key=lambda x: -len(x[1]))

    total_written = 0
    for func, entries in sorted_funcs:
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', func) if func != '__module__' else '__module__'
        func_dir = os.path.join(output_dir, safe_name)
        os.makedirs(func_dir, exist_ok=True)

        for batch_idx in range(0, len(entries), lines_per_file):
            batch = entries[batch_idx:batch_idx + lines_per_file]
            part = batch_idx // lines_per_file + 1

            txt_path = os.path.join(func_dir, f'sensitive-logs-{part:03d}.txt')
            idx_path = os.path.join(func_dir, f'sensitive-logs-{part:03d}.idx.txt')

            with open(txt_path, 'w', encoding='utf-8') as ft, \
                 open(idx_path, 'w', encoding='utf-8') as fi:
                for offset, (relpath, lineno, line) in enumerate(batch):
                    seq = batch_idx + offset + 1
                    ft.write(f'[{seq}]  {line}\n')
                    fi.write(f'[{seq}]  {relpath}:{lineno}\n')

            total_written += len(batch)

    print(f"Done. {total_written} log lines written to {output_dir}")


# ── Main ──────────────────────────────────────────────────────────────

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
    log_lines = scan_directory(code_dir)
    write_output(log_lines, output_dir)
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    main()
