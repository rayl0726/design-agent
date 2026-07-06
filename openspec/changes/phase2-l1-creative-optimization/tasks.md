# 二期优化：L1 创意生成质量提升 - 任务列表

## 1. 需求解析层优化

- [ ] 1.1 重构 `RequirementAnalyzer`，实现多维度特征提取（基础信息、商业目标、设计约束、文化语境、目标人群）
- [ ] 1.2 定义 `DesignRequirement` 数据结构（BasicInfo、BusinessInfo、Constraints、CulturalContext、AudienceProfile）
- [ ] 1.3 实现基于 LLM 的需求分析 Prompt，支持从文本需求中提取结构化特征
- [ ] 1.4 集成 VLM 分析，从照片中提取空间特征和氛围信息
- [ ] 1.5 添加 API 端点 `POST /api/v1/requirements/analyze`
- [ ] 1.6 编写单元测试验证多维度特征提取的准确性

## 2. 知识库重构

- [ ] 2.1 创建新的 `DesignCaseV2` SQLAlchemy 模型，包含完整的字段结构
- [ ] 2.2 创建 Milvus `case_descriptions_v2` 集合，支持多维度过滤检索
- [ ] 2.3 实现数据迁移脚本，将 V1 数据扩展为 V2 结构（使用 LLM 补全缺失字段）
- [ ] 2.4 优化 `KnowledgeBase` 服务，实现多维度检索策略（语义检索 + 标签过滤 + 关键词匹配）
- [ ] 2.5 更新 `retrieve` 方法，支持按项目类型、空间类型、预算等级、风格等条件过滤
- [ ] 2.6 编写单元测试验证多维度检索的准确性

## 3. 创意生成层优化

- [ ] 3.1 重构 `ConceptDesigner`，实现多创意差异化生成策略（10个维度）
- [ ] 3.2 定义 `CreativeConcept` 数据结构（包含差异化维度、序号、质量评分等）
- [ ] 3.3 定义 `CreativeConceptCard` 数据结构，支持卡片展示
- [ ] 3.4 实现 `generate_batch` 方法，一次性生成10个差异化创意
- [ ] 3.5 实现 `generate_with_dimension` 方法，基于指定维度生成创意
- [ ] 3.6 实现 `to_card` 方法，将完整创意转换为卡片展示数据
- [ ] 3.7 设计资深设计师角色的 SYSTEM_PROMPT，包含设计原则和输出模板
- [ ] 3.8 实现 Prompt 构建逻辑，将需求和检索上下文有效串联
- [ ] 3.9 实现 `BatchConceptGenerator`，支持并发批量生成提升效率
- [ ] 3.10 添加 API 端点 `POST /api/v1/concepts/generate-batch`
- [ ] 3.11 添加 API 端点 `GET /api/v1/concepts/{batch_id}/cards`
- [ ] 3.12 添加 API 端点 `GET /api/v1/concepts/{id}`（创意详情）
- [ ] 3.13 添加 API 端点 `POST /api/v1/concepts/{id}/select`（选择创意）
- [ ] 3.14 添加 API 端点 `POST /api/v1/concepts/{id}/optimize` 支持创意优化
- [ ] 3.15 编写单元测试验证多创意生成和卡片转换的正确性

## 4. 质量评估层实现

- [ ] 4.1 实现 `QualityEvaluator` 类，支持多维度质量评估（需求匹配度、创意创新性、商业价值、可落地性、情感价值）
- [ ] 4.2 设计评估 Prompt，使用 LLM 进行自评估
- [ ] 4.3 实现评估报告数据结构 `QualityReport`
- [ ] 4.4 集成评估逻辑到创意生成流程中
- [ ] 4.5 编写单元测试验证评估逻辑的合理性

## 5. 协调层集成

- [ ] 5.1 更新 Java 协调层 `WorkflowDefinition`，添加 V2 节点定义
- [ ] 5.2 更新工作流状态机，支持新的节点类型
- [ ] 5.3 更新 `ProjectController`，添加新的 API 端点映射

## 6. 数据填充

- [ ] 6.1 收集 20 个高质量美陈设计案例（包含完整的创意故事、材料清单、灯光设计等）
- [ ] 6.2 使用数据迁移脚本将案例导入 V2 结构
- [ ] 6.3 验证导入数据的完整性和准确性

## 7. 集成与测试

- [ ] 7.1 编写端到端测试，验证从需求输入到创意生成的完整链路
- [ ] 7.2 测试多维度检索的召回准确率
- [ ] 7.3 测试创意优化功能，验证反馈循环效果
- [ ] 7.4 邀请设计师进行手动测试，收集创意质量反馈

## 8. 部署与上线

- [ ] 8.1 更新 Docker Compose 配置（如需要）
- [ ] 8.2 更新环境配置文件 `.env.example`
- [ ] 8.3 部署到测试环境进行验证
- [ ] 8.4 文档更新：更新 API 文档和使用说明
