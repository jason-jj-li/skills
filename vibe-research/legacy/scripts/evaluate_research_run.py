#!/usr/bin/env python3
"""
Independent evaluation pass for vibe-research artifacts.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from _common import load_json, save_json, utc_now

GRADE_TO_SCORE = {"A": 90.0, "B": 80.0, "C": 70.0, "D": 60.0, "F": 0.0}

def ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator <= 0:
        return None
    return numerator / denominator

def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))

def score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"

def evaluate(workdir: Path, manifest_file: Path, gate_report: Optional[Path]) -> Dict:
    manifest = load_json(manifest_file)
    counts = manifest.get("counts", {})
    contracts = manifest.get("contracts", {})

    phase1 = float(counts.get("phase1_articles", 0))
    phase2 = float(counts.get("phase2_articles", 0))
    citation_entries = float(counts.get("citation_entries", 0))
    bib_entries = float(counts.get("bib_entries", 0))

    retrieval_yield = ratio(phase2, phase1)
    citation_coverage = ratio(citation_entries, phase2)
    bib_sync = ratio(bib_entries, citation_entries)

    contract_total = len(contracts) if isinstance(contracts, dict) else 0
    contract_passed = sum(1 for v in contracts.values() if bool(v)) if isinstance(contracts, dict) else 0
    pipeline_contract_pass_rate = ratio(contract_passed, contract_total)

    gate_contract_pass_rate = None
    gate_required_total = 0
    gate_required_passed = 0
    gate_report_path = None
    if gate_report and gate_report.exists():
        gate_data = load_json(gate_report)
        gate_summary = gate_data.get("summary", {})
        gate_required_total = int(gate_summary.get("required_total", 0))
        gate_required_passed = int(gate_summary.get("required_passed", 0))
        gate_contract_pass_rate = ratio(float(gate_required_passed), float(gate_required_total))
        gate_report_path = str(gate_report)

    required_artifacts = [
        workdir / "process" / "search_mapping.json",
        workdir / "process" / "phase1_pubmed_results.json",
        workdir / "process" / "phase2_screened.json",
        workdir / "process" / "citation_db.json",
        workdir / "process" / "references.bib",
        manifest_file,
    ]
    artifact_present = sum(1 for p in required_artifacts if p.exists())
    artifact_completeness = ratio(float(artifact_present), float(len(required_artifacts)))

    warnings = []
    score = 100.0

    if retrieval_yield is None:
        score -= 20
        warnings.append("retrieval_yield unavailable (phase1_articles is zero)")
    elif retrieval_yield < 0.03 or retrieval_yield > 1.0:
        score -= 15
        warnings.append(f"retrieval_yield out of expected range: {retrieval_yield:.3f}")

    if citation_coverage is None:
        score -= 20
        warnings.append("citation_coverage unavailable (phase2_articles is zero)")
    else:
        score -= 30 * (1 - clamp(citation_coverage, 0.0, 1.0))
        if citation_coverage < 1.0:
            warnings.append(f"citation_coverage below 1.0: {citation_coverage:.3f}")

    if bib_sync is None:
        score -= 10
        warnings.append("bib_sync unavailable (citation_entries is zero)")
    else:
        score -= 30 * (1 - clamp(bib_sync, 0.0, 1.0))
        if bib_sync < 1.0:
            warnings.append(f"bib_sync below 1.0: {bib_sync:.3f}")

    if pipeline_contract_pass_rate is None:
        score -= 25
        warnings.append("pipeline contracts missing in manifest")
    else:
        score -= 35 * (1 - clamp(pipeline_contract_pass_rate, 0.0, 1.0))
        if pipeline_contract_pass_rate < 1.0:
            warnings.append(f"pipeline_contract_pass_rate below 1.0: {pipeline_contract_pass_rate:.3f}")

    if gate_contract_pass_rate is not None:
        score -= 35 * (1 - clamp(gate_contract_pass_rate, 0.0, 1.0))
        if gate_contract_pass_rate < 1.0:
            warnings.append(f"gate_contract_pass_rate below 1.0: {gate_contract_pass_rate:.3f}")

    if artifact_completeness is not None:
        score -= 20 * (1 - clamp(artifact_completeness, 0.0, 1.0))
        if artifact_completeness < 1.0:
            warnings.append(f"artifact_completeness below 1.0: {artifact_completeness:.3f}")

    score = clamp(score, 0.0, 100.0)
    grade = score_to_grade(score)

    ready_for_next_gate = (
        (pipeline_contract_pass_rate == 1.0)
        and (gate_contract_pass_rate is None or gate_contract_pass_rate == 1.0)
        and grade in {"A", "B"}
    )

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "workdir": str(workdir),
        "manifest_file": str(manifest_file),
        "gate_report_file": gate_report_path,
        "metrics": {
            "retrieval_yield": retrieval_yield,
            "citation_coverage": citation_coverage,
            "bib_sync": bib_sync,
            "pipeline_contract_pass_rate": pipeline_contract_pass_rate,
            "gate_contract_pass_rate": gate_contract_pass_rate,
            "artifact_completeness": artifact_completeness,
        },
        "counts": {
            "phase1_articles": phase1,
            "phase2_articles": phase2,
            "citation_entries": citation_entries,
            "bib_entries": bib_entries,
            "pipeline_contract_total": contract_total,
            "pipeline_contract_passed": contract_passed,
            "gate_required_total": gate_required_total,
            "gate_required_passed": gate_required_passed,
            "artifact_present": artifact_present,
            "artifact_required": len(required_artifacts),
        },
        "score": {
            "value": score,
            "grade": grade,
            "ready_for_next_gate": ready_for_next_gate,
        },
        "warnings": warnings,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Run independent evaluation for vibe-research outputs.")
    parser.add_argument("workdir", type=Path, help="Research version workdir (paper_family/vN)")
    parser.add_argument("--manifest", type=Path, help="Manifest JSON (default: outputs/manifest.json)")
    parser.add_argument("--gate-report", type=Path, help="Gate contracts report JSON (optional)")
    parser.add_argument("--output", type=Path, help="Output report path (default: outputs/eval_report.json)")
    parser.add_argument("--fail-below", choices=list(GRADE_TO_SCORE.keys()), help="Fail (exit 1) if grade below threshold")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    manifest_file = args.manifest.resolve() if args.manifest else (workdir / "outputs" / "manifest.json")
    if not manifest_file.exists():
        print(f"[error] Missing manifest file: {manifest_file}")
        print("[hint] Run the research pipeline to generate outputs/manifest.json first.")
        raise SystemExit(1)

    gate_report = args.gate_report.resolve() if args.gate_report else (workdir / "process" / "gate_contracts.json")
    if not gate_report.exists():
        gate_report = None

    output = args.output.resolve() if args.output else (workdir / "outputs" / "eval_report.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    report = evaluate(workdir, manifest_file, gate_report)
    save_json(output, report)

    grade = report["score"]["grade"]
    score = report["score"]["value"]
    ready = report["score"]["ready_for_next_gate"]
    print(f"Evaluation grade: {grade} ({score:.1f})")
    print(f"Ready for next gate: {ready}")
    print(f"Report: {output}")

    if args.fail_below and score < GRADE_TO_SCORE[args.fail_below]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
