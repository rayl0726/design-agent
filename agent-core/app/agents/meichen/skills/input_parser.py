from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2
from fastapi import UploadFile

from app.core.config import settings
from app.services.embedding_client import embedding_client
from app.services.intent_recognition import get_intent_service
from app.services.taxonomy_loader import load_taxonomy
from app.services.vlm_client import vlm_client

UPLOAD_ROOT = Path(settings.upload_dir)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

_TAXONOMY = load_taxonomy()


def _taxonomy_prompt_fragment() -> str:
    space_types = [s["name"] for s in _TAXONOMY.space_types]
    points = [p["name"] for p in _TAXONOMY.points]
    styles = [s["name"] for s in _TAXONOMY.styles]
    materials = [m["name"] for m in _TAXONOMY.materials]
    return (
        "空间类型必须从以下候选中选择：" + ", ".join(space_types) + "\n"
        "点位必须从以下候选中选择：" + ", ".join(points) + "\n"
        "风格必须从以下候选中选择：" + ", ".join(styles) + "\n"
        "材质必须从以下候选中选择：" + ", ".join(materials) + "\n"
        "无法确定时请返回 null。"
    )


def _normalize_vlm_value(value: Any, field: str) -> Any:
    if not value or not isinstance(value, str):
        return value
    lowered = value.lower()
    mapping: dict[str, dict[str, str]] = {
        "space_type": _TAXONOMY.alias_to_space_type,
        "style": _TAXONOMY.alias_to_style,
        "material": _TAXONOMY.alias_to_material,
        "point": _TAXONOMY.alias_to_point,
    }
    alias_map = mapping.get(field, {})
    return alias_map.get(lowered, value)


def _save_upload(file: UploadFile, project_id: str, prefix: str) -> Path:
    ext = Path(file.filename or "unknown").suffix
    dest = UPLOAD_ROOT / project_id / f"{prefix}_{file.filename or 'unknown'}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest


class PhotoParser:
    SYSTEM = "你是一位商业空间视觉分析师，擅长从照片中识别空间类型、尺寸感、人流特征和现有装饰。"

    def _normalize_vlm_value(self, value: Any, field: str) -> Any:
        return _normalize_vlm_value(value, field)

    async def parse(self, image_path: Path | str) -> dict[str, Any]:
        prompt = (
            "你是一位商业空间视觉分析师。请分析这张现场照片，输出以下 JSON 字段（只输出 JSON，不要多余文字）：\n"
            '{"space_type": "空间类型", "estimated_area": "估算面积", '
            '"ceiling_height": "天花板高度", '
            '"existing_elements": ["现有装饰物"], '
            '"lighting_condition": "光照条件", '
            '"crowd_flow": "人流特征", '
            '"notes": "其他观察"}\n'
            + _taxonomy_prompt_fragment()
        )
        raw = await vlm_client.describe(str(image_path), prompt, json_mode=True)
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            data = {"raw_description": raw, "parse_error": True}
        data["space_type"] = self._normalize_vlm_value(data.get("space_type"), "space_type")
        data["source_type"] = "photo"
        data["file_path"] = str(image_path)
        return data


class VideoParser:
    FRAME_INTERVAL = 5  # 秒

    async def parse(self, video_path: Path | str) -> dict[str, Any]:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval_frames = int(fps * self.FRAME_INTERVAL)
        frames_dir = Path(video_path).parent / "video_frames"
        frames_dir.mkdir(exist_ok=True)

        frame_paths = []
        count = 0
        success, frame = cap.read()
        while success:
            if count % frame_interval_frames == 0:
                frame_path = frames_dir / f"frame_{count:06d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                frame_paths.append(frame_path)
            success, frame = cap.read()
            count += 1
        cap.release()

        photo_parser = PhotoParser()
        descriptions = []
        for fp in frame_paths[:10]:  # 最多处理10帧
            desc = await photo_parser.parse(fp)
            descriptions.append(desc)

        return {
            "source_type": "video",
            "file_path": str(video_path),
            "frame_count": len(frame_paths),
            "frame_descriptions": descriptions,
        }


class ReferenceParser:
    def _normalize_vlm_value(self, value: Any, field: str) -> Any:
        return _normalize_vlm_value(value, field)

    async def parse(self, image_path: Path | str) -> dict[str, Any]:
        prompt = (
            "请分析这张参考图，输出以下 JSON 字段（只输出 JSON）：\n"
            '{"style": "风格", "theme": "主题", "color_palette": ["主要颜色"], '
            '"materials": ["材质"], "space_type": "适用空间类型", '
            '"design_elements": ["设计元素"], "mood": "氛围关键词"}\n'
            + _taxonomy_prompt_fragment()
        )
        raw = await vlm_client.describe(str(image_path), prompt, json_mode=True)
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            data = {"raw_description": raw, "parse_error": True}
        data["style"] = self._normalize_vlm_value(data.get("style"), "style")
        if "materials" in data and isinstance(data["materials"], list):
            data["materials"] = [self._normalize_vlm_value(m, "material") for m in data["materials"]]
        data["space_type"] = self._normalize_vlm_value(data.get("space_type"), "space_type")
        data["source_type"] = "reference"
        data["file_path"] = str(image_path)
        return data


class TextParser:
    SYSTEM = "你是一位美陈设计需求分析师，擅长从自然语言中提取结构化设计需求。"

    _intent_service = None

    async def parse(
        self,
        text: str,
        project_id: str | None = None,
        previous_intent: dict | None = None,
        recent_messages: list[str] | None = None,
        conversation_summary: str = "",
    ) -> dict[str, Any]:
        from app.core.config import settings

        if getattr(settings, "intent_parser_legacy", False):
            return self._get_fallback_parse(text)

        service = self._intent_service or get_intent_service()

        prev_validated = None
        if previous_intent:
            try:
                prev_validated = self._dict_to_validated_intent(previous_intent)
            except Exception as e:
                print(f"TextParser.parse: _dict_to_validated_intent failed (non-fatal): {type(e).__name__}: {e}")
                prev_validated = None

        result = await service.recognize(
            text=text,
            previous_intent=prev_validated,
            project_id=project_id,
            recent_messages=recent_messages,
            conversation_summary=conversation_summary,
        )
        return self._validated_intent_to_dict(result)

    def _validated_intent_to_dict(self, result) -> dict[str, Any]:
        data = {
            "theme": result.theme.value if result.theme else "",
            "style": result.style.value if result.style else "",
            "space_type": result.space_type.value if result.space_type else "",
            "budget": result.budget.value if result.budget else "",
            "budget_level": result.budget_level.value if result.budget_level else "",
            "target_audience": result.target_audience.value if result.target_audience else "",
            "timeline": result.timeline.value if result.timeline else "",
            "material_restrictions": [m.value for m in result.material_restrictions],
            "allowed_materials": [m.value for m in result.allowed_materials],
            "special_requirements": [s.value for s in result.special_requirements],
            "color_preference": result.color_preference.value if result.color_preference else "",
            "brand_positioning": result.brand_positioning.value if result.brand_positioning else "",
            "design_system_preference": result.design_system_preference.value
            if result.design_system_preference
            else "",
            "points": [{"name": str(p.value), "count": 1, "notes": ""} for p in result.points],
            "source_type": "text",
            "trace_id": result.trace_id,
            "_recognition_meta": self._build_recognition_meta(result),
        }
        return data

    def _dict_to_validated_intent(self, data: dict | None) -> ValidatedIntent | None:
        """将 Java 传来的简单 dict 转换为 ValidatedIntent 对象。"""
        if not data:
            return None

        from app.services.intent_recognition_result import (
            ValidatedIntent,
            RecognizedField,
            FieldSource,
        )

        def _field(name: str, value) -> RecognizedField | None:
            if value is None:
                return None
            if isinstance(value, str) and not value.strip():
                return None
            return RecognizedField(
                name=name,
                value=value,
                source=FieldSource.UNKNOWN,
                confidence=1.0,
            )

        def _list_fields(name: str, values) -> list[RecognizedField]:
            if not values or not isinstance(values, list):
                return []
            return [
                RecognizedField(name=name, value=v, source=FieldSource.UNKNOWN, confidence=1.0)
                for v in values
                if v is not None and (not isinstance(v, str) or v.strip())
            ]

        def _point_fields(points_data) -> list[RecognizedField]:
            if not points_data or not isinstance(points_data, list):
                return []
            result = []
            for p in points_data:
                if isinstance(p, dict):
                    name = p.get("name", "")
                    if name and name.strip():
                        result.append(
                            RecognizedField(
                                name="points",
                                value=name.strip(),
                                source=FieldSource.UNKNOWN,
                                confidence=1.0,
                            )
                        )
                elif isinstance(p, str) and p.strip():
                    result.append(
                        RecognizedField(
                            name="points",
                            value=p.strip(),
                            source=FieldSource.UNKNOWN,
                            confidence=1.0,
                        )
                    )
            return result

        intent = ValidatedIntent(
            theme=_field("theme", data.get("theme")),
            style=_field("style", data.get("style")),
            space_type=_field("space_type", data.get("space_type")),
            budget=_field("budget", data.get("budget")),
            budget_level=_field("budget_level", data.get("budget_level")),
            target_audience=_field("target_audience", data.get("target_audience")),
            timeline=_field("timeline", data.get("timeline")),
            color_preference=_field("color_preference", data.get("color_preference")),
            brand_positioning=_field("brand_positioning", data.get("brand_positioning")),
            design_system_preference=_field(
                "design_system_preference", data.get("design_system_preference")
            ),
            material_restrictions=_list_fields(
                "material_restrictions", data.get("material_restrictions")
            ),
            allowed_materials=_list_fields(
                "allowed_materials", data.get("allowed_materials")
            ),
            special_requirements=_list_fields(
                "special_requirements", data.get("special_requirements")
            ),
            points=_point_fields(data.get("points")),
        )

        # 检查是否有任何非空字段
        has_value = any(
            getattr(intent, f) is not None
            for f in (
                "theme", "style", "space_type", "budget", "budget_level",
                "target_audience", "timeline", "color_preference",
                "brand_positioning", "design_system_preference",
            )
        ) or any(
            key in data
            for key in (
                "material_restrictions", "allowed_materials",
                "special_requirements", "points",
            )
        )

        return intent if has_value else None

    def _build_recognition_meta(self, result) -> dict[str, Any]:
        """Extract source/confidence/raw_text for all core fields for debug observability."""
        meta: dict[str, Any] = {"trace_id": result.trace_id}
        for field_name in ("theme", "space_type", "budget", "budget_level", "style"):
            field = getattr(result, field_name)
            if field is not None:
                source = field.source
                meta[f"{field_name}_source"] = source.value if hasattr(source, "value") else str(source)
                meta[f"{field_name}_confidence"] = field.confidence
                meta[f"{field_name}_raw_text"] = field.raw_text
            else:
                meta[f"{field_name}_source"] = None
                meta[f"{field_name}_confidence"] = 0.0
                meta[f"{field_name}_raw_text"] = ""
        return meta

    def _get_fallback_parse(self, text: str) -> dict[str, Any]:
        import re
        theme = ""
        style = ""
        space_type = ""
        budget = ""

        theme_match = re.search(r"(主题|风格|氛围|概念)\s*[：:]\s*([^\n]+)", text)
        if theme_match:
            theme = theme_match.group(2).strip()

        style_match = re.search(r"(风格|设计风格)\s*[：:]\s*([^\n]+)", text)
        if style_match:
            style = style_match.group(2).strip()

        space_match = re.search(r"(空间|场地|位置)\s*[：:]\s*([^\n]+)", text)
        if space_match:
            space_type = space_match.group(2).strip()

        budget_match = re.search(r"(预算|费用)\s*[：:]\s*([^\n]+)", text)
        if budget_match:
            budget = budget_match.group(2).strip()

        if not space_type:
            space_keywords = ["购物中心", "商场", "百货", "快闪店", "展厅", "步行街", "中庭", "门店", "专卖店"]
            for keyword in space_keywords:
                if keyword in text:
                    if keyword == "中庭":
                        space_type = "购物中心"
                    else:
                        space_type = keyword
                    break

        if not budget:
            budget_match = re.search(r"(\d+(?:\.\d+)?)\s*(万|元|千)", text)
            if budget_match:
                budget = budget_match.group(1) + budget_match.group(2)

        budget_level = "medium"
        if budget:
            budget_lower = budget.lower()
            if "低" in budget_lower or "少" in budget_lower:
                budget_level = "low"
            elif "高" in budget_lower or "多" in budget_lower:
                budget_level = "high"
            else:
                try:
                    match = re.search(r"(\d+)", budget)
                    if match:
                        amount = int(match.group(1))
                        if amount < 10:
                            budget_level = "low"
                        elif amount > 30:
                            budget_level = "high"
                except:
                    pass

        # 尝试提取点位信息
        points = []
        point_keywords = ["灯光画", "中庭", "门头", "灯饰画", "座椅", "DP点", "快闪店", "扶梯", "连廊", "服务台", "立柱", "橱窗", "吊旗", "地贴", "指示牌", "花车", "摊位", "入口"]
        for kw in point_keywords:
            pattern = re.search(rf"({kw})\s*[×xX*]?\s*(\d+)", text)
            if pattern:
                points.append({"name": kw, "count": int(pattern.group(2)), "notes": ""})
            elif kw in text and not any(p["name"] == kw for p in points):
                count_pattern = re.search(rf"{kw}(\d+)", text)
                if count_pattern:
                    points.append({"name": kw, "count": int(count_pattern.group(1)), "notes": ""})
                else:
                    points.append({"name": kw, "count": 1, "notes": ""})

        # 提取整体串联元素
        design_system_preference = ""
        ds_match = re.search(r"(?:整体串联元素|串联元素|统一元素|设计元素)[用是：:]\s*([^\n。，]+)", text)
        if ds_match:
            design_system_preference = ds_match.group(1).strip()

        # 从点位 notes 中提取尺寸
        for p in points:
            notes = p.get("notes", "")
            if notes and not p.get("size"):
                size_match = re.search(r"(\d+[\.\d]*)\s*[m米]\s*[×xX*]\s*(\d+[\.\d]*)\s*[m米]?\s*(?:[×xX*]\s*(\d+[\.\d]*)\s*[m米]?)?", notes)
                if size_match:
                    size = f"{size_match.group(1)}m×{size_match.group(2)}m"
                    if size_match.group(3):
                        size += f"×{size_match.group(3)}m"
                    p["size"] = size

        return {
            "theme": theme,
            "style": style,
            "space_type": space_type,
            "budget": budget,
            "budget_level": budget_level if budget else None,
            "target_audience": "",
            "timeline": "",
            "material_restrictions": [],
            "special_requirements": [],
            "color_preference": "",
            "brand_positioning": "",
            "design_system_preference": design_system_preference,
            "points": points,
            "source_type": "text",
        }


class InputMerger:
    async def merge(self, parsed_results: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {
            "space_type": None,
            "budget": None,
            "budget_level": None,
            "theme": None,
            "style": None,
            "target_audience": None,
            "timeline": None,
            "material_restrictions": [],
            "special_requirements": [],
            "color_preference": None,
            "brand_positioning": None,
            "design_system_preference": None,
            "space_description": "",
            "references": [],
            "points": [],
            "raw_inputs": parsed_results,
        }

        for result in parsed_results:
            st = result.get("source_type")
            if st == "text":
                for key in ["space_type", "budget", "budget_level", "theme", "style",
                            "target_audience", "timeline", "color_preference", "brand_positioning",
                            "design_system_preference"]:
                    if result.get(key) and not merged.get(key):
                        merged[key] = result[key]
                merged["material_restrictions"].extend(result.get("material_restrictions", []))
                merged["special_requirements"].extend(result.get("special_requirements", []))
                for point in result.get("points", []):
                    existing = next((p for p in merged["points"] if p.get("name") == point.get("name")), None)
                    if existing:
                        existing["count"] = point.get("count", existing.get("count", 1))
                        if point.get("notes"):
                            existing["notes"] = point.get("notes")
                    else:
                        merged["points"].append(point)
            elif st in ("photo", "video"):
                desc = result.get("raw_description") or result.get("space_description") or ""
                if desc:
                    merged["space_description"] += desc + "\n"
                if result.get("space_type") and not merged["space_type"]:
                    merged["space_type"] = result["space_type"]
            elif st == "reference":
                merged["references"].append(result)
            elif st == "cad":
                if result.get("area") and not merged.get("budget"):
                    pass  # CAD不直接提供预算
                if result.get("space_type") and not merged["space_type"]:
                    merged["space_type"] = result["space_type"]
            elif st in ("pdf", "ppt"):
                if result.get("theme") and not merged["theme"]:
                    merged["theme"] = result["theme"]
                if result.get("style") and not merged["style"]:
                    merged["style"] = result["style"]
                merged["special_requirements"].extend(result.get("requirements", []))

        merged["material_restrictions"] = list(set(merged["material_restrictions"]))
        merged["special_requirements"] = list(set(merged["special_requirements"]))
        return merged


class CADParser:
    async def parse(self, file_path: Path | str) -> dict[str, Any]:
        return {
            "source_type": "cad",
            "file_path": str(file_path),
            "area_estimate": 0,
            "space_type": None,
            "columns": [],
            "notes": "CAD 解析功能开发中",
        }


class PDFParser:
    async def parse(self, file_path: Path | str) -> dict[str, Any]:
        return {
            "source_type": "pdf",
            "file_path": str(file_path),
            "theme": None,
            "style": None,
            "requirements": [],
            "notes": "PDF 解析功能开发中",
        }


class PPTParser:
    async def parse(self, file_path: Path | str) -> dict[str, Any]:
        return {
            "source_type": "ppt",
            "file_path": str(file_path),
            "theme": None,
            "style": None,
            "requirements": [],
            "notes": "PPT 解析功能开发中",
        }
