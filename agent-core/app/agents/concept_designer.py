import json
from typing import Any

from app.services.image_generation import image_generation
from app.services.llm_client import llm_client


class ConceptDesignerAgent:
    SYSTEM = "你是一位拥有 15 年经验的资深美陈设计师，擅长将商业需求转化为打动人心的设计故事。"

    async def design(self, requirement: dict[str, Any], retrieval: dict[str, Any]) -> dict[str, Any]:
        try:
            story = await self._generate_story(requirement, retrieval)
            atmosphere = await self._generate_atmosphere(requirement, story)
            moodboard = await self._generate_moodboard(requirement, story)

            return {
                "level": "L1",
                "story": story,
                "atmosphere": atmosphere,
                "moodboard": moodboard,
            }
        except Exception as e:
            return await self._get_fallback_design(requirement)

    async def _generate_story(
        self, requirement: dict[str, Any], retrieval: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = (
            "请为以下美陈设计项目撰写设计主题故事，输出 JSON（只输出 JSON）：\n\n"
            f"需求：{json.dumps(requirement, ensure_ascii=False)}\n\n"
            f"参考案例摘要：{retrieval.get('summary', '')[:500]}\n\n"
            "输出字段：\n"
            '{"title": "方案标题", "story": "200字以内的设计故事", '
            '"concept": "核心概念", "narrative": "场景叙事描述", '
            '"keywords": ["关键词"]}'
        )
        raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"title": "未命名方案", "story": raw[:300], "parse_error": True}

    async def _generate_atmosphere(
        self, requirement: dict[str, Any], story: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = (
            "请基于以下设计故事，生成氛围描述，输出 JSON（只输出 JSON）：\n\n"
            f"故事：{json.dumps(story, ensure_ascii=False)}\n\n"
            "输出字段：\n"
            '{"visual": ["视觉关键词"], "tactile": ["触觉关键词"], '
            '"auditory": ["听觉关键词"], "olfactory": ["嗅觉关键词"], '
            '"paragraph": "一段完整的氛围描述文字"}'
        )
        raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"paragraph": raw[:300], "parse_error": True}

    async def _generate_moodboard(
        self, requirement: dict[str, Any], story: dict[str, Any]
    ) -> dict[str, Any]:
        theme = requirement.get("theme", "")
        style = requirement.get("style", "")
        space_type = requirement.get("space_type", "")

        prompts = []
        prompts.append(
            f"A commercial display design moodboard, {theme} theme, {style} style, "
            f"{space_type} space, soft lighting, high quality, professional photography"
        )
        prompts.append(
            f"Color palette and material board for {theme} commercial display, "
            f"{style} aesthetic, elegant textures, design reference"
        )
        prompts.append(
            f"Atmospheric rendering of {space_type} with {theme} decoration, "
            f"{style} design language, warm ambient light, shoppers in background"
        )

        images = []
        for p in prompts:
            img_path = await image_generation.generate(p, aspect_ratio="16:9", style="realistic")
            images.append(img_path)

        return {
            "generated_images": images,
            "reference_images": [
                r.get("file_path")
                for r in requirement.get("references", [])
                if r.get("file_path")
            ],
        }

    async def refine(
        self,
        current_l1: dict[str, Any],
        feedback: str,
        requirement: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            prompt = (
                "设计师对当前 L1 概念方案提出了修改意见，请根据反馈重新生成方案，输出 JSON：\n\n"
                f"当前方案：{json.dumps(current_l1, ensure_ascii=False)}\n\n"
                f"修改意见：{feedback}\n\n"
                "输出字段与 L1 结构相同：{\"story\": {...}, \"atmosphere\": {...}, \"moodboard\": {...}}"
            )
            raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {**current_l1, "refinement_error": True, "raw_feedback_response": raw}
        except Exception:
            return {**current_l1, "refinement_error": True}

    async def _get_fallback_design(self, requirement: dict[str, Any]) -> dict[str, Any]:
        theme = requirement.get("theme", "未命名主题")
        style = requirement.get("style", "现代简约")
        space_type = requirement.get("space_type", "中庭")

        prompts = []
        prompts.append(
            f"A commercial display design moodboard, {theme} theme, {style} style, "
            f"{space_type} space, soft lighting, high quality, professional photography"
        )
        prompts.append(
            f"Color palette and material board for {theme} commercial display, "
            f"{style} aesthetic, elegant textures, design reference"
        )
        prompts.append(
            f"Atmospheric rendering of {space_type} with {theme} decoration, "
            f"{style} design language, warm ambient light, shoppers in background"
        )

        images = []
        for p in prompts:
            try:
                img_path = await image_generation.generate(p, aspect_ratio="16:9", style="realistic")
                images.append(img_path)
            except Exception:
                images.append("../design-data/images/placeholder_default.png")

        return {
            "level": "L1",
            "story": {
                "title": f"{theme}主题概念方案",
                "story": f"以{theme}为设计灵感来源，打造沉浸式商业美陈空间。通过现代{style}风格的设计语言，将品牌理念与空间美学完美融合，为消费者带来独特的视觉体验和情感共鸣。",
                "concept": f"{theme}沉浸式体验",
                "narrative": f"在{space_type}空间中，通过多层次的视觉设计和互动装置，构建一个以{theme}为核心的沉浸式体验场景。消费者进入空间后，将被环绕式的视觉元素所包围，从入口到深处，逐步体验{theme}主题带来的情感旅程。",
                "keywords": [theme, style, space_type, "沉浸式", "互动体验"],
            },
            "atmosphere": {
                "visual": ["明亮通透", "层次分明", "色彩和谐", "光影交织"],
                "tactile": ["光滑质感", "温暖触感", "舒适体验"],
                "auditory": ["轻柔音乐", "环境音效", "互动反馈"],
                "olfactory": ["清新香气", "品牌香氛"],
                "paragraph": f"整体空间营造出{theme}主题的独特氛围，以明亮通透的视觉效果为基调，配合温暖舒适的触感体验。轻柔的背景音乐与环境音效相互交织，清新的香气弥漫整个空间，为消费者打造全方位的沉浸式感官体验。",
            },
            "moodboard": {
                "generated_images": images,
                "reference_images": [],
            },
        }
