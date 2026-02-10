#!/usr/bin/env python3
"""
screen_papers.py - 文献筛选与研究类型标记

功能：
1. 过滤不相关论文（基于关键词）
2. 标记研究类型（Meta分析、RCT、队列研究等）
3. 期刊筛选（只保留顶级期刊）
4. 按证据等级排序，方便写作时优先选择高质量研究

Usage:
    # 筛选并标记研究类型，按证据等级排序
    python screen_papers.py phase1_results.json \\
        --include "dietary" "cognitive" \\
        --exclude "animal" "review" \\
        --sort-by evidence \\
        -o phase2_screened.json

    # 只保留Meta分析和RCT
    python screen_papers.py phase1_results.json \\
        --study-types "Meta-Analysis" "Randomized Controlled Trial" \\
        -o phase2_screened.json

    # 只保留顶级期刊 (Tier 1-3)
    python screen_papers.py phase1_results.json \\
        --top-journals-only \\
        --sort-by journal \\
        -o phase2_screened.json
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# 研究类型定义（按证据等级排序）
STUDY_TYPE_HIERARCHY = {
    # 最高等级
    'Meta-Analysis': 1,
    'Systematic Review': 2,
    'Guideline': 3,
    'Practice Guideline': 3,

    # 实验性研究
    'Randomized Controlled Trial': 10,
    'Clinical Trial': 11,
    'Controlled Clinical Trial': 12,

    # 观察性研究
    'Cohort Studies': 20,
    'Longitudinal Studies': 21,
    'Prospective Studies': 22,
    'Case-Control Studies': 23,
    'Cross-Sectional Studies': 24,
    'Observational Study': 25,

    # 其他
    'Journal Article': 50,
    'Research Support': 60,
    'Review': 70,

    # 低等级
    'Review': 70,
    'Narrative Review': 71,
    'Editorial': 80,
    'Letter': 81,
    'Comment': 82,
    'News': 83,
}

# 研究类型别名映射（用于匹配不同的表达方式）
STUDY_TYPE_ALIASES = {
    'meta-analysis': 'Meta-Analysis',
    'meta analysis': 'Meta-Analysis',
    'systematic review': 'Systematic Review',
    'rct': 'Randomized Controlled Trial',
    'randomized': 'Randomized Controlled Trial',
    'randomised': 'Randomized Controlled Trial',
    'clinical trial': 'Clinical Trial',
    'cohort': 'Cohort Studies',
    'longitudinal': 'Longitudinal Studies',
    'case-control': 'Case-Control Studies',
    'cross-sectional': 'Cross-Sectional Studies',
}

# 顶级期刊列表（按领域分类，影响因子和声誉综合评估）
TOP_JOURNALS = {
    # 综合医学期刊 (Tier 1)
    'nature',
    'science',
    'cell',
    'the lancet',
    'nejm',
    'new england journal of medicine',
    'jama',
    'journal of the american medical association',
    'bmj',
    'british medical journal',

    # 临床医学
    'annals of internal medicine',
    'pnas',
    'proceedings of the national academy of sciences',
    'the bmj',

    # 营养学
    'american journal of clinical nutrition',
    'the journal of nutrition',
    'nutrition reviews',
    'advances in nutrition',
    'international journal of behavioral nutrition and physical activity',

    # 神经科学/认知
    'nature neuroscience',
    'science translational medicine',
    'journal of neuroscience',
    'brain',
    'neurology',
    'alzheimer',

    # 公共卫生/流行病学
    'american journal of epidemiology',
    'international journal of epidemiology',
    'epidemiology',
    'public health nutrition',

    # 老年医学
    'journals of gerontology',
    'age and ageing',
    'the journal of gerontology',

    # 高影响因子中文期刊
    '中华医学杂志',
    '中华流行病学杂志',
    '中华老年医学杂志',
}

# 期刊排名 (数字越小等级越高)
JOURNAL_RANK = {
    # Tier 1 - 顶级综合期刊 (IF > 50)
    'nature': 1,
    'science': 1,
    'cell': 1,
    'the lancet': 1,
    'nejm': 1,
    'new england journal of medicine': 1,
    'jama': 1,
    'journal of the american medical association': 1,

    # Tier 2 - 顶级专业期刊 (IF 20-50)
    'nature neuroscience': 2,
    'pnas': 2,
    'proceedings of the national academy of sciences': 2,
    'bmj': 2,
    'british medical journal': 2,
    'annals of internal medicine': 2,

    # Tier 3 - 高影响因子专业期刊 (IF 10-20)
    'brain': 3,
    'neurology': 3,
    'alzheimer': 3,
    'american journal of clinical nutrition': 3,
    'american journal of epidemiology': 3,
    'international journal of epidemiology': 3,
    'journals of gerontology': 3,

    # Tier 4 - 良好专业期刊 (IF 5-10)
    'the journal of nutrition': 4,
    'nutrition reviews': 4,
    'advances in nutrition': 4,
    'journal of neuroscience': 4,
    'age and ageing': 4,
    'epidemiology': 4,

    # Tier 5 - 其他期刊
    'default': 5,
}


def detect_study_type(paper: dict) -> Tuple[str, int]:
    """
    检测研究类型并返回 (类型名称, 证据等级)

    优先级：publication_types > title/abstract关键词
    """
    pub_types = paper.get('publication_types', [])
    title = (paper.get('title', '') or '').lower()
    abstract = (paper.get('abstract', '') or '').lower()

    # 首先检查 publication_types（最准确）
    for pub_type in pub_types:
        pub_type_lower = pub_type.lower()
        # 精确匹配
        if pub_type in STUDY_TYPE_HIERARCHY:
            return pub_type, STUDY_TYPE_HIERARCHY[pub_type]
        # 别名匹配
        for alias, standard_name in STUDY_TYPE_ALIASES.items():
            if alias in pub_type_lower:
                return standard_name, STUDY_TYPE_HIERARCHY[standard_name]

    # 如果 publication_types 没有匹配，检查标题和摘要
    text = f"{title} {abstract}"

    # 按优先级检查关键词
    keywords_priority = [
        (['meta-analysis', 'meta analysis', 'systematic review'], 'Meta-Analysis'),
        (['guideline', 'practice guideline'], 'Guideline'),
        (['randomized controlled trial', 'rct', 'randomized trial'], 'Randomized Controlled Trial'),
        (['clinical trial', 'intervention study'], 'Clinical Trial'),
        (['cohort', 'longitudinal', 'prospective'], 'Cohort Studies'),
        (['case-control', 'case control'], 'Case-Control Studies'),
        (['cross-sectional'], 'Cross-Sectional Studies'),
    ]

    for keywords, study_type in keywords_priority:
        if any(kw in text for kw in keywords):
            return study_type, STUDY_TYPE_HIERARCHY[study_type]

    # 默认分类
    if 'review' in text:
        return 'Review', STUDY_TYPE_HIERARCHY['Review']

    return 'Journal Article', STUDY_TYPE_HIERARCHY['Journal Article']


def get_journal_rank(journal: str) -> int:
    """
    获取期刊排名等级

    Returns:
        int: 1-5, 数字越小等级越高 (1=顶级, 5=其他)
    """
    if not journal:
        return 5

    journal_lower = journal.lower().strip()

    # 精确匹配
    if journal_lower in JOURNAL_RANK:
        return JOURNAL_RANK[journal_lower]

    # 模糊匹配（检查期刊名是否包含顶级期刊关键词）
    for top_journal in JOURNAL_RANK.keys():
        if top_journal != 'default' and top_journal in journal_lower:
            return JOURNAL_RANK[top_journal]

    return 5


def calculate_relevance_score(paper: dict, include_keywords: List[str],
                              exclude_keywords: List[str] = None) -> float:
    """
    计算相关性评分 (0-1)

    基于：关键词出现频率、位置（标题权重更高）
    """
    title = (paper.get('title', '') or '').lower()
    abstract = (paper.get('abstract', '') or '').lower()
    keywords_list = paper.get('keywords', [])
    mesh_terms = paper.get('mesh_terms', [])

    # 转换为小写
    include_kw = [k.lower() for k in include_keywords]
    exclude_kw = [k.lower() for k in (exclude_keywords or [])]

    # 检查排除关键词
    for kw in exclude_kw:
        if kw in title or kw in abstract:
            return 0.0

    # 计算相关性得分
    score = 0.0
    for kw in include_kw:
        # 标题匹配（权重高）
        if kw in title:
            score += 0.3
        # 摘要匹配
        if kw in abstract:
            score += 0.1
        # 关键词匹配
        if any(kw in k.lower() for k in keywords_list):
            score += 0.15
        # MeSH术语匹配
        if any(kw in m.lower() for m in mesh_terms):
            score += 0.2

    return min(score, 1.0)


def mark_study_types(papers: List[dict]) -> List[dict]:
    """为每篇文献标记研究类型、证据等级和期刊排名"""
    for paper in papers:
        study_type, evidence_level = detect_study_type(paper)
        paper['_study_type'] = study_type
        paper['_evidence_level'] = evidence_level
        paper['_journal_rank'] = get_journal_rank(paper.get('journal', ''))
    return papers


def filter_and_sort(papers: List[dict],
                   include_keywords: List[str] = None,
                   exclude_keywords: List[str] = None,
                   study_types: List[str] = None,
                   sort_by: str = 'evidence',
                   min_relevance: float = 0.0,
                   top_journals_only: bool = False,
                   max_journal_rank: int = None) -> List[dict]:
    """
    筛选并排序文献

    Args:
        papers: 文献列表
        include_keywords: 必须包含的关键词
        exclude_keywords: 必须排除的关键词
        study_types: 保留的研究类型列表
        sort_by: 排序方式 ('evidence', 'relevance', 'year', 'journal')
        min_relevance: 最低相关性阈值
        top_journals_only: 只保留顶级期刊
        max_journal_rank: 最高期刊等级 (1-5, 数字越小越顶级)
    """
    # 标记研究类型和期刊等级
    papers = mark_study_types(papers)

    filtered = []
    for paper in papers:
        # 期刊筛选
        if top_journals_only:
            if paper['_journal_rank'] > 3:  # 只保留Tier 1-3期刊
                continue
        if max_journal_rank is not None:
            if paper['_journal_rank'] > max_journal_rank:
                continue

        # 研究类型筛选
        if study_types:
            if paper['_study_type'] not in study_types:
                continue

        # 关键词筛选
        if include_keywords or exclude_keywords:
            relevance = calculate_relevance_score(paper, include_keywords or [], exclude_keywords)
            paper['_relevance_score'] = relevance
            if relevance < min_relevance:
                continue
        else:
            paper['_relevance_score'] = 1.0

        filtered.append(paper)

    # 排序
    if sort_by == 'evidence':
        filtered.sort(key=lambda p: (p['_evidence_level'], p.get('year', '0')), reverse=False)
    elif sort_by == 'relevance':
        filtered.sort(key=lambda p: p['_relevance_score'], reverse=True)
    elif sort_by == 'year':
        filtered.sort(key=lambda p: p.get('year', '0'), reverse=True)
    elif sort_by == 'journal':
        # 先按期刊等级，再按证据等级
        filtered.sort(key=lambda p: (p['_journal_rank'], p['_evidence_level']), reverse=False)

    return filtered


def print_summary(papers: List[dict]) -> None:
    """打印筛选结果摘要"""
    if not papers:
        print("没有文献符合筛选条件")
        return

    # 按研究类型和期刊分组统计
    type_counts = defaultdict(int)
    journal_counts = defaultdict(int)
    type_papers = defaultdict(list)

    for paper in papers:
        study_type = paper['_study_type']
        journal_rank = paper['_journal_rank']
        journal = paper.get('journal', 'Unknown')

        type_counts[study_type] += 1
        journal_counts[journal_rank] += 1
        type_papers[study_type].append(paper)

    print(f"\n{'='*70}")
    print(f"筛选结果统计 (共 {len(papers)} 篇)")
    print(f"{'='*70}")

    # 按证据等级顺序显示研究类型
    sorted_types = sorted(type_counts.items(), key=lambda x: STUDY_TYPE_HIERARCHY.get(x[0], 999))

    for study_type, count in sorted_types:
        level = STUDY_TYPE_HIERARCHY.get(study_type, 999)
        level_name = "高" if level < 10 else "中" if level < 30 else "低"
        print(f"  {study_type:30s} : {count:3d} 篇 (证据等级: {level_name})")

    # 期刊等级统计
    print(f"\n{'='*70}")
    print(f"期刊等级分布:")
    print(f"{'='*70}")

    journal_rank_names = {
        1: "Tier 1 - 顶级综合期刊 (Nature, Science, Lancet等)",
        2: "Tier 2 - 顶级专业期刊",
        3: "Tier 3 - 高影响因子专业期刊 (IF 10-20)",
        4: "Tier 4 - 良好专业期刊 (IF 5-10)",
        5: "Tier 5 - 其他期刊"
    }

    for rank in sorted(journal_counts.keys()):
        count = journal_counts[rank]
        rank_name = journal_rank_names.get(rank, f"Tier {rank}")
        print(f"  {rank_name}: {count} 篇")

    print(f"\n{'='*70}")
    print(f"各研究类型的前3篇文献:")
    print(f"{'='*70}")

    for study_type, _ in sorted_types[:5]:  # 只显示前5个类型
        papers_in_type = type_papers[study_type][:3]
        print(f"\n[{study_type}]")
        for i, paper in enumerate(papers_in_type, 1):
            pmid = paper.get('pmid', 'N/A')
            title = paper.get('title', 'No title')[:70]
            year = paper.get('year', 'N/A')
            journal = paper.get('journal', 'Unknown')
            journal_rank = paper['_journal_rank']
            relevance = paper.get('_relevance_score', 1.0)
            print(f"  {i}. PMID: {pmid} ({year}) - 相关度: {relevance:.2f} - 期刊: Tier {journal_rank}")
            print(f"     {journal}")
            print(f"     {title}...")


def save_results(papers: List[dict], input_data: dict,
                output_file: Path, criteria: dict) -> None:
    """保存筛选结果"""
    # 按研究类型分组
    grouped = defaultdict(list)
    for paper in papers:
        grouped[paper['_study_type']].append(paper)

    output_data = {
        "timestamp": input_data.get("timestamp"),
        "section": input_data.get("section"),
        "outline_title": input_data.get("outline_title"),
        "date_range": input_data.get("date_range"),
        "screening_info": {
            "source_file": str(input_data.get("_source_file", "unknown")),
            "total_original": len(input_data.get("articles", [])),
            "total_selected": len(papers),
            "selection_criteria": criteria,
        },
        "study_type_summary": {
            study_type: len(papers_list)
            for study_type, papers_list in grouped.items()
        },
        "articles": papers
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ 筛选结果已保存到: {output_file}")
    print(f"  原始文献: {input_data.get('total_original', len(input_data.get('articles', [])))} 篇")
    print(f"  筛选后: {len(papers)} 篇")


def main():
    parser = argparse.ArgumentParser(
        description='筛选文献并标记研究类型',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 按关键词筛选，按证据等级排序
  python screen_papers.py phase1_results.json \\
    --include "dietary" "cognitive" \\
    --exclude "animal" \\
    --sort-by evidence \\
    -o phase2_screened.json

  # 只保留Meta分析和RCT
  python screen_papers.py phase1_results.json \\
    --study-types "Meta-Analysis" "Randomized Controlled Trial" \\
    -o phase2_screened.json

  # 只保留顶级期刊 (Tier 1-3: Nature, Science, Lancet等)
  python screen_papers.py phase1_results.json \\
    --top-journals-only \\
    --sort-by journal \\
    -o phase2_screened.json

  # 按相关性排序
  python screen_papers.py phase1_results.json \\
    --include "mediterranean" "diet" \\
    --sort-by relevance \\
    -o phase2_screened.json
        '''
    )

    parser.add_argument('input_file', type=Path, help='Phase 1检索结果JSON文件')
    parser.add_argument('--output', '-o', type=Path, help='输出筛选后的文献JSON文件')

    # 筛选条件
    parser.add_argument('--include', nargs='+', help='必须包含的关键词')
    parser.add_argument('--exclude', nargs='+', help='必须排除的关键词')
    parser.add_argument('--study-types', nargs='+',
                       help='只保留特定研究类型 (如: "Meta-Analysis", "Randomized Controlled Trial")')
    parser.add_argument('--min-relevance', type=float, default=0.0,
                       help='最低相关性阈值 (0-1, 默认: 0.0)')
    parser.add_argument('--abstract-only', action='store_true', help='只保留有摘要的文献')

    # 期刊筛选
    parser.add_argument('--top-journals-only', action='store_true',
                       help='只保留顶级期刊 (Tier 1-3)')
    parser.add_argument('--max-journal-rank', type=int, choices=[1, 2, 3, 4, 5],
                       help='最高期刊等级 (1=顶级综合, 2=顶级专业, 3=高影响因子, 4=良好, 5=其他)')

    # 排序方式
    parser.add_argument('--sort-by', choices=['evidence', 'relevance', 'year', 'journal'],
                       default='evidence',
                       help='排序方式: evidence(证据等级), relevance(相关性), year(年份), journal(期刊) [默认: evidence]')
    parser.add_argument('--limit', type=int, help='限制输出数量')

    # 显示选项
    parser.add_argument('--summary-only', action='store_true', help='只显示统计摘要，不保存文件')

    args = parser.parse_args()

    # 加载数据
    with open(args.input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    papers = data.get('articles', [])
    data['_source_file'] = args.input_file

    print(f"加载了 {len(papers)} 篇文献")

    # 筛选有摘要的文献
    if args.abstract_only:
        before = len(papers)
        papers = [p for p in papers if p.get('abstract')]
        print(f"筛选有摘要: {before} → {len(papers)} 篇")

    # 筛选和排序
    filtered = filter_and_sort(
        papers,
        include_keywords=args.include,
        exclude_keywords=args.exclude,
        study_types=args.study_types,
        sort_by=args.sort_by,
        min_relevance=args.min_relevance,
        top_journals_only=args.top_journals_only,
        max_journal_rank=args.max_journal_rank
    )

    # 限制数量
    if args.limit:
        filtered = filtered[:args.limit]
        print(f"限制输出数量: {len(filtered)} 篇")

    # 打印摘要
    print_summary(filtered)

    # 保存结果
    if not args.summary_only and args.output:
        criteria = {
            'include_keywords': args.include,
            'exclude_keywords': args.exclude,
            'study_types': args.study_types,
            'sort_by': args.sort_by,
            'min_relevance': args.min_relevance,
            'abstract_only': args.abstract_only,
            'top_journals_only': args.top_journals_only,
            'max_journal_rank': args.max_journal_rank
        }
        save_results(filtered, data, args.output, criteria)

        print(f"\n下一步: 使用筛选后的结果生成citation数据库和BibTeX")
        print(f"  python scripts/build_citation_db.py {args.output}")
    elif not args.summary_only:
        print("\n提示: 使用 -o 参数保存筛选结果")


if __name__ == '__main__':
    main()
