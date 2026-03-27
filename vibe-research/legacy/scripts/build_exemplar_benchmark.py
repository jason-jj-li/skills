#!/usr/bin/env python3
"""
Build exemplar benchmark pack from target journal / neighbor journals before execution.

Outputs:
- process/exemplar_benchmark.json
- process/exemplar_benchmark.md
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from _common import TOP_TIER_HINTS, load_json, save_json, utc_now

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def save_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def esearch(term: str, retmax: int = 20) -> Tuple[int, List[str]]:
    params = {"db": "pubmed", "term": term, "retmode": "json", "retmax": retmax}
    try:
        resp = requests.get(f"{EUTILS}/esearch.fcgi", params=params, timeout=40)
        resp.raise_for_status()
        data = resp.json()["esearchresult"]
        return int(data.get("count", 0)), data.get("idlist", [])
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"[warning] PubMed esearch failed: {exc}")
        return 0, []

def efetch(pmids: List[str]) -> str:
    if not pmids:
        return ""
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    try:
        resp = requests.get(f"{EUTILS}/efetch.fcgi", params=params, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        print(f"[warning] PubMed efetch failed: {exc}")
        return ""

def infer_method_clause(method_preference: str, selected_mode: str) -> str:
    m = (method_preference or "") + " " + (selected_mode or "")
    m = m.lower()
    if "meta" in m:
        return '("Meta-Analysis"[Publication Type] OR "meta-analysis"[Title] OR "systematic review"[Title])'
    if "scoping" in m:
        return '("scoping review"[Title/Abstract] OR "evidence map"[Title/Abstract] OR "systematic review"[Title])'
    return '("systematic review"[Title/Abstract] OR "evidence synthesis"[Title/Abstract] OR "meta-analysis"[Title])'

def infer_topic_clause(request_text: str) -> str:
    t = request_text.lower()
    parts: List[str] = []

    if "生命历程" in request_text or "life-course" in t or "life course" in t:
        parts.append('("life course"[Title/Abstract] OR life-course[Title/Abstract] OR "early life"[Title/Abstract])')
    if "aces" in t or "adverse childhood" in t or "childhood adversity" in t or "童年" in request_text:
        parts.append('("adverse childhood experiences"[Title/Abstract] OR ACEs[Title/Abstract] OR "childhood adversity"[Title/Abstract])')
    if "stroke" in t or "卒中" in request_text:
        parts.append('(stroke[Title/Abstract] OR cerebrovascular[Title/Abstract])')
    if "dementia" in t or "认知" in request_text or "痴呆" in request_text:
        parts.append('(dementia[Title/Abstract] OR "cognitive impairment"[Title/Abstract])')

    # Fallback: mine simple English tokens from request
    if not parts:
        stop = {
            "the",
            "and",
            "with",
            "for",
            "from",
            "that",
            "this",
            "meta",
            "analysis",
            "journal",
            "public",
            "health",
            "lancet",
            "write",
            "paper",
            "pdf",
            "topic",
            "related",
            "benchmark",
        }
        tokens = re.findall(r"[a-z][a-z\-]{3,}", t)
        tokens = [x for x in tokens if x not in stop]
        uniq: List[str] = []
        seen = set()
        for tok in tokens:
            if tok not in seen:
                uniq.append(tok)
                seen.add(tok)
            if len(uniq) >= 5:
                break
        if uniq:
            parts.append("(" + " OR ".join(f"{w}[Title/Abstract]" for w in uniq) + ")")

    return " AND ".join(parts)

def journal_clause(target_journal: str) -> str:
    t = (target_journal or "").strip().lower()
    if "lancet public health" in t:
        return '"Lancet Public Health"[Journal]'
    if t == "the lancet" or t == "lancet":
        return '"Lancet"[Journal]'
    if "jama" in t:
        return '"JAMA"[Journal]'
    if "bmj" in t:
        return '"BMJ"[Journal]'
    if "nejm" in t:
        return '"N Engl J Med"[Journal]'
    if "nature" in t:
        return '"Nature"[Journal]'
    if target_journal:
        return f'"{target_journal}"[Journal]'
    return '"Lancet Public Health"[Journal]'

def neighbor_journal_clause() -> str:
    neighbors = [
        '"Lancet Public Health"[Journal]',
        '"Lancet"[Journal]',
        '"BMJ"[Journal]',
        '"JAMA"[Journal]',
        '"JAMA Netw Open"[Journal]',
        '"Am J Epidemiol"[Journal]',
        '"Int J Epidemiol"[Journal]',
        '"Epidemiology"[Journal]',
        '"PLoS Med"[Journal]',
    ]
    return "(" + " OR ".join(neighbors) + ")"

def parse_article(article: ET.Element) -> Dict:
    pmid = article.findtext(".//PMID", default="")
    title = " ".join("".join(article.findtext(".//ArticleTitle", default="")).split())
    journal = article.findtext(".//Journal/Title", default="")
    year = article.findtext(".//JournalIssue/PubDate/Year", default="")
    if not year:
        year = article.findtext(".//ArticleDate/Year", default="")

    doi = ""
    for aid in article.findall(".//ArticleId"):
        if (aid.attrib.get("IdType") or "").lower() == "doi":
            doi = (aid.text or "").strip()
            break

    sections = []
    full_abs = []
    for a in article.findall(".//Abstract/AbstractText"):
        label = (a.attrib.get("Label") or "").strip()
        txt = re.sub(r"\s+", " ", " ".join(a.itertext())).strip()
        if txt:
            sections.append({"label": label, "text": txt})
            full_abs.append(txt)

    abs_text = " ".join(full_abs)
    lower = abs_text.lower()

    signals = {
        "registration_or_prospero": bool(re.search(r"prospero|registration|registered", lower)),
        "random_effects": bool(re.search(r"random[- ]effects?", lower)),
        "heterogeneity_i2": bool(re.search(r"\bi2\b|heterogeneity", lower)),
        "publication_bias_or_funnel": bool(re.search(r"publication bias|funnel", lower)),
        "risk_of_bias_tool": bool(re.search(r"risk of bias|newcastle[- ]ottawa|robins|cochrane", lower)),
        "grade_or_certainty": bool(re.search(r"grade|certainty of evidence", lower)),
        "funding_statement": bool(re.search(r"funding", lower)),
        "structured_abstract": len(sections) >= 2 and any(s.get("label") for s in sections),
    }

    return {
        "pmid": pmid,
        "title": title,
        "journal": journal,
        "year": year,
        "doi": doi,
        "abstract_sections": sections,
        "signals": signals,
    }

def build_md(payload: Dict) -> str:
    lines: List[str] = []
    lines.append("# Exemplar Benchmark")
    lines.append("")
    lines.append(f"- Generated at: {payload['generated_at']}")
    lines.append(f"- Target journal: {payload['target_journal']}")
    lines.append(f"- Method target: {payload['method_target']}")
    lines.append("")
    lines.append("## Query Log")
    lines.append("")
    lines.append("| Query Tier | Hit Count | Used PMIDs |")
    lines.append("|---|---:|---:|")
    for q in payload.get("query_log", []):
        lines.append(f"| {q['tier']} | {q['count']} | {q['used_pmids']} |")

    lines.append("")
    lines.append("## Exemplars")
    lines.append("")
    lines.append("| PMID | Year | Journal | Title |")
    lines.append("|---|---:|---|---|")
    for ex in payload.get("exemplars", []):
        title = ex.get("title", "").replace("|", " ")
        lines.append(f"| {ex.get('pmid','')} | {ex.get('year','')} | {ex.get('journal','')} | {title} |")

    lines.append("")
    lines.append("## Pattern Summary")
    lines.append("")
    summary = payload.get("summary", {})
    lines.append(f"- Exemplar count: {summary.get('n_exemplars', 0)}")
    labels = summary.get("common_abstract_labels", [])
    if labels:
        lines.append("- Common abstract labels: " + ", ".join(f"{x['label']}({x['count']})" for x in labels))
    sigs = summary.get("signal_counts", {})
    if sigs:
        lines.append("- Method/reporting signals:")
        for k, v in sigs.items():
            lines.append(f"  - {k}: {v}")

    lines.append("")
    lines.append("## Planning Hints")
    lines.append("")
    for h in payload.get("planning_hints", []):
        lines.append(f"- {h}")

    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Build exemplar benchmark from target/neighbor journals.")
    parser.add_argument("--contract", type=Path, default=Path("process/project_contract.json"))
    parser.add_argument("--mode-decision", type=Path, default=Path("process/mode_decision.json"))
    parser.add_argument("--max-exemplars", type=int, default=6)
    parser.add_argument("--output-json", type=Path, default=Path("process/exemplar_benchmark.json"))
    parser.add_argument("--output-md", type=Path, default=Path("process/exemplar_benchmark.md"))
    args = parser.parse_args()

    contract = load_json(args.contract.resolve())
    mode = load_json(args.mode_decision.resolve()) if args.mode_decision.resolve().exists() else {}

    intent = contract.get("intent", {})
    target_journal = intent.get("target_journal", "")
    request_text = contract.get("request_text", "")
    method_pref = intent.get("method_preference", "auto")
    selected_mode = mode.get("decision", {}).get("selected_mode", "")

    method_q = infer_method_clause(method_pref, selected_mode)
    topic_q = infer_topic_clause(request_text)
    same_journal = journal_clause(target_journal)
    neighbor_journals = neighbor_journal_clause()

    queries: List[Tuple[str, str]] = []
    if topic_q:
        queries.append(("same_journal_method_topic", f"{same_journal} AND {method_q} AND ({topic_q})"))
    queries.append(("same_journal_method", f"{same_journal} AND {method_q}"))
    if topic_q:
        queries.append(("neighbor_method_topic", f"{neighbor_journals} AND {method_q} AND ({topic_q})"))
    queries.append(("neighbor_method", f"{neighbor_journals} AND {method_q}"))

    query_log: List[Dict] = []
    selected_pmids: List[str] = []
    seen = set()

    for tier, q in queries:
        count, ids = esearch(q, retmax=max(20, args.max_exemplars * 4))
        used = 0
        for pmid in ids:
            if pmid not in seen and len(selected_pmids) < args.max_exemplars:
                selected_pmids.append(pmid)
                seen.add(pmid)
                used += 1
        query_log.append({"tier": tier, "query": q, "count": count, "used_pmids": used})
        if len(selected_pmids) >= args.max_exemplars:
            break

    xml_text = efetch(selected_pmids)
    exemplars: List[Dict] = []
    if xml_text:
        root = ET.fromstring(xml_text)
        for article in root.findall(".//PubmedArticle"):
            exemplars.append(parse_article(article))

    label_counter = Counter()
    signal_counter = Counter()
    for ex in exemplars:
        for sec in ex.get("abstract_sections", []):
            label = (sec.get("label") or "").strip()
            if label:
                label_counter[label] += 1
        for k, v in ex.get("signals", {}).items():
            if v:
                signal_counter[k] += 1

    hints: List[str] = []
    if signal_counter.get("structured_abstract", 0) >= max(1, len(exemplars) // 2):
        hints.append("Use structured abstract/headings aligned to journal style (e.g., Background/Methods/Findings/Interpretation/Funding).")
    if signal_counter.get("random_effects", 0) > 0:
        hints.append("Describe random-effects framework explicitly and justify heterogeneity handling.")
    if signal_counter.get("heterogeneity_i2", 0) > 0:
        hints.append("Report heterogeneity statistics (I2, tau2, Q-test) and preplanned sensitivity analyses.")
    if signal_counter.get("risk_of_bias_tool", 0) > 0:
        hints.append("Specify risk-of-bias tool and ensure study-level bias reporting in main text or supplement.")
    if signal_counter.get("registration_or_prospero", 0) > 0:
        hints.append("State registration/protocol status clearly (PROSPERO or equivalent).")
    if not hints:
        hints.append("Exemplar abstracts are weakly method-explicit; prioritize full-text method extraction before drafting.")

    payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "target_journal": target_journal,
        "method_target": selected_mode or method_pref,
        "quality_bar": intent.get("quality_bar", "unknown"),
        "query_log": query_log,
        "exemplars": exemplars,
        "summary": {
            "n_exemplars": len(exemplars),
            "common_abstract_labels": [
                {"label": k, "count": v} for k, v in label_counter.most_common(8)
            ],
            "signal_counts": dict(signal_counter),
        },
        "planning_hints": hints,
        "inference": {
            "is_top_tier_target": any(x in (target_journal or "").lower() for x in TOP_TIER_HINTS),
            "confidence": "medium" if exemplars else "low",
        },
    }

    save_json(args.output_json.resolve(), payload)
    save_md(args.output_md.resolve(), build_md(payload))

    print(f"Exemplar benchmark JSON: {args.output_json.resolve()}")
    print(f"Exemplar benchmark MD: {args.output_md.resolve()}")
    print(f"exemplars={len(exemplars)}")

if __name__ == "__main__":
    main()
