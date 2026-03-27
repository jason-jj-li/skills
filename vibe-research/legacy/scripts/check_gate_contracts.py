#!/usr/bin/env python3
"""
Evaluate publish/readiness gate contracts for a vibe-research workdir.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from _common import TOP_TIER_HINTS, bool_policy, infer_journal_target, infer_submission_like, infer_top_tier_target, load_json, resolve_gate_policy, save_json, utc_now

GATE_STATES = ("EXECUTE", "DECISION", "PUBLISH")


def rel(path: Path, workdir: Path) -> str:
    try:
        return str(path.relative_to(workdir))
    except ValueError:
        return str(path)

def find_existing(workdir: Path, candidates: List[str]) -> List[str]:
    out: List[str] = []
    for candidate in candidates:
        p = workdir / candidate
        if p.exists():
            out.append(candidate)
    return out

def find_globbed(workdir: Path, patterns: List[str]) -> List[str]:
    out: List[str] = []
    for pattern in patterns:
        for path in sorted(workdir.glob(pattern)):
            if path.is_file():
                out.append(rel(path, workdir))
    return out

def pick_latest_non_empty(workdir: Path, candidates: List[str]) -> Optional[str]:
    existing: List[Path] = []
    for candidate in candidates:
        p = workdir / candidate
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            existing.append(p)
    if not existing:
        return None
    latest = max(existing, key=lambda p: p.stat().st_mtime)
    return rel(latest, workdir)

def choose_manifest(workdir: Path) -> Optional[Path]:
    refined = workdir / "outputs" / "refined_manifest.json"
    if refined.exists():
        return refined
    regular = workdir / "outputs" / "manifest.json"
    if regular.exists():
        return regular
    return None

def is_non_empty(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0

def load_contract(workdir: Path) -> Dict:
    path = workdir / "process" / "project_contract.json"
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return load_json(path)
    except Exception:
        return {}

def evaluate_revision_traceability(workdir: Path) -> Tuple[str, List[str], str]:
    metadata_file = workdir / "metadata.json"
    is_revision = False
    if metadata_file.exists():
        metadata = load_json(metadata_file)
        is_revision = bool(metadata.get("is_revision")) or bool(metadata.get("parent_paper_id"))

    revision_plan = find_globbed(workdir, ["revision_plan_*.md"])
    reply_files = find_globbed(workdir, ["reply_to_reviewers_*.md"])
    inputs_files = find_globbed(workdir, ["revision_inputs_*.json"])
    evidence = revision_plan + reply_files + inputs_files

    if not is_revision and not evidence:
        return "not_applicable", [], "No revision chain detected."

    if revision_plan and reply_files:
        return "pass", evidence, "Revision traceability files found."
    return "fail", evidence, "Missing revision_plan_*.md or reply_to_reviewers_*.md."

def make_contract(contract_id: str, description: str, required: bool, status: str, evidence: List[str], details: str) -> Dict:
    return {
        "id": contract_id,
        "description": description,
        "required": required,
        "status": status,
        "evidence": evidence,
        "details": details,
    }

def read_score_verdict(report_path: Path, score_key: str) -> Tuple[str, Optional[float], Optional[float], str]:
    if not report_path.exists() or report_path.stat().st_size == 0:
        return "missing", None, None, "Missing report JSON."
    try:
        payload = load_json(report_path)
        block = payload.get(score_key, {})
        if not isinstance(block, dict):
            return "invalid", None, None, f"Missing `{score_key}` block."
        verdict = str(block.get("verdict", "")).lower()
        score = block.get("score_pct")
        threshold = block.get("pass_threshold_score")
        return verdict or "invalid", score, threshold, ""
    except Exception as exc:
        return "invalid", None, None, f"Unreadable JSON: {exc}"

def evaluate(workdir: Path, gate_state: str) -> Dict:
    contracts: List[Dict] = []
    contract = load_contract(workdir)
    policy = resolve_gate_policy(contract)

    journal_target = policy["journal_target"]
    top_tier_target = policy["top_tier_target"]

    standards = workdir / "process" / "standards_snapshot.md"
    standards_ok = is_non_empty(standards)
    contracts.append(
        make_contract(
            "standards_snapshot_present",
            "process/standards_snapshot.md exists and is non-empty",
            True,
            "pass" if standards_ok else "fail",
            ["process/standards_snapshot.md"] if standards_ok else [],
            "Standards gate ready." if standards_ok else "Missing or empty standards snapshot.",
        )
    )

    target_required = policy["target_gate_required"]
    target_files = find_existing(
        workdir,
        [
            "process/target_gate.json",
            "process/target_gate.md",
            "outputs/target_gate.json",
            "outputs/target_gate.md",
        ],
    )
    target_json_rel = pick_latest_non_empty(workdir, ["process/target_gate.json", "outputs/target_gate.json"])
    target_md_present = ("process/target_gate.md" in target_files) or ("outputs/target_gate.md" in target_files)
    target_artifacts_ok = bool(target_json_rel) and target_md_present
    contracts.append(
        make_contract(
            "target_gate_artifacts_present",
            "target gate report artifacts (JSON+MD) exist",
            target_required,
            "pass" if target_artifacts_ok else ("not_applicable" if not target_required else "fail"),
            target_files,
            (
                "Target gate artifacts found."
                if target_artifacts_ok
                else ("Gate not required for this project." if not target_required else "Missing target_gate.json or target_gate.md.")
            ),
        )
    )

    target_verdict_status = "not_applicable"
    target_verdict_details = "Gate not required for this project."
    target_verdict_evidence: List[str] = []
    if target_required:
        target_verdict_status = "fail"
        target_verdict_details = "Missing target gate report JSON."
        if target_json_rel:
            target_json = workdir / target_json_rel
            target_verdict_evidence = [target_json_rel]
            try:
                payload = load_json(target_json)
                verdict = str(((payload.get("summary") or {}).get("verdict") or "")).lower()
                if verdict == "pass":
                    target_verdict_status = "pass"
                    target_verdict_details = "Target gate passed."
                else:
                    target_verdict_status = "fail"
                    target_verdict_details = "Target gate failed."
            except Exception as exc:
                target_verdict_status = "fail"
                target_verdict_details = f"Unreadable target gate report: {exc}"

    contracts.append(
        make_contract(
            "target_gate_verdict_pass",
            "target gate verdict is pass",
            target_required,
            target_verdict_status,
            target_verdict_evidence,
            target_verdict_details,
        )
    )

    exemplar_files = find_existing(workdir, ["process/exemplar_benchmark.json", "process/exemplar_benchmark.md"])
    contracts.append(
        make_contract(
            "exemplar_benchmark_present",
            "Exemplar benchmark artifacts exist for target-journal alignment",
            top_tier_target,
            "pass" if exemplar_files else ("not_applicable" if not top_tier_target else "fail"),
            exemplar_files,
            (
                "Exemplar benchmark found."
                if exemplar_files
                else ("Not required for non-top-tier target." if not top_tier_target else "Missing exemplar benchmark artifacts.")
            ),
        )
    )

    manifest_file = choose_manifest(workdir)
    manifest_data: Dict = {}
    if manifest_file:
        manifest_data = load_json(manifest_file)
    manifest_evidence = [rel(manifest_file, workdir)] if manifest_file else []
    contracts.append(
        make_contract(
            "pipeline_manifest_present",
            "outputs/manifest.json or outputs/refined_manifest.json exists",
            True,
            "pass" if manifest_file else "fail",
            manifest_evidence,
            "Manifest found." if manifest_file else "No pipeline manifest found.",
        )
    )

    manifest_contracts = manifest_data.get("contracts", {}) if manifest_data else {}
    if isinstance(manifest_contracts, dict) and manifest_contracts:
        failed_manifest = [k for k, v in manifest_contracts.items() if not bool(v)]
        passed = len(failed_manifest) == 0
        detail = "All manifest contracts passed." if passed else f"Failed manifest contracts: {failed_manifest}"
        contracts.append(
            make_contract(
                "pipeline_contracts_passed",
                "all manifest contract checks are true",
                True,
                "pass" if passed else "fail",
                manifest_evidence,
                detail,
            )
        )
    else:
        contracts.append(
            make_contract(
                "pipeline_contracts_passed",
                "all manifest contract checks are true",
                True,
                "fail",
                manifest_evidence,
                "Manifest contracts are missing or invalid.",
            )
        )

    method_log_found = find_existing(workdir, ["experiment-log.md", "process/analysis_plan.md"])
    contracts.append(
        make_contract(
            "method_log_present",
            "experiment-log.md or process/analysis_plan.md exists",
            True,
            "pass" if method_log_found else "fail",
            method_log_found,
            "Method log found." if method_log_found else "No method log detected.",
        )
    )

    if gate_state in {"DECISION", "PUBLISH"}:
        writing_files = find_existing(workdir, ["process/writing_blueprint.json", "process/writing_outline.md"])
        writing_ok = len(writing_files) == 2
        contracts.append(
            make_contract(
                "writing_outline_present",
                "journal-targeted project includes writing blueprint and outline artifacts",
                journal_target,
                "pass" if writing_ok else ("not_applicable" if not journal_target else "fail"),
                writing_files,
                (
                    "Writing blueprint and outline found."
                    if writing_ok
                    else (
                        "Not required for non-journal-targeted project."
                        if not journal_target
                        else "Missing process/writing_blueprint.json or process/writing_outline.md."
                    )
                ),
            )
        )

        superloop_required = policy["writing_superloop_required"]
        superloop_files = find_existing(
            workdir,
            [
                "process/writing_superloop_report.json",
                "process/writing_superloop_report.md",
                "outputs/writing_superloop_report.json",
                "outputs/writing_superloop_report.md",
            ],
        )
        superloop_json_rel = pick_latest_non_empty(
            workdir,
            ["process/writing_superloop_report.json", "outputs/writing_superloop_report.json"],
        )
        superloop_ok = (
            ("process/writing_superloop_report.json" in superloop_files or "outputs/writing_superloop_report.json" in superloop_files)
            and ("process/writing_superloop_report.md" in superloop_files or "outputs/writing_superloop_report.md" in superloop_files)
        )
        contracts.append(
            make_contract(
                "writing_superloop_artifacts_present",
                "writing superloop convergence report artifacts (JSON+MD) exist",
                superloop_required,
                "pass" if superloop_ok else ("not_applicable" if not superloop_required else "fail"),
                superloop_files,
                (
                    "Writing superloop artifacts found."
                    if superloop_ok
                    else (
                        "Superloop not required for this project."
                        if not superloop_required
                        else "Missing writing_superloop_report.json or writing_superloop_report.md."
                    )
                ),
            )
        )

        superloop_verdict_status = "not_applicable"
        superloop_verdict_details = "Superloop not required for this project."
        superloop_verdict_evidence: List[str] = []
        if superloop_required:
            superloop_verdict_status = "fail"
            superloop_verdict_details = "Missing writing superloop report JSON."
            if superloop_json_rel:
                superloop_json = workdir / superloop_json_rel
                superloop_verdict_evidence = [superloop_json_rel]
                try:
                    payload = load_json(superloop_json)
                    verdict = str(payload.get("verdict", "invalid")).lower()
                    rounds_completed = payload.get("rounds_completed")
                    max_rounds = payload.get("max_rounds")
                    if verdict == "pass":
                        superloop_verdict_status = "pass"
                        superloop_verdict_details = (
                            f"Writing superloop converged (rounds={rounds_completed}/{max_rounds})."
                        )
                    else:
                        superloop_verdict_status = "fail"
                        superloop_verdict_details = (
                            f"Writing superloop did not converge (verdict={verdict}, rounds={rounds_completed}/{max_rounds})."
                        )
                except Exception as exc:
                    superloop_verdict_status = "fail"
                    superloop_verdict_details = f"Unreadable writing superloop report: {exc}"

        contracts.append(
            make_contract(
                "writing_superloop_verdict_pass",
                "writing superloop convergence verdict is pass",
                superloop_required,
                superloop_verdict_status,
                superloop_verdict_evidence,
                superloop_verdict_details,
            )
        )

        style_gate_files = find_existing(
            workdir,
            [
                "process/style_gate_contract.json",
                "process/style_gate_report.json",
                "process/style_gate_report.md",
                "outputs/style_gate_contract.json",
                "outputs/style_gate_report.json",
                "outputs/style_gate_report.md",
            ],
        )
        style_gate_report_rel = pick_latest_non_empty(
            workdir,
            ["process/style_gate_report.json", "outputs/style_gate_report.json"],
        )
        style_gate_contract_present = (
            "process/style_gate_contract.json" in style_gate_files
            or "outputs/style_gate_contract.json" in style_gate_files
        )
        style_gate_ok = style_gate_contract_present and bool(style_gate_report_rel)
        contracts.append(
            make_contract(
                "style_gate_artifacts_present",
                "journal-targeted project includes measurable style-gate contract and report",
                journal_target,
                "pass" if style_gate_ok else ("not_applicable" if not journal_target else "fail"),
                style_gate_files,
                (
                    "Style gate contract/report found."
                    if style_gate_ok
                    else (
                        "Not required for non-journal-targeted project."
                        if not journal_target
                        else "Missing style gate artifacts: style_gate_contract.json + latest style_gate_report.json."
                    )
                ),
            )
        )

        style_gate_verdict_status = "not_applicable"
        style_gate_verdict_details = "Not required for non-journal-targeted project."
        style_gate_verdict_evidence: List[str] = []
        if journal_target:
            style_gate_verdict_status = "fail"
            style_gate_verdict_details = "Missing style gate report JSON."
            if style_gate_report_rel:
                style_gate_report_path = workdir / style_gate_report_rel
                style_gate_verdict_evidence = [style_gate_report_rel]
                verdict, score, threshold, err = read_score_verdict(style_gate_report_path, "style_score")
                if verdict == "pass":
                    style_gate_verdict_status = "pass"
                    style_gate_verdict_details = f"Style gate passed (score={score}, threshold={threshold})."
                elif err:
                    style_gate_verdict_status = "fail"
                    style_gate_verdict_details = err
                else:
                    style_gate_verdict_status = "fail"
                    style_gate_verdict_details = f"Style gate failed (score={score}, threshold={threshold})."

        contracts.append(
            make_contract(
                "style_gate_verdict_pass",
                "journal-targeted project has passing style-gate verdict",
                journal_target,
                style_gate_verdict_status,
                style_gate_verdict_evidence,
                style_gate_verdict_details,
            )
        )

        prose_review_files = find_existing(
            workdir,
            [
                "process/prose_quality_review.json",
                "process/prose_quality_review.md",
                "outputs/prose_quality_review.json",
                "outputs/prose_quality_review.md",
            ],
        )
        prose_json_rel = pick_latest_non_empty(
            workdir,
            ["process/prose_quality_review.json", "outputs/prose_quality_review.json"],
        )
        prose_presence_ok = (
            ("process/prose_quality_review.json" in prose_review_files or "outputs/prose_quality_review.json" in prose_review_files)
            and ("process/prose_quality_review.md" in prose_review_files or "outputs/prose_quality_review.md" in prose_review_files)
        )
        contracts.append(
            make_contract(
                "prose_quality_artifacts_present",
                "journal-targeted project includes prose-quality JSON+MD artifacts from scientific-writing pass",
                journal_target,
                "pass" if prose_presence_ok else ("not_applicable" if not journal_target else "fail"),
                prose_review_files,
                (
                    "Prose quality artifacts found."
                    if prose_presence_ok
                    else (
                        "Not required for non-journal-targeted project."
                        if not journal_target
                        else "Missing prose quality artifacts: require both prose_quality_review.json and prose_quality_review.md."
                    )
                ),
            )
        )

        prose_verdict_status = "not_applicable"
        prose_verdict_details = "Not required for non-journal-targeted project."
        prose_verdict_evidence: List[str] = []
        if journal_target:
            prose_verdict_status = "fail"
            prose_verdict_details = "Missing prose quality JSON report."
            if prose_json_rel:
                prose_json = workdir / prose_json_rel
                prose_verdict_evidence = [prose_json_rel]
                verdict, score, threshold, err = read_score_verdict(prose_json, "prose_score")
                if verdict == "pass":
                    prose_verdict_status = "pass"
                    prose_verdict_details = f"Prose quality passed (score={score}, threshold={threshold})."
                elif err:
                    prose_verdict_status = "fail"
                    prose_verdict_details = err
                else:
                    prose_verdict_status = "fail"
                    prose_verdict_details = f"Prose quality failed (score={score}, threshold={threshold})."

        contracts.append(
            make_contract(
                "prose_quality_verdict_pass",
                "journal-targeted project has passing prose-quality verdict",
                journal_target,
                prose_verdict_status,
                prose_verdict_evidence,
                prose_verdict_details,
            )
        )

        content_required = policy["content_focus_gate_required"]
        content_files = find_existing(
            workdir,
            [
                "process/content_focus_review.json",
                "process/content_focus_review.md",
                "outputs/content_focus_review.json",
                "outputs/content_focus_review.md",
            ],
        )
        content_json_rel = pick_latest_non_empty(
            workdir,
            ["process/content_focus_review.json", "outputs/content_focus_review.json"],
        )
        content_ok = (
            ("process/content_focus_review.json" in content_files or "outputs/content_focus_review.json" in content_files)
            and ("process/content_focus_review.md" in content_files or "outputs/content_focus_review.md" in content_files)
        )
        contracts.append(
            make_contract(
                "content_focus_artifacts_present",
                "content-focus gate artifacts (JSON+MD) exist",
                content_required,
                "pass" if content_ok else ("not_applicable" if not content_required else "fail"),
                content_files,
                (
                    "Content-focus artifacts found."
                    if content_ok
                    else (
                        "Gate not required for this project." if not content_required else "Missing content_focus_review.json or content_focus_review.md."
                    )
                ),
            )
        )

        content_verdict_status = "not_applicable"
        content_verdict_details = "Gate not required for this project."
        content_verdict_evidence: List[str] = []
        if content_required:
            content_verdict_status = "fail"
            content_verdict_details = "Missing content focus report JSON."
            if content_json_rel:
                content_json = workdir / content_json_rel
                content_verdict_evidence = [content_json_rel]
                verdict, score, threshold, err = read_score_verdict(content_json, "content_score")
                if verdict == "pass":
                    content_verdict_status = "pass"
                    content_verdict_details = f"Content focus passed (score={score}, threshold={threshold})."
                elif err:
                    content_verdict_status = "fail"
                    content_verdict_details = err
                else:
                    content_verdict_status = "fail"
                    content_verdict_details = f"Content focus failed (score={score}, threshold={threshold})."

        contracts.append(
            make_contract(
                "content_focus_verdict_pass",
                "content-focus gate verdict is pass",
                content_required,
                content_verdict_status,
                content_verdict_evidence,
                content_verdict_details,
            )
        )

        field_required = policy["field_progress_gate_required"]
        field_files = find_existing(
            workdir,
            [
                "process/field_progress_review.json",
                "process/field_progress_review.md",
                "outputs/field_progress_review.json",
                "outputs/field_progress_review.md",
            ],
        )
        field_json_rel = pick_latest_non_empty(
            workdir,
            ["process/field_progress_review.json", "outputs/field_progress_review.json"],
        )
        field_ok = (
            ("process/field_progress_review.json" in field_files or "outputs/field_progress_review.json" in field_files)
            and ("process/field_progress_review.md" in field_files or "outputs/field_progress_review.md" in field_files)
        )
        contracts.append(
            make_contract(
                "field_progress_artifacts_present",
                "field-progress gate artifacts (JSON+MD) exist",
                field_required,
                "pass" if field_ok else ("not_applicable" if not field_required else "fail"),
                field_files,
                (
                    "Field-progress artifacts found."
                    if field_ok
                    else (
                        "Gate not required for this project." if not field_required else "Missing field_progress_review.json or field_progress_review.md."
                    )
                ),
            )
        )

        field_verdict_status = "not_applicable"
        field_verdict_details = "Gate not required for this project."
        field_verdict_evidence: List[str] = []
        if field_required:
            field_verdict_status = "fail"
            field_verdict_details = "Missing field-progress report JSON."
            if field_json_rel:
                field_json = workdir / field_json_rel
                field_verdict_evidence = [field_json_rel]
                verdict, score, threshold, err = read_score_verdict(field_json, "field_progress_score")
                if verdict == "pass":
                    field_verdict_status = "pass"
                    field_verdict_details = f"Field progress passed (score={score}, threshold={threshold})."
                elif err:
                    field_verdict_status = "fail"
                    field_verdict_details = err
                else:
                    field_verdict_status = "fail"
                    field_verdict_details = f"Field progress failed (score={score}, threshold={threshold})."

        contracts.append(
            make_contract(
                "field_progress_verdict_pass",
                "field-progress gate verdict is pass",
                field_required,
                field_verdict_status,
                field_verdict_evidence,
                field_verdict_details,
            )
        )

        citation_required = policy["citation_architecture_gate_required"]
        citation_files = find_existing(
            workdir,
            [
                "process/citation_architecture_review.json",
                "process/citation_architecture_review.md",
                "outputs/citation_architecture_review.json",
                "outputs/citation_architecture_review.md",
            ],
        )
        citation_json_rel = pick_latest_non_empty(
            workdir,
            ["process/citation_architecture_review.json", "outputs/citation_architecture_review.json"],
        )
        citation_ok = (
            ("process/citation_architecture_review.json" in citation_files or "outputs/citation_architecture_review.json" in citation_files)
            and ("process/citation_architecture_review.md" in citation_files or "outputs/citation_architecture_review.md" in citation_files)
        )
        contracts.append(
            make_contract(
                "citation_architecture_artifacts_present",
                "citation architecture gate artifacts (JSON+MD) exist",
                citation_required,
                "pass" if citation_ok else ("not_applicable" if not citation_required else "fail"),
                citation_files,
                (
                    "Citation architecture artifacts found."
                    if citation_ok
                    else (
                        "Gate not required for this project." if not citation_required else "Missing citation_architecture_review.json or citation_architecture_review.md."
                    )
                ),
            )
        )

        citation_verdict_status = "not_applicable"
        citation_verdict_details = "Gate not required for this project."
        citation_verdict_evidence: List[str] = []
        if citation_required:
            citation_verdict_status = "fail"
            citation_verdict_details = "Missing citation architecture report JSON."
            if citation_json_rel:
                citation_json = workdir / citation_json_rel
                citation_verdict_evidence = [citation_json_rel]
                verdict, score, threshold, err = read_score_verdict(citation_json, "citation_score")
                if verdict == "pass":
                    citation_verdict_status = "pass"
                    citation_verdict_details = f"Citation architecture passed (score={score}, threshold={threshold})."
                elif err:
                    citation_verdict_status = "fail"
                    citation_verdict_details = err
                else:
                    citation_verdict_status = "fail"
                    citation_verdict_details = f"Citation architecture failed (score={score}, threshold={threshold})."

        contracts.append(
            make_contract(
                "citation_architecture_verdict_pass",
                "citation architecture gate verdict is pass",
                citation_required,
                citation_verdict_status,
                citation_verdict_evidence,
                citation_verdict_details,
            )
        )

        trace_required = policy["claim_traceability_gate_required"]
        trace_files = find_existing(
            workdir,
            [
                "process/claim_traceability_review.json",
                "process/claim_traceability_review.md",
                "outputs/claim_traceability_review.json",
                "outputs/claim_traceability_review.md",
            ],
        )
        trace_json_rel = pick_latest_non_empty(
            workdir,
            ["process/claim_traceability_review.json", "outputs/claim_traceability_review.json"],
        )
        trace_ok = (
            ("process/claim_traceability_review.json" in trace_files or "outputs/claim_traceability_review.json" in trace_files)
            and ("process/claim_traceability_review.md" in trace_files or "outputs/claim_traceability_review.md" in trace_files)
        )
        contracts.append(
            make_contract(
                "claim_traceability_artifacts_present",
                "claim-traceability gate artifacts (JSON+MD) exist",
                trace_required,
                "pass" if trace_ok else ("not_applicable" if not trace_required else "fail"),
                trace_files,
                (
                    "Claim-traceability artifacts found."
                    if trace_ok
                    else (
                        "Gate not required for this project."
                        if not trace_required
                        else "Missing claim_traceability_review.json or claim_traceability_review.md."
                    )
                ),
            )
        )

        trace_verdict_status = "not_applicable"
        trace_verdict_details = "Gate not required for this project."
        trace_verdict_evidence: List[str] = []
        if trace_required:
            trace_verdict_status = "fail"
            trace_verdict_details = "Missing claim-traceability report JSON."
            if trace_json_rel:
                trace_json = workdir / trace_json_rel
                trace_verdict_evidence = [trace_json_rel]
                verdict, score, threshold, err = read_score_verdict(trace_json, "traceability_score")
                if verdict == "pass":
                    trace_verdict_status = "pass"
                    trace_verdict_details = f"Claim traceability passed (score={score}, threshold={threshold})."
                elif err:
                    trace_verdict_status = "fail"
                    trace_verdict_details = err
                else:
                    trace_verdict_status = "fail"
                    trace_verdict_details = f"Claim traceability failed (score={score}, threshold={threshold})."

        contracts.append(
            make_contract(
                "claim_traceability_verdict_pass",
                "claim-traceability gate verdict is pass",
                trace_required,
                trace_verdict_status,
                trace_verdict_evidence,
                trace_verdict_details,
            )
        )

        split_required = policy["main_supplement_split_required"]
        split_files = find_existing(
            workdir,
            [
                "process/main_supplement_split_plan.json",
                "process/main_supplement_split_plan.md",
                "outputs/main_supplement_split_plan.json",
                "outputs/main_supplement_split_plan.md",
            ],
        )
        split_json_rel = pick_latest_non_empty(
            workdir,
            ["process/main_supplement_split_plan.json", "outputs/main_supplement_split_plan.json"],
        )
        split_ok = (
            ("process/main_supplement_split_plan.json" in split_files or "outputs/main_supplement_split_plan.json" in split_files)
            and ("process/main_supplement_split_plan.md" in split_files or "outputs/main_supplement_split_plan.md" in split_files)
        )
        contracts.append(
            make_contract(
                "main_supplement_split_artifacts_present",
                "main/supplement split plan artifacts (JSON+MD) exist",
                split_required,
                "pass" if split_ok else ("not_applicable" if not split_required else "fail"),
                split_files,
                (
                    "Main/supplement split artifacts found."
                    if split_ok
                    else (
                        "Gate not required for this project." if not split_required else "Missing main_supplement_split_plan.json or main_supplement_split_plan.md."
                    )
                ),
            )
        )

        split_verdict_status = "not_applicable"
        split_verdict_details = "Gate not required for this project."
        split_verdict_evidence: List[str] = []
        if split_required:
            split_verdict_status = "fail"
            split_verdict_details = "Missing main/supplement split JSON report."
            if split_json_rel:
                split_json = workdir / split_json_rel
                split_verdict_evidence = [split_json_rel]
                try:
                    payload = load_json(split_json)
                    move_count = len(payload.get("sections_move_to_supplement", []))
                    applied = bool(payload.get("applied"))
                    if gate_state == "PUBLISH":
                        if move_count == 0 or applied:
                            split_verdict_status = "pass"
                            split_verdict_details = "Main/supplement split policy satisfied for publish gate."
                        else:
                            split_verdict_status = "fail"
                            split_verdict_details = "Technical sections remain unsplit; rerun split with --apply before publish gate."
                    else:
                        split_verdict_status = "pass"
                        split_verdict_details = (
                            "Split plan exists; apply before publish if technical sections were flagged."
                            if move_count > 0 and not applied
                            else "Split plan acceptable for decision gate."
                        )
                except Exception as exc:
                    split_verdict_status = "fail"
                    split_verdict_details = f"Unreadable split plan report: {exc}"

        contracts.append(
            make_contract(
                "main_supplement_split_verdict_pass",
                "main/supplement split gate verdict is pass",
                split_required,
                split_verdict_status,
                split_verdict_evidence,
                split_verdict_details,
            )
        )

        triad_required = policy["triad_review_required"]
        triad_files = find_existing(
            workdir,
            [
                "process/triad_review.json",
                "process/triad_review.md",
                "outputs/triad_review.json",
                "outputs/triad_review.md",
            ],
        )
        triad_json_rel = pick_latest_non_empty(workdir, ["process/triad_review.json", "outputs/triad_review.json"])
        triad_ok = (
            ("process/triad_review.json" in triad_files or "outputs/triad_review.json" in triad_files)
            and ("process/triad_review.md" in triad_files or "outputs/triad_review.md" in triad_files)
        )
        contracts.append(
            make_contract(
                "triad_review_artifacts_present",
                "triad review artifacts (JSON+MD) exist",
                triad_required,
                "pass" if triad_ok else ("not_applicable" if not triad_required else "fail"),
                triad_files,
                (
                    "Triad review artifacts found."
                    if triad_ok
                    else (
                        "Gate not required for this project." if not triad_required else "Missing triad_review.json or triad_review.md."
                    )
                ),
            )
        )

        triad_verdict_status = "not_applicable"
        triad_verdict_details = "Gate not required for this project."
        triad_verdict_evidence: List[str] = []
        if triad_required:
            triad_verdict_status = "fail"
            triad_verdict_details = "Missing triad review JSON report."
            if triad_json_rel:
                triad_json = workdir / triad_json_rel
                triad_verdict_evidence = [triad_json_rel]
                try:
                    payload = load_json(triad_json)
                    overall = payload.get("overall", {}) if isinstance(payload, dict) else {}
                    verdict = str(overall.get("verdict", "")).lower()
                    score = overall.get("score_pct")
                    if verdict == "pass":
                        triad_verdict_status = "pass"
                        triad_verdict_details = f"Triad review passed (score={score})."
                    else:
                        triad_verdict_status = "fail"
                        triad_verdict_details = f"Triad review failed (score={score})."
                except Exception as exc:
                    triad_verdict_status = "fail"
                    triad_verdict_details = f"Unreadable triad review report: {exc}"

        contracts.append(
            make_contract(
                "triad_review_verdict_pass",
                "triad review verdict is pass",
                triad_required,
                triad_verdict_status,
                triad_verdict_evidence,
                triad_verdict_details,
            )
        )

        internal_review = find_existing(workdir, ["advisor_summary.json", "outputs/advisor_summary.json"]) + find_globbed(
            workdir, ["prose_review_*.md", "exhibit_review_*.md", "advisor_*.md", "internal_review*.md"]
        )
        contracts.append(
            make_contract(
                "internal_review_artifacts_present",
                "internal review artifacts exist",
                True,
                "pass" if internal_review else "fail",
                internal_review,
                "Internal review artifacts found." if internal_review else "No internal review artifacts found.",
            )
        )

        external_review = find_existing(workdir, ["parallel_review_summary.json", "outputs/parallel_review_summary.json"]) + find_globbed(
            workdir, ["review_*.md", "reviewer_*.md", "external_review*.md"]
        )
        contracts.append(
            make_contract(
                "external_review_artifacts_present",
                "external review artifacts exist",
                True,
                "pass" if external_review else "fail",
                external_review,
                "External review artifacts found." if external_review else "No external review artifacts found.",
            )
        )

        decision_summary = find_existing(workdir, ["decision_summary.md", "process/decision_summary.md", "outputs/decision_summary.md"])
        contracts.append(
            make_contract(
                "decision_summary_present",
                "decision summary artifact exists",
                True,
                "pass" if decision_summary else "fail",
                decision_summary,
                "Decision summary found." if decision_summary else "No decision summary file found.",
            )
        )

    if gate_state == "PUBLISH":
        publish_artifacts = find_existing(workdir, ["manuscript/paper.pdf", "metadata.json"])
        publish_ok = len(publish_artifacts) == 2
        contracts.append(
            make_contract(
                "publish_artifacts_present",
                "manuscript/paper.pdf and metadata.json exist",
                True,
                "pass" if publish_ok else "fail",
                publish_artifacts,
                "Publish artifacts found." if publish_ok else "Missing paper PDF or metadata.",
            )
        )

        repl_docs = find_existing(
            workdir,
            ["manuscript/replication.md", "process/replication.md", "outputs/replication.md", "REPRODUCIBILITY.md"],
        )
        contracts.append(
            make_contract(
                "replication_instructions_present",
                "replication/reproducibility instructions exist",
                True,
                "pass" if repl_docs else "fail",
                repl_docs,
                "Replication instructions found." if repl_docs else "No replication instructions detected.",
            )
        )

        rev_status, rev_evidence, rev_details = evaluate_revision_traceability(workdir)
        required = rev_status != "not_applicable"
        contracts.append(
            make_contract(
                "revision_traceability_complete",
                "revision artifacts are complete when revision is required",
                required,
                rev_status,
                rev_evidence,
                rev_details,
            )
        )

    required_contracts = [c for c in contracts if c["required"]]
    required_passed = [c for c in required_contracts if c["status"] == "pass"]
    failed_required = [c for c in required_contracts if c["status"] != "pass"]

    return {
        "schema_version": 2,
        "gate_state": gate_state,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "policy": policy,
        "contracts": contracts,
        "summary": {
            "required_total": len(required_contracts),
            "required_passed": len(required_passed),
            "failed_required": len(failed_required),
            "all_required_passed": len(failed_required) == 0,
        },
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate gate contracts for a vibe-research workdir.")
    parser.add_argument("workdir", type=Path, help="Research version workdir (paper_family/vN)")
    parser.add_argument("--for-state", default="EXECUTE", choices=GATE_STATES, help="Target gate state")
    parser.add_argument("--output", type=Path, help="Output JSON report path")
    parser.add_argument("--no-strict", action="store_true", help="Always exit 0 even if required contracts fail")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        print(f"[error] Workdir does not exist: {workdir}")
        print("[hint] Provide a valid working directory with process/ folder.")
        raise SystemExit(1)

    output = args.output.resolve() if args.output else (workdir / "process" / "gate_contracts.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    report = evaluate(workdir, args.for_state)
    save_json(output, report)

    summary = report["summary"]
    print(f"Gate state: {args.for_state}")
    print(f"Required contracts passed: {summary['required_passed']}/{summary['required_total']}")
    print(f"Report: {output}")

    if not summary["all_required_passed"] and not args.no_strict:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
