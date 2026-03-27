#!/usr/bin/env python3
"""
Run triad review (Editor, Methods, Domain) from gate artifacts.

Outputs:
- process/triad_review.json
- process/triad_review.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from _common import load_json, save_json, utc_now

GRADE_BANDS = [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")]

def save_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def read_score(path: Path, block: str) -> Optional[float]:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        payload = load_json(path)
    except Exception:
        return None
    section = payload.get(block, {})
    if isinstance(section, dict) and "score_pct" in section:
        try:
            return float(section["score_pct"])
        except Exception:
            return None
    if block == "style_score":
        style = payload.get("style_score", {})
        if isinstance(style, dict) and "score_pct" in style:
            try:
                return float(style["score_pct"])
            except Exception:
                return None
    return None

def quality_bar(workdir: Path) -> str:
    path = workdir / "process" / "project_contract.json"
    if not path.exists():
        return "submission"
    try:
        obj = load_json(path)
        return str(((obj.get("intent") or {}).get("quality_bar") or "submission")).lower()
    except Exception:
        return "submission"

def grade(score: float) -> str:
    for cut, g in GRADE_BANDS:
        if score >= cut:
            return g
    return "F"

def weighted_mean(parts: List[tuple[Optional[float], float]], fallback: float = 0.0) -> float:
    num = 0.0
    den = 0.0
    for s, w in parts:
        if s is None:
            continue
        num += s * w
        den += w
    if den <= 0:
        return fallback
    return num / den

def evaluate(workdir: Path) -> Dict:
    prose_score = read_score(workdir / "process" / "prose_quality_review.json", "prose_score")
    style_score = read_score(workdir / "process" / "style_gate_report.json", "style_score")
    content_score = read_score(workdir / "process" / "content_focus_review.json", "content_score")
    field_score = read_score(workdir / "process" / "field_progress_review.json", "field_progress_score")
    citation_score = read_score(workdir / "process" / "citation_architecture_review.json", "citation_score")
    traceability_score = read_score(workdir / "process" / "claim_traceability_review.json", "traceability_score")

    # Optional novelty/feasibility signal.
    novelty_score: Optional[float] = None
    feasibility = workdir / "process" / "feasibility_report.json"
    if feasibility.exists() and feasibility.stat().st_size > 0:
        try:
            fea = load_json(feasibility)
            selected = fea.get("selected") or {}
            if isinstance(selected, dict):
                n = selected.get("novelty_score")
                if n is not None:
                    novelty_score = float(n) * 100.0
        except Exception:
            novelty_score = None

    editor_score = weighted_mean(
        [
            (prose_score, 0.35),
            (content_score, 0.20),
            (field_score, 0.25),
            (style_score, 0.20),
        ],
        fallback=0.0,
    )
    methods_score = weighted_mean(
        [
            (style_score, 0.30),
            (content_score, 0.20),
            (citation_score, 0.20),
            (traceability_score, 0.30),
        ],
        fallback=0.0,
    )
    domain_score = weighted_mean(
        [
            (citation_score, 0.35),
            (field_score, 0.25),
            (traceability_score, 0.25),
            (novelty_score, 0.15),
        ],
        fallback=0.0,
    )

    overall = weighted_mean(
        [
            (editor_score, 0.34),
            (methods_score, 0.33),
            (domain_score, 0.33),
        ],
        fallback=0.0,
    )

    qb = quality_bar(workdir)
    if qb == "top_tier_submission":
        bar = 85.0
    elif qb == "submission":
        bar = 80.0
    else:
        bar = 75.0

    panel = {
        "editor": round(editor_score, 1),
        "methods_reviewer": round(methods_score, 1),
        "domain_reviewer": round(domain_score, 1),
    }

    open_actions: List[str] = []
    if prose_score is None:
        open_actions.append("Run prose-quality gate to supply editor evidence.")
    if style_score is None:
        open_actions.append("Run style gate evaluation to supply methods evidence.")
    if content_score is None:
        open_actions.append("Run content-focus gate to verify content-first narrative.")
    if field_score is None:
        open_actions.append("Run field-progress gate to verify the manuscript explains where the field stands now.")
    if citation_score is None:
        open_actions.append("Run citation-architecture gate to verify evidence density and recency.")
    if traceability_score is None:
        open_actions.append("Run claim-traceability gate to verify quantitative claims are citation-anchored.")

    for role, score in panel.items():
        if score < bar:
            open_actions.append(f"Improve {role} score from {score} to >= {bar}.")

    verdict = "pass" if all(v >= bar for v in panel.values()) and overall >= bar else "fail"

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "quality_bar": qb,
        "threshold_score": bar,
        "inputs": {
            "prose_score": prose_score,
            "style_score": style_score,
            "content_score": content_score,
            "field_progress_score": field_score,
            "citation_score": citation_score,
            "traceability_score": traceability_score,
            "novelty_score": novelty_score,
        },
        "panel_scores": panel,
        "overall": {
            "score_pct": round(overall, 1),
            "grade": grade(overall),
            "verdict": verdict,
        },
        "open_actions": open_actions,
    }

def to_markdown(report: Dict) -> str:
    lines = [
        "# Triad Review",
        "",
        f"- Quality bar: {report.get('quality_bar', 'unknown')}",
        f"- Threshold: {report.get('threshold_score', 0)}",
        f"- Overall: {(report.get('overall') or {}).get('score_pct', 0)} ({(report.get('overall') or {}).get('grade', 'N/A')})",
        f"- Verdict: {(report.get('overall') or {}).get('verdict', 'unknown')}",
        "",
        "## Panel Scores",
        "",
        "| Reviewer | Score |",
        "|---|---:|",
    ]
    for role, score in (report.get("panel_scores") or {}).items():
        lines.append(f"| {role} | {score} |")

    actions = report.get("open_actions") or []
    lines.extend(["", "## Open Actions", ""])
    if not actions:
        lines.append("- None")
    else:
        for item in actions:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Run triad review from existing gate reports.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--output", type=Path, help="Output JSON path (default: process/triad_review.json)")
    parser.add_argument("--md", type=Path, help="Output markdown path (default: process/triad_review.md)")
    parser.add_argument("--no-strict", action="store_true", help="Exit 0 even when triad review fails")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        raise FileNotFoundError(f"Workdir does not exist: {workdir}")

    report = evaluate(workdir)
    output = args.output.resolve() if args.output else (workdir / "process" / "triad_review.json")
    md_out = args.md.resolve() if args.md else (workdir / "process" / "triad_review.md")

    save_json(output, report)
    save_md(md_out, to_markdown(report))

    verdict = (report.get("overall") or {}).get("verdict", "unknown")
    print(f"Triad review verdict: {verdict}")
    print(f"JSON: {output}")
    print(f"MD: {md_out}")

    if verdict != "pass" and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
