#!/usr/bin/env python3
"""
Evaluate whether the manuscript clearly explains where the field stands now.

Outputs:
- process/field_progress_review.json
- process/field_progress_review.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import load_json, save_json, split_frontmatter, split_h1_sections, utc_now

PROGRESS_TERMS = (
    "increasing",
    "decreasing",
    "growth",
    "trend",
    "trajectory",
    "maturing",
    "shift",
    "expanded",
    "limited",
    "plateau",
    "heterogeneity",
    "consistent",
    "mixed",
)

GAP_TERMS = (
    "gap",
    "unknown",
    "uncertain",
    "understudied",
    "unresolved",
    "future research",
    "next question",
    "priority",
)

INTERPRETATION_TERMS = (
    "suggest",
    "indicate",
    "imply",
    "interpret",
    "meaning",
    "clinical",
    "policy",
    "practice",
    "implication",
)

CORE_SECTION_HINTS = (
    "results",
    "discussion",
    "conclusion",
    "research in context",
    "where the field stands",
)

def save_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def paragraphs(text: str) -> List[str]:
    raw = [re.sub(r"\s+", " ", block.strip()) for block in re.split(r"\n\s*\n", text) if block.strip()]
    out: List[str] = []
    for block in raw:
        if block.startswith("#") or block.startswith("|") or block.startswith("!"):
            continue
        if len(re.findall(r"[A-Za-z0-9\-]+", block)) < 14:
            continue
        out.append(block)
    return out

def sentences(text: str) -> List[str]:
    flat = re.sub(r"\s+", " ", text.strip())
    if not flat:
        return []
    chunks = re.split(r"(?<=[.!?])\s+", flat)
    return [c.strip() for c in chunks if len(c.strip()) >= 30]

def has_citation(text: str) -> bool:
    return bool(re.search(r"@[A-Za-z0-9:_\-]+", text))

def has_numeric_anchor(text: str) -> bool:
    return bool(re.search(r"\d", text))

def quality_bar(workdir: Path) -> str:
    contract = workdir / "process" / "project_contract.json"
    if not contract.exists():
        return "submission"
    try:
        payload = load_json(contract)
        return str(((payload.get("intent") or {}).get("quality_bar") or "submission")).lower()
    except Exception:
        return "submission"

def thresholds_for(qb: str) -> Dict[str, float]:
    if qb == "top_tier_submission":
        return {
            "pass_threshold": 85.0,
            "progress_paragraph_ratio_min": 0.45,
            "gap_statement_min": 6,
            "interpretation_sentence_min": 10,
            "core_section_coverage_min": 0.75,
            "field_state_h1_required": 1.0,
        }
    if qb == "submission":
        return {
            "pass_threshold": 80.0,
            "progress_paragraph_ratio_min": 0.35,
            "gap_statement_min": 4,
            "interpretation_sentence_min": 7,
            "core_section_coverage_min": 0.60,
            "field_state_h1_required": 0.0,
        }
    return {
        "pass_threshold": 75.0,
        "progress_paragraph_ratio_min": 0.25,
        "gap_statement_min": 2,
        "interpretation_sentence_min": 4,
        "core_section_coverage_min": 0.45,
        "field_state_h1_required": 0.0,
    }

def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))

def evaluate_text(manuscript: str, qb: str) -> Dict:
    _, body = split_frontmatter(manuscript)
    sections = split_h1_sections(body)
    h1_titles = [title for title, _ in sections]
    h1_titles_low = [title.lower() for title in h1_titles]

    has_research_context_h1 = any(
        "research in context" in title or "current evidence" in title or "state of the field" in title
        for title in h1_titles_low
    )
    has_field_state_h1 = any(
        "where the field stands" in title or "field stands now" in title or "background" in title
        for title in h1_titles_low
    )

    core_sections: List[Tuple[str, str]] = []
    for title, text in sections:
        low = title.lower()
        if any(hint in low for hint in CORE_SECTION_HINTS):
            core_sections.append((title, text))
    if not core_sections:
        core_sections = sections

    core_text = "\n\n".join(text for _, text in core_sections)
    core_paragraphs = paragraphs(core_text)
    core_sentences = sentences(core_text)

    progress_paragraph_hits = 0
    for para in core_paragraphs:
        low = para.lower()
        if any(term in low for term in PROGRESS_TERMS) and (has_citation(para) or has_numeric_anchor(para)):
            progress_paragraph_hits += 1
    progress_para_ratio = progress_paragraph_hits / max(1, len(core_paragraphs))

    gap_sentences = [s for s in core_sentences if any(term in s.lower() for term in GAP_TERMS)]
    interpretation_sentences = [s for s in core_sentences if any(term in s.lower() for term in INTERPRETATION_TERMS)]

    covered_sections = 0
    for _, text in core_sections:
        if has_citation(text) or has_numeric_anchor(text):
            covered_sections += 1
    core_section_coverage = covered_sections / max(1, len(core_sections))

    th = thresholds_for(qb)

    s_structure = 0.0
    s_structure += 0.5 if has_research_context_h1 else 0.0
    if th["field_state_h1_required"] < 0.5:
        s_structure += 0.5
    else:
        s_structure += 0.5 if has_field_state_h1 else 0.0

    s_progress = clamp01(progress_para_ratio / max(0.01, th["progress_paragraph_ratio_min"]))
    s_gap = clamp01(len(gap_sentences) / max(1, th["gap_statement_min"]))
    s_interpretation = clamp01(len(interpretation_sentences) / max(1, th["interpretation_sentence_min"]))
    s_coverage = clamp01(core_section_coverage / max(0.01, th["core_section_coverage_min"]))

    score = 100.0 * (
        0.18 * s_structure
        + 0.28 * s_progress
        + 0.18 * s_gap
        + 0.20 * s_interpretation
        + 0.16 * s_coverage
    )

    checks = [
        {
            "id": "research_in_context_h1_present",
            "pass": has_research_context_h1,
            "expected": "present",
            "actual": "present" if has_research_context_h1 else "missing",
        },
        {
            "id": "field_state_h1_present_when_required",
            "pass": has_field_state_h1 if th["field_state_h1_required"] > 0.5 else True,
            "expected": "present" if th["field_state_h1_required"] > 0.5 else "optional",
            "actual": "present" if has_field_state_h1 else "missing",
        },
        {
            "id": "progress_paragraph_ratio",
            "pass": progress_para_ratio >= th["progress_paragraph_ratio_min"],
            "expected": f">= {th['progress_paragraph_ratio_min']}",
            "actual": round(progress_para_ratio, 4),
        },
        {
            "id": "gap_statements_count",
            "pass": len(gap_sentences) >= th["gap_statement_min"],
            "expected": f">= {th['gap_statement_min']}",
            "actual": len(gap_sentences),
        },
        {
            "id": "interpretation_sentences_count",
            "pass": len(interpretation_sentences) >= th["interpretation_sentence_min"],
            "expected": f">= {th['interpretation_sentence_min']}",
            "actual": len(interpretation_sentences),
        },
        {
            "id": "core_section_evidence_coverage",
            "pass": core_section_coverage >= th["core_section_coverage_min"],
            "expected": f">= {th['core_section_coverage_min']}",
            "actual": round(core_section_coverage, 4),
        },
    ]

    critical_checks = {"progress_paragraph_ratio", "core_section_evidence_coverage"}
    pass_threshold = th["pass_threshold"]
    critical_pass = all(c["pass"] for c in checks if c["id"] in critical_checks)
    verdict = "pass" if score >= pass_threshold and critical_pass else "fail"

    return {
        "quality_bar": qb,
        "thresholds": th,
        "metrics": {
            "h1_order": h1_titles,
            "core_sections": [title for title, _ in core_sections],
            "core_paragraph_count": len(core_paragraphs),
            "progress_paragraph_count": progress_paragraph_hits,
            "progress_paragraph_ratio": round(progress_para_ratio, 4),
            "gap_statement_count": len(gap_sentences),
            "interpretation_sentence_count": len(interpretation_sentences),
            "core_section_coverage_ratio": round(core_section_coverage, 4),
            "has_research_in_context_h1": has_research_context_h1,
            "has_field_state_h1": has_field_state_h1,
        },
        "field_progress_score": {
            "score_pct": round(score, 1),
            "pass_threshold_score": pass_threshold,
            "verdict": verdict,
        },
        "checks": checks,
    }

def to_markdown(report: Dict) -> str:
    lines = [
        "# Field Progress Review",
        "",
        f"- Quality bar: {report.get('quality_bar', 'unknown')}",
        f"- Score: {(report.get('field_progress_score') or {}).get('score_pct', 0)}",
        f"- Threshold: {(report.get('field_progress_score') or {}).get('pass_threshold_score', 0)}",
        f"- Verdict: {(report.get('field_progress_score') or {}).get('verdict', 'unknown')}",
        "",
        "## Checks",
        "",
        "| Check | Pass | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for check in report.get("checks", []):
        lines.append(f"| {check['id']} | {'Yes' if check['pass'] else 'No'} | {check['expected']} | {check['actual']} |")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate whether manuscript explains field progress.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"), help="Manuscript path")
    parser.add_argument("--quality-bar", help="Override quality bar")
    parser.add_argument("--output", type=Path, help="Output JSON path (default: process/field_progress_review.json)")
    parser.add_argument("--md", type=Path, help="Output markdown path (default: process/field_progress_review.md)")
    parser.add_argument("--no-strict", action="store_true", help="Exit 0 even when gate fails")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        raise FileNotFoundError(f"Workdir does not exist: {workdir}")

    manuscript = args.manuscript if args.manuscript.is_absolute() else (workdir / args.manuscript)
    if not manuscript.exists():
        raise FileNotFoundError(f"Missing manuscript: {manuscript}")

    qb = (args.quality_bar or quality_bar(workdir)).lower().strip()
    report_core = evaluate_text(manuscript.read_text(encoding="utf-8"), qb)
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "manuscript": str(manuscript),
        **report_core,
    }

    output = args.output.resolve() if args.output else (workdir / "process" / "field_progress_review.json")
    md_out = args.md.resolve() if args.md else (workdir / "process" / "field_progress_review.md")
    save_json(output, report)
    save_md(md_out, to_markdown(report))

    verdict = (report.get("field_progress_score") or {}).get("verdict", "unknown")
    print(f"Field progress verdict: {verdict}")
    print(f"JSON: {output}")
    print(f"MD: {md_out}")

    if verdict != "pass" and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
