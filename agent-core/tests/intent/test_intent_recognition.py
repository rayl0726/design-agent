import pytest

from app.services.embedding_client import embedding_client
from app.services.intent_recognition import IntentRecognitionService
from app.services.intent_recognition_result import FieldSource
from app.services.llm_client import llm_client


@pytest.fixture(autouse=True)
def _stub_external_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _complete(*args: object, **kwargs: object) -> str:
        return "{}"

    async def _embed(*args: object, **kwargs: object) -> list[float]:
        return [0.0] * 64

    monkeypatch.setattr(llm_client, "complete", _complete)
    monkeypatch.setattr(embedding_client, "embed", _embed)


@pytest.fixture
def service() -> IntentRecognitionService:
    return IntentRecognitionService()


@pytest.mark.asyncio
async def test_exact_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("购物中心中庭海洋主题")
    assert result.space_type is not None
    assert result.space_type.value == "购物中心中庭"
    assert result.space_type.source == FieldSource.EXACT


@pytest.mark.asyncio
async def test_alias_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("popup store 快闪")
    assert result.space_type is not None
    assert result.space_type.value == "快闪店"
    assert result.space_type.source == FieldSource.ALIAS


@pytest.mark.asyncio
async def test_fuzzy_space_type(service: IntentRecognitionService) -> None:
    result = await service.recognize("百货入口国潮美陈")
    assert result.space_type is not None
    assert result.space_type.value == "百货入口"


@pytest.mark.asyncio
async def test_extract_budget(service: IntentRecognitionService) -> None:
    result = await service.recognize("购物中心中庭，预算15万")
    assert result.budget is not None
    assert result.budget.value == 150000


@pytest.mark.asyncio
async def test_match_points(service: IntentRecognitionService) -> None:
    result = await service.recognize("新春快闪店，门头×2，DP点×3")
    names = [str(p.value.get("name", "")) for p in result.points]
    assert "门头" in names
    assert "DP点" in names
