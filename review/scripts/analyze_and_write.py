#!/usr/bin/env python3
"""
analyze_and_write.py - Phase 4: LLM辅助文献分析与写作

交互式流程：
1. 读取筛选后的文献（Phase 2输出）
2. 为每篇文献生成LLM分析提示
3. 收集LLM分析结果
4. 基于所有分析结果生成综述

Usage:
    # 分析模式（交互式）
    python scripts/analyze_and_write.py phase2_screened.json --mode analyze

    # 写作模式（基于已有分析结果）
    python scripts/analyze_and_write.py phase2_analyzed.json --mode write

    # 完整流程（分析+写作）
    python scripts/analyze_and_write.py phase2_screened.json --mode full
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def print_llm_prompt(paper: dict, index: int, total: int) -> None:
    """打印LLM分析提示"""
    pmid = paper.get('pmid', 'N/A')
    title = paper.get('title', 'No title')
    authors = paper.get('authors', [])
    abstract = paper.get('abstract', 'No abstract')
    journal = paper.get('journal', 'Unknown')
    year = paper.get('year', 'N/A')
    study_type = paper.get('_study_type', 'Unknown')
    evidence_level = paper.get('_evidence_level', 99)
    journal_rank = paper.get('_journal_rank', 5)

    print(f"\n{'='*80}")
    print(f"文献 [{index}/{total}]: PMID {pmid}")
    print(f"{'='*80}")
    print(f"\n📄 基本信息:")
    print(f"  标题: {title}")
    print(f"  期刊: {journal} ({year}) - Tier {journal_rank}")
    print(f"  作者: {', '.join(authors[:3])}{' et al.' if len(authors) > 3 else ''}")
    print(f"  研究类型: {study_type} (证据等级: {evidence_level})")

    print(f"\n📝 摘要:")
    print(f"  {abstract[:1500]}...")
    if len(abstract) > 1500:
        print(f"  [...摘要还有 {len(abstract) - 1500} 字]")

    print(f"\n{'='*80}")
    print(f"请将以下提示发送给AI助手进行分析：")
    print(f"{'='*80}")
    print()
    print(f"""请帮我分析以下文献，提取关键信息用于文献综述写作：

**PMID**: {pmid}
**标题**: {title}
**期刊**: {journal} ({year})
**研究类型**: {study_type}

**摘要**:
{abstract}

请提供以下分析（JSON格式）:
{{
  "pmid": "{pmid}",
  "study_objective": "研究目标是什么？",
  "study_design": "研究设计类型（如RCT、队列研究等）",
  "participants": "研究对象（样本量、人群特征）",
  "intervention_exposure": "干预措施或暴露因素",
  "comparison": "对照组",
  "outcomes": "主要结局指标和测量方法",
  "key_findings": "主要发现（具体数据）",
  "conclusions": "研究结论",
  "limitations": "研究局限性",
  "relevance_score": "与本综述的相关性（1-10分）",
  "quality_assessment": "研究质量评估（高/中/低）",
  "key_quotes": ["值得引用的原句1", "值得引用的原句2"]
}}

请只返回JSON，不要其他内容。""")
    print()
    print(f"{'='*80}")
    print(f"等待你粘贴AI的回复...")
    print(f"输入完成后按回车，然后输入'END'结束")
    print(f"{'='*80}")


def get_llm_analysis_interactive() -> dict:
    """获取LLM分析结果（交互式）"""
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
    except EOFError:
        pass

    json_text = '\n'.join(lines)

    # 提取JSON
    import re
    json_match = re.search(r'\{[^\{\}]*(?:\{[^\{\}]*\}[^\{\}]*)*\}', json_text, re.DOTALL)
    if json_match:
        json_text = json_match.group(0)

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON解析失败: {e}")
        print("请确保粘贴的是有效的JSON格式")
        return None


def analyze_papers_interactive(papers: List[dict]) -> List[dict]:
    """交互式分析所有文献"""
    analyzed = []

    print(f"\n{'='*80}")
    print(f"文献分析模式")
    print(f"{'='*80}")
    print(f"总共 {len(papers)} 篇文献需要分析")
    print(f"预计耗时: {len(papers) * 2-5} 分钟（取决于LLM响应速度）")
    print()
    print(f"提示：")
    print(f"  1. 为每篇文献生成分析提示")
    print(f"  2. 将提示发送给AI助手（在当前对话中）")
    print(f"  3. 粘贴AI的JSON回复")
    print(f"  4. 脚本验证并保存分析结果")
    print()

    for i, paper in enumerate(papers, 1):
        print_llm_prompt(paper, i, len(papers))

        analysis = get_llm_analysis_interactive()

        if analysis:
            # 验证必要字段
            required_fields = ['pmid', 'key_findings', 'conclusions']
            missing = [f for f in required_fields if not analysis.get(f)]
            if missing:
                print(f"⚠️  分析结果缺少字段: {missing}")
                print("是否继续？(y/n): ", end='')
                if input().strip().lower() != 'y':
                    print("跳过此篇，继续下一篇")
                    continue

            # 添加到分析结果
            paper_with_analysis = {**paper, '_analysis': analysis}
            analyzed.append(paper_with_analysis)
            print(f"✓ [{i}/{len(papers)}] 分析完成")
        else:
            print(f"✗ [{i}/{len(papers)}] 分析失败或被跳过")

    return analyzed


def save_analysis_results(papers: List[dict], output_file: Path, source_data: dict) -> None:
    """保存分析结果"""
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "source_file": str(source_data.get('screening_info', {}).get('source_file', 'unknown')),
        "total_analyzed": len(papers),
        "analysis_summary": {
            "avg_relevance_score": sum(
                p.get('_analysis', {}).get('relevance_score', 0) for p in papers
            ) / max(len(papers), 1),
            "high_quality_count": sum(
                1 for p in papers if p.get('_analysis', {}).get('quality_assessment') == '高'
            ),
        },
        "articles": papers
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ 分析结果已保存到: {output_file}")
    print(f"  分析文献数: {len(papers)}")


def print_writing_prompt(papers: List[dict], topic: str) -> None:
    """打印写作提示"""
    print(f"\n{'='*80}")
    print(f"基于分析结果的文献综述写作")
    print(f"{'='*80}")
    print()
    print(f"**研究主题**: {topic}")
    print(f"**纳入文献数**: {len(papers)}")
    print()
    print(f"以下是为每篇文献分析的关键发现：")
    print()

    for i, paper in enumerate(papers[:10], 1):  # 只显示前10篇
        pmid = paper.get('pmid', 'N/A')
        title = paper.get('title', 'No title')[:80]
        analysis = paper.get('_analysis', {})

        print(f"[{i}] PMID: {pmid}")
        print(f"    标题: {title}...")
        print(f"    主要发现: {analysis.get('key_findings', 'N/A')[:100]}...")
        print(f"    结论: {analysis.get('conclusions', 'N/A')[:100]}...")
        print(f"    相关性: {analysis.get('relevance_score', 'N/A')}/10")
        print()

    if len(papers) > 10:
        print(f"... 还有 {len(papers) - 10} 篇文献")

    print()
    print(f"{'='*80}")
    print(f"请将以下内容发送给AI助手进行综述写作：")
    print(f"{'='*80}")
    print()
    print(f"""我已经分析了 {len(papers)} 篇关于"{topic}"的文献。现在请你帮我撰写一篇系统综述。

**文献列表及关键发现**：

""")

    for i, paper in enumerate(papers, 1):
        pmid = paper.get('pmid', 'N/A')
        title = paper.get('title', 'No title')
        analysis = paper.get('_analysis', {})

        print(f"""文献{i}: PMID {pmid}
- 标题: {title}
- 研究设计: {analysis.get('study_design', 'N/A')}
- 主要发现: {analysis.get('key_findings', 'N/A')}
- 结论: {analysis.get('conclusions', 'N/A')}
- 相关性: {analysis.get('relevance_score', 'N/A')}/10
- 质量评估: {analysis.get('quality_assessment', 'N/A')}

""")

    print(f"""**写作要求**:

1. **结构**:
   - 引言（背景、研究目的）
   - 方法（简要说明纳入标准）
   - 结果（按主题或研究类型组织）
   - 讨论（综合分析各研究结论）
   - 结论

2. **引用格式**: 使用citekey格式，如 [@pmid_year_keyword]
   - citekey格式由期刊名年份和关键词组成
   - 示例: [@nature2025_dietary], [@lancet2024_cognitive]

3. **重点**:
   - 突出高质量证据（系统综述、RCT、顶级期刊）
   - 综合各研究的主要发现
   - 指出研究间的一致性和差异
   - 提出研究局限和未来方向

请使用markdown格式撰写综述，并在适当位置使用citekey引用文献。""")


def write_review_interactive(papers: List[dict], topic: str, output_file: Path) -> None:
    """交互式写作综述"""
    print_writing_prompt(papers, topic)

    print()
    print(f"{'='*80}")
    print(f"等待你粘贴AI生成的综述...")
    print(f"输入完成后按回车，然后输入'END'结束")
    print(f"{'='*80}")

    lines = []
    try:
        while True:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
    except EOFError:
        pass

    review_text = '\n'.join(lines)

    # 保存综述
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(review_text)

    print()
    print(f"✓ 综述已保存到: {output_file}")
    print(f"  字数: {len(review_text)}")


def main():
    parser = argparse.ArgumentParser(
        description='LLM辅助文献分析与写作',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 分析模式 - 交互式分析每篇文献
  python scripts/analyze_and_write.py phase2_screened.json --mode analyze -o phase2_analyzed.json

  # 写作模式 - 基于已有分析结果写综述
  python scripts/analyze_and_write.py phase2_analyzed.json --mode write --topic "饮食模式与认知功能" -o review.md

  # 完整流程 - 分析+写作
  python scripts/analyze_and_write.py phase2_screened.json --mode full --topic "饮食模式与认知功能" -o review.md
        '''
    )

    parser.add_argument('input_file', type=Path, help='Phase 2筛选结果JSON文件')
    parser.add_argument('--mode', choices=['analyze', 'write', 'full'], required=True,
                       help='模式: analyze(分析), write(写作), full(完整流程)')
    parser.add_argument('--topic', help='研究主题（写作模式需要）')
    parser.add_argument('--output', '-o', type=Path, help='输出文件路径')

    args = parser.parse_args()

    # 加载数据
    with open(args.input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    papers = data.get('articles', [])

    if not papers:
        print("❌ 没有找到文献数据")
        sys.exit(1)

    print(f"加载了 {len(papers)} 篇文献")

    # 设置默认输出文件
    if not args.output:
        if args.mode == 'analyze':
            args.output = args.input_file.parent / 'phase2_analyzed.json'
        elif args.mode in ['write', 'full']:
            args.output = args.input_file.parent / 'review.md'

    if args.mode == 'analyze':
        # 分析模式
        analyzed = analyze_papers_interactive(papers)
        save_analysis_results(analyzed, args.output, data)

    elif args.mode == 'write':
        # 写作模式
        if not args.topic:
            print("❌ 写作模式需要 --topic 参数")
            sys.exit(1)
        write_review_interactive(papers, args.topic, args.output)

    elif args.mode == 'full':
        # 完整流程：先分析，再写作
        print("\n[阶段 1/2] 文献分析")
        analyzed = analyze_papers_interactive(papers)

        # 保存分析结果
        analysis_file = args.input_file.parent / 'phase2_analyzed.json'
        save_analysis_results(analyzed, analysis_file, data)

        print(f"\n[阶段 2/2] 文献写作")
        if not args.topic:
            print("⚠️  未提供 --topic 参数，使用默认主题")
            args.topic = data.get('outline_title', '文献综述')

        # 更新输出文件名
        if args.output.name == 'review.md':
            args.output = args.input_file.parent / 'review.md'

        write_review_interactive(analyzed, args.topic, args.output)

        print(f"\n✓ 完整流程完成！")
        print(f"  分析结果: {analysis_file}")
        print(f"  综述文件: {args.output}")


if __name__ == '__main__':
    main()
