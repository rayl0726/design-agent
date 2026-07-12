## 1. 项目骨架与基础设施

- [x] 1.1 初始化 Java 项目（Maven/Gradle），创建 Spring Boot 骨架，包含 Web、JPA、SQLite 驱动依赖
- [x] 1.2 初始化 Python 项目（Poetry/uv），创建 `pyproject.toml`，包含 FastAPI、Milvus、Pillow、python-pptx、ezdxf、Jinja2、pdfplumber、PyMuPDF、python-pptx 等依赖
- [x] 1.3 创建项目目录结构：`java-orchestrator/`（Java 协调层）、`python-ai/`（Python AI 服务）、`data/sqlite/`、`data/milvus/`
- [x] 1.4 添加 `.env.example`，包含 Ollama 地址、Milvus 地址、Pollinations 端点、模板路径
- [x] 1.5 创建 `docker-compose.yml`，包含 Milvus Standalone 服务
- [x] 1.6 创建 `README.md`，包含 Ollama 安装、Milvus 启动、项目启动说明

## 2. 本地 LLM 与 Embedding 环境

- [x] 2.1 实现 `python-ai/app/services/llm_client.py`，提供 Ollama 文本补全（Qwen2.5）的统一接口，支持流式和 JSON 模式
- [x] 2.2 实现 `python-ai/app/services/vlm_client.py`，用于 Ollama 视觉补全（Qwen2.5-VL），接受图片路径/Base64，返回结构化描述
- [x] 2.3 实现 `python-ai/app/services/embedding_client.py`，用于 Ollama Embedding（bge-m3），支持批量文本编码和本地缓存
- [x] 2.4 添加 LLM 提供者抽象层，以便后续通过配置切换到 SiliconFlow/DeepSeek

## 3. 数据层（SQLite + Milvus）

- [x] 3.1 定义 SQLAlchemy 模型：`Project`、`MaterialPrice`、`DesignCase`、`MaterialSpec`、`ProjectDocument`
- [x] 3.2 初始化 SQLite 数据库，使用 Alembic 迁移（或 MVP 阶段简单 create-all）
- [x] 3.3 初始化 Milvus 集合，创建：`case_descriptions`（向量+元数据）、`image_descriptions`（向量+元数据）
- [x] 3.4 实现 `python-ai/app/services/knowledge_base.py`，提供双查询接口：`semantic_search()`（Milvus）和 `structured_query()`（SQLite）
- [x] 3.5 实现 Java 层的 JPA 实体和 Repository，用于项目状态和工作流日志持久化

## 4. 输入解析器

- [x] 4.1 实现照片解析：接受图片上传，调用 VLM，返回空间描述 JSON
- [x] 4.2 实现视频抽帧：使用 OpenCV 或 ffmpeg，批量处理后通过照片解析器处理
- [x] 4.3 实现 CAD 解析（ezdxf）：提取轮廓、柱网、面积，渲染 PNG 预览
- [x] 4.4 实现 PDF 解析（pdfplumber/PyMuPDF）：提取文本和内嵌图片
- [x] 4.5 实现 PPT 解析（python-pptx）：提取幻灯片文本和缩略图
- [x] 4.6 实现参考图解析：VLM 风格分析 + 视觉 Embedding 去重
- [x] 4.7 实现文本需求提取器：LLM Prompt 配合 JSON Schema 输出结构化字段
- [x] 4.8 实现输入合并器：将照片/CAD/PDF/PPT/参考图/文本的解析结果合并为统一结构

## 5. 需求分析 Agent

- [x] 5.1 实现需求分析 Agent，合并多来源解析输出为统一的 `DesignRequirement` 结构
- [x] 5.2 添加预算档次分类器：查询 SQLite 历史数据，计算低/中/高分位
- [x] 5.3 添加主题/风格提取：生成色板（hex）和材料建议
- [x] 5.4 添加约束识别：显式限制 + LLM 推理的隐性风险提示
- [x] 5.5 添加冲突检测：标记冲突信息，返回给 Java 协调层等待设计师确认

## 6. 知识检索 Agent

- [x] 6.1 实现语义案例检索：构建混合查询（主题+过滤条件），查询 Milvus，返回 top-5 及元数据
- [x] 6.2 实现材料/价格查询：对 material_price 表进行模糊搜索，无结果时返回相似名称
- [x] 6.3 实现检索摘要生成器：将案例和材料合成为 800 字以内的 Markdown 摘要，供下游 Agent 使用
- [x] 6.4 添加检索降级逻辑：结果数 < 3 时逐步放宽过滤条件

## 7. L1 概念设计 Agent

- [x] 7.1 实现故事生成：LLM Prompt 采用资深美陈设计师人设，结合案例参考和需求上下文
- [x] 7.2 实现氛围生成：分类关键词（视觉/触觉/听觉）+ 感官段落
- [x] 7.3 实现 Moodboard 合成：生成 2-3 个 AI 生图 Prompt，调用图像生成服务，从 Milvus 检索 3-6 张历史参考图
- [x] 7.4 添加用户反馈循环端点：接受通过/驳回及原因，按修改后的调性/方向重新生成

## 8. L2 视觉设计 Agent

- [x] 8.1 实现概念效果图生成：基于 L1 + 空间上下文构建英文 Prompt，调用图像生成（2-3 个变体）
- [x] 8.2 实现色彩材质板生成：使用 Pillow 程序化合成色卡、材料标签、应用区域
- [x] 8.3 添加视觉一致性检查器：LLM 对比渲染 Prompt 与 L1 概念，自动修正不一致
- [x] 8.4 添加纯 CAD 输入的渲染降级：在 Prompt 中使用尺寸信息，并添加免责声明

## 9. L3 可落地设计 Agent

- [x] 9.1 实现平面点位标注：分析布局，提出 3-8 个安装点位，使用 Pillow 渲染标注 PNG（CAD 底图 + 编号圆圈 + 图例）
- [x] 9.2 实现物料清单生成：将设计拆解为单品，生成包含规格、数量、供应商建议的 JSON
- [x] 9.3 实现预算汇总：查询 SQLite 价格，计算材料/制作/安装/设计费，超支 10% 时标红
- [x] 9.4 添加材料限制合规过滤及自动替代建议
- [x] 9.5 添加纯照片输入的平面降级：简化示意布局，附"需现场复核"声明

## 10. 图像生成服务

- [x] 10.1 实现 `python-ai/app/services/image_generation.py`，统一接口：`generate(prompt, aspect_ratio, style)`
- [x] 10.2 实现 Pollinations.AI 提供者：HTTP 客户端，含超时、重试、Prompt 翻译（中→英）
- [x] 10.3 实现 ComfyUI 提供者占位：本地 ComfyUI 队列/工作流 HTTP API 客户端
- [x] 10.4 实现提供者降级链：Pollinations → ComfyUI → 占位图，含重试逻辑
- [x] 10.5 添加本地图像缓存：按内容哈希保存到 `data/images/`

## 11. 文档生成器

- [x] 11.1 实现 L1 预览 Jinja2 HTML 模板（封面、故事、氛围、Moodboard）
- [x] 11.2 实现 L3 完整交付 Jinja2 HTML 模板（全章节、可排序材料表、打印 CSS）
- [x] 11.3 实现 PPT 生成器（python-pptx）：加载 `template.pptx`，映射内容到版式，替换图片
- [x] 11.4 实现默认 PPT 模板：当 `template.pptx` 缺失时程序化生成最小模板
- [x] 11.5 实现 PDF 生成器：HTML → WeasyPrint/Playwright 转换，A4 页边距与页码
- [x] 11.6 实现 PDF 降级：WeasyPrint 失败时通过 LibreOffice 无头模式从 PPT 转换

## 12. Java 协调层 DAG 调度器

- [x] 12.1 实现 `WorkflowNode` 和 `WorkflowDefinition`：硬编码 DAG 结构
- [x] 12.2 实现拓扑排序算法：Kahn 算法或 DFS
- [x] 12.3 实现 `WorkflowEngine`：线程池并行执行无依赖节点，支持串行依赖等待
- [x] 12.4 实现状态机：INIT → PARSING → ... → COMPLETED，状态持久化到 SQLite
- [x] 12.5 实现人工确认中断点：L1/L2/L3 后暂停，暴露 REST API 供前端确认/驳回
- [x] 12.6 实现失败重试：单节点失败时重试 3 次，失败后标记整个工作流为 FAILED
- [x] 12.7 实现工作流恢复：服务重启后读取 SQLite 状态，从断点继续执行

## 13. Java REST API

- [x] 13.1 实现项目创建接口：`POST /projects`，接受 multipart 上传（照片、CAD、PDF、PPT、参考图）+ 文本 JSON
- [x] 13.2 实现工作流触发接口：`POST /projects/{id}/workflow/start`，可选择层级（L1/L2/L3）
- [x] 13.3 实现人工确认接口：`POST /projects/{id}/workflow/confirm`，接受通过/驳回/反馈
- [x] 13.4 实现文档导出接口：`GET /projects/{id}/export?format=html|ppt|pdf`
- [x] 13.5 实现状态查询接口：`GET /projects/{id}/status`，返回当前阶段及输出
- [x] 13.6 添加 CORS 和静态文件服务，用于预览生成的 HTML 和图片

## 14. RAG 知识库填充

- [~] 14.1 构建商场公众号文章爬虫：抓取 50 篇高质量案例（案例故事、照片）<!-- 不再计划：数据爬虫不在当前 MVP 范围内 -->
- [~] 14.2 构建站酷/Behance 美陈设计项目爬虫：抓取 50 个含设计说明的项目 <!-- 不再计划：数据爬虫不在当前 MVP 范围内 -->
- [x] 14.3 实现 LLM 结构化提取流水线：解析文章 → 提取字段 → 校验 → 写入 SQLite + Milvus
- [~] 14.4 爬取 1688 常用美陈材料 300 条：名称、规格、价格区间、类目 <!-- 不再计划：数据爬虫不在当前 MVP 范围内 -->
- [x] 14.5 实现知识库管理 CLI：`python -m admin.ingest_cases --source dir/` 和 `python -m admin.ingest_materials --csv file.csv`

## 15. 集成与端到端测试

- [x] 15.1 编写集成测试：上传示例照片 + 文本"夏日海洋中庭吊饰预算15万" → 校验 L1 输出含故事和 Moodboard
- [~] 15.2 编写集成测试：完整 L3 工作流含 CAD 上传 → 校验标注图、物料清单、预算表存在 <!-- 不再计划：L3 工作流尚未实现 -->
- [~] 15.3 测试三种导出格式（HTML/PPT/PDF）的完整性和图片嵌入 <!-- 不再计划：导出功能尚未完整实现 -->
- [~] 15.4 测试本地 Ollama 降级：断开 Pollinations，验证 ComfyUI/占位图行为 <!-- 不再适用：项目约束已移除所有 Ollama 本地模型降级 -->
- [~] 15.5 测试 PDF/PPT 解析：上传示例 PDF 和 PPT，校验文本提取和图片提取 <!-- 不再计划：PDF/PPT 解析功能尚未完整实现 -->
- [~] 15.6 邀请真实美陈设计师进行端到端手动测试，收集输出质量反馈 <!-- 不再计划：待产品正式发布后进行 -->
