## ADDED Requirements

### Requirement: YAML 化 Agent 注册
Agent Registry SHALL 支持通过 YAML 配置文件注册 Agent，包含 agent id、名称、描述、默认标识、handler class、task templates 和可用工具列表。

#### Scenario: 启动时加载注册表
- **WHEN** agent-core 服务启动
- **THEN** Agent Registry SHALL 读取 config/agents.yaml 并加载所有 enabled agent

#### Scenario: 获取默认 Agent
- **WHEN** 前端创建新会话未指定 agent_type
- **THEN** Agent Registry SHALL 返回标记为 default 的 agent（generic）

### Requirement: 支持 Task Template 注册
每个 Agent 的注册信息 SHALL 包含其支持的 task templates，定义任务类型、必填字段、依赖和置信度阈值。

#### Scenario: 美陈 Agent 注册任务模板
- **WHEN** 注册 meichen agent
- **THEN** 其 task_templates SHALL 包含 information_gathering、retrieve_cases、generate_ideas、generate_images

#### Scenario: 通用 Agent 使用默认模板
- **WHEN** 注册 generic agent
- **THEN** 其 task_templates SHALL 包含 understand、plan、execute、verify

### Requirement: 低成本新增 Agent
新增 Agent SHALL 只需要：创建 agent 目录、实现 BaseAgent 子类、在 YAML 中注册，无需修改运行时框架代码。

#### Scenario: 新增预留 Agent
- **WHEN** 开发者在 config/agents.yaml 中添加 football agent（enabled=false）
- **THEN** 运行时 SHALL 识别该 agent 但不在前端激活列表中展示
