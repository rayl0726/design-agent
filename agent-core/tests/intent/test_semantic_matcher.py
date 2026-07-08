import pytest

from app.services.semantic_matcher import SemanticMatcher
from app.services.taxonomy_loader import load_taxonomy


@pytest.mark.asyncio
async def test_semantic_match_space_type() -> None:
    taxonomy = load_taxonomy()
    matcher = SemanticMatcher(taxonomy, threshold=0.75)
    name, score = await matcher.match("pop-up store", "space_type")
    assert name == "快闪店"
    assert score >= 0.75
