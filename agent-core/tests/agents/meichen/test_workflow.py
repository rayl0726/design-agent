import pytest
from unittest.mock import AsyncMock, patch

from app.agents.meichen.workflow import run_meichen_workflow


@pytest.mark.asyncio
async def test_requirement_passed_through_workflow():
    """验证 workflow 把原始 requirement 透传给 L2/L3 的 wrapper。"""
    with patch("app.agents.meichen.skills.input_parser.parse_input", new_callable=AsyncMock) as mock_parse:
        with patch("app.agents.meichen.skills.requirement_analyst.analyze_requirement", new_callable=AsyncMock) as mock_analyze:
            with patch("app.agents.meichen.skills.concept_designer.design_concepts", new_callable=AsyncMock) as mock_concepts:
                with patch("app.agents.meichen.skills.visual_designer.generate_visuals", new_callable=AsyncMock) as mock_visuals:
                    with patch("app.agents.meichen.skills.technical_designer.design_technical", new_callable=AsyncMock) as mock_technical:
                        inputs = {"text": "海洋主题购物中心中庭，预算15万"}
                        parsed = {"source_type": "text", "theme": "海洋"}
                        requirement = {
                            "theme": "海洋",
                            "style": "自然沉浸式",
                            "space_type": "购物中心中庭",
                            "budget": "15万",
                        }
                        concepts = {"level": "L1", "ideas": []}
                        visuals = {"level": "L2"}
                        technical = {"level": "L3"}

                        mock_parse.return_value = parsed
                        mock_analyze.return_value = requirement
                        mock_concepts.return_value = concepts
                        mock_visuals.return_value = visuals
                        mock_technical.return_value = technical

                        result = await run_meichen_workflow(inputs)

                        mock_parse.assert_awaited_once_with(inputs)
                        mock_analyze.assert_awaited_once_with(parsed)
                        mock_concepts.assert_awaited_once_with(requirement)
                        mock_visuals.assert_awaited_once_with(concepts, requirement)
                        mock_technical.assert_awaited_once_with(concepts, visuals, requirement)

                        assert result["l1_output"] is requirement
                        assert result["l2_output"] is concepts
                        assert result["l3_output"] is technical
                        assert result["visuals"] is visuals
