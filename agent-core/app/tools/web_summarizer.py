from __future__ import annotations

import logging
from typing import Any

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM_PROMPT = (
    "你是信息整理助手。请根据提供的网页正文/摘要，用中文简洁、准确地回答用户问题。"
    "如果信息有冲突，请说明。最后必须列出参考来源（编号、标题、链接）。"
)

_MAX_TOTAL_CHARS = 6000


async def summarize(query: str, fetched: list[dict[str, Any]], client: LLMClient) -> str:
    """调用 LLM 对抓取内容生成中文摘要。"""
    if not fetched:
        return "未找到可总结的网页内容。"

    source_lines: list[str] = []
    for i, item in enumerate(fetched, 1):
        flag = "（摘要）" if item.get("used_snippet_fallback") else ""
        source_lines.append(
            f"[{i}]{flag} {item.get('title', '')}\n链接：{item.get('link', '')}\n内容：{item.get('text', '')}"
        )

    user_prompt = (
        f"用户问题：{query}\n\n"
        "以下是搜索结果中的网页内容：\n"
        + "\n\n".join(source_lines)
    )[:_MAX_TOTAL_CHARS]

    try:
        summary = await client.complete(_SUMMARY_SYSTEM_PROMPT, user_prompt, temperature=0.5)
        summary = summary.strip()
        if not summary:
            raise ValueError("empty summary")
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)
        summary = "已搜索到以下结果，但未能生成摘要，请直接查看来源。"

    references = [f"{i}. {item.get('title', '')}\n   {item.get('link', '')}" for i, item in enumerate(fetched, 1)]
    return summary + "\n\n参考来源：\n" + "\n".join(references)
