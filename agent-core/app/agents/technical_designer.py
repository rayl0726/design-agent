from __future__ import annotations

import json
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.agents.knowledge_retrieval import retrieve_cases, retrieve_materials
from app.services.image_generation import generate_images_with_fallback
from app.core.config import settings
from app.models.database import get_session
from app.models.project import MaterialPrice, MaterialSpec
from app.services.llm_client import llm_client


class TechnicalDesignerAgent:
    SYSTEM = "你是一位资深美陈项目工程师，擅长将设计方案拆解为可执行的物料清单和预算。"

    async def design(
        self,
        l2: dict[str, Any],
        requirement: dict[str, Any],
        cad_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        effective_requirement = self._extract_effective_requirement(l2, requirement)
        layout = await self._generate_layout_annotation(l2, effective_requirement, cad_data)
        material_list = await self._generate_material_list(l2, effective_requirement)
        budget = await self._generate_budget(material_list)

        return {
            "level": "L3",
            "layout_annotation": layout,
            "material_list": material_list,
            "budget": budget,
        }

    def _extract_effective_requirement(self, l2: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
        result = {}
        
        result["theme"] = requirement.get("theme", "")
        result["style"] = requirement.get("style", "")
        result["space_type"] = requirement.get("space_type", "")
        result["budget_level"] = requirement.get("budget_level", "")
        result["area"] = requirement.get("area", "")
        
        if not result["theme"] or not result["style"]:
            story = requirement.get("story", {})
            if isinstance(story, dict):
                if not result["theme"]:
                    result["theme"] = story.get("title", "") or story.get("concept", "")
                if not result["style"]:
                    keywords = story.get("keywords", [])
                    if isinstance(keywords, list):
                        result["style"] = ", ".join(keywords)
        
        if not result["theme"]:
            result["theme"] = l2.get("level", "")
        
        return result

    async def _generate_layout_annotation(
        self,
        l2: dict[str, Any],
        requirement: dict[str, Any],
        cad_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        # 如果无 CAD，使用默认面积生成简化示意
        if not cad_data or not cad_data.get("area_estimate"):
            area = float(requirement.get("area", 100)) if requirement.get("area") else 100
            columns = []
            
            points = self._suggest_points(area, columns)
            
            default_cad_data = {
                "area_estimate": area,
                "columns": [],
            }
            layout_path = self._render_layout(default_cad_data, points, requirement)

            return {
                "type": "simplified",
                "note": "无 CAD 输入，生成简化示意布局，需现场复核",
                "area": area,
                "points": points,
                "layout_image": layout_path,
                "layout_svg": self._generate_simplified_layout(requirement),
            }

        area = cad_data.get("area_estimate", 0)
        columns = cad_data.get("columns", [])

        points = self._suggest_points(area, columns)

        layout_path = self._render_layout(cad_data, points, requirement)

        return {
            "type": "annotated",
            "area": area,
            "points": points,
            "layout_image": layout_path,
        }

    def _suggest_points(self, area: float, columns: list[dict]) -> list[dict]:
        count = min(max(int(area / 30), 3), 8)
        points = []
        side = math.sqrt(area) if area > 0 else 10
        cols = math.ceil(math.sqrt(count))
        rows = math.ceil(count / cols)

        for i in range(count):
            r = i // cols
            c = i % cols
            x = (c + 0.5) * (side / cols)
            y = (r + 0.5) * (side / rows)
            # 简单避开柱网（距离 > 1m）
            for col in columns:
                cx, cy = col.get("center", [0, 0])
                if math.hypot(x - cx, y - cy) < 150:
                    x += 200
            points.append({
                "id": f"P{i + 1}",
                "x": round(x, 2),
                "y": round(y, 2),
                "type": "吊饰" if i == 0 else "地面装置" if i == 1 else "装饰",
            })
        return points

    def _generate_simplified_layout(self, requirement: dict[str, Any]) -> str:
        return "<svg><rect width='100%' height='100%' fill='#f5f5f5'/></svg>"

    def _render_layout(
        self, cad_data: dict[str, Any], points: list[dict], requirement: dict[str, Any]
    ) -> str:
        width, height = 1200, 900
        img = Image.new("RGB", (width, height), "#F8F8F8")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 20)
            font_large = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 28)
        except Exception:
            font = ImageFont.load_default()
            font_large = ImageFont.load_default()

        # 标题
        title = f"{requirement.get('theme', '方案')} - 平面点位布置图"
        draw.text((50, 20), title, fill="#333333", font=font_large)

        # 绘制柱网
        for col in cad_data.get("columns", []):
            cx, cy = col.get("center", [0, 0])
            sx, sy = cx / 10 + 100, cy / 10 + 100
            draw.ellipse([sx - 10, sy - 10, sx + 10, sy + 10], fill="#AAAAAA", outline="#666666")

        # 绘制点位
        for p in points:
            px, py = p["x"] / 10 + 100, p["y"] / 10 + 100
            draw.ellipse([px - 15, py - 15, px + 15, py + 15], fill="#E74C3C", outline="#C0392B")
            draw.text((px + 20, py - 10), f"{p['id']} ({p['type']})", fill="#333333", font=font)

        # 图例
        legend_y = height - 100
        draw.rectangle([50, legend_y, 70, legend_y + 20], fill="#E74C3C", outline="#C0392B")
        draw.text((80, legend_y), "安装点位", fill="#333333", font=font)
        draw.ellipse([200, legend_y + 5, 220, legend_y + 25], fill="#AAAAAA", outline="#666666")
        draw.text((230, legend_y), "柱网", fill="#333333", font=font)

        path = f"{settings.image_cache_dir}/layout_{requirement.get('theme', 'default')}.png"
        img.save(path)
        return path

    async def _generate_material_list(
        self, l2: dict[str, Any], requirement: dict[str, Any]
    ) -> list[dict[str, Any]]:
        print("DEBUG: Using fallback material list (database-matched, no LLM)")
        items = self._generate_fallback_material_list(requirement)

        # 查询价格
        db = get_session()
        try:
            for item in items:
                name = item.get("name", "")
                if not name:
                    continue
                row = db.query(MaterialPrice).filter(MaterialPrice.name.contains(name)).first()
                if row and row.price_low:
                    item["unit_price"] = row.price_low
                    item["total_price"] = round(row.price_low * (item.get("quantity", 1) or 1), 2)
                    item["supplier_hint"] = row.supplier_hint or item.get("supplier_hint", "")
        finally:
            db.close()

        return items

    def _generate_fallback_material_list(self, requirement: dict[str, Any]) -> list[dict[str, Any]]:
        db = get_session()
        try:
            prices = db.query(MaterialPrice).all()
            if prices:
                return [
                    {
                        "name": "亚克力板",
                        "material": "亚克力",
                        "size": "定制尺寸",
                        "process": "雕刻+抛光",
                        "unit": "平方米",
                        "quantity": 10,
                        "unit_price": 0.0,
                        "total_price": 0.0,
                        "supplier_hint": "建议从亚克力板材供应商处采购"
                    },
                    {
                        "name": "LED灯带",
                        "material": "LED灯珠+PCB板",
                        "size": "长度20m",
                        "process": "防水处理",
                        "unit": "米",
                        "quantity": 50,
                        "unit_price": 0.0,
                        "total_price": 0.0,
                        "supplier_hint": "建议使用户外防水LED灯带"
                    },
                    {
                        "name": "金属框架",
                        "material": "铝合金/不锈钢",
                        "size": "定制尺寸",
                        "process": "焊接+烤漆",
                        "unit": "件",
                        "quantity": 5,
                        "unit_price": 0.0,
                        "total_price": 0.0,
                        "supplier_hint": "建议寻找金属加工供应商"
                    },
                    {
                        "name": "PVC板",
                        "material": "PVC",
                        "size": "定制尺寸",
                        "process": "雕刻+喷涂",
                        "unit": "平方米",
                        "quantity": 15,
                        "unit_price": 0.0,
                        "total_price": 0.0,
                        "supplier_hint": "建议从PVC板材供应商处采购"
                    },
                    {
                        "name": "UV喷绘",
                        "material": "喷绘布/车贴",
                        "size": "定制尺寸",
                        "process": "UV喷绘+覆膜",
                        "unit": "平方米",
                        "quantity": 30,
                        "unit_price": 0.0,
                        "total_price": 0.0,
                        "supplier_hint": "建议从喷绘供应商处采购"
                    },
                    {
                        "name": "霓虹灯",
                        "material": "霓虹灯管",
                        "size": "定制尺寸",
                        "process": "定制弯管",
                        "unit": "米",
                        "quantity": 10,
                        "unit_price": 0.0,
                        "total_price": 0.0,
                        "supplier_hint": "建议寻找霓虹灯定制供应商"
                    },
                    {
                        "name": "发光字",
                        "material": "亚克力+LED",
                        "size": "定制尺寸",
                        "process": "雕刻+组装",
                        "unit": "个",
                        "quantity": 5,
                        "unit_price": 0.0,
                        "total_price": 0.0,
                        "supplier_hint": "建议寻找发光字制作供应商"
                    }
                ]
        finally:
            db.close()
        
        return []

    async def _generate_budget(self, material_list: list[dict[str, Any]]) -> dict[str, Any]:
        material_cost = sum(item.get("total_price", 0) or 0 for item in material_list)
        production_cost = material_cost * 0.3  # 制作费 30%
        installation_cost = material_cost * 0.15  # 安装费 15%
        design_fee = material_cost * 0.1  # 设计费 10%
        total = material_cost + production_cost + installation_cost + design_fee

        return {
            "material_cost": round(material_cost, 2),
            "production_cost": round(production_cost, 2),
            "installation_cost": round(installation_cost, 2),
            "design_fee": round(design_fee, 2),
            "total": round(total, 2),
            "currency": "CNY",
            "items": material_list,
            "over_budget": False,
        }
