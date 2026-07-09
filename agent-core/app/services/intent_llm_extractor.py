from __future__ import annotations

import json
import re
from typing import Any, Protocol

from pydantic import ValidationError

from app.services.intent_schemas import IntentOutput
from app.services.learning.few_shot_library import Example, FewShotLibrary
from app.services.llm_client import llm_client as _default_llm_client
from app.services.taxonomy_loader import Taxonomy, load_taxonomy


class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        ...


_INTENT_SYSTEM_PROMPT = """你是一位美陈设计需求分析专家。请从用户的自然语言输入中提取结构化设计需求，并输出为 JSON。

提取规则：
1. 空间类型（space_type）尽量使用标准名称；如果用户描述不在标准列表中，保留原值。
2. 主题（theme）、预算（budget）、颜色偏好（color_preference）、品牌定位（brand_positioning）、目标受众（target_audience）、工期（timeline）是开放字段，直接从用户输入中提取，不要过度推断。
3. 预算可以是数字（元）或字符串（如"30万"、"300k"、"二十万到三十万"）。
4. 材质限制（material_restrictions）列出用户明确不想使用的材质；allowed_materials 列出用户明确允许的材质。
5. 点位（points）使用标准点位名称；支持多个点位。
6. 如果某个字段用户没有提到，输出 null 或空列表，不要编造。
7. 输出必须是合法 JSON，不要包含任何解释或 markdown 代码块。"""


class IntentLLMExtractor:
    """LLM 结构化输出提取器。"""

    def __init__(
        self,
        taxonomy: Taxonomy | None = None,
        llm_client: LLMClient | None = None,
        max_retries: int = 2,
        few_shot_library: FewShotLibrary | None = None,
    ):
        self.taxonomy = taxonomy or load_taxonomy()
        self._llm_client = llm_client or _default_llm_client
        self._max_retries = max_retries
        self._few_shot_library = few_shot_library

    def _taxonomy_prompt_fragment(self) -> str:
        space_types = [s["name"] for s in self.taxonomy.space_types]
        points = [p["name"] for p in self.taxonomy.points]
        styles = [s["name"] for s in self.taxonomy.styles]
        materials = [m["name"] for m in self.taxonomy.materials]
        return (
            "\n参考 taxonomy（允许输出列表之外的值）：\n"
            f"- 空间类型候选：{', '.join(space_types)}\n"
            f"- 点位候选：{', '.join(points)}\n"
            f"- 风格候选：{', '.join(styles)}\n"
            f"- 材质候选：{', '.join(materials)}\n"
        )

    async def _build_prompt(self, text: str) -> str:
        schema_json = IntentOutput.model_json_schema()
        return (
            f"用户输入：\"{text}\"\n\n"
            "请提取设计需求并输出符合以下 JSON Schema 的对象：\n"
            f"{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n"
            f"{self._taxonomy_prompt_fragment()}"
            f"{await self._few_shot_prompt_fragment(text)}"
        )

    async def _few_shot_prompt_fragment(self, text: str) -> str:
        if self._few_shot_library is None:
            return ""
        examples = await self._few_shot_library.retrieve(
            space_type=self._extract_space_type_hint(text),
            theme=self._extract_theme_hint(text),
            top_k=3,
        )
        if not examples:
            return ""
        rendered = "\n参考示例（输入 -> 输出）：\n" + "\n".join(
            f"- 输入：{e.input_text}\n  输出：{self._example_output(e)}" for e in examples
        )
        return rendered + "\n"

    def _extract_space_type_hint(self, text: str) -> str | None:
        for name in self.taxonomy.space_type_names:
            if name in text:
                return name
        return None

    def _extract_theme_hint(self, text: str) -> str | None:
        match = re.search(r"([^，。]+?)(?:主题|theme)", text)
        if match:
            return match.group(1).strip()
        return None

    def _example_output(self, example: Example) -> str:
        parts = [f"space_type: {example.space_type}"]
        if example.theme:
            parts.append(f"theme: {example.theme}")
        if example.budget:
            parts.append(f"budget: {example.budget}")
        if example.points:
            parts.append(f"points: {', '.join(example.points)}")
        return "; ".join(parts)

    def _parse_llm_output(self, raw: str) -> IntentOutput | None:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```")
            cleaned = cleaned.removesuffix("```").strip()
        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        try:
            output = IntentOutput.model_validate(data)
        except ValidationError:
            return None
        if self._is_empty_output(output):
            return None
        return output

    @staticmethod
    def _is_empty_output(output: IntentOutput) -> bool:
        return (
            output.space_type is None
            and output.theme is None
            and output.style is None
            and output.budget is None
            and not output.points
            and not output.material_restrictions
            and not output.allowed_materials
            and output.color_preference is None
            and output.brand_positioning is None
            and output.target_audience is None
            and output.timeline is None
            and output.design_system_preference is None
            and not output.special_requirements
        )

    async def extract(self, text: str) -> IntentOutput | None:
        prompt = await self._build_prompt(text)
        for attempt in range(self._max_retries + 1):
            try:
                raw = await self._llm_client.complete(
                    system_prompt=_INTENT_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    json_mode=True,
                    temperature=0.3,
                )
                parsed = self._parse_llm_output(raw)
                if parsed is not None:
                    return parsed
            except Exception as e:
                print(f"IntentLLMExtractor attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                if attempt == self._max_retries:
                    break
        return None
