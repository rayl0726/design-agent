from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pdfplumber

from app.services.llm_client import llm_client
from app.services.vlm_client import vlm_client


class PDFParser:
    async def parse(self, file_path: Path | str) -> dict[str, Any]:
        path = Path(file_path)
        text_content = self._extract_text(str(path))
        images = self._extract_images(str(path))

        is_scanned = len(text_content.strip()) < 200
        if is_scanned:
            text_content = await self._ocr_pages(str(path))

        structured = await self._extract_requirements(text_content)
        return {
            "source_type": "pdf",
            "file_path": str(path),
            "is_scanned": is_scanned,
            "text": text_content,
            "images": images,
            **structured,
        }

    def _extract_text(self, path: str) -> str:
        texts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
        return "\n".join(texts)

    def _extract_images(self, path: str) -> list[str]:
        doc = fitz.open(path)
        image_paths = []
        img_dir = Path(path).parent / "pdf_images"
        img_dir.mkdir(exist_ok=True)
        for page_num in range(len(doc)):
            page = doc[page_num]
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                img_path = img_dir / f"page{page_num + 1}_img{img_index + 1}.{ext}"
                with open(img_path, "wb") as f:
                    f.write(image_bytes)
                image_paths.append(str(img_path))
        doc.close()
        return image_paths

    async def _ocr_pages(self, path: str) -> str:
        doc = fitz.open(path)
        texts = []
        img_dir = Path(path).parent / "pdf_ocr"
        img_dir.mkdir(exist_ok=True)
        for i in range(min(len(doc), 10)):  # 最多 OCR 10 页
            page = doc[i]
            pix = page.get_pixmap(dpi=200)
            img_path = img_dir / f"page_{i + 1}.png"
            pix.save(str(img_path))
            prompt = "请识别这张图片中的所有文字，保持原有段落格式输出。"
            text = await vlm_client.describe(str(img_path), prompt)
            texts.append(text)
        doc.close()
        return "\n".join(texts)

    async def _extract_requirements(self, text: str) -> dict[str, Any]:
        system = "你是一位需求文档分析师，擅长从设计需求书中提取结构化信息。"
        prompt = (
            f"请从以下需求文档中提取关键信息，输出 JSON（只输出 JSON）：\n\n{text[:4000]}\n\n"
            "输出字段：\n"
            '{"theme": "主题", "style": "风格", "space_type": "空间类型", '
            '"budget": "预算", "timeline": "工期", "requirements": ["需求列表"], '
            '"restrictions": ["限制条件"]}'
        )
        raw = await llm_client.complete(system, prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_description": raw, "parse_error": True}
