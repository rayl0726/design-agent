# 二期优化：L1 创意生成质量提升 - 技术设计

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户输入层                                   │
│   照片/CAD/PDF/PPT/参考图/文本需求                               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  需求解析层（RequirementParser）                   │
│   多维度特征提取 → 标准化需求结构                                 │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  知识检索层（KnowledgeRetrieval）                 │
│   ┌──────────────┬──────────────┬──────────────┐               │
│   │ 语义检索     │ 关键词匹配   │ 标签过滤     │               │
│   │ Milvus      │ 材料库      │ 风格/主题库  │               │
│   └──────────────┴──────────────┴──────────────┘               │
│   信息融合 → 构建上下文                                          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                  创意生成层（ConceptDesigner）                    │
│   标准化模板 + LLM → 高质量创意方案                              │
│   质量评估 → 优化迭代                                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     输出层                                       │
│   纯文本创意方案（Markdown格式）                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心模块职责

| 模块 | 职责 | 关键技术 |
|------|------|----------|
| **需求解析层** | 从多来源输入中提取标准化需求特征 | LLM + VLM + 规则解析 |
| **知识检索层** | 多维度检索知识库，构建创意上下文 | Milvus + MySQL |
| **创意生成层** | 基于模板和上下文生成高质量创意方案 | LLM + 标准化 Prompt |
| **质量评估层** | 评估创意方案质量，支持迭代优化 | LLM 自评估 + 用户反馈 |

## 2. 数据库设计

### 2.1 DesignCase 表结构

```sql
CREATE TABLE design_cases (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    project_type VARCHAR(100),
    space_type VARCHAR(100),
    space_size VARCHAR(200),
    budget_level VARCHAR(20),
    source_url VARCHAR(1000),
    
    brand VARCHAR(200),
    marketing_objective VARCHAR(500),
    target_audience TEXT,
    brand_tone VARCHAR(200),
    
    concept_statement VARCHAR(500),
    design_theme VARCHAR(200),
    design_style VARCHAR(200),
    creative_story TEXT,
    atmosphere_description TEXT,
    emotional_value TEXT,
    
    color_palette TEXT,
    materials TEXT,
    forms VARCHAR(500),
    lighting TEXT,
    interactive_elements TEXT,
    
    installation_period VARCHAR(100),
    display_period VARCHAR(100),
    technical_features TEXT,
    challenges_overcome TEXT,
    
    foot_traffic_increase VARCHAR(50),
    sales_increase VARCHAR(50),
    social_media_coverage VARCHAR(500),
    client_feedback TEXT,
    
    keywords TEXT,
    tags TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_design_cases_project_type ON design_cases(project_type);
CREATE INDEX idx_design_cases_space_type ON design_cases(space_type);
CREATE INDEX idx_design_cases_budget_level ON design_cases(budget_level);
CREATE INDEX idx_design_cases_design_style ON design_cases(design_style);
CREATE INDEX idx_design_cases_design_theme ON design_cases(design_theme);
```

### 2.2 向量检索集合

```python
# Milvus Collection: case_descriptions_v2
schema = {
    "fields": [
        {"name": "id", "type": "VARCHAR", "max_length": 36, "is_primary": True},
        {"name": "embedding", "type": "FLOAT_VECTOR", "dim": 1024},
        {"name": "title", "type": "VARCHAR", "max_length": 500},
        {"name": "project_type", "type": "VARCHAR", "max_length": 100},
        {"name": "space_type", "type": "VARCHAR", "max_length": 100},
        {"name": "budget_level", "type": "VARCHAR", "max_length": 20},
        {"name": "design_theme", "type": "VARCHAR", "max_length": 200},
        {"name": "design_style", "type": "VARCHAR", "max_length": 200},
        {"name": "brand_tone", "type": "VARCHAR", "max_length": 200},
        {"name": "concept_statement", "type": "VARCHAR", "max_length": 500},
        {"name": "keywords", "type": "VARCHAR", "max_length": 2000},
    ],
    "description": "设计案例语义检索 V2 - 支持多维度过滤"
}

index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "COSINE",
    "params": {"nlist": 256}
}
```

## 3. 核心模块实现

### 3.1 需求解析层

#### 3.1.1 多维度特征提取

```python
class RequirementAnalyzer:
    def analyze(self, input_data: dict) -> DesignRequirement:
        """
        从多来源输入中提取标准化需求特征
        
        Args:
            input_data: 包含照片/CAD/PDF/PPT/参考图/文本需求的输入
            
        Returns:
            DesignRequirement: 标准化需求结构
        """
        # 1. 基础信息提取
        basic_info = self._extract_basic_info(input_data)
        
        # 2. 商业目标分析
        business_info = self._analyze_business_objectives(input_data)
        
        # 3. 设计约束梳理
        constraints = self._identify_constraints(input_data)
        
        # 4. 文化语境分析
        cultural_context = self._analyze_cultural_context(input_data)
        
        # 5. 目标人群画像
        audience_profile = self._build_audience_profile(input_data)
        
        return DesignRequirement(
            basic_info=basic_info,
            business_info=business_info,
            constraints=constraints,
            cultural_context=cultural_context,
            audience_profile=audience_profile
        )
```

#### 3.1.2 DesignRequirement 数据结构

```python
@dataclass
class BasicInfo:
    project_name: str
    project_type: str
    space_type: str
    space_size: str
    budget_level: str

@dataclass
class BusinessInfo:
    marketing_objective: str
    target_audience: str
    brand_tone: str

@dataclass 
class Constraints:
    time_period: str
    technical_limits: list[str]
    material_limits: list[str]
    style_preferences: list[str]

@dataclass
class CulturalContext:
    festival_theme: str
    regional_culture: str
    season_feature: str

@dataclass
class AudienceProfile:
    demographics: str
    behavior_patterns: str
    emotional_needs: str

@dataclass
class DesignRequirement:
    basic_info: BasicInfo
    business_info: BusinessInfo
    constraints: Constraints
    cultural_context: CulturalContext
    audience_profile: AudienceProfile
```

### 3.2 知识检索层

#### 3.2.1 多维度检索策略

```python
class KnowledgeRetrieval:
    def retrieve(self, requirement: DesignRequirement, top_k: int = 5) -> list[DesignCase]:
        """
        多维度检索知识库
        
        检索策略：
        1. 语义检索：基于完整需求描述进行向量检索
        2. 标签过滤：按项目类型、空间类型、预算等级、风格等进行过滤
        3. 关键词匹配：提取需求中的关键词进行精确匹配
        """
        # 1. 构建查询向量
        query_text = self._build_query_text(requirement)
        query_embedding = embedding_client.embed(query_text)
        
        # 2. 构建过滤条件
        expr = self._build_filter_expression(requirement)
        
        # 3. Milvus 检索
        results = self.milvus_client.search(
            collection_name="case_descriptions_v2",
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 32}},
            limit=top_k,
            expr=expr or None,
            output_fields=[
                "title", "project_type", "space_type", "budget_level",
                "design_theme", "design_style", "brand_tone",
                "concept_statement", "creative_story", "atmosphere_description",
                "color_palette", "materials", "lighting", "keywords"
            ]
        )
        
        # 4. 信息融合
        return self._fuse_results(results)
```

### 3.3 创意生成层

#### 3.3.1 多创意生成策略

一次性生成10个差异化创意，每个创意从不同维度切入：

```python
class ConceptDesigner:
    DIFFERENTIATION_DIMENSIONS = [
        {"id": 1, "name": "brand_strengthen", "label": "品牌调性强化", "strategy": "深度结合品牌DNA，突出品牌识别度"},
        {"id": 2, "name": "emotional_resonance", "label": "情感共鸣", "strategy": "以情感故事为主线，引发目标人群共鸣"},
        {"id": 3, "name": "interactive_experience", "label": "互动体验", "strategy": "强调互动性和参与感，打造沉浸式体验"},
        {"id": 4, "name": "visual_impact", "label": "视觉冲击", "strategy": "追求视觉震撼效果，打造网红打卡点"},
        {"id": 5, "name": "cultural_integration", "label": "文化融合", "strategy": "将地域文化/节日元素与现代设计结合"},
        {"id": 6, "name": "sustainability", "label": "可持续性", "strategy": "环保材料+循环利用，突出社会责任"},
        {"id": 7, "name": "technology_sense", "label": "科技感", "strategy": "融入数字技术（LED/AR/投影），展现未来感"},
        {"id": 8, "name": "minimalist_aesthetics", "label": "简约美学", "strategy": "极简主义设计，强调空间留白和材质质感"},
        {"id": 9, "name": "scenario_narrative", "label": "场景叙事", "strategy": "构建完整的场景故事，引导用户体验动线"},
        {"id": 10, "name": "cross_boundary", "label": "跨界融合", "strategy": "打破传统边界，融合艺术/时尚/科技等多元元素"}
    ]
    
    def generate_batch(self, requirement: DesignRequirement, context: list[DesignCase], count: int = 10) -> list[CreativeConcept]:
        """
        一次性生成多个差异化创意方案
        
        Args:
            requirement: 标准化需求
            context: 检索到的案例上下文
            count: 生成创意数量（默认10）
            
        Returns:
            list[CreativeConcept]: 创意方案列表
        """
        concepts = []
        for i, dimension in enumerate(self.DIFFERENTIATION_DIMENSIONS[:count]):
            concept = self.generate_with_dimension(requirement, context, dimension)
            concepts.append(concept)
        return concepts
    
    def generate_with_dimension(self, requirement: DesignRequirement, context: list[DesignCase], dimension: dict) -> CreativeConcept:
        """
        基于指定差异化维度生成创意方案
        
        Args:
            requirement: 标准化需求
            context: 检索到的案例上下文
            dimension: 差异化维度配置
            
        Returns:
            CreativeConcept: 完整创意方案
        """
        # 1. 构建差异化 Prompt
        prompt = self._build_differentiated_prompt(requirement, context, dimension)
        
        # 2. 调用 LLM
        response = llm_client.complete(self.SYSTEM_PROMPT, prompt, json_mode=True)
        
        # 3. 解析结果并添加维度信息
        concept = self._parse_response(response)
        concept.differentiation_dimension = dimension["label"]
        concept.differentiation_strategy = dimension["strategy"]
        concept.serial_number = dimension["id"]
        
        return concept
    
    def _build_differentiated_prompt(self, requirement: DesignRequirement, context: list[DesignCase], dimension: dict) -> str:
        """构建差异化创意生成 Prompt"""
        return f"""
        请基于以下需求，生成一个「{dimension['label']}」方向的创意方案。
        
        设计策略：{dimension['strategy']}
        
        项目需求：
        {json.dumps(requirement.dict(), ensure_ascii=False, indent=2)}
        
        参考案例：
        {json.dumps([case.dict() for case in context], ensure_ascii=False, indent=2)}
        
        请确保该创意与其他维度的创意有明显差异，突出{dimension['label']}的特点。
        """
    
    SYSTEM_PROMPT = """
    你是一位拥有20年经验的资深美陈设计总监，擅长从商业角度出发，创造具有情感共鸣的空间体验。
    
    你的设计原则：
    1. 以商业目标为导向，确保设计能实现预期的营销效果
    2. 注重情感价值传递，创造令人难忘的空间体验
    3. 兼顾美学与实用性，确保方案可落地执行
    4. 保持创新思维，突破常规设计边界
    5. 每个创意必须有独特的切入点，避免重复
    
    请按照以下模板输出创意方案：
    {
        "project_brief": {
            "requirement_analysis": "...",
            "target_audience_profile": "..."
        },
        "creative_concept": {
            "core_concept": "...",
            "creative_storyline": "...",
            "atmosphere_creation": "..."
        },
        "design_elements": {
            "color_scheme": "...",
            "material_selection": "...",
            "form_design": "...",
            "lighting_design": "..."
        },
        "space_planning": {
            "layout_plan": "...",
            "circulation_design": "..."
        },
        "emotional_value": {
            "emotional_touchpoints": "...",
            "brand_value_delivery": "..."
        },
        "execution_suggestions": {
            "implementation_points": "...",
            "risk_management": "..."
        }
    }
    """
```

#### 3.3.2 CreativeConcept 数据结构

```python
@dataclass
class ProjectBrief:
    requirement_analysis: str
    target_audience_profile: str

@dataclass
class CreativeConceptCore:
    core_concept: str
    creative_storyline: str
    atmosphere_creation: str

@dataclass
class DesignElements:
    color_scheme: str
    material_selection: str
    form_design: str
    lighting_design: str

@dataclass
class SpacePlanning:
    layout_plan: str
    circulation_design: str

@dataclass
class EmotionalValue:
    emotional_touchpoints: str
    brand_value_delivery: str

@dataclass
class ExecutionSuggestions:
    implementation_points: str
    risk_management: str

@dataclass
class CreativeConcept:
    id: str
    serial_number: int
    differentiation_dimension: str
    differentiation_strategy: str
    project_brief: ProjectBrief
    creative_concept: CreativeConceptCore
    design_elements: DesignElements
    space_planning: SpacePlanning
    emotional_value: EmotionalValue
    execution_suggestions: ExecutionSuggestions
    quality_score: float = 0.0
    recommended_budget: str = ""
    
    def to_card(self) -> CreativeConceptCard:
        """转换为卡片展示数据"""
        return CreativeConceptCard(
            id=self.id,
            serial_number=self.serial_number,
            differentiation_label=self.differentiation_dimension,
            title=self._extract_title(),
            core_concept=self.creative_concept.core_concept,
            color_palette=self._extract_color_palette(),
            style_tags=self._extract_style_tags(),
            recommended_budget=self.recommended_budget,
            quality_score=self.quality_score
        )
    
    def _extract_title(self) -> str:
        """从核心概念中提取创意标题"""
        return self.creative_concept.core_concept[:20] + "..." if len(self.creative_concept.core_concept) > 20 else self.creative_concept.core_concept
    
    def _extract_color_palette(self) -> list[str]:
        """从配色方案中提取主色调"""
        return ["#FF6B6B", "#4ECDC4", "#45B7D1"]
    
    def _extract_style_tags(self) -> list[str]:
        """提取风格标签"""
        return ["现代", "简约", "时尚"]
```

#### 3.3.3 创意卡片数据结构

```python
@dataclass
class CreativeConceptCard:
    id: str
    serial_number: int
    differentiation_label: str
    title: str
    core_concept: str
    color_palette: list[str]
    style_tags: list[str]
    recommended_budget: str
    quality_score: float
```

#### 3.3.4 批量生成优化

为提高性能，支持并发生成：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class BatchConceptGenerator:
    def __init__(self, designer: ConceptDesigner, max_workers: int = 5):
        self.designer = designer
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def generate_concurrent(self, requirement: DesignRequirement, context: list[DesignCase], count: int = 10) -> list[CreativeConcept]:
        """
        并发生成多个创意方案，提升生成效率
        
        Args:
            requirement: 标准化需求
            context: 检索到的案例上下文
            count: 生成创意数量
            
        Returns:
            list[CreativeConcept]: 创意方案列表
        """
        loop = asyncio.get_event_loop()
        tasks = []
        
        for i, dimension in enumerate(self.designer.DIFFERENTIATION_DIMENSIONS[:count]):
            # 每个创意使用不同的上下文切片，增加多样性
            context_slice = context[i % len(context):(i % len(context)) + min(3, len(context))]
            task = loop.run_in_executor(
                self.executor,
                self.designer.generate_with_dimension,
                requirement,
                context_slice,
                dimension
            )
            tasks.append(task)
        
        # 并发执行
        results = await asyncio.gather(*tasks)
        
        # 按序号排序
        return sorted(results, key=lambda c: c.serial_number)
```

### 3.4 质量评估层

```python
class QualityEvaluator:
    def evaluate(self, concept: CreativeConcept, requirement: DesignRequirement) -> QualityReport:
        """
        评估创意方案质量
        
        评估维度：
        1. 需求匹配度：方案是否满足用户需求
        2. 创意创新性：方案是否具有创新性
        3. 商业价值：方案是否能实现商业目标
        4. 可落地性：方案是否具备实施条件
        5. 情感价值：方案是否能传递情感价值
        """
        # 使用 LLM 进行自评估
        evaluation_prompt = self._build_evaluation_prompt(concept, requirement)
        response = llm_client.complete(self.EVALUATOR_PROMPT, evaluation_prompt, json_mode=True)
        
        return self._parse_evaluation(response)
```

## 4. API 接口设计

### 4.1 需求分析接口

```
POST /api/v1/requirements/analyze
Content-Type: multipart/form-data

请求参数：
- files: 文件数组（照片/CAD/PDF/PPT/参考图）
- text_requirement: 文本需求 JSON

响应：
{
    "id": "uuid",
    "basic_info": {...},
    "business_info": {...},
    "constraints": {...},
    "cultural_context": {...},
    "audience_profile": {...}
}
```

### 4.2 批量创意生成接口

```
POST /api/v1/concepts/generate-batch
Content-Type: application/json

请求参数：
{
    "requirement_id": "uuid",
    "count": 10,
    "top_k": 5
}

响应：
{
    "id": "uuid",
    "requirement_id": "uuid",
    "concepts": [
        {
            "id": "uuid",
            "serial_number": 1,
            "differentiation_dimension": "品牌调性强化",
            "project_brief": {...},
            "creative_concept": {...},
            "design_elements": {...},
            "space_planning": {...},
            "emotional_value": {...},
            "execution_suggestions": {...},
            "quality_score": 0.85,
            "recommended_budget": "15-20万"
        }
    ],
    "generated_at": "2026-07-04T10:30:00Z",
    "total_count": 10
}
```

### 4.3 创意卡片列表接口

```
GET /api/v1/concepts/{batch_id}/cards
Content-Type: application/json

响应：
{
    "batch_id": "uuid",
    "cards": [
        {
            "id": "uuid",
            "serial_number": 1,
            "differentiation_label": "品牌调性强化",
            "title": "时光之旅",
            "core_concept": "以品牌历史为脉络，打造沉浸式时光隧道体验",
            "color_palette": ["#FF6B6B", "#4ECDC4", "#45B7D1"],
            "style_tags": ["现代", "简约", "时尚"],
            "recommended_budget": "15-20万",
            "quality_score": 0.85
        }
    ]
}
```

### 4.4 创意详情接口

```
GET /api/v1/concepts/{id}
Content-Type: application/json

响应：
{
    "id": "uuid",
    "serial_number": 1,
    "differentiation_dimension": "品牌调性强化",
    "differentiation_strategy": "深度结合品牌DNA，突出品牌识别度",
    "project_brief": {...},
    "creative_concept": {...},
    "design_elements": {...},
    "space_planning": {...},
    "emotional_value": {...},
    "execution_suggestions": {...},
    "quality_score": 0.85,
    "recommended_budget": "15-20万"
}
```

### 4.5 创意优化接口

```
POST /api/v1/concepts/{id}/optimize
Content-Type: application/json

请求参数：
{
    "feedback": "用户反馈",
    "aspects_to_improve": ["创意创新性", "商业价值"]
}

响应：
{
    "id": "uuid",
    "optimized_concept": {...},
    "improvements": [...]
}
```

### 4.6 选择创意接口

```
POST /api/v1/concepts/{id}/select
Content-Type: application/json

请求参数：
{
    "workflow_id": "uuid"
}

响应：
{
    "id": "uuid",
    "selected_concept_id": "uuid",
    "status": "selected",
    "message": "创意已选择，即将进入 L2 视觉设计阶段"
}
```

## 5. 数据迁移方案

### 5.1 现有数据迁移

```python
def migrate_cases_v1_to_v2():
    """将 V1 案例数据迁移到 V2 结构"""
    # 1. 查询 V1 数据
    v1_cases = db.query(DesignCaseV1).all()
    
    # 2. 使用 LLM 扩展字段
    for case in v1_cases:
        prompt = f"""
        请将以下设计案例扩展为完整的结构化数据：
        
        标题：{case.title}
        主题：{case.theme}
        风格：{case.style}
        空间类型：{case.space_type}
        预算等级：{case.budget_level}
        摘要：{case.summary}
        
        请补充以下字段：
        - brand: 品牌名称
        - marketing_objective: 营销目标
        - target_audience: 目标人群描述
        - brand_tone: 品牌调性
        - concept_statement: 核心创意概念（一句话）
        - creative_story: 创意故事线（500字）
        - atmosphere_description: 氛围描述
        - color_palette: 配色方案
        - materials: 材料清单
        - lighting: 灯光设计
        - emotional_value: 情感价值传递
        
        输出 JSON 格式。
        """
        response = llm_client.complete("你是一位美陈设计专家，擅长分析和扩展设计案例信息", prompt, json_mode=True)
        extended_data = json.loads(response)
        
        # 3. 创建 V2 案例
        v2_case = DesignCaseV2(**extended_data)
        db.add(v2_case)
    
    db.commit()
```

## 6. 部署与集成

### 6.1 Python AI 服务集成

在 `agent-core/app/api/routers.py` 中添加新的 API 端点：

```python
from app.agents.requirement_analyst import RequirementAnalyzer
from app.agents.concept_designer import ConceptDesigner
from app.services.knowledge_base import KnowledgeBase

requirement_analyzer = RequirementAnalyzer()
concept_designer = ConceptDesigner()
knowledge_base = KnowledgeBase()

@app.post("/api/v1/requirements/analyze")
async def analyze_requirement(files: list[UploadFile] = None, text_requirement: str = None):
    input_data = await parse_input(files, text_requirement)
    requirement = requirement_analyzer.analyze(input_data)
    return requirement.dict()

@app.post("/api/v1/concepts/generate")
async def generate_concept(request: GenerateConceptRequest):
    requirement = get_requirement(request.requirement_id)
    context = knowledge_base.retrieve(requirement, request.top_k)
    concept = concept_designer.generate(requirement, context)
    return concept.dict()
```

### 6.2 Java 协调层集成

在 `agent-api/src/main/java/com/meichen/orchestrator/workflow/WorkflowDefinition.java` 中更新节点定义：

```java
new WorkflowNode("requirement_analyze_v2", "/api/v1/requirements/analyze", List.of(), true),
new WorkflowNode("concept_design_v2", "/api/v1/concepts/generate", List.of("requirement_analyze_v2"), true),
```

## 7. 测试方案

### 7.1 单元测试

```python
# test_requirement_analyzer.py
def test_multi_dimension_extraction():
    """测试多维度特征提取"""
    input_data = {
        "text_requirement": "为XX商场中庭设计一个春节主题美陈，预算20万"
    }
    analyzer = RequirementAnalyzer()
    requirement = analyzer.analyze(input_data)
    
    assert requirement.basic_info.project_type == "商场美陈"
    assert requirement.basic_info.space_type == "中庭"
    assert requirement.cultural_context.festival_theme == "春节"

# test_knowledge_retrieval.py
def test_multi_dimension_retrieval():
    """测试多维度检索"""
    requirement = DesignRequirement(...)
    retrieval = KnowledgeRetrieval()
    results = retrieval.retrieve(requirement, top_k=5)
    
    assert len(results) == 5
    assert all(r.design_style == requirement.constraints.style_preferences[0] for r in results)

# test_concept_designer.py
def test_template_generation():
    """测试标准化模板生成"""
    requirement = DesignRequirement(...)
    context = [DesignCase(...)]
    designer = ConceptDesigner()
    concept = designer.generate(requirement, context)
    
    assert concept.project_brief.requirement_analysis
    assert concept.creative_concept.core_concept
    assert concept.design_elements.color_scheme
```

### 7.2 集成测试

```python
def test_end_to_end():
    """端到端测试：从需求输入到创意生成"""
    # 1. 模拟用户输入
    input_data = {
        "text_requirement": "为XX购物中心入口设计一个夏日清凉主题美陈，吸引年轻客群，预算15万"
    }
    
    # 2. 需求分析
    analyzer = RequirementAnalyzer()
    requirement = analyzer.analyze(input_data)
    
    # 3. 知识检索
    retrieval = KnowledgeRetrieval()
    context = retrieval.retrieve(requirement)
    
    # 4. 创意生成
    designer = ConceptDesigner()
    concept = designer.generate(requirement, context)
    
    # 5. 质量评估
    evaluator = QualityEvaluator()
    report = evaluator.evaluate(concept, requirement)
    
    assert report.overall_score >= 0.7
```
