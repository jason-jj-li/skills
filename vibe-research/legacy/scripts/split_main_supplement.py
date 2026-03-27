#!/usr/bin/env python3
"""
Plan or apply a main-text vs supplement split for technical sections.

Outputs:
- process/main_supplement_split_plan.json
- process/main_supplement_split_plan.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import save_json, split_frontmatter, split_h1_sections, utc_now

TECH_SECTION_HINTS = (
    "technical appendix",
    "reproducibility",
    "verification",
    "data lock",
    "pipeline",
    "implementation details",
    "appendix",
)

def save_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9\-]+", text))

def is_technical_section(title: str, content: str) -> bool:
    t = title.lower().strip()
    if any(h in t for h in TECH_SECTION_HINTS):
        return True
    # high-density technical language trigger
    low = content.lower()
    term_hits = sum(len(re.findall(p, low)) for p in (r"checksum", r"sha256", r"manifest", r"json", r"script", r"workflow", r"pipeline", r"pmid overlap"))
    words = max(1, word_count(content))
    return (term_hits / words) > 0.015 and words > 120

def render_sections(sections: List[Tuple[str, str]]) -> str:
    out = []
    for title, content in sections:
        out.append(f"# {title}\n\n{content.strip()}\n")
    return "\n".join(out).strip() + "\n"

def to_markdown(plan: Dict) -> str:
    lines = [
        "# Main vs Supplement Split Plan",
        "",
        f"- Generated: {plan.get('generated_at', '')}",
        f"- Main-text words: {plan.get('summary', {}).get('main_words', 0)}",
        f"- Supplement words (planned): {plan.get('summary', {}).get('supplement_words', 0)}",
        f"- Technical in main ratio: {plan.get('summary', {}).get('technical_in_main_ratio', 0)}",
        f"- Recommendation: {plan.get('summary', {}).get('recommendation', '')}",
        "",
        "## Move to Supplement",
        "",
    ]
    move = plan.get("sections_move_to_supplement", [])
    if not move:
        lines.append("- None")
    else:
        for s in move:
            lines.append(f"- {s['title']} ({s['words']} words)")

    lines.extend(["", "## Keep in Main Text", ""])
    keep = plan.get("sections_keep_in_main", [])
    for s in keep:
        lines.append(f"- {s['title']} ({s['words']} words)")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Plan/apply main-text vs supplement split.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"), help="Manuscript path")
    parser.add_argument("--supplement", type=Path, default=Path("manuscript/supplement_methods_appendix.qmd"), help="Supplement output path")
    parser.add_argument("--output", type=Path, help="Output JSON path (default: process/main_supplement_split_plan.json)")
    parser.add_argument("--md", type=Path, help="Output markdown path (default: process/main_supplement_split_plan.md)")
    parser.add_argument("--apply", action="store_true", help="Apply split by moving technical sections")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        raise FileNotFoundError(f"Workdir does not exist: {workdir}")

    manuscript = args.manuscript if args.manuscript.is_absolute() else (workdir / args.manuscript)
    supplement = args.supplement if args.supplement.is_absolute() else (workdir / args.supplement)
    if not manuscript.exists():
        raise FileNotFoundError(f"Missing manuscript: {manuscript}")

    text = manuscript.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    sections = split_h1_sections(body)

    keep: List[Tuple[str, str]] = []
    move: List[Tuple[str, str]] = []
    for title, content in sections:
        if is_technical_section(title, content):
            move.append((title, content))
        else:
            keep.append((title, content))

    main_words = sum(word_count(c) for _, c in keep)
    supp_words = sum(word_count(c) for _, c in move)
    total_words = max(1, main_words + supp_words)
    tech_ratio = round(supp_words / total_words, 4)

    recommendation = (
        "Move technical sections to supplement before submission."
        if move
        else "No obvious technical sections detected for splitting."
    )

    plan = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "manuscript": str(manuscript),
        "apply_requested": bool(args.apply),
        "sections_move_to_supplement": [
            {"title": t, "words": word_count(c)} for t, c in move
        ],
        "sections_keep_in_main": [
            {"title": t, "words": word_count(c)} for t, c in keep
        ],
        "summary": {
            "main_words": main_words,
            "supplement_words": supp_words,
            "technical_in_main_ratio": tech_ratio,
            "recommendation": recommendation,
        },
    }

    if args.apply and move:
        # Back up manuscript before overwriting
        backup_path = manuscript.with_suffix(manuscript.suffix + ".bak")
        import shutil
        shutil.copy2(manuscript, backup_path)
        plan["backup_path"] = str(backup_path)

        supplement_text = "# Supplement: Technical Methods and Reproducibility\n\n" + render_sections(move)
        supplement.parent.mkdir(parents=True, exist_ok=True)
        supplement.write_text(supplement_text, encoding="utf-8")

        pointer = "\n# Supplementary Technical Details\n\nDetailed technical methods and reproducibility checks are provided in the supplementary file.\n"
        new_main = (fm + "\n" if fm else "") + render_sections(keep).rstrip() + pointer + "\n"
        manuscript.write_text(new_main, encoding="utf-8")
        plan["applied"] = True
        plan["supplement_path"] = str(supplement)
    else:
        plan["applied"] = False

    output = args.output.resolve() if args.output else (workdir / "process" / "main_supplement_split_plan.json")
    md_out = args.md.resolve() if args.md else (workdir / "process" / "main_supplement_split_plan.md")

    save_json(output, plan)
    save_md(md_out, to_markdown(plan))

    print(f"Split plan written: {output}")
    print(f"Split plan markdown: {md_out}")
    if plan.get("applied"):
        print(f"Applied split. Supplement: {plan.get('supplement_path')}")

if __name__ == "__main__":
    main()
