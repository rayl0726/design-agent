## Context

当前 Admin 后台（agent-admin-backend:8081 + agent-admin-front:8082）仅有 3 个 metrics 端点：
- `GET /api/admin/metrics/overview` — 6 个计数指标
- `GET /api/admin/metrics/stages` — 阶段耗时统计（从 stage_log_stats 预聚合表读取）
- `GET /api/admin/metrics/feedback-distribution` — 反馈按 tag+type 分组

数据来源仅覆盖 `projects`、`feedbacks`、`stage_logs`、`stage_log_stats` 四张表。系统中的 `thinking_logs`、`workflow_logs`、`session_messages`、`intent_traces` 数据未被利用。AI 模型调用（LLM/VLM/Embedding/Image Generation）和知识库检索完全没有埋点记录。

业界 AI Agent 可观测性标准要求覆盖 6 大类指标：业务流量、AI 模型调用、图像生成、意图质量、知识库 RAG、系统健康。当前覆盖率约 15%。

## Goals / Non-Goals

**Goals:**
- 将监控指标覆盖率从 15% 提升到 90%+，覆盖业界标准的 6 大类指标
- 利用已有数据库表数据，无需额外基础设施即可查询的指标优先实现
- 在 Python 侧增加 AI 调用埋点，将 LLM/VLM/Embedding/Image 调用记录持久化到数据库
- Admin 前端支持多维度图表展示和时间范围筛选

**Non-Goals:**
- 不引入 Prometheus/Grafana/OpenTelemetry 等外部可观测性基础设施
- 不实现分布式 Trace 和告警系统（后续迭代）
- 不实现实时流式监控（当前以数据库聚合查询为主）
- 不改造 agent-web 用户前端

## Decisions

### Decision 1: 两层数据采集架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     数据采集架构                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: 已有数据直接查询（无需埋点）                            │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ projects → 漏斗转化、级别分布、空间类型分布            │      │
│  │ session_messages → 对话轮数统计                       │      │
│  │ feedbacks → 纠正率、反馈标签分布、图像反馈率           │      │
│  │ stage_logs → 时间异常、子阶段溢出、端到端成功率        │      │
│  │ workflow_logs → 重试次数分布、错误类型分布             │      │
│  │ thinking_logs → 节点级执行统计                        │      │
│  │ intent_traces → 识别来源分布、置信度分布               │      │
│  └───────────────────────────────────────────────────────┘      │
│                           ↓                                     │
│  Layer 2: 新增埋点写入数据库                                     │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ ai_call_logs (新表) → LLM/VLM/Embedding/Image 调用    │      │
│  │ rag_search_logs (新表) → 知识库检索记录               │      │
│  └───────────────────────────────────────────────────────┘      │
│                           ↓                                     │
│  Admin Backend (聚合查询) → Admin Front (图表展示)               │
└─────────────────────────────────────────────────────────────────┘
```

**Rationale**: Layer 1 可立即实现且零代码侵入；Layer 2 需在 Python 侧埋点但数据更精确。分两层降低实现风险。

### Decision 2: ai_call_logs 表设计

```sql
CREATE TABLE ai_call_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(36),
    call_type ENUM('llm', 'vlm', 'embedding', 'image_generation'),
    provider VARCHAR(50),          -- zhipu / siliconflow / pollinations / comfyui / ollama
    model VARCHAR(100),            -- GLM-4.7-Flash / CogView-3 / bge-m3 等
    node_name VARCHAR(50),         -- text_parse / concept_design / image_generation 等
    status ENUM('success', 'failed', 'timeout', 'rate_limited'),
    duration_ms INT,
    input_tokens INT,              -- LLM/VLM only
    output_tokens INT,             -- LLM/VLM only
    total_tokens INT,              -- LLM/VLM only
    error_message TEXT,
    retry_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_call_type_created (call_type, created_at),
    INDEX idx_provider_created (provider, created_at),
    INDEX idx_project_id (project_id),
    INDEX idx_status_created (status, created_at)
);
```

**Rationale**: 单表存储所有 AI 调用类型，通过 `call_type` 区分。比每类一张表更灵活，查询更简单。

### Decision 3: rag_search_logs 表设计

```sql
CREATE TABLE rag_search_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(36),
    query_text TEXT,
    search_type ENUM('semantic', 'structured', 'fallback'),
    result_count INT,              -- 返回的案例/材料数
    duration_ms INT,
    cache_hit BOOLEAN DEFAULT FALSE,
    timed_out BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_search_type_created (search_type, created_at),
    INDEX idx_project_id (project_id)
);
```

### Decision 4: Python 侧埋点方式

在 `llm_client.py`、`vlm_client.py`、`embedding_client.py`、`image_generation.py` 中使用装饰器模式，在每次调用前后自动记录到 `ai_call_logs` 表。通过 HTTP API 写入 agent-api 的日志端点（避免 Python 直连 MySQL）。

```python
# 示例：LLM 调用埋点
@log_ai_call(call_type='llm')
async def complete(self, system_prompt, user_prompt, ...):
    ...
```

**Rationale**: 装饰器模式零侵入业务代码。通过 HTTP API 写入而非直连数据库，保持 Python 侧无数据库依赖。

### Decision 5: Admin 前端页面结构

```
Dashboard (重构)
├── 概览卡片（扩展至 12+ 指标）
├── 业务漏斗图（新增）
├── 阶段耗时统计（保留）
├── 反馈分布（保留）
└── 时间范围选择器（新增）

AI 模型监控（新页面）
├── 调用总量趋势（按类型分）
├── Provider 分布
├── 延迟分布（p50/p95/p99）
├── Token 用量趋势
├── 错误率 & 429 限流
└── 成本估算

图像生成监控（新页面）
├── 生成统计（成功/失败/总数）
├── Provider 分布
├── 耗时分布
├── 反馈率 & 标签分布
└── 每项目平均生成数

意图质量监控（新页面）
├── 识别来源分布
├── 置信度分布
├── 按字段纠正率
├── 对话轮数分布
└── 别名提议统计

系统健康监控（新页面）
├── 工作流成功率
├── 重试次数分布
├── 时间异常 & 子阶段溢出
├── HTTP QPS & 错误率
└── 线程池 & 连接池使用率
```

### Decision 6: intent_traces 数据读取方式

intent_traces 以 JSONL 文件存储在 `agent-core/data/intent_traces/` 目录。Admin Backend (Java) 无法直接读取 Python 文件系统。方案：在 agent-core 中新增 API 端点 `/api/v1/admin/intent-traces/stats` 返回聚合统计，Admin Backend 通过 WebClient 调用获取。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Python 埋点增加 AI 调用延迟 | 每次调用增加 ~5ms HTTP 日志写入 | 使用异步非阻塞写入，失败不阻塞主流程 |
| ai_call_logs 表增长过快 | 每天可能产生数万条记录 | 添加定时清理任务，保留 30 天明细 + 预聚合统计 |
| intent_traces 文件读取跨服务 | Java 无法直接读 Python 文件 | 通过 agent-core HTTP API 聚合查询，非直接读文件 |
| 前端图表过多导致性能下降 | 多个 ECharts 图表同时渲染 | 按页面懒加载，每页最多 6 个图表 |
| 线程池/连接池监控需 Spring Actuator | 引入新依赖 | Actuator 是 Spring Boot 原生模块，轻量级 |
