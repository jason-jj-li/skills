#!/usr/bin/env python3
"""
Initialize a versioned research family workspace for long-running vibe-research tasks.

Legacy warning:
  This script initializes the older JSON-first workflow. For new MD-first
  projects, prefer the AGENTS.md / STATE.md / TASKS.md / CHANGELOG.md
  bootstrap flow documented in references/quickstart.md.

Example:
  python init_research_family.py aces_sensory \
    --root /path/to/workspace \
    --title "ACEs and sensory impairment in older adults" \
    --contributor jjlee
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from _common import load_json, utc_now

LEAN_LAYOUT_DIRS = ["process", "outputs", "logs", "manuscript"]
FULL_LAYOUT_DIRS = ["code", "data", "figures", "process", "outputs", "tables", "logs", "manuscript"]

def write_json(path: Path, payload: Dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def infer_next_version(family_dir: Path) -> int:
    versions = []
    for child in family_dir.iterdir():
        if child.is_dir() and child.name.startswith("v"):
            try:
                versions.append(int(child.name[1:]))
            except ValueError:
                continue
    return (max(versions) + 1) if versions else 1

def infer_parent_paper_id(family_dir: Path, version: int) -> Optional[str]:
    if version <= 1:
        return None
    parent_meta = family_dir / f"v{version - 1}" / "metadata.json"
    if not parent_meta.exists():
        return None
    payload = load_json(parent_meta)
    return payload.get("paper_id")

def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

def build_initialization_md(args: argparse.Namespace, paper_id: str, parent: Optional[str]) -> str:
    lines = [
        "# Initialization",
        "",
        f"- Timestamp (UTC): {utc_now()}",
        f"- Paper family: {args.family_id}",
        f"- Paper ID: {paper_id}",
        f"- Title: {args.title}",
        f"- Contributor: {args.contributor}",
        f"- Authoring model: {args.authoring_model}",
        f"- Layout: {args.layout}",
    ]
    if parent:
        lines.append(f"- Parent paper: {parent}")
    lines.extend(["", "## Scope", "", "- Define one primary research question.", "- Lock standards before execution."])
    return "\n".join(lines) + "\n"

def build_initial_plan_md(args: argparse.Namespace) -> str:
    return (
        "# Initial Research Plan\n\n"
        f"**Title:** {args.title}\n"
        f"**Date:** {datetime.now().date().isoformat()}\n\n"
        "## 1. Research Question\n\n"
        "- [TODO] Primary question\n\n"
        "## 2. Identification/Analysis Strategy\n\n"
        "- [TODO] Design and estimand\n\n"
        "## 3. Data Sources\n\n"
        "- [TODO] Source list and provenance plan\n\n"
        "## 4. Risks and Mitigations\n\n"
        "- [TODO] Key threats and checks\n\n"
        "## 5. Execution Milestones\n\n"
        "- [ ] Standards-first gate\n"
        "- [ ] Retrieval/screening\n"
        "- [ ] Synthesis and write-up\n"
    )

def build_research_plan_md(args: argparse.Namespace, paper_id: str, parent: Optional[str]) -> str:
    parent_line = f"\n**Parent:** {parent}\n" if parent else "\n"
    return (
        "# Research Plan\n\n"
        f"**Paper ID:** {paper_id}\n"
        f"**Title:** {args.title}\n"
        f"**Version:** v{args.version}\n"
        f"{parent_line}\n"
        "## Execution States\n\n"
        "INIT -> STANDARDS -> RANK -> EXECUTE -> INTERNAL_REVIEW -> "
        "EXTERNAL_REVIEW -> DECISION -> (REVISION|PUBLISH)\n\n"
        "## Standards Constraints\n\n"
        "- [TODO] Derived from process/standards_snapshot.md\n\n"
        "## Decision Rule\n\n"
        "- [TODO] Define pass/fail gate thresholds\n"
    )

def build_revision_plan_md(parent: str) -> str:
    return (
        "# Revision Plan 1\n\n"
        f"**Parent:** {parent}\n\n"
        "## Workstreams\n\n"
        "1. [TODO] Methodology fixes\n"
        "2. [TODO] Reporting fixes\n"
        "3. [TODO] Replication fixes\n"
    )

def build_reply_md() -> str:
    return (
        "# Reply to Reviewers\n\n"
        "## Scope of This Revision\n\n"
        "- [TODO]\n\n"
        "## Reviewer 1\n\n"
        "- Concern: [TODO]\n"
        "- Response: [TODO]\n\n"
        "## Reviewer 2\n\n"
        "- Concern: [TODO]\n"
        "- Response: [TODO]\n\n"
        "## Reviewer 3\n\n"
        "- Concern: [TODO]\n"
        "- Response: [TODO]\n"
    )

def build_standards_snapshot_stub() -> str:
    return (
        "# Standards Snapshot\n\n"
        "- Access date: YYYY-MM-DD\n"
        "- Journal target URL: [TODO]\n"
        "- Reporting standard URL: [TODO]\n\n"
        "## Actionable Requirements\n\n"
        "- [TODO] Word limit\n"
        "- [TODO] Reference limit\n"
        "- [TODO] Figure/table limit\n"
        "- [TODO] Mandatory sections/checklists\n"
    )

def build_manuscript_stub(title: str) -> str:
    return (
        "---\n"
        f"title: \"{title}\"\n"
        "format:\n"
        "  pdf: default\n"
        "bibliography: ../process/references.bib\n"
        "---\n\n"
        "# Structured summary\n\n"
        "## Background\n\n"
        "[TODO]\n\n"
        "## Methods\n\n"
        "[TODO]\n\n"
        "## Findings\n\n"
        "[TODO]\n\n"
        "## Interpretation\n\n"
        "[TODO]\n\n"
        "## Funding\n\n"
        "[TODO]\n\n"
        "# Research in context\n\n"
        "## Evidence before this study\n\n"
        "[TODO]\n\n"
        "## Added value of this study\n\n"
        "[TODO]\n\n"
        "## Implications of all the available evidence\n\n"
        "[TODO]\n\n"
        "# Where the field stands now\n\n"
        "[TODO]\n\n"
        "# Introduction\n\n"
        "[TODO]\n\n"
        "# Methods\n\n"
        "[TODO]\n\n"
        "# Results\n\n"
        "[TODO]\n\n"
        "# Discussion\n\n"
        "[TODO]\n\n"
        "# Conclusions\n\n"
        "[TODO]\n"
    )

def build_supplement_stub() -> str:
    return "# Supplement: Technical Methods and Reproducibility\n\n[TODO]\n"

def merge_project_contract_template(template: Dict, title: str) -> Dict:
    payload = dict(template)
    payload["generated_at"] = utc_now()
    payload["request_text"] = f"Initialize project scaffold: {title}"
    intent = payload.get("intent", {}) if isinstance(payload.get("intent"), dict) else {}
    if "|" in str(intent.get("deliverable_tier", "")):
        intent["deliverable_tier"] = "draft"
    if "|" in str(intent.get("quality_bar", "")):
        intent["quality_bar"] = "draft"
    if "|" in str(intent.get("language", "")) or not str(intent.get("language", "")).strip():
        intent["language"] = "en"
    if "|" in str(intent.get("method_preference", "")):
        intent["method_preference"] = "auto"
    payload["intent"] = intent

    gate_policy = payload.get("gate_policy", {}) if isinstance(payload.get("gate_policy"), dict) else {}
    if "|" in str(gate_policy.get("convergence_policy", "")):
        gate_policy["convergence_policy"] = "light"
    payload["gate_policy"] = gate_policy
    return payload

def merge_gate_contract_template(template: Dict, workdir: Path) -> Dict:
    payload = dict(template)
    payload["generated_at"] = utc_now()
    payload["workdir"] = str(workdir)
    payload["gate_state"] = "EXECUTE"
    return payload

def _parse_version(value: str) -> int:
    """Accept both integer (1) and vN (v1) formats."""
    stripped = value.strip().lower()
    if stripped.startswith("v"):
        stripped = stripped[1:]
    try:
        return int(stripped)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid version: '{value}'. Use an integer or 'vN' format, e.g. 1 or v1.")

def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize versioned vibe-research family workspace.")
    parser.add_argument("family_id", help="Family identifier, e.g. aces_sensory")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Root folder containing paper families")
    parser.add_argument("--title", required=True, help="Paper title for metadata")
    parser.add_argument("--version", type=_parse_version, help="Version number, e.g. 1 or v1 (default: auto-increment)")
    parser.add_argument("--contributor", default="unknown", help="Contributor name")
    parser.add_argument("--authoring-model", default="unknown", help="Primary authoring model")
    parser.add_argument("--parent-paper-id", help="Parent paper ID for revision versions")
    parser.add_argument("--layout", choices=["lean", "full"], default="lean", help="Workspace layout style")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_root = script_dir.parent
    assets_dir = skill_root / "assets"
    tasks_template = assets_dir / "research_tasks.template.json"
    workflow_template = assets_dir / "workflow_state.template.json"
    thresholds_template = assets_dir / "decision_thresholds.template.json"
    contract_template = assets_dir / "project_contract.template.json"
    gate_template = assets_dir / "gate_contracts.template.json"

    required_templates = [
        tasks_template,
        workflow_template,
        thresholds_template,
        contract_template,
        gate_template,
    ]
    missing_templates = [str(p) for p in required_templates if not p.exists()]
    if missing_templates:
        raise FileNotFoundError(f"Missing required templates in vibe-research/assets: {missing_templates}")

    family_dir = (args.root / args.family_id).resolve()
    family_dir.mkdir(parents=True, exist_ok=True)
    version = args.version if args.version else infer_next_version(family_dir)
    args.version = version

    version_dir = family_dir / f"v{version}"
    if version_dir.exists():
        raise FileExistsError(f"Version directory already exists: {version_dir}")
    version_dir.mkdir(parents=True, exist_ok=False)

    layout_dirs = LEAN_LAYOUT_DIRS if args.layout == "lean" else FULL_LAYOUT_DIRS
    for sub in layout_dirs:
        (version_dir / sub).mkdir(parents=True, exist_ok=True)

    parent = args.parent_paper_id or infer_parent_paper_id(family_dir, version)
    paper_id = f"{args.family_id}_v{version}"

    metadata = {
        "paper_id": paper_id,
        "title": args.title,
        "method": "Unknown",
        "contributor": args.contributor,
        "contributors": [args.contributor],
        "authoring_model": args.authoring_model,
        "published_at": None,
        "version": version,
        "paper_family_id": args.family_id,
        "layout": args.layout,
    }
    if parent:
        metadata["parent_paper_id"] = parent
        metadata["is_revision"] = True
    write_json(version_dir / "metadata.json", metadata)

    workflow_state = load_json(workflow_template)
    now = utc_now()
    workflow_state["paper_family_id"] = args.family_id
    workflow_state["paper_id"] = paper_id
    workflow_state["version"] = version
    workflow_state["history"][0]["timestamp"] = now
    workflow_state["last_updated"] = now
    write_json(version_dir / "workflow_state.json", workflow_state)

    write_json(version_dir / "research_tasks.json", load_json(tasks_template))
    write_json(version_dir / "process" / "decision_thresholds.json", load_json(thresholds_template))
    write_json(
        version_dir / "process" / "project_contract.json",
        merge_project_contract_template(load_json(contract_template), args.title),
    )
    write_json(
        version_dir / "process" / "gate_contracts.json",
        merge_gate_contract_template(load_json(gate_template), version_dir),
    )

    write_text(version_dir / "initialization.md", build_initialization_md(args, paper_id, parent))
    write_text(version_dir / "initial_plan.md", build_initial_plan_md(args))
    write_text(version_dir / "research_plan.md", build_research_plan_md(args, paper_id, parent))
    write_text(version_dir / "research-progress.txt", "# Research Progress Log\n")
    write_text(version_dir / "experiment-log.md", "# Experiment Log\n")
    write_text(version_dir / "literature.json", "{}\n")
    write_text(version_dir / "hypothesis.json", "{}\n")
    write_text(version_dir / "process" / "standards_snapshot.md", build_standards_snapshot_stub())
    write_text(version_dir / "process" / "analysis_plan.md", "# Analysis Plan\n\n[TODO]\n")
    write_text(version_dir / "manuscript" / "paper.qmd", build_manuscript_stub(args.title))
    write_text(version_dir / "manuscript" / "supplement_methods_appendix.qmd", build_supplement_stub())

    if version > 1:
        write_text(version_dir / "revision_plan_1.md", build_revision_plan_md(parent or "unknown"))
        write_text(version_dir / "reply_to_reviewers_1.md", build_reply_md())

    print(f"Initialized: {version_dir}")
    print(f"Paper ID: {paper_id}")
    print(f"Layout: {args.layout}")
    if parent:
        print(f"Parent: {parent}")

if __name__ == "__main__":
    main()
