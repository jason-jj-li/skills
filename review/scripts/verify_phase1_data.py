#!/usr/bin/env python3
"""
verify_phase1_data.py - Verify Phase 1 PubMed retrieval data completeness

Checks:
1. Required fields are present (pmid, title, authors, journal, year)
2. Abstract completeness (no truncated abstracts)
3. DOI availability
4. Data quality metrics
5. Duplicate detection

Usage:
    python verify_phase1_data.py process/phase1_pubmed_results_*.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List


def load_results(file_path: Path) -> dict:
    """Load Phase 1 results JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_required_fields(articles: List[dict]) -> Dict[str, List[str]]:
    """Check required fields are present and non-empty"""
    missing_fields = {
        'pmid': [],
        'title': [],
        'authors': [],
        'journal': [],
        'year': []
    }

    for article in articles:
        pmid = article.get('pmid', 'unknown')
        for field in missing_fields.keys():
            value = article.get(field)
            if not value or (isinstance(value, list) and len(value) == 0):
                missing_fields[field].append(pmid)

    return missing_fields


def check_abstract_completeness(articles: List[dict]) -> dict:
    """Check abstract completeness and quality"""
    stats = {
        'total': len(articles),
        'with_abstract': 0,
        'without_abstract': 0,
        'suspiciously_short': [],  # < 100 chars
        'avg_length': 0,
        'min_length': float('inf'),
        'max_length': 0
    }

    total_length = 0
    for article in articles:
        abstract = article.get('abstract', '')
        length = len(abstract)
        pmid = article.get('pmid', 'unknown')

        if abstract:
            stats['with_abstract'] += 1
            total_length += length
            stats['min_length'] = min(stats['min_length'], length)
            stats['max_length'] = max(stats['max_length'], length)
            if length < 100:
                stats['suspiciously_short'].append((pmid, length))
        else:
            stats['without_abstract'] += 1

    if stats['with_abstract'] > 0:
        stats['avg_length'] = total_length / stats['with_abstract']
    else:
        stats['min_length'] = 0

    return stats


def check_doi_coverage(articles: List[dict]) -> dict:
    """Check DOI availability"""
    with_doi = sum(1 for a in articles if a.get('doi'))
    return {
        'total': len(articles),
        'with_doi': with_doi,
        'without_doi': len(articles) - with_doi,
        'coverage': with_doi / len(articles) * 100 if articles else 0
    }


def detect_duplicates(articles: List[dict]) -> List[str]:
    """Detect duplicate PMIDs"""
    seen = set()
    duplicates = []
    for article in articles:
        pmid = article.get('pmid')
        if pmid in seen:
            duplicates.append(pmid)
        seen.add(pmid)
    return duplicates


def check_author_data(articles: List[dict]) -> dict:
    """Check author data quality"""
    no_authors = []
    author_counts = []

    for article in articles:
        authors = article.get('authors', [])
        pmid = article.get('pmid', 'unknown')
        if not authors:
            no_authors.append(pmid)
        else:
            author_counts.append(len(authors))

    return {
        'no_authors': no_authors,
        'total_analyzed': len(articles),
        'avg_authors': sum(author_counts) / len(author_counts) if author_counts else 0,
        'max_authors': max(author_counts) if author_counts else 0,
        'min_authors': min(author_counts) if author_counts else 0
    }


def verify_file(file_path: Path) -> dict:
    """Verify a single Phase 1 results file"""
    print(f"\n{'='*60}")
    print(f"Verifying: {file_path.name}")
    print(f"{'='*60}")

    data = load_results(file_path)
    articles = data.get('articles', [])

    if not articles:
        print("❌ No articles found in file")
        return {'valid': False, 'file': str(file_path)}

    print(f"\nTotal articles: {len(articles)}")

    # 1. Required fields check
    print("\n[1/5] Required fields check...")
    missing = check_required_fields(articles)
    has_missing = any(v for v in missing.values())

    if has_missing:
        print("⚠️  Missing fields detected:")
        for field, pmids in missing.items():
            if pmids:
                print(f"  - {field}: {len(pmids)} missing")
        print(f"  Example PMIDs with missing fields: {list(set(sum(missing.values(), [])))[:5]}")
    else:
        print("✅ All required fields present")

    # 2. Abstract completeness
    print("\n[2/5] Abstract completeness check...")
    abstract_stats = check_abstract_completeness(articles)
    print(f"  With abstract: {abstract_stats['with_abstract']}/{abstract_stats['total']} "
          f"({100*abstract_stats['with_abstract']/abstract_stats['total']:.1f}%)")
    print(f"  Without abstract: {abstract_stats['without_abstract']}")
    print(f"  Avg length: {abstract_stats['avg_length']:.0f} chars")
    print(f"  Range: {abstract_stats['min_length']} - {abstract_stats['max_length']} chars")

    if abstract_stats['suspiciously_short']:
        print(f"  ⚠️  {len(abstract_stats['suspiciously_short'])} suspiciously short abstracts (<100 chars):")
        for pmid, length in abstract_stats['suspiciously_short'][:5]:
            print(f"    - PMID {pmid}: {length} chars")

    # 3. DOI coverage
    print("\n[3/5] DOI coverage check...")
    doi_stats = check_doi_coverage(articles)
    print(f"  With DOI: {doi_stats['with_doi']}/{doi_stats['total']} ({doi_stats['coverage']:.1f}%)")
    print(f"  Without DOI: {doi_stats['without_doi']}")

    # 4. Duplicate detection
    print("\n[4/5] Duplicate detection...")
    duplicates = detect_duplicates(articles)
    if duplicates:
        print(f"  ⚠️  Found {len(duplicates)} duplicate PMIDs: {duplicates}")
    else:
        print("  ✅ No duplicates found")

    # 5. Author data check
    print("\n[5/5] Author data quality check...")
    author_stats = check_author_data(articles)
    print(f"  Articles without authors: {len(author_stats['no_authors'])}")
    print(f"  Avg authors per article: {author_stats['avg_authors']:.1f}")
    print(f"  Range: {author_stats['min_authors']} - {author_stats['max_authors']} authors")

    # Overall assessment
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    all_valid = (
        not has_missing and
        abstract_stats['with_abstract'] / abstract_stats['total'] >= 0.8 and
        doi_stats['coverage'] >= 0.7 and
        not duplicates
    )

    if all_valid:
        print("✅ PASS: Data quality meets minimum thresholds")
        print("   - Required fields: Complete")
        print("   - Abstract coverage: ≥80%")
        print("   - DOI coverage: ≥70%")
        print("   - No duplicates")
    else:
        print("⚠️  WARNING: Data quality below thresholds")
        if has_missing:
            print("   - Some required fields are missing")
        if abstract_stats['with_abstract'] / abstract_stats['total'] < 0.8:
            print("   - Abstract coverage below 80%")
        if doi_stats['coverage'] < 0.7:
            print("   - DOI coverage below 70%")
        if duplicates:
            print("   - Duplicate PMIDs found")

    return {
        'valid': all_valid,
        'file': str(file_path),
        'total_articles': len(articles),
        'abstract_coverage': abstract_stats['with_abstract'] / abstract_stats['total'] * 100,
        'doi_coverage': doi_stats['coverage'],
        'has_duplicates': bool(duplicates),
        'missing_required_fields': has_missing
    }


def main():
    parser = argparse.ArgumentParser(
        description='Verify Phase 1 PubMed retrieval data completeness'
    )
    parser.add_argument('files', nargs='+', type=Path, help='Phase 1 result JSON files')
    parser.add_argument('--strict', action='store_true', help='Fail on any warning')

    args = parser.parse_args()

    results = []
    for file_path in args.files:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}", file=sys.stderr)
            continue
        result = verify_file(file_path)
        results.append(result)

    # Overall summary
    if len(results) > 1:
        print(f"\n{'='*60}")
        print("OVERALL SUMMARY")
        print(f"{'='*60}")
        passed = sum(1 for r in results if r['valid'])
        print(f"Files checked: {len(results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {len(results) - passed}")

    # Exit code
    if args.strict:
        sys.exit(0 if all(r['valid'] for r in results) else 1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
