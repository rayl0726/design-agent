## ADDED Requirements

### Requirement: 分层记忆模型
记忆系统 SHALL 包含三层：Working Memory（工作记忆）、Short-term Memory（短期会话记忆）、Long-term Memory（长期用户记忆）。

#### Scenario: 单轮对话使用 Working Memory
- **WHEN** Agent 正在执行当前任务
- **THEN** Working Memory SHALL 保存当前目标、已收集字段、中间结果和待确认项

#### Scenario: 跨轮对话使用 Short-term Memory
- **WHEN** 用户在多轮对话中补充信息
- **THEN** Short-term Memory SHALL 保留本会话的消息历史和轮级摘要

### Requirement: 上下文压缩
当会话轮次或 token 预算超过阈值时，系统 SHALL 对历史消息进行摘要压缩，但 SHALL 保护已确认的关键字段不丢失。

#### Scenario: 长对话自动摘要
- **WHEN** 会话轮次超过 15 轮
- **THEN** 系统 SHALL 生成主题摘要，并只保留最近 3 轮原始消息

#### Scenario: 关键字段不被压缩
- **WHEN** 用户已确认 theme=海洋、space_type=购物中心中庭、budget=15万
- **THEN** 这些字段 SHALL 始终保留在 Working Memory 中，即使上下文被压缩

### Requirement: 上下文组装策略
每次进入 Agent Loop 时，系统 SHALL 按固定顺序组装上下文：System Prompt + Agent Registry + User Profile + Long-term Memory + Conversation Summary + Recent Messages + Working Memory + Current Input。

#### Scenario: 加载完整上下文
- **WHEN** Agent 开始处理用户消息
- **THEN** Memory Manager SHALL 返回按上述顺序组装且未超过 token 预算的上下文

### Requirement: 长期记忆可检索
Long-term Memory SHALL 支持按用户和类型检索，未来可支持向量语义检索。

#### Scenario: 读取用户偏好
- **WHEN** 用户历史会话中多次偏好轻奢风格
- **THEN** Long-term Memory SHALL 返回该偏好，供当前推理参考
