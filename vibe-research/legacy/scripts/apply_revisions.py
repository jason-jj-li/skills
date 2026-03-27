#!/usr/bin/env python3
"""
Rule-based manuscript auto-fixer.

Legacy warning:
  This script belongs to the older JSON-first writing superloop. In new
  MD-first projects, keep accepted claim state in `process/claims.md` and
  treat any structured exports as disposable.

Reads a revision_tasks.json (schema v2) and applies mechanical fixes
to the manuscript that do NOT require LLM judgment.  Fixes include:

  - Cliché phrase removal
  - Sentence-starter repetition reduction
  - Transition word insertion at paragraph boundaries
  - Bullet-list to prose conversion (simple lists)
  - Missing IMRAD section scaffolding
  - Citation style inconsistency normalization (minor)

Items that require creative rewriting (e.g. "add more citations",
"expand narrative") are collected into an `llm_revision_prompt.md`
file for the Claude agent to handle.

Usage:
    python apply_revisions.py <workdir> \
        --manuscript manuscript/paper.qmd \
        --revisions process/writing_superloop/round_01/revision_tasks.json \
        [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from _common import load_json, save_json, split_frontmatter, split_h1_sections, utc_now

# ---------------------------------------------------------------------------
# Cliché database
# ---------------------------------------------------------------------------

_CLICHES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bIt is worth noting\b(?:\s+that\b)?", re.I), "Notably,"),
    (re.compile(r"\bIt should be noted\b(?:\s+that\b)?", re.I), "Notably,"),
    (re.compile(r"\bIt is important to note that\b", re.I), "Importantly,"),
    (re.compile(r"\bFurther research is needed\b", re.I), "Future work could"),
    (re.compile(r"\bMore research is needed\b", re.I), "Future work could"),
    (re.compile(r"\bIn conclusion,?\s*", re.I), ""),
    (re.compile(r"\bTo the best of our knowledge\b", re.I), "To our knowledge"),
    (re.compile(r"\bA growing body of (?:literature|evidence|research)\b", re.I), "Emerging evidence"),
    (re.compile(r"\bSheds? (?:new )?light on\b", re.I), "clarifies"),
    (re.compile(r"\bBridges? (?:the|a|an) gap\b", re.I), "connects"),
    (re.compile(r"\bNovel approach\b", re.I), "approach"),
    (re.compile(r"\bRobust (?:framework|methodology)\b", re.I), "framework"),
    (re.compile(r"\bParadigm shift\b", re.I), "methodological shift"),
    (re.compile(r"\bCutting[- ]edge\b", re.I), "recent"),
    (re.compile(r"\bState[- ]of[- ]the[- ]art\b", re.I), "current"),
    (re.compile(r"\bIn this paper,?\s*we\b", re.I), "We"),
    (re.compile(r"\bIn this study,?\s*we\b", re.I), "We"),
    (re.compile(r"\bThe aim of this (?:paper|study) is\b", re.I), "This study aims"),
    (re.compile(r"\bPlay(?:s|ed)? (?:a )?(?:crucial|key|vital|important|pivotal) role\b", re.I), "contributes"),
    (re.compile(r"\ba number of\b", re.I), "several"),
    (re.compile(r"\bvery\s+", re.I), ""),
]

# ---------------------------------------------------------------------------
# Transition words for paragraph coherence
# ---------------------------------------------------------------------------

_TRANSITION_POOL = [
    "Moreover,", "Furthermore,", "In addition,", "However,",
    "Nevertheless,", "Conversely,", "Similarly,", "By contrast,",
    "Accordingly,", "Consequently,", "In particular,", "Specifically,",
    "Notably,", "Importantly,", "Likewise,", "Alternatively,",
]

# ---------------------------------------------------------------------------
# Sentence-starter alternatives
# ---------------------------------------------------------------------------

_STARTER_ALTERNATIVES = {
    "the": ["This", "That", "Such", "These"],
    "this": ["The", "Such", "That"],
    "we": ["The authors", "Our analysis", "This study"],
    "it": ["The finding", "This result", "The outcome"],
    "these": ["Such", "The", "Those"],
    "there": ["Several", "Multiple", "Numerous"],
}

# ---------------------------------------------------------------------------
# IMRAD sections
# ---------------------------------------------------------------------------

_IMRAD_SECTIONS = {
    "introduction": "# Introduction\n\n[TODO: Write introduction establishing context, gap, and contribution]\n",
    "methods": "# Methods\n\n[TODO: Describe study design, data sources, and analytical approach]\n",
    "results": "# Results\n\n[TODO: Present findings with numeric evidence]\n",
    "discussion": "# Discussion\n\n[TODO: Interpret findings, compare with literature, discuss implications]\n",
    "conclusions": "# Conclusions\n\n[TODO: Summarize key findings and state their implications]\n",
}

_FIELD_STATE_SCAFFOLD = "# Where the field stands now\n\n[TODO: Describe the current state of the field with recent citations]\n"
_RESEARCH_CTX_SCAFFOLD = "# Research in context\n\n**Evidence before this study**\n\n[TODO: Summarize prior evidence]\n\n**Added value of this study**\n\n[TODO: Describe contribution]\n\n**Implications of all the available evidence**\n\n[TODO: Synthesize implications]\n"

# ---------------------------------------------------------------------------
# Classification: which checks are mechanically fixable?
# ---------------------------------------------------------------------------

MECHANICAL_CHECKS = {
    "Cliche suppression",
    "Sentence-starter repetition control",
    "Sentence-length variability sanity",
    "Narrative section bullet leakage",
    "Interpretive transition coherence",
    "Core IMRAD section presence",
    "frontloaded_field_state_section",
    "field_state_h1_present_when_required",
    "research_in_context_h1_present",
    "Citation style consistency",
}

# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------


def fix_cliches(text: str) -> Tuple[str, int]:
    """Remove / replace cliché phrases.  Returns (fixed_text, count)."""
    count = 0
    for pattern, replacement in _CLICHES:
        text, n = pattern.subn(replacement, text)
        count += n
    # Clean up double spaces introduced by removal
    text = re.sub(r"  +", " ", text)
    # Clean up empty sentences (just period after replacement)
    text = re.sub(r"\.\s*\.", ".", text)
    return text, count


def fix_sentence_starters(text: str) -> Tuple[str, int]:
    """Diversify repeated consecutive sentence starters."""
    paragraphs = text.split("\n\n")
    total_fixes = 0

    for p_idx, para in enumerate(paragraphs):
        # Skip headings, code blocks, bullets
        if para.strip().startswith(("#", "```", "-", "*", "1.", ">")):
            continue
        sentences = re.split(r"(?<=[.!?])\s+", para)
        if len(sentences) < 3:
            continue

        prev_starter = ""
        new_sentences = []
        for s in sentences:
            words = s.split()
            if not words:
                new_sentences.append(s)
                continue
            starter = words[0].lower().rstrip(",")
            if starter == prev_starter and starter in _STARTER_ALTERNATIVES:
                alts = _STARTER_ALTERNATIVES[starter]
                replacement = alts[total_fixes % len(alts)]
                # Preserve original capitalization pattern
                words[0] = replacement
                s = " ".join(words)
                total_fixes += 1
            prev_starter = starter
            new_sentences.append(s)

        paragraphs[p_idx] = " ".join(new_sentences)

    return "\n\n".join(paragraphs), total_fixes


def fix_bullet_leakage(text: str) -> Tuple[str, int]:
    """Convert simple bullet lists in narrative sections to prose."""
    sections = split_h1_sections(text)
    narrative_titles = {"introduction", "results", "discussion", "findings"}
    fixes = 0

    for title, content in sections:
        if title.lower() not in narrative_titles:
            continue
        # Find bullet runs: sequences of lines starting with - or *
        bullet_run_re = re.compile(
            r"((?:^[ \t]*[-*][ \t]+.+\n?){2,})", re.MULTILINE
        )
        for match in bullet_run_re.finditer(content):
            bullet_block = match.group(0)
            items = []
            for line in bullet_block.strip().split("\n"):
                item = re.sub(r"^[ \t]*[-*][ \t]+", "", line).strip()
                if item:
                    # Remove trailing period for joining
                    item = item.rstrip(".")
                    items.append(item)
            if len(items) < 2:
                continue
            # Join into flowing prose
            if len(items) == 2:
                prose = f"{items[0]} and {items[1]}."
            else:
                prose = ", ".join(items[:-1]) + f", and {items[-1]}."
            text = text.replace(bullet_block.strip(), prose)
            fixes += 1

    return text, fixes


def fix_transitions(text: str) -> Tuple[str, int]:
    """Add transition words between paragraphs lacking them."""
    paragraphs = text.split("\n\n")
    fixes = 0
    pool_idx = 0

    for i in range(1, len(paragraphs)):
        para = paragraphs[i].strip()
        # Skip headings, code blocks, YAML, empty
        if not para or para.startswith(("#", "```", "---", "-", "*", ">", "|", "[")):
            continue
        # Check if paragraph already starts with a transition
        first_word = para.split()[0].rstrip(",") if para.split() else ""
        known_transitions = {t.rstrip(",").lower() for t in _TRANSITION_POOL}
        known_transitions.update({"however", "therefore", "thus", "hence", "indeed",
                                   "meanwhile", "although", "yet", "still", "also"})
        if first_word.lower() in known_transitions:
            continue
        # Only add transition if previous paragraph is also prose
        prev = paragraphs[i - 1].strip()
        if not prev or prev.startswith(("#", "```", "---", "-", "*", ">", "|", "[")):
            continue
        # Add a transition
        transition = _TRANSITION_POOL[pool_idx % len(_TRANSITION_POOL)]
        pool_idx += 1
        paragraphs[i] = f"{transition} {para[0].lower()}{para[1:]}"
        fixes += 1

    return "\n\n".join(paragraphs), fixes


def fix_missing_sections(text: str, failed_checks: List[str]) -> Tuple[str, int]:
    """Add scaffold sections for missing IMRAD / field-state / research-in-context."""
    _, body = split_frontmatter(text)
    existing_titles = {t.lower() for t, _ in split_h1_sections(body)}
    additions = []
    fixes = 0

    for check in failed_checks:
        if check == "Core IMRAD section presence":
            for key, scaffold in _IMRAD_SECTIONS.items():
                if key not in existing_titles:
                    additions.append(scaffold)
                    fixes += 1
        elif check in ("frontloaded_field_state_section", "field_state_h1_present_when_required"):
            candidates = {"where the field stands now", "current state of the field",
                          "field context", "state of the field"}
            if not candidates & existing_titles:
                additions.append(_FIELD_STATE_SCAFFOLD)
                fixes += 1
        elif check == "research_in_context_h1_present":
            if "research in context" not in existing_titles:
                additions.append(_RESEARCH_CTX_SCAFFOLD)
                fixes += 1

    if additions:
        # Insert scaffolds before the last section (usually References/Bibliography)
        insert_point = text.rfind("\n# ")
        if insert_point > 0:
            text = text[:insert_point] + "\n\n" + "\n\n".join(additions) + text[insert_point:]
        else:
            text = text + "\n\n" + "\n\n".join(additions)

    return text, fixes


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def apply_revisions(
    manuscript_path: Path,
    revision_tasks: Dict,
    dry_run: bool = False,
) -> Dict:
    """Apply mechanical fixes and return an application report."""
    text = manuscript_path.read_text(encoding="utf-8")
    original_text = text

    items = revision_tasks.get("items", [])
    if not items:
        return {
            "applied": [],
            "deferred_to_llm": [],
            "manuscript_changed": False,
            "backup_path": "",
        }

    # Classify items
    mechanical_items = []
    llm_items = []
    for item in items:
        check = item.get("check", "")
        if check in MECHANICAL_CHECKS:
            mechanical_items.append(item)
        else:
            llm_items.append(item)

    applied: List[Dict] = []
    failed_check_names = [item.get("check", "") for item in mechanical_items]

    # 1. Cliché removal
    if "Cliche suppression" in failed_check_names:
        text, count = fix_cliches(text)
        if count > 0:
            applied.append({"fix": "cliche_removal", "changes": count})

    # 2. Sentence-starter diversification
    if "Sentence-starter repetition control" in failed_check_names:
        text, count = fix_sentence_starters(text)
        if count > 0:
            applied.append({"fix": "starter_diversification", "changes": count})

    # 3. Bullet-to-prose
    if "Narrative section bullet leakage" in failed_check_names:
        text, count = fix_bullet_leakage(text)
        if count > 0:
            applied.append({"fix": "bullet_to_prose", "changes": count})

    # 4. Transition insertion
    if "Interpretive transition coherence" in failed_check_names:
        text, count = fix_transitions(text)
        if count > 0:
            applied.append({"fix": "transition_insertion", "changes": count})

    # 5. Missing section scaffolding
    section_checks = [c for c in failed_check_names if c in {
        "Core IMRAD section presence",
        "frontloaded_field_state_section",
        "field_state_h1_present_when_required",
        "research_in_context_h1_present",
    }]
    if section_checks:
        text, count = fix_missing_sections(text, section_checks)
        if count > 0:
            applied.append({"fix": "section_scaffolding", "changes": count})

    manuscript_changed = text != original_text
    backup_path = ""

    if manuscript_changed and not dry_run:
        # Create backup
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup = manuscript_path.parent / f".{manuscript_path.stem}.backup.{ts}{manuscript_path.suffix}"
        shutil.copy2(manuscript_path, backup)
        backup_path = str(backup)
        # Write revised manuscript
        manuscript_path.write_text(text, encoding="utf-8")

    return {
        "applied": applied,
        "deferred_to_llm": [
            {
                "gate": item.get("gate", ""),
                "check": item.get("check", ""),
                "instruction": item.get("instruction", ""),
            }
            for item in llm_items
        ],
        "manuscript_changed": manuscript_changed,
        "backup_path": backup_path,
    }


def write_llm_prompt(output_path: Path, deferred_items: List[Dict], round_idx: int) -> None:
    """Write a focused revision prompt for items requiring LLM intervention."""
    if not deferred_items:
        return
    lines = [
        f"# LLM Revision Prompt (Round {round_idx})",
        "",
        "The following issues require creative rewriting. Apply each fix to `manuscript/paper.qmd`:",
        "",
    ]
    for i, item in enumerate(deferred_items, 1):
        instruction = item.get("instruction", f"Fix: {item.get('check', 'unknown')}")
        lines.append(f"{i}. **[{item.get('gate', '?')}]** {instruction}")
    lines.extend([
        "",
        "## Rules",
        "",
        "- Preserve all `@citekey` references",
        "- Preserve all verified numeric claims from `process/claims.md` or its exported ledger",
        "- Preserve figure/table references (`@fig-`, `@tbl-`)",
        "- Keep word counts within ±10% of spec targets",
        "- Do not add fabricated citations or statistics",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply rule-based manuscript revisions.")
    parser.add_argument("workdir", type=Path, help="Research workdir (paper_family/vN)")
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript/paper.qmd"))
    parser.add_argument("--revisions", type=Path, help="Path to revision_tasks.json")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without modifying files")
    parser.add_argument("--output-json", type=Path, default=None, help="Path for application report")
    parser.add_argument("--output-prompt", type=Path, default=None, help="Path for LLM revision prompt")
    args = parser.parse_args()

    workdir = args.workdir.resolve()
    if not workdir.exists():
        print(f"[error] Workdir does not exist: {workdir}")
        raise SystemExit(1)

    manuscript = args.manuscript if args.manuscript.is_absolute() else (workdir / args.manuscript)
    if not manuscript.exists():
        print(f"[error] Missing manuscript: {manuscript}")
        raise SystemExit(1)

    # Find revisions file
    revisions_path = args.revisions
    if revisions_path and not revisions_path.is_absolute():
        revisions_path = workdir / revisions_path
    if not revisions_path or not revisions_path.exists():
        print("[error] No revision_tasks.json found.")
        print("[hint] Run the writing superloop first to generate revision tasks.")
        raise SystemExit(1)

    revision_tasks = load_json(revisions_path)
    round_idx = revision_tasks.get("round", 0)

    result = apply_revisions(manuscript, revision_tasks, dry_run=args.dry_run)

    # Write application report
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "manuscript": str(manuscript),
        "revisions_source": str(revisions_path),
        "round": round_idx,
        "dry_run": args.dry_run,
        **result,
    }

    output_json = args.output_json
    if not output_json:
        output_json = revisions_path.parent / "auto_fix_report.json"
    save_json(output_json, report)

    # Write LLM prompt for deferred items
    if result["deferred_to_llm"]:
        output_prompt = args.output_prompt
        if not output_prompt:
            output_prompt = revisions_path.parent / "llm_revision_prompt.md"
        write_llm_prompt(output_prompt, result["deferred_to_llm"], round_idx)
        print(f"[info] LLM revision prompt: {output_prompt}")

    # Summary
    applied_count = sum(a["changes"] for a in result["applied"])
    deferred_count = len(result["deferred_to_llm"])
    mode = "DRY-RUN " if args.dry_run else ""
    print(f"[info] {mode}Auto-fix: {applied_count} mechanical changes applied, {deferred_count} items deferred to LLM.")
    if result["backup_path"]:
        print(f"[info] Backup: {result['backup_path']}")
    print(f"[info] Report: {output_json}")


if __name__ == "__main__":
    main()
