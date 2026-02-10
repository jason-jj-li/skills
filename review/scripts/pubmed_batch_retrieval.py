#!/usr/bin/env python3
"""
pubmed_batch_retrieval.py - PubMed batch retrieval with curl and rate limiting

Improvements over current implementation:
1. Uses curl for API calls (more reliable than urllib)
2. Batch processing (200 PMIDs per EFetch request)
3. Rate limit handling (3 req/sec without API key, 10 req/sec with key)
4. Resume capability with checkpoint file
5. Complete data extraction using findall() for abstracts
6. Extracts all fields: volume, issue, pages, DOI, etc.
"""

import argparse
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# PubMed E-utilities API endpoints
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ESEARCH_URL = f"{BASE_URL}esearch.fcgi"
EFETCH_URL = f"{BASE_URL}efetch.fcgi"

# Rate limiting: 3 requests/sec without API key, 10 req/sec with API key
# Default to 3 req/sec (0.33s delay between requests)
REQUEST_DELAY = 0.34
BATCH_SIZE = 200  # PMIDs per EFetch request


def load_search_mapping(mapping_file: Path) -> dict:
    """Load search mapping JSON file"""
    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def curl_esearch(query: str, retmax: int = 100, api_key: Optional[str] = None) -> List[str]:
    """Execute ESearch using curl and return PMID list.

    Uses GET request with URL encoding for better compatibility with special characters.
    """
    # Build URL with parameters
    # Note: We need to properly URL encode the term parameter
    params = [
        f"db=pubmed",
        f"term={urllib.parse.quote(query)}",
        f"retmax={retmax}",
        "retmode=json"
    ]

    if api_key:
        params.append(f"api_key={urllib.parse.quote(api_key)}")

    url = f"{ESEARCH_URL}?{'&'.join(params)}"

    # Execute curl with GET request
    curl_params = ["curl", "-s", url]

    try:
        result = subprocess.run(curl_params, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"❌ curl返回错误码: {result.returncode}")
            if result.stderr:
                print(f"stderr: {result.stderr}")
            return []

        data = json.loads(result.stdout)
        return data.get("esearchresult", {}).get("idlist", [])
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        if result.stdout:
            print(f"stdout: {result.stdout[:500]}")
        raise


def curl_efetch(pmids: List[str], api_key: Optional[str] = None) -> str:
    """Execute EFetch using curl and return XML string"""
    pmid_str = ",".join(pmids)

    params = [
        "curl", "-s",
        EFETCH_URL,
        "-d", f"db=pubmed",
        "-d", f"id={pmid_str}",
        "-d", "retmode=xml"
    ]

    if api_key:
        params.extend(["-d", f"api_key={api_key}"])

    result = subprocess.run(params, capture_output=True, text=True, check=True)
    return result.stdout


def extract_abstract_text(medline_citation: ET.Element) -> str:
    """
    Extract complete abstract text including structured abstracts.

    Handles:
    - Unstructured abstracts (single AbstractText)
    - Structured abstracts (multiple AbstractText with label attributes)
    - Abstracts with nested markup (italic, bold, etc.)

    Returns empty string if no abstract found.
    """
    abstract_elem = medline_citation.find('.//Abstract')
    if abstract_elem is None:
        return ""

    abstract_segments = abstract_elem.findall('AbstractText')
    if not abstract_segments:
        return ""

    # Build abstract from all segments
    abstract_parts = []
    for seg in abstract_segments:
        # Get label if present (e.g., "BACKGROUND", "METHODS")
        label = seg.get('label')
        if label:
            label = label.strip() + ": "

        # Get all text content including nested elements
        # itertext() recursively gets all text from element and children
        text_content = ''.join(seg.itertext()).strip()

        if text_content:
            if label:
                abstract_parts.append(label + text_content)
            else:
                abstract_parts.append(text_content)

    # Join with proper spacing
    abstract = ' '.join(abstract_parts).strip()

    # Clean up multiple spaces
    abstract = re.sub(r'\s+', ' ', abstract)

    return abstract


def extract_article_data(pubmed_article: ET.Element) -> dict:
    """
    Extract complete article data from PubMedArticle element.

    Extracts ALL fields needed for scoping review:
    - PMID, DOI, title, authors, year, journal
    - Volume, issue, pages
    - Abstract (complete, using itertext() for nested markup)
    - Publication type, MeSH terms, Keywords
    - Affiliation information
    """
    article = {}
    medline_citation = pubmed_article.find('MedlineCitation')
    pubmed_data = pubmed_article.find('PubmedData')

    if medline_citation is None:
        return None

    # PMID
    pmid_elem = medline_citation.find('PMID')
    article['pmid'] = pmid_elem.text if pmid_elem is not None else ''

    # Article title (use itertext() to handle nested markup like italic, bold)
    title_elem = medline_citation.find('.//Article/ArticleTitle')
    article['title'] = ''.join(title_elem.itertext()).strip() if title_elem is not None else ''

    # Authors with affiliation
    authors = []
    affiliations = []
    for author in medline_citation.findall('.//Author'):
        lastname = author.find('LastName')
        forename = author.find('Forename')
        initials = author.find('Initials')
        affiliation_list = author.findall('.//AffiliationInfo/Affiliation')

        if lastname is not None:
            author_parts = [lastname.text]
            if forename is not None:
                author_parts.append(forename.text)
            elif initials is not None:
                author_parts.append(initials.text)
            authors.append(' '.join(filter(None, author_parts)))

        # Collect affiliations
        for aff in affiliation_list:
            if aff is not None and aff.text:
                affiliations.append(aff.text.strip())

    article['authors'] = authors
    article['affiliations'] = affiliations if affiliations else []

    # Journal (ISO abbreviation)
    journal_elem = medline_citation.find('.//Journal/ISOAbbreviation')
    if journal_elem is not None and journal_elem.text:
        article['journal'] = journal_elem.text
    else:
        # Fallback to full title
        journal_elem = medline_citation.find('.//Journal/Title')
        article['journal'] = journal_elem.text if journal_elem is not None else ''

    # Volume
    volume_elem = medline_citation.find('.//JournalIssue/Volume')
    article['volume'] = volume_elem.text if volume_elem is not None else ''

    # Issue
    issue_elem = medline_citation.find('.//JournalIssue/Issue')
    article['issue'] = issue_elem.text if issue_elem is not None else ''

    # Pages
    pages_elem = medline_citation.find('.//Pagination/MedlinePgn')
    article['pages'] = pages_elem.text if pages_elem is not None else ''

    # Publication date (year, month, day if available)
    year_elem = medline_citation.find('.//PubDate/Year')
    if year_elem is None:
        # Try MedlineDate (e.g., "2023 May-Jun")
        medline_date = medline_citation.find('.//PubDate/MedlineDate')
        if medline_date is not None:
            match = re.search(r'(\d{4})', medline_date.text)
            article['year'] = match.group(1) if match else ''
        else:
            article['year'] = ''
    else:
        article['year'] = year_elem.text if year_elem is not None else ''

    # Abstract (COMPLETE extraction using itertext())
    article['abstract'] = extract_abstract_text(medline_citation)

    # DOI - check both PubmedData and MedlineCitation
    article['doi'] = ''
    if pubmed_data is not None:
        for article_id in pubmed_data.findall('.//ArticleId'):
            if article_id.get('IdType') == 'doi' and article_id.text:
                article['doi'] = article_id.text
                break

    # Publication type
    pub_types = []
    for pt in medline_citation.findall('.//PublicationType'):
        if pt.text:
            pub_types.append(pt.text)
    article['publication_types'] = pub_types

    # MeSH terms (both descriptors and qualifiers)
    mesh_terms = []
    for mesh in medline_citation.findall('.//MeshHeading'):
        desc = mesh.find('DescriptorName')
        if desc is not None and desc.text:
            mesh_term = desc.text
            # Check for qualifiers
            quals = mesh.findall('QualifierName')
            if quals:
                qual_texts = [q.text for q in quals if q.text]
                if qual_texts:
                    mesh_term += '/' + '/'.join(qual_texts)
            mesh_terms.append(mesh_term)
    article['mesh_terms'] = mesh_terms

    # Keywords
    keywords = []
    for kw in medline_citation.findall('.//Keyword'):
        if kw is not None and kw.text:
            keywords.append(kw.text)
    article['keywords'] = keywords

    # Publication status (e.g., "ppublish", "epublish")
    pub_status = medline_citation.find('.//PublicationStatus')
    article['publication_status'] = pub_status.text if pub_status is not None else ''

    return article


def load_checkpoint(checkpoint_file: Path) -> dict:
    """Load checkpoint data if exists"""
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_checkpoint(checkpoint_file: Path, data: dict):
    """Save checkpoint data"""
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_theme(theme: dict, checkpoint: dict, api_key: Optional[str] = None) -> dict:
    """Process a single search theme with batch retrieval and checkpointing"""
    theme_name = theme['theme']
    query = theme['query']
    retmax = theme.get('retmax', 100)

    print(f"\n{'='*60}")
    print(f"Theme: {theme_name}")
    print(f"Query: {query[:80]}...")
    print(f"{'='*60}")

    # Check if already completed
    if theme_name in checkpoint and checkpoint[theme_name].get('complete', False):
        print(f"✓ Already completed (found {checkpoint[theme_name]['count']} articles)")
        return checkpoint[theme_name]

    # Step 1: ESearch to get PMIDs
    print(f"\n[1/3] Running ESearch...")
    pmids = curl_esearch(query, retmax, api_key)
    print(f"  Found {len(pmids)} PMIDs")
    time.sleep(REQUEST_DELAY)

    if not pmids:
        result = {'pmids': [], 'articles': [], 'count': 0, 'complete': True}
        checkpoint[theme_name] = result
        return result

    # Step 2: Batch EFetch to get article details
    print(f"\n[2/3] Running EFetch in batches of {BATCH_SIZE}...")

    all_articles = []
    checkpoint_pmids = checkpoint.get(theme_name, {}).get('pmids', [])

    # Process in batches
    for i in range(0, len(pmids), BATCH_SIZE):
        batch = pmids[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(pmids) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"  Batch {batch_num}/{total_batches}: {len(batch)} PMIDs", end='', flush=True)

        # Check if this batch was already processed
        batch_already_done = all(pmid in checkpoint_pmids for pmid in batch)
        if batch_already_done and checkpoint.get(theme_name, {}).get('articles'):
            # Use cached articles for this batch
            start_idx = i
            end_idx = min(i + BATCH_SIZE, len(checkpoint[theme_name]['articles']))
            cached_articles = checkpoint[theme_name]['articles'][start_idx:end_idx]
            all_articles.extend(cached_articles)
            print(" (cached)")
            continue

        # Fetch this batch
        try:
            xml_text = curl_efetch(batch, api_key)
            root = ET.fromstring(xml_text)

            # Extract articles
            batch_articles = []
            for pubmed_article in root.findall('.//PubmedArticle'):
                article_data = extract_article_data(pubmed_article)
                if article_data and article_data.get('pmid'):
                    batch_articles.append(article_data)

            all_articles.extend(batch_articles)
            print(f" → {len(batch_articles)} articles")

        except ET.ParseError as e:
            print(f" ✗ XML parse error: {e}")
        except Exception as e:
            print(f" ✗ Error: {e}")

        # Rate limit delay
        time.sleep(REQUEST_DELAY)

    # Step 3: Update checkpoint
    print(f"\n[3/3] Complete: {len(all_articles)} articles retrieved")
    result = {
        'pmids': pmids,
        'articles': all_articles,
        'count': len(all_articles),
        'complete': True
    }
    checkpoint[theme_name] = result

    return result


def main():
    parser = argparse.ArgumentParser(
        description='PubMed batch retrieval with curl and rate limiting'
    )
    parser.add_argument('mapping_file', type=Path, help='Path to search_mapping.json')
    parser.add_argument('--output', '-o', type=Path, help='Output JSON file path')
    parser.add_argument('--api-key', help='NCBI API key (optional, increases rate limit)')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')

    args = parser.parse_args()

    if not args.mapping_file.exists():
        print(f"Error: Mapping file not found: {args.mapping_file}", file=sys.stderr)
        sys.exit(1)

    # Load search mapping
    mapping = load_search_mapping(args.mapping_file)
    themes = mapping.get('themes', [])

    if not themes:
        print("Error: No themes found in mapping file", file=sys.stderr)
        sys.exit(1)

    # Set up output file and directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output:
        output_file = args.output
        output_dir = args.output.parent
    else:
        output_dir = args.mapping_file.parent
        output_file = output_dir / f"phase1_pubmed_results_{timestamp}.json"

    checkpoint_file = output_dir / "phase1_checkpoint.json"

    # Load checkpoint if resuming
    checkpoint = {}
    if args.resume and checkpoint_file.exists():
        checkpoint = load_checkpoint(checkpoint_file)
        print(f"Resumed from checkpoint")

    # Process each theme
    all_results = {
        'timestamp': timestamp,
        'section': mapping.get('section', ''),
        'outline_title': mapping.get('outline_title', ''),
        'date_range': mapping.get('date_range', ''),
        'search_results': {},
        'articles': []
    }

    total_articles = 0
    for theme in themes:
        result = process_theme(theme, checkpoint, args.api_key)

        # Update search results
        theme_name = theme['theme']
        all_results['search_results'][theme_name] = {
            'query': theme['query'],
            'maps_to': theme.get('maps_to', []),
            'count': result['count']
        }

        # Add articles (avoid duplicates)
        seen_pmids = {a['pmid'] for a in all_results['articles']}
        for article in result.get('articles', []):
            if article['pmid'] not in seen_pmids:
                all_results['articles'].append(article)
                seen_pmids.add(article['pmid'])

        total_articles = len(all_results['articles'])

        # Save checkpoint after each theme
        save_checkpoint(checkpoint_file, checkpoint)

    # Save final results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"✓ Complete: {total_articles} articles retrieved")
    print(f"  Output: {output_file}")
    print(f"  Checkpoint: {checkpoint_file}")
    print(f"{'='*60}")

    # Data quality summary
    with_abstract = sum(1 for a in all_results['articles'] if a.get('abstract'))
    with_doi = sum(1 for a in all_results['articles'] if a.get('doi'))
    print(f"\nData Quality:")
    if total_articles > 0:
        print(f"  With abstract: {with_abstract}/{total_articles} ({100*with_abstract/total_articles:.1f}%)")
        print(f"  With DOI: {with_doi}/{total_articles} ({100*with_doi/total_articles:.1f}%)")
        print(f"  Avg abstract length: {sum(len(a.get('abstract','')) for a in all_results['articles'])/max(total_articles,1):.0f} chars")
    else:
        print(f"  No articles retrieved - check search queries")


if __name__ == '__main__':
    main()
