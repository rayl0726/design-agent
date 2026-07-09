## Why

已落地的阶段日志系统出现了部分记录耗时为负数的问题，导致无法准确判断各模块真实耗时。同时，日志目前仅记录阶段状态，缺少对慢模块的定位能力和可执行的加速优化建议。需要修正计时逻辑，并让阶段日志直接服务于性能优化决策。

## What Changes

- 修复 `StageLog` 计时字段计算逻辑，消除负数 duration 的根因（时区/并发/重复完成等）。
- 在阶段日志中增加子阶段拆分，尤其是在 `visual_design`/`technical_design` 等耗时节点内记录图片生成、LLM 调用、知识检索等子步骤耗时。
- 新增性能汇总接口/视图，按阶段汇总平均耗时、失败率、P95 延迟。
- 基于阶段日志数据，为每个慢阶段自动生成或推荐优化策略（如并行化、缓存、超时、降级）。
- 将阶段日志持久化与异步统计解耦，避免日志写入影响工作流性能。

## Capabilities

### New Capabilities
- `stage-log-performance`: 阶段日志的计时修正、子阶段拆分、性能汇总与慢节点优化建议。

### Modified Capabilities
- （无现有 spec 级别的需求变更；计时修正和子阶段打点属于当前 `stage-log` 能力的实现完善。）

## Impact

- `agent-api` 的 `StageLogService`、`WorkflowEngine`、`StageLogController`。
- `agent-api` 新增性能分析服务与统计接口。
- `agent-web` 的「日志」抽屉增加子阶段展开和慢阶段提示。
- 可能新增数据库索引（按 project_id + stage_name + started_at）以支持汇总查询。
