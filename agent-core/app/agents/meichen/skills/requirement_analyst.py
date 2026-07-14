from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func

from app.models.database import get_session
from app.models.project import MaterialPrice
from app.services.llm_client import llm_client


class RequirementAnalyst:
    SYSTEM = "你是一位资深美陈设计项目经理，擅长将客户需求转化为清晰、可执行的设计任务书。"

    async def analyze(self, merged_input: dict[str, Any]) -> dict[str, Any]:
        try:
            budget_level = self._classify_budget(merged_input.get("budget"))
            points = self._normalize_points(merged_input.get("points", []))
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
                "design_system_preference": merged_input.get("design_system_preference"),
                "space_description": merged_input.get("space_description", ""),
                "references": merged_input.get("references", []),
                "points": points,
                "raw_inputs": merged_input.get("raw_inputs", []),
            }

            # 生成推荐值
            recommendations = self._generate_recommendations(requirement)
            requirement["recommendations"] = recommendations

            # 应用推荐值到需求（如果用户未提供）
            self._apply_recommendations(requirement, recommendations)

            # LLM 增强分析
            enhanced = await self._llm_enhance(requirement)
            for key, value in enhanced.items():
                if value is not None and value != "" and value != []:
                    requirement[key] = value

            # 约束与冲突检测
            constraints = self._detect_constraints(requirement)
            conflicts = self._detect_conflicts(requirement)
            requirement["constraints"] = constraints
            requirement["conflicts"] = conflicts
            requirement["needs_confirmation"] = len(recommendations) > 0 or len(conflicts) > 0
            requirement["missing_fields"] = self._detect_missing(requirement)
            requirement["is_complete"] = len(requirement["missing_fields"]) == 0

            return requirement
        except Exception as e:
            return self._get_fallback_requirement(merged_input)

    def _generate_recommendations(self, requirement: dict[str, Any]) -> dict[str, dict[str, Any]]:
        recommendations = {}

        space_type = requirement.get("space_type") or ""
        budget = requirement.get("budget") or ""

        # 推荐点位配置
        if not requirement.get("points") or len(requirement.get("points", [])) == 0:
            points_rec = self._recommend_points(space_type, budget)
            if points_rec:
                recommendations["points"] = {
                    "field": "points",
                    "label": "点位配置",
                    "reason": f"根据空间类型'{space_type}'和预算'{budget}'，推荐以下点位配置",
                    "suggestion": points_rec,
                }

        # 推荐目标人群
        if not requirement.get("target_audience"):
            audience_rec = self._recommend_audience(space_type)
            if audience_rec:
                recommendations["target_audience"] = {
                    "field": "target_audience",
                    "label": "目标人群",
                    "reason": f"根据空间类型'{space_type}'，推荐目标人群",
                    "suggestion": audience_rec,
                }

        # 推荐材质
        if not requirement.get("material_restrictions") or len(requirement.get("material_restrictions", [])) == 0:
            material_rec = self._recommend_materials(budget, space_type)
            if material_rec:
                recommendations["material_restrictions"] = {
                    "field": "material_restrictions",
                    "label": "材质建议",
                    "reason": f"根据预算'{budget}'和空间类型'{space_type}'，推荐以下材质",
                    "suggestion": material_rec,
                }

        # 推荐品牌色/配色
        theme = requirement.get("theme") or ""
        if not requirement.get("brand_colors") and not requirement.get("color_preference"):
            color_rec = self._recommend_colors(theme, space_type)
            if color_rec:
                recommendations["brand_colors"] = {
                    "field": "brand_colors",
                    "label": "品牌色/配色",
                    "reason": f"根据主题'{theme}'和空间类型'{space_type}'，推荐以下配色方案",
                    "suggestion": color_rec,
                }

        # 推荐设计风格
        if not requirement.get("style"):
            style_rec = self._recommend_style(theme, space_type)
            if style_rec:
                recommendations["style"] = {
                    "field": "style",
                    "label": "设计风格",
                    "reason": f"根据主题'{theme}'和空间类型'{space_type}'，推荐设计风格",
                    "suggestion": style_rec,
                }

        # 推荐整体串联元素
        if not requirement.get("design_system_preference"):
            ds_rec = self._recommend_design_system_preference(theme, space_type)
            if ds_rec:
                recommendations["design_system_preference"] = {
                    "field": "design_system_preference",
                    "label": "整体串联元素",
                    "reason": f"根据主题'{theme}'和空间类型'{space_type}'，推荐不同点位间的统一元素",
                    "suggestion": ds_rec,
                }

        return recommendations

    def _recommend_points(self, space_type: str, budget: str) -> list[dict[str, str]]:
        space = space_type.lower()
        budget_level = self._classify_budget(budget)

        if "购物中心" in space or "商场" in space:
            if budget_level == "low":
                return [
                    {"name": "中庭", "size": "4m×3m×2.5m", "notes": "主视觉装置"},
                    {"name": "门头", "size": "6m×2m×0.8m", "notes": "入口装饰"},
                ]
            elif budget_level == "medium":
                return [
                    {"name": "中庭", "size": "6m×4m×3m", "notes": "核心主装置"},
                    {"name": "门头", "size": "8m×2.5m×1m", "notes": "主题门头"},
                    {"name": "DP点1", "size": "3m×2m×2.5m", "notes": "互动打卡点"},
                    {"name": "DP点2", "size": "3m×2m×2.5m", "notes": "互动打卡点"},
                ]
            else:
                return [
                    {"name": "中庭", "size": "8m×6m×4m", "notes": "大型沉浸式装置"},
                    {"name": "门头", "size": "10m×3m×1.5m", "notes": "主题门头"},
                    {"name": "DP点1", "size": "4m×3m×3m", "notes": "互动打卡点"},
                    {"name": "DP点2", "size": "4m×3m×3m", "notes": "互动打卡点"},
                    {"name": "DP点3", "size": "4m×3m×3m", "notes": "互动打卡点"},
                    {"name": "灯饰画", "size": "12m×4m", "notes": "通道装饰"},
                ]
        elif "百货" in space:
            if budget_level == "low":
                return [
                    {"name": "主入口", "size": "6m×2.5m×1m", "notes": "入口装饰"},
                    {"name": "中庭", "size": "4m×3m×2.5m", "notes": "主视觉装置"},
                ]
            elif budget_level == "medium":
                return [
                    {"name": "主入口", "size": "8m×3m×1.5m", "notes": "主题门头"},
                    {"name": "中庭", "size": "6m×4m×3m", "notes": "核心主装置"},
                    {"name": "楼层导视", "size": "2m×1m×0.5m", "notes": "楼层装饰"},
                    {"name": "DP点", "size": "3m×2m×2.5m", "notes": "互动打卡点"},
                ]
            else:
                return [
                    {"name": "主入口", "size": "10m×3.5m×2m", "notes": "主题门头"},
                    {"name": "中庭", "size": "8m×6m×4m", "notes": "大型沉浸式装置"},
                    {"name": "楼层导视", "size": "2.5m×1.2m×0.6m", "notes": "楼层装饰"},
                    {"name": "DP点1", "size": "4m×3m×3m", "notes": "互动打卡点"},
                    {"name": "DP点2", "size": "4m×3m×3m", "notes": "互动打卡点"},
                    {"name": "扶梯装饰", "size": "随扶梯长度", "notes": "扶梯周边装饰"},
                ]
        elif "快闪店" in space:
            return [
                {"name": "门头", "size": "4m×2m×1m", "notes": "快闪店入口"},
                {"name": "内部装置", "size": "5m×3m×3m", "notes": "店内核心装置"},
                {"name": "橱窗", "size": "3m×2.5m×0.8m", "notes": "橱窗展示"},
            ]
        elif "展厅" in space:
            return [
                {"name": "序厅", "size": "6m×4m×3m", "notes": "入口欢迎区"},
                {"name": "主展区", "size": "8m×6m×4m", "notes": "核心展示区"},
                {"name": "互动区", "size": "4m×4m×3m", "notes": "体验互动区"},
            ]
        else:
            return [
                {"name": "中庭", "size": "6m×4m×3m", "notes": "核心主装置"},
                {"name": "门头", "size": "8m×2.5m×1m", "notes": "主题门头"},
                {"name": "DP点", "size": "3m×2m×2.5m", "notes": "互动打卡点"},
            ]

    def _recommend_audience(self, space_type: str) -> str:
        space = space_type.lower()
        if "亲子" in space or "儿童" in space:
            return "家庭亲子（25-45岁家长及3-12岁儿童）"
        elif "高端" in space or "奢侈品" in space:
            return "高端商务人群（30-55岁，高消费能力）"
        elif "潮流" in space or "年轻" in space:
            return "年轻潮人（18-30岁，追求时尚潮流）"
        elif "快闪" in space or "品牌" in space:
            return "品牌粉丝及年轻消费者（18-35岁）"
        elif "购物中心" in space or "商场" in space:
            return "全年龄段消费者（家庭、年轻人、老年人）"
        else:
            return "全年龄段消费者"

    def _recommend_materials(self, budget: str, space_type: str) -> list[str]:
        budget_level = self._classify_budget(budget)
        space = space_type.lower()

        if budget_level == "low":
            return ["亚克力", "PVC板", "LED灯带", "仿真绿植", "喷绘"]
        elif budget_level == "medium":
            return ["亚克力", "金属框架", "LED灯带", "玻璃", "仿真绿植", "发光字"]
        else:
            return ["亚克力", "不锈钢框架", "LED显示屏", "玻璃", "真植物", "水晶", "发光字", "镜面"]

    def _recommend_colors(self, theme: str, space_type: str) -> str:
        theme_lower = theme.lower()
        if "海洋" in theme_lower or "蓝色" in theme_lower:
            return "#1E90FF（深海蓝）、#00CED1（青色）、#87CEEB（天蓝）、#FFFFFF（白色）、点缀金色"
        elif "森林" in theme_lower or "绿色" in theme_lower:
            return "#228B22（森林绿）、#90EE90（浅绿）、#8B4513（棕色）、#FFFFFF（白色）"
        elif "新春" in theme_lower or "红色" in theme_lower or "国潮" in theme_lower:
            return "#DC143C（中国红）、#FFD700（金色）、#FFFFFF（白色）、#000000（黑色）"
        elif "轻奢" in theme_lower or "金色" in theme_lower:
            return "#FFD700（金色）、#8B4513（棕色）、#1a1a1a（深灰）、#FFFFFF（白色）"
        elif "科技" in theme_lower or "未来" in theme_lower:
            return "#00FFFF（青色）、#FF00FF（紫色）、#000000（黑色）、#FFFFFF（白色）"
        elif "浪漫" in theme_lower or "粉色" in theme_lower:
            return "#FF69B4（粉色）、#FFC0CB（浅粉）、#FFFFFF（白色）、#87CEEB（天蓝）"
        elif "简约" in theme_lower or "现代" in theme_lower:
            return "#333333（深灰）、#666666（中灰）、#999999（浅灰）、#FFFFFF（白色）"
        else:
            return "#3b82f6（蓝色）、#f59e0b（橙色）、#FFFFFF（白色）、#1e293b（深蓝）"

    def _recommend_style(self, theme: str, space_type: str) -> str:
        theme_lower = theme.lower()
        space = space_type.lower()
        if "新春" in theme_lower or "国潮" in theme_lower:
            return "国潮复古"
        elif "海洋" in theme_lower or "森林" in theme_lower:
            return "自然沉浸式"
        elif "科技" in theme_lower or "未来" in theme_lower:
            return "科技未来"
        elif "轻奢" in theme_lower or "鎏金" in theme_lower:
            return "轻奢高端"
        elif "亲子" in space or "儿童" in space:
            return "童趣温馨"
        elif "快闪" in space or "潮流" in space:
            return "潮流互动"
        else:
            return "现代简约"

    def _recommend_design_system_preference(self, theme: str, space_type: str) -> str:
        theme_lower = theme.lower()
        if "海洋" in theme_lower:
            return "海浪弧线与泡沫造型语言，统一贯穿各点位"
        elif "森林" in theme_lower or "自然" in theme_lower:
            return "植物生长曲线与木质肌理，统一贯穿各点位"
        elif "新春" in theme_lower or "国潮" in theme_lower:
            return "祥云纹样与中国红金色块，统一贯穿各点位"
        elif "科技" in theme_lower or "未来" in theme_lower:
            return "霓虹光带与几何矩阵，统一贯穿各点位"
        elif "轻奢" in theme_lower or "鎏金" in theme_lower:
            return "金属弧线与水晶光点，统一贯穿各点位"
        elif "浪漫" in theme_lower or "爱情" in theme_lower:
            return "心形柔光与渐变纱幔，统一贯穿各点位"
        else:
            return "品牌主题图形与主色调块，统一贯穿各点位"

    def _apply_recommendations(self, requirement: dict[str, Any], recommendations: dict[str, dict[str, Any]]) -> None:
        for key, rec in recommendations.items():
            if key == "points":
                requirement["points"] = rec["suggestion"]
            elif key == "target_audience":
                requirement["target_audience"] = rec["suggestion"]
            elif key == "material_restrictions":
                requirement["material_restrictions"] = rec["suggestion"]
            elif key == "brand_colors":
                requirement["brand_colors"] = rec["suggestion"]
            elif key == "style":
                requirement["style"] = rec["suggestion"]
            elif key == "design_system_preference":
                requirement["design_system_preference"] = rec["suggestion"]

    def _detect_missing(self, requirement: dict[str, Any]) -> list[dict[str, Any]]:
        missing = []
        if not requirement.get("theme"):
            missing.append({"field": "theme", "label": "项目主题", "question": "这次美陈设计的主题是什么？比如：夏日海洋、新春国潮、轻奢鎏金、未来科技等。"})
        if not requirement.get("space_type"):
            missing.append({"field": "space_type", "label": "空间类型", "question": "设计用在什么类型的商业空间？比如：购物中心中庭、百货入口、快闪店、展厅、步行街等。"})
        if not requirement.get("budget"):
            missing.append({"field": "budget", "label": "预算区间", "question": "项目预算大概是多少？比如：5万、10-15万、30万以内等。"})

        points = requirement.get("points") or []
        valid_points = [p for p in points if isinstance(p, dict) and p.get("name")]
        if not valid_points:
            missing.append({"field": "points", "label": "涉及点位", "question": "涉及哪些点位？每个点位有几个？比如：中庭1个、门头2个、DP点3个、灯饰画1组等。"})

        return missing

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

        db = get_session()
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

    def _normalize_points(self, points: list[Any]) -> list[dict[str, Any]]:
        import re
        normalized = []
        for p in points:
            if not isinstance(p, dict):
                continue
            point = dict(p)
            notes = str(point.get("notes", "") or "")
            if not point.get("size") and notes:
                size_match = re.search(r"(\d+[\.\d]*)\s*[m米]\s*[×xX*]\s*(\d+[\.\d]*)\s*[m米]?\s*(?:[×xX*]\s*(\d+[\.\d]*)\s*[m米]?)?", notes)
                if size_match:
                    size = f"{size_match.group(1)}m×{size_match.group(2)}m"
                    if size_match.group(3):
                        size += f"×{size_match.group(3)}m"
                    point["size"] = size
            normalized.append(point)
        return normalized

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
            "points": merged_input.get("points", []),
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
            "missing_fields": self._detect_missing({
                "theme": merged_input.get("theme"),
                "space_type": merged_input.get("space_type"),
                "budget": merged_input.get("budget"),
                "style": merged_input.get("style"),
                "target_audience": merged_input.get("target_audience"),
                "color_preference": merged_input.get("color_preference"),
                "brand_colors": merged_input.get("brand_colors"),
                "material_restrictions": merged_input.get("material_restrictions", []),
                "design_system_preference": merged_input.get("design_system_preference"),
                "points": self._normalize_points(merged_input.get("points", [])),
            }),
            "is_complete": False,
        }
