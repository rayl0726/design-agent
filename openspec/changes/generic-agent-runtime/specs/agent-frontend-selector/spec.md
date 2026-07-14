## ADDED Requirements

### Requirement: 全局 Agent 选择器
前端 SHALL 在输入框下方全局展示 Agent 选择器，默认选中"通用 Agent"，"美陈 Agent"作为其子模式。

#### Scenario: 默认展示通用 Agent
- **WHEN** 用户进入聊天页面
- **THEN** AgentSelector SHALL 默认选中"通用 Agent"

#### Scenario: 切换 Agent 创建新会话
- **WHEN** 用户点击"美陈 Agent"标签
- **THEN** 系统 SHALL 创建一个新的 meichen 模式会话，而不是改变当前会话的 agent

### Requirement: 折叠式 Reasoning Trace
前端 SHALL 以折叠形式展示 Agent 的 reasoning trace，包括 thought、tool call、verification 过程。

#### Scenario: 查看思考过程
- **WHEN** Agent 正在处理请求
- **THEN** 用户 SHALL 能看到"思考中..."及可展开的 reasoning trace

#### Scenario: 查看工具调用
- **WHEN** Agent 调用 knowledge_retrieval 或 invoke_meichen_workflow
- **THEN** reasoning trace SHALL 显示工具名称和状态

### Requirement: Agent 专属欢迎内容
每个 Agent 模式 SHALL 拥有独立的欢迎语和示例 chips。

#### Scenario: 通用 Agent 欢迎页
- **WHEN** 用户处于通用 Agent 模式
- **THEN** 欢迎页 SHALL 展示通用能力介绍和通用示例

#### Scenario: 美陈 Agent 欢迎页
- **WHEN** 用户处于美陈 Agent 模式
- **THEN** 欢迎页 SHALL 展示美陈设计示例 chips

### Requirement: 创建会话携带 agent_type
前端创建会话 API SHALL 携带 agent_type 参数，后端根据该参数初始化对应 Agent 模式。

#### Scenario: 创建通用会话
- **WHEN** 用户点击"新建对话"且当前为通用 Agent
- **THEN** 前端 SHALL 调用 POST /projects 并传入 agent_type=generic
