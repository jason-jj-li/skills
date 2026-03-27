#!/usr/bin/env python3
"""
Evaluate whether manuscript is content-first (not process-report-first).

Outputs:
- process/content_focus_review.json
- process/content_focus_review.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import load_json, save_json, split_frontmatter, split_h1_sections, utc_now

IMPLICATION_TERMS = (
    "implication",
    "implications",
    "policy",
    "practice",
    "decision",
    "translation",
    "priority",
    "next step",
    "strategy",
    "recommend",
)

TECHNICAL_TERMS = (
    "checksum",
    "sha256",
    "pipeline",
    "artifact",
    "manifest",
    "json",
    "script",
    "workflow",
    "rerun",
    "lock",
    "versioned workspace",
)

def save_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9\-]+", text))

def paragraphs(text: str) -> List[str]:
    chunks = [re.sub(r"\s+", " ", c.strip()) for c in re.split(r"\n\s*\n", text) if c.strip()]
    out: List[str] = []
    for c in chunks:
        if c.startswith("!") or c.startswith("|") or c.startswith("#"):
            continue
        if len(re.findall(r"[A-Za-z0-9\-]+", c)) < 12:
            continue
        out.append(c)
    return out

def numeric_para_ratio(text: str) -> float:
    paras = paragraphs(text)
    if not paras:
        return 0.0
    hits = sum(1 for p in paras if re.search(r"\d", p))
    return hits / len(paras)

def implication_para_ratio(text: str) -> float:
    paras = paragraphs(text)
    if not paras:
        return 0.0
    hits = 0
    for p in paras:
        low = p.lower()
        if any(t in low for t in IMPLICATION_TERMS):
            hits += 1
    return hits / len(paras)

def technical_term_ratio(text: str) -> float:
    words = max(1, word_count(text))
    low = text.lower()
    hits = 0
    for t in TECHNICAL_TERMS:
        hits += len(re.findall(re.escape(t), low))
    return hits / words

def quality_bar(workdir: Path) -> str:
    c = workdir / "process" / "project_contract.json"
    if not c.exists():
        return "submission"
    try:
        obj = load_json(c)
        return str(((obj.get("intent") or {}).get("quality_bar") or "submission")).lower()
    except Exception:
        return "submission"

def thresholds_for(qb: str) -> Dict[str, float]:
    if qb == "top_tier_submission":
        return {
            "pass_threshold": 85.0,
            "methods_ratio_max": 0.22,
            "narrative_ratio_min": 0.55,
            "results_numeric_ratio_min": 0.75,
            "discussion_implication_ratio_min": 0.40,
            "technical_ratio_max": 0.015,
            "frontload_required": 1.0,
        }
    if qb == "submission":
        return {
            "pass_threshold": 80.0,
            "methods_ratio_max": 0.28,
            "narrative_ratio_min": 0.50,
            "results_numeric_ratio_min": 0.60,
            "discussion_implication_ratio_min": 0.30,
            "technical_ratio_max": 0.020,
            "frontload_required": 0.0,
        }
    return {
        "pass_threshold": 75.0,
        "methods_ratio_max": 0.33,
        "narrative_ratio_min": 0.45,
        "results_numeric_ratio_min": 0.50,
        "discussion_implication_ratio_min": 0.25,
        "technical_ratio_max": 0.025,
        "frontload_required": 0.0,
    }

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def evaluate_text(manuscript: str, qb: str) -> Dict:
    _, body = split_frontmatter(manuscript)
    sections = split_h1_sections(body)
    sec_map = {title.lower(): text for title, text in sections}

    total_words = max(1, word_count(body))
    methods_words = sum(word_count(t) for title, t in sections if "method" in title.lower())
    narrative_words = sum(
        word_count(t)
        for title, t in sections
        if any(k in title.lower() for k in ("introduction", "results", "discussion", "conclusion", "where the field"))
    )

    methods_ratio = methods_words / total_words
    narrative_ratio = narrative_words / total_words

    results_text = "\n\n".join(t for title, t in sections if "result" in title.lower())
    discussion_text = "\n\n".join(t for title, t in sections if "discussion" in title.lower())

    results_ratio = numeric_para_ratio(results_text)
    discussion_ratio = implication_para_ratio(discussion_text)

    non_methods_text = "\n\n".join(t for title, t in sections if "method" not in title.lower())
    tech_ratio = technical_term_ratio(non_methods_text)

    h1_titles = [title.lower() for title, _ in sections]
    # Accept equivalent frontloading H1 names (not just Lancet-specific wording)
    frontload_variants = (
        "where the field stands now",
        "where the field stands",
        "research in context",
        "background",
        "state of the field",
        "current evidence",
    )
    frontload = 1.0 if any(any(v in h for v in frontload_variants) for h in h1_titles[:4]) else 0.0

    th = thresholds_for(qb)

    s_methods = clamp01(1 - max(0.0, methods_ratio - th["methods_ratio_max"]) / max(0.01, th["methods_ratio_max"]))
    s_narrative = clamp01(narrative_ratio / max(0.01, th["narrative_ratio_min"]))
    s_results = clamp01(results_ratio / max(0.01, th["results_numeric_ratio_min"]))
    s_disc = clamp01(discussion_ratio / max(0.01, th["discussion_implication_ratio_min"]))
    s_tech = clamp01(1 - max(0.0, tech_ratio - th["technical_ratio_max"]) / max(0.001, th["technical_ratio_max"]))
    s_frontload = 1.0 if th["frontload_required"] < 0.5 else frontload

    score = 100.0 * (
        0.22 * s_methods
        + 0.18 * s_narrative
        + 0.20 * s_results
        + 0.18 * s_disc
        + 0.12 * s_tech
        + 0.10 * s_frontload
    )

    checks = [
        {
            "id": "methods_ratio_within_limit",
            "pass": methods_ratio <= th["methods_ratio_max"],
            "actual": round(methods_ratio, 4),
            "expected": f"<= {th['methods_ratio_max']}",
        },
        {
            "id": "narrative_word_share_sufficient",
            "pass": narrative_ratio >= th["narrative_ratio_min"],
            "actual": round(narrative_ratio, 4),
            "expected": f">= {th['narrative_ratio_min']}",
        },
        {
            "id": "results_numeric_density",
            "pass": results_ratio >= th["results_numeric_ratio_min"],
            "actual": round(results_ratio, 4),
            "expected": f">= {th['results_numeric_ratio_min']}",
        },
        {
            "id": "discussion_implication_density",
            "pass": discussion_ratio >= th["discussion_implication_ratio_min"],
            "actual": round(discussion_ratio, 4),
            "expected": f">= {th['discussion_implication_ratio_min']}",
        },
        {
            "id": "technical_term_overflow_control",
            "pass": tech_ratio <= th["technical_ratio_max"],
            "actual": round(tech_ratio, 6),
            "expected": f"<= {th['technical_ratio_max']}",
        },
        {
            "id": "frontloaded_field_state_section",
            "pass": bool(frontload) if th["frontload_required"] > 0.5 else True,
            "actual": int(frontload),
            "expected": "present in first 4 H1 sections" if th["frontload_required"] > 0.5 else "optional",
        },
    ]

    pass_threshold = th["pass_threshold"]
    verdict = "pass" if score >= pass_threshold and all(c["pass"] for c in checks if c["id"] != "frontloaded_field_state_section" or th["frontload_required"] > 0.5) else "fail"

    return {
        "quality_bar": qb,
        "thresholds": th,
        "metrics": {
            "total_words": total_words,
            "methods_words": methods_words,
            "methods_word_ratio": round(methods_ratio, 4),
            "narrative_word_ratio": round(narrative_ratio, 4),
            "results_numeric_paragraph_ratio": round(results_ratio, 4),
            "discussion_implication_paragraph_ratio": round(discussion_ratio, 4),
            "technical_term_ratio_outside_methods": round(tech_ratio, 6),
            "frontload_field_state": bool(frontload),
            "h1_order": [title for title, _ in sections],
        },
        "content_score": {
            "score_pct": round(score, 1),
            "pass_threshold_score": pass_threshold,
            "verdict": verdict,
        },
        "checks": checks,
    }

def to_markdown(report: Dict) -> str:
    lines = [
        "# Content Focus Review",
        "",
        f"- Quality bar: {report.get('quality_bar', 'unknown')}",
        f"- Score: {(report.get('content_score') or {}).get('score_pct', 0)}",
        f"- Threshold: {(report.get('content_score') or {}).get('pass_threshold_score', 0)}",
        f"- Verdict: {(report.get('content_score') or {}).get('verdict', 'unknown')}",
        "",
        "## Checks",
        "",
        "| Check | Pass | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for c in report.get("checks", []):
        lines.append(f"| {c['id']} | {'Yes' if c['pass'] else 'No'} | {c['expected']} | {c['actual']} |")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate whether manuscript is content-first.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"), help="Manuscript path (relative to workdir if not absolute)")
    parser.add_argument("--output", type=Path, help="Output JSON path (default: process/content_focus_review.json)")
    parser.add_argument("--md", type=Path, help="Output markdown path (default: process/content_focus_review.md)")
    parser.add_argument("--quality-bar", help="Override quality bar")
    parser.add_argument("--no-strict", action="store_true", help="Exit 0 even when gate fails")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        raise FileNotFoundError(f"Workdir does not exist: {workdir}")

    manuscript = args.manuscript if args.manuscript.is_absolute() else (workdir / args.manuscript)
    if not manuscript.exists():
        raise FileNotFoundError(f"Missing manuscript: {manuscript}")

    output = args.output.resolve() if args.output else (workdir / "process" / "content_focus_review.json")
    md_out = args.md.resolve() if args.md else (workdir / "process" / "content_focus_review.md")

    text = manuscript.read_text(encoding="utf-8")
    qb = (args.quality_bar or quality_bar(workdir)).lower().strip()

    core = evaluate_text(text, qb)
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "manuscript": str(manuscript),
        **core,
    }

    save_json(output, report)
    save_md(md_out, to_markdown(report))

    verdict = report["content_score"]["verdict"]
    print(f"Content focus verdict: {verdict}")
    print(f"JSON: {output}")
    print(f"MD: {md_out}")

    if verdict != "pass" and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
