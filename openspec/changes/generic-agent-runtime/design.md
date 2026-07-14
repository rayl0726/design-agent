# 通用 Agent 运行时架构设计

## Context

当前系统由三个主要模块组成：

- `agent-core`（Python FastAPI）：承载美陈设计所需的 AI agent，包括 `input_parser`、`requirement_analyst`、`concept_designer`、`visual_designer`、`technical_designer` 等。这些 agent 通过 `api/routers.py` 中的硬编码端点暴露，prompt 和输出结构都默认服务美陈场景。
- `agent-api`（Java Spring Boot）：负责用户会话、Project 状态管理、工作流编排、SSE 事件推送。
- `agent-web`（Vue 3）：单一 Chat 界面，所有交互都围绕美陈设计工作流。

当前问题：
1. `WorkflowDefinition` 是全局静态 DAG，无法按 agent 切换。
2. `DialogueService` 的意图识别、字段校验、消息类型都假设用户在和美陈 agent 对话。
3. `Project` 实体没有 `agent_type`，无法区分不同 agent 的会话。
4. 前端没有 agent 选择能力，所有欢迎语、示例 chips、消息渲染组件都是美陈专属。

本设计目标是把 `agent-core` 升级为**通用 Agent 运行时**，让美陈成为其中的一个插件式 agent 模式。

## Goals / Non-Goals

**Goals:**

- 建立通用 Agent 运行时框架，支持 ReAct 风格的推理-行动循环。
- 支持请求的语义拆解和多任务规划，每个子任务执行后自我评估置信度。
- 全局可配置的置信度阈值（默认 0.95），未达标时自动重试、补充信息或询问用户。
- 设计分层记忆系统（Working / Short-term / Long-term）和上下文压缩策略。
- 通过 YAML 化的 Agent Registry 低成本注册新 agent；美陈作为默认专业模式被复用。
- 前端默认展示"通用 Agent"，"美陈 Agent"作为子模式；新增折叠式 reasoning trace。

**Non-Goals:**

- 本次不实现除美陈之外的第二个完整 agent（如足球数据分析仅预留注册位）。
- 本次不引入外部 web search API 或代码执行沙箱，只在工具系统中预留接口。
- 本次不改 `java_projects` 表名，仅新增字段。
- 不推翻现有美陈工作流的内部逻辑，只是将其包装为可被通用 agent 调用的工具。

## Decisions

### 1. 通用 Agent 运行时放在 `agent-core`

**决策**：核心 ReAct Loop、工具系统、记忆管理、任务规划全部放在 Python 侧的 `agent-core`。

**理由**：
- `agent-core` 已经拥有 LLM/VLM、RAG、图片生成等全部 AI 基础设施，推理循环天然属于 AI 运行时。
- `agent-api` 保留其擅长的会话状态管理、SSE、用户认证、持久化。
- 避免在 Java 侧再实现一套 LLM 调用和 prompt 管理。

**替代方案**：把通用 loop 放在 `agent-api`。放弃原因：需要把大量 AI 能力（prompt、tool、memory）迁移到 Java，成本高且重复建设。

### 2. 美陈作为 Agent 插件，同时被通用 Agent 通过工具调用

**决策**：
- 将现有 `app/agents/` 下美陈相关代码迁移到 `app/agents/meichen/`。
- 提供 `invoke_meichen_workflow` 工具，通用 Agent 在识别到美陈需求且字段齐全后调用它。

**理由**：
- 现有美陈 DAG 复杂（stage logs、HTML 生成、checkpoint 确认），先不拆解。
- 通用 Agent 负责"判断是否需要启动美陈"和"收集前置信息"，美陈工作流负责"生成方案"。
- 未来如果要把美陈也改成 loop 式，可以逐步把每个节点变成 tool。

### 3. Agent Registry 使用 YAML 配置

**决策**：用 `config/agents.yaml` 注册 agent、task templates、核心字段和工具集，启动时加载到内存。

**理由**：
- 用户明确"配置化，目前不会很多 agent"。
- YAML 改动简单，无需新增 DB 表和 admin 后台。
- 未来可平滑迁移到 DB + 热加载。

**替代方案**：DB 化 registry。放弃原因：当前阶段 over-engineering。

### 4. 会话模型：Project 语义升级为 Conversation

**决策**：
- 先不改 `java_projects` 表名，新增 `agent_type`、`agent_context_json` 字段。
- 业务上把 Project 视为 Conversation，美陈产生的方案数据继续用 `l1/l2/l3_output_json` 存储。

**理由**：
- 最小化数据库迁移成本。
- 后续如果 conversation 和 project 真的需要拆分，再独立建表。

### 5. 默认入口是通用 Agent，美陈是子模式

**决策**：前端默认选中"通用 Agent"，点击"美陈 Agent"时创建一个新的美陈模式会话。

**理由**：
- 符合用户"优先展示通用 agent"的要求。
- 美陈 Agent 可视为"通用 Agent + 默认调用美陈 workflow"的快捷模式，减少一轮 reasoning。
- 未来新增 agent 都走同一套交互范式。

### 6. 置信度：全局阈值 + 任务级阈值

**决策**：
- 全局最终阈值默认 0.95，可配置。
- 每个 task 可配置自己的 `confidence_threshold`（如信息收集 0.95、图片生成 0.80）。
- 整体置信度未达标时，由 Agent 自主决定重试、补充检索或询问用户。

**理由**：
- 统一门槛保证输出质量。
- 不同任务类型对"高把握"的定义不同，任务级阈值更灵活。

### 7. 上下文压缩：分层 + 关键字段保护

**决策**：
- 消息历史按轮次压缩为摘要，但关键字段抽取到 working memory，不参与压缩。
- 当 token 预算超过阈值或轮次过多时触发压缩。

**理由**：
- 避免 LLM 上下文过长导致成本和质量下降。
- 关键字段（如 theme/space_type/budget）一旦确认就不应被摘要丢失。

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        agent-web                            │
│  AgentSelector（默认通用） │ ReasoningTrace（折叠）           │
│  ChatView / IdeaGallery / DataCard...                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼───────────────────────────────────┐
│                        agent-api                            │
│  ProjectController / ConversationService / AgentDispatcher  │
│  AgentRegistry (YAML)                                       │
│  SSEEmitterService                                          │
│  SessionMessageService / ProjectRepository                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────┐
│                        agent-core                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Generic Agent Runtime                   │   │
│  │  AgentLoop / ContextManager / MemoryManager          │   │
│  │  RequestAnalyzer / TaskPlanner / Verifier            │   │
│  │  ToolRegistry / ResponseGenerator                    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Tools     │  │   Agents    │  │  Agent Registry     │ │
│  │  ask_user   │  │  generic/   │  │  config/agents.yaml │ │
│  │  respond_   │  │  meichen/   │  └─────────────────────┘ │
│  │  knowledge_ │  │  (football) │                            │
│  │  retrieval  │  └─────────────┘                            │
│  │  invoke_    │                                             │
│  │  meichen_   │                                             │
│  │  workflow   │                                             │
│  └─────────────┘                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Shared Services                           │   │
│  │  llm_client / vlm_client / image_generation         │   │
│  │  knowledge_base / embedding_client / call_logger    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Agent Loop (`app/runtime/agent_loop.py`)

核心循环：

```
PLAN → SELECT → EXECUTE → VERIFY → DECIDE
```

退出条件：
- 调用 `respond_to_user` action
- 达到 `max_iterations`（默认 10）
- 相同 action + input 连续重复 2 次
- 单次 loop 时间超过 5 分钟
- 出现不可恢复错误

### 2. Request Analyzer + Task Planner

请求理解分两步：
1. **Intent Parser**：识别用户意图、agent mode、关键字段。
2. **Task Planner**：根据 agent mode 的 task templates 生成 Task Plan。

每个 Task 包含：
- `id`, `goal`, `type`
- `required_fields`
- `success_criteria`
- `confidence_threshold`
- `dependencies`

### 3. Verifier（置信度评估）

三种评估方式：
- **Rule-based**：字段完整性、图片成功数等。
- **Self-evaluation**：LLM 对生成内容（如创意差异化）打分并说明理由。
- **External validator**：数据查询结果对比事实。

Verifier 输出：
- `confidence`: 0~1
- `reason`: 评估理由
- `suggested_action`: retry / retrieve_more / ask_user / accept

### 4. Tool System

工具基类：

```python
class BaseTool(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema

    @abstractmethod
    async def execute(self, inputs: dict, context: ToolContext) -> ToolResult:
        ...
```

Phase 1 内置工具：
- `ask_user`
- `respond_to_user`
- `knowledge_retrieval`
- `invoke_meichen_workflow`
- `image_generation`

预留工具：
- `web_search`
- `code_execution`
- `database_query`
- `chart_generator`

### 5. Memory Manager

三层记忆：

| 层级 | 内容 | 生命周期 | 存储 |
|---|---|---|---|
| Working Memory | 当前任务目标、已收集字段、中间结果、待确认项 | 单次 loop | 运行时对象 |
| Short-term Memory | 当前会话完整消息历史、轮级摘要 | 单个 conversation | MySQL `session_messages` + `agent_context_json` |
| Long-term Memory | 用户画像、跨会话摘要、成功案例模式 | 用户级别 | MySQL `user_memories` + 向量检索 |

上下文加载时按以下顺序组装：
1. System Prompt + Agent Registry
2. User Profile + 相关 Long-term Memory
3. Conversation Summary
4. Recent Messages（已压缩）
5. Working Memory
6. Current Turn Input

### 6. Agent Registry

`config/agents.yaml` 示例：

```yaml
agents:
  - id: generic
    name: 通用 Agent
    description: 通用问题求解与任务执行 Agent
    default: true
    handler_class: app.agents.generic.agent.GenericAgent
    task_templates:
      - id: understand
      - id: plan
      - id: execute
      - id: verify
    tools:
      - ask_user
      - respond_to_user
      - knowledge_retrieval
      - web_search
      - invoke_meichen_workflow

  - id: meichen
    name: 美陈 Agent
    description: 商业空间美陈设计方案生成
    handler_class: app.agents.meichen.agent.MeichenAgent
    task_templates:
      - id: information_gathering
        required_fields: [theme, space_type, budget]
        confidence_threshold: 0.95
      - id: retrieve_cases
        dependencies: [information_gathering]
      - id: generate_ideas
        dependencies: [information_gathering, retrieve_cases]
      - id: generate_images
        dependencies: [generate_ideas]
    tools:
      - ask_user
      - respond_to_user
      - knowledge_retrieval
      - invoke_meichen_workflow

  - id: football
    name: 足球数据 Agent
    description: 足球数据分析（预留）
    enabled: false
```

## Data Model Changes

### `java_projects` 表新增字段

```sql
ALTER TABLE java_projects
  ADD COLUMN agent_type VARCHAR(30) NOT NULL DEFAULT 'meichen',
  ADD COLUMN agent_context_json TEXT;
```

### 新增 `user_memories` 表（Long-term Memory）

```sql
CREATE TABLE user_memories (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  memory_type VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(768),  -- 若使用向量扩展
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_type (user_id, memory_type)
);
```

## API Changes

### agent-core

新增统一 Agent 路由：

```python
@router.post("/agents/{agent_id}/run")
async def run_agent(agent_id: str, payload: AgentRunRequest):
    agent = registry.get(agent_id)
    return await agent.run(payload)
```

保留现有美陈端点作为内部 tool 调用（短期兼容）。

### agent-api

创建会话：

```http
POST /api/v1/projects
Content-Type: application/json

{
  "name": "新对话",
  "agent_type": "generic",
  "inputs": []
}
```

消息接口保持不变，但 `ProjectController.addMessage` 内部按 `agent_type` 分发到对应 handler。

SSE 新增事件：
- `task_update`
- `tool_call`
- `reasoning`
- `clarification`

## Frontend Changes

- `AgentSelector`：全局置于输入框下方，默认选中"通用 Agent"，"美陈 Agent"为子模式。
- `ReasoningTrace`：折叠展示 thought / tool call / verification 过程。
- 创建会话时携带 `agent_type`。
- 消息类型扩展：`idea_gallery`（美陈）、`data_card`（未来）、`chart`（未来）。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| Loop 循环过长或死循环 | 响应慢、成本高 | `max_iterations`、时间上限、重复 action 检测、强制降级 |
| LLM 调用成本激增 | 每次循环都调 LLM | 简单 routing 用小模型；复杂推理才用大模型；限制 loop 次数 |
| 上下文压缩丢失关键信息 | 用户明确要求被忽略 | 关键字段写入 working memory，不参与压缩；摘要保留关键决策 |
| 工具调用失败级联 | 整体任务失败 | 每个 tool 有 fallback；verifier 失败后自主选择重试或询问用户 |
| 现有美陈流程被重构破坏 | 回归风险 | Phase 1 保留现有 workflow，仅通过 `invoke_meichen_workflow` 调用；完整回归测试 |
| 前端消息类型扩展导致兼容性问题 | 旧消息渲染异常 | 未知 messageType 降级为 `TextMessage` 或 `raw-content` |

## Migration Plan

1. **Phase 1: 搭建运行时骨架**
   - agent-core 新增 `runtime/`、`tools/`、`agents/generic/`、`agents/meichen/`。
   - 迁移现有美陈代码到 `agents/meichen/`。
   - 实现基础 Agent Loop、Context Manager、Memory Manager。

2. **Phase 2: 接入 agent-api 与前端**
   - agent-api 新增 `AgentRegistry`、`AgentDispatcher`、`GenericAgentHandler`。
   - 数据库新增字段。
   - 前端新增 `AgentSelector`、`ReasoningTrace`。

3. **Phase 3: 工具与置信度**
   - 实现 `invoke_meichen_workflow`、 `knowledge_retrieval`、 `ask_user`、 `respond_to_user`。
   - 实现 Verifier 和置信度评估。
   - 接入上下文压缩。

4. **Phase 4: 验证与回归**
   - 通用 Agent 走通"收集字段 → 调用美陈 workflow → 返回方案"完整链路。
   - 原有美陈直接模式回归测试。
   - 预留 `football` agent 注册位。

## Open Questions

1. 通用 Agent 识别到美陈需求后，是**直接调用** `invoke_meichen_workflow`，还是**切换会话 agent_type 为 meichen** 再走专门 handler？
   - 初步倾向：保持会话 agent_type 不变，通用 Agent 直接调用 tool；这样 reasoning trace 更完整。

2. 长期记忆的向量检索是否必须？
   - 初步倾向：Phase 1 可先不用向量，直接用关键词/规则匹配；后续再接入 embedding。

3. `agent_context_json` 是否需要在每次 loop 后都持久化？
   - 初步倾向：每轮 loop 结束或任务切换时持久化，避免进程崩溃丢失状态。
