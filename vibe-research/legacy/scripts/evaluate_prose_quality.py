#!/usr/bin/env python3
"""
Evaluate manuscript prose quality for journal-targeted vibe-research projects.

Outputs:
- process/prose_quality_review.json
- process/prose_quality_review.md
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from _common import load_json, save_json, split_sentences, utc_now

TRANSITION_TERMS = (
    "however",
    "moreover",
    "furthermore",
    "therefore",
    "consequently",
    "in contrast",
    "by contrast",
    "in addition",
    "in turn",
    "notably",
    "overall",
    "nevertheless",
    "nonetheless",
    "conversely",
    "similarly",
    "accordingly",
    "thus",
    "hence",
    "meanwhile",
    "alternatively",
    "specifically",
    "importantly",
    "in particular",
    "as a result",
    "on the other hand",
    "taken together",
    "collectively",
    "consistent with",
    "in line with",
)

Cliche_PHRASES = (
    "it is worth noting",
    "it should be noted",
    "in conclusion",
    "very",
    "a number of",
    "plays a crucial role",
    "further research is needed",
)

ANCHOR_PATTERNS = (
    r"\b\d+(\.\d+)?%?\b",
    r"\bn\s*=\s*\d+\b",
    r"\b95%\s*CI\b",
    r"\bI\s*2\b",
    r"\bFigure\s+\d+\b",
    r"\bTable\s+\d+\b",
    r"\bPMID\b",
)

NARRATIVE_BULLET_LINE = re.compile(r"^\s*(?:[-*]\s+|\d+\.\s+)")

def save_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)

def block_by_h1(text: str, header: str) -> str:
    m = re.search(rf"^# {re.escape(header)}\n(.*?)(?=^# |\Z)", text, flags=re.M | re.S)
    return m.group(1).strip() if m else ""

def extract_prose_paragraphs(text: str) -> List[str]:
    cleaned = strip_code_blocks(text)
    chunks = re.split(r"\n\s*\n", cleaned)
    out: List[str] = []
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        first = c.splitlines()[0].strip()
        if (
            first.startswith("#")
            or first.startswith("![")
            or first.startswith("|")
            or first.startswith("\\begin")
            or first.startswith("\\end")
            or NARRATIVE_BULLET_LINE.match(first)
        ):
            continue
        if re.match(r"^\|?[-: ]+\|[-: |]*$", first):
            continue
        if len(re.findall(r"[A-Za-z0-9\-]+", c)) < 12:
            continue
        out.append(re.sub(r"\s+", " ", c))
    return out

def count_bullet_lines(text: str) -> int:
    count = 0
    for line in strip_code_blocks(text).splitlines():
        if NARRATIVE_BULLET_LINE.match(line):
            count += 1
    return count

def paragraph_anchor_ratio(paragraphs: List[str]) -> float:
    if not paragraphs:
        return 0.0
    reg = re.compile("|".join(ANCHOR_PATTERNS), flags=re.I)
    anchored = sum(1 for p in paragraphs if reg.search(p))
    return anchored / len(paragraphs)

def paragraph_transition_ratio(paragraphs: List[str]) -> float:
    if not paragraphs:
        return 0.0
    anchored = 0
    for p in paragraphs:
        p_lower = p.lower()
        if any(term in p_lower for term in TRANSITION_TERMS):
            anchored += 1
    return anchored / len(paragraphs)

def sentence_length_stats(text: str) -> Dict:
    lengths: List[int] = []
    for sent in split_sentences(text):
        words = re.findall(r"[A-Za-z0-9\-]+", sent)
        if words:
            lengths.append(len(words))
    if not lengths:
        return {"median": 0.0, "stdev": 0.0, "n_sentences": 0}
    return {
        "median": round(float(statistics.median(lengths)), 2),
        "stdev": round(float(statistics.pstdev(lengths)), 2) if len(lengths) > 1 else 0.0,
        "n_sentences": len(lengths),
    }

def max_consecutive_same_starter(text: str) -> int:
    starters: List[str] = []
    for sent in split_sentences(text):
        words = re.findall(r"[A-Za-z]+", sent)
        if len(words) >= 2:
            starters.append(f"{words[0].lower()} {words[1].lower()}")
        elif words:
            starters.append(words[0].lower())
    if not starters:
        return 0
    max_run = 1
    run = 1
    for idx in range(1, len(starters)):
        if starters[idx] == starters[idx - 1]:
            run += 1
            if run > max_run:
                max_run = run
        else:
            run = 1
    return max_run

def cliche_count(text: str) -> int:
    lower = text.lower()
    return sum(
        len(re.findall(r"\b" + re.escape(p) + r"\b", lower))
        for p in Cliche_PHRASES
    )

def detect_citation_mode(text: str) -> Dict:
    citekeys = set(re.findall(r"@([A-Za-z0-9:_\-]+)", text))
    bracket_num = len(re.findall(r"\[\d{1,3}\]", text))
    author_year = len(re.findall(r"\([A-Z][A-Za-z]+,\s*(?:19|20)\d{2}[a-z]?\)", text))
    modes = []
    if citekeys:
        modes.append("citekey")
    if bracket_num > 0:
        modes.append("numeric_bracket")
    if author_year > 0:
        modes.append("author_year")
    return {
        "modes": modes,
        "n_modes": len(modes),
        "citekeys": sorted(citekeys),
        "has_mixed_styles": len(modes) > 1,
    }

def check_citekeys_in_bib(citekeys: List[str], bib_path: Path) -> Dict:
    if not citekeys:
        return {"checked": False, "missing": [], "details": "No citekeys used in manuscript."}
    if not bib_path.exists():
        return {"checked": True, "missing": list(citekeys), "details": f"Missing bibliography file: {bib_path}"}
    text = bib_path.read_text(encoding="utf-8")
    keys_in_bib = set(re.findall(r"@(?:article|book|misc|inproceedings)\{([^,]+),", text, flags=re.I))
    missing = sorted(k for k in citekeys if k not in keys_in_bib)
    if missing:
        return {"checked": True, "missing": missing, "details": "Some citekeys are not present in references.bib."}
    return {"checked": True, "missing": [], "details": "All citekeys were found in references.bib."}

def default_thresholds(quality: str) -> Dict:
    if quality == "top_tier_submission":
        return {
            "pass_threshold_score": 85.0,
            "max_bullets_in_narrative_sections": 0,
            "interpretive_transition_ratio_min": 0.50,
            "interpretive_anchor_ratio_min": 0.65,
            "max_consecutive_same_sentence_starter": 3,
            "cliche_phrase_max": 2,
            "sentence_median_words_range": [10.0, 35.0],
            "sentence_stdev_min": 3.0,
            "citation_mode_required": True,
        }
    if quality == "submission":
        return {
            "pass_threshold_score": 80.0,
            "max_bullets_in_narrative_sections": 1,
            "interpretive_transition_ratio_min": 0.40,
            "interpretive_anchor_ratio_min": 0.50,
            "max_consecutive_same_sentence_starter": 4,
            "cliche_phrase_max": 3,
            "sentence_median_words_range": [10.0, 35.0],
            "sentence_stdev_min": 3.0,
            "citation_mode_required": True,
        }
    return {
        "pass_threshold_score": 75.0,
        "max_bullets_in_narrative_sections": 2,
        "interpretive_transition_ratio_min": 0.30,
        "interpretive_anchor_ratio_min": 0.40,
        "max_consecutive_same_sentence_starter": 5,
        "cliche_phrase_max": 4,
        "sentence_median_words_range": [10.0, 35.0],
        "sentence_stdev_min": 3.0,
        "citation_mode_required": False,
    }

def resolve_thresholds(workdir: Path, quality: str) -> Dict:
    thresholds = default_thresholds(quality)
    source = "defaults"
    style_contract = workdir / "process" / "style_gate_contract.json"
    if not style_contract.exists():
        thresholds["source"] = source
        return thresholds

    try:
        payload = load_json(style_contract)
        style_gate = payload.get("style_gate", {})
        prose_targets = style_gate.get("prose_quality_targets", {})
        quant_targets = style_gate.get("quantitative_targets", {})

        if isinstance(prose_targets, dict):
            for key in (
                "pass_threshold_score",
                "max_bullets_in_narrative_sections",
                "interpretive_transition_ratio_min",
                "interpretive_anchor_ratio_min",
                "max_consecutive_same_sentence_starter",
                "cliche_phrase_max",
                "sentence_median_words_range",
                "sentence_stdev_min",
                "citation_mode_required",
            ):
                if key in prose_targets:
                    thresholds[key] = prose_targets[key]

        if (
            isinstance(quant_targets, dict)
            and "max_consecutive_same_sentence_starter" in quant_targets
            and "max_consecutive_same_sentence_starter" not in prose_targets
        ):
            thresholds["max_consecutive_same_sentence_starter"] = quant_targets["max_consecutive_same_sentence_starter"]
        source = "style_gate_contract"
    except Exception:
        source = "defaults_fallback_unreadable_style_contract"

    thresholds["source"] = source
    return thresholds

def collect_narrative_paragraphs(sections: List[str]) -> List[str]:
    paragraphs: List[str] = []
    for section in sections:
        paragraphs.extend(extract_prose_paragraphs(section))
    return paragraphs

def evaluate(manuscript_text: str, quality_bar: str, workdir: Path) -> Dict:
    quality = (quality_bar or "").lower().strip()
    thresholds = resolve_thresholds(workdir, quality)
    pass_threshold = float(thresholds["pass_threshold_score"])
    max_bullets = int(thresholds["max_bullets_in_narrative_sections"])
    min_transition_ratio = float(thresholds["interpretive_transition_ratio_min"])
    min_anchor_ratio = float(thresholds["interpretive_anchor_ratio_min"])
    max_starter_run = int(thresholds["max_consecutive_same_sentence_starter"])
    max_cliches = int(thresholds["cliche_phrase_max"])
    sentence_median_range = thresholds.get("sentence_median_words_range", [10.0, 35.0])
    sentence_median_low = float(sentence_median_range[0])
    sentence_median_high = float(sentence_median_range[1])
    sentence_stdev_min = float(thresholds.get("sentence_stdev_min", 3.0))
    citation_mode_required = bool(thresholds.get("citation_mode_required", False))

    intro = block_by_h1(manuscript_text, "Introduction")
    methods = block_by_h1(manuscript_text, "Methods")
    results = block_by_h1(manuscript_text, "Results")
    discussion = block_by_h1(manuscript_text, "Discussion")
    conclusions = block_by_h1(manuscript_text, "Conclusions")
    summary = block_by_h1(manuscript_text, "Structured summary")

    core_missing = [name for name, txt in [
        ("Introduction", intro),
        ("Methods", methods),
        ("Results", results),
        ("Discussion", discussion),
        ("Conclusions", conclusions),
    ] if not txt]

    narrative_text = "\n\n".join([summary, intro, results, discussion, conclusions])
    bullet_lines = count_bullet_lines(narrative_text)
    narrative_paras = collect_narrative_paragraphs([summary, intro, results, discussion, conclusions])
    narrative_body_text = "\n\n".join(narrative_paras)

    discussion_paras = extract_prose_paragraphs(discussion)
    conclusion_paras = extract_prose_paragraphs(conclusions)
    argument_paras = discussion_paras + conclusion_paras
    # Fallback: if discussion+conclusions yield no paragraphs, use all narrative paragraphs
    if not argument_paras:
        argument_paras = narrative_paras
    anchor_ratio = paragraph_anchor_ratio(argument_paras)
    transition_ratio = paragraph_transition_ratio(argument_paras)
    sentence_stats = sentence_length_stats(narrative_body_text)
    starter_run = max_consecutive_same_starter(narrative_body_text)
    cliche_hits = cliche_count(narrative_body_text)

    citation_mode = detect_citation_mode(narrative_body_text)
    citekey_check = check_citekeys_in_bib(citation_mode["citekeys"], workdir / "process" / "references.bib")
    citation_mode_pass = (
        citation_mode["n_modes"] == 1 and not citation_mode["has_mixed_styles"]
        if citation_mode_required
        else not citation_mode["has_mixed_styles"]
    )

    checks = [
        {
            "name": "Core IMRAD section presence",
            "pass": len(core_missing) == 0,
            "expected": "Introduction, Methods, Results, Discussion, Conclusions present",
            "actual": "present" if len(core_missing) == 0 else f"missing: {', '.join(core_missing)}",
            "weight": 0.18,
        },
        {
            "name": "Narrative section bullet leakage",
            "pass": bullet_lines <= max_bullets,
            "expected_max": max_bullets,
            "actual": bullet_lines,
            "weight": 0.12,
        },
        {
            "name": "Interpretive paragraph evidence anchoring",
            "pass": anchor_ratio >= min_anchor_ratio,
            "expected_min": round(min_anchor_ratio, 2),
            "actual": round(anchor_ratio, 3),
            "weight": 0.16,
            "supporting_n_paragraphs": len(argument_paras),
        },
        {
            "name": "Interpretive transition coherence",
            "pass": transition_ratio >= min_transition_ratio,
            "expected_min": round(min_transition_ratio, 2),
            "actual": round(transition_ratio, 3),
            "weight": 0.12,
            "supporting_n_paragraphs": len(argument_paras),
        },
        {
            "name": "Sentence-starter repetition control",
            "pass": starter_run <= max_starter_run,
            "expected_max": max_starter_run,
            "actual": starter_run,
            "weight": 0.10,
        },
        {
            "name": "Cliche suppression",
            "pass": cliche_hits <= max_cliches,
            "expected_max": max_cliches,
            "actual": cliche_hits,
            "weight": 0.10,
        },
        {
            "name": "Sentence-length variability sanity",
            "pass": sentence_median_low <= sentence_stats["median"] <= sentence_median_high and sentence_stats["stdev"] >= sentence_stdev_min,
            "expected": f"median {sentence_median_low}-{sentence_median_high} words and stdev >= {sentence_stdev_min}",
            "actual": f"median={sentence_stats['median']}, stdev={sentence_stats['stdev']}",
            "weight": 0.10,
        },
        {
            "name": "Citation style consistency",
            "pass": citation_mode_pass,
            "expected": "exactly one in-text citation mode" if citation_mode_required else "at most one in-text citation mode",
            "actual": ", ".join(citation_mode["modes"]) if citation_mode["modes"] else "none detected",
            "weight": 0.07,
        },
        {
            "name": "Citekey coverage in bibliography",
            "pass": len(citekey_check["missing"]) == 0,
            "expected": "all citekeys resolve in process/references.bib",
            "actual": "all resolved" if len(citekey_check["missing"]) == 0 else f"missing: {', '.join(citekey_check['missing'])}",
            "weight": 0.05,
        },
    ]

    score = 0.0
    for c in checks:
        if c["pass"]:
            score += c["weight"]
    score_pct = round(score * 100.0, 1)
    verdict = "pass" if score_pct >= pass_threshold else "fail"
    return {
        "checks": checks,
        "score_pct": score_pct,
        "pass_threshold_score": pass_threshold,
        "verdict": verdict,
        "signals": {
            "quality_bar": quality or "unspecified",
            "thresholds_source": thresholds.get("source", "unknown"),
            "core_missing": core_missing,
            "bullet_lines_in_narrative_sections": bullet_lines,
            "narrative_paragraphs": len(narrative_paras),
            "discussion_paragraphs": len(discussion_paras),
            "conclusion_paragraphs": len(conclusion_paras),
            "anchor_ratio": round(anchor_ratio, 3),
            "transition_ratio": round(transition_ratio, 3),
            "sentence_stats": sentence_stats,
            "citation_mode": citation_mode,
            "citekey_check": citekey_check,
        },
    }

def write_review_md(path: Path, report: Dict) -> None:
    score = report["prose_score"]
    checks = score["checks"]
    lines = [
        "# Prose Quality Review",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Target journal: {report['target_journal']}",
        f"- Quality bar: {report['quality_bar']}",
        f"- Manuscript: {report['manuscript']}",
        f"- Prose score: {score['score_pct']}/100",
        f"- Threshold: {score['pass_threshold_score']}",
        f"- Verdict: {score['verdict']}",
        "",
        "## Check Results",
        "",
        "| Check | Pass | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for item in checks:
        if "expected" in item:
            expected = str(item["expected"])
        elif "expected_range" in item:
            expected = f"{item['expected_range'][0]} to {item['expected_range'][1]}"
        elif "expected_min" in item:
            expected = f">= {item['expected_min']}"
        else:
            expected = f"<= {item.get('expected_max', '')}"
        lines.append(
            f"| {item['name']} | {'Yes' if item['pass'] else 'No'} | {expected} | {item.get('actual', '')} |"
        )

    failed = [c for c in checks if not c["pass"]]
    lines.extend(["", "## Required Revisions", ""])
    if not failed:
        lines.append("- No blocking prose quality failures.")
    else:
        for item in failed:
            lines.append(f"- Revise for: {item['name']}.")
    lines.append("")
    save_md(path, "\n".join(lines))

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate manuscript prose quality.")
    parser.add_argument("workdir", type=Path, help="Project version directory")
    parser.add_argument("--manuscript", default="manuscript/paper.qmd", help="Manuscript path relative to workdir")
    parser.add_argument("--output-json", default="process/prose_quality_review.json")
    parser.add_argument("--output-md", default="process/prose_quality_review.md")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    process_dir = workdir / "process"
    contract_path = process_dir / "project_contract.json"
    contract = load_json(contract_path) if contract_path.exists() else {}
    intent = contract.get("intent", {})
    quality_bar = str(intent.get("quality_bar", "")).strip()
    target_journal = str(intent.get("target_journal", "")).strip() or "journal_unspecified"

    manuscript_path = (workdir / args.manuscript).resolve()
    if not manuscript_path.exists():
        raise FileNotFoundError(f"Manuscript not found: {manuscript_path}")

    manuscript_text = manuscript_path.read_text(encoding="utf-8")
    prose_score = evaluate(manuscript_text, quality_bar, workdir)
    report = {
        "generated_at": utc_now(),
        "target_journal": target_journal,
        "quality_bar": quality_bar or "unspecified",
        "manuscript": str(manuscript_path),
        "prose_score": prose_score,
    }
    json_out = (workdir / args.output_json).resolve()
    md_out = (workdir / args.output_md).resolve()
    save_json(json_out, report)
    write_review_md(md_out, report)

    print(f"Prose quality report written: {json_out}")
    print(f"Prose quality markdown written: {md_out}")
    print(f"Prose score: {prose_score['score_pct']} ({prose_score['verdict']})")

if __name__ == "__main__":
    main()
