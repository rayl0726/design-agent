## Context

当前系统包含 `agent-api`（Spring Boot）和 `agent-core`（Python FastAPI），以及前端 `agent-front`（Vite）。管理员需要查看用户反馈、系统指标和 prompt 模板效果，但现有模块没有提供这些管理功能。新增独立的 `agent-admin-backend` 和 `agent-admin-front` 模块，可以在不污染现有业务代码的前提下提供后台能力。

## Goals / Non-Goals

**Goals:**
- 提供反馈管理后台，支持查看、筛选和标记处理状态。
- 提供系统指标看板，展示项目、图像、反馈、阶段耗时等关键指标。
- 提供 prompt 模板管理，展示模板版本与图像反馈的关联。
- 提供意图词库管理，支持查看别名提议并应用到 `intent_taxonomy.yaml`。

**Non-Goals:**
- 不实现复杂的 RBAC 权限系统，初期仅支持简单的登录/密码或本地访问。
- 不替代现有 `agent-api` 的业务接口，Admin 后台只读或内部管理写入。
- 不自动部署，本变更只提供可运行的前后端模块。

## Decisions

- **Admin 后端作为独立 Spring Boot 模块**：与 `agent-api` 解耦，避免互相影响启动和依赖。
- **Admin 后端直接连接现有 MySQL 数据库只读查询**：复用已有数据，减少同步成本；写操作通过内部 API 或文件系统完成（如 alias 写入 taxonomy YAML）。
- **前端使用 React + Vite**：与现有 `agent-front` 技术栈保持一致，降低维护成本。
- **Prometheus/Spring Boot Actuator 作为指标来源**：系统指标优先复用 Spring Boot 原生端点，自定义指标后续补充。
- **意图词库编辑以 YAML 文件为目标**：alias 提议经审核后写回 `agent-core/data/intent_taxonomy.yaml`，并触发重新加载。

## Risks / Trade-offs

- [Admin 后端直接连生产库存在误写风险] → 只读数据源为主，写操作通过显式管理端点并记录审计日志。
- [前端与 agent-api 认证体系不一致] → 初期使用独立简单登录，后续可接入统一认证。
- [YAML 编辑可能破坏 taxonomy 格式] → 使用 PyYAML/ruamel.yaml 保留格式并验证后写入。

## Migration Plan

1. 创建 `agent-admin-backend` 和 `agent-admin-front` 目录及基础脚手架。
2. 配置数据库连接指向现有 MySQL 实例（只读账号）。
3. 实现核心管理页面并对接后端 API。
4. 本地验证后合并到 main。

## Open Questions

- Admin 前端是否复用 `agent-front` 的组件库和路由？
- 是否需要一个独立的 Admin 数据库用户，还是复用现有 `meichen` 用户但限制权限？
