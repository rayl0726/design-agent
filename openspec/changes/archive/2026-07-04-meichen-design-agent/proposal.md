## Why

美陈设计（商业空间视觉陈列设计）方案产出过程高度依赖设计师个人经验，从需求理解、案例检索、概念构思到效果图生成、物料清单编制，环节多、周期长（通常 3-7 天）。对于乙方设计公司而言，高频次的方案投标需要快速响应，但人力成本限制了出案速度和方案数量。需要一个 AI Agent 系统来辅助美陈设计师，将方案产出时间从数天压缩到数小时，同时通过知识库检索提升方案的专业性和可参考性。

## What Changes

- 构建一个以商场购物中心为主、覆盖快闪/展览场景的美陈设计 Agent 系统。
- 系统采用分层递进输出：L1 概念方向 → L2 视觉方案 → L3 可落地方案。
- 支持多模态输入：场地平面图/CAD、现场照片/视频、参考图、文本需求（预算、主题、人群、工期、材料限制）。
- 输出三种交付格式：HTML 预览、PPT（甲方汇报）、PDF 归档。
- 内置 RAG 知识库：设计案例库（案例故事、设计手法、材料工艺）+ 材料价格库（历史参考价，可选对接 1688）。
- 图像生成采用免费/低成本方案：Pollinations.AI 为主力，本地 ComfyUI 为备选。
- LLM 采用免费/本地优先策略：Ollama 本地部署 Qwen2.5 + bge-m3 embedding，降低验证期成本至零。

## Capabilities

### New Capabilities
- `input-parser`: 多模态输入解析。处理现场照片（VLM 分析空间尺度/装饰）、CAD/DWG 图纸解析（提取轮廓/柱网）、参考图风格分析、文本需求结构化提取。
- `requirement-analyst`: 需求分析 Agent。将非结构化输入转化为标准化设计需求（JSON Schema），包含预算档次、主题关键词、空间类型、目标人群、材料限制、工期约束。
- `knowledge-retrieval`: RAG 知识检索。基于向量检索相似案例 + 结构化查询材料价格/工艺参数/项目模板，输出检索摘要供后续 Agent 使用。
- `concept-designer`: L1 概念设计 Agent。输出设计主题故事、氛围描述、Moodboard（6-9 张参考图）。
- `visual-designer`: L2 视觉方案 Agent。基于 L1 概念生成 AI 概念效果图（2-3 张）+ 色彩材质板（1 张）。
- `technical-designer`: L3 可落地方案 Agent。基于 CAD 轮廓做 AI 平面点位标注、生成物料清单（材料/尺寸/工艺/数量/参考价）、生成预算汇总表。
- `doc-generator`: 文档生成器。将方案内容渲染为 HTML（预览）、PPT（python-pptx 模板化生成）、PDF（HTML 转 PDF）。
- `image-generation`: 图像生成服务。抽象层封装 Pollinations.AI 和本地 ComfyUI，支持 Moodboard/概念图/材质板生成。

### Modified Capabilities
- 无。本项目为全新系统，无现有 spec 需要修改。

## Impact

- 新增 FastAPI 后端服务，提供方案生成工作流的 HTTP API。
- 引入 LangGraph 作为 Agent 编排框架，管理 L1→L2→L3 的状态流转和人工确认节点。
- 引入 Chroma（本地）作为向量数据库，存储案例文本和图像描述的 Embedding。
- 引入 SQLite 作为结构化数据库，存储材料价格、物料清单模板、项目元数据。
- 本地部署 Ollama 运行 Qwen2.5（文本推理）、Qwen2.5-VL（图像理解）、bge-m3（文本嵌入）。
- 外部依赖：Pollinations.AI（免费图像生成，HTTP 调用）。
- 前端（二期）：React + Tailwind 的可视化方案编辑器，本期仅输出静态文档。
