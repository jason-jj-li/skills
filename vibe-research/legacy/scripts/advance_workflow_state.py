#!/usr/bin/env python3
"""
Advance workflow_state.json with transition and artifact-gate validation.

Legacy warning:
  This script advances the older JSON-first state machine. It is not the
  canonical control path for new MD-first projects.

Example:
  python advance_workflow_state.py /path/to/paper_family/v1 --to STANDARDS
  python advance_workflow_state.py /path/to/paper_family/v1 --to DECISION \
    --note "2/3 reviewers MINOR REVISION"
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from _common import load_json, utc_now

TRANSITIONS = {
    "INIT": ["STANDARDS"],
    "STANDARDS": ["RANK"],
    "RANK": ["EXECUTE"],
    "EXECUTE": ["INTERNAL_REVIEW"],
    "INTERNAL_REVIEW": ["EXTERNAL_REVIEW"],
    "EXTERNAL_REVIEW": ["DECISION"],
    "DECISION": ["REVISION", "PUBLISH"],
    "REVISION": ["EXECUTE"],
    "PUBLISH": [],
}

# Each target state defines one or more requirement groups.
# At least one file in each group must exist unless --force is used.
STATE_REQUIREMENTS: Dict[str, List[List[str]]] = {
    "RANK": [["process/standards_snapshot.md"]],
    "EXECUTE": [["research_tasks.json"], ["ideas_ranked.json", "process/novelty_scan.md"]],
    "INTERNAL_REVIEW": [["manuscript/paper.qmd"], ["outputs/manifest.json", "outputs/refined_manifest.json"]],
    "EXTERNAL_REVIEW": [["advisor_summary.json", "outputs/advisor_summary.json"]],
    "DECISION": [["parallel_review_summary.json", "outputs/parallel_review_summary.json"]],
    "REVISION": [["revision_plan_1.md"], ["reply_to_reviewers_1.md"]],
    "PUBLISH": [["manuscript/paper.pdf"], ["metadata.json"]],
}

def write_json(path: Path, payload: Dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def validate_requirements(workdir: Path, target_state: str) -> List[str]:
    missing_groups = []
    groups = STATE_REQUIREMENTS.get(target_state, [])
    for group in groups:
        if not any((workdir / rel).exists() for rel in group):
            missing_groups.append(" OR ".join(group))
    return missing_groups

def _any_exists(workdir: Path, candidates: List[str]) -> bool:
    return any((workdir / rel).exists() for rel in candidates)


def _verdict_pass(workdir: Path, candidates: List[str]) -> bool:
    """Check if any candidate JSON file exists AND contains a passing verdict."""
    for rel in candidates:
        fpath = workdir / rel
        if fpath.exists():
            try:
                data = load_json(fpath)
                verdict = data.get("verdict", data.get("status", "")).lower()
                if verdict == "pass":
                    return True
            except Exception:
                continue
    return False

def set_gate_flags(payload: Dict, workdir: Path, target_state: str) -> None:
    gates = payload.get("gates", {})
    if target_state in {"STANDARDS", "RANK", "EXECUTE", "INTERNAL_REVIEW", "EXTERNAL_REVIEW", "DECISION", "REVISION", "PUBLISH"}:
        gates["standards_first_passed"] = target_state not in {"INIT", "STANDARDS"} or gates.get("standards_first_passed", False)
    if target_state in {"STANDARDS", "RANK", "EXECUTE", "INTERNAL_REVIEW", "EXTERNAL_REVIEW", "DECISION", "REVISION", "PUBLISH"}:
        gates["target_gate_passed"] = gates.get("target_gate_passed", False) or _verdict_pass(
            workdir,
            ["process/target_gate.json"],
        ) or _any_exists(workdir, ["process/target_gate.md"])
    if target_state in {"EXECUTE", "INTERNAL_REVIEW", "EXTERNAL_REVIEW", "DECISION", "REVISION", "PUBLISH"}:
        gates["ranking_passed"] = True
    if target_state in {"INTERNAL_REVIEW", "EXTERNAL_REVIEW", "DECISION", "REVISION", "PUBLISH"}:
        gates["execution_passed"] = True
    if target_state in {"DECISION", "REVISION", "PUBLISH"}:
        gates["style_gate_passed"] = gates.get("style_gate_passed", False) or _verdict_pass(
            workdir,
            ["process/style_gate_report.json", "outputs/style_gate_report.json"],
        )
        gates["content_focus_gate_passed"] = gates.get("content_focus_gate_passed", False) or _verdict_pass(
            workdir,
            ["process/content_focus_review.json", "outputs/content_focus_review.json"],
        )
        gates["citation_architecture_gate_passed"] = gates.get("citation_architecture_gate_passed", False) or _verdict_pass(
            workdir,
            ["process/citation_architecture_review.json", "outputs/citation_architecture_review.json"],
        )
        gates["triad_review_passed"] = gates.get("triad_review_passed", False) or _verdict_pass(
            workdir,
            ["process/triad_review.json", "outputs/triad_review.json"],
        )
    if target_state in {"EXTERNAL_REVIEW", "DECISION", "REVISION", "PUBLISH"}:
        gates["internal_review_passed"] = True
    if target_state in {"DECISION", "REVISION", "PUBLISH"}:
        gates["external_review_passed"] = True
    if target_state in {"REVISION", "PUBLISH"}:
        gates["decision_recorded"] = True
    payload["gates"] = gates

def main() -> None:
    parser = argparse.ArgumentParser(description="Advance workflow state with gate checks.")
    parser.add_argument("workdir", type=Path, help="Version directory containing workflow_state.json")
    parser.add_argument("--to", required=True, choices=list(TRANSITIONS.keys()), help="Target workflow state")
    parser.add_argument("--note", default="", help="Optional history note")
    parser.add_argument("--force", action="store_true", help="Skip artifact gate checks")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    state_file = workdir / "workflow_state.json"
    if not state_file.exists():
        raise FileNotFoundError(f"Missing workflow state file: {state_file}")

    payload = load_json(state_file)
    current = payload.get("current_state", "INIT")
    target = args.to

    allowed = TRANSITIONS.get(current, [])
    if target not in allowed:
        raise ValueError(f"Invalid transition: {current} -> {target}. Allowed: {allowed}")

    if not args.force:
        missing = validate_requirements(workdir, target)
        if missing:
            print("Cannot advance state, missing requirement groups:")
            for group in missing:
                print(f"  - {group}")
            raise SystemExit(1)

    event = {
        "from": current,
        "state": target,
        "timestamp": utc_now(),
        "note": args.note or "state transition",
    }
    payload.setdefault("history", []).append(event)
    payload["current_state"] = target
    payload["last_updated"] = event["timestamp"]
    set_gate_flags(payload, workdir, target)
    write_json(state_file, payload)

    print(f"State advanced: {current} -> {target}")
    print(f"Updated: {state_file}")

if __name__ == "__main__":
    main()
