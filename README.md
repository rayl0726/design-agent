# 美陈设计 Agent 系统

美陈设计师的 AI 辅助出案系统，将方案产出时间从 3-7 天压缩至数小时。

## 架构

- **Java 协调层** (`agent-api/`): Spring Boot + 自研 DAG 调度器，负责工作流编排、状态管理、REST API
- **Python AI 服务** (`agent-core/`): FastAPI，负责 LLM/VLM 推理、RAG 检索、图像生成、文档生成
- **向量数据库**: Milvus (Docker)
- **结构化数据库**: MySQL

## 快速开始

### 1. 启动 Milvus

```bash
docker-compose up -d
```

### 2. 启动 Ollama 并拉取模型

```bash
# 安装 Ollama: https://ollama.com

ollama pull qwen2.5:14b
ollama pull qwen2.5-vl
ollama pull bge-m3
```

### 3. 启动 Python AI 服务

```bash
cd agent-core
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### 4. 启动 Java 协调层

```bash
cd agent-api
./mvnw spring-boot:run
```

### 5. 访问 API 文档

- Java 协调层: http://localhost:8080/swagger-ui.html
- Python AI 服务: http://localhost:8000/docs

## 输入支持

- 现场照片 / 视频
- CAD 图纸 (DWG/DXF)
- PDF 需求书 / 参考文档
- PPT 参考方案
- 参考图 (Pinterest/小红书)
- 自然语言文本需求

## 输出格式

- **L1 概念方向**: 设计主题故事 + 氛围描述 + Moodboard
- **L2 视觉方案**: L1 + AI 概念效果图 + 色彩材质板
- **L3 可落地方案**: L2 + 平面点位图 + 物料清单 + 预算表

文档导出: HTML 预览 / PPT 汇报 / PDF 归档

## 技术栈

| 层 | 技术 |
|---|---|
| 协调层 | Java 17, Spring Boot 3.2, MySQL |
| AI 服务 | Python 3.11, FastAPI, Ollama |
| LLM | Qwen2.5 14B/32B, Qwen2.5-VL |
| Embedding | bge-m3 |
| 向量库 | Milvus 2.4 |
| 图像生成 | Pollinations.AI (免费) |
| 文档生成 | python-pptx, Jinja2, WeasyPrint |
