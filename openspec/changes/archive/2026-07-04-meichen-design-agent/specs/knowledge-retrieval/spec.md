## 新增需求

### 需求：语义案例检索
系统须基于主题、风格、空间类型和预算档次，从 Milvus 向量数据库中检索历史相似设计案例。

#### 场景：主题案例搜索
- **当** 需求分析 Agent 输出 theme="夏日海洋"、space_type="中庭"、budget_level="medium"
- **则** 系统构建结合主题关键词和结构化过滤条件的混合查询
- **且** 在 Milvus 中执行带元数据过滤（space_type、budget_level）的向量相似度搜索
- **且** 返回 top-5 案例，含：case_name、mall_name、design_highlights、material_summary、similarity_score

#### 场景：未找到相似案例
- **当** 向量搜索返回结果少于 3 条
- **则** 系统逐步放宽过滤条件：先移除 budget_level，再移除 space_type
- **且** 在输出中附加警告："该组合历史案例有限，结果仅基于主题相似度"

### 需求：材料与价格查询
系统须查询结构化 SQLite 数据库，获取材料规格、典型价格及替代建议。

#### 场景：材料价格查询
- **当** 可落地设计 Agent 请求查询"亚克力吊饰"和"LED灯带"等材料价格
- **则** 系统对 material_price 表按 material_name 模糊匹配查询
- **且** 返回：unit_price_range、common_specifications、supplier_region、last_updated_date
- **且** 无精确匹配时，返回编辑距离 < 3 的相似材料

#### 场景：预算受限时的材料替代建议
- **当** budget_level 为"低"且设计师请求材料替代方案
- **则** 系统查询同一功能分类下价格更低的材料
- **且** 返回替代方案及价格对比和取舍说明

### 需求：生成检索摘要
系统须将检索到的案例和材料数据合成为简洁的知识摘要，供下游 Agent 使用。

#### 场景：摘要生成
- **当** 案例检索和材料查询均已完成
- **则** 系统生成 Markdown 格式摘要，包含：similar_case_highlights、recommended_materials、typical_price_range_for_budget、design_pattern_suggestions
- **且** 摘要长度限制在 800 中文字符以内，以适配下游 LLM 上下文窗口
