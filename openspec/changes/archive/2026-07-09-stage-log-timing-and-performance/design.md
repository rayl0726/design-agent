## Context

`StageLog` 表和 `StageLogService` 已经落地，可在每个工作流节点前后打点记录耗时。实际运行中出现了部分 `duration_ms` 为负数的情况，导致：
- 无法判断该阶段真实耗时。
- 汇总平均/P95 延迟时数据失真。
- 难以定位真正拖慢整个生成流程的模块。

当前 `visual_design` 阶段内部包含图片生成、LLM 创意生成、知识检索等多个子步骤，但这些子步骤耗时黑盒化，无法判断是“图片生成慢”还是“LLM 调用慢”。

## Goals / Non-Goals

**Goals:**
- 根查并修复 `duration_ms` 为负数的问题，使用单调时钟计算耗时。
- 在耗时大阶段内部增加子阶段（sub-stage）日志，细化到图片生成、LLM 调用、知识检索等。
- 保证父阶段耗时大于等于子阶段耗时之和，发现不一致时标记异常。
- 提供按阶段/子阶段的性能汇总能力（平均耗时、P95、失败率）。
- 基于汇总数据给出可执行的优化建议，支持单阶段阈值和跨阶段关联分析。
- 确保日志写入不影响主工作流性能；统计分析走异步预聚合。
- 修复历史负数耗时记录。

**Non-Goals:**
- 不替换现有的 `workflow_logs` 表。
- 不改写图片生成或 LLM 模型本身，只提供优化建议。
- 不引入外部 APM 系统（如 SkyWalking、Jaeger）。

## Decisions

1. **负数 duration 根因与修复**
   - 根因：当前使用 `LocalDateTime.now()` 计算 `started_at` / `completed_at`，再用 `ChronoUnit.MILLIS.between` 求 duration；系统时间回拨或并发重复完成会导致负数。
   - 修复：
     - `StageLogService` 在 `startStage` 时记录 `System.nanoTime()` 到内存 `Map<Long, Long> startNanos`（或新增持久化字段 `started_nanos`）。
     - `completeStage` / `failStage` 时从 `startNanos` 计算 duration，写入 `duration_ms`。
     - 增加幂等校验：仅 `RUNNING` 状态可过渡到 `SUCCESS` / `FAILED`；重复调用直接返回已持久化记录。
     - 若计算结果 < 0，置 `duration_ms = null` 并标记 `time_anomaly = true`。
   - `started_at` / `completed_at` 仍用 `LocalDateTime` 保存，仅用于展示，不参与 duration 计算。

2. **子阶段设计与时间完整性**
   - `StageLog` 表已有 `parent_id` 字段，用于支持父子阶段。
   - 在 `WorkflowEngine.runNode` 内部，根据节点类型拆分子阶段：
     - `visual_design`: `image_generation`（每张图或批量）、`idea_rendering`、`color_material_board`。
     - `technical_design`: `layout_rendering`、`cost_estimation`。
     - `knowledge_retrieve`: `semantic_search`、`summary_generation`。
   - 子阶段日志统一走 `StageLogService`，前端默认折叠，可展开查看。
   - 父阶段完成时校验：若存在子阶段，要求 `parent.duration_ms >= sum(sub.duration_ms)`；否则标记 `sub_stage_overflow = true`。

3. **性能统计服务**
   - 新增 `stage_log_stats` 表，字段：`stage_name`、`window_start`、`window_end`、`avg_ms`、`p95_ms`、`max_ms`、`success_count`、`failed_count`。
   - 新增 `StageLogAnalyticsService`：
     - 定时任务每分钟从 `stage_logs` 聚合最近 1 小时/24 小时数据写入 `stage_log_stats`。
     - 提供 API `/api/v1/analytics/stages`（读预聚合数据）。
     - 提供 API `/api/v1/analytics/stages/{stageName}`（单阶段详情）。
     - 提供 API `/api/v1/projects/{publicId}/analytics`（单次会话全链路耗时）。
   - 复杂统计走预聚合，避免实时扫大表。

4. **优化建议引擎**
   - 基于规则引擎：
     - `visual_design` avg > 60s → 建议“图片并行生成”或“降低并发/换供应商”。
     - `knowledge_retrieve` p95 > 30s → 建议“增加超时保护”和“缓存知识库”。
     - 某阶段失败率 > 10% → 建议“增加降级策略”。
   - 新增关联分析：
     - 若 `knowledge_retrieve` 慢 + `visual_design` 慢 → 优先优化知识库缓存（LLM prompt 过长导致图片生成慢）。
     - 若只有 `image_generation` 子阶段慢 → 建议换图片供应商或调整并发。
     - 若 `semantic_search` 慢但 `summary_generation` 不慢 → 建议向量库/索引优化。
   - 建议结果写入 `stage_logs.metadata_json` 或在汇总接口返回。

5. **异步解耦**
   - `StageLogService` 的写操作本身已是同步 DB 写入，但数据量小、单条插入，影响可忽略。
   - 统计分析、预聚合、推荐生成走独立线程池或定时任务，不阻塞工作流线程。

6. **历史数据修复**
   - 上线前执行一次性 Flyway 脚本或运维脚本：
     - 将 `duration_ms < 0` 的记录置为 `null`。
     - 设置 `time_anomaly = true`。
   - 上线后第一周每天告警 `time_anomaly` 数量，确认修复生效。

## Risks / Trade-offs

- **[Risk] 修复负数 duration 后仍偶发** → 增加 `duration_ms < 0` 的告警/补偿逻辑：置为 null 并标记 `time_anomaly`。
- **[Risk] 子阶段过多导致日志表膨胀** → 仅对定义为“耗时节点”的 stage 开启子阶段；增加按 retention 清理策略。
- **[Risk] 子阶段之和超过父阶段** → 增加 `sub_stage_overflow` 标记，用于排查漏记或并发计时问题。
- **[Trade-off] 统计查询可能影响 DB 性能** → 对 `stage_logs(project_id, stage_name, status, started_at)` 增加复合索引；复杂统计走 `stage_log_stats` 预聚合。

## Migration Plan

- 阶段 1：修复 `StageLogService` 计时逻辑，增加幂等校验和 `time_anomaly` 标记；执行历史负数数据修复脚本。
- 阶段 2：在 `WorkflowEngine` 中为 `visual_design`、`technical_design`、`knowledge_retrieve` 增加子阶段打点，并校验父阶段时间完整性。
- 阶段 3：新增 `stage_log_stats` 表、`StageLogAnalyticsService`、汇总接口和前端慢阶段提示。
- 阶段 4：实现关联分析推荐引擎，基于真实数据输出第一批优化建议并落地（如图片并行化、知识检索缓存）。
- 回滚：若子阶段日志影响性能，可通过配置 `stage.sub-stage.enabled=false` 关闭子阶段记录。

## Open Questions

- 是否将 `duration_ms` 字段类型改为 `BIGINT` 并允许 NULL，以区分“未完成”和“异常”？
- 性能汇总接口是否需要权限控制（仅管理员）？
- 单调时钟时间戳是保存在内存 Map 中，还是新增 `started_nanos` 持久化字段？
