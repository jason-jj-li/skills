#!/usr/bin/env python3
"""
Evaluate citation architecture for publication-grade manuscripts.

Outputs:
- process/citation_architecture_review.json
- process/citation_architecture_review.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import load_json, save_json, split_frontmatter, split_h1_sections, utc_now

def save_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9\-]+", text))

def citekeys_in_text(text: str) -> List[str]:
    return re.findall(r"@([A-Za-z0-9:_\-]+)", text)

def author_year_citations(text: str) -> List[str]:
    """Detect author-date citations like (Smith et al., 2020) or (Smith, 2020)."""
    return re.findall(
        r"\(([A-Z][A-Za-z]+(?:\s+et\s+al\.?)?,\s*(?:19|20)\d{2}[a-z]?)\)",
        text,
    )

def numeric_bracket_citations(text: str) -> List[str]:
    """Detect numeric bracket citations like [1], [1,2], [1-3]."""
    return re.findall(r"\[(\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*)\]", text)

def detect_citation_style(text: str) -> str:
    """Return dominant citation style: 'citekey', 'author_year', 'numeric', or 'none'."""
    n_citekey = len(citekeys_in_text(text))
    n_author = len(author_year_citations(text))
    n_numeric = len(numeric_bracket_citations(text))
    counts = {"citekey": n_citekey, "author_year": n_author, "numeric": n_numeric}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "none"

def count_unique_citations(text: str, style: str) -> int:
    """Count unique citations for the detected style."""
    if style == "citekey":
        return len(set(citekeys_in_text(text)))
    if style == "author_year":
        return len(set(author_year_citations(text)))
    if style == "numeric":
        nums: set = set()
        for match in numeric_bracket_citations(text):
            for part in re.split(r"[,\-–]", match):
                part = part.strip()
                if part.isdigit():
                    nums.add(int(part))
        return len(nums)
    return 0

def section_unique_citations(text: str, style: str) -> int:
    """Count unique citations in a section text for any detected style."""
    return count_unique_citations(text, style)

def parse_bib_years(bib_text: str) -> Dict[str, int]:
    starts = list(re.finditer(r"@\w+\{([^,]+),", bib_text))
    years: Dict[str, int] = {}
    for i, m in enumerate(starts):
        key = m.group(1).strip()
        start = m.start()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(bib_text)
        chunk = bib_text[start:end]
        ym = re.search(r"\byear\s*=\s*[\{\"]?(\d{4})", chunk, flags=re.I)
        if ym:
            years[key] = int(ym.group(1))
    return years

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
            "unique_citations_min": 35,
            "recent3_share_min": 0.25,
            "recent5_share_min": 0.50,
            "intro_unique_min": 6,
            "discussion_unique_min": 8,
            "citation_density_min": 12.0,
        }
    if qb == "submission":
        return {
            "pass_threshold": 80.0,
            "unique_citations_min": 25,
            "recent3_share_min": 0.18,
            "recent5_share_min": 0.40,
            "intro_unique_min": 4,
            "discussion_unique_min": 5,
            "citation_density_min": 8.0,
        }
    return {
        "pass_threshold": 75.0,
        "unique_citations_min": 18,
        "recent3_share_min": 0.10,
        "recent5_share_min": 0.30,
        "intro_unique_min": 3,
        "discussion_unique_min": 4,
        "citation_density_min": 6.0,
    }

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _extract_author_year_years(text: str) -> List[int]:
    """Extract publication years from author-year citations like (Smith et al., 2023)."""
    matches = re.findall(
        r"\([A-Z][A-Za-z]+(?:\s+et\s+al\.?)?,\s*((?:19|20)\d{2})[a-z]?\)",
        text,
    )
    return [int(y) for y in matches]


def _extract_numeric_years_from_bib(text: str, bib_text: str) -> List[int]:
    """For numeric-bracket style, try to extract years from bib entries."""
    key_year = parse_bib_years(bib_text)
    return list(key_year.values()) if key_year else []


def evaluate(manuscript_text: str, bib_text: str, qb: str) -> Dict:
    _, body = split_frontmatter(manuscript_text)
    sections = split_h1_sections(body)

    style = detect_citation_style(manuscript_text)
    keys = citekeys_in_text(manuscript_text)
    unique_keys = sorted(set(keys))
    unique_count = count_unique_citations(manuscript_text, style)
    key_year = parse_bib_years(bib_text)

    # For non-citekey styles, missing-in-bib check is not applicable
    if style == "citekey":
        missing = sorted([k for k in unique_keys if k not in key_year])
    else:
        missing = []

    # Extract years for recency calculation — strategy depends on citation style
    if style == "citekey":
        valid_years = [key_year[k] for k in unique_keys if k in key_year]
    elif style == "author_year":
        valid_years = _extract_author_year_years(manuscript_text)
    elif style == "numeric":
        valid_years = _extract_numeric_years_from_bib(manuscript_text, bib_text)
    else:
        valid_years = []

    now_year = datetime.now(timezone.utc).year
    recent3 = sum(1 for y in valid_years if y >= now_year - 2)
    recent5 = sum(1 for y in valid_years if y >= now_year - 5)
    n_valid = max(1, len(valid_years)) if valid_years else max(1, unique_count)
    recent3_share = recent3 / n_valid
    recent5_share = recent5 / n_valid

    intro_text = "\n\n".join(t for title, t in sections if "intro" in title.lower())
    discussion_text = "\n\n".join(t for title, t in sections if "discussion" in title.lower())
    results_text = "\n\n".join(t for title, t in sections if "result" in title.lower())

    intro_unique = section_unique_citations(intro_text, style)
    discussion_unique = section_unique_citations(discussion_text, style)
    results_unique = section_unique_citations(results_text, style)

    total_words = max(1, word_count(body))
    citation_density_per_1000 = unique_count / total_words * 1000.0

    th = thresholds_for(qb)

    s_unique = clamp01(unique_count / max(1, th["unique_citations_min"]))
    s_recent3 = clamp01(recent3_share / max(0.001, th["recent3_share_min"]))
    s_recent5 = clamp01(recent5_share / max(0.001, th["recent5_share_min"]))
    s_intro = clamp01(intro_unique / max(1, th["intro_unique_min"]))
    s_disc = clamp01(discussion_unique / max(1, th["discussion_unique_min"]))
    s_density = clamp01(citation_density_per_1000 / max(0.1, th["citation_density_min"]))
    s_missing = 1.0 if not missing else 0.0

    score = 100.0 * (
        0.25 * s_unique
        + 0.15 * s_recent3
        + 0.15 * s_recent5
        + 0.10 * s_intro
        + 0.10 * s_disc
        + 0.10 * s_density
        + 0.15 * s_missing
    )

    checks = [
        {
            "id": "unique_citation_count",
            "pass": unique_count >= th["unique_citations_min"],
            "expected": f">= {th['unique_citations_min']}",
            "actual": unique_count,
        },
        {
            "id": "recent_3y_share",
            "pass": recent3_share >= th["recent3_share_min"],
            "expected": f">= {th['recent3_share_min']:.2f}",
            "actual": round(recent3_share, 4),
        },
        {
            "id": "recent_5y_share",
            "pass": recent5_share >= th["recent5_share_min"],
            "expected": f">= {th['recent5_share_min']:.2f}",
            "actual": round(recent5_share, 4),
        },
        {
            "id": "introduction_citation_coverage",
            "pass": intro_unique >= th["intro_unique_min"],
            "expected": f">= {th['intro_unique_min']}",
            "actual": intro_unique,
        },
        {
            "id": "discussion_citation_coverage",
            "pass": discussion_unique >= th["discussion_unique_min"],
            "expected": f">= {th['discussion_unique_min']}",
            "actual": discussion_unique,
        },
        {
            "id": "citation_density",
            "pass": citation_density_per_1000 >= th["citation_density_min"],
            "expected": f">= {th['citation_density_min']:.1f} per 1000 words",
            "actual": round(citation_density_per_1000, 2),
        },
        {
            "id": "missing_citekeys",
            "pass": len(missing) == 0,
            "expected": "0",
            "actual": len(missing),
        },
    ]

    pass_threshold = th["pass_threshold"]
    # For non-citekey styles, skip missing-key check in verdict
    missing_ok = len(missing) == 0 if style == "citekey" else True
    verdict = "pass" if score >= pass_threshold and missing_ok else "fail"

    return {
        "quality_bar": qb,
        "citation_style": style,
        "thresholds": th,
        "metrics": {
            "unique_citation_count": unique_count,
            "citation_mentions_total": len(keys) if style == "citekey" else unique_count,
            "missing_citekeys": missing,
            "recent_3y_share": round(recent3_share, 4),
            "recent_5y_share": round(recent5_share, 4),
            "introduction_unique_citations": intro_unique,
            "results_unique_citations": results_unique,
            "discussion_unique_citations": discussion_unique,
            "citation_density_per_1000_words": round(citation_density_per_1000, 2),
            "manuscript_word_count": total_words,
        },
        "citation_score": {
            "score_pct": round(score, 1),
            "pass_threshold_score": pass_threshold,
            "verdict": verdict,
        },
        "checks": checks,
    }

def to_markdown(report: Dict) -> str:
    lines = [
        "# Citation Architecture Review",
        "",
        f"- Quality bar: {report.get('quality_bar', 'unknown')}",
        f"- Score: {(report.get('citation_score') or {}).get('score_pct', 0)}",
        f"- Threshold: {(report.get('citation_score') or {}).get('pass_threshold_score', 0)}",
        f"- Verdict: {(report.get('citation_score') or {}).get('verdict', 'unknown')}",
        "",
        "## Checks",
        "",
        "| Check | Pass | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for c in report.get("checks", []):
        lines.append(f"| {c['id']} | {'Yes' if c['pass'] else 'No'} | {c['expected']} | {c['actual']} |")

    missing = (report.get("metrics") or {}).get("missing_citekeys", [])
    if missing:
        lines.extend(["", "## Missing Citekeys", ""])
        for k in missing:
            lines.append(f"- {k}")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate citation architecture for manuscript.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"), help="Manuscript path")
    parser.add_argument("--bib", type=Path, default=Path("process/references.bib"), help="Bib path")
    parser.add_argument("--quality-bar", help="Override quality bar")
    parser.add_argument("--output", type=Path, help="Output JSON path (default: process/citation_architecture_review.json)")
    parser.add_argument("--md", type=Path, help="Output markdown path (default: process/citation_architecture_review.md)")
    parser.add_argument("--no-strict", action="store_true", help="Exit 0 even on failure")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        raise FileNotFoundError(f"Workdir does not exist: {workdir}")

    manuscript = args.manuscript if args.manuscript.is_absolute() else (workdir / args.manuscript)
    bib = args.bib if args.bib.is_absolute() else (workdir / args.bib)
    if not manuscript.exists():
        raise FileNotFoundError(f"Missing manuscript: {manuscript}")
    if not bib.exists():
        raise FileNotFoundError(f"Missing bibliography file: {bib}")

    qb = (args.quality_bar or quality_bar(workdir)).lower().strip()
    report_core = evaluate(manuscript.read_text(encoding="utf-8"), bib.read_text(encoding="utf-8"), qb)
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "manuscript": str(manuscript),
        "bib": str(bib),
        **report_core,
    }

    output = args.output.resolve() if args.output else (workdir / "process" / "citation_architecture_review.json")
    md_out = args.md.resolve() if args.md else (workdir / "process" / "citation_architecture_review.md")
    save_json(output, report)
    save_md(md_out, to_markdown(report))

    verdict = report["citation_score"]["verdict"]
    print(f"Citation architecture verdict: {verdict}")
    print(f"JSON: {output}")
    print(f"MD: {md_out}")

    if verdict != "pass" and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
