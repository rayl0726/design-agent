# 通用 Agent 运行时架构

## Why

当前系统是一个硬编码为美陈设计的工作流（`text_parse → requirement_analyze → knowledge_retrieve → concept_design → visual_design → technical_design`），所有节点、prompt、输出结构都默认服务单一垂直领域。随着业务扩展，需要让系统从"单一设计工作流"演进为"通用 Agent 平台"：美陈只是其中一个专业模式，未来可低成本接入展厅、数据分析等其他 Agent。同时 Agent 应具备自主决策能力——能语义拆解请求、分任务执行、自我评估置信度，并在达到高把握度后再向用户返回结果。

## What Changes

- 在 `agent-core` 中引入通用 Agent 运行时框架（`app/runtime/`），提供 ReAct 风格的推理-行动循环、任务规划、工具注册、置信度评估和上下文管理。
- 将现有美陈相关代码迁移为 `agent-core/app/agents/meichen/` 下的一个 Agent 插件，通过 `invoke_meichen_workflow` 工具被通用 Agent 调用。
- 新增 `app/agents/generic/` 通用 Agent，作为默认入口；前端默认展示"通用 Agent"标签，"美陈 Agent"作为其子模式。
- 新增 YAML 化的 Agent Registry（`config/agents.yaml`），用于注册 agent、task template、核心字段和工具集。
- 扩展 `agent-api` 的 `Project`/`Conversation` 模型，新增 `agent_type`、`agent_context_json` 等字段，并增加 `GenericAgentHandler` 负责会话分发与 SSE 转发。
- 前端 `ChatView` 增加全局 `AgentSelector` 组件，默认选中通用 Agent；新增折叠式 reasoning trace 和 tool call 状态展示。
- 设计分层记忆系统（Working / Short-term / Long-term）和上下文压缩策略，支持多轮对话不丢失关键信息。
- 预留 `football` 等未来 Agent 的注册接口，本次不实现具体逻辑。

## Capabilities

### New Capabilities

- `generic-agent-runtime`: 通用 Agent 运行时核心，包括 ReAct Loop、任务拆解、置信度评估、上下文与记忆管理。
- `agent-registry`: Agent 注册与配置管理，支持 YAML 配置化注册新 Agent 和任务模板。
- `agent-tool-system`: 通用工具框架与工具注册中心，内置 `ask_user`、`respond_to_user`、`knowledge_retrieval`、`web_search`、`code_execution`、`image_generation`、`invoke_meichen_workflow` 等工具。
- `agent-memory-management`: 分层记忆系统与上下文压缩，包括 working memory、short-term conversation memory、long-term user memory。
- `agent-frontend-selector`: 前端 Agent 选择器与 reasoning trace 展示，支持会话级 agent 切换和折叠式思考链。

### Modified Capabilities

- `intent-recognition`: 从单一意图字段提取升级为请求语义理解与多任务拆解，输出 Task Plan。
- `image-generation-prompts`: 图片生成能力作为通用工具被 Agent Loop 动态调用，保持现有 prompt 模板机制。
- `knowledge-rag-metrics` / `admin-knowledge-rag-metrics`: 知识检索作为通用工具，RAG 日志按 `agent_type` 分类。

## Impact

- **agent-core**: 新增 `runtime/`、`tools/`、`agents/generic/`，重构 `agents/` 为按 agent 隔离的目录结构；`api/routers.py` 简化为动态 agent 路由注册。
- **agent-api**: `ProjectController`、`DialogueService`、`WorkflowService` 增加按 `agent_type` 分发的逻辑；新增 `AgentRegistry`、`GenericAgentHandler`、扩展 SSE 事件类型。
- **agent-web**: `ChatView` 增加 `AgentSelector`、`ReasoningTrace` 组件；API client 支持创建会话时携带 `agent_type`。
- **数据库**: `java_projects` 表新增 `agent_type`、`agent_context_json` 字段（先不改表名）。
- **外部依赖**: 可能新增 web search API（如 SerpAPI/Bing）、代码执行沙箱等，Phase 1 暂不实装。
