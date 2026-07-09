import pytest
from unittest.mock import AsyncMock

from app.services.learning.feedback_reader import FeedbackReader


@pytest.mark.asyncio
async def test_list_unprocessed_intent_corrections():
    reader = FeedbackReader(db_url="sqlite+aiosqlite:///:memory:")
    reader._execute = AsyncMock(return_value=[
        {"intent_field": "space_type", "original_value": "商场", "corrected_value": "购物中心中庭", "count": 3}
    ])
    results = await reader.list_unprocessed_intent_corrections()
    assert len(results) == 1
    assert results[0].original_value == "商场"
    assert results[0].count == 3
