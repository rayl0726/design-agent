from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.models.database import SessionLocal
from app.models.project import DesignCase
from app.services.embedding_client import embedding_client
from app.services.knowledge_base import knowledge_base
from app.services.llm_client import llm_client


SYSTEM_PROMPT = "你是一位美陈设计资料整理专家，擅长从案例描述中提取结构化信息。"


async def extract_case_info(text: str, image_paths: list[str]) -> dict:
    prompt = (
        "请从以下美陈设计案例描述中提取结构化信息，输出 JSON（只输出 JSON）：\n\n"
        f"{text[:3000]}\n\n"
        "输出字段：\n"
        '{"title": "案例标题", "space_type": "空间类型", "budget_level": "预算档次(low/medium/high)", '
        '"theme": "主题", "style": "风格", "summary": "200字以内案例摘要"}'
    )
    raw = await llm_client.complete(SYSTEM_PROMPT, prompt, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"title": "未命名案例", "summary": text[:200], "parse_error": True}


async def ingest_case_file(text_path: Path, image_dir: Path | None = None):
    text = text_path.read_text(encoding="utf-8")
    images = []
    if image_dir and image_dir.exists():
        images = sorted(image_dir.glob("*"))

    info = await extract_case_info(text, [str(i) for i in images])

    db = SessionLocal()
    try:
        case = DesignCase(
            title=info.get("title", text_path.stem),
            space_type=info.get("space_type"),
            budget_level=info.get("budget_level"),
            theme=info.get("theme"),
            style=info.get("style"),
            summary=info.get("summary", text[:500]),
            images_json=json.dumps([str(i) for i in images]),
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        # 写入 Milvus
        embedding = await embedding_client.embed(case.summary or case.title)
        collection = knowledge_base._get_case_collection()
        collection.insert([
            [case.id],
            [embedding],
            [case.title],
            [case.space_type or ""],
            [case.budget_level or ""],
            [case.theme or ""],
            [case.style or ""],
            [case.summary or ""],
        ])
        collection.flush()

        print(f"[OK] 导入案例: {case.title} ({case.id})")
        return case.id
    finally:
        db.close()


async def main():
    parser = argparse.ArgumentParser(description="导入设计案例到知识库")
    parser.add_argument("--source", required=True, help="案例文本文件或目录")
    parser.add_argument("--images", help="案例图片目录")
    args = parser.parse_args()

    source = Path(args.source)
    image_dir = Path(args.images) if args.images else None

    if source.is_file():
        await ingest_case_file(source, image_dir)
    elif source.is_dir():
        for text_file in source.glob("*.txt"):
            await ingest_case_file(text_file, image_dir)
    else:
        print(f"[ERROR] 路径不存在: {source}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
