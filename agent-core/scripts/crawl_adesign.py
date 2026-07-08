"""A'Design Award 爬虫：采集商业空间/零售美陈/装置艺术案例。

使用方式：
    python agent-core/scripts/crawl_adesign.py --output /Users/liulei/private-work/design-agent/design-data/temp --limit 50
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://competition.adesignaward.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# A'Design Award 详情页字段
DETAIL_FIELDS = [
    "DESIGN NAME",
    "PRIMARY FUNCTION",
    "INSPIRATION",
    "UNIQUE PROPERTIES / PROJECT DESCRIPTION",
    "OPERATION / FLOW / INTERACTION",
    "PROJECT DURATION AND LOCATION",
    "PRODUCTION / REALIZATION TECHNOLOGY",
    "SPECIFICATIONS / TECHNICAL PROPERTIES",
    "TAGS",
    "RESEARCH ABSTRACT",
    "CHALLENGE",
]

# 强相关关键词：命中即保留（词组匹配更精准）
STRONG_KEYWORDS = [
    "visual merchandising", "retail vm", "window display", "shop window",
    "retail display", "store display", "display design",
    "shopping mall", "mall interior", "mall design", "mall atrium",
    "retail interior", "retail space", "retail store", "retail design",
    "flagship store", "flagship",
    "boutique", "department store", "concept store",
    "showroom", "trade show booth", "exhibition booth",
    "exhibition design", "exhibition space",
    "pop-up", "popup", "pop up store", "pop-up store",
    "commercial installation", "art installation", "interactive installation",
    "event design", "festival decoration", "seasonal display",
    "brand experience", "immersive experience", "customer experience",
    "experience space", "experience center", "sales center", "sales centre",
    "culture center", "cultural space",
]

# 中等相关关键词：命中两个以上保留（单个词）
MEDIUM_KEYWORDS = [
    "retail", "commercial", "display", "installation", "exhibition",
    "mall", "showroom", "boutique", "flagship", "pop-up", "popup",
    "lobby", "atrium", "plaza", "public space", "cultural",
]

# 明确不相关的关键词（排除住宅、家具、医疗、办公等）
IRRELEVANT_KEYWORDS = [
    "residential", "apartment", "house", "home interior", "private residence",
    "villa", "living room", "bedroom", "kitchen", "bathroom", "toilet",
    "office", "headquarters", "workplace", "coworking",
    "clinic", "hospital", "medical", "dental", "healthcare",
    "school", "classroom", "kindergarten", "library", "university",
    "restaurant", "cafe", "bar", "hotel", "spa", "salon",
    "packaging design", "logo design", "brand identity", "graphic design",
    "app design", "website design", "ui design", "ux design",
    "vehicle", "car design", "yacht", "aircraft",
]


class ADesignCrawler:
    """A'Design Award 爬虫。"""

    def __init__(self, output_dir: str, delay: float = 2.0, limit: int = 50):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.limit = limit
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch(self, url: str) -> str:
        """获取页面内容，带简单重试。"""
        for attempt in range(3):
            try:
                time.sleep(self.delay)
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as exc:
                logger.warning("[RETRY %d/3] %s: %s", attempt + 1, url, exc)
                time.sleep(2 ** attempt)
        return ""

    def discover_urls(self, category: int = 8, page: int = 1) -> list[str]:
        """从分类获奖列表页发现详情页 URL。

        默认 CATEGORY=8 对应 "Interior Space and Exhibition Design"，
        包含 retail store, exhibition, pop-up, window display 等商业空间案例。
        """
        url = f"{BASE_URL}/design-award-winners.php"
        params = {"CATEGORY": category, "PAGE": page}

        logger.info("[DISCOVER] %s params=%s", url, params)
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "gooddesign.php?ID=" in href or "design.php?ID=" in href:
                # 统一转换为 design.php 详情页
                full_url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
                full_url = full_url.replace("gooddesign.php", "design.php")
                if full_url not in links:
                    links.append(full_url)

        logger.info("[DISCOVER] found %d urls", len(links))
        return links

    def parse_detail(self, html: str, url: str) -> dict[str, Any]:
        """解析详情页，提取结构化字段。"""
        # 标题：优先从 <title> 提取，格式为 "A' Design Award and Competition - Title"
        title = ""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
        if title_match:
            raw_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            # 去掉前缀 "A' Design Award and Competition - "
            title = re.sub(r"^A['\u2019]\s*Design\s+Award\s+and\s+Competition\s*-\s*", "", raw_title, flags=re.I)
            # 去掉后缀 "by Designer"
            title = re.sub(r"\s+by\s+.*$", "", title)

        # 清理 HTML 标签
        clean_text = re.sub(r'<[^>]+>', ' ', html)
        clean_text = re.sub(r'\s+', ' ', clean_text)

        # 定位 DESIGN DETAILS 区域
        start_idx = clean_text.find('DESIGN NAME:')
        end_idx = clean_text.find('CLIENT/STUDIO/BRAND DETAILS')
        if end_idx == -1:
            end_idx = clean_text.find('NOMINATION DETAILS')
        if end_idx == -1:
            end_idx = len(clean_text)

        if start_idx == -1:
            return {"title": title, "source_url": url, "parse_error": "DESIGN NAME not found"}

        section = clean_text[start_idx:end_idx]

        # 使用字段名分割文本
        field_pattern = r'\n?\s*(' + '|'.join(re.escape(f) for f in DETAIL_FIELDS) + r')\s*:\s*'
        parts = re.split(field_pattern, section)

        result = {"title": title, "source_url": url}
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                field_name = parts[i].strip()
                value = parts[i + 1].strip()
                result[field_name] = value

        # 提取图片（A'Design Award 真实图片路径为 ./designs/<hash>-N-thumb.jpg）
        images = []
        seen = set()
        for img_match in re.finditer(r'<img[^>]+src\s*=\s*["\'](\.?/designs/[^"\']+-thumb(?:-big)?\.jpg(?:\?[^"\']*)?)["\']', html):
            src = img_match.group(1)
            # 转为大图 URL
            large = re.sub(r'-thumb(?:-big)?\.jpg', '.jpg', src)
            large = large.lstrip('.')
            full_url = f"{BASE_URL}{large}"
            if full_url not in seen:
                seen.add(full_url)
                images.append(full_url)
        result["images"] = images[:10]

        # 提取奖项信息
        award_match = re.search(r'(Platinum Winner|Gold Winner|Silver Winner|Bronze Winner|Iron Winner|Winner)', clean_text)
        if award_match:
            result["award_level"] = award_match.group(1)

        # 提取类别：A'Design Award 分类名通常为 "Interior Space and Exhibition Design Award Category"
        category_match = re.search(r'([A-Za-z\s&,]+)\s+Design\s+Award\s+Category', clean_text)
        if category_match:
            result["category"] = category_match.group(1).strip() + " Design"
        else:
            # 备选：从 DESIGN DETAILS 区域之前的文本提取
            prefix = clean_text[:start_idx]
            cat_match = re.search(r'([A-Za-z\s&,]+)\s+Design\s+Award', prefix)
            if cat_match:
                result["category"] = cat_match.group(1).strip() + " Design"

        return result

    def is_relevant(self, data: dict[str, Any]) -> bool:
        """判断案例是否与商业空间/美陈相关。

        规则：
        1. 包含强相关关键词 -> 保留
        2. 包含明显不相关关键词 -> 排除
        3. 否则根据中等关键词命中数量判断

        关键词匹配使用词边界，避免 "spa" 误杀 "spatial" 等情况。
        """
        text = " ".join([
            data.get("PRIMARY FUNCTION", ""),
            data.get("category", ""),
            data.get("TAGS", ""),
            data.get("UNIQUE PROPERTIES / PROJECT DESCRIPTION", ""),
            data.get("title", ""),
        ]).lower()

        def has_word(text: str, keyword: str) -> bool:
            """使用词边界匹配关键词。"""
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            return bool(re.search(pattern, text))

        # 如果包含明显不相关关键词，直接排除
        if any(has_word(text, kw) for kw in IRRELEVANT_KEYWORDS):
            return False

        # 包含强相关关键词，直接保留
        if any(has_word(text, kw) for kw in STRONG_KEYWORDS):
            return True

        # 命中至少两个中等关键词才保留
        medium_hits = sum(1 for kw in MEDIUM_KEYWORDS if has_word(text, kw))
        return medium_hits >= 2

    def map_to_v2(self, data: dict[str, Any]) -> dict[str, Any]:
        """将 A'Design Award 字段映射到 DesignCase V2 结构。"""
        description = data.get("UNIQUE PROPERTIES / PROJECT DESCRIPTION", "")
        inspiration = data.get("INSPIRATION", "")
        challenge = data.get("CHALLENGE", "")

        # 构建创意故事
        creative_story = " ".join(filter(None, [
            inspiration,
            data.get("OPERATION / FLOW / INTERACTION", ""),
            data.get("RESEARCH ABSTRACT", ""),
        ]))

        # 构建氛围描述
        atmosphere = " ".join(filter(None, [
            data.get("OPERATION / FLOW / INTERACTION", ""),
            challenge,
        ]))

        # 提取材料
        materials_text = data.get("PRODUCTION / REALIZATION TECHNOLOGY", "")

        # 提取尺寸
        specs = data.get("SPECIFICATIONS / TECHNICAL PROPERTIES", "")

        record = {
            "title": data.get("DESIGN NAME") or data.get("title", ""),
            "project_type": self._infer_project_type(data),
            "space_type": self._infer_space_type(data),
            "space_size": specs,
            "budget_level": "",
            "source_url": data.get("source_url", ""),
            "brand": "",
            "marketing_objective": "",
            "target_audience": "",
            "brand_tone": "",
            "concept_statement": inspiration[:500] if inspiration else description[:500],
            "design_theme": data.get("DESIGN NAME", ""),
            "design_style": "",
            "creative_story": creative_story[:2000],
            "atmosphere_description": atmosphere[:1500],
            "emotional_value": challenge[:1000],
            "color_palette": "",
            "materials": materials_text[:1500],
            "forms": "",
            "lighting": "",
            "interactive_elements": "",
            "installation_period": data.get("PROJECT DURATION AND LOCATION", ""),
            "display_period": "",
            "technical_features": materials_text[:1000],
            "challenges_overcome": challenge[:1500],
            "foot_traffic_increase": "",
            "sales_increase": "",
            "social_media_coverage": "",
            "client_feedback": "",
            "keywords": data.get("TAGS", ""),
            "tags": data.get("TAGS", ""),
            "award_level": data.get("award_level", ""),
            "category": data.get("category", ""),
            "primary_function": data.get("PRIMARY FUNCTION", ""),
            "images": data.get("images", []),
            "raw_data": data,
        }
        record["quality_score"] = self._estimate_quality(record)
        return record

    def _estimate_quality(self, record: dict[str, Any]) -> float:
        """基于字段完整度给出简单质量评分。"""
        score = 0.0
        if record.get("concept_statement"):
            score += 0.2
        if record.get("creative_story"):
            score += 0.2
        if record.get("atmosphere_description"):
            score += 0.2
        if record.get("materials"):
            score += 0.1
        if record.get("space_size"):
            score += 0.1
        if record.get("images"):
            score += 0.1
        if record.get("award_level"):
            score += 0.1
        return round(min(score, 1.0), 2)

    def _infer_project_type(self, data: dict[str, Any]) -> str:
        """推断项目类型。"""
        text = " ".join([
            data.get("PRIMARY FUNCTION", ""),
            data.get("TAGS", ""),
            data.get("title", ""),
        ]).lower()

        if any(kw in text for kw in ["retail vm", "window display", "visual merchandising"]):
            return "视觉陈列/美陈"
        if any(kw in text for kw in ["interior", "retail interior"]):
            return "商业空间"
        if any(kw in text for kw in ["event", "happening", "festival"]):
            return "活动/节庆装置"
        if any(kw in text for kw in ["installation", "sculpture"]):
            return "艺术装置"
        if any(kw in text for kw in ["exhibition"]):
            return "展览展示"
        return "商业空间"

    def _infer_space_type(self, data: dict[str, Any]) -> str:
        """推断空间类型。"""
        text = " ".join([
            data.get("UNIQUE PROPERTIES / PROJECT DESCRIPTION", ""),
            data.get("TAGS", ""),
        ]).lower()

        if any(kw in text for kw in ["mall", "shopping mall", "atrium", "lobby"]):
            return "商场中庭/大堂"
        if any(kw in text for kw in ["store", "shop", "boutique", "flagship"]):
            return "店铺/门店"
        if any(kw in text for kw in ["window", "show window"]):
            return "橱窗"
        if any(kw in text for kw in ["plaza", "square", "outdoor"]):
            return "广场/户外"
        if any(kw in text for kw in ["exhibition", "gallery", "museum"]):
            return "展厅/展馆"
        return "商业空间"

    def run(self) -> None:
        """运行爬虫。"""
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"adesign_cases_{ts}.jsonl"

        # 发现 URL（优先从 Interior Space and Exhibition Design 分类抓取）
        all_urls: list[str] = []
        seen_urls: set[str] = set()
        page = 1
        max_pages = (self.limit * 5 // 20) + 5  # 多翻页保证过滤后足够
        while len(all_urls) < self.limit * 5 and page <= max_pages:
            try:
                urls = self.discover_urls(category=8, page=page)
                if not urls:
                    break
                new_urls = [u for u in urls if u not in seen_urls]
                seen_urls.update(new_urls)
                all_urls.extend(new_urls)
                logger.info("[DISCOVER] page=%d, new=%d, total urls: %d", page, len(new_urls), len(all_urls))
                page += 1
            except Exception as exc:
                logger.error("[DISCOVER ERROR] page=%d: %s", page, exc)
                break

        all_urls = all_urls[: self.limit * 5]
        logger.info("[START] will process up to %d urls, target %d cases", len(all_urls), self.limit)

        saved = 0
        processed = 0
        for url in all_urls:
            if saved >= self.limit:
                break

            processed += 1
            try:
                html = self.fetch(url)
                if not html:
                    continue

                data = self.parse_detail(html, url)
                if "parse_error" in data:
                    logger.warning("[PARSE ERROR] %s", url)
                    continue

                if not self.is_relevant(data):
                    logger.info("[SKIP] not relevant: %s", url)
                    continue

                v2_record = self.map_to_v2(data)

                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(v2_record, ensure_ascii=False) + "\n")

                saved += 1
                logger.info("[SAVED %d/%d] %s", saved, self.limit, v2_record.get("title", "")[:60])

            except Exception as exc:
                logger.exception("[ERROR] %s: %s", url, exc)

        logger.info("[DONE] processed %d, saved %d cases to %s", processed, saved, output_file)


def main():
    parser = argparse.ArgumentParser(description="Crawl A'Design Award cases")
    parser.add_argument("--output", default="/Users/liulei/private-work/design-agent/design-data/temp", help="输出目录")
    parser.add_argument("--limit", type=int, default=50, help="采集数量")
    parser.add_argument("--delay", type=float, default=2.0, help="请求间隔秒数")
    args = parser.parse_args()

    crawler = ADesignCrawler(output_dir=args.output, delay=args.delay, limit=args.limit)
    crawler.run()


if __name__ == "__main__":
    main()
