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
from app.services.llm_client import llm_client
from app.services.vlm_client import vlm_client

UPLOAD_ROOT = Path(settings.upload_dir)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _save_upload(file: UploadFile, project_id: str, prefix: str) -> Path:
    ext = Path(file.filename or "unknown").suffix
    dest = UPLOAD_ROOT / project_id / f"{prefix}_{file.filename or 'unknown'}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest


class PhotoParser:
    SYSTEM = "你是一位商业空间视觉分析师，擅长从照片中识别空间类型、尺寸感、人流特征和现有装饰。"

    async def parse(self, image_path: Path | str) -> dict[str, Any]:
        prompt = (
            "请分析这张现场照片，输出以下 JSON 字段（只输出 JSON，不要多余文字）：\n"
            '{"space_type": "空间类型（中庭/走廊/入口/快闪店等）", '
            '"estimated_area": "估算面积（如约200平米）", '
            '"ceiling_height": "天花板高度估算", '
            '"existing_elements": ["现有装饰物/设施列表"], '
            '"lighting_condition": "光照条件", '
            '"crowd_flow": "人流特征", '
            '"notes": "其他观察"}'
        )
        raw = await vlm_client.describe(str(image_path), prompt, json_mode=True)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"raw_description": raw, "parse_error": True}
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
    async def parse(self, image_path: Path | str) -> dict[str, Any]:
        prompt = (
            "请分析这张参考图，输出以下 JSON 字段（只输出 JSON）：\n"
            '{"style": "风格标签", "theme": "主题标签", "color_palette": ["主要颜色"], '
            '"materials": ["材质标签"], "space_type": "适用空间类型", '
            '"design_elements": ["设计元素"], "mood": "氛围关键词"}'
        )
        raw = await vlm_client.describe(str(image_path), prompt, json_mode=True)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"raw_description": raw, "parse_error": True}
        data["source_type"] = "reference"
        data["file_path"] = str(image_path)
        return data


class TextParser:
    SYSTEM = "你是一位美陈设计需求分析师，擅长从自然语言中提取结构化设计需求。"

    async def parse(self, text: str) -> dict[str, Any]:
        try:
            prompt = (
                f"请从以下需求文本中提取结构化信息，输出 JSON（只输出 JSON）：\n\n{text}\n\n"
                "输出字段：\n"
                '{"theme": "主题", "style": "风格", "space_type": "空间类型", '
                '"budget": "预算", "budget_level": "budget档次(low/medium/high)", '
                '"target_audience": "目标人群", "timeline": "工期", '
                '"material_restrictions": ["材料限制"], "special_requirements": ["特殊要求"], '
                '"color_preference": "颜色偏好", "brand_positioning": "品牌定位"}'
            )
            raw = await llm_client.complete(self.SYSTEM, prompt, json_mode=True)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"raw_text": text, "parse_error": True}
            data["source_type"] = "text"
            return data
        except Exception:
            return self._get_fallback_parse(text)

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

        budget_level = "medium"
        budget_lower = budget.lower()
        if "低" in budget_lower or "少" in budget_lower:
            budget_level = "low"
        elif "高" in budget_lower or "多" in budget_lower:
            budget_level = "high"

        return {
            "theme": theme or "现代商业",
            "style": style or "现代简约",
            "space_type": space_type or "",
            "budget": budget,
            "budget_level": budget_level,
            "target_audience": "",
            "timeline": "",
            "material_restrictions": [],
            "special_requirements": [],
            "color_preference": "",
            "brand_positioning": "",
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
            "space_description": "",
            "references": [],
            "raw_inputs": parsed_results,
        }

        for result in parsed_results:
            st = result.get("source_type")
            if st == "text":
                for key in ["space_type", "budget", "budget_level", "theme", "style",
                            "target_audience", "timeline", "color_preference", "brand_positioning"]:
                    if result.get(key) and not merged.get(key):
                        merged[key] = result[key]
                merged["material_restrictions"].extend(result.get("material_restrictions", []))
                merged["special_requirements"].extend(result.get("special_requirements", []))
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
