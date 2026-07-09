from unittest.mock import AsyncMock

import pytest

from app.services.learning.feedback_reader import ImageFeedbackRecord
from app.services.learning.prompt_version_tracker import PromptVersionTracker


@pytest.mark.asyncio
async def test_compare_template_versions():
    tracker = PromptVersionTracker(reader=AsyncMock())
    tracker.reader.list_image_feedback_by_version = AsyncMock(
        side_effect=lambda v: {
            "atrium-v1": [
                ImageFeedbackRecord("image_feedback", "composition", "中庭", 0, "atrium-v1", "good"),
                ImageFeedbackRecord("image_feedback", "composition", "中庭", 1, "atrium-v1", "bad"),
            ],
            "atrium-v2": [
                ImageFeedbackRecord("image_feedback", "composition", "中庭", 0, "atrium-v2", "good"),
                ImageFeedbackRecord("image_feedback", "composition", "中庭", 1, "atrium-v2", "good"),
            ],
        }.get(v, [])
    )

    report = await tracker.compare_versions(["atrium-v1", "atrium-v2"])
    assert report["atrium-v1"].negative == 1
    assert report["atrium-v2"].positive == 2
