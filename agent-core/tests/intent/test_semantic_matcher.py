import pytest

from app.services.semantic_matcher import SemanticMatcher
from app.services.taxonomy_loader import Taxonomy, load_taxonomy


def _space_type_vectors(taxonomy: Taxonomy) -> dict[str, list[float]]:
    """Build deterministic one-hot vectors for each space type and its aliases."""
    vectors: dict[str, list[float]] = {}
    dim = len(taxonomy.space_types)
    for idx, item in enumerate(taxonomy.space_types):
        vec = [1.0 if i == idx else 0.0 for i in range(dim)]
        name = item["name"]
        vectors[name.lower()] = vec
        for alias in item.get("aliases", []):
            vectors[alias.lower()] = vec
    return vectors


@pytest.mark.asyncio
async def test_semantic_match_space_type_with_fake_embeddings() -> None:
    taxonomy = load_taxonomy()
    vectors = _space_type_vectors(taxonomy)
    dim = len(taxonomy.space_types)

    async def embed_func(text: str) -> list[float]:
        return vectors.get(text.lower(), [0.0] * dim)

    matcher = SemanticMatcher(taxonomy, threshold=0.75, embed_func=embed_func)
    name, score = await matcher.match("pop-up store", "space_type")
    assert name == "快闪店"
    assert score >= 0.75


@pytest.mark.integration
@pytest.mark.asyncio
async def test_semantic_match_space_type() -> None:
    taxonomy = load_taxonomy()
    matcher = SemanticMatcher(taxonomy, threshold=0.75)
    name, score = await matcher.match("pop-up store", "space_type")
    assert name == "快闪店"
    assert score >= 0.75
