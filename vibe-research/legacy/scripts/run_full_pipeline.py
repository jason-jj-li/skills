#!/usr/bin/env python3
"""
Non-interactive orchestrator for vibe-research + review pipeline.

Legacy warning:
  This orchestrator assumes the older JSON-first artifact model. Use it only
  for legacy projects or when you deliberately export structured inputs from
  the MD-first control layer.

Pipeline:
  Phase 0  search strategy
  Phase 1  PubMed retrieval
  Phase 1V retrieval quality verification
  Phase 2  screening/classification
  Phase 3  citation DB + BibTeX generation
  Writing  optional writing-gate execution
  Eval     gate-contract check + independent scoring (optional)
  Checkpoint + resume support
  Contract checks + manifest output
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from _common import TOP_TIER_HINTS, bool_policy, infer_journal_target, infer_submission_like, infer_top_tier_target, load_json, resolve_gate_policy, save_json

def run_cmd(cmd: List[str]) -> None:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)

def infer_include_keywords(topic: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", topic.lower())
    seen = set()
    out = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= 8:
            break
    return out

def count_bib_entries(bib_file: Path) -> int:
    return bib_file.read_text(encoding="utf-8").count("@article{")

def read_score_verdict(report_path: Path, block: str) -> Dict[str, object]:
    if not report_path.exists() or report_path.stat().st_size == 0:
        return {
            "status": "missing",
            "verdict": "missing",
            "score_pct": None,
            "pass_threshold_score": None,
            "error": f"Missing report: {report_path}",
        }
    try:
        payload = load_json(report_path)
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

def load_checkpoint(path: Path, topic: str, workdir: Path) -> Dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        payload.setdefault("phases", {})
        payload["last_updated"] = datetime.now().isoformat()
        return payload
    now = datetime.now().isoformat()
    payload = {
        "schema_version": 1,
        "topic": topic,
        "workdir": str(workdir),
        "started_at": now,
        "last_updated": now,
        "phases": {},
    }
    save_json(path, payload)
    return payload

def mark_phase(checkpoint: Dict, checkpoint_file: Path, phase: str, status: str = "done", **kwargs: str) -> None:
    checkpoint["phases"][phase] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        **kwargs,
    }
    checkpoint["last_updated"] = datetime.now().isoformat()
    save_json(checkpoint_file, checkpoint)

def should_skip_phase(
    resume: bool,
    checkpoint: Dict,
    phase: str,
    required_outputs: Optional[List[Path]] = None,
) -> bool:
    if not resume:
        return False
    phase_state = checkpoint.get("phases", {}).get(phase, {})
    if phase_state.get("status") != "done":
        return False
    outputs = required_outputs or []
    if outputs and not all(p.exists() for p in outputs):
        return False
    print(f"\n↻ Resume mode: skipping completed phase `{phase}`")
    return True

def save_partial_manifest(manifest: Dict, outputs_dir: Path, stop_after: str) -> Path:
    payload = dict(manifest)
    payload["stopped_after"] = stop_after
    payload["finished_at"] = datetime.now().isoformat()
    out = outputs_dir / "manifest.partial.json"
    save_json(out, payload)
    return out

def resolve_path(workdir: Path, path: Path) -> Path:
    return path if path.is_absolute() else (workdir / path)

def run_target_gate_preflight(
    workdir: Path,
    local_scripts: Path,
    checkpoint: Dict,
    checkpoint_file: Path,
    manifest: Dict,
    resume: bool,
    target_gate_required: bool,
    soft_fail: bool,
) -> None:
    if not target_gate_required:
        manifest["steps"].append({"step": "target_gate", "status": "not_required"})
        return

    target_gate_json = workdir / "process" / "target_gate.json"
    target_gate_md = workdir / "process" / "target_gate.md"
    if should_skip_phase(resume, checkpoint, "target_gate", [target_gate_json, target_gate_md]):
        manifest["steps"].append({"step": "target_gate", "status": "resumed", "output": str(target_gate_json)})
        return

    cmd = [sys.executable, str(local_scripts / "build_target_gate.py"), str(workdir)]
    if soft_fail:
        cmd.append("--no-strict")
    run_cmd(cmd)
    manifest["steps"].append({"step": "target_gate", "status": "done", "output": str(target_gate_json)})
    mark_phase(checkpoint, checkpoint_file, "target_gate", status="done", output=str(target_gate_json))

def run_writing_gates(
    workdir: Path,
    local_scripts: Path,
    gate_state: str,
    manuscript_path: Path,
    bib_path: Path,
    supplement_path: Path,
    gate_policy: Dict[str, bool],
    soft_fail: bool,
    apply_supplement_split: bool,
) -> List[Dict]:
    steps: List[Dict] = []

    if not manuscript_path.exists():
        message = f"Manuscript not found: {manuscript_path}"
        if soft_fail:
            print(f"\n⚠ {message}; skipping writing gates because --gate-soft-fail is enabled.")
            steps.append({"step": "writing_gates", "status": "skipped", "reason": message})
            return steps
        raise FileNotFoundError(message)

    style_cmd = [
        sys.executable,
        str(local_scripts / "build_style_gate.py"),
        str(workdir),
        "--manuscript",
        str(manuscript_path),
    ]
    run_cmd(style_cmd)
    style_report = workdir / "process" / "style_gate_report.json"
    style_verdict = read_score_verdict(style_report, "style_score")
    style_step = {"step": "style_gate", "status": "done", **style_verdict}
    steps.append(style_step)
    if style_verdict["verdict"] != "pass" and not soft_fail:
        raise SystemExit(f"Style gate failed: {style_verdict}")

    prose_cmd = [
        sys.executable,
        str(local_scripts / "evaluate_prose_quality.py"),
        str(workdir),
        "--manuscript",
        str(manuscript_path),
    ]
    run_cmd(prose_cmd)
    prose_report = workdir / "process" / "prose_quality_review.json"
    prose_verdict = read_score_verdict(prose_report, "prose_score")
    prose_step = {"step": "prose_quality_gate", "status": "done", **prose_verdict}
    steps.append(prose_step)
    if prose_verdict["verdict"] != "pass" and not soft_fail:
        raise SystemExit(f"Prose quality gate failed: {prose_verdict}")

    if gate_policy["content_focus_gate_required"]:
        content_cmd = [
            sys.executable,
            str(local_scripts / "evaluate_content_focus.py"),
            str(workdir),
            "--manuscript",
            str(manuscript_path),
        ]
        if soft_fail:
            content_cmd.append("--no-strict")
        run_cmd(content_cmd)
        content_report = workdir / "process" / "content_focus_review.json"
        content_verdict = read_score_verdict(content_report, "content_score")
        steps.append({"step": "content_focus_gate", "status": "done", **content_verdict})
        if content_verdict["verdict"] != "pass" and not soft_fail:
            raise SystemExit(f"Content-focus gate failed: {content_verdict}")
    else:
        steps.append({"step": "content_focus_gate", "status": "not_required"})

    if gate_policy["field_progress_gate_required"]:
        field_cmd = [
            sys.executable,
            str(local_scripts / "evaluate_field_progress.py"),
            str(workdir),
            "--manuscript",
            str(manuscript_path),
        ]
        if soft_fail:
            field_cmd.append("--no-strict")
        run_cmd(field_cmd)
        field_report = workdir / "process" / "field_progress_review.json"
        field_verdict = read_score_verdict(field_report, "field_progress_score")
        steps.append({"step": "field_progress_gate", "status": "done", **field_verdict})
        if field_verdict["verdict"] != "pass" and not soft_fail:
            raise SystemExit(f"Field-progress gate failed: {field_verdict}")
    else:
        steps.append({"step": "field_progress_gate", "status": "not_required"})

    if gate_policy["citation_architecture_gate_required"]:
        if not bib_path.exists():
            message = f"Bibliography not found: {bib_path}"
            if soft_fail:
                print(f"\n⚠ {message}; skipping citation architecture gate.")
                steps.append({"step": "citation_architecture_gate", "status": "skipped", "reason": message})
            else:
                raise FileNotFoundError(message)
        else:
            citation_cmd = [
                sys.executable,
                str(local_scripts / "evaluate_citation_architecture.py"),
                str(workdir),
                "--manuscript",
                str(manuscript_path),
                "--bib",
                str(bib_path),
            ]
            if soft_fail:
                citation_cmd.append("--no-strict")
            run_cmd(citation_cmd)
            citation_report = workdir / "process" / "citation_architecture_review.json"
            citation_verdict = read_score_verdict(citation_report, "citation_score")
            steps.append({"step": "citation_architecture_gate", "status": "done", **citation_verdict})
            if citation_verdict["verdict"] != "pass" and not soft_fail:
                raise SystemExit(f"Citation architecture gate failed: {citation_verdict}")
    else:
        steps.append({"step": "citation_architecture_gate", "status": "not_required"})

    if gate_policy["claim_traceability_gate_required"]:
        traceability_cmd = [
            sys.executable,
            str(local_scripts / "evaluate_claim_traceability.py"),
            str(workdir),
            "--manuscript",
            str(manuscript_path),
        ]
        if soft_fail:
            traceability_cmd.append("--no-strict")
        run_cmd(traceability_cmd)
        traceability_report = workdir / "process" / "claim_traceability_review.json"
        traceability_verdict = read_score_verdict(traceability_report, "traceability_score")
        steps.append({"step": "claim_traceability_gate", "status": "done", **traceability_verdict})
        if traceability_verdict["verdict"] != "pass" and not soft_fail:
            raise SystemExit(f"Claim-traceability gate failed: {traceability_verdict}")
    else:
        steps.append({"step": "claim_traceability_gate", "status": "not_required"})

    if gate_policy["main_supplement_split_required"]:
        split_cmd = [
            sys.executable,
            str(local_scripts / "split_main_supplement.py"),
            str(workdir),
            "--manuscript",
            str(manuscript_path),
            "--supplement",
            str(supplement_path),
        ]
        if apply_supplement_split:
            split_cmd.append("--apply")
        run_cmd(split_cmd)
        split_plan = workdir / "process" / "main_supplement_split_plan.json"
        split_move_count = 0
        split_applied = False
        if split_plan.exists() and split_plan.stat().st_size > 0:
            try:
                split_payload = load_json(split_plan)
                split_move_count = len(split_payload.get("sections_move_to_supplement", []))
                split_applied = bool(split_payload.get("applied"))
            except Exception:
                split_move_count = 0
                split_applied = False
        split_verdict = "pass"
        split_detail = "Split gate passed."
        if gate_state == "PUBLISH" and split_move_count > 0 and not split_applied:
            split_verdict = "fail"
            split_detail = "Technical sections remain unsplit; rerun with --apply-supplement-split."
        steps.append(
            {
                "step": "main_supplement_split_gate",
                "status": "done",
                "applied": bool(apply_supplement_split),
                "supplement": str(supplement_path),
                "verdict": split_verdict,
                "details": split_detail,
                "move_count": split_move_count,
                "applied_detected": split_applied,
            }
        )
        if split_verdict != "pass" and not soft_fail:
            raise SystemExit(split_detail)
    else:
        steps.append({"step": "main_supplement_split_gate", "status": "not_required"})

    if gate_policy["triad_review_required"] and gate_state in {"DECISION", "PUBLISH"}:
        triad_cmd = [sys.executable, str(local_scripts / "run_triad_review.py"), str(workdir)]
        if soft_fail:
            triad_cmd.append("--no-strict")
        run_cmd(triad_cmd)
        triad_report = workdir / "process" / "triad_review.json"
        triad_verdict = read_score_verdict(triad_report, "overall")
        if triad_verdict["status"] == "invalid":
            # run_triad_review stores verdict in `overall`; map manually if needed
            if triad_report.exists() and triad_report.stat().st_size > 0:
                try:
                    triad_payload = load_json(triad_report)
                    triad_overall = triad_payload.get("overall", {})
                    triad_verdict = {
                        "status": "ok",
                        "verdict": str(triad_overall.get("verdict", "invalid")).lower(),
                        "score_pct": triad_overall.get("score_pct"),
                        "pass_threshold_score": triad_payload.get("threshold_score"),
                        "error": "",
                    }
                except Exception as exc:
                    triad_verdict = {
                        "status": "invalid",
                        "verdict": "invalid",
                        "score_pct": None,
                        "pass_threshold_score": None,
                        "error": f"Unreadable triad review report: {exc}",
                    }
        steps.append({"step": "triad_review_gate", "status": "done", **triad_verdict})
        if triad_verdict["verdict"] != "pass" and not soft_fail:
            raise SystemExit(f"Triad review gate failed: {triad_verdict}")
    else:
        steps.append({"step": "triad_review_gate", "status": "not_required"})

    return steps

def main() -> None:
    parser = argparse.ArgumentParser(description="Run non-interactive vibe-research/review pipeline with contracts.")
    parser.add_argument("topic", help="Research topic string")
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path("vibe_research_runs") / datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Output working directory",
    )
    parser.add_argument("--years", default="2020:2026", help="Publication year range for Phase 0")
    parser.add_argument("--pico-json", type=Path, help="PICO analysis JSON for Phase 0 generation")
    parser.add_argument("--search-mapping", type=Path, help="Prebuilt search_mapping.json")
    parser.add_argument("--api-key", help="Optional NCBI API key")
    parser.add_argument("--profile", choices=["default", "strict"], default="strict")
    parser.add_argument("--include", nargs="+", help="Include keywords for screening")
    parser.add_argument("--exclude", nargs="+", help="Exclude keywords for screening")
    parser.add_argument("--limit", type=int, help="Limit screened results")
    parser.add_argument("--skip-retrieval", action="store_true", help="Skip Phase 1 retrieval")
    parser.add_argument("--phase1-file", type=Path, help="Existing phase1 JSON if skipping retrieval")
    parser.add_argument("--skills-root", type=Path, help="Path to skills repo root")
    parser.add_argument("--resume", action="store_true", help="Resume from completed phases using checkpoint")
    parser.add_argument("--checkpoint-file", type=Path, help="Checkpoint JSON path")
    parser.add_argument(
        "--mode-decision",
        type=Path,
        default=Path("process/mode_decision.json"),
        help="Routing decision JSON; if present with go=false, pipeline stops unless overridden.",
    )
    parser.add_argument(
        "--allow-go-false",
        action="store_true",
        help="Allow execution even when routing decision says go=false (manual override).",
    )
    parser.add_argument(
        "--allow-missing-exemplar",
        action="store_true",
        help="Allow execution for top-tier targets even when exemplar benchmark artifacts are missing.",
    )
    parser.add_argument(
        "--stop-after",
        choices=["phase0", "phase1", "phase1_verify", "phase2", "phase3", "contracts", "writing_gates", "eval"],
        help="Stop pipeline after the specified phase",
    )
    parser.add_argument("--run-eval", action="store_true", help="Run gate contracts + independent evaluation at end")
    parser.add_argument(
        "--gate-state",
        choices=["EXECUTE", "DECISION", "PUBLISH"],
        default="EXECUTE",
        help="Gate level for legacy/scripts/check_gate_contracts.py",
    )
    parser.add_argument("--gate-soft-fail", action="store_true", help="Do not fail pipeline on gate contract failures")
    parser.add_argument("--eval-fail-below", choices=["A", "B", "C", "D", "F"], help="Fail if eval grade is below threshold")
    parser.add_argument("--run-writing-gates", action="store_true", help="Run writing gates after phase 3 even without --run-eval")
    parser.add_argument(
        "--run-writing-superloop",
        action="store_true",
        help="Run iterative writing superloop (multi-round gate convergence) instead of one-pass writing gates.",
    )
    parser.add_argument("--writing-max-rounds", type=int, help="Override writing superloop max rounds")
    parser.add_argument("--skip-writing-gates", action="store_true", help="Skip writing gates even for DECISION/PUBLISH evaluation")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"), help="Manuscript path for writing gates")
    parser.add_argument(
        "--supplement",
        type=Path,
        default=Path("manuscript/supplement_methods_appendix.qmd"),
        help="Supplement path for split gate",
    )
    parser.add_argument("--apply-supplement-split", action="store_true", help="Apply split plan by moving technical sections to supplement")
    args = parser.parse_args()

    if not args.search_mapping and not args.pico_json:
        parser.error("Provide either --search-mapping or --pico-json.")
    if args.skip_retrieval and not args.phase1_file:
        parser.error("--skip-retrieval requires --phase1-file.")
    if args.stop_after == "eval" and not args.run_eval:
        parser.error("--stop-after eval requires --run-eval.")
    if args.run_writing_gates and args.skip_writing_gates:
        parser.error("--run-writing-gates cannot be combined with --skip-writing-gates.")
    if args.run_writing_superloop and args.skip_writing_gates:
        parser.error("--run-writing-superloop cannot be combined with --skip-writing-gates.")
    if args.run_writing_superloop and args.run_writing_gates:
        parser.error("Use either --run-writing-gates or --run-writing-superloop, not both.")
    if args.writing_max_rounds is not None and args.writing_max_rounds <= 0:
        parser.error("--writing-max-rounds must be > 0.")

    script_file = Path(__file__).resolve()
    local_scripts = script_file.parent
    skills_root = args.skills_root or script_file.parents[2]
    review_scripts = skills_root / "review" / "scripts"
    if not review_scripts.exists():
        parser.error(f"Cannot find review scripts: {review_scripts}")

    workdir = args.workdir.resolve()
    process_dir = workdir / "process"
    outputs_dir = workdir / "outputs"
    logs_dir = workdir / "logs"
    for p in [process_dir, outputs_dir, logs_dir]:
        p.mkdir(parents=True, exist_ok=True)

    checkpoint_file = args.checkpoint_file.resolve() if args.checkpoint_file else (process_dir / "pipeline_checkpoint.json")
    checkpoint = load_checkpoint(checkpoint_file, args.topic, workdir)

    manifest = {
        "topic": args.topic,
        "started_at": datetime.now().isoformat(),
        "profile": args.profile,
        "workdir": str(workdir),
        "checkpoint_file": str(checkpoint_file),
        "steps": [],
    }

    search_mapping = process_dir / "search_mapping.json"
    phase1_file = process_dir / "phase1_pubmed_results.json"
    phase2_file = process_dir / "phase2_screened.json"
    citation_db = process_dir / "citation_db.json"
    references_bib = process_dir / "references.bib"

    contract_file = workdir / "process" / "project_contract.json"
    contract: Dict = load_json(contract_file) if contract_file.exists() else {}
    gate_policy = resolve_gate_policy(contract)
    manifest["gate_policy"] = gate_policy

    run_target_gate_preflight(
        workdir=workdir,
        local_scripts=local_scripts,
        checkpoint=checkpoint,
        checkpoint_file=checkpoint_file,
        manifest=manifest,
        resume=args.resume,
        target_gate_required=gate_policy["target_gate_required"],
        soft_fail=args.gate_soft_fail,
    )

    if args.mode_decision.is_absolute():
        mode_decision_file = args.mode_decision.resolve()
    else:
        local_mode_decision = args.mode_decision.resolve()
        workdir_mode_decision = (workdir / args.mode_decision).resolve()
        mode_decision_file = workdir_mode_decision if workdir_mode_decision.exists() else local_mode_decision

    if mode_decision_file.exists() and not args.allow_go_false:
        mode_decision = load_json(mode_decision_file)
        decision = mode_decision.get("decision", {})
        go = bool(decision.get("go", True))
        if not go:
            reason = decision.get("reason", [])
            reason_text = " | ".join(str(r) for r in reason) if isinstance(reason, list) else str(reason)
            selected_mode = decision.get("selected_mode", "unknown")
            manifest["steps"].append(
                {
                    "step": "route_gate",
                    "status": "blocked",
                    "mode_decision": str(mode_decision_file),
                    "selected_mode": selected_mode,
                    "reason": reason_text,
                }
            )
            mark_phase(
                checkpoint,
                checkpoint_file,
                "route_gate",
                status="blocked",
                selected_mode=selected_mode,
                reason=reason_text,
            )
            partial = save_partial_manifest(manifest, outputs_dir, "route_gate")
            print("\n🚫 Routing gate blocked execution (go=false).")
            print(f"Mode decision: {mode_decision_file}")
            print(f"Reason: {reason_text}")
            print(f"Partial manifest: {partial}")
            print("Use --allow-go-false only when you intentionally want exploratory execution.")
            sys.exit(2)

    if contract and not args.allow_missing_exemplar and infer_top_tier_target(contract):
        exemplar_json = workdir / "process" / "exemplar_benchmark.json"
        exemplar_md = workdir / "process" / "exemplar_benchmark.md"
        if not exemplar_json.exists() and not exemplar_md.exists():
            manifest["steps"].append(
                {
                    "step": "exemplar_gate",
                    "status": "blocked",
                    "reason": "top_tier_target_requires_exemplar_benchmark",
                }
            )
            mark_phase(
                checkpoint,
                checkpoint_file,
                "exemplar_gate",
                status="blocked",
                reason="top_tier_target_requires_exemplar_benchmark",
            )
            partial = save_partial_manifest(manifest, outputs_dir, "exemplar_gate")
            print("\n🚫 Exemplar gate blocked execution (top-tier target, missing exemplar benchmark).")
            print("Expected one of: process/exemplar_benchmark.json, process/exemplar_benchmark.md")
            print(f"Partial manifest: {partial}")
            print("Use --allow-missing-exemplar only when you intentionally bypass this gate.")
            sys.exit(3)

    if should_skip_phase(args.resume, checkpoint, "phase0", [search_mapping]):
        manifest["steps"].append({"step": "phase0", "mode": "resumed", "output": str(search_mapping)})
    else:
        if args.search_mapping:
            shutil.copy2(args.search_mapping, search_mapping)
            mode = "copied"
        else:
            cmd = [
                sys.executable,
                str(review_scripts / "generate_search_strategy.py"),
                args.topic,
                "--json",
                str(args.pico_json),
                "--years",
                args.years,
                "--output",
                str(search_mapping),
            ]
            run_cmd(cmd)
            mode = "generated"
        manifest["steps"].append({"step": "phase0", "mode": mode, "output": str(search_mapping)})
        mark_phase(checkpoint, checkpoint_file, "phase0", output=str(search_mapping), mode=mode)
    if args.stop_after == "phase0":
        partial = save_partial_manifest(manifest, outputs_dir, "phase0")
        print(f"\n⏹ Stopped after phase0. Partial manifest: {partial}")
        return

    if should_skip_phase(args.resume, checkpoint, "phase1", [phase1_file]):
        manifest["steps"].append({"step": "phase1", "mode": "resumed", "output": str(phase1_file)})
    else:
        if args.skip_retrieval:
            shutil.copy2(args.phase1_file, phase1_file)
            mode = "copied"
        else:
            cmd = [
                sys.executable,
                str(review_scripts / "pubmed_batch_retrieval.py"),
                str(search_mapping),
                "-o",
                str(phase1_file),
            ]
            if args.api_key:
                cmd.extend(["--api-key", args.api_key])
            run_cmd(cmd)
            mode = "retrieved"
        manifest["steps"].append({"step": "phase1", "mode": mode, "output": str(phase1_file)})
        mark_phase(checkpoint, checkpoint_file, "phase1", output=str(phase1_file), mode=mode)
    if args.stop_after == "phase1":
        partial = save_partial_manifest(manifest, outputs_dir, "phase1")
        print(f"\n⏹ Stopped after phase1. Partial manifest: {partial}")
        return

    if should_skip_phase(args.resume, checkpoint, "phase1_verify"):
        manifest["steps"].append({"step": "phase1_verify", "status": "resumed"})
    else:
        run_cmd([sys.executable, str(review_scripts / "verify_phase1_data.py"), str(phase1_file)])
        manifest["steps"].append({"step": "phase1_verify", "status": "pass"})
        mark_phase(checkpoint, checkpoint_file, "phase1_verify", status="done")
    if args.stop_after == "phase1_verify":
        partial = save_partial_manifest(manifest, outputs_dir, "phase1_verify")
        print(f"\n⏹ Stopped after phase1_verify. Partial manifest: {partial}")
        return

    include_kw = args.include or (infer_include_keywords(args.topic) if args.profile == "strict" else None)
    if should_skip_phase(args.resume, checkpoint, "phase2", [phase2_file]):
        manifest["steps"].append(
            {"step": "phase2", "output": str(phase2_file), "include": include_kw, "exclude": args.exclude, "mode": "resumed"}
        )
    else:
        cmd = [
            sys.executable,
            str(review_scripts / "screen_papers.py"),
            str(phase1_file),
            "--profile",
            args.profile,
            "--sort-by",
            "evidence",
            "-o",
            str(phase2_file),
        ]
        if include_kw:
            cmd.extend(["--include", *include_kw])
        if args.exclude:
            cmd.extend(["--exclude", *args.exclude])
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])
        run_cmd(cmd)
        manifest["steps"].append({"step": "phase2", "output": str(phase2_file), "include": include_kw, "exclude": args.exclude})
        mark_phase(checkpoint, checkpoint_file, "phase2", output=str(phase2_file))
    if args.stop_after == "phase2":
        partial = save_partial_manifest(manifest, outputs_dir, "phase2")
        print(f"\n⏹ Stopped after phase2. Partial manifest: {partial}")
        return

    if should_skip_phase(args.resume, checkpoint, "phase3", [citation_db, references_bib]):
        manifest["steps"].append({"step": "phase3", "citation_db": str(citation_db), "bibtex": str(references_bib), "mode": "resumed"})
    else:
        run_cmd([sys.executable, str(review_scripts / "build_citation_db.py"), str(phase2_file), "-o", str(citation_db)])
        run_cmd([sys.executable, str(review_scripts / "generate_bibtex.py"), str(phase2_file), "--output", str(references_bib)])
        manifest["steps"].append({"step": "phase3", "citation_db": str(citation_db), "bibtex": str(references_bib)})
        mark_phase(checkpoint, checkpoint_file, "phase3", citation_db=str(citation_db), bibtex=str(references_bib))
    if args.stop_after == "phase3":
        partial = save_partial_manifest(manifest, outputs_dir, "phase3")
        print(f"\n⏹ Stopped after phase3. Partial manifest: {partial}")
        return

    phase1_data = load_json(phase1_file)
    phase2_data = load_json(phase2_file)
    citation_data = load_json(citation_db)

    c_phase1 = len(phase1_data.get("articles", []))
    c_phase2 = len(phase2_data.get("articles", []))
    c_citation = int(citation_data.get("total_citations", 0))
    c_bib = count_bib_entries(references_bib)

    checks = {
        "phase2_not_exceed_phase1": c_phase2 <= c_phase1,
        "citation_count_matches_phase2": c_citation == c_phase2,
        "bib_count_matches_citation_db": c_bib == c_citation,
    }
    manifest["contracts"] = checks
    manifest["counts"] = {
        "phase1_articles": c_phase1,
        "phase2_articles": c_phase2,
        "citation_entries": c_citation,
        "bib_entries": c_bib,
    }
    mark_phase(
        checkpoint,
        checkpoint_file,
        "contracts",
        status="done",
        phase1_articles=str(c_phase1),
        phase2_articles=str(c_phase2),
        citation_entries=str(c_citation),
        bib_entries=str(c_bib),
    )

    if args.stop_after == "contracts":
        partial = save_partial_manifest(manifest, outputs_dir, "contracts")
        print(f"\n⏹ Stopped after contracts. Partial manifest: {partial}")
        return

    manifest["finished_at"] = datetime.now().isoformat()
    manifest_file = outputs_dir / "manifest.json"
    save_json(manifest_file, manifest)

    failed = [k for k, v in checks.items() if not v]
    if failed:
        print("\n❌ Contract checks failed:")
        for name in failed:
            print(f"  - {name}")
        print(f"Manifest: {manifest_file}")
        sys.exit(1)

    print("\n✅ Pipeline completed with all contract checks passing.")
    print(f"Manifest: {manifest_file}")
    print(f"Checkpoint: {checkpoint_file}")

    auto_writing = args.run_eval and args.gate_state in {"DECISION", "PUBLISH"} and gate_policy["submission_like"]
    auto_superloop = auto_writing and gate_policy.get("writing_superloop_required", False)
    should_run_superloop = (args.run_writing_superloop or auto_superloop) and not args.skip_writing_gates
    should_run_writing = ((args.run_writing_gates or auto_writing) and not args.skip_writing_gates) and not should_run_superloop
    manuscript_path = resolve_path(workdir, args.manuscript)
    supplement_path = resolve_path(workdir, args.supplement)
    bib_path = references_bib

    if should_run_superloop:
        superloop_cmd = [
            sys.executable,
            str(local_scripts / "run_writing_superloop.py"),
            str(workdir),
            "--manuscript",
            str(manuscript_path),
            "--bib",
            str(bib_path),
            "--supplement",
            str(supplement_path),
            "--gate-state",
            args.gate_state if args.gate_state in {"DECISION", "PUBLISH"} else "DECISION",
        ]
        if args.writing_max_rounds:
            superloop_cmd.extend(["--max-rounds", str(args.writing_max_rounds)])
        if args.apply_supplement_split:
            superloop_cmd.append("--apply-supplement-split")
        if args.gate_soft_fail:
            superloop_cmd.append("--no-strict")
        run_cmd(superloop_cmd)

        superloop_report = workdir / "process" / "writing_superloop_report.json"
        superloop_status = {
            "status": "missing",
            "verdict": "missing",
            "rounds_completed": None,
            "max_rounds": None,
            "error": f"Missing report: {superloop_report}",
        }
        if superloop_report.exists() and superloop_report.stat().st_size > 0:
            try:
                payload = load_json(superloop_report)
                superloop_status = {
                    "status": "ok",
                    "verdict": str(payload.get("verdict", "invalid")).lower(),
                    "rounds_completed": payload.get("rounds_completed"),
                    "max_rounds": payload.get("max_rounds"),
                    "error": "",
                }
            except Exception as exc:
                superloop_status = {
                    "status": "invalid",
                    "verdict": "invalid",
                    "rounds_completed": None,
                    "max_rounds": None,
                    "error": f"Unreadable report JSON: {exc}",
                }

        manifest["writing_gates"] = {
            "enabled": True,
            "mode": "superloop",
            "manuscript": str(manuscript_path),
            "supplement": str(supplement_path),
            "report": str(superloop_report),
            "status": superloop_status,
        }
        save_json(manifest_file, manifest)
        mark_phase(checkpoint, checkpoint_file, "writing_gates", status="done", gate_state=args.gate_state, mode="superloop")

        if superloop_status.get("verdict") != "pass" and not args.gate_soft_fail:
            raise SystemExit(f"Writing superloop failed: {superloop_status}")

    elif should_run_writing:
        writing_steps = run_writing_gates(
            workdir=workdir,
            local_scripts=local_scripts,
            gate_state=args.gate_state,
            manuscript_path=manuscript_path,
            bib_path=bib_path,
            supplement_path=supplement_path,
            gate_policy=gate_policy,
            soft_fail=args.gate_soft_fail,
            apply_supplement_split=args.apply_supplement_split,
        )
        manifest["writing_gates"] = {
            "enabled": True,
            "mode": "single_pass",
            "manuscript": str(manuscript_path),
            "supplement": str(supplement_path),
            "steps": writing_steps,
        }
        save_json(manifest_file, manifest)
        mark_phase(checkpoint, checkpoint_file, "writing_gates", status="done", gate_state=args.gate_state)

    if args.stop_after == "writing_gates":
        if not (should_run_writing or should_run_superloop):
            raise SystemExit("--stop-after writing_gates requested, but writing gates were not scheduled.")
        partial = save_partial_manifest(manifest, outputs_dir, "writing_gates")
        print(f"\n⏹ Stopped after writing_gates. Partial manifest: {partial}")
        return

    if args.run_eval:
        gate_report = process_dir / "gate_contracts.json"
        eval_report = outputs_dir / "eval_report.json"

        gate_cmd = [
            sys.executable,
            str(local_scripts / "check_gate_contracts.py"),
            str(workdir),
            "--for-state",
            args.gate_state,
            "--output",
            str(gate_report),
        ]
        if args.gate_soft_fail:
            gate_cmd.append("--no-strict")
        run_cmd(gate_cmd)

        eval_cmd = [
            sys.executable,
            str(local_scripts / "evaluate_research_run.py"),
            str(workdir),
            "--manifest",
            str(manifest_file),
            "--output",
            str(eval_report),
        ]
        if gate_report.exists():
            eval_cmd.extend(["--gate-report", str(gate_report)])
        if args.eval_fail_below:
            eval_cmd.extend(["--fail-below", args.eval_fail_below])
        run_cmd(eval_cmd)

        manifest["evaluation"] = {
            "gate_state": args.gate_state,
            "gate_report": str(gate_report),
            "eval_report": str(eval_report),
        }
        save_json(manifest_file, manifest)
        mark_phase(checkpoint, checkpoint_file, "eval", status="done", gate_state=args.gate_state)

        print("\n✅ Evaluation stage completed.")
        print(f"Gate report: {gate_report}")
        print(f"Eval report: {eval_report}")
        if args.stop_after == "eval":
            print("\n⏹ Stopped after eval.")
            return

if __name__ == "__main__":
    main()
