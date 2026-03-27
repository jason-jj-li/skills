#!/usr/bin/env python3
"""
Maintain no-go topic registry when mode pivot/no-go is triggered.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from _common import load_json, save_json, utc_now

def ensure_registry(path: Path) -> Dict:
    if path.exists():
        payload = load_json(path)
        payload.setdefault("schema_version", 1)
        payload.setdefault("entries", [])
        return payload
    return {"schema_version": 1, "updated_at": "", "entries": []}

def should_record(mode_decision: Dict) -> bool:
    decision = mode_decision.get("decision", {})
    requested_mode = decision.get("requested_mode", "auto")
    selected_mode = decision.get("selected_mode", "")
    go = bool(decision.get("go", True))
    pivot_required = bool(decision.get("pivot_required", False))
    return (not go) or pivot_required or (
        requested_mode == "meta_analysis" and selected_mode != "meta_analysis"
    )

def build_entry(mode_decision: Dict, contract: Dict) -> Dict:
    decision = mode_decision.get("decision", {})
    selected = mode_decision.get("selected_candidate", {})
    reasons = decision.get("reason", [])
    reason_text = " | ".join(reasons) if isinstance(reasons, list) else str(reasons)
    return {
        "topic": selected.get("topic", ""),
        "requested_mode": decision.get("requested_mode", "auto"),
        "blocked_for_tier": contract.get("intent", {}).get("deliverable_tier", "unknown"),
        "reason": reason_text,
        "replacement_mode": decision.get("selected_mode", ""),
        "source_mode_decision_file": mode_decision.get("_source_file", ""),
        "timestamp": utc_now(),
    }

def dedup_append(entries: List[Dict], new_entry: Dict) -> bool:
    for existing in entries:
        if (
            existing.get("topic") == new_entry.get("topic")
            and existing.get("requested_mode") == new_entry.get("requested_mode")
            and existing.get("blocked_for_tier") == new_entry.get("blocked_for_tier")
        ):
            return False
    entries.append(new_entry)
    return True

def main() -> None:
    parser = argparse.ArgumentParser(description="Update no-go topic registry from mode decision.")
    parser.add_argument("workdir", nargs="?", type=Path, default=None, help="Research workdir (if set, resolves default paths relative to it)")
    parser.add_argument(
        "--mode-decision",
        type=Path,
        default=None,
        help="Mode decision JSON (default: <workdir>/process/mode_decision.json)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="No-go registry JSON (default: <workdir>/process/no_go_topics.json)",
    )
    parser.add_argument(
        "--force-record",
        action="store_true",
        help="Record entry even if no pivot/no-go was triggered",
    )
    args = parser.parse_args()

    base = args.workdir.resolve() if args.workdir else Path.cwd()
    mode_decision_file = args.mode_decision.resolve() if args.mode_decision else (base / "process" / "mode_decision.json")
    if not mode_decision_file.exists():
        print(f"[error] Mode decision file not found: {mode_decision_file}")
        raise SystemExit(1)
    mode_decision = load_json(mode_decision_file)
    mode_decision["_source_file"] = str(mode_decision_file)

    contract_file = Path(mode_decision.get("contract_file", "")).resolve()
    contract = load_json(contract_file) if contract_file.exists() else {}

    registry_file = args.registry.resolve() if args.registry else (base / "process" / "no_go_topics.json")
    registry = ensure_registry(registry_file)

    if args.force_record or should_record(mode_decision):
        entry = build_entry(mode_decision, contract)
        changed = dedup_append(registry["entries"], entry)
        status = "recorded" if changed else "already_exists"
    else:
        status = "skip"

    registry["updated_at"] = utc_now()
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    save_json(registry_file, registry)

    print(f"No-go registry updated: {registry_file}")
    print(f"status={status} entries={len(registry['entries'])}")

if __name__ == "__main__":
    main()
