# Phase 5: Citation Verification (Detailed Guide)

## Overview

Phase 5 verifies that all citations in the markdown document are valid and traceable to Phase 1 retrieval.

## Quick Verification

```bash
# Basic verification (citekey consistency only)
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib

# Full verification with DOI metadata check
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib --verify-doi
```

## What Gets Verified

### 1. Citekey Consistency (Required)

- All `[@citekey]` markers in MD exist in `.bib` file
- No orphaned citekeys (in MD but not in .bib)
- Reports unused citekeys (in .bib but not in MD)

### 2. DOI Link Validity (Optional, with `--verify-doi`)

- All DOIs in .bib file resolve correctly
- HTTP status codes: 200/302/403 → Valid, 404 → Invalid

### 3. DOI Metadata (Optional, with `--verify-doi`)

- First author surname matches
- Journal name matches
- Year matches

## Output

### Success (All Valid)

```
============================================================
BibTeX Citation Verification
============================================================
Markdown: chapterXX/X.X-final.md
BibTeX: process/references.bib

Citekeys in Markdown: 34
Citekeys in BibTeX: 146

✅ PASS: All citations verified
============================================================
```

### Failure (Errors Found)

```
============================================================
BibTeX Citation Verification
============================================================
Markdown: chapterXX/X.X-final.md
BibTeX: process/references.bib

Citekeys in Markdown: 35
Citekeys in BibTeX: 146

❌ FAIL: Found citation errors

⚠️  1 citekeys in MD but not in .bib:
  - [@fake2024_nonexistent]

⚠️  140 citekeys in .bib but not in MD:
  - @abelia2023_comparison
  - @addicott2023_smoking
  ... and 138 more

============================================================
```

## Common Issues

### Missing Citekey

**Error**: `[@citekey] in MD but not in .bib`

**Causes**:
1. Typo in citekey spelling
2. Paper not in Phase 1 results
3. Citekey database out of sync

**Solutions**:
1. Check spelling in markdown
2. Verify paper exists in Phase 1 results
3. Re-run: `python scripts/build_citation_db.py` and `python scripts/generate_bibtex.py`

### Unused Citekeys

**Warning**: `citekeys in .bib but not in MD`

**Note**: This is informational, not an error. Not all papers need to be cited.

**If you want to clean up**:
1. Review unused citekeys
2. Remove from .bib if truly not needed
3. Or regenerate .bib with selected PMIDs only

### DOI Mismatches

**Error**: `DOI metadata mismatches`

**Example**:
```
⚠️  1 DOI metadata mismatches:
  - @yu2021_association: year: 2020 != 2021
```

**Solutions**:
1. Verify correct year in source
2. Update .bib file if needed
3. Or ignore if minor discrepancy

## Integration with Workflow

### After Writing Phase 4

```bash
# 1. Build citation database (if not done)
python scripts/build_citation_db.py process/phase1_pubmed_results.json

# 2. Generate BibTeX file (if not done)
python scripts/generate_bibtex.py process/phase1_pubmed_results.json

# 3. Verify citations
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib
```

### Fixing Errors

If verification fails:

1. **Check missing citekeys**:
   ```bash
   # See which citekeys are missing
   python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib
   ```

2. **Find correct citekey**:
   ```bash
   # Search citation database
   grep "your author name" process/citation_db.json
   ```

3. **Update markdown**:
   - Fix typos in citekeys
   - Replace with correct citekey
   - Remove citation if paper not relevant

4. **Re-verify**:
   ```bash
   python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib
   ```

## Exit Codes

- `0` - All citations verified (PASS)
- `1` - Citation errors found (FAIL)

## CI/CD Integration

For automated verification in workflows:

```bash
# In build script
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib
if [ $? -ne 0 ]; then
    echo "Citation verification failed"
    exit 1
fi
```

## Advanced: Custom Verification

For project-specific verification rules, modify the script:

```python
# Add custom rules in verify_citations()

# Example: Require minimum citation count
if result['citekeys_in_md'] < 30:
    print("⚠️  Warning: Fewer than 30 citations")

# Example: Check for recent publications
recent = sum(1 for e in bib_entries.values() if e.get('year', '0') > '2022')
print(f"Recent publications: {recent}/{len(bib_entries)}")
```
