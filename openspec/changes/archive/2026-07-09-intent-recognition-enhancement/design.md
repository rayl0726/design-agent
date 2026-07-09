## Context

当前的需求解析模块位于 `agent-core` 中，主要依赖简单的关键词匹配或 LLM 直接抽取。测试反馈显示：
- “中庭”能被识别，但“快闪店”“百货入口”“步行街”“展厅”等常见商业空间类型无法识别。
- 缺少别名和同义词扩展，例如“中庭吊饰”应映射到“中庭”点位。
- 多轮对话中没有利用上下文补全缺失字段，导致用户需要重复输入。
- 识别过程不可观测，无法判断某个字段是精确匹配、模糊匹配还是 LLM 兜底得到。
- `PhotoParser` / `VideoParser` / `ReferenceParser` 与文本解析没有共享同一份领域词库，跨模态输出不一致。

## Goals / Non-Goals

**Goals:**
- 建立商业美陈领域词库，覆盖空间类型、点位、预算、风格、材质、时间等维度。
- 实现分层识别策略：精确词库匹配 → 别名/同义词扩展 → 编辑距离模糊匹配 → 语义向量匹配 → LLM 兜底补充。
- LLM 兜底仅针对本地未命中或低置信度的字段，而不是重新抽取全部字段。
- 引入上下文补全：基于当前对话已识别字段、领域默认值和字段优先级策略表，自动补全缺失的关键信息。
- 输出识别结果时附带置信度、识别来源和候选词，便于调试和后续优化。
- 建立 golden test set 和自动化准确率评估，防止阈值/词库调整导致识别退化。
- 低置信度字段触发主动追问，而不是使用不可靠默认值。
- 跨模态解析（photo/video/reference）使用同一份 taxonomy，保证字段一致性。

**Non-Goals:**
- 不重新实现通用大模型，仅把 LLM 作为受限的补充识别层。
- 不改造前端 UI，追问消息通过现有文本消息机制下发。
- 不涉及图片生成模型本身的改动。

## Decisions

1. **词库与识别服务分离**
   - 将领域词库存储在 YAML/JSON 文件中（如 `agent-core/data/intent_taxonomy.yaml`），便于运营调整。
   - 新增 `IntentRecognitionService` 统一处理识别逻辑，替换散落在 parser 中的硬编码匹配。

2. **分层识别策略**
   - Layer 1（精确匹配）：对用户输入分词后，在词库中直接命中标准词。
   - Layer 2（别名/同义词）：维护每个标准词的别名列表（如“快闪店”→“pop-up store”→“快闪”）。
   - Layer 3（编辑距离模糊匹配）：使用 `rapidfuzz` 计算相似度，阈值建议 0.75，关键字段阈值 0.85。
   - Layer 4（语义向量匹配）：使用 taxonomy embedding 捕获语义相近但字形差异大的表达（如“百货入口”↔“商场入口”），阈值建议 0.82，source 标记为 `semantic`。
   - Layer 5（LLM 兜底补充）：仅对本地未命中或低置信度的字段调用轻量级 LLM；prompt 中注入已识别字段和标准词库约束，要求模型只能从候选值中选择或保持未知。

3. **LLM 精细化调用**
   - 本地识别完成后生成“待填充意图对象”，只把 `null` 或 confidence < threshold 的字段交给 LLM。
   - prompt 中显式列出该字段的标准词候选列表，降低模型幻觉。
   - 对完整输入的首次解析也走“本地优先 + LLM 补字段”路径，而不是直接调 LLM 抽全部。

4. **上下文补全机制**
   - 在对话状态 `DialogueState` 中维护最近一次完整意图 `last_intent`。
   - 定义字段优先级策略表：
     - 必须追问（阻塞）：`space_type`、`budget`
     - 可静默继承：`style`、`color_preference`、`material_restrictions`、`special_requirements`
     - 可领域默认补全：`points`（按 `space_type` 给出默认点位组合，如快闪店 → 门头、DP点、合影墙）、`timeline`
   - 当新输入缺失某字段时，按策略表决定是追问、继承还是填充默认值。

5. **跨模态词库统一**
   - 将 `intent_taxonomy.yaml` 中的标准空间类型、点位、风格、材质词序列化为 JSON，注入 `PhotoParser`、`VideoParser`、`ReferenceParser` 的 VLM prompt。
   - 要求 VLM 输出必须从候选词中选择，无法命中时返回 `unknown`。

6. **可观测性输出**
   - 识别结果结构增加 `source` 字段：`exact`、`alias`、`fuzzy`、`semantic`、`llm`、`default`、`unknown`。
   - 增加 `confidence` 字段（0-1）和 `candidates` 候选列表。
   - 这些元数据写入 `thinking_logs` 或调试接口，不暴露给最终用户文案。

7. **评测基准与 CI**
   - 在 `agent-core/tests/intent/golden_cases.jsonl` 维护测试用例，覆盖 exact / alias / fuzzy / semantic / llm / context 六类场景。
   - 实现 `IntentRecognitionEvaluator`，计算关键字段（`space_type`、`budget`、`points`）的准确率、召回率和平均置信度。
   - 在 CI 中运行：关键字段准确率低于 90% 时失败。

8. **依赖选型**
   - 中文分词使用 `jieba`（无模型文件、启动快），并加载 taxonomy 作为自定义词典。
   - 模糊匹配使用 `rapidfuzz`（纯 C++ 实现，性能优于 `fuzzywuzzy`）。
   - 语义向量使用轻量级模型（如 `BAAI/bge-small-zh` 或利用现有 embedding 服务）对 taxonomy 条目预计算 embedding。
   - 词库热加载：启动时加载，后续可通过环境变量或文件监听刷新。

9. **在线词库扩展**
   - 对 source=`unknown` 且后续被用户确认的字段，记录到 `intent_feedback_log`。
   - 提供脚本/管理接口，将高频 unknown 输入合并回 `intent_taxonomy.yaml`。

## Risks / Trade-offs

- **[Risk] 词库覆盖不全导致识别率低** → 先整理核心 50+ 商业空间类型和 30+ 常用点位，后续根据 golden test set 和用户反馈日志持续扩展。
- **[Risk] rapidfuzz 阈值过低引入误识别** → 默认阈值 0.75，对关键字段（如空间类型）采用更严格阈值 0.85。
- **[Risk] 语义向量模型增加启动时间和资源** → 使用 small 模型或复用现有 embedding 服务；taxonomy 规模小，embedding 缓存占用可忽略。
- **[Risk] LLM 兜底增加成本和延迟** → 仅对未命中字段调用；prompt 中注入约束减少迭代次数。
- **[Trade-off] 上下文补全可能“过度假设”** → 严格按策略表执行，低置信度补全必须追问，高置信度补全才静默填充。

## Migration Plan

- 阶段 1：新增词库文件、`IntentRecognitionService`、语义向量层和单元测试，保持旧 parser 作为兼容层。
- 阶段 2：将现有输入解析入口迁移到新服务，保留 LLM 兜底和旧 parser feature flag 回滚能力。
- 阶段 3：为 photo/video/reference parser 注入 taxonomy，统一跨模态输出。
- 阶段 4：建立 golden test set 和 CI 准确率检查。
- 阶段 5：上线后收集 1 周真实输入，调整词库、阈值和策略表。
- 回滚：若识别准确率下降，切换回旧 parser 开关（通过 feature flag）。

## Open Questions

- 是否需要在词库中维护品牌/活动相关词汇（如“新春”“国潮”作为风格标签）？
- 低置信度追问的文案模板是否由运营配置还是硬编码？
- 语义向量层是本地加载 small 模型，还是复用现有的 `embedding_client` 服务？
