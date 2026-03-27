# Skill Integration Patterns

How vibe-research works with existing skills.

## Skill Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                 High-Level Workflows                     │
├─────────────────────────────────────────────────────────┤
│  vibe-coding          │  vibe-research                   │
│  (AI-assisted coding) │  (AI-assisted research)          │
├─────────────────────────────────────────────────────────┤
│                 Execution Layer                          │
├─────────────────────────────────────────────────────────┤
│  review               │  data-skill                      │
│  (literature review)  │  (data analysis)                 │
├─────────────────────────────────────────────────────────┤
│                 Tool Layer                               │
├─────────────────────────────────────────────────────────┤
│  scientific-skills (90+ domain-specific tools)          │
└─────────────────────────────────────────────────────────┘
```

## When to Call Which Skill

### vibe-coding vs vibe-research

| Scenario | Use |
|----------|-----|
| "帮我实现一个排序算法" | vibe-coding |
| "帮我写一个数据分析脚本" | vibe-coding |
| "研究一下 X 对 Y 的影响" | vibe-research |
| "帮我做文献综述" | vibe-research |

### review skill (Literature)

| Trigger | Call review skill |
|---------|-------------------|
| Need PubMed search | `review` Phase 1 |
| Need to screen papers | `review` Phase 2 |
| Need verified citations | `review` Phase 3-4 |
| Need BibTeX generation | `review` scripts |

**Key Scripts**:
- `generate_search_strategy.py` - Topic to MeSH
- `pubmed_batch_retrieval.py` - PubMed retrieval
- `screen_papers.py` - Smart screening
- `build_citation_db.py` - Citation database
- `verify_bibtex_citations.py` - Citation verification

### data-skill (Analysis)

| Trigger | Use data-skill |
|---------|----------------|
| Variable exploration | `templates/*/explore_variable.*` |
| Data cleaning | `templates/*/clean_data.*` |
| Scatter/bar/box plots | `templates/*/plot_*.*` |
| Statistical tests | `templates/*/statistical_test.*` |
| Quarto documents | QMD integration workflow |

### scientific-skills (Domain Tools)

| Domain | Route to |
|--------|----------|
| Medical literature | `pubmed-database` |
| ML/AI | `scikit-learn`, `pymc`, `transformers` |
| Visualization | `matplotlib`, `seaborn`, `plotly` |
| Scientific writing | `scientific-writing`, `scientific-slides` |
| Clinical research | `clinicaltrials`, `fda`, `clinvar` |

## Combined Workflow Example

```
User: "研究ACEs对老年人认知功能的影响"

vibe-research dispatches:
  │
  ├─► Step 1: 知识缺口
  │     └─► AI分析文献结构
  │
  ├─► Step 2: 文献综述
  │     └─► review skill
  │           ├─► pubmed_batch_retrieval.py
  │           ├─► screen_papers.py
  │           └─► build_citation_db.py
  │
  ├─► Step 3: 假设生成
  │     └─► AI + 人选择
  │
  ├─► Step 4: 实验设计
  │     └─► vibe-coding (写分析代码)
  │
  ├─► Step 5: 执行
  │     └─► 运行分析
  │
  ├─► Step 6: 分析
  │     └─► data-skill
  │           ├─► statistical_test.R
  │           └─► plot_*.R
  │
  └─► Step 7: 写作
        └─► scientific-writing + review引用
```

## Key Principles

1. **vibe-research is the orchestrator** - It decides what to do, not how
2. **review handles literature** - All citation-related work goes through review
3. **data-skill handles analysis** - Statistical and visualization work
4. **scientific-skills provides tools** - Domain-specific capabilities
5. **vibe-coding handles code** - When research requires coding

## Avoiding Duplication

| What | Where it lives | How to use |
|------|---------------|------------|
| PubMed检索 | review skill | Call review, don't reimplement |
| 统计模板 | data-skill | Use data-skill templates |
| 引用格式 | review skill | Use review's BibTeX workflow |
| 可视化主题 | data-skill | Use data-skill themes |

## Skill Communication Pattern

```python
# In vibe-research SKILL.md
"调用 review skill 进行文献检索"

# In execution
# AI reads vibe-research → sees "调用 review skill" → reads review skill → executes
```

This pattern allows:
- Each skill to be independently maintained
- vibe-research to stay high-level
- Execution details to live in specialized skills
