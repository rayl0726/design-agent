from __future__ import annotations

import asyncio
import json
import re

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.meichen.skills.input_parser import PhotoParser, VideoParser, CADParser, PDFParser, PPTParser, ReferenceParser, TextParser, InputMerger
from app.agents.meichen.skills.requirement_analyst import RequirementAnalyst
from app.agents.meichen.skills.knowledge_retrieval import KnowledgeRetrievalAgent
from app.agents.meichen.skills.concept_designer import ConceptDesignerAgent
from app.agents.meichen.skills.visual_designer import VisualDesignerAgent
from app.agents.meichen.skills.technical_designer import TechnicalDesignerAgent
from app.services.doc_generator import doc_generator
from app.services.negative_prompt_builder import NegativePromptBuilder
from app.services.prompt_template_loader import PromptTemplateLoader
from app.services.prompt_template_renderer import PromptTemplateRenderer
from app.services.llm_client import LLMClient
from app.tools.web_search import WebSearchTool
from app.api.endpoints import debug, learning, admin_metrics

router = APIRouter()
router.include_router(learning.router)
router.include_router(debug.router)
router.include_router(admin_metrics.router)

_prompt_template_loader = PromptTemplateLoader()
_prompt_template_renderer = PromptTemplateRenderer()
_negative_prompt_builder = NegativePromptBuilder()


# ---------- 输入解析器 ----------

@router.post("/agents/input-parser/parse-photo")
async def parse_photo(payload: dict = None):
    if not payload or not payload.get("file_path"):
        return {"source_type": "photo", "photos": [], "notes": "无照片输入"}
    parser = PhotoParser()
    return await parser.parse(payload.get("file_path"))


@router.post("/agents/input-parser/parse-video")
async def parse_video(payload: dict = None):
    if not payload or not payload.get("file_path"):
        return {"source_type": "video", "notes": "无视频输入"}
    parser = VideoParser()
    return await parser.parse(payload.get("file_path"))


@router.post("/agents/input-parser/parse-cad")
async def parse_cad(payload: dict = None):
    if not payload or not payload.get("file_path"):
        return {"source_type": "cad", "notes": "无CAD输入"}
    parser = CADParser()
    return await parser.parse(payload.get("file_path"))


@router.post("/agents/input-parser/parse-pdf")
async def parse_pdf(payload: dict = None):
    if not payload or not payload.get("file_path"):
        return {"source_type": "pdf", "notes": "无PDF输入"}
    parser = PDFParser()
    return await parser.parse(payload.get("file_path"))


@router.post("/agents/input-parser/parse-ppt")
async def parse_ppt(payload: dict = None):
    if not payload or not payload.get("file_path"):
        return {"source_type": "ppt", "notes": "无PPT输入"}
    parser = PPTParser()
    return await parser.parse(payload.get("file_path"))


@router.post("/agents/input-parser/parse-reference")
async def parse_reference(payload: dict = None):
    if not payload or not payload.get("file_path"):
        return {"source_type": "reference", "notes": "无参考图输入"}
    parser = ReferenceParser()
    return await parser.parse(payload.get("file_path"))


@router.post("/agents/input-parser/parse-text")
async def parse_text(payload: dict):
    text = payload.get("text", "")
    project_id = payload.get("project_id")
    previous_intent = payload.get("previous_intent")
    recent_messages = payload.get("recent_messages")
    conversation_summary = payload.get("conversation_summary", "")
    parser = TextParser()
    return await parser.parse(
        text,
        project_id=project_id,
        previous_intent=previous_intent,
        recent_messages=recent_messages,
        conversation_summary=conversation_summary,
    )


@router.post("/agents/input-parser/merge")
async def merge_inputs(inputs: dict):
    merger = InputMerger()
    parsed_results = inputs.get("parsed_results", [])
    return await merger.merge(parsed_results)


# ---------- 需求分析 ----------

@router.post("/agents/requirement-analyst/analyze")
async def analyze_requirement(merged_input: dict):
    analyst = RequirementAnalyst()
    return await analyst.analyze(merged_input)


# ---------- 知识检索 ----------

@router.post("/agents/knowledge-retrieval/retrieve")
async def retrieve_knowledge(requirement: dict):
    agent = KnowledgeRetrievalAgent()
    return await agent.retrieve(requirement)


# ---------- 概念设计 L1 ----------

@router.post("/agents/concept-designer/design")
async def design_concept(payload: dict):
    requirement = payload.get("requirement_analyze", {})
    retrieval = payload.get("knowledge_retrieve", {})
    agent = ConceptDesignerAgent()
    return await agent.design(requirement, retrieval)


@router.post("/agents/concept-designer/refine")
async def refine_concept(payload: dict):
    current_l1 = payload.get("current_l1", {})
    feedback = payload.get("feedback", "")
    requirement = payload.get("requirement", {})
    agent = ConceptDesignerAgent()
    return await agent.refine(current_l1, feedback, requirement)


# ---------- 视觉设计 L2 ----------

@router.post("/agents/visual-designer/design")
async def design_visual(payload: dict):
    l1 = payload.get("concept_design", {})
    requirement = payload.get("requirement_analyze", {})
    agent = VisualDesignerAgent()
    return await agent.design(l1, requirement)


# ---------- 技术设计 L3 ----------

@router.post("/agents/technical-designer/design")
async def design_technical(payload: dict):
    l2 = payload.get("visual_design", {})
    requirement = payload.get("requirement_analyze", {})
    cad_data = payload.get("cad_parse", {})
    
    concept_design = payload.get("concept_design", {})
    if concept_design and not requirement:
        requirement = concept_design
    
    agent = TechnicalDesignerAgent()
    return await agent.design(l2, requirement, cad_data if cad_data else None)


# ---------- 文档生成 ----------

@router.post("/agents/doc-generator/generate")
async def generate_document(payload: dict = Body(...)):
    project_id = payload.get("project_id", "unknown")
    level = payload.get("level", payload.get("current_level", "L3"))
    concept = payload.get("concept_design", {})
    visual = payload.get("visual_design", {})
    technical = payload.get("technical_design", {})
    requirement = payload.get("requirement_analyze", {})

    design_data = {}
    if level == "L1":
        design_data = concept
    elif level == "L2":
        design_data = visual if visual else concept
    else:
        design_data = technical if technical else (visual if visual else concept)

    project_data = {
        "project_id": project_id,
        "title": design_data.get("story", {}).get("title", "美陈设计方案"),
        "story": design_data.get("story", {}),
        "atmosphere": design_data.get("atmosphere", {}),
        "images": design_data.get("moodboard", {}).get("generated_images", []),
        "material_list": design_data.get("material_list", []),
        "budget": design_data.get("budget", {}),
        **requirement,
    }

    html_path = await doc_generator.generate_html(project_data, level)
    ppt_path = await doc_generator.generate_ppt(project_data, level)
    pdf_path = await doc_generator.generate_pdf(project_data, level)

    return {
        "html": html_path,
        "ppt": ppt_path,
        "pdf": pdf_path,
    }


# ---------- Prompt 预览 ----------

class PromptPreviewRequest(BaseModel):
    theme: str
    space_type: str
    budget_level: str | None = None
    style: str | None = None
    negative_prompts: list[str] | None = None


class PromptPreviewResponse(BaseModel):
    positive: str
    negative: str
    template_version: str
    aspect_ratio: str


@router.post("/api/v1/prompt-preview", response_model=PromptPreviewResponse)
async def preview_prompt(req: PromptPreviewRequest) -> PromptPreviewResponse:
    template_name = _prompt_template_loader.select_for_space_type(req.space_type)
    template = _prompt_template_loader.load(template_name)
    negative = _negative_prompt_builder.build(
        space_type=req.space_type,
        user_negative=req.negative_prompts,
    )
    rendered = await _prompt_template_renderer.render(
        template,
        {
            "theme": req.theme,
            "space_type": req.space_type,
            "budget_level": req.budget_level or "medium",
            "style": req.style,
            "negative_prompts": negative.split(", ") if negative else [],
        },
    )
    return PromptPreviewResponse(
        positive=rendered.positive,
        negative=rendered.negative,
        template_version=rendered.version,
        aspect_ratio=rendered.aspect_ratio,
    )


# ---------- 通用 Agent Runtime ----------

class AgentRunRequest(BaseModel):
    conversationId: str
    userInput: str
    contextJson: str | None = None


def _chunk_text(text: str, chunk_size: int = 1):
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


WEB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "当问题涉及最新资讯、实时信息或需要查询网页时，使用此工具搜索互联网。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用于搜索引擎的中文或英文查询词。",
                }
            },
            "required": ["query"],
        },
    },
}


async def _generic_run_stream(user_input: str):
    import logging

    log = logging.getLogger(__name__)
    client = LLMClient()
    web_search = WebSearchTool()

    system_prompt = (
        "你是美陈设计平台的通用 AI 助手，能够调用 web_search 工具查询互联网获取最新信息。\n"
        "规则：\n"
        "1. 当用户问题涉及最新资讯、实时数据、当前事件、天气、股价、最新政策等你无法直接确认的事实，"
        "   或者问题明显需要联网查询时，必须调用 web_search 工具。\n"
        "2. 对于常识性问题、问候、简单数学/逻辑/编程问题、历史事实、已明确的知识，直接回答，不要调用工具。\n"
        "3. 调用工具时，请通过 function calling 机制返回 tool_calls，不要在回答文本中输出任何类似 "
        "   `<tool_call>...</tool_call>` 的 XML 标记。\n"
        "4. 请用中文简洁、准确地回答。"
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        # 1. Decide whether tools are needed
        first = await client.chat(system_prompt, user_input, tools=[WEB_SEARCH_TOOL_SCHEMA])

        # 2. Execute tool calls if any
        if first.tool_calls:
            assistant_msg: dict = {"role": "assistant", "content": first.content}
            if first.tool_calls:
                assistant_msg["tool_calls"] = first.tool_calls
            messages.append(assistant_msg)

            for tc in first.tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "unknown")
                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}

                tool_call_id = tc.get("id", "")
                log.info("Tool call start: %s(%s)", tool_name, arguments)
                yield f"event: tool_start\ndata: {json.dumps({'id': tool_call_id, 'tool_name': tool_name, 'arguments': arguments}, ensure_ascii=False)}\n\n"

                from app.runtime.tool import ToolContext

                queue: asyncio.Queue[str | None] = asyncio.Queue()

                async def emit(event_name: str, payload: dict, _id=tool_call_id):
                    payload_with_id = {"id": _id, **payload}
                    await queue.put(
                        f"event: {event_name}\ndata: {json.dumps(payload_with_id, ensure_ascii=False)}\n\n"
                    )

                async def run_tool(_id=tool_call_id, _tool_name=tool_name, _arguments=arguments):
                    try:
                        result = await web_search.execute(
                            _arguments,
                            ToolContext(
                                conversation_id="generic",
                                agent_type="generic",
                                working_memory={},
                                emit=emit,
                                tool_call_id=_id,
                            ),
                        )
                        observation = result.observation
                        log.info("Tool call done: %s, observation_len=%d", _tool_name, len(observation))
                        await queue.put(
                            f"event: tool_result\ndata: {json.dumps({'id': _id, 'tool_name': _tool_name, 'arguments': _arguments, 'observation': observation}, ensure_ascii=False)}\n\n"
                        )
                        return observation
                    finally:
                        await queue.put(None)

                tool_task = asyncio.create_task(run_tool())
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield item
                observation = await tool_task

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": observation,
                })

            # 3. Generate final answer with tool results
            final_payload = {
                "model": client.primary_provider.model if hasattr(client.primary_provider, "model") else "glm-4.7-flash",
                "messages": messages,
                "stream": False,
                "temperature": 0.7,
            }
            final_resp = await client.primary_provider.client.post(
                f"{client.primary_provider.base_url}/chat/completions",
                json=final_payload,
                headers={"Authorization": f"Bearer {client.primary_provider.api_key}"},
                timeout=180.0,
            )
            final_resp.raise_for_status()
            answer = final_resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            answer = re.sub(r"<tool_call>[\s\S]*?</tool_call>", "", answer).strip()
            if not answer:
                answer = "已为您完成搜索，但未生成有效回答。"
            for chunk in _chunk_text(answer, chunk_size=1):
                yield f"event: text_delta\ndata: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
        else:
            # No tool call needed; stream the answer directly
            try:
                async for delta in client.stream(system_prompt, user_input):
                    if delta:
                        yield f"event: text_delta\ndata: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            except Exception as e:
                log.warning("Streaming failed (%s), falling back to complete + simulated streaming", e)
                answer = await client.complete(system_prompt, user_input)
                for chunk in _chunk_text(answer, chunk_size=1):
                    yield f"event: text_delta\ndata: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
    except Exception as e:
        log.error("Generic agent run failed: %s", e, exc_info=True)
        error_msg = f"抱歉，处理过程中出现错误：{e}"
        for chunk in _chunk_text(error_msg, chunk_size=1):
            yield f"event: text_delta\ndata: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
    yield "event: done\ndata: {}\n\n"


@router.post("/agents/{agent_id}/run")
async def run_agent(agent_id: str, req: AgentRunRequest):
    if agent_id == "generic":
        return StreamingResponse(
            _generic_run_stream(req.userInput),
            media_type="text/event-stream",
        )
    return StreamingResponse(
        _generic_run_stream(req.userInput),
        media_type="text/event-stream",
    )
