#!/usr/bin/env python3
"""
Build a machine-readable project contract from a user request.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from _common import utc_now, TOP_TIER_HINTS

DELIVERABLE_HINTS = {
    "submission_ready": [
        "submission",
        "submit",
        "journal",
        "review",
        "peer review",
        "审稿",
        "投稿",
        "发表",
        "可直接提交",
        "lancet",
        "nejm",
        "jama",
        "bmj",
    ],
    "draft": [
        "draft",
        "初稿",
        "草稿",
        "outline",
        "提纲",
    ],
    "explore": [
        "explore",
        "探索",
        "brainstorm",
        "test",
        "测试",
        "try",
        "试试",
    ],
}

NEGATIVE_SUBMISSION_HINTS = [
    "不投稿",
    "不要求投稿",
    "不需要投稿",
    "无需投稿",
    "不发表",
    "不要求发表",
    "不需要发表",
    "无需发表",
    "not for submission",
    "no submission",
    "no publish",
    "not publishable",
]

METHOD_HINTS = {
    "meta_analysis": ["meta-analysis", "meta analysis", "荟萃", "元分析", "meta"],
    "systematic_review": ["systematic review", "系统综述", "sys review"],
    "scoping_review": ["scoping review", "范围综述"],
    "evidence_gap_map": ["gap map", "evidence gap", "证据缺口"],
    "protocol": ["protocol", "方案", "registered protocol"],
}

STANDARD_HINTS = {
    "PRISMA": ["prisma"],
    "MOOSE": ["moose"],
    "STROBE": ["strobe"],
    "CONSORT": ["consort"],
    "Cochrane": ["cochrane"],
}

JOURNAL_HINTS = [
    "lancet public health",
    "lancet",
    "nejm",
    "jama",
    "bmj",
    "nature",
    "science",
    "cell",
    "annals of internal medicine",
    "plos medicine",
    "circulation",
    "european heart journal",
    "gut",
    "brain",
    "annals of neurology",
    "academy of management journal",
    "academy of management review",
    "american economic review",
    "quarterly journal of economics",
    "american journal of sociology",
    "american sociological review",
]

# Use centralised list from _common
TOP_TIER_JOURNAL_HINTS = TOP_TIER_HINTS

INNOVATION_HINTS = [
    "innovative",
    "innovation",
    "novel",
    "novelty",
    "gap",
    "underexplored",
    "未写",
    "创新",
    "新颖",
    "别人没写",
]

QUALITY_HINTS = [
    "high quality",
    "rigorous",
    "robust",
    "publishable",
    "top-tier",
    "顶刊",
    "高质量",
    "可投稿",
]

TOP_TIER_INTENT_HINTS = [
    "top-tier",
    "top tier",
    "high-impact",
    "high impact",
    "顶刊",
]

NON_RESEARCH_HINTS = [
    "write me a poem",
    "write a poem",
    "tell me a joke",
    "tell a joke",
    "write a story",
    "translate this",
    "翻译",
    "写诗",
    "讲笑话",
    "help me debug",
    "fix my code",
    "calendar",
    "schedule",
    "weather",
    "recipe",
    "cooking",
]

def load_text(text: Optional[str], from_file: Optional[Path]) -> str:
    if from_file:
        return from_file.read_text(encoding="utf-8")
    if text:
        return text
    return ""

def contains_any(haystack: str, needles: List[str]) -> bool:
    return any(n in haystack for n in needles)

def infer_deliverable_tier(text: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    t = text.lower()
    if contains_any(t, NEGATIVE_SUBMISSION_HINTS):
        if contains_any(t, DELIVERABLE_HINTS["draft"]):
            return "draft"
        return "explore"
    if contains_any(t, DELIVERABLE_HINTS["submission_ready"]):
        return "submission_ready"
    if contains_any(t, DELIVERABLE_HINTS["draft"]):
        return "draft"
    if contains_any(t, DELIVERABLE_HINTS["explore"]):
        return "explore"
    return "unknown"

def infer_method_preference(text: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    t = text.lower()
    for method, hints in METHOD_HINTS.items():
        if contains_any(t, hints):
            return method
    return "auto"

def infer_reporting_standards(text: str, explicit: List[str]) -> List[str]:
    if explicit:
        return sorted(set(explicit))
    t = text.lower()
    out: List[str] = []
    for standard, hints in STANDARD_HINTS.items():
        if contains_any(t, hints):
            out.append(standard)
    return out

def infer_target_journal(text: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    t = text.lower()
    for journal in JOURNAL_HINTS:
        if journal in t:
            if journal == "lancet":
                return "The Lancet"
            if journal == "lancet public health":
                return "The Lancet Public Health"
            if journal in {"nejm", "jama", "bmj"}:
                return journal.upper()
            return journal.title()
    return ""

def infer_language(text: str) -> str:
    if not text.strip():
        return "unknown"
    # CJK Unified Ideographs + Japanese Hiragana/Katakana + Korean Hangul
    has_cjk = bool(re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    has_alpha = bool(re.search(r"[A-Za-z]", text))
    if has_cjk and has_alpha:
        return "mixed"
    if has_cjk:
        # Distinguish Chinese vs Japanese vs Korean
        has_jp = bool(re.search(r"[\u3040-\u30ff]", text))
        has_kr = bool(re.search(r"[\uac00-\ud7af]", text))
        if has_jp:
            return "ja"
        if has_kr:
            return "ko"
        return "zh"
    if has_alpha:
        return "en"
    return "unknown"

def infer_primary_goal(deliverable_tier: str, method_preference: str) -> str:
    if deliverable_tier == "submission_ready":
        return "publication"
    if method_preference in {"meta_analysis", "systematic_review", "scoping_review", "evidence_gap_map"}:
        return "knowledge_synthesis"
    return "unknown"

def infer_is_research(text: str, deliverable_tier: str, method_preference: str) -> bool:
    """Return False if the request is clearly non-research."""
    t = text.lower()
    if contains_any(t, NON_RESEARCH_HINTS):
        return False
    # If user explicitly specified a research-related tier or method, it's research
    if deliverable_tier in {"submission_ready", "draft"}:
        return True
    if method_preference != "auto":
        return True
    # If any research keyword appears, consider it research
    research_signals = [
        "meta-analysis", "meta analysis", "systematic review", "scoping review",
        "荟萃", "综述", "研究", "evidence", "literature", "pubmed",
        "review", "protocol", "manuscript", "paper", "study",
    ]
    if contains_any(t, research_signals):
        return True
    # Very short non-specific requests are likely not research
    if len(t.split()) < 5 and deliverable_tier == "unknown":
        return False
    return True

def infer_quality_bar(deliverable_tier: str, target_journal: str, request_text: str) -> str:
    if deliverable_tier == "explore":
        return "exploratory"
    if deliverable_tier == "draft":
        return "draft"
    if deliverable_tier == "submission_ready":
        tj = (target_journal or "").lower()
        if any(h in tj for h in TOP_TIER_JOURNAL_HINTS):
            return "top_tier_submission"
        if contains_any(request_text.lower(), TOP_TIER_INTENT_HINTS):
            return "top_tier_submission"
        return "submission"
    return "unknown"

def infer_research_requirement(request_text: str, quality_bar: str) -> str:
    t = request_text.lower()
    need_innovation = contains_any(t, INNOVATION_HINTS)
    need_quality = contains_any(t, QUALITY_HINTS) or quality_bar in {"submission", "top_tier_submission"}
    if quality_bar == "top_tier_submission":
        return "innovation_and_quality"
    if need_innovation and need_quality:
        return "innovation_and_quality"
    if need_innovation:
        return "innovation_priority"
    if need_quality:
        return "quality_priority"
    return "balanced"

def infer_gate_policy(
    deliverable_tier: str,
    quality_bar: str,
    target_journal: str,
    reporting_standards: List[str],
) -> Dict[str, object]:
    journal_targeted = bool((target_journal or "").strip()) or bool(reporting_standards)
    submission_like = deliverable_tier == "submission_ready" or quality_bar in {"submission", "top_tier_submission"}
    top_tier = quality_bar == "top_tier_submission"

    return {
        "target_gate_required": journal_targeted,
        "content_focus_gate_required": submission_like,
        "citation_architecture_gate_required": submission_like,
        "field_progress_gate_required": submission_like,
        "claim_traceability_gate_required": submission_like,
        "main_supplement_split_required": submission_like,
        "triad_review_required": top_tier,
        "writing_superloop_required": top_tier,
        "convergence_policy": "strict" if top_tier else ("standard" if submission_like else "light"),
        "max_major_revision_rounds": 3 if top_tier else (2 if submission_like else 1),
    }

def build_acceptance_criteria(
    deliverable_tier: str,
    quality_bar: str,
    must_compile_pdf: bool,
) -> List[str]:
    criteria = [
        "Selected method must be feasible for available evidence density.",
        "Journal and reporting standards must be documented before execution.",
        "All conclusions must be traceable to retrieved sources.",
    ]
    if quality_bar == "top_tier_submission":
        criteria.append(
            "If routed evidence cannot support target-journal quality bar, stop at routing and return no-go."
        )
    if deliverable_tier == "submission_ready":
        criteria.append("Deliverable must pass submission-grade gate contracts.")
        criteria.append("Main narrative must clearly explain where the field currently stands and what remains unresolved.")
        criteria.append("Quantitative claims in core sections must be citation-traceable.")
    if must_compile_pdf:
        criteria.append("A compileable manuscript PDF must be produced.")
    return criteria

def build_contract(
    request_text: str,
    deliverable_tier: str,
    target_journal: str,
    reporting_standards: List[str],
    method_preference: str,
    allow_mode_switch: bool,
    must_compile_pdf: bool,
) -> Dict:
    must_be_submission_ready = deliverable_tier == "submission_ready"
    quality_bar = infer_quality_bar(deliverable_tier, target_journal, request_text)
    research_requirement = infer_research_requirement(request_text, quality_bar)
    is_research = infer_is_research(request_text, deliverable_tier, method_preference)
    gate_policy = infer_gate_policy(
        deliverable_tier=deliverable_tier,
        quality_bar=quality_bar,
        target_journal=target_journal,
        reporting_standards=reporting_standards,
    )
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "request_text": request_text,
        "is_research": is_research,
        "intent": {
            "deliverable_tier": deliverable_tier,
            "primary_goal": infer_primary_goal(deliverable_tier, method_preference),
            "target_journal": target_journal,
            "reporting_standards": reporting_standards,
            "method_preference": method_preference,
            "quality_bar": quality_bar,
            "research_requirement": research_requirement,
            "language": infer_language(request_text),
        },
        "constraints": {
            "must_compile_pdf": must_compile_pdf,
            "must_be_submission_ready": must_be_submission_ready,
            "allow_mode_switch": allow_mode_switch,
            "stop_on_goal_mismatch": quality_bar == "top_tier_submission",
            "require_innovation_and_quality": research_requirement == "innovation_and_quality",
        },
        "gate_policy": gate_policy,
        "acceptance_criteria": build_acceptance_criteria(deliverable_tier, quality_bar, must_compile_pdf),
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Parse user request into a project contract.")
    parser.add_argument("request_text", nargs="?", help="Raw user request text")
    parser.add_argument("--from-file", type=Path, help="Read request text from file")
    parser.add_argument(
        "--deliverable-tier",
        choices=["explore", "draft", "submission_ready", "unknown"],
        help="Override inferred deliverable tier",
    )
    parser.add_argument("--target-journal", help="Explicit target journal")
    parser.add_argument("--standard", action="append", default=[], help="Reporting standard (repeatable)")
    parser.add_argument(
        "--method-preference",
        choices=["meta_analysis", "systematic_review", "scoping_review", "evidence_gap_map", "protocol", "auto"],
        help="Override method preference",
    )
    parser.add_argument("--must-compile-pdf", action="store_true", help="Require PDF compile in acceptance criteria")
    parser.add_argument("--no-mode-switch", action="store_true", help="Disallow automatic method switching")
    parser.add_argument("--output", type=Path, default=Path("process/project_contract.json"), help="Output JSON path")
    args = parser.parse_args()

    request_text = load_text(args.request_text, args.from_file).strip()
    if not request_text:
        raise SystemExit("Request text is empty. Provide text argument or --from-file.")

    deliverable_tier = infer_deliverable_tier(request_text, args.deliverable_tier)
    method_preference = infer_method_preference(request_text, args.method_preference)
    reporting_standards = infer_reporting_standards(request_text, args.standard)
    target_journal = infer_target_journal(request_text, args.target_journal)

    contract = build_contract(
        request_text=request_text,
        deliverable_tier=deliverable_tier,
        target_journal=target_journal,
        reporting_standards=reporting_standards,
        method_preference=method_preference,
        allow_mode_switch=not args.no_mode_switch,
        must_compile_pdf=args.must_compile_pdf,
    )

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(contract, f, ensure_ascii=False, indent=2)

    print(f"Contract written: {output}")
    print(
        f"tier={contract['intent']['deliverable_tier']} "
        f"method_pref={contract['intent']['method_preference']} "
        f"journal={contract['intent']['target_journal'] or 'N/A'}"
    )

if __name__ == "__main__":
    main()
