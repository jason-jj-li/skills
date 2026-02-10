# Citekey 引用格式工作流程

## 核心理念

```
写作: [@citekey] → 验证: verify_bibtex_citations.py → 渲染: Pandoc → 输出: HTML/PDF/Word
```

## 为什么使用 [@citekey]？

| 问题 | APA格式 | Citekey格式 |
|:-----|:--------|:-----------|
| 能否自动验证 | ❌ | ✅ 100%准确 |
| 防止LLM幻觉 | ❌ | ✅ 只能引用已检索文献 |
| 格式转换 | 手动 | 自动(任何格式) |
| 自由选择文献 | 困难 | 简单 |

---

## 完整工作流程

### 步骤1: 检索文献 (Phase 1)

```bash
python scripts/pubmed_batch_retrieval.py process/search_mapping.json
# 输出: process/phase1_pubmed_results.json (189篇文献)
```

### 步骤2: 生成BibTeX文件

```bash
python scripts/generate_bibtex.py process/phase1_pubmed_results.json
# 输出: process/references.bib (189个BibTeX条目)
```

### 步骤3: 生成citekey数据库

```bash
python scripts/build_citation_db.py process/phase1_pubmed_results.json > process/citation_db.json
# 输出: 每篇文献的citekey
```

### 步骤4: 筛选文献

**方式A: 交互式筛选**
```bash
python scripts/screen_papers.py process/phase1_pubmed_results.json --interactive -o process/selected.json
```

**方式B: 关键词筛选**
```bash
python scripts/screen_papers.py process/phase1_pubmed_results.json \
  --include "social" "depression" \
  --exclude "animal" \
  -o process/selected.json
```

### 步骤5: 写作 (使用 [@citekey])

```markdown
Recent research shows that social support is important [@deshpande2025_association].
Multiple studies have confirmed this [@jung2025_socially; @ali2026_im].

## References
(自动生成，或者写作时先不写，最后添加)
```

**关键点**:
- 使用`@citekey`而不是作者年份
- 每个citekey对应BibTeX中的一个条目
- 可以自由选择使用哪些citekey
- 未使用的citekey不会出现在最终参考文献中

### 步骤6: 验证引用

```bash
python scripts/verify_bibtex_citations.py chapter01/1.1-final.md process/references.bib
# 输出: ✅ PASS 或 ❌ FAIL (列出缺失的citekey)
```

### 步骤7: 渲染最终文档

**使用Pandoc渲染为多种格式**:

```bash
# 安装Pandoc
brew install pandoc

# 渲染为HTML (可直接在浏览器中查看)
pandoc chapter01/1.1-final.md \
  --bibliography=process/references.bib \
  --citeproc \
  -o chapter01/1.1-final.html

# 渲染为PDF
pandoc chapter01/1.1-final.md \
  --bibliography=process/references.bib \
  --citeproc \
  -o chapter01/1.1-final.pdf

# 渲染为Word文档
pandoc chapter01/1.1-final.md \
  --bibliography=process/references.bib \
  --citeproc \
  -o chapter01/1.1-final.docx

# 使用不同的引用格式 (APA, MLA, Chicago等)
pandoc chapter01/1.1-final.md \
  --bibliography=process/references.bib \
  --csl=apa.csl \
  --citeproc \
  -o chapter01/1.1-final-apa.html
```

**使用渲染脚本**:

```bash
./scripts/render_markdown.sh chapter01/1.1-final.md
# 自动生成: .html, .pdf, .docx
```

---

## 自由选择文献的示例

### 场景: 从189篇中选择5篇写作

1. **检索**: 获得189篇文献的BibTeX文件
2. **筛选**: 选择5篇最相关的文献
3. **写作**: 只使用这5篇的citekey
4. **验证**: `verify_bibtex_citations.py` 确认这5个citekey都存在
5. **渲染**: Pandoc自动生成只包含这5篇的参考文献列表

### 示例代码

```markdown
# 只使用5个citekey
Recent studies show [@deshpande2025_association] that social support 
is important for treatment outcomes. Other research [@jung2025_socially; 
@hernández-lópez2025_reducing] supports this finding.

## References
(自动生成，只包含上面使用的3篇文献)
```

---

## 格式转换示例

### 输入 (Markdown + citekey)

```markdown
This is important [@deshpande2025_association].
Multiple studies show [@jung2025_socially; @ali2026_im].
```

### 输出1: APA格式 (Pandoc)

```html
This is important (Deshpande et al., 2025).
Multiple studies show (Jung et al., 2025; Ali, 2026).
```

### 输出2: 数字格式

```html
This is important [1].
Multiple studies show [2][3].
```

### 输出3: 作者-年份格式

```html
This is important (Deshpande, Wu, & Steffens, 2025).
Multiple studies show (Jung et al., 2025; Ali, 2026).
```

---

## 常见问题

### Q: 为什么IDE预览不显示引用？

**A**: `[@citekey]`不是标准Markdown，需要用Pandoc渲染。

```bash
# 使用Pandoc预览
pandoc input.md --bibliography=references.bib --citeproc -o preview.html
open preview.html
```

### Q: 如何在IDE中预览？

**A**: 使用支持Pandoc的IDE扩展，或者：
1. 写作时用`[@citekey]`
2. 定期用Pandoc生成HTML预览
3. 在浏览器中查看最终效果

### Q: 如何只使用部分文献？

**A**: 只在Markdown中写需要的citekey即可。

```markdown
# BibTeX有189篇，但只引用5篇
Important finding [@citekey1].
Another study [@citekey2].

# 最终参考文献只包含citekey1和citekey2
```

---

## 文件组织

```
project/
├── process/
│   ├── search_mapping.json              # 检索策略
│   ├── phase1_pubmed_results.json       # 189篇原始结果
│   ├── selected.json                    # 筛选后的文献 (可选)
│   └── references.bib                   # 189个BibTeX条目
├── chapter01/
│   ├── 1.1-draft.md                    # 写作草稿 (使用 [@citekey])
│   ├── 1.1-final.md                   # 最终版本
│   └── 1.1-final.html                 # 渲染后的HTML (可预览)
└── scripts/
    ├── render_markdown.sh              # 一键渲染脚本
    └── convert_references.py          # 格式转换工具
```

---

## 总结

**[@citekey]格式的优势**:

1. ✅ **写作时简单**: `@citekey`而不是复杂格式
2. ✅ **可验证**: 100%防止引用错误
3. ✅ **可转换**: 自动生成任何引用格式
4. ✅ **可筛选**: 只使用需要的文献
5. ✅ **可追溯**: 每个citekey对应真实PMID
