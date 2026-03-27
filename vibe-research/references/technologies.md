# Technologies Powering Vibe-Research

How transformers, embeddings, and knowledge graphs enable AI-driven research.

## Core Technologies

### Large Language Models (LLMs)

```
训练数据: 教科书、论文、网站
能力: 理解概念、生成文本、回答问题
局限: 可能不知道最新研究、可能产生错误信息
```

**在 vibe-research 中的作用**:
- 理解科学文本
- 生成假设和研究思路
- 撰写论文草稿

---

### Vector Embeddings

```
原理: 将文本转换为高维向量
特性: 相似内容 → 相近向量
用途: 语义搜索（即使没有共同关键词也能找到相关内容）
```

**在 vibe-research 中的作用**:
- 检索相关论文（语义匹配）
- 跨领域发现隐藏联系
- 构建可搜索的知识库

---

### Retrieval-Augmented Generation (RAG)

```
流程:
1. 问题 → 向量
2. 向量 → 检索相关文档
3. 文档 + 问题 → LLM 生成答案
4. 答案 + 引用来源
```

**关键好处**: 减少 AI 幻觉，所有声明都有来源

---

### Knowledge Graphs

```
结构:
  节点 = 实体/概念
  边 = 关系

示例:
  Gene A --[inhibits]--> Protein B
  Method X --[outperforms]--> Method Y
```

**在 vibe-research 中的作用**:

| 功能 | 说明 |
|------|------|
| **映射领域** | 可视化整个知识结构 |
| **发现缺口** | 稀疏节点 = 研究不足 |
| **链接预测** | A→B, B→C → 发现 A→C |
| **跨域连接** | 不同领域间的意外联系 |

---

## Link Prediction Example

```
Paper 1: "Gene X affects pathway Y"
Paper 2: "Pathway Y influences disease Z"

知识图谱自动发现:
  Gene X --> Pathway Y --> Disease Z

潜在新假设: "Gene X may influence disease Z"
```

> 这正是 vibe-research 能发现人类可能忽略的联系的原因。

---

## Multimodal Capabilities

当前 vibe-research 主要是文本基础，但正在发展：

| 数据类型 | AI 能力 |
|----------|---------|
| **图像** | 分析论文中的图表、实验图像 |
| **数值** | 直接处理原始数据表格 |
| **代码** | 理解和生成分析代码 |

**未来方向**: AI 不仅能读论文，还能直接分析图表数据

---

## Practical Tools

| 工具类型 | 示例 | 用途 |
|----------|------|------|
| **文献助手** | Elicit, Perplexity, Semantic Scholar | 快速检索和总结论文 |
| **代码生成** | GitHub Copilot, ChatGPT | 编写分析代码 |
| **知识图谱** | Neo4j, custom LLM extraction | 构建领域知识网络 |
| **自动实验** | The AI Scientist, Agent Laboratory | 完整研究流程自动化 |

---

## Key Insight

> 模型提供语言和推理能力，嵌入提供记忆和检索，知识图谱提供结构和发现。

三者结合 = AI 可以扮演"勤奋的博士生"（读所有东西、精确回忆）+ "创造性思考者"（发现意外联系）。
