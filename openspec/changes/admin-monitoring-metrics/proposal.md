## Why

当前 Admin 后台仅有 6 个概览指标和 2 个图表（阶段耗时 + 反馈分布），远低于业界 AI Agent 可观测性标准（通常 40+ 指标）。系统缺少 AI 模型调用监控（LLM/VLM/Embedding 的调用量、延迟、Token 消耗、错误率）、业务漏斗转化（项目从 draft → completed 各阶段流失率）、图像生成质量追踪、意图识别准确率分析、知识库 RAG 性能指标，以及系统基础设施健康监控（线程池、连接池、HTTP 错误率）。这些盲区导致运营和算法团队无法及时发现性能退化、成本异常和质量下滑。

## What Changes

- 新增 **业务流量指标**：项目漏斗转化率（draft → generating → completed）、项目放弃率、平均对话轮数、L1/L2/L3 级别分布、按空间类型/预算/风格的项目分布
- 新增 **AI 模型调用指标**：LLM/VLM/Embedding 调用次数、成功率、错误率、延迟分布（p50/p95/p99）、Token 用量、API 429 限流次数、重试次数、成本估算
- 新增 **图像生成指标**：生成总数/成功率/失败率、各 Provider 分布（智谱/SiliconFlow/Pollinations）、平均耗时、每项目平均生成数、图像反馈率、反馈标签分布
- 新增 **意图识别质量指标**：识别来源分布（exact/alias/fuzzy/semantic/llm/default）、平均置信度分布、低置信度字段占比、按字段分组的纠正率、对话轮数分布
- 新增 **知识库 RAG 指标**：语义搜索次数/平均耗时、Top-K 命中率、Embedding 缓存命中率、降级触发次数、检索超时次数
- 新增 **系统健康指标**：端到端工作流成功率、工作流重试次数分布、时间异常事件数、子阶段溢出事件数、线程池使用率、数据库连接池使用率、HTTP 请求 QPS/错误率
- 新增 **Prompt 模板增强指标**：模板使用频率、模板质量趋势、版本对比分析
- 扩展 Admin 前端 Dashboard：新增多个图表页面和筛选器，支持时间范围选择和维度下钻
- 在 agent-core Python 代码中增加 AI 调用埋点（LLM/VLM/Embedding/Image Generation 的调用日志写入数据库）
- 在 agent-api Java 代码中增加 HTTP 请求监控和线程池监控

## Capabilities

### New Capabilities
- `admin-ai-model-metrics`: AI 模型调用监控（LLM/VLM/Embedding 调用量、延迟、Token、成本、错误率）
- `admin-image-generation-metrics`: 图像生成监控（Provider 分布、成功率、耗时、反馈率）
- `admin-business-funnel-metrics`: 业务漏斗与转化监控（项目状态流转、完成率、对话轮数、级别分布）
- `admin-intent-quality-metrics`: 意图识别质量监控（来源分布、置信度、纠正率、对话轮数）
- `admin-knowledge-rag-metrics`: 知识库与 RAG 性能监控（检索次数、命中率、缓存率、超时）
- `admin-system-health-metrics`: 系统基础设施健康监控（线程池、连接池、HTTP 错误率、工作流成功率）

### Modified Capabilities
- `admin-system-metrics`: 扩展概览指标，增加时间维度筛选和趋势对比
- `admin-prompt-template-management`: 增加模板使用频率和质量趋势分析

## Impact

- **agent-core (Python)**: 需在 `llm_client.py`、`vlm_client.py`、`embedding_client.py`、`image_generation.py`、`knowledge_base.py` 中增加调用埋点，记录到新表 `ai_call_logs`
- **agent-api (Java)**: 需增加 HTTP 请求拦截器记录 QPS 和错误率，增加线程池监控
- **agent-admin-backend (Java)**: 新增 6 个 Metrics Service + Controller 端点，新增 DTO 和 Repository
- **agent-admin-front (Vue)**: 重构 Dashboard 页面，新增多个指标卡片和图表，支持时间范围筛选
- **数据库**: 新增 `ai_call_logs` 表（LLM/VLM/Embedding/Image 调用记录）、`rag_search_logs` 表（知识库检索记录）
- **依赖**: 前端可能需要引入更多 ECharts 图表类型（漏斗图、热力图、仪表盘）
