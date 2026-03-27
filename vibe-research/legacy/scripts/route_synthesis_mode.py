#!/usr/bin/env python3
"""
Route project to the most feasible synthesis mode based on intent and feasibility.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import load_json, save_json, utc_now, TOP_TIER_HINTS

SUPPORTED_MODES = {
    "meta_analysis",
    "systematic_review_no_meta",
    "scoping_review",
    "evidence_gap_map",
    "protocol",
}

MODE_ALIASES = {
    "systematic_review": "systematic_review_no_meta",
}

# Use centralised list from _common
TOP_TIER_JOURNAL_HINTS = TOP_TIER_HINTS

DEFAULT_POLICY = {
    "schema_version": 1,
    "thresholds": {
        "submission_meta_min_all_count": 15,
        "submission_meta_min_effect_signal_rate": 0.25,
        "top_tier_submission_meta_min_all_count": 25,
        "top_tier_submission_meta_min_effect_signal_rate": 0.35,
        "min_publishability_score": 0.8,
        "min_novelty_score": 0.70,
        "min_journal_fit_score": 0.55,
        "max_prior_meta_count_for_innovation": 1,
    },
}

def merge_dict(base: Dict, override: Dict) -> Dict:
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = merge_dict(merged[k], v)
        else:
            merged[k] = v
    return merged

def load_policy(contract_file: Path, feasibility: Dict, thresholds_json: Path | None) -> Tuple[Dict, str]:
    policy = dict(DEFAULT_POLICY)
    source = "default"

    if isinstance(feasibility.get("policy_used"), dict):
        policy = merge_dict(policy, feasibility["policy_used"])
        source = "feasibility_report.policy_used"

    policy_path = thresholds_json
    if policy_path is None:
        default_policy = contract_file.resolve().parent / "decision_thresholds.json"
        if default_policy.exists():
            policy_path = default_policy

    if policy_path:
        p = policy_path.resolve()
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                user_policy = json.load(f)
            policy = merge_dict(policy, user_policy)
            source = str(p)

    return policy, source

def normalize_mode(mode: str) -> str:
    if mode in MODE_ALIASES:
        return MODE_ALIASES[mode]
    return mode

def pick_best_candidate(feasibility: Dict) -> Dict:
    candidates = feasibility.get("candidates", [])
    if not candidates:
        print("[error] Feasibility report has no candidates.")
        print("[hint] Run assess_feasibility.py first to generate candidate evaluations.")
        raise SystemExit(1)
    ranking = feasibility.get("ranking", [])
    if ranking:
        rank_index = {cid: i for i, cid in enumerate(ranking)}
        candidates = sorted(candidates, key=lambda c: rank_index.get(c.get("id", ""), 10_000))
    else:
        candidates = sorted(candidates, key=lambda c: c.get("scores", {}).get("publishability", 0), reverse=True)
    return candidates[0]

def infer_readiness_flags(best: Dict, thresholds: Dict) -> Dict[str, bool]:
    novelty = float(best.get("scores", {}).get("novelty", 0.0))
    publishability = float(best.get("scores", {}).get("publishability", 0.0))
    journal_fit = float(best.get("scores", {}).get("journal_fit", 0.0))
    meta_count = int(best.get("metrics", {}).get("meta_count", 0))
    min_nov = float(thresholds.get("min_novelty_score", 0.70))
    min_pub = float(thresholds.get("min_publishability_score", 0.8))
    min_fit = float(thresholds.get("min_journal_fit_score", 0.55))
    max_prior_meta = int(thresholds.get("max_prior_meta_count_for_innovation", 1))

    innovation_ready = novelty >= min_nov and meta_count <= max_prior_meta
    quality_ready = publishability >= min_pub and journal_fit >= min_fit
    return {
        "innovation_ready": innovation_ready,
        "quality_ready": quality_ready,
        "innovation_and_quality_ready": innovation_ready and quality_ready,
    }

def decide_mode(contract: Dict, best: Dict, policy: Dict) -> Tuple[Dict, List[str]]:
    intent = contract.get("intent", {})
    constraints = contract.get("constraints", {})
    thresholds = policy.get("thresholds", {})

    requested_mode = normalize_mode(intent.get("method_preference", "auto"))
    allow_mode_switch = bool(constraints.get("allow_mode_switch", True))
    stop_on_goal_mismatch = bool(constraints.get("stop_on_goal_mismatch", False))
    deliverable_tier = intent.get("deliverable_tier", "unknown")
    quality_bar = intent.get("quality_bar", "unknown")
    target_journal = str(intent.get("target_journal", "")).lower()
    top_tier_submission = quality_bar == "top_tier_submission" or (
        quality_bar == "unknown"
        and deliverable_tier == "submission_ready"
        and any(h in target_journal for h in TOP_TIER_JOURNAL_HINTS)
    )
    research_requirement = str(intent.get("research_requirement", "")).lower()
    require_innovation_and_quality = bool(constraints.get("require_innovation_and_quality", False)) or (
        research_requirement == "innovation_and_quality"
    ) or top_tier_submission

    suggested_mode = best.get("suggested_mode", "evidence_gap_map")
    if suggested_mode not in SUPPORTED_MODES:
        suggested_mode = "evidence_gap_map"

    reasons: List[str] = []
    go = True
    pivot_required = False
    selected_mode = suggested_mode

    all_count = int(best.get("metrics", {}).get("all_count", 0))
    effect_signal_rate = float(best.get("metrics", {}).get("effect_signal_rate", 0.0))
    publishability_score = float(best.get("scores", {}).get("publishability", 0.0))
    readiness = infer_readiness_flags(best, thresholds)

    submission_min_n = int(thresholds.get("submission_meta_min_all_count", 15))
    submission_min_eff = float(thresholds.get("submission_meta_min_effect_signal_rate", 0.25))
    top_tier_min_n = int(thresholds.get("top_tier_submission_meta_min_all_count", 25))
    top_tier_min_eff = float(thresholds.get("top_tier_submission_meta_min_effect_signal_rate", 0.35))
    min_publishability = float(thresholds.get("min_publishability_score", 0.8))

    submission_meta_feasible = (
        all_count >= submission_min_n
        and effect_signal_rate >= submission_min_eff
        and not bool(best.get("no_go_for_submission_meta", False))
    )
    top_tier_meta_feasible = (
        all_count >= top_tier_min_n
        and effect_signal_rate >= top_tier_min_eff
        and not bool(best.get("no_go_for_submission_meta", False))
    )
    top_tier_general_feasible = publishability_score >= min_publishability

    if requested_mode == "auto":
        selected_mode = suggested_mode
        reasons.append("Auto mode selected best feasible synthesis mode from feasibility ranking.")
    elif requested_mode == "meta_analysis":
        if top_tier_submission and deliverable_tier == "submission_ready":
            if top_tier_meta_feasible:
                selected_mode = "meta_analysis"
                reasons.append("Requested top-tier meta-analysis is feasible under current evidence profile.")
            else:
                reasons.append("Requested top-tier submission meta-analysis is not feasible for current evidence profile.")
                if allow_mode_switch:
                    selected_mode = suggested_mode
                    pivot_required = True
                    reasons.append(f"Pivot candidate is '{selected_mode}', but this is treated as a goal mismatch for top-tier target.")
                else:
                    selected_mode = "meta_analysis"
                    reasons.append("Method lock is enabled; requested mode retained but infeasible.")
                go = False
                reasons.append("Fail-fast enabled: stop after routing and report no-go to the user.")
        elif submission_meta_feasible or deliverable_tier != "submission_ready":
            selected_mode = "meta_analysis"
            reasons.append("Requested meta-analysis is feasible under current evidence profile.")
        else:
            reasons.append("Requested submission-grade meta-analysis is not feasible for current evidence profile.")
            if allow_mode_switch:
                selected_mode = suggested_mode
                pivot_required = True
                reasons.append(f"Pivoting to '{selected_mode}' because mode switching is enabled.")
            else:
                selected_mode = "meta_analysis"
                go = False
                reasons.append("No-Go because method lock is enabled and requested mode is infeasible.")
    elif requested_mode in SUPPORTED_MODES:
        selected_mode = requested_mode
        if requested_mode != suggested_mode:
            reasons.append(
                f"Requested mode '{requested_mode}' differs from feasibility suggestion '{suggested_mode}'."
            )
            if allow_mode_switch:
                reasons.append("Proceeding with requested mode; monitor feasibility risks closely.")
            else:
                reasons.append("Method lock is enabled; requested mode retained.")
    else:
        selected_mode = suggested_mode
        reasons.append("Unknown requested mode; falling back to feasibility suggestion.")

    if (
        top_tier_submission
        and deliverable_tier == "submission_ready"
        and not top_tier_general_feasible
        and stop_on_goal_mismatch
    ):
        go = False
        reasons.append(
            "Best candidate publishability score is below configured top-tier bar; stopping at routing by policy."
        )

    if require_innovation_and_quality and not readiness["innovation_and_quality_ready"]:
        go = False
        reasons.append("Fundamental requirement `innovation_and_quality` is not met by the best candidate.")
        if not readiness["innovation_ready"]:
            reasons.append(
                "Innovation check failed (novelty/meta-pressure below threshold profile)."
            )
        if not readiness["quality_ready"]:
            reasons.append(
                "Quality check failed (publishability/journal-fit below threshold profile)."
            )

    if deliverable_tier == "submission_ready" and selected_mode in {"scoping_review", "evidence_gap_map"}:
        reasons.append(
            "Selected mode is unlikely to satisfy submission-ready expectation without user-level scope adjustment."
        )

    next_actions = [
        f"Lock topic '{best.get('topic', '')}' and selected mode '{selected_mode}'.",
        "Record standards in process/standards_snapshot.md before retrieval/execution.",
    ]
    if selected_mode == "meta_analysis":
        next_actions.append("Run retrieval with strict effect-size extractability checks and subgroup harmonization.")
    elif selected_mode == "systematic_review_no_meta":
        next_actions.append("Proceed with qualitative synthesis and structured certainty/bias reporting.")
    elif selected_mode == "scoping_review":
        next_actions.append("Switch to mapping outcomes and evidence clusters instead of pooled effect estimates.")
    elif selected_mode == "evidence_gap_map":
        next_actions.append("Produce gap map deliverable and explicit no-go rationale for meta-analysis.")
    elif selected_mode == "protocol":
        next_actions.append("Produce protocol-first deliverable with preregistration and analysis plan.")

    if not go:
        next_actions.insert(0, "Stop execution after routing and output explicit no-go rationale plus pivot options.")

    decision = {
        "selected_candidate_id": best.get("id", ""),
        "selected_mode": selected_mode,
        "go": go,
        "pivot_required": pivot_required,
        "requested_mode": requested_mode,
        "require_innovation_and_quality": require_innovation_and_quality,
        "checks": readiness,
        "reason": reasons,
    }
    return decision, next_actions

def main() -> None:
    parser = argparse.ArgumentParser(description="Route to synthesis mode from contract + feasibility reports.")
    parser.add_argument("--contract", type=Path, default=Path("process/project_contract.json"), help="Project contract JSON")
    parser.add_argument(
        "--feasibility",
        type=Path,
        default=Path("process/feasibility_report.json"),
        help="Feasibility report JSON",
    )
    parser.add_argument(
        "--thresholds-json",
        type=Path,
        help="Optional thresholds/weights JSON (defaults to process/decision_thresholds.json if present)",
    )
    parser.add_argument("--output", type=Path, default=Path("process/mode_decision.json"), help="Output decision JSON")
    args = parser.parse_args()

    contract_file = args.contract.resolve()
    contract = load_json(contract_file)
    feasibility = load_json(args.feasibility.resolve())
    policy, policy_source = load_policy(contract_file, feasibility, args.thresholds_json)
    best = pick_best_candidate(feasibility)
    decision, next_actions = decide_mode(contract, best, policy)
    th = policy.get("thresholds", {})
    top_tier_thresholds = {
        "submission_meta_min_all_count": int(th.get("top_tier_submission_meta_min_all_count", 25)),
        "submission_meta_min_effect_signal_rate": float(th.get("top_tier_submission_meta_min_effect_signal_rate", 0.35)),
        "min_publishability_score": float(th.get("min_publishability_score", 0.8)),
        "min_novelty_score": float(th.get("min_novelty_score", 0.70)),
        "min_journal_fit_score": float(th.get("min_journal_fit_score", 0.55)),
        "max_prior_meta_count_for_innovation": int(th.get("max_prior_meta_count_for_innovation", 1)),
    }

    payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "contract_file": str(contract_file),
        "feasibility_file": str(args.feasibility.resolve()),
        "decision": decision,
        "policy_source": policy_source,
        "policy_used": policy,
        "thresholds": {
            "submission_meta_min_all_count": int(th.get("submission_meta_min_all_count", 15)),
            "submission_meta_min_effect_signal_rate": float(th.get("submission_meta_min_effect_signal_rate", 0.25)),
        },
        "top_tier_thresholds": top_tier_thresholds,
        "execution_policy": {
            "stop_after_routing": not decision["go"],
            "reason": "goal_mismatch_or_infeasible" if not decision["go"] else "continue",
        },
        "next_actions": next_actions,
        "selected_candidate": best,
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    save_json(output, payload)

    print(f"Mode decision written: {output}")
    print(
        f"go={decision['go']} selected_mode={decision['selected_mode']} "
        f"pivot_required={decision['pivot_required']}"
    )

if __name__ == "__main__":
    main()
