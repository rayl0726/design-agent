from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func

from app.models.database import SessionLocal
from app.models.project import MaterialPrice
from app.services.llm_client import llm_client


class RequirementAnalyst:
    SYSTEM = "你是一位资深美陈设计项目经理，擅长将客户需求转化为清晰、可执行的设计任务书。"

    async def analyze(self, merged_input: dict[str, Any]) -> dict[str, Any]:
        try:
            budget_level = self._classify_budget(merged_input.get("budget"))
            requirement = {
                "space_type": merged_input.get("space_type"),
                "budget": merged_input.get("budget"),
                "budget_level": budget_level,
                "theme": merged_input.get("theme"),
                "style": merged_input.get("style"),
                "target_audience": merged_input.get("target_audience"),
                "timeline": merged_input.get("timeline"),
                "material_restrictions": merged_input.get("material_restrictions", []),
                "special_requirements": merged_input.get("special_requirements", []),
                "color_preference": merged_input.get("color_preference"),
                "brand_positioning": merged_input.get("brand_positioning"),
                "space_description": merged_input.get("space_description", ""),
                "references": merged_input.get("references", []),
                "raw_inputs": merged_input.get("raw_inputs", []),
            }

            # LLM 增强分析
            enhanced = await self._llm_enhance(requirement)
            requirement.update(enhanced)

            # 约束与冲突检测
            constraints = self._detect_constraints(requirement)
            conflicts = self._detect_conflicts(requirement)
            requirement["constraints"] = constraints
            requirement["conflicts"] = conflicts
            requirement["needs_confirmation"] = len(conflicts) > 0

            return requirement
        except Exception as e:
            return self._get_fallback_requirement(merged_input)

    def _classify_budget(self, budget_text: str | None) -> str | None:
        if not budget_text:
            return None
        text = budget_text.lower()
        # 提取数字
        import re
        numbers = re.findall(r"\d+", text)
        if not numbers:
            return None
        value = int(numbers[0])
        # 判断单位
        if "万" in text or "w" in text:
            value *= 10000
        elif "千" in text:
            value *= 1000

        db = SessionLocal()
        try:
            prices = [p[0] for p in db.query(MaterialPrice.price_low).filter(MaterialPrice.price_low.isnot(None)).all()]
            if len(prices) < 3:
                # 无历史数据，使用启发式规则
                if value < 50000:
                    return "low"
                elif value < 200000:
                    return "medium"
                else:
                    return "high"
            prices.sort()
            low_q = prices[int(len(prices) * 0.33)]
            high_q = prices[int(len(prices) * 0.66)]
            if value < low_q:
                return "low"
            elif value < high_q:
                return "medium"
            else:
                return "high"
        finally:
            db.close()

    async def _llm_enhance(self, requirement: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "请根据以下设计需求，生成补充分析和建议，输出 JSON（只输出 JSON）：\n\n"
            f"{json.dumps(requirement, ensure_ascii=False, indent=2)}\n\n"
            "输出字段：\n"
            '{"color_palette": ["#RRGGBB"], "material_suggestions": ["材料建议"], '
            '"mood_keywords": ["氛围关键词"], "design_direction": "设计方向建议", '
            '"spatial_notes": "空间注意事项", "risk_hints": ["风险提示"]}'
        )
        raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"parse_error": True, "raw": raw}

    def _detect_constraints(self, requirement: dict[str, Any]) -> list[dict[str, Any]]:
        constraints = []
        restrictions = requirement.get("material_restrictions", [])
        for r in restrictions:
            constraints.append({"type": "explicit", "content": r, "severity": "hard"})

        timeline = requirement.get("timeline")
        if timeline and ("急" in timeline or "紧" in timeline or "天" in timeline):
            constraints.append({"type": "inferred", "content": f"工期紧张：{timeline}", "severity": "medium"})

        budget_level = requirement.get("budget_level")
        if budget_level == "low":
            constraints.append({"type": "inferred", "content": "预算有限，需控制成本", "severity": "medium"})

        return constraints

    def _detect_conflicts(self, requirement: dict[str, Any]) -> list[dict[str, Any]]:
        conflicts = []
        budget_level = requirement.get("budget_level")
        theme = requirement.get("theme") or ""

        # 主题与预算冲突
        luxury_themes = ["奢华", "高端", "钻石", "水晶", "鎏金"]
        if budget_level == "low" and any(t in theme for t in luxury_themes):
            conflicts.append({
                "type": "budget_theme_mismatch",
                "description": f"预算档次为低，但主题'{theme}'偏向高端，可能需要调整预期",
                "severity": "high",
            })

        # 工期与复杂度冲突
        timeline = requirement.get("timeline", "") or ""
        restrictions = requirement.get("material_restrictions", []) or []
        if ("急" in timeline or "紧" in timeline) and len(restrictions) > 3:
            conflicts.append({
                "type": "timeline_complexity_mismatch",
                "description": "工期紧张但限制条件较多，可能影响落地可行性",
                "severity": "medium",
            })

        return conflicts

    def _get_fallback_requirement(self, merged_input: dict[str, Any]) -> dict[str, Any]:
        text = merged_input.get("text", "") or ""
        theme = merged_input.get("theme")
        if not theme:
            import re
            theme_match = re.search(r"(主题|风格|氛围|概念)\s*[：:]\s*([^\n]+)", text)
            theme = theme_match.group(2).strip() if theme_match else "现代商业"

        style = merged_input.get("style") or "现代简约"
        space_type = merged_input.get("space_type") or "中庭"

        return {
            "space_type": space_type,
            "budget": merged_input.get("budget"),
            "budget_level": "medium",
            "theme": theme,
            "style": style,
            "target_audience": "全年龄段消费者",
            "timeline": merged_input.get("timeline"),
            "material_restrictions": [],
            "special_requirements": [],
            "color_preference": None,
            "brand_positioning": None,
            "space_description": f"{space_type}商业空间美陈设计",
            "references": [],
            "raw_inputs": [],
            "color_palette": ["#FFFFFF", "#1a1a2e", "#16213e", "#0f3460"],
            "material_suggestions": ["亚克力", "LED灯带", "金属框架", "玻璃"],
            "mood_keywords": ["现代", "时尚", "明亮", "高端"],
            "design_direction": f"以{theme}为主题，{style}风格，打造沉浸式商业体验空间",
            "spatial_notes": f"{space_type}空间需考虑人流动线和视觉焦点",
            "risk_hints": [],
            "constraints": [],
            "conflicts": [],
            "needs_confirmation": False,
        }
