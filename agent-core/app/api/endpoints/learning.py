from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.learning.alias_expansion import AliasExpansionService, AliasProposal
from app.services.learning.feedback_reader import FeedbackReader
from app.services.learning.few_shot_library import Example, FewShotLibrary
from app.services.learning.prompt_version_tracker import PromptVersionTracker
from app.services.learning.taxonomy_writer import TaxonomyWriter

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])

feedback_reader = FeedbackReader()
alias_service = AliasExpansionService(min_occurrences=3)
few_shot_lib = FewShotLibrary()
version_tracker = PromptVersionTracker(reader=feedback_reader)
taxonomy_writer = TaxonomyWriter()


class AliasProposalResponse(BaseModel):
    field: str
    alias: str
    canonical: str
    occurrences: int
    confidence: float


class ApplyAliasRequest(BaseModel):
    field: str
    alias: str
    canonical: str


class FewShotAppendRequest(BaseModel):
    input_text: str
    space_type: str
    theme: str | None = None
    budget: int | None = None
    points: list[str] | None = None


@router.get("/alias-proposals", response_model=list[AliasProposalResponse])
async def list_alias_proposals() -> list[AliasProposalResponse]:
    corrections = await feedback_reader.list_unprocessed_intent_corrections()
    proposals = alias_service.propose(corrections)
    return [
        AliasProposalResponse(
            field=p.field,
            alias=p.alias,
            canonical=p.canonical,
            occurrences=p.occurrences,
            confidence=p.confidence,
        )
        for p in proposals
    ]


@router.post("/alias-proposals/apply")
async def apply_alias_proposal(req: ApplyAliasRequest) -> dict:
    proposal = AliasProposal(
        field=req.field,
        alias=req.alias,
        canonical=req.canonical,
        occurrences=0,
        confidence=1.0,
    )
    ok = taxonomy_writer.apply_alias(proposal)
    if not ok:
        raise HTTPException(status_code=404, detail="Canonical value not found in taxonomy")
    return {"applied": True}


@router.post("/few-shot-examples")
async def append_few_shot_example(req: FewShotAppendRequest) -> dict:
    await few_shot_lib.append(Example(**req.model_dump()))
    return {"saved": True}


@router.get("/few-shot-examples")
async def list_few_shot_examples(
    space_type: str,
    theme: str | None = None,
    top_k: int = 3,
) -> list[dict]:
    examples = await few_shot_lib.retrieve(space_type=space_type, theme=theme, top_k=top_k)
    return [example.__dict__ for example in examples]


@router.get("/prompt-version-comparison")
async def compare_prompt_versions(versions: str) -> dict:
    version_list = [v.strip() for v in versions.split(",") if v.strip()]
    reports = await version_tracker.compare_versions(version_list)
    return {
        v: {
            "total": r.total,
            "positive": r.positive,
            "negative": r.negative,
            "tags": r.tags,
        }
        for v, r in reports.items()
    }
