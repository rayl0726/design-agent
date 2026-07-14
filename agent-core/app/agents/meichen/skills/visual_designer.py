import asyncio
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.services.image_generation import image_generation
from app.services.llm_client import llm_client


class VisualDesignerAgent:
    SYSTEM = "你是一位擅长 AI 视觉表达的美陈设计师，精通将概念转化为可落地的视觉方案。"

    async def design(self, l1: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
        ideas = l1.get("ideas", [])
        if not ideas:
            # 兼容旧结构：如果没有 ideas，走原来的通用概念图生成
            concept_images = await self._generate_concept_images(l1, requirement)
            color_material_board = await self._generate_color_material_board(l1, requirement)
            return {
                "level": "L2",
                "concept_images": concept_images,
                "color_material_board": color_material_board,
            }

        ideas_with_images = await self._generate_idea_images(ideas)
        return {
            "level": "L2",
            "ideas": ideas_with_images,
        }

    async def _generate_idea_images(self, ideas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        all_tasks = []
        task_to_point = {}
        task_to_idea = {}

        for idea in ideas:
            enriched = dict(idea)
            points = idea.get("points", [])
            
            if points:
                for point in points:
                    # 按优先级取可用的视角提示词，单张时优先用中心视角
                    all_prompts = [
                        point.get("center_prompt", ""),
                        point.get("left_prompt", ""),
                        point.get("right_prompt", ""),
                    ]
                    prompts = [p for p in all_prompts if p][:settings.images_per_point]
                    point["image_urls"] = [""] * min(len(prompts), settings.images_per_point)
                    for prompt_idx, prompt in enumerate(prompts):
                        task = image_generation.generate(prompt, aspect_ratio="16:9", style="realistic")
                        all_tasks.append(task)
                        task_to_point[task] = (point, prompt_idx)
                        task_to_idea[task] = idea.get("title")
                
                first_point = points[0]
                if first_point.get("image_urls"):
                    enriched["image_url"] = first_point["image_urls"][1] if len(first_point["image_urls"]) > 1 else first_point["image_urls"][0]
            else:
                prompts = idea.get("image_prompts", [])
                if not prompts and idea.get("image_prompt"):
                    prompts = [idea.get("image_prompt")]
                if not prompts:
                    base_prompt = self._build_default_prompt(idea)
                    prompts = self._expand_prompts(base_prompt)

                enriched["image_urls"] = [""] * min(len(prompts), settings.images_per_point)
                for i, prompt in enumerate(prompts[:settings.images_per_point]):
                    task = image_generation.generate(prompt, aspect_ratio="16:9", style="realistic")
                    all_tasks.append(task)
                    task_to_point[task] = (enriched, i)
                    task_to_idea[task] = idea.get("title")
                enriched["image_url"] = ""
            
            results.append(enriched)

        if all_tasks:
            print(f"[VisualDesigner] Starting parallel image generation: {len(all_tasks)} images, max parallel={settings.max_parallel_images}")
            semaphore = asyncio.Semaphore(settings.max_parallel_images)
            
            async def with_limit(task, point_info, idea_title):
                async with semaphore:
                    try:
                        result = await task
                        point, idx = point_info
                        if isinstance(point, dict) and "image_urls" in point:
                            point["image_urls"][idx] = result
                        elif isinstance(point, dict) and "image_urls" in point:
                            point["image_urls"][idx] = result
                        print(f"[VisualDesigner] generated image for '{idea_title}': {result}")
                        return result
                    except Exception as e:
                        print(f"[VisualDesigner] image generation failed for '{idea_title}': {e}")
                        point, idx = point_info
                        if isinstance(point, dict) and "image_urls" in point:
                            point["image_urls"][idx] = ""
                        return ""

            limited_tasks = [with_limit(task, task_to_point[task], task_to_idea[task]) for task in all_tasks]
            await asyncio.gather(*limited_tasks)
            print(f"[VisualDesigner] All {len(all_tasks)} images generated")

        for enriched in results:
            points = enriched.get("points", [])
            if points:
                first_point = points[0]
                if first_point.get("image_urls"):
                    enriched["image_url"] = first_point["image_urls"][1] if len(first_point["image_urls"]) > 1 else first_point["image_urls"][0]
            elif enriched.get("image_urls"):
                enriched["image_url"] = enriched["image_urls"][0] if enriched["image_urls"] else ""

        return results

    def _expand_prompts(self, base_prompt: str) -> list[str]:
        """将一个基础提示词扩展为 5 个不同视角的提示词。"""
        return [
            f"Bird's eye view, {base_prompt}, aerial perspective showing full layout",
            f"Main entrance frontal view, {base_prompt}, eye-level shot, welcoming composition",
            f"Atrium centerpiece close-up, {base_prompt}, dramatic lighting, detailed installation",
            f"Storefront/entrance detail shot, {base_prompt}, material texture, craftsmanship",
            f"DP point interactive area close-up, {base_prompt}, visitors engaging, lifestyle photography",
        ]

    def _build_default_prompt(self, idea: dict[str, Any]) -> str:
        return (
            f"Commercial display design in shopping mall, "
            f"{idea.get('title', '')}, {idea.get('concept', '')}, {idea.get('style', '')} style, "
            f"{idea.get('materials', '')}, realistic rendering, soft lighting, "
            f"high-end commercial space, professional architecture photography"
        )

    async def _generate_concept_images(
        self, l1: dict[str, Any], requirement: dict[str, Any]
    ) -> list[dict[str, Any]]:
        story = l1.get("story", {})
        theme = requirement.get("theme", "")
        style = requirement.get("style", "")
        space_type = requirement.get("space_type", "")
        space_desc = requirement.get("space_description", "")[:200]

        prompts = []
        prompts.append(
            f"Interior commercial display design, {theme}, {style}, {space_type}, "
            f"{story.get('concept', '')}, realistic rendering, soft lighting, "
            f"high-end shopping mall, professional architecture photography"
        )
        prompts.append(
            f"Perspective view of {space_type} decorated with {theme} elements, "
            f"{style} style, vibrant colors, shoppers walking, festive atmosphere, "
            f"architectural visualization"
        )
        prompts.append(
            f"Close-up detail of {theme} decoration installation, {style} craftsmanship, "
            f"material textures, dramatic lighting, product photography style"
        )

        images = []
        for i, p in enumerate(prompts):
            img_path = await image_generation.generate(p, aspect_ratio="16:9", style="realistic")
            images.append({"index": i + 1, "prompt": p, "path": img_path})

        return images

    async def _generate_color_material_board(
        self, l1: dict[str, Any], requirement: dict[str, Any]
    ) -> str:
        # 提取颜色
        palette = requirement.get("color_palette", [])
        if not palette:
            palette = ["#2E5C8A", "#F5A623", "#FFFFFF", "#4A4A4A", "#D4A574"]

        # 创建色卡图
        width, height = 1200, 800
        img = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(img)

        # 标题
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 36)
            font_label = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
        except Exception:
            font_title = ImageFont.load_default()
            font_label = ImageFont.load_default()

        title = f"{requirement.get('theme', '设计')} - 色彩材质板"
        draw.text((50, 30), title, fill="#333333", font=font_title)

        # 绘制色块
        swatch_w, swatch_h = 180, 120
        start_x, start_y = 50, 100
        for i, color in enumerate(palette[:6]):
            x = start_x + i * (swatch_w + 20)
            y = start_y
            draw.rectangle([x, y, x + swatch_w, y + swatch_h], fill=color, outline="#CCCCCC")
            draw.text((x, y + swatch_h + 10), color, fill="#333333", font=font_label)

        # 材质区域
        materials = requirement.get("material_suggestions", [])
        y_offset = start_y + swatch_h + 80
        draw.text((50, y_offset), "建议材质", fill="#333333", font=font_title)
        for i, mat in enumerate(materials[:5]):
            draw.text((50, y_offset + 50 + i * 40), f"• {mat}", fill="#555555", font=font_label)

        # 应用区域
        y_offset += 50 + len(materials[:5]) * 40 + 40
        draw.text((50, y_offset), "应用区域", fill="#333333", font=font_title)
        areas = ["主视觉焦点", "通道引导", "休憩区域", "打卡点位"]
        for i, area in enumerate(areas):
            draw.text((50, y_offset + 50 + i * 40), f"• {area}", fill="#555555", font=font_label)

        cache_dir = Path(settings.image_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        output_path = cache_dir / f"color_material_board_{requirement.get('theme', 'default')}.png"
        img.save(output_path)
        return output_path.name

    async def consistency_check(self, l1: dict[str, Any], l2: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "请检查 L2 视觉方案是否与 L1 概念方向一致，输出 JSON：\n\n"
            f"L1 概念：{json.dumps(l1.get('story', {}), ensure_ascii=False)}\n\n"
            f"L2 视觉：{json.dumps(l2.get('concept_images', []), ensure_ascii=False)}\n\n"
            ' {"consistent": true/false, "issues": ["不一致点"], "suggestions": ["修正建议"]}'
        )
        raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"consistent": True, "parse_error": True}


async def generate_visuals(
    concepts: dict[str, Any], requirement: dict[str, Any]
) -> dict[str, Any]:
    """入口包装：根据 L1 概念方案生成 L2 视觉方案。"""
    agent = VisualDesignerAgent()
    return await agent.design(concepts, requirement)
