## ADDED Requirements

### Requirement: 统一工具接口
所有工具 SHALL 实现统一的 BaseTool 接口，包含 name、description、parameters schema 和 execute 方法。

#### Scenario: 注册新工具
- **WHEN** 开发者实现一个继承 BaseTool 的新工具
- **THEN** ToolRegistry SHALL 通过 register 方法将其纳入可用工具集

### Requirement: 内置基础工具
Phase 1 工具系统 SHALL 至少内置：ask_user、respond_to_user、knowledge_retrieval、invoke_meichen_workflow、image_generation。

#### Scenario: 信息不足时提问
- **WHEN** Agent 判断缺少关键字段
- **THEN** Agent SHALL 调用 ask_user 工具向用户发起澄清问题

#### Scenario: 调用美陈工作流
- **WHEN** Agent 识别到美陈需求且字段齐全
- **THEN** Agent SHALL 调用 invoke_meichen_workflow 工具生成设计方案

### Requirement: 预留扩展工具接口
工具系统 SHALL 预留 web_search、code_execution、database_query、chart_generator 的扩展接口，Phase 1 可不实现具体逻辑。

#### Scenario: 未来接入网页搜索
- **WHEN** 后续实现 web_search 工具
- **THEN** 只需新增一个 BaseTool 实现并注册，无需修改 ToolRegistry 框架

### Requirement: 工具调用可观测
每次工具调用 SHALL 记录调用名称、输入、输出摘要、耗时和执行状态，供 reasoning trace 展示。

#### Scenario: 展示工具调用过程
- **WHEN** Agent 调用 knowledge_retrieval
- **THEN** 前端 reasoning trace SHALL 显示"正在检索知识库..."及结果摘要
