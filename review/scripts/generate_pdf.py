#!/usr/bin/env python3
"""
generate_pdf.py - 将Markdown文献综述渲染为PDF

自动处理 [@citekey] 引用，生成格式化的PDF文档。

Usage:
    python generate_pdf.py chapter01/1.1-final.md process/references.bib
    python generate_pdf.py chapter01/1.1-final.md process/references.bib --output paper.pdf
    python generate_pdf.py chapter01/1.1-final.md process/references.bib --format html
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set


def check_dependencies():
    """检查必要的依赖"""
    dependencies = {
        'pandoc': 'Pandoc - 必需，用于Markdown转换',
        'pdflatex': 'LaTeX - PDF生成需要',
    }
    
    missing = []
    for cmd, desc in dependencies.items():
        if not subprocess.run(['which', cmd], capture_output=True).returncode == 0:
            missing.append(f"{cmd} ({desc})")
    
    if missing:
        print("❌ 缺少必要的依赖:")
        for m in missing:
            print(f"  - {m}")
        print()
        print("安装方法:")
        print("  brew install pandoc")
        print("  brew install mactex")
        return False
    
    return True


def extract_used_citekeys(md_file: Path) -> Set[str]:
    """从Markdown文件中提取使用的citekey"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取所有 [@citekey] 格式的引用
    citekeys = set(re.findall(r'\[@([a-z0-9_áéíóúñüöä\-]+)\]', content))
    return citekeys


def verify_citations_in_bibtex(md_file: Path, bib_file: Path) -> bool:
    """验证所有citekey都在BibTeX文件中"""
    citekeys = extract_used_citekeys(md_file)
    
    with open(bib_file, 'r', encoding='utf-8') as f:
        bib_content = f.read()
    
    # 提取BibTeX中的所有citekey
    bib_citekeys = set(re.findall(r'@article\{([^,]+),', bib_content))
    
    missing = citekeys - bib_citekeys
    
    if missing:
        print(f"❌ 发现 {len(missing)} 个citekey不在BibTeX文件中:")
        for ck in sorted(missing):
            print(f"  - @{ck}")
        return False
    
    print(f"✅ 所有 {len(citekeys)} 个citekey都在BibTeX文件中")
    return True


def generate_pdf(md_file: Path, bib_file: Path, output_file: Path = None) -> bool:
    """使用Pandoc生成PDF"""
    
    if not check_dependencies():
        return False
    
    # 验证引用
    if not verify_citations_in_bibtex(md_file, bib_file):
        return False
    
    # 默认输出文件名
    if output_file is None:
        output_file = md_file.with_suffix('.pdf')
    
    print()
    print("=== 生成PDF ===")
    print(f"输入: {md_file}")
    print(f"BibTeX: {bib_file}")
    print(f"输出: {output_file}")
    print()
    
    # 构建pandoc命令
    cmd = [
        'pandoc',
        str(md_file),
        '--bibliography', str(bib_file),
        '--citeproc',
        '--pdf-engine=xelatex',
        '-V', 'colorlinks=true',
        '-V', 'linkcolor=blue',
        '-V', 'urlcolor=blue',
        '-V', 'toc=true',
        '-V', 'toc-depth=2',
        '-o', str(output_file),
    ]
    
    print("执行命令:")
    print(' '.join(cmd))
    print()
    
    # 执行pandoc
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ PDF生成失败:")
            print(result.stderr)
            return False
        
        print(f"✅ PDF已生成: {output_file}")
        return True
        
    except FileNotFoundError:
        print("❌ 找不到pandoc命令")
        print("请安装: brew install pandoc")
        return False


def generate_html(md_file: Path, bib_file: Path, output_file: Path = None) -> bool:
    """生成HTML格式"""
    
    if output_file is None:
        output_file = md_file.with_suffix('.html')
    
    cmd = [
        'pandoc',
        str(md_file),
        '--bibliography', str(bib_file),
        '--citeproc',
        '--standalone',
        '-o', str(output_file),
    ]
    
    print(f"生成HTML: {output_file}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ HTML生成失败: {result.stderr}")
        return False
    
    print(f"✅ HTML已生成: {output_file}")
    return True


def generate_word(md_file: Path, bib_file: Path, output_file: Path = None) -> bool:
    """生成Word文档"""
    
    if output_file is None:
        output_file = md_file.with_suffix('.docx')
    
    cmd = [
        'pandoc',
        str(md_file),
        '--bibliography', str(bib_file),
        '--citeproc',
        '-o', str(output_file),
    ]
    
    print(f"生成Word: {output_file}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Word生成失败: {result.stderr}")
        return False
    
    print(f"✅ Word已生成: {output_file}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='将Markdown文献综述渲染为PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 生成PDF
  python generate_pdf.py chapter01/1.1-final.md process/references.bib
  
  # 指定输出文件
  python generate_pdf.py chapter01/1.1-final.md process/references.bib -o output.pdf
  
  # 生成HTML
  python generate_pdf.py chapter01/1.1-final.md process/references.bib --format html
  
  # 生成所有格式
  python generate_pdf.py chapter01/1.1-final.md process/references.bib --all
        '''
    )
    
    parser.add_argument('markdown_file', type=Path, help='输入的Markdown文件')
    parser.add_argument('bib_file', type=Path, help='BibTeX引用文件')
    parser.add_argument('--output', '-o', type=Path, help='输出文件路径')
    parser.add_argument('--format', choices=['pdf', 'html', 'word', 'all'], 
                        default='pdf', help='输出格式 (default: pdf)')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not args.markdown_file.exists():
        print(f"❌ 文件不存在: {args.markdown_file}")
        return 1
    
    if not args.bib_file.exists():
        print(f"❌ BibTeX文件不存在: {args.bib_file}")
        return 1
    
    print(f"=== 文献综述PDF生成器 ===")
    print(f"Markdown: {args.markdown_file}")
    print(f"BibTeX: {args.bib_file}")
    print()
    
    success = True
    
    if args.format == 'pdf':
        success = generate_pdf(args.markdown_file, args.bib_file, args.output)
    elif args.format == 'html':
        success = generate_html(args.markdown_file, args.bib_file, args.output)
    elif args.format == 'word':
        success = generate_word(args.markdown_file, args.bib_file, args.output)
    elif args.format == 'all':
        success = generate_pdf(args.markdown_file, args.bib_file)
        success = generate_html(args.markdown_file, args.bib_file) and success
        success = generate_word(args.markdown_file, args.bib_file) and success
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
