from __future__ import annotations
from typing import Any


async def run_meichen_workflow(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Orchestrates existing meichen skills in the original DAG order.
    This is a compatibility wrapper; internal logic preserved.
    """
    from app.agents.meichen.skills.input_parser import parse_input
    from app.agents.meichen.skills.requirement_analyst import analyze_requirement
    from app.agents.meichen.skills.concept_designer import design_concepts
    from app.agents.meichen.skills.visual_designer import generate_visuals
    from app.agents.meichen.skills.technical_designer import design_technical

    parsed = await parse_input(inputs)
    requirement = await analyze_requirement(parsed)
    concepts = await design_concepts(requirement)
    visuals = await generate_visuals(concepts)
    technical = await design_technical(concepts, visuals)

    return {
        "l1_output": requirement,
        "l2_output": concepts,
        "l3_output": technical,
        "visuals": visuals,
    }
