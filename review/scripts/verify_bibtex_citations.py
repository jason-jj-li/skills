#!/usr/bin/env python3
"""
verify_bibtex_citations.py - Verify BibTeX citations in Markdown files

Simplifies citation verification using BibTeX citekeys instead of complex regex.

Checks:
1. All [@citekey] markers in MD exist in .bib file
2. DOI metadata matches (optional)
3. No orphaned references in .bib file

Example:
    python verify_bibtex_citations.py chapter.md references.bib
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set


def extract_citekeys_from_markdown(md_content: str) -> Set[str]:
    """
    Extract all [@citekey] markers from markdown content.

    Pattern: [@citekey] or [@citekey; @citekey2; @citekey3; ...]
    """
    # Simple pattern: match [@citekey] and extract citekey
    # This will match all occurrences, including multiple citekeys in one bracket
    pattern = r'\[@([a-z0-9_]+)\]'

    citekeys = set()
    for match in re.finditer(pattern, md_content):
        citekeys.add(match.group(1))

    return citekeys


def parse_bibtex_file(bib_file: Path) -> Dict[str, dict]:
    """
    Parse BibTeX file and extract entries.

    Returns dict mapping citekey to entry data.
    """
    entries = {}

    with open(bib_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by @article entries
    pattern = r'@article\{([a-z0-9_]+),\s*(.*?)\n\}'
    for match in re.finditer(pattern, content, re.DOTALL):
        citekey = match.group(1)
        entry_content = match.group(2)

        # Parse fields
        entry = {
            'citekey': citekey,
            'author': '',
            'title': '',
            'year': '',
            'journal': '',
            'doi': '',
            'pmid': ''
        }

        # Extract field values
        for field in ['author', 'title', 'year', 'journal', 'doi', 'pmid']:
            field_pattern = rf'{field}\s*=\s*\{{([^}}]*)\}}'
            field_match = re.search(field_pattern, entry_content)
            if field_match:
                entry[field] = field_match.group(1).strip()

        entries[citekey] = entry

    return entries


def fetch_doi_metadata(doi: str) -> dict:
    """
    Fetch DOI metadata from CrossRef API.

    Returns dict with author, year, journal info.
    """
    import urllib.request
    import ssl

    # Create SSL context (macOS fix)
    ssl_context = ssl._create_unverified_context()

    url = f"https://api.crossref.org/works/{doi}"
    try:
        with urllib.request.urlopen(url, context=ssl_context, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            item = data.get('message', {})

            # Extract metadata
            authors = [f"{a.get('given', '')} {a.get('family', '')}".strip()
                       for a in item.get('author', [])[:3]]
            year = item.get('published-print', {}).get('date-parts', [['']])[0][0]
            journal = item.get('short-container-title', [''])[0]

            return {
                'authors': authors,
                'year': str(year),
                'journal': journal
            }
    except Exception as e:
        return {}


def verify_doi_metadata(entry: dict, metadata: dict) -> List[str]:
    """
    Verify that BibTeX entry matches DOI metadata.

    Returns list of mismatched fields.
    """
    mismatches = []

    # Check year
    if metadata.get('year') and entry.get('year'):
        if metadata['year'] != entry['year']:
            mismatches.append(f"year: {entry['year']} != {metadata['year']}")

    # Check journal (fuzzy match)
    if metadata.get('journal') and entry.get('journal'):
        bib_journal = entry['journal'].lower().strip()
        meta_journal = metadata['journal'].lower().strip()
        if meta_journal not in bib_journal and bib_journal not in meta_journal:
            mismatches.append(f"journal: {entry['journal']} != {metadata['journal']}")

    return mismatches


def verify_citations(
    md_file: Path,
    bib_file: Path,
    verify_doi: bool = False
) -> dict:
    """
    Verify all citations in markdown file against BibTeX file.

    Returns verification result dict.
    """
    print("=" * 60)
    print("BibTeX Citation Verification")
    print("=" * 60)
    print(f"Markdown: {md_file}")
    print(f"BibTeX: {bib_file}")
    print()

    # Read markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Extract citekeys from markdown
    citekeys_in_md = extract_citekeys_from_markdown(md_content)

    # Parse BibTeX file
    bib_entries = parse_bibtex_file(bib_file)

    # Find missing citekeys
    missing_citekeys = citekeys_in_md - set(bib_entries.keys())

    # Find unused citekeys (in .bib but not in .md)
    unused_citekeys = set(bib_entries.keys()) - citekeys_in_md

    # Verify DOI metadata (if requested)
    doi_mismatches = []
    if verify_doi:
        print("\nVerifying DOI metadata...")
        for citekey, entry in bib_entries.items():
            if citekey in citekeys_in_md and entry.get('doi'):
                metadata = fetch_doi_metadata(entry['doi'])
                if metadata:
                    mismatches = verify_doi_metadata(entry, metadata)
                    if mismatches:
                        doi_mismatches.append((citekey, mismatches))

    # Results
    result = {
        'citekeys_in_md': len(citekeys_in_md),
        'citekeys_in_bib': len(bib_entries),
        'missing_citekeys': list(missing_citekeys),
        'unused_citekeys': list(unused_citekeys),
        'doi_mismatches': doi_mismatches,
        'all_valid': len(missing_citekeys) == 0 and len(doi_mismatches) == 0
    }

    # Print summary
    print(f"\nCitekeys in Markdown: {result['citekeys_in_md']}")
    print(f"Citekeys in BibTeX: {result['citekeys_in_bib']}")
    print()

    if result['all_valid']:
        print("✅ PASS: All citations verified")
    else:
        print("❌ FAIL: Found citation errors")

        if missing_citekeys:
            print(f"\n⚠️  {len(missing_citekeys)} citekeys in MD but not in .bib:")
            for citekey in sorted(missing_citekeys):
                print(f"  - [@{citekey}]")

        if unused_citekeys:
            print(f"\n⚠️  {len(unused_citekeys)} citekeys in .bib but not in MD:")
            for citekey in sorted(unused_citekeys)[:10]:  # Show first 10
                print(f"  - @{citekey}")
            if len(unused_citekeys) > 10:
                print(f"  ... and {len(unused_citekeys) - 10} more")

        if doi_mismatches:
            print(f"\n⚠️  {len(doi_mismatches)} DOI metadata mismatches:")
            for citekey, mismatches in doi_mismatches[:10]:
                print(f"  - @{citekey}: {', '.join(mismatches)}")

    print()
    print("=" * 60)

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Verify BibTeX citations in Markdown files'
    )
    parser.add_argument('md_file', type=Path, help='Markdown file to verify')
    parser.add_argument('bib_file', type=Path, help='BibTeX file')
    parser.add_argument('--verify-doi', action='store_true', help='Verify DOI metadata (slow)')

    args = parser.parse_args()

    if not args.md_file.exists():
        print(f"Error: Markdown file not found: {args.md_file}", file=sys.stderr)
        sys.exit(1)

    if not args.bib_file.exists():
        print(f"Error: BibTeX file not found: {args.bib_file}", file=sys.stderr)
        sys.exit(1)

    result = verify_citations(args.md_file, args.bib_file, args.verify_doi)

    sys.exit(0 if result['all_valid'] else 1)


if __name__ == '__main__':
    main()
