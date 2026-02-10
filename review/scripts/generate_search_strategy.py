#!/usr/bin/env python3
"""
generate_search_strategy.py - AI-assisted PubMed search strategy generator

This script helps generate professional PubMed search strategies by:
1. Displaying a structured prompt for AI assistant analysis
2. Accepting PICO analysis in JSON format
3. Converting the analysis into PubMed search queries

Usage:
    # Interactive mode (default)
    python generate_search_strategy.py "睡眠质量与心血管疾病风险"

    # Skip interactive, provide JSON via stdin or paste
    python generate_search_strategy.py "睡眠质量与心血管疾病风险" --skip-interactive

    # Read JSON from file
    python generate_search_strategy.py "topic" --json analysis.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List


def print_ai_prompt(topic: str) -> None:
    """Print structured prompt for AI assistant analysis"""
    print("=" * 70)
    print("请将以下问题发送给AI助手（在当前对话中）:")
    print("=" * 70)
    print()
    print(f"""请帮我分析以下研究主题并生成PubMed检索策略:

**研究主题**: {topic}

请提供PICO分析，对每个元素请提供:

1. **Population (人群)**: 研究对象是谁？
2. **Exposure/Intervention (暴露/干预)**: 主要暴露因素或干预措施是什么？
3. **Outcome (结局)**: 结局指标是什么？

对每个元素，请提供:
- MeSH术语 (使用[mh]标记，例如: "Alzheimer Disease"[mh])
- 自由词检索词 (使用[Title/Abstract]标记，例如: biomarkers[Title/Abstract])

请以JSON格式返回，格式如下:

{{
  "population": {{
    "name": "例如: Older adults",
    "mesh_terms": ["Aged[mh]", "Frailty[mh]"],
    "free_text_terms": ["elderly[Title/Abstract]", "older adults[Title/Abstract]"]
  }},
  "exposure": {{
    "name": "例如: Physical exercise",
    "mesh_terms": ["Exercise[mh]"],
    "free_text_terms": ["exercise[Title/Abstract]", "physical activity[Title/Abstract]"]
  }},
  "outcome": {{
    "name": "例如: Cognitive function",
    "mesh_terms": ["Cognition[mh]"],
    "free_text_terms": ["cognit*[Title/Abstract]", "memory[Title/Abstract]"]
  }}
}}

如果某个元素无法识别，请使用空数组。""")
    print()
    print("=" * 70)


def get_ai_analysis_interactive() -> dict:
    """Get PICO analysis from user (who got it from AI assistant)"""
    print()
    print("请粘贴AI助手返回的JSON分析结果:")
    print("(输入完成后按回车，然后输入Ctrl+D或输入'END'结束)")
    print()

    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
    except EOFError:
        pass

    json_text = "\n".join(lines)

    # Try to extract JSON from text
    json_match = re.search(r'\{[\s\S]*\}', json_text)
    if json_match:
        json_text = json_match.group(0)

    try:
        analysis = json.loads(json_text)
        return analysis
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        print("请确保粘贴的是有效的JSON格式")
        sys.exit(1)


def read_json_from_file(json_file: Path) -> dict:
    """Read PICO analysis from JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ 无法读取JSON文件: {e}")
        sys.exit(1)


def build_boolean_query(mesh_terms: List[str], free_terms: List[str]) -> str:
    """Build Boolean query from MeSH and free text terms"""
    parts = []

    if mesh_terms:
        # Join MeSH terms with OR
        parts.append("(" + " OR ".join(mesh_terms) + ")")

    if free_terms:
        # Join free text terms with OR
        terms = [f"({t})" if " OR " in t or " and " in t.lower() else t for t in free_terms]
        parts.append("(" + " OR ".join(terms) + ")")

    if not parts:
        return ""

    return " AND ".join(parts) if len(parts) > 1 else parts[0]


def generate_search_queries(analysis: dict, year_range: str = "2022:2025") -> dict:
    """Generate PubMed search queries from topic analysis"""

    queries = []

    # Build base queries from analysis
    population = analysis.get("population", {})
    exposure = analysis.get("exposure", {})
    outcome = analysis.get("outcome", {})

    # Build exposure and outcome queries
    exp_query = build_boolean_query(
        exposure.get("mesh_terms", []),
        exposure.get("free_text_terms", [])
    )
    out_query = build_boolean_query(
        outcome.get("mesh_terms", []),
        outcome.get("free_text_terms", [])
    )

    # Only generate queries if we have meaningful terms
    if not exp_query or not out_query:
        print("❌ 错误: 检索词不足")
        print("   确保analysis包含exposure和outcome的mesh_terms或free_text_terms")
        sys.exit(1)

    # Theme 1: Main exposure-outcome relationship
    queries.append({
        "theme": f"{exposure['name'].replace(' ', '_')}_{outcome['name'].replace(' ', '_')}",
        "maps_to": ["1.1.1"],
        "query": f"({exp_query}) AND ({out_query}) AND ({year_range}[Date - Publication])",
        "retmax": 100
    })

    # Theme 2: Specific outcome focus (if MeSH available)
    if outcome.get("mesh_terms"):
        outcome_mesh = outcome["mesh_terms"][0]
        outcome_name = outcome_mesh.replace('"', '').replace('[mh]', '').replace(' ', '_')
        queries.append({
            "theme": f"{exposure['name'].replace(' ', '_')}_{outcome_name}",
            "maps_to": ["1.1.2"],
            "query": f"({exp_query}) AND {outcome_mesh} AND ({year_range}[Date - Publication])",
            "retmax": 100
        })

    # Theme 3: Systematic reviews/meta-analyses
    queries.append({
        "theme": f"Systematic_Reviews_{outcome['name'].replace(' ', '_')}",
        "maps_to": ["1.1.3"],
        "query": f"({out_query}) AND (systematic[sb] OR meta-analysis[pt] OR review[pt]) AND ({year_range}[Date - Publication])",
        "retmax": 50
    })

    return {
        "section": "1.1",
        "outline_title": analysis.get("exposure", {}).get("name", "Research Topic"),
        "date_range": f"{year_range}[Date - Publication]",
        "themes": queries
    }


def print_search_strategy_summary(strategy: dict):
    """Print summary of generated search strategy"""
    print("=" * 60)
    print("PubMed检索策略生成完成")
    print("=" * 60)
    print(f"\n研究主题: {strategy.get('outline_title', 'N/A')}")
    print(f"时间范围: {strategy.get('date_range', 'N/A')}")

    print(f"\n生成{len(strategy['themes'])}个检索主题:\n")

    for i, theme in enumerate(strategy['themes'], 1):
        print(f"{i}. {theme['theme']}")
        print(f"   映射到: {', '.join(theme['maps_to'])}")
        print(f"   检索数量: {theme['retmax']}")
        print(f"   检索式: {theme['query'][:120]}...")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='AI-assisted PubMed search strategy generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 交互模式 (默认) - 在当前对话中询问AI
  python generate_search_strategy.py "睡眠质量与心血管疾病风险"

  # 跳过交互 - 从文件读取JSON
  python generate_search_strategy.py "topic" --json analysis.json -o process/search_mapping.json

  # 预览检索策略（不保存）
  python generate_search_strategy.py "睡眠质量与心血管疾病风险" --dry-run
        '''
    )
    parser.add_argument('topic', help='研究主题 (例如: "运动与认知功能的关系")')
    parser.add_argument('--output', '-o', type=Path, help='输出文件路径 (默认: process/search_mapping.json)')
    parser.add_argument('--years', default='2022:2025', help='年份范围 (默认: 2022:2025)')
    parser.add_argument('--dry-run', action='store_true', help='只预览检索策略，不保存文件')
    parser.add_argument('--skip-interactive', action='store_true', help='跳过交互模式，直接从标准输入读取JSON')
    parser.add_argument('--json', type=Path, help='从JSON文件读取PICO分析')

    args = parser.parse_args()

    # Get PICO analysis
    if args.json:
        # Read from JSON file
        analysis = read_json_from_file(args.json)
    elif args.skip_interactive:
        # Read from stdin without showing prompt
        try:
            json_text = sys.stdin.read()
            json_match = re.search(r'\{[\s\S]*\}', json_text)
            if json_match:
                json_text = json_match.group(0)
            analysis = json.loads(json_text)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ JSON解析失败: {e}")
            sys.exit(1)
    else:
        # Interactive mode: show prompt and get analysis
        print_ai_prompt(args.topic)
        analysis = get_ai_analysis_interactive()

    # Generate search queries
    strategy = generate_search_queries(analysis, args.years)

    # Print summary
    print_search_strategy_summary(strategy)

    # Save file
    if not args.dry_run:
        if args.output:
            output_file = args.output
        else:
            output_file = Path("process/search_mapping.json")

        # Ensure directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, indent=2, ensure_ascii=False)

        print(f"✓ 检索策略已保存到: {output_file}")
        print(f"\n下一步: 执行PubMed检索")
        print(f"  python scripts/pubmed_batch_retrieval.py {output_file}")
    else:
        print("--dry-run 模式，文件未保存")


if __name__ == '__main__':
    main()
