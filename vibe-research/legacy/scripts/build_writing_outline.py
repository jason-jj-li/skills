#!/usr/bin/env python3
"""
Build journal-aligned writing blueprint + manuscript outline from exemplar benchmark.

Legacy warning:
  This script emits JSON-first planning artifacts. For new MD-first projects,
  keep the accepted outline and planning state in Markdown after generation.

Outputs:
- process/writing_blueprint.json
- process/writing_outline.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from _common import load_json, save_json, utc_now

LABEL_ALIASES = {
    "background": {"background", "introduction"},
    "methods": {"methods", "method"},
    "findings": {"findings", "results", "result"},
    "interpretation": {"interpretation", "conclusions", "conclusion", "discussion"},
    "funding": {"funding", "support", "financial support"},
}

CANONICAL_LABELS = {
    "background": "Background",
    "methods": "Methods",
    "findings": "Findings",
    "interpretation": "Interpretation",
    "funding": "Funding",
}

TOP_TIER_QUALITY_BAR = "top_tier_submission"
SUBMISSION_QUALITY_BARS = {"submission", TOP_TIER_QUALITY_BAR}

def save_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def normalize_label(label: str) -> str:
    return re.sub(r"[^a-z]+", " ", (label or "").strip().lower()).strip()

def map_label(label: str) -> str:
    n = normalize_label(label)
    for key, aliases in LABEL_ALIASES.items():
        if n in aliases:
            return key
    return n

def derive_abstract_template(summary: Dict, quality_bar: str) -> List[str]:
    counts: Dict[str, int] = {}
    for item in summary.get("common_abstract_labels", []):
        raw = str(item.get("label", "")).strip()
        if not raw:
            continue
        mapped = map_label(raw)
        counts[mapped] = counts.get(mapped, 0) + int(item.get("count", 0))

    out: List[str] = []
    preferred_order = ["background", "methods", "findings", "interpretation", "funding"]
    for key in preferred_order:
        if key in counts:
            out.append(CANONICAL_LABELS[key])

    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    for key, _ in ranked:
        label = CANONICAL_LABELS[key] if key in CANONICAL_LABELS else key.title()
        if label and label not in out:
            out.append(label)

    if not out:
        if (quality_bar or "").strip().lower() == TOP_TIER_QUALITY_BAR:
            out = ["Background", "Methods", "Findings", "Interpretation", "Funding"]
        else:
            out = ["Background", "Methods", "Results", "Interpretation"]
    return out

def derive_reporting_constraints(summary: Dict, target_journal: str, selected_mode: str, quality_bar: str) -> List[str]:
    signals = summary.get("signal_counts", {})
    out: List[str] = []
    quality = (quality_bar or "").strip().lower()

    if quality in SUBMISSION_QUALITY_BARS:
        out.append("Write all core sections in full paragraphs; avoid bulletized prose in abstract, introduction, results, and discussion.")
        out.append("Use claim-evidence-implication paragraph flow with quantitative anchors in interpretive sections.")
    if quality == TOP_TIER_QUALITY_BAR:
        out.append("Avoid template-like repetitive openings; vary sentence starters and transitions across adjacent paragraphs.")
    if str(target_journal).strip():
        out.append(f"Verify heading structure and declarations against current author instructions for {target_journal}.")

    if signals.get("registration_or_prospero", 0) > 0:
        out.append("State protocol/registration details and deviations in Methods.")
    if signals.get("random_effects", 0) > 0:
        out.append("Specify synthesis model and justify random-effects assumptions.")
    if signals.get("heterogeneity_i2", 0) > 0:
        out.append("Report heterogeneity (I2/tau2/Q) and sensitivity analyses.")
    if signals.get("publication_bias_or_funnel", 0) > 0:
        out.append("Report publication bias assessment (funnel plot/small-study effects) where applicable.")
    if signals.get("risk_of_bias_tool", 0) > 0:
        out.append("Report study-level risk-of-bias method and results with a dedicated subsection.")
    if signals.get("grade_or_certainty", 0) > 0:
        out.append("Report certainty of evidence grading and link to primary outcomes.")
    if signals.get("funding_statement", 0) > 0 or quality in SUBMISSION_QUALITY_BARS:
        out.append("Include funding statement and role-of-funder declaration.")

    if selected_mode == "meta_analysis":
        out.append("Provide effect-size harmonization and prespecified subgroup analyses.")
    elif selected_mode == "systematic_review_no_meta":
        out.append("Use structured qualitative synthesis and justify why pooling is inappropriate.")
    elif selected_mode == "scoping_review":
        out.append("Focus on evidence mapping logic and transparent charting framework.")

    if not out:
        out.append("Follow a structured IMRaD narrative with explicit methods-to-claims traceability.")
    deduped: List[str] = []
    for item in out:
        if item not in deduped:
            deduped.append(item)
    return deduped

def infer_research_in_context_need(summary: Dict, quality_bar: str) -> bool:
    quality = (quality_bar or "").strip().lower()
    if quality == TOP_TIER_QUALITY_BAR:
        return True
    hints = summary.get("common_abstract_labels", [])
    for item in hints:
        lbl = normalize_label(str(item.get("label", "")))
        if lbl in {
            "evidence before this study",
            "added value of this study",
            "implications of all the available evidence",
            "research in context",
        }:
            return True
    return False

def build_outline_sections(
    include_research_in_context: bool,
    selected_mode: str,
    abstract_template: List[str],
    reporting_constraints: List[str],
) -> List[Dict]:
    sections: List[Dict] = [
        {
            "id": "title_page",
            "title": "Title Page",
            "purpose": "Declare manuscript identity, affiliations, and metadata.",
            "required_elements": [
                "Submission-grade title with exposure, outcome, and population.",
                "Author list, affiliations, corresponding author.",
                "Word count and key words.",
            ],
            "linked_artifacts": ["process/project_contract.json"],
        },
        {
            "id": "abstract",
            "title": "Structured Abstract",
            "purpose": "Provide a stand-alone, journal-conform summary.",
            "required_elements": [
                f"Use section labels: {', '.join(abstract_template)}.",
                "State design, sample, effect metric, main estimate, and interpretation.",
                "Keep abstract prose narrative (no bullet lists).",
            ],
            "linked_artifacts": ["process/exemplar_benchmark.json", "process/feasibility_report.json"],
        },
    ]

    if include_research_in_context:
        sections.append(
            {
                "id": "research_in_context",
                "title": "Research in Context",
                "purpose": "Position novelty and relevance for editors/reviewers quickly.",
                "required_elements": [
                    "Evidence before this study.",
                    "Added value of this study.",
                    "Implications of all available evidence.",
                ],
                "linked_artifacts": ["process/exemplar_benchmark.md", "process/no_go_topics.json"],
            }
        )

    methods_elements = [
        "Eligibility criteria and study selection flow.",
        "Data extraction protocol and variable dictionary.",
        "Bias/quality appraisal framework.",
        "Synthesis strategy aligned to selected mode.",
    ]
    results_elements = [
        "Study selection summary and characteristics table.",
        "Primary outcome synthesis with consistent metric definitions.",
        "Sensitivity/robustness findings.",
    ]
    if selected_mode == "meta_analysis":
        results_elements.append("Forest plots, heterogeneity, and small-study effect assessments.")
    else:
        results_elements.append("Narrative synthesis logic and reasons pooling was not performed.")

    sections.extend(
        [
            {
                "id": "introduction",
                "title": "Introduction",
                "purpose": "Define gap and hypothesis in one narrative line.",
                "required_elements": [
                    "Current evidence gap and unresolved contradiction.",
                    "Why this question matters for population health or policy.",
                    "Objective statement with estimand.",
                ],
                "linked_artifacts": ["process/standards_snapshot.md", "process/exemplar_benchmark.md"],
            },
            {
                "id": "methods",
                "title": "Methods",
                "purpose": "Make analysis decisions auditable and reproducible.",
                "required_elements": methods_elements,
                "linked_artifacts": ["process/standards_snapshot.md", "process/exemplar_benchmark.json", "experiment-log.md"],
            },
            {
                "id": "results",
                "title": "Results",
                "purpose": "Present evidence first, interpretation second.",
                "required_elements": results_elements,
                "linked_artifacts": ["outputs/manifest.json", "process/citation_db.json", "process/references.bib"],
            },
            {
                "id": "discussion",
                "title": "Discussion",
                "purpose": "Interpret findings with limitations and external validity boundaries.",
                "required_elements": [
                    "Main finding and what is new.",
                    "Consistency/inconsistency with prior evidence.",
                    "Strengths, limitations, and bias implications.",
                    "Policy/clinical/research implications aligned to evidence strength.",
                ],
                "linked_artifacts": ["process/exemplar_benchmark.md", "process/gate_contracts.json"],
            },
            {
                "id": "declarations",
                "title": "Declarations",
                "purpose": "Cover non-negotiable journal reporting statements.",
                "required_elements": [
                    "Funding and role of funder.",
                    "Conflicts of interest.",
                    "Data/code availability statement.",
                    "Ethics statement if applicable.",
                ],
                "linked_artifacts": ["process/standards_snapshot.md"],
            },
        ]
    )

    sections.append(
        {
            "id": "style_constraints",
            "title": "Style Constraints Checklist",
            "purpose": "Convert exemplar style into executable writing constraints.",
            "required_elements": reporting_constraints,
            "linked_artifacts": ["process/writing_blueprint.json"],
        }
    )
    return sections

def sync_tasks(tasks_file: Path, outline_file: Path, blueprint_file: Path, constraints: List[str]) -> Tuple[bool, str]:
    if not tasks_file.exists():
        return False, f"tasks file not found: {tasks_file}"

    payload = load_json(tasks_file)
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return False, "tasks JSON does not contain a list at key `tasks`"

    target = None
    for task in tasks:
        if str(task.get("step", "")).lower() == "writeup":
            target = task
            break
    if target is None:
        return False, "writeup task not found in tasks list"

    artifacts = target.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
        target["artifacts"] = artifacts
    for file_path in [outline_file, blueprint_file]:
        try:
            rel_artifact = str(file_path.relative_to(tasks_file.parent))
        except ValueError:
            rel_artifact = str(file_path)
        abs_artifact = str(file_path)

        if abs_artifact in artifacts and rel_artifact != abs_artifact:
            artifacts[artifacts.index(abs_artifact)] = rel_artifact
        elif rel_artifact not in artifacts and abs_artifact not in artifacts:
            artifacts.append(rel_artifact)

    notes = str(target.get("notes", "")).strip()
    style_line = "Style constraints must be satisfied before writeup passes=true."
    if style_line not in notes:
        notes = f"{notes} {style_line}".strip()
    top_constraints = "; ".join(constraints[:3]) if constraints else "No additional constraints extracted."
    constraint_line = f"Exemplar-derived constraints: {top_constraints}"
    if constraint_line not in notes:
        notes = f"{notes} {constraint_line}".strip()
    target["notes"] = notes

    save_json(tasks_file, payload)
    return True, f"synced writeup task in {tasks_file}"

def build_md(payload: Dict) -> str:
    lines: List[str] = []
    lines.append("# Writing Outline")
    lines.append("")
    lines.append(f"- Generated at: {payload['generated_at']}")
    lines.append(f"- Target journal: {payload.get('target_journal', '')}")
    lines.append(f"- Method target: {payload.get('method_target', '')}")
    lines.append("")
    lines.append("## Style Profile")
    lines.append("")
    lines.append("- Structured abstract template: " + ", ".join(payload["style_profile"]["abstract_template"]))
    for rule in payload["style_profile"]["reporting_constraints"]:
        lines.append(f"- {rule}")
    lines.append("")
    lines.append("## Manuscript Outline")
    lines.append("")
    for section in payload.get("manuscript_outline", []):
        lines.append(f"### {section['title']}")
        lines.append("")
        lines.append(f"- Purpose: {section['purpose']}")
        lines.append("- Required elements:")
        for element in section.get("required_elements", []):
            lines.append(f"  - {element}")
        lines.append("- Linked artifacts: " + ", ".join(section.get("linked_artifacts", [])))
        lines.append("")
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Build writing blueprint and outline from exemplar benchmark.")
    parser.add_argument("--contract", type=Path, default=Path("process/project_contract.json"))
    parser.add_argument("--mode-decision", type=Path, default=Path("process/mode_decision.json"))
    parser.add_argument("--exemplar", type=Path, default=Path("process/exemplar_benchmark.json"))
    parser.add_argument("--output-json", type=Path, default=Path("process/writing_blueprint.json"))
    parser.add_argument("--output-md", type=Path, default=Path("process/writing_outline.md"))
    parser.add_argument("--tasks-json", type=Path, default=Path("research_tasks.json"))
    parser.add_argument("--sync-tasks", action="store_true", help="Update writeup task with outline/style constraints.")
    args = parser.parse_args()

    contract = load_json(args.contract.resolve())
    mode = load_json(args.mode_decision.resolve()) if args.mode_decision.resolve().exists() else {}
    exemplar = load_json(args.exemplar.resolve())

    intent = contract.get("intent", {})
    target_journal = intent.get("target_journal", "")
    quality_bar = str(intent.get("quality_bar", "")).strip().lower()
    method_target = mode.get("decision", {}).get("selected_mode") or intent.get("method_preference", "auto")
    summary = exemplar.get("summary", {})

    abstract_template = derive_abstract_template(summary, quality_bar)
    reporting_constraints = derive_reporting_constraints(summary, target_journal, str(method_target), quality_bar)
    include_ric = infer_research_in_context_need(summary, quality_bar)
    manuscript_outline = build_outline_sections(include_ric, str(method_target), abstract_template, reporting_constraints)

    payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "target_journal": target_journal,
        "method_target": method_target,
        "source_files": {
            "contract": str(args.contract.resolve()),
            "mode_decision": str(args.mode_decision.resolve()),
            "exemplar": str(args.exemplar.resolve()),
        },
        "style_profile": {
            "abstract_template": abstract_template,
            "reporting_constraints": reporting_constraints,
            "quality_bar": quality_bar or "unspecified",
            "include_research_in_context": include_ric,
            "planning_hints_from_exemplar": exemplar.get("planning_hints", []),
        },
        "manuscript_outline": manuscript_outline,
    }

    output_json = args.output_json.resolve()
    output_md = args.output_md.resolve()
    save_json(output_json, payload)
    save_md(output_md, build_md(payload))

    sync_status = "skipped"
    if args.sync_tasks:
        tasks_file = args.tasks_json.resolve()
        ok, msg = sync_tasks(tasks_file, output_md, output_json, reporting_constraints)
        sync_status = "done" if ok else f"failed ({msg})"

    print(f"Writing blueprint JSON: {output_json}")
    print(f"Writing outline MD: {output_md}")
    print(f"sync_tasks={sync_status}")

if __name__ == "__main__":
    main()
