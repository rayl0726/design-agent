"""使用 LLM 清洗和补全设计案例数据。

读取原始 JSONL，调用 Ollama (qwen2.5:14b) 提取/补全结构化字段，
输出清洗后的 JSONL。

使用方式：
    python agent-core/scripts/enrich_cases_with_llm.py \
        --input /Users/liulei/private-work/design-data/temp/adesign_samples_v1.jsonl \
        --output /Users/liulei/private-work/design-data/temp/adesign_samples_v1_enriched.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
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

USER_PROMPT_TEMPLATE = """你是一位资深美陈设计资料整理专家。请根据提供的商业空间/展览/美陈设计案例原始文本，提取并补全结构化字段。

规则：
1. 基于原文信息推断和总结，不要编造不存在的信息
2. 如果原文没有明确信息，填写"未明确"
3. 输出必须是合法 JSON，不要包含任何其他说明文字
4. 配色方案请给出 HEX 颜色值
5. 保持简洁专业

【原始案例信息】
标题：{title}
项目类型：{project_type}
空间类型：{space_type}
核心概念：{concept_statement}
氛围描述：{atmosphere_description}
材料工艺：{materials}
关键词标签：{keywords}

请输出以下 JSON 字段：
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

只输出 JSON："""


def build_prompt(case: dict[str, Any]) -> str:
    """为单个案例构建清洗 Prompt。"""
    return USER_PROMPT_TEMPLATE.format(
        title=case.get("title", ""),
        project_type=case.get("project_type", ""),
        space_type=case.get("space_type", ""),
        concept_statement=case.get("concept_statement", "")[:500],
        atmosphere_description=case.get("atmosphere_description", "")[:500],
        materials=case.get("materials", "")[:500],
        keywords=case.get("keywords", ""),
    )


def parse_llm_output(raw: str) -> dict[str, Any]:
    """解析 LLM 返回的 JSON。"""
    # 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    import re
    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试提取第一个 JSON 对象
    brace_match = re.search(r'\{[\s\S]*\}', raw)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning("[PARSE FAILED] raw: %s", raw[:200])
    return {}


async def enrich_one(case: dict[str, Any], index: int, total: int) -> dict[str, Any]:
    """清洗单个案例。"""
    logger.info("[ENRICH %d/%d] %s", index, total, case.get("title", "")[:50])

    prompt = build_prompt(case)
    raw_output = await llm_client.complete(
        "",  # 不使用 system prompt，避免部分模型异常
        prompt,
        json_mode=False,
        temperature=0.3,
    )

    if not raw_output:
        logger.warning("[EMPTY] LLM returned empty for %s", case.get("title", ""))
        return case

    enriched = parse_llm_output(raw_output)

    # 合并清洗后的字段
    result = dict(case)
    result["enriched"] = enriched
    result["enriched_at"] = asyncio.get_event_loop().time()

    # 将清洗后的字段提升到顶层（方便使用）
    for key in [
        "design_theme", "design_style", "color_palette", "materials_parsed",
        "forms", "lighting", "interactive_elements", "brand_tone",
        "target_audience", "marketing_objective", "emotional_value",
        "budget_level", "creative_summary",
    ]:
        if key in enriched:
            result[key] = enriched[key]

    return result


async def enrich_cases(input_path: str, output_path: str, max_concurrent: int = 1) -> None:
    """批量清洗案例数据。"""
    input_file = Path(input_path)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 读取原始数据
    with open(input_file, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    logger.info("[LOADED] %d cases from %s", len(cases), input_file)

    # 并发清洗（控制并发数避免 Ollama 过载）
    semaphore = asyncio.Semaphore(max_concurrent)

    async def worker(i: int, case: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await enrich_one(case, i + 1, len(cases))

    tasks = [worker(i, case) for i, case in enumerate(cases)]
    enriched_cases = await asyncio.gather(*tasks)

    # 保存结果
    with open(output_file, "w", encoding="utf-8") as f:
        for case in enriched_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    logger.info("[DONE] saved %d enriched cases to %s", len(enriched_cases), output_file)


def main():
    parser = argparse.ArgumentParser(description="Enrich design cases with LLM")
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
        "--max-concurrent",
        type=int,
        default=3,
        help="最大并发数",
    )
    args = parser.parse_args()

    asyncio.run(enrich_cases(args.input, args.output, args.max_concurrent))


if __name__ == "__main__":
    main()
