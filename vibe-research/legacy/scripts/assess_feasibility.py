#!/usr/bin/env python3
"""
Assess publishability feasibility of candidate topics before method lock.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from _common import load_json, save_json, utc_now, TOP_TIER_HINTS

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# Use centralised list from _common — substring matching (consistent with other scripts)
HIGH_BAR_JOURNALS = TOP_TIER_HINTS

# Module-level offline flag — set by main() when --offline is passed
_OFFLINE = False
EFFECT_RE = re.compile(
    r"(odds ratio|hazard ratio|risk ratio|relative risk|95%\s*ci|or\s*=|hr\s*=|rr\s*=)",
    re.IGNORECASE,
)
AGE_RE = re.compile(
    r"(older|aged|elderly|middle-aged|midlife|late-life|age\s*[4-9][0-9]|45\+|50\+|60\+)",
    re.IGNORECASE,
)

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
    "weights": {
        "novelty": 0.20,
        "evidence_sufficiency": 0.35,
        "extractability": 0.30,
        "journal_fit": 0.15,
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

def load_policy(path: Path | None) -> Dict:
    policy = dict(DEFAULT_POLICY)
    if path and path.exists():
        user_policy = load_json(path)
        policy = merge_dict(policy, user_policy)
    return policy

def eutils_esearch_count(term: str) -> int:
    if _OFFLINE:
        return 0
    try:
        params = {"db": "pubmed", "term": term, "retmode": "json", "rettype": "count"}
        resp = requests.get(f"{EUTILS}/esearch.fcgi", params=params, timeout=40)
        resp.raise_for_status()
        return int(resp.json()["esearchresult"]["count"])
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"[warn] PubMed esearch_count failed ({exc}), returning 0")
        return 0

def eutils_esearch_ids(term: str, retmax: int) -> List[str]:
    if _OFFLINE:
        return []
    try:
        params = {"db": "pubmed", "term": term, "retmode": "json", "retmax": retmax}
        resp = requests.get(f"{EUTILS}/esearch.fcgi", params=params, timeout=40)
        resp.raise_for_status()
        return resp.json()["esearchresult"].get("idlist", [])
    except (requests.RequestException, KeyError) as exc:
        print(f"[warn] PubMed esearch_ids failed ({exc}), returning []")
        return []

def eutils_efetch_abstracts(pmids: List[str]) -> List[str]:
    if not pmids or _OFFLINE:
        return []
    try:
        params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
        resp = requests.get(f"{EUTILS}/efetch.fcgi", params=params, timeout=40)
        resp.raise_for_status()
        xml_text = resp.text
    except requests.RequestException as exc:
        print(f"[warn] PubMed efetch failed ({exc}), returning []")
        return []

    abstracts: List[str] = []
    for chunk in xml_text.split("<AbstractText"):
        if ">" not in chunk:
            continue
        body = chunk.split(">", 1)[1]
        abstract = body.split("</AbstractText>", 1)[0]
        abstract = re.sub(r"<[^>]+>", " ", abstract)
        abstract = re.sub(r"\s+", " ", abstract).strip()
        if abstract:
            abstracts.append(abstract)
    return abstracts

def score_evidence_sufficiency(all_count: int) -> float:
    if all_count < 4:
        return 0.1
    if all_count < 8:
        return 0.25
    if all_count < 15:
        return 0.45
    if all_count < 30:
        return 0.7
    if all_count < 60:
        return 0.9
    return 1.0

def score_novelty(meta_count: int) -> float:
    if meta_count == 0:
        return 1.0
    if meta_count == 1:
        return 0.8
    if meta_count <= 3:
        return 0.6
    if meta_count <= 6:
        return 0.4
    return 0.2

def score_extractability(effect_signal_rate: float) -> float:
    return min(1.0, max(0.0, effect_signal_rate * 2.5))

def score_journal_fit(
    deliverable_tier: str,
    target_journal: str,
    evidence_sufficiency: float,
    extractability: float,
    all_count: int,
) -> float:
    if deliverable_tier != "submission_ready":
        return 0.8
    score = min(evidence_sufficiency, extractability)
    if all_count >= 20:
        score = min(1.0, score + 0.1)
    if any(h in target_journal.strip().lower() for h in HIGH_BAR_JOURNALS) and all_count < 20:
        score = max(0.0, score - 0.1)
    return score

def suggest_mode(all_count: int, effect_signal_rate: float, policy: Dict) -> str:
    th = policy.get("thresholds", {})
    min_n = int(th.get("submission_meta_min_all_count", 15))
    min_eff = float(th.get("submission_meta_min_effect_signal_rate", 0.25))
    if all_count >= min_n and effect_signal_rate >= min_eff:
        return "meta_analysis"
    if all_count >= 8:
        return "systematic_review_no_meta"
    if all_count >= 4:
        return "scoping_review"
    return "evidence_gap_map"

def compute_publishability(
    novelty: float,
    evidence_sufficiency: float,
    extractability: float,
    journal_fit: float,
    weights: Dict,
) -> float:
    w_nov = float(weights.get("novelty", 0.20))
    w_evi = float(weights.get("evidence_sufficiency", 0.35))
    w_ext = float(weights.get("extractability", 0.30))
    w_fit = float(weights.get("journal_fit", 0.15))
    w_sum = w_nov + w_evi + w_ext + w_fit
    if w_sum <= 0:
        w_nov, w_evi, w_ext, w_fit = 0.20, 0.35, 0.30, 0.15
        w_sum = 1.0
    # Normalize user-provided weights.
    w_nov, w_evi, w_ext, w_fit = [x / w_sum for x in (w_nov, w_evi, w_ext, w_fit)]
    score = w_nov * novelty + w_evi * evidence_sufficiency + w_ext * extractability + w_fit * journal_fit
    return round(score, 4)

def parse_candidate_specs(specs: List[str]) -> List[Dict]:
    out: List[Dict] = []
    for raw in specs:
        parts = raw.split("|||")
        if len(parts) != 3:
            print(f"[error] Invalid --candidate format: {raw}")
            print("[hint] Expected format: id|||topic|||query")
            raise SystemExit(1)
        out.append({"id": parts[0].strip(), "topic": parts[1].strip(), "query": parts[2].strip()})
    return out

def load_candidates(candidates_json: Path | None, inline_specs: List[str]) -> List[Dict]:
    candidates: List[Dict] = []
    if candidates_json:
        data = load_json(candidates_json)
        if isinstance(data, dict):
            candidates = data.get("candidates", [])
        elif isinstance(data, list):
            candidates = data
    if inline_specs:
        candidates.extend(parse_candidate_specs(inline_specs))
    if not candidates:
        print("[error] No candidates provided.")
        print("[hint] Use --candidates-json or --candidate 'id|||topic|||query'.")
        raise SystemExit(1)
    for idx, c in enumerate(candidates):
        if not c.get("id"):
            c["id"] = f"topic-{idx+1:02d}"
        if not c.get("topic") or not c.get("query"):
            print(f"[error] Candidate missing topic/query: {c}")
            print("[hint] Each candidate needs at least 'topic' and 'query' fields.")
            raise SystemExit(1)
    return candidates

def evaluate_candidate(
    candidate: Dict,
    deliverable_tier: str,
    target_journal: str,
    sample_size: int,
    policy: Dict,
) -> Dict:
    query = candidate["query"]
    meta_query = f'{query} AND ("Meta-Analysis"[Publication Type] OR "systematic review"[Title])'

    all_count = eutils_esearch_count(query)
    meta_count = eutils_esearch_count(meta_query)
    pmids = eutils_esearch_ids(query, retmax=sample_size)
    abstracts = eutils_efetch_abstracts(pmids)

    if abstracts:
        effect_hits = sum(1 for a in abstracts if EFFECT_RE.search(a))
        age_hits = sum(1 for a in abstracts if AGE_RE.search(a))
        effect_signal_rate = effect_hits / len(abstracts)
        age_fit_rate = age_hits / len(abstracts)
    else:
        effect_signal_rate = 0.0
        age_fit_rate = 0.0

    novelty = score_novelty(meta_count)
    evidence_sufficiency = score_evidence_sufficiency(all_count)
    extractability = score_extractability(effect_signal_rate)
    journal_fit = score_journal_fit(deliverable_tier, target_journal, evidence_sufficiency, extractability, all_count)
    publishability = compute_publishability(
        novelty,
        evidence_sufficiency,
        extractability,
        journal_fit,
        policy.get("weights", {}),
    )

    suggested = suggest_mode(all_count, effect_signal_rate, policy)
    no_go_submission_meta = deliverable_tier == "submission_ready" and suggested != "meta_analysis"

    th = policy.get("thresholds", {})
    min_pub = float(th.get("min_publishability_score", 0.8))
    min_nov = float(th.get("min_novelty_score", 0.85))
    min_fit = float(th.get("min_journal_fit_score", 0.55))
    max_prior_meta = int(th.get("max_prior_meta_count_for_innovation", 1))

    innovation_ready = novelty >= min_nov and meta_count <= max_prior_meta
    quality_ready = publishability >= min_pub and journal_fit >= min_fit
    innovation_and_quality_ready = innovation_ready and quality_ready

    notes: List[str] = []
    if all_count < 8:
        notes.append("Evidence count is sparse for submission-grade synthesis.")
    if effect_signal_rate < 0.25:
        notes.append("Few abstracts show directly extractable effect-size language.")
    if meta_count > 3:
        notes.append("Novelty is moderate due to multiple prior syntheses.")
    if not innovation_ready:
        notes.append("Innovation bar not met under current threshold profile.")
    if not quality_ready:
        notes.append("Quality bar not met under current threshold profile.")
    if no_go_submission_meta:
        notes.append("No-Go for submission-grade meta-analysis; pivot recommended.")

    return {
        "id": candidate["id"],
        "topic": candidate["topic"],
        "query": candidate["query"],
        "metrics": {
            "all_count": all_count,
            "meta_count": meta_count,
            "sample_size": len(abstracts),
            "effect_signal_rate": round(effect_signal_rate, 4),
            "age_fit_rate": round(age_fit_rate, 4),
        },
        "scores": {
            "novelty": round(novelty, 4),
            "evidence_sufficiency": round(evidence_sufficiency, 4),
            "extractability": round(extractability, 4),
            "journal_fit": round(journal_fit, 4),
            "publishability": publishability,
        },
        "flags": {
            "innovation_ready": innovation_ready,
            "quality_ready": quality_ready,
            "innovation_and_quality_ready": innovation_and_quality_ready,
        },
        "suggested_mode": suggested,
        "no_go_for_submission_meta": no_go_submission_meta,
        "notes": notes,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Assess topic feasibility and publishability before method lock.")
    parser.add_argument("--contract", type=Path, default=Path("process/project_contract.json"), help="Project contract JSON")
    parser.add_argument("--candidates-json", type=Path, help="Candidates JSON file")
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="Candidate as 'id|||topic|||query' (repeatable)",
    )
    parser.add_argument("--sample-size", type=int, default=40, help="EFetch sample size for extractability signals")
    parser.add_argument(
        "--thresholds-json",
        type=Path,
        help="Optional thresholds/weights JSON (defaults to process/decision_thresholds.json if present)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("process/feasibility_report.json"),
        help="Output feasibility report JSON",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip PubMed API calls; generate stub metrics with zeros",
    )
    args = parser.parse_args()

    global _OFFLINE
    _OFFLINE = args.offline

    contract = load_json(args.contract.resolve())
    intent = contract.get("intent", {})
    deliverable_tier = intent.get("deliverable_tier", "unknown")
    target_journal = intent.get("target_journal", "")
    default_policy_path = args.contract.resolve().parent / "decision_thresholds.json"
    policy_path = args.thresholds_json.resolve() if args.thresholds_json else default_policy_path
    policy = load_policy(policy_path if policy_path.exists() else None)

    candidates = load_candidates(args.candidates_json.resolve() if args.candidates_json else None, args.candidate)
    evaluated = [evaluate_candidate(c, deliverable_tier, target_journal, args.sample_size, policy) for c in candidates]
    ranking = [r["id"] for r in sorted(evaluated, key=lambda x: x["scores"]["publishability"], reverse=True)]

    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "contract_file": str(args.contract.resolve()),
        "source": "pubmed_eutils",
        "policy_file": str(policy_path) if policy_path.exists() else "",
        "policy_used": policy,
        "candidates": evaluated,
        "ranking": ranking,
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    save_json(output, report)

    best = sorted(evaluated, key=lambda x: x["scores"]["publishability"], reverse=True)[0]
    print(f"Feasibility report written: {output}")
    print(
        f"best={best['id']} mode={best['suggested_mode']} "
        f"publishability={best['scores']['publishability']}"
    )

if __name__ == "__main__":
    main()
