import json
from typing import Any

from app.core.config import settings
from app.services.image_generation import image_generation
from app.services.llm_client import llm_client


class ConceptDesignerAgent:
    SYSTEM = "你是一位拥有 15 年经验的资深美陈设计师，擅长将商业需求转化为打动人心的设计故事。你只输出合法 JSON，不输出任何解释或 markdown 标记。"

    async def design(self, requirement: dict[str, Any], retrieval: dict[str, Any]) -> dict[str, Any]:
        try:
            ideas = await self._generate_ideas(requirement, retrieval)
            return {
                "level": "L1",
                "ideas": ideas,
            }
        except Exception as e:
            print(f"[ConceptDesigner] design failed: {e}")
            return await self._get_fallback_design(requirement)

    async def _generate_ideas(
        self, requirement: dict[str, Any], retrieval: dict[str, Any]
    ) -> list[dict[str, Any]]:
        compact_req = self._compact_requirement(requirement)
        theme = compact_req.get("theme", "") or "未命名主题"
        space_type = compact_req.get("space_type", "") or "商业空间"
        points = compact_req.get("points", [])
        point_desc = self._format_points(points)
        budget = compact_req.get("budget", "")
        prompt = (
            f"你是一位资深美陈设计师。请为以下项目生成 {settings.idea_count} 个差异化创意方向。\n\n"
            f"项目主题：{theme}\n"
            f"空间类型：{space_type}\n"
            f"预算：{budget}\n"
            f"涉及点位：{point_desc}\n"
            f"完整需求：{json.dumps(compact_req, ensure_ascii=False)}\n\n"
            f"参考案例摘要：{retrieval.get('summary', '')[:600]}\n\n"
            "严格要求：\n"
            f"1. 必须输出 JSON 数组，共 {settings.idea_count} 个对象，不要任何 markdown 代码块标记\n"
            "2. 每个创意的 title、theme、concept、atmosphere 必须明确体现项目主题、空间类型和点位\n"
            "3. applicablePoints 必须说明每个点位（中庭/门头/DP点等）具体怎么布置\n"
            f"4. {settings.idea_count} 个创意之间要有明显差异：不同视觉风格、不同空间策略、不同互动方式\n"
            "5. 描述要具体、详细，让甲方一眼能看懂\n"
            "6. 每个创意必须提供 design_system 对象，定义全局设计语言\n"
            "7. 每个创意必须提供 points 数组，为每个点位生成左/中/右三个视角的 AI 绘画提示词\n"
            "8. 同一点位的三个提示词只能改相机角度（left/center/right view），场景内容必须完全一致\n"
            "9. 所有点位的提示词必须引用 design_system 中的核心元素、色板、材质\n"
            "10. 所有提示词必须包含：'simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography, high quality rendering'\n\n"
            "每个创意对象必须包含以下字段：\n"
            '- title: 创意标题（10字以内，必须包含主题关键词）\n'
            '- theme: 主题概念（50-80字，紧扣主题、空间、点位）\n'
            '- concept: 核心概念（30字以内）\n'
            '- style: 设计风格\n'
            '- colorPalette: 颜色数组，每项包含 name 和 hex\n'
            '- materials: 主要材质\n'
            '- design_system: 对象，包含核心设计语言定义（见下方说明）\n'
            '- points: 数组，每个元素是一个点位对象（见下方说明）\n'
            '- applicablePoints: 适用点位及布置方式（必须分点说明）\n'
            '- spatialLayout: 空间布局描述\n'
            '- designHighlights: 设计亮点（3-5条，用逗号或分号分隔）\n'
            '- atmosphere: 氛围描述（80字左右）\n'
            '- estimatedBudget: 预算参考\n\n'
            "design_system 对象必须包含：\n"
            '- core_element: 核心视觉符号（如"翻涌的海浪弧线"）\n'
            '- color_palette: 全局色板描述（文字描述，不是数组）\n'
            '- material_language: 主材质体系（如"亚克力、金属、LED"）\n'
            '- lighting_mood: 灯光调性（如"暖白光，营造温馨氛围"）\n'
            '- connection_across_points: 点位间呼应方式（如"各点位统一使用海浪曲线造型"）\n\n'
            "points 数组中每个点位对象必须包含：\n"
            '- point_name: 点位名称（如"中庭""门头A""DP点1"）\n'
            '- description: 该点位在该创意下的具体设计描述\n'
            '- left_prompt: 左视角英文 AI 绘画提示词（100-200词）\n'
            '- center_prompt: 中视角英文 AI 绘画提示词（100-200词）\n'
            '- right_prompt: 右视角英文 AI 绘画提示词（100-200词）\n\n'
            "输出示例：[{\"title\":\"...\",\"theme\":\"...\",\"design_system\":{\"core_element\":\"...\",\"color_palette\":\"...\",\"material_language\":\"...\",\"lighting_mood\":\"...\",\"connection_across_points\":\"...\"},\"points\":[{\"point_name\":\"中庭\",\"description\":\"...\",\"left_prompt\":\"...\",\"center_prompt\":\"...\",\"right_prompt\":\"...\"}],...},{...}]"
        )
        raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
        print(f"[ConceptDesigner] raw length={len(raw) if raw else 0}")
        return self._parse_ideas(raw, requirement)

    def _format_points(self, points: list[dict[str, Any]]) -> str:
        if not points:
            return "未指定"
        parts = []
        for p in points:
            name = p.get("name", "")
            count = p.get("count", 1)
            notes = p.get("notes", "")
            if name:
                item = f"{name}×{count}"
                if notes and notes != "未知":
                    item += f"({notes})"
                parts.append(item)
        return "、".join(parts) if parts else "未指定"

    def _compact_requirement(self, requirement: dict[str, Any]) -> dict[str, Any]:
        """精简需求字段，避免 prompt 过长。"""
        return {
            "theme": requirement.get("theme", ""),
            "space_type": requirement.get("space_type", ""),
            "budget": requirement.get("budget", ""),
            "style": requirement.get("style", ""),
            "points": requirement.get("points", []),
            "notes": requirement.get("notes", ""),
        }

    def _parse_ideas(self, raw: str, requirement: dict[str, Any]) -> list[dict[str, Any]]:
        if not raw or not raw.strip():
            return self._fallback_ideas(requirement)

        cleaned = raw.strip()
        # 去掉 markdown 代码块标记
        if cleaned.startswith("```"):
            cleaned = cleaned[cleaned.find("\n") + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

        ideas = None
        # 尝试直接解析
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                ideas = parsed
            elif isinstance(parsed, dict):
                if "ideas" in parsed and isinstance(parsed["ideas"], list):
                    ideas = parsed["ideas"]
                else:
                    # 可能整个对象是一个 idea，或者对象嵌套在 theme 里
                    ideas = [parsed]
        except json.JSONDecodeError:
            # 尝试提取第一个 [ ... ] 数组
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(cleaned[start:end + 1])
                    if isinstance(parsed, list):
                        ideas = parsed
                except json.JSONDecodeError:
                    pass

        if not ideas:
            return self._fallback_ideas(requirement)

        result = []
        for idea in ideas:
            if not isinstance(idea, dict):
                continue
            # 处理 theme 字段嵌套 JSON 字符串的脏数据
            for key in ["theme", "concept", "style", "materials", "applicablePoints", "spatialLayout", "designHighlights", "atmosphere", "estimatedBudget"]:
                value = idea.get(key)
                if isinstance(value, str):
                    value = value.strip()
                    if value.startswith("{") and value.endswith("}"):
                        try:
                            inner = json.loads(value)
                            if isinstance(inner, dict):
                                # 如果是 theme 嵌套了对象，尝试提取其中的 theme 或 title
                                if key == "theme" and "theme" in inner:
                                    idea[key] = inner.get("theme", "")
                                elif key == "title" and "title" in inner:
                                    idea[key] = inner.get("title", "")
                                else:
                                    idea[key] = inner.get(key, value)
                        except json.JSONDecodeError:
                            pass
                elif value is None:
                    idea[key] = ""
            result.append(idea)

        if len(result) < 3:
            result.extend(self._fallback_ideas(requirement, count=3 - len(result), start_idx=len(result) + 1))

        return result[:3]

    def _fallback_ideas(
        self, requirement: dict[str, Any], count: int = 3, start_idx: int = 1
    ) -> list[dict[str, Any]]:
        theme = requirement.get("theme", "") or "未命名主题"
        space_type = requirement.get("space_type", "") or "商业空间"
        budget = requirement.get("budget", "") or "项目预算区间"
        points = requirement.get("points", [])
        point_names = ", ".join([p.get("name", "") for p in points]) if points else space_type
        point_desc = self._format_points(points)

        variants = [
            ("沉浸式主景装置", f"以{theme}大型主题装置为核心，在{space_type}打造视觉焦点", "现代艺术"),
            ("互动打卡墙", f"设置可拍照互动的{theme}主题墙面，增强社交传播", "潮流互动"),
            ("光影艺术走廊", f"利用灯光和投影营造{theme}沉浸式通道体验", "科技光影"),
        ]

        fallback_points = []
        if points:
            for p in points:
                p_name = p.get("name", "未命名点位")
                p_size = p.get("size", "") or p.get("notes", "") or "中等尺寸"
                fallback_points.append({
                    "point_name": p_name,
                    "description": f"{p_name}布置{theme}主题装置，采用{variants[0][2]}风格，{p_size}",
                    "left_prompt": f"{theme} commercial display installation at {p_name}, {variants[0][2]} style, acrylic and LED materials, left side view, simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography, high quality rendering",
                    "center_prompt": f"{theme} commercial display installation at {p_name}, {variants[0][2]} style, acrylic and LED materials, center frontal view, simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography, high quality rendering",
                    "right_prompt": f"{theme} commercial display installation at {p_name}, {variants[0][2]} style, acrylic and LED materials, right side view, simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography, high quality rendering",
                })
        else:
            fallback_points = [{
                "point_name": "中庭",
                "description": f"中庭布置{theme}主题核心装置，作为视觉焦点",
                "left_prompt": f"{theme} commercial display installation at atrium, {variants[0][2]} style, acrylic and LED materials, left side view, simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography, high quality rendering",
                "center_prompt": f"{theme} commercial display installation at atrium, {variants[0][2]} style, acrylic and LED materials, center frontal view, simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography, high quality rendering",
                "right_prompt": f"{theme} commercial display installation at atrium, {variants[0][2]} style, acrylic and LED materials, right side view, simple and clean background, focus on the commercial display installation, minimal surrounding distraction, professional architecture photography, high quality rendering",
            }]

        ideas = []
        for i in range(count):
            idx = (start_idx - 1 + i) % len(variants)
            title, concept, style = variants[idx]
            ideas.append({
                "title": f"{theme}{title}",
                "theme": f"以{theme}为核心，在{space_type}中{concept}。结合{point_desc}等点位，通过多层次视觉设计让消费者沉浸其中。",
                "concept": concept,
                "style": style,
                "colorPalette": [
                    {"name": "主色", "hex": "#3b82f6"},
                    {"name": "辅色", "hex": "#f59e0b"},
                    {"name": "点缀色", "hex": "#ffffff"},
                ],
                "materials": "亚克力、LED灯带、金属框架、艺术涂料、仿真植物",
                "design_system": {
                    "core_element": f"{theme}主题造型",
                    "color_palette": "蓝色系为主，金色点缀",
                    "material_language": "亚克力、金属、LED灯带",
                    "lighting_mood": "暖白光，营造温馨氛围",
                    "connection_across_points": f"各点位统一使用{theme}主题元素和蓝色系配色",
                },
                "points": fallback_points,
                "applicablePoints": f"在{point_desc}等关键点位设置{theme}主题装置：中庭布置主视觉装置，门头设置主题门头或吊饰，DP点布置小型互动装置或拍照点。",
                "spatialLayout": f"以{space_type}入口或中庭为视觉焦点，沿人流动线分层展开{theme}主题元素，形成吸引—停留—互动—传播的空间叙事。",
                "designHighlights": "视觉冲击力强、主题表达清晰、易于拍照传播、成本可控、模块化便于安装维护",
                "atmosphere": f"整体空间营造出{theme}主题的独特氛围，以明亮通透的视觉效果为基调，为消费者打造沉浸式感官体验。",
                "estimatedBudget": budget,
            })
        return ideas

    async def refine(
        self,
        current_l1: dict[str, Any],
        feedback: str,
        requirement: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            prompt = (
                "设计师对当前 3 个创意方案提出了修改意见，请根据反馈重新生成 3 个创意，输出 JSON：\n\n"
                f"当前方案：{json.dumps(current_l1, ensure_ascii=False)}\n\n"
                f"修改意见：{feedback}\n\n"
                "输出字段与当前方案结构保持一致：每个创意包含 title/theme/concept/style/design_system/points 等字段，每个 point 包含 point_name/description/size/image_urls。"
            )
            raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {**current_l1, "refinement_error": True, "raw_feedback_response": raw}
        except Exception:
            return {**current_l1, "refinement_error": True}

    async def _get_fallback_design(self, requirement: dict[str, Any]) -> dict[str, Any]:
        return {
            "level": "L1",
            "ideas": self._fallback_ideas(requirement),
        }


async def design_concepts(requirement: dict[str, Any]) -> dict[str, Any]:
    """入口包装：根据需求生成 L1 概念方案。"""
    agent = ConceptDesignerAgent()
    return await agent.design(requirement, {})
