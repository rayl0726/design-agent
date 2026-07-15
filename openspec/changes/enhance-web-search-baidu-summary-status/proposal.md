## Why

当前通用 Agent 的 `web_search` 仅调用 Bing，返回最多 5 条标题+摘要，无法对网页正文做综合总结；用户也无法感知搜索和总结的执行进度，容易以为页面卡住。为了提升回答质量与交互体验，需要支持多源搜索、正文摘要，并在工具卡片中展示实时状态。

## What Changes

- 扩展 `WebSearchTool`，新增 Baidu 搜索结果源，与 Bing 并行搜索后合并去重。
- 对 Top 3 条结果抓取网页正文，失败时 fallback 到搜索摘要。
- 调用 LLM 对正文/摘要进行综合总结，生成一段中文回答并保留来源链接。
- 新增 SSE `tool_progress` 事件，在搜索、总结阶段向前端推送状态。
- 前端工具卡片支持“搜索中... / 总结中... / 已完成”状态切换。
- 百度结果增加广告过滤：按广告标签、链接域名黑名单、文本标记剔除推广条目。

## Capabilities

### New Capabilities
- `web-search`: 多源网页搜索、广告过滤、正文抓取与 LLM 综合总结。
- `generic-agent-tool-status`: 通用 Agent 工具执行过程中的实时状态反馈（搜索中/总结中/已完成）。

### Modified Capabilities
- 无现有 spec 需求变更。

## Impact

- `agent-core/app/tools/web_search.py`：核心搜索、抓取、摘要逻辑。
- `agent-core/app/runtime/tool.py`（可选）：为 `ToolContext` 增加状态发射能力。
- `agent-core/app/api/routers.py`：`/agents/{agent_id}/run` SSE 增加 `tool_progress` 转发。
- `agent-api/src/main/java/.../GenericAgentHandler.java`：解析并转发 `tool_progress` 事件。
- `agent-web/src/views/ChatView.vue`：监听 `tool_progress`，更新工具卡片状态。
- 新增/调整前后端单元测试与集成测试。
