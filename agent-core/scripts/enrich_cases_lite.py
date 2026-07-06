"""使用 LLM 轻量清洗设计案例数据（字段精简，速度更快）。

只提取最核心的 5 个字段，适合本地 14B 模型快速处理。

使用方式：
    python agent-core/scripts/enrich_cases_lite.py \
        --input /Users/liulei/private-work/design-data/temp/adesign_samples_v1.jsonl \
        --output /Users/liulei/private-work/design-data/temp/adesign_samples_v1_enriched.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.llm_client import llm_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """你是一位资深美陈设计资料整理专家。请根据以下设计案例提取核心信息，输出合法 JSON。

标题：{title}
类型：{project_type} / {space_type}
概念：{concept_statement}
氛围：{atmosphere_description}
材料：{materials}
标签：{keywords}

输出 JSON（只输出 JSON，不要其他文字）：
{{
    "design_theme": "30字内设计主题",
    "design_style": "设计风格",
    "color_palette": [{{"name": "颜色", "hex": "#RRGGBB", "role": "主色/辅色/点缀色"}}],
    "materials_parsed": [{{"material": "材料", "usage": "用途"}}],
    "creative_summary": "80字内创意总结"
}}"""


def build_prompt(case: dict[str, Any]) -> str:
    """构建精简 Prompt。"""
    return PROMPT_TEMPLATE.format(
        title=case.get("title", ""),
        project_type=case.get("project_type", ""),
        space_type=case.get("space_type", ""),
        concept_statement=case.get("concept_statement", "")[:250],
        atmosphere_description=case.get("atmosphere_description", "")[:250],
        materials=case.get("materials", "")[:250],
        keywords=case.get("keywords", ""),
    )


def parse_llm_output(raw: str) -> dict[str, Any]:
    """解析 LLM 返回的 JSON。"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r'\{[\s\S]*\}', raw)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def merge_enriched(case: dict[str, Any], enriched: dict[str, Any]) -> dict[str, Any]:
    """合并清洗字段。"""
    result = dict(case)
    result["enriched"] = enriched
    result["enriched_at"] = time.time()

    for key in ["design_theme", "design_style", "color_palette", "materials_parsed", "creative_summary"]:
        if key in enriched:
            result[key] = enriched[key]

    return result


async def enrich_cases(input_path: str, output_path: str) -> None:
    """批量清洗案例数据，带断点续传。"""
    input_file = Path(input_path)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    processed_count = 0
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            processed_count = sum(1 for _ in f if _.strip())
        logger.info("[RESUME] already processed %d cases", processed_count)

    remaining = cases[processed_count:]
    logger.info("[START] total=%d, remaining=%d", len(cases), len(remaining))

    with open(output_file, "a", encoding="utf-8") as f:
        for i, case in enumerate(remaining):
            idx = processed_count + i + 1
            logger.info("[ENRICH %d/%d] %s", idx, len(cases), case.get("title", "")[:50])

            prompt = build_prompt(case)
            start = time.time()
            raw = await llm_client.complete(
                "",
                prompt,
                json_mode=False,
                temperature=0.3,
            )
            elapsed = time.time() - start
            logger.info("[LLM] elapsed %.1fs for %s", elapsed, case.get("title", "")[:30])

            enriched = parse_llm_output(raw) if raw else {}
            if not enriched:
                logger.warning("[PARSE FAILED] %s", case.get("title", ""))

            result = merge_enriched(case, enriched)
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            f.flush()

    logger.info("[DONE] saved enriched cases to %s", output_file)


def main():
    parser = argparse.ArgumentParser(description="Lite enrich design cases with LLM")
    parser.add_argument(
        "--input",
        default="/Users/liulei/private-work/design-data/temp/adesign_samples_v1.jsonl",
        help="输入 JSONL 文件路径",
    )
    parser.add_argument(
        "--output",
        default="/Users/liulei/private-work/design-data/temp/adesign_samples_v1_enriched.jsonl",
        help="输出 JSONL 文件路径",
    )
    args = parser.parse_args()

    asyncio.run(enrich_cases(args.input, args.output))


if __name__ == "__main__":
    main()
