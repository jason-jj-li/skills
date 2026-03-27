#!/usr/bin/env python3
"""
Evaluate traceability of quantitative claims to citations.

Outputs:
- process/claim_traceability_review.json
- process/claim_traceability_review.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import load_json, save_json, split_frontmatter, split_h1_sections, utc_now

DIRECTIONAL_TERMS = (
    "increase",
    "decrease",
    "higher",
    "lower",
    "associated",
    "risk",
    "protective",
    "linked",
    "predict",
    "improved",
    "worse",
)

CORE_SECTION_HINTS = (
    "structured summary",
    "research in context",
    "results",
    "discussion",
    "conclusion",
    "where the field stands",
)

def save_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def sentence_split(text: str) -> List[str]:
    flat = re.sub(r"\s+", " ", text.strip())
    if not flat:
        return []
    chunks = re.split(r"(?<=[.!?])\s+", flat)
    out: List[str] = []
    for chunk in chunks:
        s = chunk.strip()
        if len(s) < 25:
            continue
        if s.startswith("|") or s.startswith("!") or s.startswith("#"):
            continue
        out.append(s)
    return out

def has_citation(text: str) -> bool:
    return bool(re.search(r"@[A-Za-z0-9:_\-]+", text))

def is_quantitative_claim(text: str) -> bool:
    low = text.lower()
    if re.search(r"\d", low):
        return True
    patterns = (
        r"\bor\b",
        r"\brr\b",
        r"\bhr\b",
        r"\baor\b",
        r"\bsmd\b",
        r"\bmd\b",
        r"\bci\b",
        r"\bp\s*[<=>]",
    )
    return any(re.search(pattern, low) for pattern in patterns)

def is_directional_claim(text: str) -> bool:
    low = text.lower()
    return any(term in low for term in DIRECTIONAL_TERMS)

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
            "quant_claim_min": 12,
            "traceability_ratio_min": 0.90,
            "uncited_quant_claim_max": 1,
            "uncited_directional_max": 3,
        }
    if qb == "submission":
        return {
            "pass_threshold": 80.0,
            "quant_claim_min": 8,
            "traceability_ratio_min": 0.85,
            "uncited_quant_claim_max": 2,
            "uncited_directional_max": 4,
        }
    return {
        "pass_threshold": 75.0,
        "quant_claim_min": 4,
        "traceability_ratio_min": 0.75,
        "uncited_quant_claim_max": 4,
        "uncited_directional_max": 6,
    }

def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))

def extract_core_text(manuscript: str) -> str:
    _, body = split_frontmatter(manuscript)
    sections = split_h1_sections(body)
    if not sections:
        return body
    selected: List[str] = []
    for title, text in sections:
        low = title.lower()
        if any(hint in low for hint in CORE_SECTION_HINTS):
            selected.append(text)
    return "\n\n".join(selected) if selected else body

def evaluate_text(manuscript: str, qb: str) -> Dict:
    core_text = extract_core_text(manuscript)
    raw_sentences = sentence_split(core_text)
    n = len(raw_sentences)

    quant_indices = [i for i, sentence in enumerate(raw_sentences) if is_quantitative_claim(sentence)]
    cited_quant_indices: List[int] = []
    uncited_quant_indices: List[int] = []

    for idx in quant_indices:
        window_start = max(0, idx - 1)
        window_end = min(n - 1, idx + 1)
        window_has_citation = any(has_citation(raw_sentences[j]) for j in range(window_start, window_end + 1))
        if window_has_citation:
            cited_quant_indices.append(idx)
        else:
            uncited_quant_indices.append(idx)

    directional_uncited_indices = [
        i for i, sentence in enumerate(raw_sentences) if is_directional_claim(sentence) and not has_citation(sentence)
    ]

    quant_count = len(quant_indices)
    cited_quant_count = len(cited_quant_indices)
    uncited_quant_count = len(uncited_quant_indices)
    traceability_ratio = cited_quant_count / max(1, quant_count)

    th = thresholds_for(qb)
    s_volume = clamp01(quant_count / max(1, th["quant_claim_min"]))
    s_traceability = clamp01(traceability_ratio / max(0.01, th["traceability_ratio_min"]))
    s_uncited_quant = clamp01(1 - (uncited_quant_count / max(1, th["uncited_quant_claim_max"] + 1)))
    s_uncited_directional = clamp01(1 - (len(directional_uncited_indices) / max(1, th["uncited_directional_max"] + 1)))

    score = 100.0 * (
        0.20 * s_volume
        + 0.45 * s_traceability
        + 0.25 * s_uncited_quant
        + 0.10 * s_uncited_directional
    )

    checks = [
        {
            "id": "quantitative_claim_volume",
            "pass": quant_count >= th["quant_claim_min"],
            "expected": f">= {th['quant_claim_min']}",
            "actual": quant_count,
        },
        {
            "id": "quantitative_claim_traceability_ratio",
            "pass": traceability_ratio >= th["traceability_ratio_min"],
            "expected": f">= {th['traceability_ratio_min']}",
            "actual": round(traceability_ratio, 4),
        },
        {
            "id": "uncited_quantitative_claim_limit",
            "pass": uncited_quant_count <= th["uncited_quant_claim_max"],
            "expected": f"<= {th['uncited_quant_claim_max']}",
            "actual": uncited_quant_count,
        },
        {
            "id": "uncited_directional_claim_limit",
            "pass": len(directional_uncited_indices) <= th["uncited_directional_max"],
            "expected": f"<= {th['uncited_directional_max']}",
            "actual": len(directional_uncited_indices),
        },
    ]

    critical_checks = {
        "quantitative_claim_traceability_ratio",
        "uncited_quantitative_claim_limit",
    }
    critical_pass = all(check["pass"] for check in checks if check["id"] in critical_checks)
    pass_threshold = th["pass_threshold"]
    verdict = "pass" if score >= pass_threshold and critical_pass else "fail"

    uncited_examples = [raw_sentences[idx] for idx in uncited_quant_indices[:12]]

    return {
        "quality_bar": qb,
        "thresholds": th,
        "metrics": {
            "sentence_count_core": n,
            "quantitative_claim_count": quant_count,
            "cited_quantitative_claim_count": cited_quant_count,
            "uncited_quantitative_claim_count": uncited_quant_count,
            "traceability_ratio": round(traceability_ratio, 4),
            "uncited_directional_claim_count": len(directional_uncited_indices),
            "uncited_quantitative_claim_examples": uncited_examples,
        },
        "traceability_score": {
            "score_pct": round(score, 1),
            "pass_threshold_score": pass_threshold,
            "verdict": verdict,
        },
        "checks": checks,
    }

def to_markdown(report: Dict) -> str:
    lines = [
        "# Claim Traceability Review",
        "",
        f"- Quality bar: {report.get('quality_bar', 'unknown')}",
        f"- Score: {(report.get('traceability_score') or {}).get('score_pct', 0)}",
        f"- Threshold: {(report.get('traceability_score') or {}).get('pass_threshold_score', 0)}",
        f"- Verdict: {(report.get('traceability_score') or {}).get('verdict', 'unknown')}",
        "",
        "## Checks",
        "",
        "| Check | Pass | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for check in report.get("checks", []):
        lines.append(f"| {check['id']} | {'Yes' if check['pass'] else 'No'} | {check['expected']} | {check['actual']} |")

    examples = (report.get("metrics") or {}).get("uncited_quantitative_claim_examples", [])
    if examples:
        lines.extend(["", "## Uncited Quantitative Claims (Examples)", ""])
        for i, sample in enumerate(examples, start=1):
            lines.append(f"{i}. {sample}")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate quantitative-claim citation traceability.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"), help="Manuscript path")
    parser.add_argument("--quality-bar", help="Override quality bar")
    parser.add_argument("--output", type=Path, help="Output JSON path (default: process/claim_traceability_review.json)")
    parser.add_argument("--md", type=Path, help="Output markdown path (default: process/claim_traceability_review.md)")
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

    output = args.output.resolve() if args.output else (workdir / "process" / "claim_traceability_review.json")
    md_out = args.md.resolve() if args.md else (workdir / "process" / "claim_traceability_review.md")
    save_json(output, report)
    save_md(md_out, to_markdown(report))

    verdict = (report.get("traceability_score") or {}).get("verdict", "unknown")
    print(f"Claim traceability verdict: {verdict}")
    print(f"JSON: {output}")
    print(f"MD: {md_out}")

    if verdict != "pass" and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
