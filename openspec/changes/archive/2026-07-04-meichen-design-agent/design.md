## Context

美陈设计行业乙方公司面临的核心痛点是方案产出周期长、人力成本高。一个标准的中庭美陈方案从需求对接到交付 PPT 通常需要 3-7 天，而设计师在案例检索、概念发散、效果图绘制、物料清单编制上消耗了大量重复性劳动时间。与此同时，行业知识（材料工艺、价格区间、案例手法）分散在设计师个人经验中，难以复用。

本项目目标是为美陈设计师提供一个 AI Agent 辅助系统，将方案产出时间压缩至数小时。系统采用分层递进出案模式（L1 概念 → L2 视觉 → L3 落地），设计师在每层均可人工干预和调整，最终输出可直接交付甲方的方案文档（HTML/PPT/PDF）。

验证期约束：
- 零 API 成本优先：LLM、Embedding 全部本地部署（Ollama）。
- 图像生成零成本：Pollinations.AI 为主力。
- 单开发者可维护：架构简洁，避免引入过多分布式组件。
- 知识库从零建设：需要可快速填充的 RAG 数据管道。

## Goals / Non-Goals

**Goals:**
- 支持多模态输入（照片、CAD、PDF、PPT、参考图、文本）并提取结构化设计需求。
- 通过 RAG 检索历史案例和材料知识，辅助方案创作。
- 分层递进输出 L1/L2/L3 方案，每层支持人工确认后再进入下一层。
- 自动生成 Moodboard、概念效果图、色彩材质板、平面标注图、物料清单、预算表。
- 输出 HTML 预览、PPT 汇报文档、PDF 归档三种格式。
- 验证期系统可在本地单机（Mac 16G+ 或 PC 8G 显存）完整运行，零外部 LLM 费用。

**Non-Goals:**
- 不生成真实 CAD 文件（DXF/DWG 输出），L3 仅做图像级平面标注。
- 不做实时 3D 模型生成或渲染（如 Blender 自动化）。
- 不做设计师之外的甲方直接交互（本期定位为设计师工具，非 C 端产品）。
- 不接真实 1688 API（验证期采用爬虫/手动导入的历史价格）。
- 不做精细的权限管理和多租户隔离。

## Decisions

### 1. 系统架构：Java 协调层 + Python AI 服务
- **决策**：采用 Java（Spring Boot）作为协调层，负责 DAG 工作流调度、状态管理、REST API、人工确认；Python（FastAPI）作为 AI 服务层，负责 LLM/VLM 推理、RAG 检索、图像生成、文档生成。
- **理由**：Java 在 API 稳定性、类型安全、并发处理、长期维护性上优于 Python；Python 在 AI 生态（Ollama、Milvus、图像处理、PPT 生成）上不可替代。分层后各取所长，且每层可独立扩展。
- **替代方案**：纯 Python（FastAPI + LangGraph）。放弃原因：LangGraph 对固定 SOP 流水线过度设计，状态调试像黑盒；用户需要白盒可控的调度层。

### 2. Agent 编排：自研 DAG 调度器 vs. LangGraph
- **决策**：Java 协调层自研 DAG 调度器（WorkflowEngine），不用 LangGraph。
- **理由**：本项目是固定 SOP 流水线（解析→分析→检索→L1→L2→L3→导出），不需要动态任务分解。自研 DAG 约 300 行代码，DAG 结构硬编码在代码里（`List.of(...)`），100% 白盒可控。LangGraph 的 Human-in-the-loop 能力在 Java 层通过状态机中断点实现。
- **替代方案**：LangGraph 状态机。放弃原因：学习曲线陡、异步调试困难、绑定 LangChain 生态。

### 3. LLM 策略：本地 Ollama 为主 vs. 云端 API
- **决策**：验证期全部本地 Ollama，文本用 Qwen2.5 14B/32B，图像理解用 Qwen2.5-VL，Embedding 用 bge-m3。
- **理由**：零成本、无限调用、无网络依赖。Qwen 系列中文能力足以支撑美陈设计场景。
- **替代方案**：SiliconFlow/DeepSeek API。放弃原因：验证期目标是证明概念可行性，任何 API 成本都是阻碍。保留 API 兜底作为二期扩展点。

### 4. 图像生成：Pollinations.AI vs. 本地 ComfyUI
- **决策**：Pollinations.AI 为主力，本地 ComfyUI 为备选。
- **理由**：Pollinations 完全免费、无需 GPU、HTTP 调用简单，适合 Moodboard 和概念效果图的快速验证。ComfyUI 需要 GPU 和复杂工作流配置，作为验证期后备和后期风格精细化控制。

### 5. RAG 架构：双轨制（向量 + 结构化 SQL）
- **决策**：非结构化知识（案例文本、设计说明）走 Milvus 向量检索；结构化知识（材料价格、规格参数、供应商）走 SQLite 查询。
- **理由**：美陈方案生成既需要语义相似案例（向量），又需要精确的预算数字（SQL）。混合检索比纯向量更准确。Milvus 的 Java/Python client 均成熟，支持一步到位。

### 6. 数据存储：SQLite + Milvus vs. PostgreSQL + Milvus
- **决策**：验证期用 SQLite（结构化）+ Milvus（向量），本地部署。
- **理由**：SQLite 零运维、单文件可迁移；Milvus 通过 Docker 本地运行，Java 和 Python 均有成熟 client。当数据量超过 10 万或需要多机部署时，SQLite 可平滑迁移到 PostgreSQL。

### 7. 文档生成：python-pptx 后端生成 vs. 前端导出
- **决策**：MVP 阶段用 python-pptx 后端模板化生成 PPT，HTML 用 Jinja2 渲染，PDF 由 HTML 转 PDF（Playwright/WeasyPrint）。
- **理由**：设计师交付甲方的核心格式是 PPT，python-pptx 可以在 2 天内跑通可交付的模板。前端可视化编辑器属于体验优化，放到二期。

### 8. CAD 处理：ezdxf 解析 + Pillow 图像标注 vs. 真实 CAD 编辑
- **决策**：用 ezdxf 提取 CAD 轮廓线和柱网位置，生成 PNG 底图后用 Pillow 做点位标注和文字说明。
- **理由**：真实 CAD 编辑库（如 PyAutoCAD）依赖 Windows 和 AutoCAD 软件授权，不适合跨平台部署。图像级标注足以满足 L3 方案的可视化需求。

### 9. 输入解析扩展：PDF/PPT 解析
- **决策**：支持 PDF 和 PPT 作为输入，提取文本和图片作为辅助需求材料。
- **理由**：甲方常提供 PDF 需求书或参考 PPT，设计师也常有历史方案 PPT 需要复用。PDF 用 pdfplumber/PyMuPDF 解析文本和图片；PPT 用 python-pptx 解析幻灯片文本和参考图。

## System Architecture

### 整体架构

```
前端 (React/Vue)
       │
       ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│              Java 协调层 (Spring Boot)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  WorkflowEngine (自研 DAG 调度器)                    │   │
│  │  • 项目状态机管理                                     │   │
│  │  • DAG 拓扑排序与并行执行                             │   │
│  │  • 人工确认中断点 (L1/L2/L3)                         │   │
│  │  • 失败重试与状态持久化                               │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ REST API    │  │ 项目状态库   │  │ 文件存储服务        │ │
│  │ Controller  │  │ (SQLite)    │  │ (本地磁盘)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
       │
       ▼ HTTP/REST (内网)
┌─────────────────────────────────────────────────────────────┐
│              Python AI 服务 (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Agent 路由层 │  │ 工具函数层   │  │ 知识库客户端        │ │
│  │ (/agents/*) │  │ (tools.py)  │  │ (Milvus + SQLite)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ 输入解析 Agent│ │ 需求分析 Agent│ │ 知识检索 Agent│        │
│  │ input-parser │ │ requirement  │ │ knowledge    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ 概念设计 L1  │ │ 视觉设计 L2  │ │ 可落地设计 L3│        │
│  │ concept      │ │ visual       │ │ technical    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐                                          │
│  │ 文档生成 Agent│                                          │
│  │ doc-generator│                                          │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
       │
       ▼ HTTP/REST (本地/免费)
┌─────────────────────────────────────────────────────────────┐
│                    基础设施层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Ollama       │  │ Pollinations │  │ 本地文件系统      │ │
│  │ • Qwen2.5    │  │ .AI          │  │ (上传/生成文件)   │ │
│  │ • Qwen2.5-VL │  │ (免费图像)   │  │                  │ │
│  │ • bge-m3     │  │              │  │                  │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Java 协调层 DAG 调度器

#### DAG 结构

```
                    ┌─────────────────┐
                    │     INIT        │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐
        │照片解析  │   │CAD解析  │   │文本解析  │  ← 并行
        │PDF解析   │   │PPT解析  │   │         │
        └────┬────┘   └────┬────┘   └────┬────┘
             └──────────────┼──────────────┘
                            ▼
                    ┌───────────────┐
                    │  需求分析      │  ← 串行
                    └───────┬───────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        ┌─────────────┐           ┌─────────────┐
        │ 案例检索     │           │ 材料查价     │  ← 并行
        └──────┬──────┘           └──────┬──────┘
               └───────────┬─────────────┘
                           ▼
                   ┌───────────────┐
                   │  L1 概念设计   │  ← 串行
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ L1 人工确认   │  ← 中断点
                   └───────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │效果图   │  │材质板   │  │一致性检查│  ← 效果图+材质板并行，一致性检查依赖前两者
        └────┬────┘  └────┬────┘  └────┬────┘
             └─────────────┼────────────┘
                           ▼
                   ┌───────────────┐
                   │ L2 人工确认   │  ← 中断点
                   └───────┬───────┘
                           ▼
                   ┌───────────────┐
                   │ L3 可落地设计  │  ← 串行
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ L3 人工确认   │  ← 中断点（可选）
                   └───────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │ HTML    │  │ PPT     │  │ PDF     │  ← 并行
        └─────────┘  └─────────┘  └─────────┘
```

#### 核心 Java 类结构

```java
// 节点定义
public class WorkflowNode {
    private String id;
    private String agentEndpoint;       // Python Agent 的 HTTP 路径
    private List<String> dependencies;  // 前置节点 ID 列表
    private boolean requiresHumanConfirm;
}

// DAG 定义（硬编码，完全透明）
public class MeichenWorkflow {
    public static List<WorkflowNode> getDefinition() {
        return List.of(
            new WorkflowNode("photo_parse", "/agents/input-parser/parse-photo", List.of(), false),
            new WorkflowNode("cad_parse", "/agents/input-parser/parse-cad", List.of(), false),
            new WorkflowNode("pdf_parse", "/agents/input-parser/parse-pdf", List.of(), false),
            new WorkflowNode("ppt_parse", "/agents/input-parser/parse-ppt", List.of(), false),
            new WorkflowNode("text_parse", "/agents/input-parser/parse-text", List.of(), false),
            new WorkflowNode("requirement_analyze", "/agents/requirement-analyst/analyze",
                List.of("photo_parse", "cad_parse", "pdf_parse", "ppt_parse", "text_parse"), false),
            new WorkflowNode("case_retrieve", "/agents/knowledge-retrieval/cases",
                List.of("requirement_analyze"), false),
            new WorkflowNode("price_query", "/agents/knowledge-retrieval/prices",
                List.of("requirement_analyze"), false),
            new WorkflowNode("l1_design", "/agents/concept-designer/design",
                List.of("case_retrieve", "price_query"), false),
            new WorkflowNode("l1_confirm", null, List.of("l1_design"), true),
            new WorkflowNode("rendering", "/agents/visual-designer/rendering",
                List.of("l1_confirm"), false),
            new WorkflowNode("material_board", "/agents/visual-designer/material-board",
                List.of("l1_confirm"), false),
            new WorkflowNode("consistency_check", "/agents/visual-designer/consistency-check",
                List.of("rendering", "material_board"), false),
            new WorkflowNode("l2_confirm", null, List.of("consistency_check"), true),
            new WorkflowNode("l3_design", "/agents/technical-designer/design",
                List.of("l2_confirm"), false),
            new WorkflowNode("l3_confirm", null, List.of("l3_design"), true),
            new WorkflowNode("export_html", "/agents/doc-generator/generate",
                List.of("l3_confirm"), false),
            new WorkflowNode("export_ppt", "/agents/doc-generator/generate",
                List.of("l3_confirm"), false),
            new WorkflowNode("export_pdf", "/agents/doc-generator/generate",
                List.of("l3_confirm"), false)
        );
    }
}

// 执行引擎
public class WorkflowEngine {
    public void execute(String projectId) {
        // 1. 拓扑排序
        // 2. 线程池并行执行无依赖节点
        // 3. 节点完成后检查下游依赖是否满足
        // 4. requiresHumanConfirm=true 时暂停，更新状态为 WAITING_CONFIRM
        // 5. 用户确认后，从该节点继续执行
    }
}
```

#### 状态机

```
INIT → PARSING → ANALYZING → RETRIEVING → L1_DESIGNING → L1_WAITING_CONFIRM
→ L1_CONFIRMED → L2_DESIGNING → L2_WAITING_CONFIRM → L2_CONFIRMED
→ L3_DESIGNING → L3_WAITING_CONFIRM → L3_CONFIRMED → EXPORTING → COMPLETED
```

每个状态转换都持久化到 SQLite，服务重启后可从当前状态恢复。

### Python AI 服务 Agent 设计

#### Agent 1: 输入解析 (input-parser)

| 维度 | 内容 |
|------|------|
| **职责** | 把用户上传的"原材料"翻译成结构化数据 |
| **输入** | `{project_id, files: [{type:"photo"\|"cad"\|"pdf"\|"ppt"\|"reference", path}], text: string}` |
| **输出** | `{photos:[...], cad:{outline, columns, area}, pdf:{extracted_text, images}, ppt:{slides:[{text, images}]}, references:[...], text_requirement:{...}}` |
| **内部处理** | 1. 照片解析（VLM 并行）→ 2. CAD 解析（ezdxf）→ 3. PDF 解析（pdfplumber/PyMuPDF）→ 4. PPT 解析（python-pptx）→ 5. 参考图解析（VLM 并行）→ 6. 文本解析（LLM JSON 提取） |
| **LLM 调用** | • **Qwen2.5-VL**：照片/参考图理解<br>• **Qwen2.5 14B**：文本需求提取、PDF 文本摘要 |
| **工具/库** | ezdxf, Pillow, OpenCV, pdfplumber/PyMuPDF, python-pptx |
| **内部状态机** | ❌ 不需要 |
| **HTTP 端点** | `POST /agents/input-parser/parse` |

#### Agent 2: 需求分析 (requirement-analyst)

| 维度 | 内容 |
|------|------|
| **职责** | 合并多源解析结果，输出标准化设计任务书，检测冲突 |
| **输入** | `{parsed_result: {...}}` |
| **输出** | `{requirement:{theme, budget_amount, budget_level, space_type, style_direction, constraints, risks, missing_info}}` |
| **内部处理** | 1. 字段合并与冲突检测 → 2. 预算档次分类（查 SQLite 历史分位）→ 3. 主题方向提取 → 4. 隐性风险识别 |
| **LLM 调用** | • **Qwen2.5 14B**：合并推理、冲突检测、风险识别 |
| **工具/库** | SQLite 查询 |
| **内部状态机** | ❌ 不需要 |
| **HTTP 端点** | `POST /agents/requirement-analyst/analyze` |

#### Agent 3: 知识检索 (knowledge-retrieval)

| 维度 | 内容 |
|------|------|
| **职责** | 从知识库检索相似案例和材料价格，合成知识摘要 |
| **输入** | `{requirement: {...}}` |
| **输出** | `{cases:[...], materials:[...], summary: "800字以内Markdown"}` |
| **内部处理** | 1. 案例向量检索（Milvus，并行）→ 2. 材料价格查询（SQLite，并行）→ 3. LLM 合成摘要 |
| **LLM 调用** | • **Qwen2.5 14B**：将检索结果合成为 800 字摘要 |
| **工具/库** | Milvus client, SQLite client |
| **中间件** | Milvus（向量库）, SQLite |
| **内部状态机** | ❌ 不需要 |
| **HTTP 端点** | `POST /agents/knowledge-retrieval/retrieve` |

#### Agent 4: 概念设计 L1 (concept-designer)

| 维度 | 内容 |
|------|------|
| **职责** | 生成设计概念故事、氛围描述、Moodboard |
| **输入** | `{requirement: {...}, knowledge_summary: string}` |
| **输出** | `{concept_story: "300-500字", atmosphere:{keywords:[...], sensory_paragraph:"200字"}, moodboard:[{image_url, type:"ai"\|"reference", note}]}` |
| **内部处理** | 1. LLM 生成故事 → 2. LLM 生成氛围 → 3. 生成 2-3 个图像 Prompt → 4. 调用 Pollinations 生图 → 5. 从 Milvus 检索 3-6 张历史参考图 |
| **LLM 调用** | • **Qwen2.5 14B**：故事生成、氛围生成、Prompt 构建 |
| **工具/库** | Pollinations HTTP client, Milvus 查询 |
| **中间件** | Milvus |
| **内部状态机** | ❌ 不需要 |
| **HTTP 端点** | `POST /agents/concept-designer/design` |

#### Agent 5: 视觉设计 L2 (visual-designer)

| 维度 | 内容 |
|------|------|
| **职责** | 生成概念效果图和色彩材质板 |
| **输入** | `{l1_concept: {...}, space_context: {...}}` |
| **输出** | `{renderings:[{url, prompt, view_angle}], color_material_board:{image_url, colors:[...], materials:[...]}}` |
| **内部处理** | 1. 构建英文 Prompt → 2. 并行调用 Pollinations 生成 2-3 张效果图 → 3. Pillow 合成色彩材质板 → 4. LLM 一致性检查 |
| **LLM 调用** | • **Qwen2.5 14B**：Prompt 翻译/构建、一致性检查 |
| **工具/库** | Pollinations HTTP client, Pillow |
| **内部状态机** | ❌ 不需要 |
| **HTTP 端点** | `POST /agents/visual-designer/design` |

#### Agent 6: 可落地设计 L3 (technical-designer)

| 维度 | 内容 |
|------|------|
| **职责** | 生成平面点位标注图、物料清单、预算汇总 |
| **输入** | `{l2_visual: {...}, cad_outline: {...}, requirement: {...}}` |
| **输出** | `{layout_annotation:{image_url, points:[...]}, material_list:[...], budget_summary:{categories:[...], total, vs_budget_alert}}` |
| **内部处理** | 1. 分析布局生成点位 → 2. Pillow 在 CAD 底图上标注 → 3. LLM 拆解物料清单 → 4. 查询 SQLite 价格 → 5. 计算预算合计 |
| **LLM 调用** | • **Qwen2.5 14B**：物料拆解 |
| **工具/库** | Pillow, SQLite |
| **中间件** | SQLite |
| **内部状态机** | ⚠️ 可选简单三步（布局→物料→预算），用 3 个函数顺序调用即可 |
| **HTTP 端点** | `POST /agents/technical-designer/design` |

#### Agent 7: 文档生成 (doc-generator)

| 维度 | 内容 |
|------|------|
| **职责** | 将方案数据打包为 HTML / PPT / PDF |
| **输入** | `{project_data: {...}, format: "html"\|"ppt"\|"pdf"}` |
| **输出** | `{document_url: string}` |
| **内部处理** | HTML: Jinja2 模板渲染 → PPT: python-pptx 填充模板 → PDF: WeasyPrint HTML 转 PDF |
| **LLM 调用** | ❌ 不需要 |
| **工具/库** | Jinja2, python-pptx, WeasyPrint, Pillow |
| **内部状态机** | ❌ 不需要 |
| **HTTP 端点** | `POST /agents/doc-generator/generate` |

### LLM 选型总表（全部免费/本地）

| 用途 | 模型 | 部署方式 | 成本 | 备选 |
|------|------|----------|------|------|
| **文本推理**（所有 Agent 的"大脑"） | Qwen2.5 14B / 32B | Ollama 本地 | 0 元 | SiliconFlow（免费额度） |
| **图像理解**（照片/参考图/PDF图片解析） | Qwen2.5-VL | Ollama 本地 | 0 元 | 通义千问 VL API |
| **文本嵌入**（RAG 向量化） | bge-m3 | Ollama 本地 | 0 元 | SiliconFlow Embedding |
| **图像生成**（效果图/Moodboard） | Pollinations AI | 免费 HTTP API | 0 元 | 本地 ComfyUI + SDXL |

### 中间件选型总表

| 中间件 | 用途 | 部署方式 | 理由 |
|--------|------|----------|------|
| **SQLite** | 项目状态、材料价格、历史案例元数据 | 本地文件 | 零配置，Java JDBC + Python sqlite3 都原生支持 |
| **Milvus** | 向量数据库（案例描述、图像描述 Embedding） | Docker 本地 | Java/Python client 均成熟，支持 10 万+ 数据量，一步到位 |
| **Ollama** | 本地大模型推理服务 | 本地进程（11434 端口） | 统一接口，换模型只需改名称 |
| **Pollinations.AI** | 免费图像生成 | 外部 HTTP API | 无需 Key，直接 HTTP GET |

### Agent 交互协议（Java ↔ Python）

Java 通过 **同步 HTTP POST** 调用 Python Agent。

**请求规范**：
```http
POST http://python-ai-service:8000/agents/{agent-name}/{action}
Content-Type: application/json

{
  "project_id": "uuid",
  "input": { /* 该 Agent 需要的输入 JSON */ },
  "context": { /* 可选：上游 Agent 的完整输出，用于调试 */ }
}
```

**响应规范**：
```json
{
  "status": "success",
  "output": { /* Agent 产出的结构化数据 */ },
  "metadata": {
    "agent_name": "concept-designer",
    "llm_calls": 3,
    "image_calls": 2,
    "duration_ms": 15000,
    "model_used": "qwen2.5:14b"
  },
  "logs": [
    {"step": "prompt_build", "status": "ok", "time_ms": 200},
    {"step": "ollama_generate", "status": "ok", "time_ms": 8000},
    {"step": "pollinations_call", "status": "ok", "time_ms": 6000}
  ]
}
```

### 白盒可控设计

| 黑盒风险点 | 本方案如何处理 |
|-----------|--------------|
| 框架隐藏了执行流程 | Java 协调层的 DAG 就是代码里的 `List.of(...)`，打开文件就看到完整流程图 |
| Agent 内部逻辑不透明 | 每个 Python Agent 是独立函数，输入输出有 Pydantic Schema，没有封装框架 |
| LLM 调用过程看不到 | Python Agent 的响应里包含 `logs` 字段，记录每次 LLM 调用的耗时和状态 |
| Prompt 不可控 | 每个 Agent 的 Prompt 是独立模板文件（`prompts/concept_story.txt`），随时修改 |
| 向量检索为什么返回这个结果 | Milvus 查询自带 `distance` 分数，返回结果里直接暴露 |
| 状态丢了怎么办 | Java 层的 SQLite 持久化每一步状态，服务重启后从断点恢复 |

## Risks / Trade-offs

- [Risk] **本地 14B 模型在复杂结构化输出上不稳定**（如 L3 物料清单同时输出多个表格字段时格式错乱）
  → Mitigation：Prompt 中加入 Few-shot 示例；简化单次输出结构（分多次调用生成不同表格）；硬件允许时升级到 32B。

- [Risk] **Pollinations.AI 对中文 Prompt 理解弱，生成图像风格不可控**
  → Mitigation：LLM 先将概念描述翻译成英文 Prompt；为常见美陈风格预设 Prompt 模板；备选 ComfyUI 本地工作流。

- [Risk] **RAG 知识库初期数据少，检索结果质量差**
  → Mitigation：验证期允许设计师手动上传和标注案例；优先爬取 50-100 个高质量商场公众号案例，经 LLM 结构化后入库；知识库数据量 < 500 时，降级为通用 LLM 推理。

- [Risk] **Ollama 本地推理速度慢，影响交互体验**
  → Mitigation：14B 模型在 M 系列 Mac 上速度可接受；对非实时任务（如概念生成、效果图生成）采用异步任务队列；异步结果通过 WebSocket 或轮询推送给前端。

- [Risk] **CAD 图纸格式多样，ezdxf 解析失败率高**
  → Mitigation：支持用户同时上传 CAD + 现场照片作为 fallback；解析失败时降级为仅基于照片做方案。

- [Risk] **Milvus 本地部署增加验证期复杂度**
  → Mitigation：提供 `docker-compose.yml` 一键启动 Milvus Standalone；验证期数据量 < 1 万时，Milvus 资源占用极低（< 2GB 内存）；如 Docker 不可用，提供 SQLite + 全文搜索的降级方案。

- [Risk] **PDF/PPT 解析结果质量不稳定**
  → Mitigation：PDF 解析使用 pdfplumber（文本）+ PyMuPDF（图片提取）双库校验；PPT 解析使用 python-pptx 提取文本和缩略图；解析失败时标记为"未解析内容"，不阻断主流程。

## Migration Plan

- **Phase 1（验证期）**：Java Spring Boot + Python FastAPI + Ollama + SQLite + Milvus（Docker）+ Pollinations，本地单机运行。
- **Phase 2（扩展期）**：
  - LLM 迁移：保留 Ollama 抽象层，增加 SiliconFlow/DeepSeek/GPT-4 等云端 Provider 切换能力。
  - 数据库迁移：SQLite → PostgreSQL（SQLAlchemy 抽象层支持平滑迁移）。
  - 存储迁移：本地文件存储 → MinIO/S3（图像和文档对象存储）。
  - 协调层扩展：WorkflowEngine 支持动态 DAG（从数据库加载流程定义）。

## Open Questions

1. 现场视频输入的解析策略：是抽帧后按单张照片处理，还是需要时序理解？（本期建议先只支持照片）
2. 设计师对 AI 生成效果图的修改需求频率：如果很高，是否需要引入图像编辑 Agent（如局部重绘）？（本期建议先不支持，设计师在外部工具修改后重新上传）
3. PDF/PPT 解析后的图片是否直接进入参考图分析流程？（建议：PDF 中的图片和 PPT 中的幻灯片图片均作为参考图输入，经 VLM 分析后纳入风格提取）
