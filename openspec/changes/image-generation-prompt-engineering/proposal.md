## Why

当前文生图流程直接拼接用户输入作为 prompt，导致生成结果主体不突出、背景杂乱，难以满足商业美陈展示需求。同时系统缺乏从用户反馈中持续学习的能力，无法自动修正识别错误和优化生成效果。需要引入结构化 prompt 工程与反馈驱动的学习飞轮，提升图像生成质量和系统自适应能力。

## What Changes

- 设计并实现针对商业美陈场景的结构化 prompt 模板（主体-环境-视角-光照-风格-负向提示），优先突出空间主体、弱化背景。
- 为购物中心中庭等核心空间类型提供默认模板和可配置的负向提示词列表。
- 在图像生成链路中接入 prompt 模板引擎，根据空间类型、主题、预算等参数自动渲染 prompt。
- 构建学习飞轮基础设施：基于 `feedbacks` 表记录意图纠错和图像反馈，扩展 alias 词库、积累 few-shot 示例、支持 prompt 版本对比。
- 新增 prompt 模板版本管理和效果追踪，为后续 A/B 对比和自动优化提供数据基础。

## Capabilities

### New Capabilities
- `image-generation-prompts`: 定义商业美陈图像生成的结构化 prompt 模板、负向提示配置及模板渲染规则。
- `learning-flywheel`: 定义用户反馈收集、alias 扩展、few-shot 示例库和 prompt 版本学习的机制。

### Modified Capabilities
- `intent-recognition`: 补充学习飞轮所需的意图纠错反馈字段和别名学习接口。

## Impact

- `agent-core` 图像生成服务（`app/services/image_generation.py` 及相关 prompt 渲染逻辑）。
- `agent-api` 的反馈接口和数据库 `feedbacks` 表。
- 新增配置和模板文件：`agent-core/data/prompt_templates/`、`agent-core/data/negative_prompts/`。
- 可能依赖的外部服务：SiliconFlow FLUX.1-schnell、Pollinations.AI。
