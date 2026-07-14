## 1. 准备与基础框架

- [ ] 1.1 在 `agent-core` 创建 `app/runtime/`、`app/tools/`、`app/agents/generic/`、`app/agents/meichen/` 目录结构
- [ ] 1.2 将现有美陈相关 agent 文件迁移到 `app/agents/meichen/skills/`，保持现有逻辑不变
- [ ] 1.3 创建 `config/agents.yaml` 并注册 `generic`、`meichen`、`football(预留)` 三个 agent
- [ ] 1.4 实现 `AgentRegistry` 加载器，启动时解析 YAML 到内存对象
- [ ] 1.5 在 `agent-core` 新增统一路由 `/agents/{agent_id}/run` 并保留现有美陈端点短期兼容

## 2. 通用 Agent 运行时核心

- [ ] 2.1 定义 `BaseAgent`、`AgentLoopResult`、`ToolContext`、`ToolResult` 等核心模型
- [ ] 2.2 实现 `AgentLoop`：支持 PLAN → SELECT → EXECUTE → VERIFY → DECIDE 循环
- [ ] 2.3 实现循环安全机制：`max_iterations`、时间上限、重复 action 检测、异常终止
- [ ] 2.4 实现 `RequestAnalyzer`：基于 LLM 结构化输出进行意图识别和任务拆解
- [ ] 2.5 实现 `TaskPlanner`：根据 agent 的 task templates 生成带依赖的 Task Plan
- [ ] 2.6 实现 `Verifier`：支持 rule-based、self-evaluation、external validator 三种评估方式
- [ ] 2.7 实现全局置信度配置（默认 0.95）和任务级阈值覆盖
- [ ] 2.8 实现 `GenericAgent`：使用通用 loop 处理输入，支持澄清、重试、最终回复

## 3. 工具系统与美陈集成

- [ ] 3.1 实现 `ToolRegistry` 和 `BaseTool` 抽象
- [ ] 3.2 实现 `ask_user` 工具：返回澄清问题给 agent-api
- [ ] 3.3 实现 `respond_to_user` 工具：结束 loop 并生成最终回复
- [ ] 3.4 实现 `knowledge_retrieval` 工具：复用现有 RAG 能力，支持 `agent_type` 参数
- [ ] 3.5 实现 `invoke_meichen_workflow` 工具：包装现有美陈 DAG，接收 theme/space_type/budget 等参数
- [ ] 3.6 实现 `image_generation` 工具：复用现有图片生成服务
- [ ] 3.7 预留 `web_search`、`code_execution`、`database_query`、`chart_generator` 工具接口
- [ ] 3.8 将美陈 workflow 改造为可被 tool 调用，保持原有 L1/L2/L3 输出和 stage logs 不变

## 4. 记忆与上下文管理

- [ ] 4.1 设计并实现 `MemoryManager`，支持 Working / Short-term / Long-term 三层
- [ ] 4.2 实现 `ContextManager`：按固定顺序组装上下文并管理 token budget
- [ ] 4.3 实现对话轮级摘要和主题摘要，触发条件：轮次 > 5 或 > 15
- [ ] 4.4 实现关键字段保护机制：已确认字段写入 Working Memory，不参与压缩
- [ ] 4.5 新增 `user_memories` 表和对应 Repository（长期记忆）
- [ ] 4.6 实现 `update_memory` 工具：允许 Agent 在任务完成后写入长期记忆

## 5. agent-api 分发与数据模型

- [ ] 5.1 在 `java_projects` 表新增 `agent_type`、`agent_context_json` 字段
- [ ] 5.2 扩展 `Project` 实体和 DTO，支持 `agent_type` 创建和查询
- [ ] 5.3 实现 `AgentRegistry`（Java 侧），从配置或 agent-core 同步 agent 列表
- [ ] 5.4 实现 `AgentDispatcher`：根据 `agent_type` 分发到 `MeichenAgentHandler` 或 `GenericAgentHandler`
- [ ] 5.5 实现 `GenericAgentHandler`：调用 agent-core `/agents/{agent_id}/run`，转发 SSE 事件
- [ ] 5.6 扩展 SSE 事件类型：`task_update`、`tool_call`、`reasoning`、`clarification`
- [ ] 5.7 修改 `ProjectController.addMessage` 按 `agent_type` 路由 handler
- [ ] 5.8 修改创建 project API，支持前端传入 `agent_type`

## 6. 前端 Agent 选择器与交互

- [ ] 6.1 实现 `AgentSelector` 组件，置于输入框下方，默认选中"通用 Agent"
- [ ] 6.2 实现切换 agent 时创建新会话的逻辑
- [ ] 6.3 实现不同 agent 的欢迎语和示例 chips
- [ ] 6.4 实现 `ReasoningTrace` 组件，折叠展示 thought / tool call / verification
- [ ] 6.5 扩展消息类型渲染：未知类型降级为 `TextMessage` 或 `raw-content`
- [ ] 6.6 修改 API client：创建会话时携带 `agent_type`
- [ ] 6.7 处理新增 SSE 事件并更新前端状态

## 7. RAG 与监控适配

- [ ] 7.1 修改 `rag_search_logs` 写入逻辑，支持记录 `agent_type` 和 `conversation_id`
- [ ] 7.2 修改 RAG metrics API，支持按 `agent_type` 过滤和分组
- [ ] 7.3 修改 admin RAG 页面，展示按 agent 的检索指标

## 8. 测试与回归

- [ ] 8.1 编写 `AgentLoop` 单元测试：循环终止、重复 action 检测、置信度门控
- [ ] 8.2 编写 `TaskPlanner` 单元测试：美陈需求拆解、通用问题拆解、多意图拆解
- [ ] 8.3 编写 `Verifier` 单元测试：rule-based 评估、self-evaluation 评估
- [ ] 8.4 编写 `ContextManager` 单元测试：上下文压缩、关键字段保护
- [ ] 8.5 集成测试：通用 Agent → 收集字段 → 调用美陈 workflow → 返回方案
- [ ] 8.6 回归测试：原有美陈直接模式功能不降级
- [ ] 8.7 前端 E2E 测试：切换 agent、创建会话、展示 reasoning trace
- [ ] 8.8 后端编译通过（`-Xlint:all`）且 Python lint 通过

## 9. 文档与部署

- [ ] 9.1 更新 `agent-core` README，说明新的 agent 插件开发方式
- [ ] 9.2 更新 API 文档，说明新增 `/agents/{agent_id}/run` 端点和 SSE 事件
- [ ] 9.3 更新数据库迁移脚本
- [ ] 9.4 部署到测试环境并验证完整链路
