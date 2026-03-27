#!/usr/bin/env python3
"""
Run a multi-round writing superloop for submission-grade manuscripts.

This script operationalizes a critic-fixer-style convergence loop:
round N -> run writing gates -> collect failed checks -> [auto-fix if enabled] -> emit revision tasks -> repeat.

With --auto-fix, the superloop applies rule-based mechanical fixes (cliché removal,
sentence-starter diversification, bullet-to-prose, transition insertion, section
scaffolding) between rounds, then generates an LLM revision prompt for remaining items.

Outputs:
- process/writing_superloop_report.json
- process/writing_superloop_report.md
- process/writing_superloop/round_XX/*
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import TOP_TIER_HINTS, bool_policy, infer_journal_target, infer_submission_like, infer_top_tier_target, load_json, save_json, utc_now



def save_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def run_cmd(cmd: List[str]) -> None:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)

def resolve_gate_policy(contract: Dict, force_triad: bool = False) -> Dict[str, bool]:
    journal_target = infer_journal_target(contract)
    top_tier_target = infer_top_tier_target(contract)
    submission_like = infer_submission_like(contract)
    policy = contract.get("gate_policy", {}) if isinstance(contract, dict) else {}
    if not isinstance(policy, dict):
        policy = {}
    triad_required = bool_policy(policy, "triad_review_required", top_tier_target)
    if force_triad:
        triad_required = True
    return {
        "journal_target": journal_target,
        "top_tier_target": top_tier_target,
        "submission_like": submission_like,
        "content_focus_gate_required": bool_policy(policy, "content_focus_gate_required", submission_like),
        "citation_architecture_gate_required": bool_policy(policy, "citation_architecture_gate_required", submission_like),
        "field_progress_gate_required": bool_policy(policy, "field_progress_gate_required", submission_like),
        "claim_traceability_gate_required": bool_policy(policy, "claim_traceability_gate_required", submission_like),
        "main_supplement_split_required": bool_policy(policy, "main_supplement_split_required", submission_like),
        "triad_review_required": triad_required,
    }

def quality_bar(workdir: Path) -> str:
    path = workdir / "process" / "project_contract.json"
    if not path.exists():
        return "submission"
    try:
        payload = load_json(path)
        return str(((payload.get("intent") or {}).get("quality_bar") or "submission")).lower()
    except Exception:
        return "submission"

def default_rounds_from_quality_bar(qb: str) -> int:
    if qb == "top_tier_submission":
        return 5
    if qb == "submission":
        return 3
    return 2

def read_score_verdict(path: Path, block: str) -> Dict:
    if not path.exists() or path.stat().st_size == 0:
        return {
            "status": "missing",
            "verdict": "missing",
            "score_pct": None,
            "pass_threshold_score": None,
            "error": f"Missing report: {path}",
        }
    try:
        payload = load_json(path)
    except Exception as exc:
        return {
            "status": "invalid",
            "verdict": "invalid",
            "score_pct": None,
            "pass_threshold_score": None,
            "error": f"Unreadable JSON: {exc}",
        }
    score_block = payload.get(block, {})
    if not isinstance(score_block, dict):
        return {
            "status": "invalid",
            "verdict": "invalid",
            "score_pct": None,
            "pass_threshold_score": None,
            "error": f"Missing score block `{block}`",
        }
    return {
        "status": "ok",
        "verdict": str(score_block.get("verdict", "invalid")).lower(),
        "score_pct": score_block.get("score_pct"),
        "pass_threshold_score": score_block.get("pass_threshold_score"),
        "error": "",
    }

def build_failed_items(
    gate_name: str,
    report_path: Path,
    check_key: str,
    label_key: str,
) -> List[Dict]:
    if not report_path.exists() or report_path.stat().st_size == 0:
        return [{
            "gate": gate_name,
            "severity": "critical",
            "check": "report_presence",
            "expected": "gate report exists and is non-empty",
            "actual": "missing",
            "source": str(report_path),
        }]
    try:
        payload = load_json(report_path)
    except Exception as exc:
        return [{
            "gate": gate_name,
            "severity": "critical",
            "check": "report_readability",
            "expected": "valid JSON report",
            "actual": f"unreadable ({exc})",
            "source": str(report_path),
        }]

    items: List[Dict] = []
    for check in payload.get(check_key, []):
        if bool(check.get("pass")):
            continue
        expected = (
            check.get("expected")
            if "expected" in check
            else (
                f">= {check.get('expected_min')}"
                if "expected_min" in check
                else (
                    f"<= {check.get('expected_max')}"
                    if "expected_max" in check
                    else str(check.get("expected_range", "n/a"))
                )
            )
        )
        items.append(
            {
                "gate": gate_name,
                "severity": "critical",
                "check": str(check.get(label_key, "unknown_check")),
                "expected": str(expected),
                "actual": str(check.get("actual", "n/a")),
                "source": str(report_path),
            }
        )
    return items

def split_gate_status(path: Path, gate_state: str, required: bool) -> Dict:
    if not required:
        return {"verdict": "not_required", "details": "Split gate not required.", "move_count": 0, "applied": False}
    if not path.exists() or path.stat().st_size == 0:
        return {"verdict": "fail", "details": "Missing main/supplement split plan.", "move_count": 0, "applied": False}
    try:
        payload = load_json(path)
    except Exception as exc:
        return {"verdict": "fail", "details": f"Unreadable split plan: {exc}", "move_count": 0, "applied": False}
    move_count = len(payload.get("sections_move_to_supplement", []))
    applied = bool(payload.get("applied"))
    if gate_state == "PUBLISH":
        if move_count == 0 or applied:
            return {
                "verdict": "pass",
                "details": "Split policy satisfied for publish gate.",
                "move_count": move_count,
                "applied": applied,
            }
        return {
            "verdict": "fail",
            "details": "Technical sections remain unsplit; rerun with --apply-supplement-split.",
            "move_count": move_count,
            "applied": applied,
        }
    return {
        "verdict": "pass",
        "details": "Split plan exists (apply required before publish if sections are flagged).",
        "move_count": move_count,
        "applied": applied,
    }

def _revision_instruction(item: Dict) -> str:
    """Generate a concise AI-actionable instruction for a single failed check."""
    gate = item.get("gate", "")
    check = item.get("check", "")
    expected = item.get("expected", "")
    actual = item.get("actual", "")

    instruction_map = {
        "unique_citation_count": f"Add more unique citations to reach {expected} (currently {actual}).",
        "recent_3y_share": f"Increase proportion of references from the last 3 years to {expected}.",
        "recent_5y_share": f"Replace older references with studies from the last 5 years.",
        "introduction_citation_coverage": f"Add citations to the Introduction section (need {expected}, have {actual}).",
        "discussion_citation_coverage": f"Add citations to the Discussion section (need {expected}, have {actual}).",
        "citation_density": f"Increase overall citation density to {expected}.",
        "missing_citekeys": "Ensure all @citekeys in text have matching entries in references.bib.",
        "methods_ratio_within_limit": f"Shorten Methods section to keep word ratio within {expected}.",
        "narrative_word_share_sufficient": f"Expand narrative sections (Intro/Results/Discussion) to reach ratio {expected}.",
        "results_numeric_density": f"Add more numeric evidence (percentages, CIs, effect sizes) to Results paragraphs.",
        "discussion_implication_density": f"Add practice/policy implication language to Discussion paragraphs.",
        "technical_term_overflow_control": f"Remove technical/pipeline terms from narrative sections.",
        "frontloaded_field_state_section": "Add a field-context section (e.g. 'Where the field stands now') near the beginning.",
        "research_in_context_h1_present": "Add a '# Research in context' section with evidence-before/evidence-after bullets.",
        "field_state_h1_present_when_required": "Add a '# Where the field stands now' section.",
        "progress_paragraph_ratio": f"Add field-progress language with citations to more paragraphs ({expected}).",
        "gap_statements_count": f"Add gap/uncertainty statements (need {expected}, have {actual}).",
        "interpretation_sentences_count": f"Add interpretation sentences using 'suggest/indicate/imply' (need {expected}).",
        "core_section_evidence_coverage": f"Ensure all core sections cite evidence or include numeric anchors.",
        "Core IMRAD section presence": f"Add missing IMRAD sections: {actual}.",
        "Narrative section bullet leakage": "Convert bullet lists in narrative sections to flowing prose.",
        "Interpretive paragraph evidence anchoring": f"Add evidence anchors (numbers, CIs, figure refs) to discussion paragraphs.",
        "Interpretive transition coherence": f"Add transition words (however, moreover, therefore, etc.) to discussion paragraphs.",
        "Sentence-starter repetition control": "Vary sentence openings to avoid repetitive consecutive starters.",
        "Cliche suppression": "Remove cliché phrases (e.g. 'it is worth noting', 'further research is needed').",
        "Sentence-length variability sanity": "Vary sentence lengths for better prose rhythm.",
        "Citation style consistency": "Use exactly one citation style throughout the manuscript.",
        "Citekey coverage in bibliography": "Add missing citekeys to references.bib.",
    }

    instruction = instruction_map.get(check, f"Revise to meet: {check} {expected} (currently {actual}).")
    return f"[{gate}] {instruction}"

def write_revision_tasks(round_dir: Path, round_idx: int, failed_items: List[Dict]) -> Tuple[Path, Path]:
    json_out = round_dir / "revision_tasks.json"
    md_out = round_dir / "revision_tasks.md"

    # Add actionable instructions to each item
    enriched_items = []
    for item in failed_items:
        enriched = dict(item)
        enriched["instruction"] = _revision_instruction(item)
        enriched_items.append(enriched)

    payload = {
        "schema_version": 2,
        "generated_at": utc_now(),
        "round": round_idx,
        "total_blocking": len(enriched_items),
        "items": enriched_items,
    }
    save_json(json_out, payload)

    lines = [
        f"# Writing Superloop Revision Tasks (Round {round_idx})",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Blocking items: {len(enriched_items)}",
        "",
        "## Actionable Instructions",
        "",
    ]
    for i, item in enumerate(enriched_items, 1):
        lines.append(f"{i}. {item['instruction']}")
    lines.extend([
        "",
        "## Detail Table",
        "",
        "| Gate | Check | Expected | Actual | Source |",
        "|---|---|---|---|---|",
    ])
    for item in enriched_items:
        lines.append(
            f"| {item['gate']} | {item['check']} | {item['expected']} | {item['actual']} | {item['source']} |"
        )
    lines.extend(
        [
            "",
            "## Rewrite Protocol",
            "",
            "1. Rewrite only the paragraphs linked to failed checks.",
            "2. Preserve numerical findings and citation keys while improving structure.",
            "3. Re-run writing superloop and confirm all gates pass in the next round.",
            "",
        ]
    )
    save_md(md_out, "\n".join(lines))
    return json_out, md_out

def sync_latest_round_artifacts(round_dir: Path, process_dir: Path) -> None:
    mapping = {
        "style_gate_contract.json": "style_gate_contract.json",
        "style_gate_report.json": "style_gate_report.json",
        "style_gate_report.md": "style_gate_report.md",
        "prose_quality_review.json": "prose_quality_review.json",
        "prose_quality_review.md": "prose_quality_review.md",
        "content_focus_review.json": "content_focus_review.json",
        "content_focus_review.md": "content_focus_review.md",
        "field_progress_review.json": "field_progress_review.json",
        "field_progress_review.md": "field_progress_review.md",
        "citation_architecture_review.json": "citation_architecture_review.json",
        "citation_architecture_review.md": "citation_architecture_review.md",
        "claim_traceability_review.json": "claim_traceability_review.json",
        "claim_traceability_review.md": "claim_traceability_review.md",
        "main_supplement_split_plan.json": "main_supplement_split_plan.json",
        "main_supplement_split_plan.md": "main_supplement_split_plan.md",
        "triad_review.json": "triad_review.json",
        "triad_review.md": "triad_review.md",
    }
    process_dir.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in mapping.items():
        src = round_dir / src_name
        if src.exists():
            shutil.copy2(src, process_dir / dst_name)

def run_round(
    workdir: Path,
    scripts_dir: Path,
    round_idx: int,
    rounds_dir: Path,
    manuscript: Path,
    bib: Path,
    supplement: Path,
    gate_state: str,
    gate_policy: Dict[str, bool],
    apply_supplement_split: bool,
) -> Dict:
    round_dir = rounds_dir / f"round_{round_idx:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)

    style_contract = round_dir / "style_gate_contract.json"
    style_json = round_dir / "style_gate_report.json"
    style_md = round_dir / "style_gate_report.md"
    prose_json = round_dir / "prose_quality_review.json"
    prose_md = round_dir / "prose_quality_review.md"
    content_json = round_dir / "content_focus_review.json"
    content_md = round_dir / "content_focus_review.md"
    field_json = round_dir / "field_progress_review.json"
    field_md = round_dir / "field_progress_review.md"
    citation_json = round_dir / "citation_architecture_review.json"
    citation_md = round_dir / "citation_architecture_review.md"
    traceability_json = round_dir / "claim_traceability_review.json"
    traceability_md = round_dir / "claim_traceability_review.md"
    split_json = round_dir / "main_supplement_split_plan.json"
    split_md = round_dir / "main_supplement_split_plan.md"
    triad_json = round_dir / "triad_review.json"
    triad_md = round_dir / "triad_review.md"

    run_cmd(
        [
            sys.executable,
            str(scripts_dir / "build_style_gate.py"),
            str(workdir),
            "--manuscript",
            str(manuscript),
            "--contract-out",
            str(style_contract),
            "--report-out",
            str(style_json),
            "--report-md-out",
            str(style_md),
        ]
    )
    run_cmd(
        [
            sys.executable,
            str(scripts_dir / "evaluate_prose_quality.py"),
            str(workdir),
            "--manuscript",
            str(manuscript),
            "--output-json",
            str(prose_json),
            "--output-md",
            str(prose_md),
        ]
    )

    if gate_policy["content_focus_gate_required"]:
        run_cmd(
            [
                sys.executable,
                str(scripts_dir / "evaluate_content_focus.py"),
                str(workdir),
                "--manuscript",
                str(manuscript),
                "--output",
                str(content_json),
                "--md",
                str(content_md),
                "--no-strict",
            ]
        )

    if gate_policy["field_progress_gate_required"]:
        run_cmd(
            [
                sys.executable,
                str(scripts_dir / "evaluate_field_progress.py"),
                str(workdir),
                "--manuscript",
                str(manuscript),
                "--output",
                str(field_json),
                "--md",
                str(field_md),
                "--no-strict",
            ]
        )

    if gate_policy["citation_architecture_gate_required"]:
        run_cmd(
            [
                sys.executable,
                str(scripts_dir / "evaluate_citation_architecture.py"),
                str(workdir),
                "--manuscript",
                str(manuscript),
                "--bib",
                str(bib),
                "--output",
                str(citation_json),
                "--md",
                str(citation_md),
                "--no-strict",
            ]
        )

    if gate_policy["claim_traceability_gate_required"]:
        run_cmd(
            [
                sys.executable,
                str(scripts_dir / "evaluate_claim_traceability.py"),
                str(workdir),
                "--manuscript",
                str(manuscript),
                "--output",
                str(traceability_json),
                "--md",
                str(traceability_md),
                "--no-strict",
            ]
        )

    split_cmd = [
        sys.executable,
        str(scripts_dir / "split_main_supplement.py"),
        str(workdir),
        "--manuscript",
        str(manuscript),
        "--supplement",
        str(supplement),
        "--output",
        str(split_json),
        "--md",
        str(split_md),
    ]
    if apply_supplement_split:
        split_cmd.append("--apply")
    run_cmd(split_cmd)

    # Triad reviewer consumes process-level gate files. Sync current round
    # artifacts before triad so it evaluates the latest round, not stale state.
    sync_latest_round_artifacts(round_dir, workdir / "process")

    if gate_policy["triad_review_required"]:
        run_cmd(
            [
                sys.executable,
                str(scripts_dir / "run_triad_review.py"),
                str(workdir),
                "--output",
                str(triad_json),
                "--md",
                str(triad_md),
                "--no-strict",
            ]
        )

    style_status = read_score_verdict(style_json, "style_score")
    prose_status = read_score_verdict(prose_json, "prose_score")
    content_status = (
        read_score_verdict(content_json, "content_score")
        if gate_policy["content_focus_gate_required"]
        else {"status": "not_required", "verdict": "not_required", "score_pct": None, "pass_threshold_score": None, "error": ""}
    )
    field_status = (
        read_score_verdict(field_json, "field_progress_score")
        if gate_policy["field_progress_gate_required"]
        else {"status": "not_required", "verdict": "not_required", "score_pct": None, "pass_threshold_score": None, "error": ""}
    )
    citation_status = (
        read_score_verdict(citation_json, "citation_score")
        if gate_policy["citation_architecture_gate_required"]
        else {"status": "not_required", "verdict": "not_required", "score_pct": None, "pass_threshold_score": None, "error": ""}
    )
    traceability_status = (
        read_score_verdict(traceability_json, "traceability_score")
        if gate_policy["claim_traceability_gate_required"]
        else {"status": "not_required", "verdict": "not_required", "score_pct": None, "pass_threshold_score": None, "error": ""}
    )
    split_status = split_gate_status(split_json, gate_state=gate_state, required=gate_policy["main_supplement_split_required"])
    triad_status = (
        read_score_verdict(triad_json, "overall")
        if gate_policy["triad_review_required"]
        else {"status": "not_required", "verdict": "not_required", "score_pct": None, "pass_threshold_score": None, "error": ""}
    )

    # run_triad_review uses `overall.verdict` + `overall.score_pct`
    if gate_policy["triad_review_required"] and triad_json.exists() and triad_json.stat().st_size > 0:
        try:
            triad_payload = load_json(triad_json)
            overall = triad_payload.get("overall", {})
            triad_status = {
                "status": "ok",
                "verdict": str(overall.get("verdict", "invalid")).lower(),
                "score_pct": overall.get("score_pct"),
                "pass_threshold_score": triad_payload.get("threshold_score"),
                "error": "",
            }
        except Exception as exc:
            triad_status = {
                "status": "invalid",
                "verdict": "invalid",
                "score_pct": None,
                "pass_threshold_score": None,
                "error": f"Unreadable triad report: {exc}",
            }

    failed_items: List[Dict] = []
    if style_status.get("verdict") != "pass":
        failed_items.extend(build_failed_items("style_gate", style_json, "checks", "name"))

    # prose checks are nested (`prose_score.checks`), so load explicitly.
    if prose_status.get("verdict") != "pass":
        if prose_json.exists() and prose_json.stat().st_size > 0:
            try:
                prose_payload = load_json(prose_json)
                for check in (prose_payload.get("prose_score") or {}).get("checks", []):
                    if bool(check.get("pass")):
                        continue
                    expected = (
                        check.get("expected")
                        if "expected" in check
                        else (
                            f">= {check.get('expected_min')}"
                            if "expected_min" in check
                            else f"<= {check.get('expected_max', 'n/a')}"
                        )
                    )
                    failed_items.append(
                        {
                            "gate": "prose_quality",
                            "severity": "critical",
                            "check": str(check.get("name", "unknown_check")),
                            "expected": str(expected),
                            "actual": str(check.get("actual", "n/a")),
                            "source": str(prose_json),
                        }
                    )
            except Exception as exc:
                failed_items.append(
                    {
                        "gate": "prose_quality",
                        "severity": "critical",
                        "check": "report_readability",
                        "expected": "valid JSON report",
                        "actual": f"unreadable ({exc})",
                        "source": str(prose_json),
                    }
                )

    if gate_policy["content_focus_gate_required"] and content_status.get("verdict") != "pass":
        failed_items.extend(build_failed_items("content_focus", content_json, "checks", "id"))
    if gate_policy["field_progress_gate_required"] and field_status.get("verdict") != "pass":
        failed_items.extend(build_failed_items("field_progress", field_json, "checks", "id"))
    if gate_policy["citation_architecture_gate_required"] and citation_status.get("verdict") != "pass":
        failed_items.extend(build_failed_items("citation_architecture", citation_json, "checks", "id"))
    if gate_policy["claim_traceability_gate_required"] and traceability_status.get("verdict") != "pass":
        failed_items.extend(build_failed_items("claim_traceability", traceability_json, "checks", "id"))
    if split_status.get("verdict") not in {"pass", "not_required"}:
        failed_items.append(
            {
                "gate": "main_supplement_split",
                "severity": "critical",
                "check": "split_policy",
                "expected": "publish-stage technical sections are split from main text",
                "actual": split_status.get("details", "failed"),
                "source": str(split_json),
            }
        )
    if gate_policy["triad_review_required"] and triad_status.get("verdict") != "pass":
        failed_items.append(
            {
                "gate": "triad_review",
                "severity": "critical",
                "check": "panel_convergence",
                "expected": "triad verdict == pass",
                "actual": f"verdict={triad_status.get('verdict')}, score={triad_status.get('score_pct')}",
                "source": str(triad_json),
            }
        )

    revision_json = None
    revision_md = None
    if failed_items:
        revision_json, revision_md = write_revision_tasks(round_dir, round_idx, failed_items)

    # Persist latest round artifacts to canonical process paths for downstream gates.
    sync_latest_round_artifacts(round_dir, workdir / "process")

    gate_pass = (
        style_status.get("verdict") == "pass"
        and prose_status.get("verdict") == "pass"
        and (not gate_policy["content_focus_gate_required"] or content_status.get("verdict") == "pass")
        and (not gate_policy["field_progress_gate_required"] or field_status.get("verdict") == "pass")
        and (not gate_policy["citation_architecture_gate_required"] or citation_status.get("verdict") == "pass")
        and (not gate_policy["claim_traceability_gate_required"] or traceability_status.get("verdict") == "pass")
        and split_status.get("verdict") in {"pass", "not_required"}
        and (not gate_policy["triad_review_required"] or triad_status.get("verdict") == "pass")
    )

    return {
        "round": round_idx,
        "generated_at": utc_now(),
        "artifacts_dir": str(round_dir),
        "gates": {
            "style": style_status,
            "prose": prose_status,
            "content_focus": content_status,
            "field_progress": field_status,
            "citation_architecture": citation_status,
            "claim_traceability": traceability_status,
            "main_supplement_split": split_status,
            "triad_review": triad_status,
        },
        "failed_items_count": len(failed_items),
        "failed_items": failed_items,
        "revision_tasks_json": str(revision_json) if revision_json else "",
        "revision_tasks_md": str(revision_md) if revision_md else "",
        "all_pass": gate_pass,
    }

def to_markdown(report: Dict) -> str:
    lines = [
        "# Writing Superloop Report",
        "",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Workdir: {report.get('workdir', '')}",
        f"- Manuscript: {report.get('manuscript', '')}",
        f"- Gate state: {report.get('gate_state', '')}",
        f"- Quality bar: {report.get('quality_bar', '')}",
        f"- Max rounds: {report.get('max_rounds', 0)}",
        f"- Rounds completed: {report.get('rounds_completed', 0)}",
        f"- Verdict: {report.get('verdict', 'unknown')}",
        "",
        "## Round Summary",
        "",
        "| Round | Style | Prose | Content | Field | Citation | Traceability | Split | Triad | Failed Items | Pass |",
        "|---:|---|---|---|---|---|---|---|---|---:|---|",
    ]
    for rd in report.get("rounds", []):
        g = rd.get("gates", {})
        lines.append(
            "| "
            + f"{rd.get('round', 0)} | "
            + f"{(g.get('style') or {}).get('verdict', 'n/a')} | "
                + f"{(g.get('prose') or {}).get('verdict', 'n/a')} | "
                + f"{(g.get('content_focus') or {}).get('verdict', 'n/a')} | "
                + f"{(g.get('field_progress') or {}).get('verdict', 'n/a')} | "
                + f"{(g.get('citation_architecture') or {}).get('verdict', 'n/a')} | "
                + f"{(g.get('claim_traceability') or {}).get('verdict', 'n/a')} | "
                + f"{(g.get('main_supplement_split') or {}).get('verdict', 'n/a')} | "
                + f"{(g.get('triad_review') or {}).get('verdict', 'n/a')} | "
                + f"{rd.get('failed_items_count', 0)} | "
            + f"{'Yes' if rd.get('all_pass') else 'No'} |"
        )

    lines.extend(["", "## Next Action", ""])
    if report.get("verdict") == "pass":
        lines.append("- Superloop converged. Ready for gate-contract check and submission decision.")
    else:
        last = report.get("rounds", [])[-1] if report.get("rounds") else {}
        task_md = last.get("revision_tasks_md", "")
        if task_md:
            lines.append(f"- Apply revision tasks: `{task_md}`")
        else:
            lines.append("- Review failed gate artifacts and revise manuscript before rerun.")
    lines.append("")
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run iterative writing superloop for manuscript quality convergence.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"), help="Manuscript path")
    parser.add_argument("--bib", type=Path, default=Path("process/references.bib"), help="Bibliography path")
    parser.add_argument(
        "--supplement",
        type=Path,
        default=Path("manuscript/supplement_methods_appendix.qmd"),
        help="Supplement path for split gate",
    )
    parser.add_argument("--gate-state", choices=["DECISION", "PUBLISH"], default="DECISION")
    parser.add_argument("--max-rounds", type=int, help="Override max rounds (default depends on quality bar)")
    parser.add_argument("--apply-supplement-split", action="store_true", help="Apply split when split gate is run")
    parser.add_argument("--force-triad", action="store_true", help="Force triad gate even when contract does not require it")
    parser.add_argument("--output-json", type=Path, default=Path("process/writing_superloop_report.json"))
    parser.add_argument("--output-md", type=Path, default=Path("process/writing_superloop_report.md"))
    parser.add_argument("--auto-fix", action="store_true", help="Apply rule-based mechanical fixes between rounds (cliché removal, transitions, etc.)")
    parser.add_argument("--no-strict", action="store_true", help="Exit 0 even when loop does not converge")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        print(f"[error] Workdir does not exist: {workdir}")
        raise SystemExit(1)

    manuscript = args.manuscript if args.manuscript.is_absolute() else (workdir / args.manuscript)
    bib = args.bib if args.bib.is_absolute() else (workdir / args.bib)
    supplement = args.supplement if args.supplement.is_absolute() else (workdir / args.supplement)
    if not manuscript.exists():
        print(f"[error] Missing manuscript: {manuscript}")
        print("[hint] Expected a Quarto/Markdown file at the manuscript path.")
        raise SystemExit(1)
    if not bib.exists():
        print(f"[error] Missing bibliography: {bib}")
        print("[hint] Create an empty .bib file or specify --bib path.")
        raise SystemExit(1)

    scripts_dir = Path(__file__).resolve().parent
    process_dir = workdir / "process"
    rounds_dir = process_dir / "writing_superloop"
    rounds_dir.mkdir(parents=True, exist_ok=True)

    contract_path = process_dir / "project_contract.json"
    if contract_path.exists():
        contract = load_json(contract_path)
    else:
        print("[warning] project_contract.json not found — all quality gates will use defaults (most gates disabled).")
        print("[hint] Run legacy/scripts/parse_user_intent.py first to create the contract.")
        contract = {}
    gate_policy = resolve_gate_policy(contract, force_triad=args.force_triad)
    qb = quality_bar(workdir)
    max_rounds = args.max_rounds if args.max_rounds and args.max_rounds > 0 else default_rounds_from_quality_bar(qb)

    rounds: List[Dict] = []
    converged = False
    fatal_error = ""
    for idx in range(1, max_rounds + 1):
        try:
            round_report = run_round(
                workdir=workdir,
                scripts_dir=scripts_dir,
                round_idx=idx,
                rounds_dir=rounds_dir,
                manuscript=manuscript,
                bib=bib,
                supplement=supplement,
                gate_state=args.gate_state,
                gate_policy=gate_policy,
                apply_supplement_split=args.apply_supplement_split,
            )
        except subprocess.CalledProcessError as exc:
            fatal_error = f"Round {idx} failed while running: {' '.join(exc.cmd)} (exit={exc.returncode})"
            rounds.append(
                {
                    "round": idx,
                    "generated_at": utc_now(),
                    "all_pass": False,
                    "failed_items_count": 1,
                    "failed_items": [
                        {
                            "gate": "execution",
                            "severity": "critical",
                            "check": "command_execution",
                            "expected": "gate script exits successfully",
                            "actual": fatal_error,
                            "source": "subprocess",
                        }
                    ],
                }
            )
            break

        rounds.append(round_report)
        if round_report.get("all_pass"):
            converged = True
            break

        # --auto-fix: apply mechanical revisions before the next round
        if args.auto_fix and round_report.get("revision_tasks_json") and idx < max_rounds:
            try:
                from apply_revisions import apply_revisions as _apply_rev
                rev_path = Path(round_report["revision_tasks_json"])
                if rev_path.exists():
                    rev_tasks = load_json(rev_path)
                    fix_result = _apply_rev(manuscript, rev_tasks, dry_run=False)
                    applied_n = sum(a["changes"] for a in fix_result.get("applied", []))
                    deferred_n = len(fix_result.get("deferred_to_llm", []))
                    print(f"[auto-fix] Round {idx}: {applied_n} mechanical changes applied, {deferred_n} items deferred to LLM.")
                    if fix_result.get("backup_path"):
                        print(f"[auto-fix] Backup: {fix_result['backup_path']}")
                    # Save auto-fix report alongside round artifacts
                    save_json(Path(round_report["artifacts_dir"]) / "auto_fix_report.json", {
                        "round": idx, "generated_at": utc_now(), **fix_result,
                    })
                    # Write LLM prompt for deferred items
                    if fix_result.get("deferred_to_llm"):
                        from apply_revisions import write_llm_prompt
                        prompt_path = Path(round_report["artifacts_dir"]) / "llm_revision_prompt.md"
                        write_llm_prompt(prompt_path, fix_result["deferred_to_llm"], idx)
                        print(f"[auto-fix] LLM revision prompt: {prompt_path}")
            except Exception as exc:
                print(f"[warning] Auto-fix failed for round {idx}: {exc}")

    verdict = "pass" if converged else "fail"
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "manuscript": str(manuscript),
        "bib": str(bib),
        "supplement": str(supplement),
        "gate_state": args.gate_state,
        "quality_bar": qb,
        "gate_policy": gate_policy,
        "max_rounds": max_rounds,
        "rounds_completed": len(rounds),
        "converged": converged,
        "verdict": verdict,
        "fatal_error": fatal_error,
        "rounds": rounds,
    }

    output_json = args.output_json if args.output_json.is_absolute() else (workdir / args.output_json)
    output_md = args.output_md if args.output_md.is_absolute() else (workdir / args.output_md)
    save_json(output_json, report)
    save_md(output_md, to_markdown(report))

    print(f"Writing superloop verdict: {verdict}")
    print(f"JSON: {output_json}")
    print(f"MD: {output_md}")

    if verdict != "pass" and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
