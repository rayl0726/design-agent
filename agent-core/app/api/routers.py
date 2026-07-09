from __future__ import annotations

from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.agents.input_parser import PhotoParser, VideoParser, CADParser, PDFParser, PPTParser, ReferenceParser, TextParser, InputMerger
from app.agents.requirement_analyst import RequirementAnalyst
from app.agents.knowledge_retrieval import KnowledgeRetrievalAgent
from app.agents.concept_designer import ConceptDesignerAgent
from app.agents.visual_designer import VisualDesignerAgent
from app.agents.technical_designer import TechnicalDesignerAgent
from app.services.doc_generator import doc_generator
from app.services.negative_prompt_builder import NegativePromptBuilder
from app.services.prompt_template_loader import PromptTemplateLoader
from app.services.prompt_template_renderer import PromptTemplateRenderer
from app.api.endpoints import learning

router = APIRouter()
router.include_router(learning.router)

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
    parser = TextParser()
    return await parser.parse(text)


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
