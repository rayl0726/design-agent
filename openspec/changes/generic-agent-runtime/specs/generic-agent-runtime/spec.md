## ADDED Requirements

### Requirement: Agent Loop 执行推理-行动循环
通用 Agent 运行时 SHALL 实现 ReAct 风格的循环：每次迭代包含 Reason（推理）、Action（选择工具/行动）、Observation（观察结果）、Verify（验证置信度）、Decide（决定下一步）。

#### Scenario: 简单查询一次性完成
- **WHEN** 用户输入"什么是美陈设计"
- **THEN** Agent 经过 1-2 轮 reasoning 后调用 respond_to_user 返回最终答案

#### Scenario: 复杂请求需要多轮迭代
- **WHEN** 用户输入"帮我设计一个海洋主题购物中心中庭美陈"
- **THEN** Agent 拆解为信息收集、案例检索、方案生成等子任务，逐轮执行并在置信度达标后返回

### Requirement: 请求语义拆解与任务规划
通用 Agent 运行时 SHALL 将用户请求拆解为结构化的 Task Plan，每个任务包含目标、类型、依赖、成功标准和置信度阈值。

#### Scenario: 美陈需求自动拆解
- **WHEN** 用户输入包含主题、空间类型、预算等美陈需求
- **THEN** Task Plan 中 SHALL 包含 information_gathering、retrieve_cases、generate_ideas、generate_images 等任务

#### Scenario: 通用咨询不触发设计任务
- **WHEN** 用户输入"美陈设计一般需要多少钱"
- **THEN** Task Plan 中 SHALL 只包含 answer_question 类任务，不生成 design_generation 任务

### Requirement: 置信度评估与门控
通用 Agent 运行时 SHALL 对每个任务执行结果评估置信度；最终返回用户前，整体置信度 MUST 达到全局可配置阈值（默认 0.95）。未达标时 SHALL 自动重试、补充信息或询问用户。

#### Scenario: 信息完整直接返回
- **WHEN** 所有关键字段已确认且整体置信度 ≥ 0.95
- **THEN** Agent SHALL 调用 respond_to_user 输出结果

#### Scenario: 创意生成置信度不足重试
- **WHEN** 创意生成任务置信度为 0.88，低于任务阈值 0.90
- **THEN** Agent SHALL 选择补充检索或换 prompt 重试，而不是直接返回

#### Scenario: 无法自动提升时询问用户
- **WHEN** 经过最大迭代次数后整体置信度仍 < 0.95
- **THEN** Agent SHALL 调用 ask_user 向用户说明不确定性并请求补充信息

### Requirement: 循环安全与终止条件
通用 Agent 运行时 SHALL 具备防止无限循环的机制：最大迭代次数、时间上限、重复 action 检测和不可恢复错误终止。

#### Scenario: 达到最大迭代次数
- **WHEN** Agent 已执行 10 轮仍未达到最终阈值
- **THEN** Agent SHALL 停止循环并向用户说明当前最佳结果或询问用户

#### Scenario: 重复 action 检测
- **WHEN** 相同 action 和 input 连续出现 2 次
- **THEN** Agent SHALL 标记为潜在死循环并强制退出或切换策略
