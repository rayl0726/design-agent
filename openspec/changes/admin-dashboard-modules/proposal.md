## Why

随着系统运行，用户反馈、意图纠错、图像生成效果和 prompt 模板映射关系等数据不断累积，但当前缺少一个统一的可视化后台来查看和管理这些信息。管理员无法直观了解系统指标、用户反馈分布以及 prompt 模板与实际生成效果之间的关联。需要新增独立的 Admin 前后台模块，为运营和算法优化提供操作界面。

## What Changes

- 新增 `agent-admin-backend` Spring Boot 模块，提供管理后台 API：用户反馈管理、系统指标、prompt 模板管理、意图词库管理。
- 新增 `agent-admin-front` 前端模块，使用 React/Vue 构建管理后台页面。
- Admin 后台通过只读/读写接口访问现有 `agent-api` 数据库，不改动现有业务表结构。
- 提供 prompt 模板与生成图像、反馈之间的映射视图，帮助管理员识别效果差的模板版本。
- 提供意图词库管理界面，支持查看、添加和审核由学习飞轮提议的别名。

## Capabilities

### New Capabilities
- `admin-feedback-management`: 后台查看和处理用户反馈（意图纠错、图像反馈）。
- `admin-system-metrics`: 后台查看系统整体指标（项目数、生成图像数、反馈分布、阶段耗时等）。
- `admin-prompt-template-management`: 后台查看 prompt 模板版本及其与反馈的关联。
- `admin-intent-lexicon-management`: 后台查看和编辑意图词库及别名提议。

### Modified Capabilities
- 无

## Impact

- 新增 Maven/Gradle 模块 `agent-admin-backend` 和前端目录 `agent-admin-front`。
- 可能新增 `agent-admin-backend` 依赖：Spring Boot Web、Spring Data JPA、Spring Security（可选）。
- `agent-admin-front` 依赖：Vite + React（或 Vue）+ UI 组件库。
- 需要与 `agent-api` 共享数据库只读访问或提供内部 API。
