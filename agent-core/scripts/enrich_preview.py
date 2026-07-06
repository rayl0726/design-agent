"""快速清洗前 N 条样本用于预览。"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.enrich_cases_lite import build_prompt, parse_llm_output, merge_enriched
from app.services.llm_client import llm_client
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def enrich_preview(input_path: str, output_path: str, count: int = 3) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    preview_cases = cases[:count]
    logger.info("[PREVIEW] will enrich %d cases", len(preview_cases))

    results = []
    for i, case in enumerate(preview_cases):
        logger.info("[ENRICH %d/%d] %s", i + 1, len(preview_cases), case.get("title", "")[:50])
        prompt = build_prompt(case)
        start = time.time()
        raw = await llm_client.complete("", prompt, json_mode=False, temperature=0.3)
        elapsed = time.time() - start
        logger.info("[LLM] elapsed %.1fs", elapsed)
        enriched = parse_llm_output(raw) if raw else {}
        results.append(merge_enriched(case, enriched))

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info("[DONE] saved %d preview cases to %s", len(results), output_file)


if __name__ == "__main__":
    input_path = "/Users/liulei/private-work/design-data/temp/adesign_samples_v1.jsonl"
    output_path = "/Users/liulei/private-work/design-data/temp/adesign_samples_preview_enriched.jsonl"
    count = 3
    asyncio.run(enrich_preview(input_path, output_path, count))
