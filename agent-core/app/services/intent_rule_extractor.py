from __future__ import annotations

import re

import jieba  # type: ignore[import-untyped]
from rapidfuzz import fuzz

from app.services.intent_schemas import IntentOutput
from app.services.taxonomy_loader import Taxonomy

_FUZZY_THRESHOLD = 0.75
_FUZZY_THRESHOLD_CRITICAL = 0.85


class IntentRuleExtractor:
    """确定性规则提取器，用于补齐 LLM 未识别的字段。"""

    def __init__(self, taxonomy: Taxonomy):
        self.taxonomy = taxonomy
        self._load_jieba_dict()

    def _load_jieba_dict(self) -> None:
        terms: list[str] = []
        sources = (
            self.taxonomy.space_types
            + self.taxonomy.points
            + self.taxonomy.budget_levels
            + self.taxonomy.styles
            + self.taxonomy.materials
        )
        for item in sources:
            terms.append(item["name"])
            terms.extend(item.get("aliases", []))
        for term in set(terms):
            jieba.add_word(term, freq=1000)

    async def extract(self, text: str) -> IntentOutput:
        tokens = [t for t in jieba.lcut(text) if t.strip()]
        output = IntentOutput()

        output.space_type = self._extract_space_type(text, tokens)
        output.points = self._extract_points(text, tokens)
        output.theme = self._extract_theme(text, tokens)
        output.budget = self._extract_budget(text)
        output.style = self._extract_style(text, tokens)
        output.material_restrictions = self._extract_material_restrictions(text)
        output.allowed_materials = self._extract_allowed_materials(text)
        output.timeline = self._extract_regex_field(
            text, r"(?:工期|时间|timeline)\s*(?:为|是|：|:)?\s*([^\n，。]+)"
        )
        output.color_preference = self._extract_regex_field(
            text, r"(?:颜色|色彩|color)\s*(?:为|是|：|:)?\s*([^\n，。]+)"
        )
        return output

    def _extract_space_type(self, text: str, tokens: list[str]) -> str | None:
        return self._match_field(
            text, tokens, self.taxonomy.space_type_names, self.taxonomy.alias_to_space_type
        )

    def _extract_style(self, text: str, tokens: list[str]) -> str | None:
        return self._match_field(
            text, tokens, self.taxonomy.style_names, self.taxonomy.alias_to_style
        )

    def _match_field(
        self,
        text: str,
        tokens: list[str],
        exact_names: set[str],
        alias_map: dict[str, str],
    ) -> str | None:
        # 1. 精确匹配
        for token in tokens:
            if token in exact_names:
                return token

        # 2. 别名匹配
        for token in tokens:
            key = token.lower()
            if key in alias_map:
                return alias_map[key]

        # 3. 子串匹配（优先最长）
        all_targets: dict[str, str] = {}
        for name in exact_names:
            all_targets[name] = name
        for alias, standard in alias_map.items():
            all_targets[alias] = standard

        candidates: list[tuple[str, str]] = []
        text_lower = text.lower()
        for target, standard in all_targets.items():
            if len(target) >= 2 and target in text_lower:
                candidates.append((target, standard))
        if candidates:
            candidates.sort(key=lambda x: len(x[0]), reverse=True)
            return candidates[0][1]

        # 4. 模糊匹配
        best: tuple[str, float] | None = None
        for token in tokens:
            for target, standard in all_targets.items():
                score = fuzz.ratio(token, target) / 100.0
                if score >= _FUZZY_THRESHOLD and (best is None or score > best[1]):
                    best = (standard, score)
        if best and best[1] >= _FUZZY_THRESHOLD_CRITICAL:
            return best[0]
        return None

    def _extract_points(self, text: str, _tokens: list[str]) -> list[str]:
        # _tokens is intentionally unused: point extraction uses substring matching over the full text
        # rather than token-level matching, so tokens are not required.
        found: list[str] = []
        seen: set[str] = set()
        all_point_targets: dict[str, str] = {}
        for name in self.taxonomy.point_names:
            all_point_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_point.items():
            all_point_targets[alias] = standard

        text_lower = text.lower()
        for target, standard in all_point_targets.items():
            if len(target) >= 2 and target in text_lower and standard not in seen:
                found.append(standard)
                seen.add(standard)
        return found

    def _extract_theme(self, text: str, tokens: list[str]) -> str | None:
        # 1. 显式 "主题为X" / "主题：X" / "theme: X"：用户明确指定主题，保留原值
        match = re.search(r"(?:主题|概念|theme)\s*(?:为|是|：|:)\s*([^\n，。]+)", text)
        if match:
            candidate = match.group(1).strip()
            if candidate and not self._is_known_non_theme(
                candidate, allow_style=True
            ):
                return candidate

        # 2. 显式标记：X主题 / X概念 / Xtheme / X风
        # 基于 token 定位，避免正则过捕获前置上下文
        markers = {"主题", "概念", "theme", "风"}
        marker_found = False
        for i, token in enumerate(tokens):
            if token not in markers or i == 0:
                continue
            marker_found = True
            candidate = tokens[i - 1]
            if token == "风":
                # 风通常表示 style；如果 candidate 或 candidate+风 命中 style，则不作为 theme
                candidate_key = candidate.lower()
                with_marker_key = (candidate + "风").lower()
                if (
                    candidate_key in self.taxonomy.style_names
                    or candidate_key in self.taxonomy.alias_to_style
                    or with_marker_key in self.taxonomy.style_names
                    or with_marker_key in self.taxonomy.alias_to_style
                ):
                    continue
            if not self._is_known_non_theme(candidate, allow_style=True):
                return candidate

        # 3. 处理 jieba 将 "海洋主题" 等合并为一个 token 的情况
        match = re.search(r"([^\n，。]+?)(?:主题|概念|theme)", text)
        if match:
            candidate = match.group(1).strip()
            candidate = re.sub(r"^[为是：:]\s*", "", candidate)
            if candidate and not self._is_known_non_theme(candidate, allow_style=True):
                return candidate

        # 若已出现显式标记但被跳过（如 style 风），不再使用裸词启发式
        if marker_found:
            return None

        # 裸词启发式：输入较短、且未命中 space_type/point/style/material/budget 的名词
        if len(text) <= 8 and len(tokens) <= 3:
            budget_match = self._extract_budget(text)
            for token in tokens:
                if (
                    len(token) >= 2
                    and token not in markers
                    and not self._is_known_non_theme(token, budget_match)
                ):
                    return token
        return None

    def _is_known_non_theme(
        self,
        token: str,
        budget_match: str | None = None,
        allow_style: bool = False,
    ) -> bool:
        # 纯数字或 budget 已匹配到的子串不应被视为 theme
        if token.isdigit():
            return True
        if budget_match and token in budget_match:
            return True
        if token in self.taxonomy.space_type_names:
            return True
        if token in self.taxonomy.point_names:
            return True
        if token in self.taxonomy.budget_level_names:
            return True
        if token in self.taxonomy.material_names:
            return True
        lowered = token.lower()
        if lowered in self.taxonomy.alias_to_space_type:
            return True
        if lowered in self.taxonomy.alias_to_point:
            return True
        if lowered in self.taxonomy.alias_to_budget_level:
            return True
        if lowered in self.taxonomy.alias_to_material:
            return True
        if allow_style:
            return False
        if token in self.taxonomy.style_names:
            return True
        if lowered in self.taxonomy.alias_to_style:
            return True
        # 如果 token 以 "风" 结尾且去掉 "风" 后是 style，也视为 style 而非 theme
        if token.endswith("风") and len(token) > 1:
            prefix = token[:-1].lower()
            if prefix in self.taxonomy.style_names or prefix in self.taxonomy.alias_to_style:
                return True
        return False

    def _extract_budget(self, text: str) -> str | None:
        range_pattern = r"([零一二两三四五六七八九十百千万亿\d]+(?:\.\d+)?)\s*[~\-到至]\s*([零一二两三四五六七八九十百千万亿\d]+(?:\.\d+)?)\s*[万w千k元]?"
        match = re.search(range_pattern, text)
        if match:
            return match.group(0).strip()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|w|千|k|元)", text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        match = re.search(r"([零一二两三四五六七八九十百千万亿]+)\s*[万w千k元]?", text)
        if match:
            return match.group(0).strip()
        return None

    def _extract_material_restrictions(self, text: str) -> list[str]:
        results: list[str] = []
        stop_chars = "，。；;"
        patterns = [
            rf"(?:不要|不用|禁用|避免|不想用|别用)\s*([^{stop_chars}]+)",
            rf"(?:排除|去除|不要出现)\s*([^{stop_chars}]+)",
        ]
        all_targets: dict[str, str] = {}
        for name in self.taxonomy.material_names:
            all_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_material.items():
            all_targets[alias] = standard

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                fragment = match.group(1).strip().lower()
                for target, standard in all_targets.items():
                    if target in fragment and standard not in results:
                        results.append(standard)
                if not results:
                    results.append(match.group(1).strip())
        return results

    def _extract_allowed_materials(self, text: str) -> list[str]:
        results: list[str] = []
        stop_chars = "，。；;"
        patterns = [
            rf"([^{stop_chars}]+?)\s*(?:可以|可用|能用|允许使用)",
            rf"(?:可以|可用|能用|允许使用)\s*([^{stop_chars}]+)",
        ]
        all_targets: dict[str, str] = {}
        for name in self.taxonomy.material_names:
            all_targets[name] = name
        for alias, standard in self.taxonomy.alias_to_material.items():
            all_targets[alias] = standard

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                fragment = match.group(1).strip().lower()
                for target, standard in all_targets.items():
                    if target in fragment and standard not in results:
                        results.append(standard)
        return results

    def _extract_regex_field(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
