#!/usr/bin/env python3
"""
generate_bibtex.py - Generate BibTeX file from Phase 1 results

Generates a .bib file with entries for selected papers.
Citekey format: {first_author_surname}{year}_{first_word}

Example:
    @article{yu2021_association,
      author = {Yu, J. J. and Nahhas, C. and ...},
      title = {Association between smoking and cognitive function...},
      ...
    }
"""

import argparse
import json
import re
import string
import sys
from pathlib import Path
from typing import Dict, List, Optional


def generate_citekey(authors: List[str], year: str, title: str) -> str:
    """
    Generate unique citekey from author, year, and title.

    Format: {first_author_surname}{year}_{first_word}

    Examples:
        - (Yu et al., 2021) "Association between smoking..." -> yu2021_association
        - (Jones et al., 2024) "Potentially modifiable risk..." -> jones2024_potentially
    """
    if not authors:
        return f"unknown{year}_article"

    # Get first author's surname
    first_author = authors[0]
    surname = first_author.split(',')[0].strip() if ',' in first_author else first_author.split()[0]
    surname = surname.lower()

    # Get first word from title (remove punctuation, lowercase)
    title_words = title.strip().split()
    first_word = title_words[0].lower().strip(string.punctuation) if title_words else "article"

    # Remove special characters from first word
    first_word = re.sub(r'[^\w]', '', first_word)

    return f"{surname}{year}_{first_word}"


def format_authors_bibtex(authors: List[str]) -> str:
    """
    Format authors for BibTeX.

    Input (PubMed format): ["Wu M", "Feng W", "Costa-Rodrigues JR"]
    Output (BibTeX format): "Wu, M and Feng, W and Costa-Rodrigues, JR"

    PubMed returns authors as "Surname Initials" (e.g., "Wu M", "Costa-Rodrigues JR")
    BibTeX requires "Surname, Initials" format
    """
    if not authors:
        return ""

    formatted = []
    for author in authors[:20]:  # Limit to 20 authors
        # Check if already in "Surname, Initials" format
        if ',' in author:
            formatted.append(author)
        else:
            # PubMed format: "Surname Initials" (e.g., "Wu M", "Costa-Rodrigues JR")
            parts = author.split()
            if len(parts) >= 2:
                # First element is surname, rest are initials
                surname = parts[0]
                initials = ' '.join(parts[1:])
                formatted.append(f"{surname}, {initials}")
            else:
                # Single name, use as-is
                formatted.append(author)

    return ' and '.join(formatted)


def escape_bibtex(text: str) -> str:
    """Escape special characters for BibTeX"""
    if not text:
        return ""
    # Replace {} with \{ \}
    text = text.replace('{', '\\{').replace('}', '\\}')
    # But keep some intentional LaTeX commands
    # text = re.sub(r'\\([{}])', r'\1', text)
    return text


def article_to_bibtex(article: dict, citekey: str) -> str:
    """Convert article dict to BibTeX entry"""
    # Required fields
    pmid = article.get('pmid', '')
    title = article.get('title', '')
    journal = article.get('journal', '')
    year = article.get('year', 'n.d.')

    # Optional fields
    authors = article.get('authors', [])
    volume = article.get('volume', '')
    issue = article.get('issue', '')
    pages = article.get('pages', '')
    doi = article.get('doi', '')

    # Format authors
    author_str = format_authors_bibtex(authors)

    # Build BibTeX entry
    bibtex = f"@article{{{citekey},\n"

    if author_str:
        bibtex += f"  author = {{{author_str}}},\n"

    bibtex += f"  title = {{{escape_bibtex(title)}}},\n"

    if journal:
        bibtex += f"  journal = {{{journal}}},\n"

    if volume:
        bibtex += f"  volume = {{{volume}}},\n"

    if issue:
        bibtex += f"  number = {{{issue}}},\n"

    if pages:
        bibtex += f"  pages = {{{pages}}},\n"

    bibtex += f"  year = {{{year}}},\n"

    if doi:
        bibtex += f"  doi = {{{doi}}},\n"

    bibtex += f"  pmid = {{{pmid}}}\n"

    bibtex += "}\n"

    return bibtex


def load_articles(json_file: Path) -> List[dict]:
    """Load articles from Phase 1/2 JSON file or citation database

    Supports two formats:
    - Phase 1/2: {"articles": [...]}
    - Citation DB: {"citations": [...]}
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if it's citation database format
    if 'citations' in data:
        # Convert citation database format to article format
        articles = []
        for citation in data['citations']:
            articles.append({
                'pmid': citation.get('pmid', ''),
                'title': citation.get('title', ''),
                'authors': [],  # Citation DB doesn't have author list, citekey only
                'journal': citation.get('journal', ''),
                'year': citation.get('year', ''),
                'volume': '',
                'issue': '',
                'pages': '',
                'doi': citation.get('doi', ''),
                '_citekey': citation.get('citekey', '')  # Pre-computed citekey
            })
        return articles
    else:
        return data.get('articles', [])


def generate_bibtex_file(
    articles: List[dict],
    output_file: Path,
    selected_pmids: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Generate BibTeX file from articles.

    Args:
        articles: List of article dicts
        output_file: Path to output .bib file
        selected_pmids: Optional list of PMIDs to include (if None, include all)

    Returns:
        Dict mapping PMID to citekey
    """
    pmid_to_citekey = {}

    with open(output_file, 'w', encoding='utf-8') as f:
        for article in articles:
            pmid = article.get('pmid', '')

            # Skip if not in selected list
            if selected_pmids is not None and pmid not in selected_pmids:
                continue

            # Skip if missing required fields
            if not pmid or not article.get('title'):
                continue

            # Generate citekey
            year = article.get('year', 'n.d.')
            title = article.get('title', '')
            authors = article.get('authors', [])

            citekey = generate_citekey(authors, year, title)

            # Check for duplicate citekeys and add suffix if needed
            base_citekey = citekey
            suffix = 1
            while citekey in pmid_to_citekey.values():
                citekey = f"{base_citekey}_{suffix}"
                suffix += 1

            pmid_to_citekey[pmid] = citekey

            # Write BibTeX entry
            bibtex_entry = article_to_bibtex(article, citekey)
            f.write(bibtex_entry + "\n")

    return pmid_to_citekey


def main():
    parser = argparse.ArgumentParser(
        description='Generate BibTeX file from Phase 1 results'
    )
    parser.add_argument('input_file', type=Path, help='Path to phase1_pubmed_results.json')
    parser.add_argument('--output', '-o', type=Path, help='Output .bib file path')
    parser.add_argument('--pmids', type=Path, help='File containing list of PMIDs to include (one per line)')
    parser.add_argument('--pmid-list', help='Comma-separated list of PMIDs to include')

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Load articles
    articles = load_articles(args.input_file)
    print(f"Loaded {len(articles)} articles from {args.input_file}")

    # Get selected PMIDs
    selected_pmids = None
    if args.pmids:
        with open(args.pmids, 'r') as f:
            selected_pmids = [line.strip() for line in f if line.strip()]
        print(f"Filtering to {len(selected_pmids)} selected PMIDs")
    elif args.pmid_list:
        selected_pmids = [p.strip() for p in args.pmid_list.split(',')]
        print(f"Filtering to {len(selected_pmids)} selected PMIDs")

    # Set output file
    if args.output:
        output_file = args.output
    else:
        output_file = args.input_file.parent / "references.bib"

    # Generate BibTeX file
    print(f"Generating BibTeX file: {output_file}")
    pmid_to_citekey = generate_bibtex_file(articles, output_file, selected_pmids)

    # Also save PMID -> citekey mapping for later use
    mapping_file = output_file.parent / "pmid_to_citekey.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(pmid_to_citekey, f, indent=2, ensure_ascii=False)

    print(f"✓ Generated {len(pmid_to_citekey)} BibTeX entries")
    print(f"  Output: {output_file}")
    print(f"  Mapping: {mapping_file}")


if __name__ == '__main__':
    main()
