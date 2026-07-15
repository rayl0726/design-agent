## 1. agent-core 搜索能力扩展

- [ ] 1.1 重构 `WebSearchTool`，拆分 Bing/Baidu 搜索客户端与结果解析器
- [ ] 1.2 实现 Baidu 搜索结果解析与广告过滤（标签/域名/文本）
- [ ] 1.3 实现 Bing 与 Baidu 结果合并、URL 与标题去重
- [ ] 1.4 实现 Top 3 结果正文并发抓取与超时 fallback
- [ ] 1.5 实现 LLM 综合摘要生成与来源链接输出
- [ ] 1.6 在 `ToolContext` 中增加 `emit` 能力，支持 `tool_progress` 事件
- [ ] 1.7 在 `/agents/{agent_id}/run` 中转发 `tool_progress` SSE

## 2. agent-api 状态事件转发

- [ ] 2.1 `GenericAgentHandler` 增加 `tool_progress` 事件解析与转发
- [ ] 2.2 `SseEmitterService` 确认支持 `tool_progress` 推送
- [ ] 2.3 添加 `GenericAgentHandlerTest` 覆盖 `tool_progress` 转发

## 3. 前端工具状态展示

- [ ] 3.1 `ChatView.vue` 监听 `tool_progress` 事件并更新对应工具卡片状态
- [ ] 3.2 工具卡片支持“搜索中... / 总结中... / 已完成”动态状态
- [ ] 3.3 确保切换会话后工具卡片状态不丢失或错乱
- [ ] 3.4 更新/新增前端组件单元测试

## 4. 测试与验证

- [ ] 4.1 agent-core 单元测试：Baidu 广告过滤、去重、摘要 fallback
- [ ] 4.2 agent-core 集成测试：完整搜索→摘要流程
- [ ] 4.3 本地启动后通过浏览器验证 Bing+Baidu 搜索、状态展示、摘要输出
