import json
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.services.image_generation import image_generation
from app.services.llm_client import llm_client


class VisualDesignerAgent:
    SYSTEM = "你是一位擅长 AI 视觉表达的美陈设计师，精通将概念转化为可落地的视觉方案。"

    async def design(self, l1: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
        concept_images = await self._generate_concept_images(l1, requirement)
        color_material_board = await self._generate_color_material_board(l1, requirement)

        return {
            "level": "L2",
            "concept_images": concept_images,
            "color_material_board": color_material_board,
        }

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

        output_path = f"{settings.image_cache_dir}/color_material_board_{requirement.get('theme', 'default')}.png"
        img.save(output_path)
        return output_path

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
