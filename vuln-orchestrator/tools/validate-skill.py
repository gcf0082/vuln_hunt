#!/usr/bin/env python3
"""
vuln-orchestrator skill validator.

Checks:
1. SKILL.md exists and has valid YAML frontmatter
2. Frontmatter has required fields: name, description
3. All 5 references files exist
4. All file references in SKILL.md (references/*.md) actually exist on disk
5. Description is non-empty
6. Required sections present in SKILL.md
"""
import sys
import re
import yaml
from pathlib import Path

REQUIRED_REFERENCES = [
    "intent-patterns.md",
    "state-schema.md",
    "stage-contracts.md",
    "dispatch-protocol.md",
    "final-report.md",
]

REQUIRED_SKILL_SECTIONS = [
    "定位",
    "路径约定",
    "预加载",
    "工作流程",
    "状态机",
    "失败处理",
    "原则",
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK:   {msg}")


def main(skill_dir: str = ".") -> int:
    skill_path = Path(skill_dir)
    skill_md = skill_path / "SKILL.md"

    if not skill_md.exists():
        fail(f"SKILL.md not found at {skill_md}")

    content = skill_md.read_text(encoding="utf-8")

    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not m:
        fail("SKILL.md missing YAML frontmatter (--- ... ---)")

    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        fail(f"YAML frontmatter parse error: {e}")

    ok("YAML frontmatter parsed")

    if "name" not in fm:
        fail("frontmatter missing 'name'")
    if "description" not in fm:
        fail("frontmatter missing 'description'")
    if not str(fm["description"]).strip():
        fail("'description' is empty")

    ok(f"frontmatter has name={fm['name']!r} and non-empty description")

    refs_dir = skill_path / "references"
    if not refs_dir.is_dir():
        fail(f"references/ directory not found at {refs_dir}")

    for ref in REQUIRED_REFERENCES:
        p = refs_dir / ref
        if not p.exists():
            fail(f"required reference missing: {p}")
    ok(f"all {len(REQUIRED_REFERENCES)} required references present")

    body = content[m.end():]
    ref_mentions = re.findall(r"`(references/[\w\-./]+\.md)`", body)
    for ref in set(ref_mentions):
        p = skill_path / ref
        if not p.exists():
            fail(f"SKILL.md references {ref} but file not found at {p}")
    ok(f"all {len(set(ref_mentions))} file references in SKILL.md resolve")

    for section in REQUIRED_SKILL_SECTIONS:
        if f"## {section}" not in body:
            fail(f"SKILL.md missing required section: ## {section}")
    ok(f"all {len(REQUIRED_SKILL_SECTIONS)} required sections present")

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    skill_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(skill_dir))
