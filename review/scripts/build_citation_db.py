#!/usr/bin/env python3
"""
build_citation_db.py - Generate citation database from Phase 1 results

Creates a citation database that ensures ALL citations in Phase 4 writing
come from verified Phase 1 retrieval results only.

Output format:
{
  "citations": [
    {
      "pmid": "33071239",
      "short_cite": "(Yu et al., 2021)",
      "full_reference": "..."
    }
  ]
}
"""

import argparse
import json
import sys
from pathlib import Path


def generate_citekey(authors: list, year: str, title: str) -> str:
    """Generate citekey for BibTeX: {surname}{year}_{first_word}"""
    import re
    import string

    if not authors:
        return f"unknown{year}_article"

    # Get first author's surname
    first_author = authors[0]
    surname = first_author.split(',')[0].strip() if ',' in first_author else first_author.split()[0]
    surname = surname.lower()

    # Get first word from title
    title_words = title.strip().split()
    first_word = title_words[0].lower().strip(string.punctuation) if title_words else "article"

    # Remove special characters
    first_word = re.sub(r'[^\w]', '', first_word)

    return f"{surname}{year}_{first_word}"


def format_short_cite(authors: list, year: str) -> str:
    """Format (Author et al., Year) citation"""
    if not authors:
        return "(Unknown, Year)"

    first_author = authors[0]
    # Extract surname (format: "Surname Initial" or "Surname")
    surname = first_author.split(',')[0].strip() if ',' in first_author else first_author.split()[0]

    if len(authors) > 2:
        return f"({surname} et al., {year})"
    elif len(authors) == 2:
        second_author = authors[1].split(',')[0].strip() if ',' in authors[1] else authors[1].split()[0]
        return f"({surname} & {second_author}, {year})"
    else:
        return f"({surname}, {year})"


def format_full_reference(article: dict) -> str:
    """Format complete APA-style reference"""
    authors = article.get('authors', [])
    year = article.get('year', 'n.d.')
    title = article.get('title', '')
    journal = article.get('journal', '')
    volume = article.get('volume', '')
    issue = article.get('issue', '')
    pages = article.get('pages', '')
    doi = article.get('doi', '')

    # Format authors
    if len(authors) > 6:
        author_list = ', '.join([a.split(',')[0].strip() if ',' in a else a.split()[0] for a in authors[:6]]) + ', ...'
    else:
        author_list = ', '.join([a.split(',')[0].strip() if ',' in a else a.split()[0] for a in authors])

    # Build reference
    ref = f"{author_list} ({year}). {title}. "

    # Journal and volume/issue
    if journal:
        ref += f"*{journal}*"
        if volume:
            ref += f", {volume}"
            if issue:
                ref += f"({issue})"
            if pages:
                ref += f", {pages}"

    # DOI
    if doi:
        if not doi.startswith('https://'):
            ref += f". https://doi.org/{doi}"
        else:
            ref += f". {doi}"

    return ref


def build_citation_db(phase1_file: Path) -> dict:
    """Build citation database from Phase 1 results"""
    with open(phase1_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    citations = []
    articles = data.get('articles', [])

    for article in articles:
        pmid = article.get('pmid', '')
        if not pmid:
            continue

        # Generate citekey for BibTeX
        citekey = generate_citekey(
            article.get('authors', []),
            article.get('year', 'n.d.'),
            article.get('title', '')
        )

        short_cite = format_short_cite(
            article.get('authors', []),
            article.get('year', 'n.d.')
        )

        full_reference = format_full_reference(article)

        # 保留完整article数据，添加citekey相关字段
        citation_entry = article.copy()  # 复制所有原始字段
        citation_entry['citekey'] = citekey
        citation_entry['short_cite'] = short_cite
        citation_entry['full_reference'] = full_reference

        citations.append(citation_entry)

    return {
        'source_file': str(phase1_file),
        'total_citations': len(citations),
        'citations': citations
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate citation database from Phase 1 results'
    )
    parser.add_argument('input_file', type=Path, help='Phase 1/2 JSON file')
    parser.add_argument('--output', '-o', type=Path, help='Output JSON file path')

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    db = build_citation_db(args.input_file)

    # Set output file
    if args.output:
        output_file = args.output
    else:
        output_file = args.input_file.parent / 'citation_db.json'

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print(f"✓ Citation database saved to: {output_file}")
    print(f"  Total citations: {db['total_citations']}")


if __name__ == '__main__':
    main()
