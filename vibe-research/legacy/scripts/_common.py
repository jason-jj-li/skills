"""Shared utilities for vibe-research scripts.

Centralises helpers that were previously duplicated across 20+ scripts.
Import with: ``from _common import load_json, save_json, utc_now, ...``
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOP_TIER_HINTS = (
    "lancet", "nejm", "jama", "bmj", "nature",
    "science", "cell", "annals of internal medicine",
    "plos medicine", "circulation", "european heart journal",
    "gut", "brain", "annals of neurology",
    "academy of management journal", "academy of management review",
    "american economic review", "quarterly journal of economics",
    "american journal of sociology", "american sociological review",
)

ABBREVIATION_RE = re.compile(
    r"\b(?:al|vs|Dr|Mr|Mrs|Ms|Prof|etc|eg|ie|No|Fig|Tab|Vol|Jr|Sr|Ref|Eq)\.\s+"
)

# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Markdown / manuscript parsing
# ---------------------------------------------------------------------------


def split_frontmatter(text: str) -> Tuple[str, str]:
    """Split YAML frontmatter from body.  Returns (frontmatter, body)."""
    if not text.startswith("---\n"):
        return "", text
    idx = text.find("\n---\n", 4)
    if idx < 0:
        return "", text
    return text[: idx + 5], text[idx + 5 :]


def split_h1_sections(body: str) -> List[Tuple[str, str]]:
    """Split body text into (title, content) pairs at ``# Heading`` boundaries."""
    matches = list(re.finditer(r"^#\s+(.+?)\s*$", body, flags=re.M))
    if not matches:
        return []
    sections: List[Tuple[str, str]] = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((title, body[start:end].strip()))
    return sections


def split_sentences(text: str) -> List[str]:
    """Split text into sentences.  Handles common abbreviations to reduce mis-splits."""
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    # Protect common abbreviations from being treated as sentence endings
    protected = ABBREVIATION_RE.sub(lambda m: m.group().replace(". ", ".<PROTECT> "), text)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [s.replace("<PROTECT>", "").strip() for s in parts if s.strip()]


# ---------------------------------------------------------------------------
# Contract / intent helpers
# ---------------------------------------------------------------------------


def infer_submission_like(contract: Dict) -> bool:
    intent = contract.get("intent", {}) if isinstance(contract, dict) else {}
    tier = str(intent.get("deliverable_tier", "")).lower()
    quality_bar = str(intent.get("quality_bar", "")).lower()
    return tier == "submission_ready" or quality_bar in {"submission", "top_tier_submission"}


def infer_top_tier_target(contract: Dict) -> bool:
    intent = contract.get("intent", {}) if isinstance(contract, dict) else {}
    quality_bar = str(intent.get("quality_bar", "")).lower()
    if quality_bar == "top_tier_submission":
        return True
    tier = str(intent.get("deliverable_tier", "")).lower()
    journal = str(intent.get("target_journal", "")).lower()
    return tier == "submission_ready" and any(x in journal for x in TOP_TIER_HINTS)


def infer_journal_target(contract: Dict) -> bool:
    intent = contract.get("intent", {}) if isinstance(contract, dict) else {}
    return bool(intent.get("target_journal"))


def bool_policy(policy: Dict, key: str, default: bool) -> bool:
    val = policy.get(key)
    if val is None:
        return default
    return bool(val)


def resolve_gate_policy(contract: Dict) -> Dict[str, bool]:
    """Derive which gates are required from the project contract."""
    journal_target = infer_journal_target(contract)
    top_tier_target = infer_top_tier_target(contract)
    submission_like = infer_submission_like(contract)

    policy = contract.get("gate_policy", {}) if isinstance(contract, dict) else {}
    if not isinstance(policy, dict):
        policy = {}

    return {
        "journal_target": journal_target,
        "top_tier_target": top_tier_target,
        "submission_like": submission_like,
        "target_gate_required": bool_policy(policy, "target_gate_required", journal_target),
        "content_focus_gate_required": bool_policy(policy, "content_focus_gate_required", submission_like),
        "citation_architecture_gate_required": bool_policy(policy, "citation_architecture_gate_required", submission_like),
        "field_progress_gate_required": bool_policy(policy, "field_progress_gate_required", submission_like),
        "claim_traceability_gate_required": bool_policy(policy, "claim_traceability_gate_required", submission_like),
        "main_supplement_split_required": bool_policy(policy, "main_supplement_split_required", submission_like),
        "triad_review_required": bool_policy(policy, "triad_review_required", top_tier_target),
        "writing_superloop_required": bool_policy(policy, "writing_superloop_required", top_tier_target),
    }
