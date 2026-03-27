#!/usr/bin/env python3
"""
Build a dynamic, journal-aware writing style gate from project artifacts.

Inputs:
- process/project_contract.json
- process/exemplar_benchmark.json (preferred)
- process/writing_blueprint.json (preferred)
- Optional manuscript path for immediate evaluation.

Outputs:
- process/style_gate_contract.json
- process/style_gate_report.json (if manuscript provided)
- process/style_gate_report.md
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import load_json, save_json, split_sentences, utc_now

DB_TERMS = [
    "PubMed",
    "MEDLINE",
    "Embase",
    "Web of Science",
    "Scopus",
    "PsycINFO",
    "Cochrane",
    "CINAHL",
    "OpenAlex",
]

WEAK_PHRASES = [
    "it is important to note",
    "it should be noted",
    "in conclusion",
    "very",
    "a number of",
]

DISCUSSION_ANCHOR_PATTERNS = [
    r"\b\d+(\.\d+)?%?\b",
    r"\bn\s*=\s*\d+\b",
    r"\b95%\s*CI\b",
    r"\bI\s*2\b",
    r"\bFigure\s+\d+\b",
    r"\bTable\s+\d+\b",
]

def load_json_if_exists(path: Path) -> Dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return load_json(path)
    except Exception:
        return {}

def sentence_lengths(text: str) -> List[int]:
    out = []
    for s in split_sentences(text):
        words = re.findall(r"[A-Za-z0-9\-]+", s)
        if words:
            out.append(len(words))
    return out

def strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)

def block_by_h1(text: str, h1: str) -> str:
    m = re.search(rf"^# {re.escape(h1)}\n(.*?)(?=^# |\Z)", text, flags=re.M | re.S)
    return m.group(1).strip() if m else ""

def block_by_h2(text: str, h2: str) -> str:
    m = re.search(rf"^## {re.escape(h2)}\n(.*?)(?=^## |\n# |\Z)", text, flags=re.M | re.S)
    return m.group(1).strip() if m else ""

def numeric_sentence_density(text: str) -> Tuple[float, int]:
    sents = split_sentences(text)
    if not sents:
        return 0.0, 0
    with_num = sum(1 for s in sents if re.search(r"\d", s))
    return with_num / len(sents), len(sents)

def extract_prose_paragraphs(text: str) -> List[str]:
    text = strip_code_blocks(text)
    parts = re.split(r"\n\s*\n", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        first = p.splitlines()[0].strip()
        if (
            first.startswith("#")
            or first.startswith("![")
            or first.startswith("|")
            or first.startswith("\\begin")
            or first.startswith("\\end")
            or first.startswith("- ")
            or first.startswith("* ")
        ):
            continue
        if re.match(r"^\|?[-: ]+\|[-: |]*$", first):
            continue
        word_n = len(re.findall(r"[A-Za-z0-9\-]+", p))
        if word_n < 10:
            continue
        out.append(re.sub(r"\s+", " ", p))
    return out

def ratio_paragraphs_with_numeric(paragraphs: List[str]) -> float:
    if not paragraphs:
        return 0.0
    hits = sum(1 for p in paragraphs if re.search(r"\d", p))
    return hits / len(paragraphs)

def ratio_discussion_anchor(paragraphs: List[str]) -> float:
    if not paragraphs:
        return 0.0
    reg = re.compile("|".join(DISCUSSION_ANCHOR_PATTERNS), flags=re.I)
    hits = sum(1 for p in paragraphs if reg.search(p))
    return hits / len(paragraphs)

def max_consecutive_same_sentence_starter(text: str) -> int:
    sents = split_sentences(text)
    starters: List[str] = []
    for s in sents:
        words = re.findall(r"[A-Za-z]+", s)
        if len(words) >= 2:
            starters.append(f"{words[0].lower()} {words[1].lower()}")
        elif len(words) == 1:
            starters.append(words[0].lower())
    if not starters:
        return 0
    max_run = 1
    run = 1
    for i in range(1, len(starters)):
        if starters[i] == starters[i - 1]:
            run += 1
            if run > max_run:
                max_run = run
        else:
            run = 1
    return max_run

def exemplar_fingerprint(exemplar_json: Dict) -> Dict:
    exs = exemplar_json.get("exemplars", [])
    findings_density = []
    methods_db_hits = []
    sentence_medians = []
    for ex in exs:
        secs = {x.get("label", "").strip().lower(): x.get("text", "") for x in ex.get("abstract_sections", [])}
        findings = secs.get("findings", "")
        methods = secs.get("methods", "")
        d, n = numeric_sentence_density(findings)
        if n > 0:
            findings_density.append(d)
        methods_db_hits.append(sum(1 for db in DB_TERMS if re.search(rf"\b{re.escape(db)}\b", methods, flags=re.I)))
        lens = sentence_lengths(" ".join(secs.values()))
        if lens:
            sentence_medians.append(statistics.median(lens))

    return {
        "n_exemplars": len(exs),
        "findings_numeric_density_mean": round(statistics.mean(findings_density), 3) if findings_density else 0.0,
        "methods_database_hits_mean": round(statistics.mean(methods_db_hits), 2) if methods_db_hits else 0.0,
        "sentence_median_words_mean": round(statistics.mean(sentence_medians), 2) if sentence_medians else 0.0,
    }

def infer_expected_abstract_template(writing_blueprint: Dict, exemplar_json: Dict) -> List[str]:
    template = (
        (writing_blueprint.get("style_profile") or {}).get("abstract_template")
        or []
    )
    if template:
        return [str(x).strip() for x in template]

    common = ((exemplar_json.get("summary") or {}).get("common_abstract_labels") or [])
    if common:
        return [str(x.get("label", "")).title().strip() for x in common if str(x.get("label", "")).strip()]

    return ["Background", "Methods", "Findings", "Interpretation", "Funding"]

def build_style_gate_contract(
    target_journal: str,
    quality_bar: str,
    expected_abstract: List[str],
    fingerprint: Dict,
    source_files: Dict,
) -> Dict:
    findings_target_min = max(0.45, fingerprint.get("findings_numeric_density_mean", 0.0) - 0.15)
    methods_db_target_min = max(2, int(round(fingerprint.get("methods_database_hits_mean", 0.0) * 0.6)))
    median = float(fingerprint.get("sentence_median_words_mean", 18.0) or 18.0)
    median_low = max(12.0, median - 6.0)
    median_high = median + 8.0
    quality_bar = (quality_bar or "").strip().lower()

    if quality_bar == "top_tier_submission":
        results_para_min = 0.75
        discussion_anchor_min = 0.65
        interpretive_transition_min = 0.50
        max_bullets_narrative = 0
        max_starter_run = 3
        cliche_phrase_max = 2
        citation_mode_required = True
        pass_threshold = 85.0
    elif quality_bar == "submission":
        results_para_min = 0.60
        discussion_anchor_min = 0.50
        interpretive_transition_min = 0.40
        max_bullets_narrative = 1
        max_starter_run = 4
        cliche_phrase_max = 3
        citation_mode_required = True
        pass_threshold = 80.0
    else:
        results_para_min = 0.50
        discussion_anchor_min = 0.40
        interpretive_transition_min = 0.30
        max_bullets_narrative = 2
        max_starter_run = 5
        cliche_phrase_max = 4
        citation_mode_required = False
        pass_threshold = 75.0

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "target_journal": target_journal or "journal_unspecified",
        "quality_bar": quality_bar or "unspecified",
        "source_files": source_files,
        "style_gate": {
            "required_sections": {
                "structured_summary": expected_abstract,
                "research_in_context": [
                    "Evidence before this study",
                    "Added value of this study",
                    "Implications of all the available evidence",
                ],
            },
            "quantitative_targets": {
                "findings_numeric_density_min": round(findings_target_min, 3),
                "methods_database_hits_min": methods_db_target_min,
                "sentence_median_words_range": [round(median_low, 2), round(median_high, 2)],
                "weak_phrase_max": 3,
                "results_paragraph_numeric_ratio_min": round(results_para_min, 2),
                "discussion_paragraph_anchor_ratio_min": round(discussion_anchor_min, 2),
                "max_consecutive_same_sentence_starter": max_starter_run,
            },
            "prose_quality_targets": {
                "pass_threshold_score": pass_threshold,
                "max_bullets_in_narrative_sections": max_bullets_narrative,
                "interpretive_transition_ratio_min": round(interpretive_transition_min, 2),
                "interpretive_anchor_ratio_min": round(discussion_anchor_min, 2),
                "max_consecutive_same_sentence_starter": max_starter_run,
                "cliche_phrase_max": cliche_phrase_max,
                "sentence_median_words_range": [10.0, 35.0],
                "sentence_stdev_min": 3.0,
                "citation_mode_required": citation_mode_required,
            },
            "pass_threshold_score": pass_threshold,
            "weak_phrases": WEAK_PHRASES,
        },
    }

def evaluate_manuscript_style(manuscript_text: str, contract: Dict) -> Dict:
    expected_abstract = (
        ((contract.get("style_gate") or {}).get("required_sections") or {}).get("structured_summary", [])
    )
    expected_ric = (
        ((contract.get("style_gate") or {}).get("required_sections") or {}).get("research_in_context", [])
    )
    targets = (contract.get("style_gate") or {}).get("quantitative_targets", {})
    weak_phrases = (contract.get("style_gate") or {}).get("weak_phrases", WEAK_PHRASES)

    summary_block = block_by_h1(manuscript_text, "Structured summary")
    ric_block = block_by_h1(manuscript_text, "Research in context")
    abstract_order = re.findall(r"^## ([A-Za-z ]+)$", summary_block, flags=re.M)
    ric_order = re.findall(r"^## ([A-Za-z ]+)$", ric_block, flags=re.M)
    findings_block = block_by_h2(summary_block, "Findings")
    methods_block = block_by_h2(summary_block, "Methods")
    results_block = block_by_h1(manuscript_text, "Results")
    discussion_block = block_by_h1(manuscript_text, "Discussion")

    findings_density, findings_n = numeric_sentence_density(findings_block)
    methods_db_hits = sum(1 for db in DB_TERMS if re.search(rf"\b{re.escape(db)}\b", methods_block, flags=re.I))
    lens = sentence_lengths(manuscript_text)
    median_len = statistics.median(lens) if lens else 0.0
    weak_counts = {p: len(re.findall(re.escape(p), manuscript_text.lower())) for p in weak_phrases}
    weak_total = sum(weak_counts.values())
    results_paragraphs = extract_prose_paragraphs(results_block)
    discussion_paragraphs = extract_prose_paragraphs(discussion_block)
    results_para_ratio = ratio_paragraphs_with_numeric(results_paragraphs)
    discussion_anchor_ratio = ratio_discussion_anchor(discussion_paragraphs)
    max_starter_run = max_consecutive_same_sentence_starter(manuscript_text)

    checks = []
    checks.append(
        {
            "name": "Structured abstract order",
            "pass": abstract_order[: len(expected_abstract)] == expected_abstract,
            "expected": expected_abstract,
            "actual": abstract_order[: len(expected_abstract)],
            "weight": 0.13,
        }
    )
    checks.append(
        {
            "name": "Research in context structure",
            "pass": ric_order[: len(expected_ric)] == expected_ric,
            "expected": expected_ric,
            "actual": ric_order[: len(expected_ric)],
            "weight": 0.10,
        }
    )
    checks.append(
        {
            "name": "Findings quantification density",
            "pass": findings_density >= float(targets.get("findings_numeric_density_min", 0.0)),
            "expected_min": float(targets.get("findings_numeric_density_min", 0.0)),
            "actual": round(findings_density, 3),
            "weight": 0.15,
            "supporting_n_sentences": findings_n,
        }
    )
    checks.append(
        {
            "name": "Methods database specificity",
            "pass": methods_db_hits >= int(targets.get("methods_database_hits_min", 1)),
            "expected_min": int(targets.get("methods_database_hits_min", 1)),
            "actual": methods_db_hits,
            "weight": 0.12,
        }
    )
    low, high = targets.get("sentence_median_words_range", [12.0, 28.0])
    checks.append(
        {
            "name": "Sentence-length envelope",
            "pass": float(low) <= median_len <= float(high),
            "expected_range": [float(low), float(high)],
            "actual": round(median_len, 2),
            "weight": 0.08,
        }
    )
    checks.append(
        {
            "name": "Weak-phrase suppression",
            "pass": weak_total <= int(targets.get("weak_phrase_max", 3)),
            "expected_max": int(targets.get("weak_phrase_max", 3)),
            "actual": weak_total,
            "weight": 0.07,
            "breakdown": weak_counts,
        }
    )
    checks.append(
        {
            "name": "Results paragraph evidence density",
            "pass": results_para_ratio >= float(targets.get("results_paragraph_numeric_ratio_min", 0.5)),
            "expected_min": float(targets.get("results_paragraph_numeric_ratio_min", 0.5)),
            "actual": round(results_para_ratio, 3),
            "weight": 0.15,
            "supporting_n_paragraphs": len(results_paragraphs),
        }
    )
    checks.append(
        {
            "name": "Discussion evidence-anchored ratio",
            "pass": discussion_anchor_ratio >= float(targets.get("discussion_paragraph_anchor_ratio_min", 0.4)),
            "expected_min": float(targets.get("discussion_paragraph_anchor_ratio_min", 0.4)),
            "actual": round(discussion_anchor_ratio, 3),
            "weight": 0.10,
            "supporting_n_paragraphs": len(discussion_paragraphs),
        }
    )
    checks.append(
        {
            "name": "Sentence-starter monotony control",
            "pass": max_starter_run <= int(targets.get("max_consecutive_same_sentence_starter", 5)),
            "expected_max": int(targets.get("max_consecutive_same_sentence_starter", 5)),
            "actual": int(max_starter_run),
            "weight": 0.10,
        }
    )

    score = 0.0
    for c in checks:
        if c["pass"]:
            score += c["weight"]
    score_pct = round(score * 100.0, 1)
    threshold = float((contract.get("style_gate") or {}).get("pass_threshold_score", 80.0))
    verdict = "pass" if score_pct >= threshold else "fail"

    return {
        "checks": checks,
        "score_pct": score_pct,
        "pass_threshold_score": threshold,
        "verdict": verdict,
    }

def write_style_md(path: Path, target_journal: str, report: Dict) -> None:
    checks = report.get("style_score", {}).get("checks", [])
    lines = [
        "# Style Gate Report",
        "",
        f"- Target journal: {target_journal or 'journal_unspecified'}",
        f"- Style score: {report['style_score']['score_pct']}/100",
        f"- Threshold: {report['style_score']['pass_threshold_score']}",
        f"- Verdict: {report['style_score']['verdict']}",
        "",
        "## Check Results",
        "",
        "| Check | Pass | Expected | Actual |",
        "|---|---|---|---|",
    ]
    for c in checks:
        if "expected" in c:
            exp = str(c["expected"])
        elif "expected_min" in c:
            exp = f">= {c['expected_min']}"
        elif "expected_range" in c:
            exp = f"{c['expected_range'][0]} to {c['expected_range'][1]}"
        else:
            exp = f"<= {c.get('expected_max', '')}"
        lines.append(f"| {c['name']} | {'Yes' if c['pass'] else 'No'} | {exp} | {c.get('actual')} |")

    failed = [c for c in checks if not c.get("pass")]
    lines.extend(["", "## Required Revisions", ""])
    if not failed:
        lines.append("- No blocking style-gate failures.")
    else:
        for c in failed:
            lines.append(f"- Revise for: {c['name']}.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description="Build dynamic style gate and evaluate manuscript style.")
    parser.add_argument("workdir", help="Project version directory")
    parser.add_argument("--manuscript", default="manuscript/paper.qmd", help="Manuscript path relative to workdir")
    parser.add_argument("--contract-out", default="process/style_gate_contract.json")
    parser.add_argument("--report-out", default="process/style_gate_report.json")
    parser.add_argument("--report-md-out", default="process/style_gate_report.md")
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    process_dir = workdir / "process"
    project_contract_path = process_dir / "project_contract.json"
    exemplar_path = process_dir / "exemplar_benchmark.json"
    writing_blueprint_path = process_dir / "writing_blueprint.json"
    project_contract = load_json_if_exists(project_contract_path)
    exemplar = load_json_if_exists(exemplar_path)
    writing_blueprint = load_json_if_exists(writing_blueprint_path)

    intent = project_contract.get("intent") or {}
    target_journal = str(intent.get("target_journal") or "").strip()
    quality_bar = str(intent.get("quality_bar") or "").strip()
    expected_abstract = infer_expected_abstract_template(writing_blueprint, exemplar)
    fingerprint = exemplar_fingerprint(exemplar)

    contract_payload = build_style_gate_contract(
        target_journal=target_journal,
        quality_bar=quality_bar,
        expected_abstract=expected_abstract,
        fingerprint=fingerprint,
        source_files={
            "project_contract": str(project_contract_path) if project_contract_path.exists() else None,
            "exemplar_benchmark": str(exemplar_path) if exemplar_path.exists() else None,
            "writing_blueprint": str(writing_blueprint_path) if writing_blueprint_path.exists() else None,
        },
    )
    save_json(workdir / args.contract_out, contract_payload)

    manuscript_path = workdir / args.manuscript
    if not manuscript_path.exists():
        print(f"Style gate contract written: {workdir / args.contract_out}")
        print(f"Skipped report: manuscript missing at {manuscript_path}")
        return

    manuscript_text = manuscript_path.read_text(encoding="utf-8")
    style_score = evaluate_manuscript_style(manuscript_text, contract_payload)
    report = {
        "generated_at": utc_now(),
        "target_journal": target_journal or "journal_unspecified",
        "manuscript": str(manuscript_path),
        "style_contract": str(workdir / args.contract_out),
        "style_score": style_score,
    }
    save_json(workdir / args.report_out, report)
    write_style_md(workdir / args.report_md_out, target_journal, report)

    print(f"Style gate contract written: {workdir / args.contract_out}")
    print(f"Style gate report written: {workdir / args.report_out}")
    print(f"Style score: {style_score['score_pct']} ({style_score['verdict']})")

if __name__ == "__main__":
    main()
