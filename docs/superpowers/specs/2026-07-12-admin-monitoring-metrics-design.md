# Admin 监控指标增强设计

## 背景

当前 Admin 后台仅有 6 个概览指标和 2 个图表（阶段耗时 + 反馈分布），远低于业界 AI Agent 可观测性标准。系统缺少 AI 模型调用监控、业务漏斗转化、系统基础设施健康等关键指标，导致运营和算法团队无法及时发现性能退化和质量下滑。

## 目标

将监控指标覆盖率从 15% 提升到 70%+，聚焦 3 类高价值指标（MVP）：
1. **业务漏斗** — 项目状态流转、完成率、对话轮数、维度分布
2. **AI 模型调用** — LLM/VLM/Embedding/Image 调用量、延迟、Token、错误率
3. **系统健康** — 工作流成功率、重试、异常、HTTP QPS、线程池、DB 连接池

## 非目标

- 不引入 Prometheus/Grafana/OpenTelemetry 等外部可观测性基础设施
- 不实现分布式 Trace 和告警系统
- 不实现实时流式监控
- 不覆盖图像生成反馈分析、意图质量、知识库 RAG 指标（后续迭代）

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 实现策略 | MVP 优先 + 纵向切片 | 聚焦 3 类高价值指标，每个 Sprint 端到端可交付 |
| Python 埋点方式 | HTTP 异步 fire-and-forget | 零 DB 依赖，失败不阻塞主流程，每次调用增加 ~5ms |
| 数据保留 | 30 天明细 + 每日预聚合 | 平衡查询性能和存储成本，30 天足够发现趋势 |
| 系统健康范围 | 全量（含 Actuator + HTTP 拦截） | 线程池/连接池/HTTP 是系统健康的核心指标 |
| 前端图表库 | ECharts（已有依赖） | 无需引入新依赖，支持漏斗图/仪表盘/热力图 |

## 架构

```
agent-admin-front (Vue, :8082)
├── Dashboard (增强: 12卡片 + 漏斗图 + 趋势图 + 时间选择器)
├── AiModelMonitoring.vue (新页面)
└── SystemHealth.vue (新页面)
        │
        │ /api/admin/metrics/*
        ▼
agent-admin-backend (Java, :8081)
├── BusinessFunnelService (查询 projects + session_messages)
├── AiModelMetricsService (查询 ai_call_logs + ai_call_daily_stats)
├── SystemHealthService (查询 stage_logs + workflow_logs + http_request_logs + Actuator)
        │
        │ WebClient → Actuator
        ▼
agent-api (Java, :8080)
├── InternalLogController (POST /api/v1/internal/ai-call-logs)
├── HttpRequestLogFilter (拦截所有请求 → http_request_logs)
├── Spring Boot Actuator (暴露线程池/HikariCP 指标)
└── @Scheduled (每日聚合 + 30天清理)
        │
        │ HTTP async POST
        ▼
agent-core (Python, :8000)
├── @log_ai_call('llm') → LLMClient
├── @log_ai_call('vlm') → ZhipuVLMClient
├── @log_ai_call('embedding') → EmbeddingClient
└── @log_ai_call('image_gen') → ImageGenerationService
```

## Sprint 1: 业务漏斗指标

**数据源**: projects + session_messages（已有表，零埋点）

### API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/admin/metrics/funnel?days=30` | 项目漏斗: draft→generating→completed 转化率 |
| `GET /api/admin/metrics/funnel/abandonment?days=7` | 超 7 天未活动的 draft 项目 |
| `GET /api/admin/metrics/funnel/levels` | L1/L2/L3 级别分布和转化率 |
| `GET /api/admin/metrics/funnel/duration?days=30` | 完成项目耗时统计 (avg/median/p90/max) |
| `GET /api/admin/metrics/conversations?days=30` | 对话轮数统计 (avg/median/max + 分布) |
| `GET /api/admin/metrics/dimensions/space-type` | 按空间类型项目分布 |
| `GET /api/admin/metrics/dimensions/budget-level` | 按预算等级项目分布 |
| `GET /api/admin/metrics/dimensions/style` | 按风格项目分布 |
| `GET /api/admin/metrics/trend/projects?days=30` | 每日项目创建趋势 |

### 前端变更

Dashboard.vue 增强：
- 新增时间范围选择器 (24h/72h/7d/30d)
- 概览卡片从 6 个扩展到 12 个
- 新增项目漏斗图 (ECharts funnel)
- 新增项目创建趋势折线图

### 任务数: ~15 个

## Sprint 2: AI 模型调用指标

### 数据库变更

**ai_call_logs 表** (明细):

| 列名 | 类型 | 说明 |
|------|------|------|
| id | BIGINT AUTO_INCREMENT | 主键 |
| project_id | VARCHAR(36) | 关联项目 |
| call_type | ENUM('llm','vlm','embedding','image_gen') | 调用类型 |
| provider | VARCHAR(50) | zhipu/siliconflow/pollinations/comfyui/ollama |
| model | VARCHAR(100) | GLM-4.7-Flash/CogView-3/bge-m3 等 |
| node_name | VARCHAR(50) | text_parse/concept_design/image_generation 等 |
| status | ENUM('success','failed','timeout','rate_limited') | 调用状态 |
| duration_ms | INT | 耗时(毫秒) |
| input_tokens | INT | 输入 Token (LLM/VLM only) |
| output_tokens | INT | 输出 Token (LLM/VLM only) |
| total_tokens | INT | 总 Token |
| error_message | TEXT | 错误信息 |
| retry_count | INT DEFAULT 0 | 重试次数 |
| created_at | DATETIME | 创建时间 |

索引: (call_type, created_at), (provider, created_at), (project_id), (status, created_at)

**ai_call_daily_stats 表** (预聚合):

| 列名 | 类型 | 说明 |
|------|------|------|
| stat_date | DATE | 统计日期 |
| call_type | ENUM | 调用类型 |
| provider | VARCHAR(50) | Provider |
| total_calls | INT | 总调用数 |
| success_calls | INT | 成功数 |
| failed_calls | INT | 失败数 |
| rate_limited_calls | INT | 限流数 |
| avg_duration_ms | INT | 平均延迟 |
| p95_duration_ms | INT | P95 延迟 |
| total_input_tokens | BIGINT | 输入 Token 总量 |
| total_output_tokens | BIGINT | 输出 Token 总量 |

唯一键: (stat_date, call_type, provider)

### Python 埋点

`app/services/call_logger.py` 实现 `@log_ai_call(call_type)` 装饰器：
- 在 `finally` 块中通过 `asyncio.create_task()` 异步发送 HTTP POST
- 超时 3 秒，异常静默丢弃
- 从函数返回值提取 Token 信息
- 从异常类型推断 status (rate_limited/timeout/failed)

应用到 4 个 Service:
- `LLMClient.complete()` / `LLMClient.stream()` → `@log_ai_call('llm')`
- `ZhipuVLMClient.describe()` / `describe_batch()` → `@log_ai_call('vlm')`
- `EmbeddingClient.embed()` / `embed_batch()` → `@log_ai_call('embedding')`
- `ImageGenerationService.generate()` → `@log_ai_call('image_gen')`

### agent-api 内部端点

- `POST /api/v1/internal/ai-call-logs` — 接收 Python 上报，无认证
- `@Scheduled(cron="0 0 2 * * *")` — 每日凌晨 2:00 聚合前一天数据 + 删除 30 天前明细

### Admin API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/admin/metrics/ai-calls/summary?hours=24` | 按 call_type 分组统计 |
| `GET /api/admin/metrics/ai-calls/by-provider?hours=24` | 按 provider 分组统计 |
| `GET /api/admin/metrics/ai-calls/timeline?hours=168` | 时间序列 |
| `GET /api/admin/metrics/ai-calls/tokens?hours=168` | Token 用量 + 成本估算 |

### 前端

新建 `AiModelMonitoring.vue`:
- 调用概览卡片 (LLM/VLM/Embedding/Image 各类调用量 + 成功率)
- 调用趋势折线图 (按小时/天)
- Provider 分布饼图
- 延迟分布柱状图 (p50/p95/p99)
- Token 用量折线图 + 成本估算
- 错误分析表格

### 任务数: ~18 个

## Sprint 3: 系统健康指标（全量）

### 数据库变更

**http_request_logs 表**:

| 列名 | 类型 | 说明 |
|------|------|------|
| id | BIGINT AUTO_INCREMENT | 主键 |
| method | VARCHAR(10) | HTTP 方法 |
| path_pattern | VARCHAR(200) | 路径模式 (如 /api/v1/projects/{id}) |
| status_code | INT | HTTP 状态码 |
| duration_ms | INT | 响应耗时 |
| created_at | DATETIME | 创建时间 |

索引: (path_pattern, created_at), (status_code, created_at)

### agent-api 改造

1. **Spring Boot Actuator** 依赖引入，暴露 `/actuator/metrics/` 和 `/actuator/health`
2. **HttpRequestLogFilter** (OncePerRequestFilter):
   - 拦截 `/api/v1/*` 请求
   - 记录 method/path_pattern/status_code/duration_ms
   - 异步写入 http_request_logs 表
   - 排除 `/actuator/*`、`/images/*`、`/data/*`
3. **线程池指标注册** 到 Actuator MeterRegistry

### Admin API 端点

| 端点 | 数据源 | 说明 |
|------|--------|------|
| `GET /api/admin/metrics/system/workflow-success?days=7` | stage_logs | 工作流成功率 + 失败点分布 |
| `GET /api/admin/metrics/system/retries?days=7` | workflow_logs | 重试次数分布 (按 node) |
| `GET /api/admin/metrics/system/errors?days=7` | workflow_logs | 错误类型分布 (按 node + category) |
| `GET /api/admin/metrics/system/anomalies?days=7` | stage_logs | 时间异常 + 子阶段溢出 |
| `GET /api/admin/metrics/system/http?hours=1` | http_request_logs | HTTP QPS + 错误率 + 响应时间 |
| `GET /api/admin/metrics/system/thread-pools` | Actuator | 线程池使用率 |
| `GET /api/admin/metrics/system/db-pool` | Actuator | HikariCP 连接池状态 |

### 前端

新建 `SystemHealth.vue`:
- 工作流成功率仪表盘 + 失败点 TOP 5 表格
- 重试分布热力图 (节点×重试次数)
- 异常事件卡片 + 受影响阶段排名表
- HTTP QPS/错误率/p95 折线图
- 线程池仪表盘×2 (workflowExecutor + dialogueExecutor)
- DB 连接池状态卡片

### 任务数: ~16 个

## 数据流

```
Sprint 1 (纯查询):
  projects/session_messages → Admin Backend SQL → Admin Front 图表

Sprint 2 (埋点+查询):
  Python AI 调用 → @log_ai_call 装饰器 → HTTP POST → agent-api → ai_call_logs
  ai_call_logs → @Scheduled 聚合 → ai_call_daily_stats
  ai_call_logs/ai_call_daily_stats → Admin Backend SQL → Admin Front 图表

Sprint 3 (Actuator+拦截+查询):
  HTTP 请求 → HttpRequestLogFilter → http_request_logs
  stage_logs/workflow_logs → Admin Backend SQL → 图表
  agent-api Actuator → Admin Backend WebClient → 图表
```

## 错误处理

- Python `_send_log()` 失败时静默丢弃，不影响 AI 调用主流程
- agent-api InternalLogController 写入失败时记录 ERROR 日志，返回 500（Python 侧忽略）
- Admin Backend WebClient 调用 Actuator 失败时返回缓存的上次值或空对象
- HTTP Filter 写入失败时仅记录日志，不阻塞 HTTP 响应

## 测试策略

- Python: 单元测试 `@log_ai_call` 装饰器，验证各状态（success/failed/timeout/rate_limited）的记录正确性
- Java: 集成测试每个 Admin API 端点，使用 @SpringBootTest + H2 内存数据库
- 前端: 端到端测试 3 个页面渲染，验证图表加载无报错
- 性能: 验证 ai_call_logs 10 万行时查询 < 500ms

## 实现顺序

```
Sprint 1 (2-3天) → Sprint 2 (4-5天) → Sprint 3 (3-4天)
总计: ~9-12 天
```

每个 Sprint 完成后端 + 前端，可独立交付和验证。
