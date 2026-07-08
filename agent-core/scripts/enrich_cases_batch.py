"""使用 LLM 批量清洗设计案例数据（更快，带断点续传）。

将案例分批送入 Ollama，每批返回多个清洗结果，显著减少模型加载和请求开销。

使用方式：
    python agent-core/scripts/enrich_cases_batch.py \
        --input /Users/liulei/private-work/design-data/temp/adesign_samples_v1.jsonl \
        --output /Users/liulei/private-work/design-data/temp/adesign_samples_v1_enriched.jsonl \
        --batch-size 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.llm_client import llm_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CASE_TEMPLATE = """案例 {idx}:
标题：{title}
项目类型：{project_type}
空间类型：{space_type}
核心概念：{concept_statement}
氛围描述：{atmosphere_description}
材料工艺：{materials}
关键词标签：{keywords}"""

BATCH_PROMPT_TEMPLATE = """你是一位资深美陈设计资料整理专家。请根据以下商业空间/展览/美陈设计案例，提取并补全结构化字段。

规则：
1. 基于原文信息推断和总结，不要编造不存在的信息
2. 如果原文没有明确信息，填写"未明确"
3. 输出必须是合法 JSONL 格式：每行一个 JSON 对象，总共 {batch_size} 行
4. 配色方案请给出 HEX 颜色值
5. 保持简洁专业

{cases}

请为以上 {batch_size} 个案例各输出一行 JSON，字段如下：
{{
    "design_theme": "设计主题（一句话）",
    "design_style": "设计风格",
    "color_palette": [{{"name": "颜色名", "hex": "#FF6B6B", "role": "主色/辅色/点缀色"}}],
    "materials_parsed": [{{"material": "材料", "usage": "用途"}}],
    "forms": "形态特征（50字内）",
    "lighting": "灯光设计（50字内）",
    "interactive_elements": "互动元素（50字内，无则写无）",
    "brand_tone": "品牌调性",
    "target_audience": "目标人群",
    "marketing_objective": "营销目标",
    "emotional_value": "情感价值（50字内）",
    "budget_level": "低/中/高/顶级",
    "creative_summary": "100字以内创意总结"
}}

只输出 JSONL，不要任何其他说明文字。"""


def build_case_text(idx: int, case: dict[str, Any]) -> str:
    """为单个案例构建输入文本。"""
    return CASE_TEMPLATE.format(
        idx=idx,
        title=case.get("title", ""),
        project_type=case.get("project_type", ""),
        space_type=case.get("space_type", ""),
        concept_statement=case.get("concept_statement", "")[:400],
        atmosphere_description=case.get("atmosphere_description", "")[:400],
        materials=case.get("materials", "")[:400],
        keywords=case.get("keywords", ""),
    )


def parse_jsonl(raw: str, expected_count: int) -> list[dict[str, Any]]:
    """从 LLM 输出中解析 JSONL。"""
    results: list[dict[str, Any]] = []

    # 尝试直接按行解析
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if len(results) == expected_count:
        return results

    # 尝试从代码块中提取
    code_block = re.search(r'```(?:jsonl?)?\s*([\s\S]*?)```', raw)
    if code_block:
        results = []
        for line in code_block.group(1).strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if len(results) == expected_count:
            return results

    # 尝试提取所有 JSON 对象
    if len(results) != expected_count:
        results = []
        for match in re.finditer(r'\{[\s\S]*?\}', raw):
            try:
                obj = json.loads(match.group(0))
                if isinstance(obj, dict):
                    results.append(obj)
            except json.JSONDecodeError:
                continue

    return results[:expected_count]


def merge_enriched(case: dict[str, Any], enriched: dict[str, Any]) -> dict[str, Any]:
    """将清洗后的字段合并回原案例。"""
    result = dict(case)
    result["enriched"] = enriched
    result["enriched_at"] = asyncio.get_event_loop().time()

    for key in [
        "design_theme", "design_style", "color_palette", "materials_parsed",
        "forms", "lighting", "interactive_elements", "brand_tone",
        "target_audience", "marketing_objective", "emotional_value",
        "budget_level", "creative_summary",
    ]:
        if key in enriched:
            result[key] = enriched[key]

    return result


async def enrich_batch(cases: list[dict[str, Any]], start_idx: int) -> list[dict[str, Any]]:
    """清洗一批案例。"""
    case_texts = [build_case_text(start_idx + i + 1, case) for i, case in enumerate(cases)]
    prompt = BATCH_PROMPT_TEMPLATE.format(
        cases="\n\n".join(case_texts),
        batch_size=len(cases),
    )

    logger.info("[BATCH] processing %d cases starting from #%d", len(cases), start_idx + 1)

    raw_output = await llm_client.complete(
        "",
        prompt,
        json_mode=False,
        temperature=0.3,
    )

    if not raw_output:
        logger.warning("[EMPTY] LLM returned empty for batch starting at %d", start_idx + 1)
        return [merge_enriched(case, {}) for case in cases]

    enriched_list = parse_jsonl(raw_output, len(cases))

    if len(enriched_list) != len(cases):
        logger.warning(
            "[PARSE MISMATCH] expected %d, got %d for batch starting at %d",
            len(cases), len(enriched_list), start_idx + 1,
        )

    results = []
    for i, case in enumerate(cases):
        enriched = enriched_list[i] if i < len(enriched_list) else {}
        results.append(merge_enriched(case, enriched))

    return results


async def enrich_cases(
    input_path: str,
    output_path: str,
    batch_size: int = 3,
) -> None:
    """批量清洗案例数据，支持断点续传。"""
    input_file = Path(input_path)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 读取原始数据
    with open(input_file, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    # 检查已有进度
    processed_count = 0
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            processed_count = sum(1 for _ in f if _.strip())
        logger.info("[RESUME] already processed %d cases", processed_count)

    remaining_cases = cases[processed_count:]
    logger.info("[LOADED] total=%d, remaining=%d", len(cases), len(remaining_cases))

    # 分批处理并追加写入
    with open(output_file, "a", encoding="utf-8") as f:
        for i in range(0, len(remaining_cases), batch_size):
            batch = remaining_cases[i : i + batch_size]
            start_idx = processed_count + i

            enriched_batch = await enrich_batch(batch, start_idx)

            for case in enriched_batch:
                f.write(json.dumps(case, ensure_ascii=False) + "\n")

            logger.info(
                "[PROGRESS] saved %d/%d",
                processed_count + i + len(batch),
                len(cases),
            )

    logger.info("[DONE] saved all enriched cases to %s", output_file)


def main():
    parser = argparse.ArgumentParser(description="Batch enrich design cases with LLM")
    parser.add_argument(
        "--input",
        default="/Users/liulei/private-work/design-agent/design-data/temp/adesign_samples_v1.jsonl",
        help="输入 JSONL 文件路径",
    )
    parser.add_argument(
        "--output",
        default="/Users/liulei/private-work/design-agent/design-data/temp/adesign_samples_v1_enriched.jsonl",
        help="输出 JSONL 文件路径",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="每批处理的案例数",
    )
    args = parser.parse_args()

    asyncio.run(enrich_cases(args.input, args.output, args.batch_size))


if __name__ == "__main__":
    main()
