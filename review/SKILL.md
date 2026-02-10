---
name: review
description: >
  Verification-first literature review workflow that prevents LLM citation hallucination.
  Uses strict retrieval-only citations: all references must come from verified PubMed/CrossRef sources,
  never from free-form LLM generation. Use for: (1) Systematic literature reviews requiring
  verified citations only, (2) Academic writing where citation accuracy is critical, (3) Literature
  synthesis with complete traceability to source data.
---

# Review - Verification-First Literature Workflow

## Core Principle

**Only cite what has been retrieved.** Phase 1 retrieves → Verified Database → Phase 2-5 use ONLY those citations → Phase 5 verifies.

## Execution Workflow (Mandatory)

**当使用本skill进行文献综述时，必须遵循以下工作流程：**

```text
1. 生成详细系统的todo列表
   ↓
2. 执行单个任务
   ↓
3. 回溯核验该任务结果
   ↓
4. 核验通过后，进入下一任务
   ↓
5. 重复步骤2-4，直到所有任务完成
```

**工作流程要求**:

1. **必须先生成详细todo**: 在开始任何工作前，首先生成完整的、系统化的todo列表，包含每个Phase的所有子任务和对应的核验步骤
2. **每步执行完都要核验**: 每完成一个任务，必须进行回溯核验，确保结果正确
3. **核验通过才能继续**: 只有当前任务核验通过后，才能进入下一个任务
4. **核验失败要修复**: 如果核验发现问题，必须先修复问题，再重新核验

**示例todo结构**:

```text
- Phase 1: 执行PubMed检索
  - Phase 1: 核验 - 检查数据完整性（abstracts、DOIs、authors）
- Phase 2: 生成citation数据库
  - Phase 2: 核验 - 检查citekey格式和唯一性
- Phase 3: 生成BibTeX文件
  - Phase 3: 核验 - 检查BibTeX条目完整性
...
```

## Quick Start

```bash
# Phase 0: Generate search strategy from topic
python scripts/generate_search_strategy.py "吸烟与认知障碍的关系" -o process/search_mapping.json

# Phase 1: Retrieve from PubMed (with batching and rate limiting)
python scripts/pubmed_batch_retrieval.py process/search_mapping.json

# Phase 1: Verify data completeness
python scripts/verify_phase1_data.py process/phase1_pubmed_results_*.json

# Phase 2: Screen papers with study type detection and journal ranking
python scripts/screen_papers.py process/phase1_pubmed_results.json \\
  --top-journals-only \\
  --sort-by evidence \\
  -o process/phase2_screened.json

# Alternative: LLM-assisted analysis and writing
python scripts/analyze_and_write.py process/phase2_screened.json \\
  --mode full \\
  --topic "吸烟与认知障碍的关系" \\
  -o review.md

# Phase 3: Generate citation database and BibTeX
python scripts/build_citation_db.py process/phase2_screened.json -o process/citation_db.json
python scripts/generate_bibtex.py process/phase2_screened.json

# Phase 4: Verify citations in final document
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib

# Phase 5: Generate PDF (Final Step)
python scripts/generate_pdf.py chapterXX/X.X-final.md process/references.bib
```

## Workflow

```text
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
 AI辅助      PubMed    智能筛选      写作/LLM   验证      PDF
检索策略    (自动)    (研究类型)    (交互式)   (自动)    (渲染)
                    期刊排名
```

**自动化阶段**: Phase 1-2, 4-5 (本skill提供脚本)
**手动阶段**: Phase 0 (需要用户干预)
**LLM辅助模式**: Phase 3 (LLM直接读取数据并撰写)

## Phases Overview

### Phase 0: Search Strategy Generation (AI-Assisted)

```bash
python scripts/generate_search_strategy.py "your topic" [--dry-run]
```

**交互式AI辅助模式**:

脚本会生成结构化的MeSH检索策略，基于主题的PICO要素：
- **Population** (研究对象)
- **Exposure/Intervention** (暴露因素/干预措施)
- **Outcome** (结局指标)

**输出**: `search_mapping.json` 包含多个检索主题，每个主题有对应的PubMed查询式。

**手动调整选项**: 可以直接编辑生成的 `search_mapping.json` 调整检索式。参考 [phase1-retrieval.md](references/phase1-retrieval.md) 中的格式。

### Phase 1: PubMed Retrieval (Automated)

Batch retrieval with curl, rate limiting (3 req/sec), resume capability, complete data extraction (100% abstract coverage).

```bash
# Run retrieval
python scripts/pubmed_batch_retrieval.py process/search_mapping.json

# Resume from checkpoint if interrupted
python scripts/pubmed_batch_retrieval.py process/search_mapping.json --resume

# Verify data completeness after retrieval
python scripts/verify_phase1_data.py process/phase1_pubmed_results_*.json
```

**Data Quality**: 100% abstract coverage using `itertext()` for nested XML markup, 98%+ DOI coverage.

See [phase1-retrieval.md](references/phase1-retrieval.md) for details.

### Phase 2: Screening and Classification

**两种筛选方案**:

#### 方案A: 智能筛选 (screen_papers.py)

使用内置脚本进行智能筛选，支持：
- **研究类型标记**: 自动识别Meta分析、RCT、队列研究等20+种类型
- **期刊排名**: 按影响因子分为Tier 1-5等级
- **相关性评分**: 基于关键词匹配计算相关性得分

```bash
# 按证据等级排序，筛选高质量研究
python scripts/screen_papers.py process/phase1_pubmed_results.json \\
  --include "dietary" "cognitive" \\
  --exclude "animal" \\
  --abstract-only \\
  --sort-by evidence \\
  -o process/phase2_screened.json

# 只保留顶级期刊 (Tier 1-3)
python scripts/screen_papers.py process/phase1_pubmed_results.json \\
  --top-journals-only \\
  --sort-by journal \\
  -o process/phase2_screened.json

# 只保留特定研究类型
python scripts/screen_papers.py process/phase1_pubmed_results.json \\
  --study-types "Meta-Analysis" "Randomized Controlled Trial" \\
  -o process/phase2_screened.json
```

**适用于**: 快速scoping review、优先选择高质量证据

#### 方案B: 系统性筛选 (PRISMA方法学)

完整的PRISMA筛选流程：

1. **去重** (Deduplication)
2. **标题筛选** (Title Screening)
3. **摘要筛选** (Abstract Screening)
4. **全文筛选** (Full-text Screening)
5. **PRISMA流程图** (Flow Diagram)

详细的筛选方法学请参考: [phase2-screening.md](references/phase2-screening.md)

**适用于**: 系统性综述、发表级研究

**筛选后处理**:

```bash
# 筛选结果与Phase 1格式兼容
python scripts/build_citation_db.py process/phase2_screened.json
python scripts/generate_bibtex.py process/phase2_screened.json
```

**注意**: 如果不进行筛选，可以直接使用Phase 1结果进行后续步骤。

### Phase 3: LLM-Assisted Writing (Primary Method)

**核心流程**：LLM直接读取筛选后的文献数据（`phase2_screened.json`），分析文献内容，撰写综述。

#### 步骤1：准备Citation数据库

```bash
# 生成citekey数据库
python scripts/build_citation_db.py process/phase2_screened.json

# 生成BibTeX文件
python scripts/generate_bibtex.py process/phase2_screened.json
```

#### 步骤2：LLM直接阅读与写作

**执行方式**：请求LLM读取以下文件并撰写综述
1. `process/citation_db.json` - 包含完整文献数据和citekey（含摘要、作者、期刊等）
2. `process/phase2_screened.json` - 筛选后的原始文献数据（可选，用于交叉验证）

**LLM写作流程**：
1. **阅读文献数据**：读取`phase2_screened.json`中的所有文献字段（title, authors, abstract, journal, year等）
2. **分析文献内容**：理解每篇文献的研究目标、设计、方法、发现和结论
3. **组织综述结构**：根据文献主题和研究类型，逻辑组织综述结构
4. **撰写综述内容**：使用学术语言，综合多篇文献的发现
5. **添加引用标记**：使用`[@citekey]`格式引用文献，citekey来自`citation_db.json`

**写作规则**：

- ✅ 使用`[@citekey]`引用格式，citekey来自`citation_db.json`
- ✅ 引用必须仅来自Phase 1检索的文献（verification-first原则）
- ✅ 综合多篇文献的发现，避免单篇文献的大段摘要
- ✅ 使用学术语言和逻辑结构组织内容
- ❌ 禁止使用APA `(Author, Year)` 格式
- ❌ 禁止引用Phase 1数据中不存在的文献

**引用示例**：

```markdown
多项研究报道了运动对认知功能的积极影响。例如，经颅直流电刺激结合有氧运动可以改善卒中后认知功能障碍患者的工作记忆 [@zhou2025_exploring]。另一项研究发现，长期阻力运动可以改善APP/PS1小鼠的认知缺陷 [@azevedo2025_distinct]。
```

#### Phase 3 Alternative: 交互式脚本（可选）

`analyze_and_write.py` 是一个**辅助工具**，适用于需要更结构化分析的场景：

```bash
# 完整流程 - 分析+写作
python scripts/analyze_and_write.py phase2_screened.json --mode full --topic "运动与认知功能" -o review.md
```

**适用场景**：
- 需要更结构化的文献分析字段
- 需要保存分析结果供后续使用
- 需要脚本的验证功能（必需字段检查）

**注意**：对于大多数场景，LLM直接读取数据并撰写综述（步骤2）更高效。

### Phase 4: Verification

Verify all citekeys exist in BibTeX file.

```bash
python scripts/verify_bibtex_citations.py chapterXX/X.X-final.md process/references.bib [--verify-doi]
```

See [phase5-verification.md](references/phase5-verification.md) for details.

### Phase 5: PDF Rendering (Final Output)

Render Markdown to final PDF with formatted citations.

```bash
python scripts/generate_pdf.py chapterXX/X.X-final.md process/references.bib
```

**Features**:

- Converts `[@citekey]` to formatted citations
- Generates reference list automatically
- Produces publication-ready PDF

**Requirements**:

- Pandoc: `brew install pandoc`
- LaTeX (for PDF): `brew install mactex` or `tlmgr install scheme-full`

**Output formats**: PDF, HTML, Word (configurable)

## Citation Format

### NEW: BibTeX Citekey Markers

```markdown
Multiple studies documented this [@bold2023_smartphone; @jones2024_potentially].
```

NOT: `(Bold et al., 2023; Jones et al., 2024)`

### Citekey Format

`{first_author_surname}{year}_{first_word}`

Examples: `yu2021_association`, `jones2024_potentially`

## File Structure

```text
project/
├── process/
│   ├── search_mapping.json              # Phase 0: Search strategy
│   ├── phase1_pubmed_results_*.json     # Phase 1: Retrieved articles
│   ├── phase1_checkpoint.json           # Resume capability
│   ├── phase2_screened.json             # Phase 2: Screened articles
│   ├── phase2_analyzed.json             # Phase 3: LLM analysis results (optional)
│   ├── citation_db.json                 # Citation database with citekeys
│   └── references.bib                   # BibTeX file
└── chapterXX/
    └── X.X-final.md                     # Uses [@citekey] markers
```

## Additional Resources

**Testing & Validation**: See [testing-results.md](references/testing-results.md) for test results and data structure specifications.

**Troubleshooting**: See [testing-results.md](references/testing-results.md#common-issues) for common issues and solutions.

## Scripts Reference

| Script | Purpose |
| :----- | :------- |
| `generate_search_strategy.py` | Topic → MeSH queries |
| `pubmed_batch_retrieval.py` | PubMed retrieval with curl, batching, rate limiting |
| `verify_phase1_data.py` | Verify Phase 1 data completeness (abstracts, DOIs, duplicates) |
| `screen_papers.py` | Literature screening with study type detection, journal ranking |
| `analyze_and_write.py` | LLM-assisted literature analysis and writing (interactive) |
| `build_citation_db.py` | Generate citekey database |
| `generate_bibtex.py` | Create .bib file from articles |
| `verify_bibtex_citations.py` | Verify citations in markdown |
| `generate_pdf.py` | Render Markdown to PDF |

## Detailed Guides

**Phase Guides**:

- **Phase 1 retrieval**: [phase1-retrieval.md](references/phase1-retrieval.md)
- **Phase 2 screening**: [phase2-screening.md](references/phase2-screening.md)
- **Phase 3 writing**: [phase4-writing.md](references/phase4-writing.md)
- **Phase 4 verification**: [phase5-verification.md](references/phase5-verification.md)

**Writing Resources**:

- **Citation styles**: [citation_styles.md](references/citation_styles.md) - APA, Nature, Chicago, Vancouver formats
- **Review template**: [assets/review_template.md](assets/review_template.md) - Comprehensive literature review template

**Additional Reference**:

- **Citekey workflow**: [citekey-workflow.md](references/citekey-workflow.md) - How to use citekey markers
