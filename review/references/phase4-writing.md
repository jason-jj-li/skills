# Phase 4: Writing with Verified Citations (Detailed Guide)

## Overview

Phase 4 synthesizes literature into a scoping review using verified citekey markers.

## Citation Format

### NEW: BibTeX Citekey Markers

Use `[@citekey]` format instead of APA `(Author, Year)`.

**Example**:
```markdown
Multiple studies have documented this finding [@bold2023_smartphone; @jones2024_potentially].
```

**NOT**:
```markdown
Multiple studies have documented this finding (Bold et al., 2023; Jones et al., 2024).
```

## Workflow

### Step 1: Generate Citation Database

```bash
# Generate citation database with citekeys from Phase 1 results
python scripts/build_citation_db.py process/phase1_pubmed_results.json > process/citation_db.json
```

Output includes:
```json
{
  "pmid": "33071239",
  "citekey": "yu2021_association",
  "short_cite": "(Yu et al., 2021)",
  "full_reference": "Yu, J. J., ... (2021). ..."
}
```

### Step 2: Generate BibTeX File

```bash
# Generate .bib file for all papers
python scripts/generate_bibtex.py process/phase1_pubmed_results.json

# Generate .bib file for selected PMIDs only
python scripts/generate_bibtex.py process/phase1_pubmed_results.json --pmid-list 33071239,12345678

# Generate .bib file from PMID list file
python scripts/generate_bibtex.py process/phase1_pubmed_results.json --pmids process/selected_pmids.txt
```

Output files:
- `process/references.bib` - BibTeX file with all entries
- `process/pmid_to_citekey.json` - PMID to citekey mapping

### Step 3: Write with Citekey Markers

**Open** `process/citation_db.json` to see available citekeys.

**Use** `[@citekey]` markers in markdown:

```markdown
## Smoking and Cognitive Performance

Recent neurobiological research demonstrates that smoking status directly affects cognitive responses [@addicott2023_smoking]. The vascular mechanisms linking smoking to cognitive impairment have been further elucidated [@rundek2022_vascular].

Longitudinal evidence supports a dose-response relationship. Heavier smokers show greater impairment [@benitoleon2023_association]. The impact extends beyond pure vascular mechanisms, as smoking reduces cognitive reserve capacity [@alvares2022_cognitive].
```

### Step 4: Verification

```bash
# Verify all citekeys exist in .bib file
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib

# With DOI metadata verification (slower)
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib --verify-doi
```

## Writing Template

### Section Structure

```markdown
## Section Title

[Content synthesizing multiple verified sources]

Multiple studies have documented this topic [@citekey1; @citekey2].
Specific findings indicate that [@citekey3]. However, other research suggests [@citekey4].

### Subsection

Detailed analysis with more citations [@citekey5; @citekey6; @citekey7].
```

### In-Text Citation Patterns

**Single citation**:
```markdown
[@yu2021_association]
```

**Multiple citations** (semicolon separated):
```markdown
[@yu2021_association; @jones2024_potentially; @bold2023_smartphone]
```

**Narrative citation** (if needed, but prefer brackets):
```markdown
As shown by Yu et al. [@yu2021_association], the association is significant.
```

## Writing Rules (ENFORCED)

### Allowed

- ✅ Use `[@citekey]` markers from `process/citation_db.json`
- ✅ Verify citekey exists in `process/references.bib` before using
- ✅ Cite multiple papers with semicolon separation

### Prohibited

- ❌ Use APA format `(Author, Year)` in new documents
- ❌ Write citations from memory
- ❌ "Invent" or guess citekeys
- ❌ Cite papers not in Phase 1 results

## Quick Citation Reference

While writing, keep this template open:

```markdown
<!-- AVAILABLE CITATIONS - Copy from process/citation_db.json only -->

@bold2023_smartphone - PMID: 37440305 - Bold et al., 2023
@jones2024_potentially - PMID: 38346414 - Jones et al., 2024
@schippinger2024_prevention - PMID: 38416181 - Schippinger & Pichler, 2024
...

<!-- END VERIFIED CITATIONS -->
```

## When You Need to Cite

1. Search `process/citation_db.json` for relevant paper
2. Use the exact `citekey` from database
3. Verify citekey exists in `process/references.bib`
4. Use `[@citekey]` format in markdown

**If no relevant paper exists** → DO NOT CITE → Return to Phase 1

## Common Issues

### Citekey not found in .bib

**Error**: `[@citekey] in MD but not in .bib`

**Solution**:
1. Check spelling of citekey
2. Verify paper is in Phase 1 results
3. Re-run `build_citation_db.py` and `generate_bibtex.py`

### Duplicate citekeys

**Symptom**: Same citekey for different papers

**Solution**: Script adds suffix (`_2`, `_3`) automatically:
- `yu2021_association`
- `yu2021_association_2`
- `yu2021_association_3`

### Too many papers to cite

**Symptom**: 50+ papers on topic, overwhelming to cite

**Solution**:
1. Focus on high-priority papers from Phase 2 screening
2. Use `--pmids` to generate .bib for selected papers only
3. Group citations: `[@multiple_studies]` with note in text
