import tempfile
from pathlib import Path

import pytest

from app.services.learning.few_shot_library import Example, FewShotLibrary


@pytest.mark.asyncio
async def test_append_and_retrieve_examples():
    with tempfile.TemporaryDirectory() as tmp:
        lib = FewShotLibrary(data_dir=Path(tmp))
        await lib.append(
            Example(
                input_text="圣诞节 30万 中庭",
                space_type="购物中心中庭",
                theme="圣诞节",
                budget=300000,
                points=["中庭", "DP点"],
            )
        )
        results = await lib.retrieve(space_type="购物中心中庭", theme="圣诞节", top_k=3)
        assert len(results) == 1
        assert results[0].input_text == "圣诞节 30万 中庭"
