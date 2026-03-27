#!/usr/bin/env python3
"""
Build revision artifacts from review/advisor markdown files.

Outputs:
  - revision_inputs_<n>.json
  - revision_plan_<n>.md
  - reply_to_reviewers_<n>.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, List


KEYWORDS = (
    "concern",
    "issue",
    "major",
    "minor",
    "fix",
    "recommend",
    "should",
    "must",
    "missing",
    "risk",
    "defer",
    "improve",
)


def collect_review_files(workdir: Path, patterns: List[str]) -> List[Path]:
    files: List[Path] = []
    for pattern in patterns:
        files.extend(sorted(workdir.glob(pattern)))
    return [p for p in files if p.is_file()]


def extract_action_lines(path: Path, limit: int = 30) -> List[str]:
    out: List[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if not any(k in low for k in KEYWORDS):
            continue
        if not (line.startswith("-") or line.startswith("*") or line.startswith("#") or ":" in line):
            continue
        out.append(line)
        if len(out) >= limit:
            break
    return out


def make_revision_plan(packet_index: int, extracted: Dict[str, List[str]]) -> str:
    lines = [
        f"# Revision Plan {packet_index}",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Reviewer Summary",
        "",
    ]
    for reviewer, items in extracted.items():
        lines.append(f"### {reviewer}")
        if not items:
            lines.append("- No actionable lines extracted; review manually.")
        else:
            for item in items[:8]:
                lines.append(f"- {item}")
        lines.append("")

    lines.extend(
        [
            "## Workstreams",
            "",
            "1. Methodology fixes",
            "- [ ] TODO",
            "2. Reporting and writing fixes",
            "- [ ] TODO",
            "3. Replication and data provenance fixes",
            "- [ ] TODO",
            "",
            "## Execution Order",
            "",
            "1. Apply high-severity methodology fixes.",
            "2. Re-run analysis and regenerate figures/tables.",
            "3. Update manuscript and reply-to-reviewers.",
            "4. Re-run review gate.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def make_reply_template(packet_index: int, extracted: Dict[str, List[str]]) -> str:
    lines = [
        f"# Reply to Reviewers {packet_index}",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Scope of Revision",
        "",
        "- [TODO] Describe what changed in this revision cycle.",
        "",
    ]
    for reviewer, items in extracted.items():
        lines.append(f"## {reviewer}")
        lines.append("")
        if not items:
            lines.append("- Concern: [TODO]")
            lines.append("- Response: [TODO]")
            lines.append("")
            continue
        for item in items[:6]:
            lines.append(f"- Concern: {item}")
            lines.append("- Response: [TODO]")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build revision plan/reply artifacts from review markdown files.")
    parser.add_argument("workdir", type=Path, help="Paper version directory")
    parser.add_argument("--index", type=int, default=1, help="Revision packet index")
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=["review_*.md", "advisor_*.md", "prose_review_*.md", "exhibit_review_*.md"],
        help="Glob patterns for review input files",
    )
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        print(f"[error] Workdir does not exist: {workdir}")
        raise SystemExit(1)
    files = collect_review_files(workdir, args.patterns)
    if not files:
        print(f"[error] No review files found in {workdir} for patterns: {args.patterns}")
        print("[hint] Ensure review markdown files exist, e.g. review_advisor.md, review_R1.md")
        raise SystemExit(1)

    extracted: Dict[str, List[str]] = {}
    for f in files:
        reviewer = f.stem
        extracted[reviewer] = extract_action_lines(f)

    packet = {
        "schema_version": 1,
        "revision_index": args.index,
        "generated_on": date.today().isoformat(),
        "files": [str(f.relative_to(workdir)) for f in files],
        "extracted": extracted,
    }

    inputs_path = workdir / f"revision_inputs_{args.index}.json"
    plan_path = workdir / f"revision_plan_{args.index}.md"
    reply_path = workdir / f"reply_to_reviewers_{args.index}.md"

    with inputs_path.open("w", encoding="utf-8") as f:
        json.dump(packet, f, ensure_ascii=False, indent=2)
    plan_path.write_text(make_revision_plan(args.index, extracted), encoding="utf-8")
    reply_path.write_text(make_reply_template(args.index, extracted), encoding="utf-8")

    print(f"Generated: {inputs_path}")
    print(f"Generated: {plan_path}")
    print(f"Generated: {reply_path}")


if __name__ == "__main__":
    main()
