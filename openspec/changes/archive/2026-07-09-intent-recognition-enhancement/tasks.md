## 1. Domain Taxonomy & Vocabulary

- [ ] 1.1 创建领域词库文件 `agent-core/data/intent_taxonomy.yaml`，覆盖空间类型、点位、预算级别、风格、材质、时间维度。
- [ ] 1.2 整理核心商业空间类型（购物中心中庭、快闪店、百货入口、展厅、步行街等 50+）及标准别名/同义词。
- [ ] 1.3 整理常用点位名称（中庭、门头、DP点、合影墙、打卡点等 30+）及同义词映射。
- [ ] 1.4 实现词库加载器 `TaxonomyLoader`，支持启动时加载、基础校验和热刷新。
- [ ] 1.5 将 `jieba` 自定义词典指向 `intent_taxonomy.yaml`，保证分词能切出领域词。

## 2. Intent Recognition Service

- [ ] 2.1 新建 `agent-core/app/services/intent_recognition.py` 与 `IntentRecognitionService` 类。
- [ ] 2.2 实现 Layer 1 精确匹配：基于分词结果在词库中直接命中标准词。
- [ ] 2.3 实现 Layer 2 别名/同义词匹配：维护别名表并在命中时返回标准词。
- [ ] 2.4 实现 Layer 3 编辑距离模糊匹配：集成 `rapidfuzz`，默认阈值 0.75，关键字段阈值 0.85。
- [ ] 2.5 实现 Layer 4 语义向量匹配：预计算 taxonomy embedding，对语义相近表达进行匹配，source 标记为 `semantic`。
- [ ] 2.6 实现 Layer 5 LLM 兜底补充：只把本地未命中或低置信度字段交给 LLM，prompt 注入已识别字段和标准词候选列表。
- [ ] 2.7 为每个识别字段输出 `source`（exact/alias/fuzzy/semantic/llm/default/unknown）、`confidence`（0-1）和 `candidates`。
- [ ] 2.8 添加 `IntentRecognitionResult` 数据类，统一输出结构。

## 3. Context Completion & Clarification

- [ ] 3.1 在对话状态中维护 `last_intent`，支持从历史消息继承已识别字段。
- [ ] 3.2 实现字段优先级策略表：必须追问字段、可静默继承字段、可领域默认补全字段。
- [ ] 3.3 实现缺失字段补全：基于领域规则提供默认值（如快闪店默认点位组合）。
- [ ] 3.4 实现低置信度字段检测，生成主动追问文本（空间类型、预算等关键字段）。
- [ ] 3.5 将追问消息接入现有消息下发机制，不改造前端 UI。

## 4. Cross-Modal Taxonomy Unification

- [ ] 4.1 将 `intent_taxonomy.yaml` 序列化为 JSON 格式，注入 `PhotoParser` 的 VLM prompt。
- [ ] 4.2 将 taxonomy 注入 `VideoParser` 和 `ReferenceParser` 的 prompt，统一输出标准词。
- [ ] 4.3 修改多模态解析输出格式，使其与 `IntentRecognitionResult` 兼容。
- [ ] 4.4 在 `InputMerger` 中合并跨模态结果时，优先采用高置信度来源。

## 5. Evaluation & CI

- [ ] 5.1 创建 `agent-core/tests/intent/golden_cases.jsonl`，覆盖 exact / alias / fuzzy / semantic / llm / context 六类场景，至少 50 条。
- [ ] 5.2 实现 `IntentRecognitionEvaluator`，计算 `space_type`、`budget`、`points` 的准确率、召回率和平均置信度。
- [ ] 5.3 将 evaluator 接入 CI，关键字段准确率低于 90% 时失败。
- [ ] 5.4 建立阈值/词库调整时必须重跑 golden test set 的流程。

## 6. Integration & Observability

- [ ] 6.1 将现有输入解析入口迁移到 `IntentRecognitionService`，保留旧 parser feature flag 回滚能力。
- [ ] 6.2 将识别元数据（source/confidence/candidates）写入 `thinking_logs`，便于排查识别错误。
- [ ] 6.3 在 `agent-core` 增加单元测试，覆盖精确/别名/模糊/语义/LLM 兜底和上下文补全场景。

## 7. Online Vocabulary Expansion

- [ ] 7.1 设计 `intent_feedback_log` 表/文件，记录 source=`unknown` 且经用户确认的字段。
- [ ] 7.2 实现后台脚本或管理接口，将高频 unknown 输入合并回 `intent_taxonomy.yaml`。
- [ ] 7.3 增加 review 流程，避免自动合并引入错误词汇。

## 8. Validation & Rollout

- [ ] 8.1 使用 golden test set 验证识别准确率，调整词库和阈值。
- [ ] 8.2 更新 `requirements.txt`（新增 `jieba`、`rapidfuzz`、语义向量依赖）。
- [ ] 8.3 重启 agent-core 并跑通完整对话流程，确认追问、补全和跨模态一致性行为符合预期。
