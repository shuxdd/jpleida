"""
Prompt模板
==========

定义LLM调用的Prompt模板。
"""

# 信息抽取Prompt
EXTRACTION_PROMPT = """
你是一个专业的竞品信息提取专家。请从以下文本中提取结构化的竞品信息。

文本内容：
{content}

请严格按照以下JSON格式返回，找不到的字段填null或空数组：

```json
{{
    "company_name": "公司全称",
    "founded": "成立时间（如：2020年）",
    "headquarters": "总部地点",
    "team_size": "团队规模（如：100-500人）",
    "funding": "融资情况",
    "products": [
        {{
            "name": "产品名称",
            "description": "一句话产品描述",
            "features": ["核心功能1", "核心功能2"],
            "pricing": {{
                "model": "定价模式（免费/订阅/按量/混合）",
                "tiers": [
                    {{"name": "套餐名", "price": "价格", "features": ["包含功能"]}}
                ]
            }}
        }}
    ],
    "target_market": "目标用户群体",
    "competitors": ["已知竞争对手列表"],
    "key_differentiators": ["核心差异化1", "核心差异化2"],
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["不足1", "不足2"]
}}
```

要求：
1. 只返回JSON，不要其他内容
2. 从文本中提取，不要编造信息
3. features 和 key_differentiators 至少提取3条（有就提取，没有就少写）
4. pricing 信息如果文本中没有，tiers 填空数组
"""

# SWOT分析Prompt
SWOT_PROMPT = """
你是一个资深竞品分析师。基于以下竞品信息，生成SWOT分析。

竞品信息：
{competitor_info}

请严格按照以下JSON格式返回：

```json
{{
    "strengths": [
        "优势1：具体说明，为什么这是优势",
        "优势2：具体说明，为什么这是优势",
        "优势3：具体说明"
    ],
    "weaknesses": [
        "劣势1：具体说明，为什么这是劣势",
        "劣势2：具体说明",
        "劣势3：具体说明"
    ],
    "opportunities": [
        "机会1：市场趋势或未满足的需求",
        "机会2：技术发展带来的机会",
        "机会3：竞争格局变化的机会"
    ],
    "threats": [
        "威胁1：竞争压力或市场变化",
        "威胁2：技术替代风险",
        "威胁3：政策或监管风险"
    ],
    "summary": "一段话总结该竞品的竞争态势（50字以内）"
}}
```

要求：
1. 只返回JSON，不要其他内容
2. 每个维度至少3条，每条要有具体说明
3. 基于提供的信息分析，不要凭空编造
4. summary 要精炼，点出核心竞争态势
"""

# 报告生成Prompt
REPORT_PROMPT = """
你是一个专业的竞品分析师。请基于以下分析数据，生成一份结构化的竞品分析报告。

分析数据：
{analysis_data}

注意：competitor_notes 是用户填写的竞品补充信息，值得重点关注，应融入报告中。

请生成以下章节（仅生成有数据的章节，数据为空则跳过）：

## 报告结构

### 1. 执行摘要
- 一段话概括分析目的、竞品范围、核心发现（100字以内）

### 2. 竞品概览
- 用表格列出各竞品的基本信息（名称、成立时间、定位、核心产品）

{sections}

## 竞争格局
- 市场定位分析
- 各竞品优劣势总结

## 战略建议
- 基于分析结果的3-5条可执行建议
- 每条建议说明原因和预期效果

要求：
1. Markdown格式，使用表格、列表增强可读性
2. 数据必须来自分析数据，不要编造
3. 总长度1500-2500字
4. 语言简洁专业，避免废话
"""

# 任务规划Prompt
PLANNING_PROMPT = """
你是一个竞品分析任务规划专家。请为以下分析任务制定数据采集计划。

任务信息：
- 竞品列表：{competitors}
- 分析类型：{analysis_type}
- 分析维度：{dimensions}

请严格按照以下JSON格式返回采集计划：

```json
{{
    "competitors": [
        {{
            "name": "竞品名称",
            "search_keywords": ["关键词1", "关键词2", "关键词3"],
            "target_urls": ["https://官网URL"],
            "info_types": ["company_info", "products", "pricing", "features"]
        }}
    ],
    "analysis_dimensions": ["features", "pricing", "swot"]
}}
```

要求：
1. 只返回JSON，不要其他内容
2. search_keywords 每个竞品3-5个，覆盖：官网、产品、定价、功能、用户评价
3. target_urls 填写已知的官网地址，不知道就留空数组
4. info_types 根据分析维度选择：company_info、products、pricing、features、reviews
"""

# 对比分析报告Prompt（当提供了 my_product 时使用）
COMPARISON_REPORT_PROMPT = """
你是一个专业的竞品分析师。请基于以下分析数据，生成一份**我方产品 vs 竞品**的对比分析报告。

分析数据：
{analysis_data}

注意：competitor_notes 是用户填写的竞品补充信息，值得重点关注，应融入报告中。

我方产品是 `my_product`，其他全部是竞品。

请生成以下章节（仅生成有数据的章节，数据为空则跳过）：

### 1. 执行摘要
- 一句话概括对比分析目的、竞品范围、核心发现（100字以内）

### 2. 我方产品 vs 竞品概览
- 用表格列出我方产品和各竞品的基本信息（名称、定位、核心产品）

{sections}

### 3. 竞争格局
- 市场定位对比图（文字描述）
- 我方与各竞品的差异化总结

### 4. 战略建议
- 基于对比分析的 3-5 条可执行建议
- 每条说明：做什么、为什么做、预期效果

要求：
1. Markdown格式，使用表格、列表增强可读性
2. 数据必须来自分析数据，不要编造
3. 总长度 1500-2500 字
4. 语言简洁专业，重点突出我方优势和改进方向
"""

# 报告质量评估 Prompt（LLM-as-Judge）
EVALUATION_PROMPT = """
你是一个严格的竞品分析报告质量评估员。请评估以下报告的质量。

## 评估维度

### 1. 覆盖度 (coverage)
是否覆盖了所有竞品和分析维度？有没有遗漏重要信息？

### 2. 分析深度 (depth)
分析是否具体有依据，还是泛泛而谈？SWOT 分析是否针对每个竞品的特点？

### 3. 结构化 (structure)
报告结构是否清晰？Markdown 格式（表格、列表、标题层级）是否规范？

### 4. 可操作性 (actionability)
战略建议是否具体可执行？是否针对每个竞品提出了差异化策略？

## 评分标准（严格）
- **1分**：严重缺陷，基本不符合要求
- **2分**：有明显不足，需要大幅改进
- **3分**：及格，达到了基本要求但不够深入
- **4分**：良好，大部分维度表现不错
- **5分**：优秀，超出预期

## 任务信息
- 竞品: {competitors}
- 分析维度: {dimensions}

## 报告内容
{report_content}

请返回严格 JSON 格式：
```json
{{
    "coverage": {{"score": 3, "reasoning": "评分理由..."}},
    "depth": {{"score": 3, "reasoning": "评分理由..."}},
    "structure": {{"score": 3, "reasoning": "评分理由..."}},
    "actionability": {{"score": 3, "reasoning": "评分理由..."}},
    "overall_score": 3,
    "overall_summary": "总体评价（30字以内）",
    "key_improvements": ["改进点1", "改进点2", "改进点3"]
}}
```
"""

# 问答Prompt
QA_PROMPT = """
你是一个竞品分析助手。基于以下知识库信息，回答用户的问题。

知识库信息：
{context}

用户问题：
{question}

回答要求：
1. 优先使用知识库中的信息回答
2. 如果知识库中没有相关信息，明确告知用户
3. 引用数据来源（URL或文档名）
4. 语言简洁专业，直接回答问题
5. 如果是对比类问题，用表格展示更清晰
"""
