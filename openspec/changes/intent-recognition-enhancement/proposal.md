## Why

当前用户在输入设计需求时，系统只能识别有限的关键词（如“中庭”），无法正确理解“快闪店”“百货入口”“步行街”等常见商业空间类型，导致需求解析不完整、后续推荐偏差。需要引入业界标准的意图识别方案，支持精确词库匹配、智能模糊识别和上下文补全，提升需求理解准确率。

## What Changes

- 建立商业美陈领域的空间类型、点位、预算、材质等标准化词库（taxonomy）。
- 将现有的简单关键词匹配替换为多层识别策略：精确匹配 → 别名/同义词扩展 → 模糊相似度匹配 → LLM 兜底识别。
- 引入上下文补全机制：根据对话历史、已识别字段和领域知识，自动补全缺失的关键信息（空间类型、预算、点位数量等）。
- 在 `agent-core` 的意图解析模块中增加可观测的中间结果（recognized tokens、confidence、fallback reason），便于后续调试。
- 为识别错误提供可配置的回退策略：低置信度时主动追问，而不是直接采用默认值。

## Capabilities

### New Capabilities
- `intent-recognition`: 用户输入的语义解析与意图识别，包括空间类型、点位、预算、风格、材质等关键字段的抽取与补全。

### Modified Capabilities
- （无现有 spec 级别的需求变更；用户上下文绑定属于实现细节，已在 design.md 中说明。）

## Impact

- `agent-core/app/agents/input_parser.py` 或同类的需求解析模块。
- `agent-core/app/services/` 下新增意图识别服务与词库管理。
- 可能引入轻量级 NLP 库（如 `jieba` 中文分词、`fuzzywuzzy`/`rapidfuzz` 模糊匹配）。
- 前端对话流程：低置信度字段需要生成追问消息。
