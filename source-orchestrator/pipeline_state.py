#!/usr/bin/env python3
"""Pipeline state checker — scan .vuln_agent_output/ and determine what needs doing.

Usage:
    python3 pipeline_state.py [work_dir]

Outputs JSON to stdout describing which stages and surfaces are pending.
Key-based matching preserves subdirectory structure (e.g., REST/) across stages.
"""

import json
import os
import re
import sys
from pathlib import Path

OUTPUT_DIR = ".vuln_agent_output"
MARKERS = {
    "collect": ".collect_done",
    "plan": ".plan_done",
}


def norm(path: Path, base: Path) -> str:
    """Return relative path string using forward slashes."""
    return str(path.relative_to(base).as_posix())


def stem_vuln_name(name: str) -> str | None:
    """Extract original surface stem from a vuln finding filename.

    'VULN-xxx-0608-021435-1.md' → 'xxx-0608-021435'
    'NOVULN-xxx.md' → 'xxx'
    Returns None if no prefix matches.
    """
    for prefix in ("VULN-", "NOVULN-", "SUSPECTED-"):
        if name.startswith(prefix):
            remaining = name[len(prefix):]
            m = re.search(r'-\d+$', remaining)
            if m:
                return remaining[:m.start()]
            return remaining
    return None


def scan_risk_kinds(plan_dir: Path) -> set[str]:
    """Return set of risk kinds found in a plan directory."""
    kinds: set[str] = set()
    if not plan_dir.exists():
        return kinds
    for f in plan_dir.iterdir():
        if f.suffix == ".md":
            for kind in ("high", "medium", "low", "none"):
                if f.name.startswith(f"{kind}-risk-"):
                    kinds.add(kind)
    return kinds


def run(work_dir_str: str = ".") -> dict:
    work_dir = Path(work_dir_str).resolve()
    od = work_dir / OUTPUT_DIR

    # ── 1. Stage-level markers ──
    stages = {}
    for stage, marker in MARKERS.items():
        stages[stage] = {"done": (od / marker).exists(), "marker": marker}
    stages["analyze"] = {"done": False}
    stages["vuln"] = {"done": False}
    stages["review"] = {"done": False}

    # ── 2. Base directories ──
    dd = od / "discovered_surfaces"
    ad = od / "analyzed_surfaces"
    pd = od / "vuln_plans"
    vd = od / "vuln_findings"
    rd = od / "vuln_reviews"

    # ── 3. Discovered surfaces ──
    # key = relative path under dd/, without .md (e.g., "REST/iface-REST-a-0608-021435")
    discovered_keys: set[str] = set()
    disc_relmap: dict[str, str] = {}  # key → relative path from od (e.g., "discovered_surfaces/REST/a.md")
    if dd.exists():
        for f in sorted(dd.rglob("*.md")):
            key = norm(f, dd).replace(".md", "")
            discovered_keys.add(key)
            disc_relmap[key] = norm(f, od)

    # ── 4. Analyzed surfaces ──
    analyzed_keys: set[str] = set()
    anl_relmap: dict[str, str] = {}
    if ad.exists():
        for f in sorted(ad.rglob("*.md")):
            key = norm(f, ad).replace(".md", "")
            analyzed_keys.add(key)
            anl_relmap[key] = norm(f, od)

    # ── 5. Planned surfaces ──
    # key = subdirectory name relative to pd/ (e.g., "REST/iface-REST-a-0608-021435")
    planned_keys: set[str] = set()
    plan_kinds: dict[str, set[str]] = {}
    if pd.exists():
        for sub in sorted(pd.rglob("*")):
            if sub.is_dir():
                kinds = scan_risk_kinds(sub)
                if kinds:
                    key = norm(sub, pd)
                    planned_keys.add(key)
                    plan_kinds[key] = kinds

    # ── 6. Vuln finding keys → file paths ──
    # key = subdirectory under vd/ + extracted stem (e.g., "REST/iface-REST-a-0608-021435")
    vuln_keys: set[str] = set()
    vuln_relmap: dict[str, list[str]] = {}  # key → list of relative paths from od
    if vd.exists():
        for f in sorted(vd.rglob("*.md")):
            stem = stem_vuln_name(f.stem)
            if stem:
                sub = norm(f.parent, vd)
                sub = "" if sub == "." else sub
                key = f"{sub}/{stem}" if sub else stem
                vuln_keys.add(key)
                vuln_relmap.setdefault(key, []).append(norm(f, od))

    # ── 7. Review keys (same format as vuln_keys) ──
    review_keys: set[str] = set()
    if rd.exists():
        for f in sorted(rd.rglob("*.md")):
            stem = stem_vuln_name(f.stem)
            if stem:
                sub = norm(f.parent, rd)
                sub = "" if sub == "." else sub
                key = f"{sub}/{stem}" if sub else stem
                review_keys.add(key)

    # ── 8. Pending calculations ──

    # Collect: not done if no marker
    collect_pending = not stages["collect"]["done"]
    only_collect = ["."] if collect_pending else []

    # Analyze: discovered keys not in analyzed keys
    analyze_pending: list[str] = []
    for key in sorted(discovered_keys):
        if key not in analyzed_keys:
            analyze_pending.append(disc_relmap[key])

    # Plan: analyzed keys not in planned keys
    plan_pending: list[str] = []
    for key in sorted(analyzed_keys):
        if key not in planned_keys:
            plan_pending.append(anl_relmap[key])

    # Vuln: analyzed keys that haven't been vuln-analyzed yet.
    # Skip surfaces where ALL plans are none-risk (nothing to analyze).
    vuln_pending: list[str] = []
    for key in sorted(analyzed_keys):
        kinds = plan_kinds.get(key, set())
        if kinds and not (kinds - {"none"}):
            continue
        if key not in vuln_keys:
            vuln_pending.append(anl_relmap[key])

    # Review: vuln keys not in review keys. Return actual vuln finding file paths.
    review_pending: list[str] = []
    for key in sorted(vuln_keys):
        if key not in review_keys:
            review_pending.extend(vuln_relmap.get(key, [f"vuln_findings/{key}"]))

    # ── 9. Stage done determination ──
    stages["collect"]["done"] = stages["collect"]["done"] or (len(discovered_keys) == 0)
    stages["analyze"]["done"] = len(analyze_pending) == 0
    stages["plan"]["done"] = len(plan_pending) == 0
    stages["vuln"]["done"] = len(vuln_pending) == 0
    stages["review"]["done"] = len(review_pending) == 0

    return {
        "work_dir": str(work_dir),
        "stages": stages,
        "counts": {
            "discovered": len(discovered_keys),
            "analyzed": len(analyzed_keys),
            "planned": len(planned_keys),
            "vuln_findings": len(vuln_keys),
            "reviews": len(review_keys),
        },
        "pending": {
            "collect": only_collect,
            "analyze": analyze_pending,
            "plan": plan_pending,
            "vuln": vuln_pending,
            "review": review_pending,
        },
    }


if __name__ == "__main__":
    wd = sys.argv[1] if len(sys.argv) > 1 else "."
    data = run(wd)
    print(json.dumps(data, indent=2, ensure_ascii=False))
