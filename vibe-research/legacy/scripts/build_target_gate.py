#!/usr/bin/env python3
"""
Build Gate-0 target profile for journal/standards alignment.

Outputs:
- process/target_gate.json
- process/target_gate.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from _common import load_json, save_json, utc_now

JOURNAL_PROFILES = {
    "jama": {
        "style_family": "AMA",
        "structured_abstract": True,
        "provisional_reference_cap": 50,
        "notes": "Confirm article-type-specific limits in official instructions.",
    },
    "the lancet": {
        "style_family": "Vancouver",
        "structured_abstract": True,
        "provisional_reference_cap": 60,
        "notes": "Confirm article-type-specific limits in official instructions.",
    },
    "bmj": {
        "style_family": "Vancouver",
        "structured_abstract": True,
        "provisional_reference_cap": 60,
        "notes": "Confirm article-type-specific limits in official instructions.",
    },
    "nejm": {
        "style_family": "AMA/Vancouver",
        "structured_abstract": True,
        "provisional_reference_cap": 50,
        "notes": "Confirm article-type-specific limits in official instructions.",
    },
    "nature": {
        "style_family": "Nature",
        "structured_abstract": False,
        "provisional_reference_cap": 50,
        "notes": "Confirm article-type-specific limits in official instructions.",
    },
}

REQ_KEYWORDS = (
    "must",
    "required",
    "should",
    "word",
    "reference",
    "citation",
    "figure",
    "table",
    "display",
    "abstract",
    "format",
    "registration",
    "prisma",
    "strobe",
    "consort",
    "moose",
)

def save_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def normalize_journal(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())

def parse_standards_snapshot(path: Path) -> Dict:
    if not path.exists() or path.stat().st_size == 0:
        return {
            "exists": False,
            "urls": [],
            "date_mentions": [],
            "requirements": [],
            "word_limits": [],
            "reference_limits": [],
            "display_item_limits": [],
        }

    text = path.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    urls = sorted(set(re.findall(r"https?://[^\s)]+", text)))
    date_mentions = sorted(
        set(
            re.findall(
                r"(?:\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4})",
                text,
                flags=re.I,
            )
        )
    )

    requirements: List[str] = []
    for ln in lines:
        low = ln.lower()
        if ln.startswith(("-", "*", "□", "1.", "2.", "3.")) and any(k in low for k in REQ_KEYWORDS):
            requirements.append(ln)

    word_limits = sorted(
        set(
            int(x.replace(",", ""))
            for x in re.findall(r"(\d[\d,]{2,})\s*(?:words?|word count|word-limit)", text, flags=re.I)
        )
    )
    reference_limits = sorted(
        set(int(x) for x in re.findall(r"(\d{1,3})\s*(?:references?|citations?)", text, flags=re.I))
    )
    display_item_limits = sorted(
        set(int(x) for x in re.findall(r"(\d{1,2})\s*(?:figures?|tables?|display items?)", text, flags=re.I))
    )

    return {
        "exists": True,
        "urls": urls,
        "date_mentions": date_mentions,
        "requirements": requirements,
        "word_limits": word_limits,
        "reference_limits": reference_limits,
        "display_item_limits": display_item_limits,
    }

def resolve_profile(target_journal: str) -> Dict:
    j = normalize_journal(target_journal)
    for key, profile in JOURNAL_PROFILES.items():
        if key in j:
            return profile
    return {
        "style_family": "journal_default",
        "structured_abstract": True,
        "provisional_reference_cap": None,
        "notes": "Use standards snapshot values as authoritative constraints.",
    }

def gate_status(required: bool, passed: bool) -> str:
    if not required:
        return "not_required"
    return "pass" if passed else "fail"

def build_report(workdir: Path, min_requirements: int) -> Dict:
    contract_path = workdir / "process" / "project_contract.json"
    contract = load_json(contract_path) if contract_path.exists() else {}
    intent = contract.get("intent", {}) if isinstance(contract, dict) else {}

    target_journal = str(intent.get("target_journal", "")).strip()
    reporting_standards = intent.get("reporting_standards", []) or []
    quality_bar = str(intent.get("quality_bar", "")).strip().lower()

    journal_targeted = bool(target_journal) or bool(reporting_standards)

    standards_path = workdir / "process" / "standards_snapshot.md"
    parsed = parse_standards_snapshot(standards_path)

    checks = [
        {
            "id": "standards_snapshot_present",
            "required": journal_targeted,
            "pass": bool(parsed["exists"]),
            "status": gate_status(journal_targeted, bool(parsed["exists"])),
            "details": "process/standards_snapshot.md exists and non-empty.",
        },
        {
            "id": "official_source_links_present",
            "required": journal_targeted,
            "pass": len(parsed["urls"]) > 0,
            "status": gate_status(journal_targeted, len(parsed["urls"]) > 0),
            "details": "At least one official instruction/standard URL captured.",
        },
        {
            "id": "access_date_recorded",
            "required": journal_targeted,
            "pass": len(parsed["date_mentions"]) > 0,
            "status": gate_status(journal_targeted, len(parsed["date_mentions"]) > 0),
            "details": "At least one concrete access date captured.",
        },
        {
            "id": "actionable_requirements_extracted",
            "required": journal_targeted,
            "pass": len(parsed["requirements"]) >= min_requirements,
            "status": gate_status(journal_targeted, len(parsed["requirements"]) >= min_requirements),
            "details": f"At least {min_requirements} actionable requirement lines extracted.",
        },
    ]

    required_checks = [c for c in checks if c["required"]]
    passed_required = [c for c in required_checks if c["pass"]]
    overall_pass = len(required_checks) == len(passed_required)

    profile = resolve_profile(target_journal)

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "intent": {
            "target_journal": target_journal,
            "reporting_standards": reporting_standards,
            "quality_bar": quality_bar,
            "journal_targeted": journal_targeted,
        },
        "journal_profile": profile,
        "standards_snapshot": {
            "path": str(standards_path),
            "exists": parsed["exists"],
            "url_count": len(parsed["urls"]),
            "date_mentions": parsed["date_mentions"],
            "requirements_count": len(parsed["requirements"]),
            "word_limits_detected": parsed["word_limits"],
            "reference_limits_detected": parsed["reference_limits"],
            "display_item_limits_detected": parsed["display_item_limits"],
            "sample_requirements": parsed["requirements"][:8],
        },
        "checks": checks,
        "summary": {
            "required_total": len(required_checks),
            "required_passed": len(passed_required),
            "all_required_passed": overall_pass,
            "verdict": "pass" if (overall_pass or not journal_targeted) else "fail",
        },
    }

def to_markdown(report: Dict) -> str:
    lines = [
        "# Target Gate Report",
        "",
        f"- Generated: {report.get('generated_at', '')}",
        f"- Journal targeted: {report.get('intent', {}).get('journal_targeted')}",
        f"- Target journal: {report.get('intent', {}).get('target_journal') or 'N/A'}",
        f"- Quality bar: {report.get('intent', {}).get('quality_bar') or 'N/A'}",
        f"- Verdict: {report.get('summary', {}).get('verdict', 'unknown')}",
        "",
        "## Checks",
        "",
        "| Check | Required | Status |",
        "|---|---:|---|",
    ]
    for c in report.get("checks", []):
        lines.append(f"| {c['id']} | {str(c['required']).lower()} | {c['status']} |")

    snap = report.get("standards_snapshot", {})
    lines.extend(
        [
            "",
            "## Snapshot Extraction",
            "",
            f"- URL count: {snap.get('url_count', 0)}",
            f"- Requirements extracted: {snap.get('requirements_count', 0)}",
            f"- Word limits detected: {snap.get('word_limits_detected', [])}",
            f"- Reference limits detected: {snap.get('reference_limits_detected', [])}",
            f"- Display item limits detected: {snap.get('display_item_limits_detected', [])}",
        ]
    )
    if snap.get("sample_requirements"):
        lines.extend(["", "## Requirement Samples", ""])
        for item in snap["sample_requirements"]:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Gate-0 target profile and checks.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--output", type=Path, help="Output JSON path (default: process/target_gate.json)")
    parser.add_argument("--md", type=Path, help="Output markdown path (default: process/target_gate.md)")
    parser.add_argument("--min-requirements", type=int, default=3, help="Minimum actionable requirements required")
    parser.add_argument("--no-strict", action="store_true", help="Exit 0 even when required checks fail")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        raise FileNotFoundError(f"Workdir does not exist: {workdir}")

    output = args.output.resolve() if args.output else (workdir / "process" / "target_gate.json")
    md_out = args.md.resolve() if args.md else (workdir / "process" / "target_gate.md")

    report = build_report(workdir, min_requirements=args.min_requirements)
    save_json(output, report)
    save_md(md_out, to_markdown(report))

    verdict = report.get("summary", {}).get("verdict", "unknown")
    print(f"Target gate verdict: {verdict}")
    print(f"JSON: {output}")
    print(f"MD: {md_out}")

    if verdict != "pass" and report.get("intent", {}).get("journal_targeted") and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
