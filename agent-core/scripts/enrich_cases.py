import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, init_db
from app.models.project import DesignCase


async def enrich_existing_cases():
    from app.services.llm_client import llm_client
    
    init_db()
    db = SessionLocal()
    
    try:
        cases = db.query(DesignCase).filter(
            (DesignCase.theme == "") | (DesignCase.theme.is_(None))
        ).all()
        
        print(f"发现 {len(cases)} 条需要补全的案例")
        
        for case in cases:
            print(f"\n处理案例: {case.title}")
            
            prompt = f"""
请分析以下设计案例，提取结构化信息。这是一个美陈设计案例分析任务。

案例标题：{case.title}
案例摘要：{case.summary}

请提取以下字段（如果无法确定，留空）：
- theme: 主题（如：春节、圣诞节、夏日清凉、科技未来等）
- style: 风格（如：现代简约、高端奢华、创意互动、复古怀旧、国潮新中式等）
- space_type: 空间类型（如：中庭、入口、橱窗、快闪店、走廊、广场等）
- budget_level: 预算等级（如：low-低预算、medium-中等预算、high-高预算、premium-顶级预算）

请只输出JSON格式，不要包含其他内容：
{{"theme": "", "style": "", "space_type": "", "budget_level": ""}}
"""
            
            try:
                response = await llm_client.complete("你是一位美陈设计专家，擅长分析设计案例并提取关键信息", prompt, json_mode=True)
                result = json.loads(response)
                
                case.theme = result.get("theme", "")
                case.style = result.get("style", "")
                case.space_type = result.get("space_type", "")
                case.budget_level = result.get("budget_level", "")
                
                print(f"提取结果: theme={case.theme}, style={case.style}, space_type={case.space_type}, budget_level={case.budget_level}")
                
                db.commit()
                
            except Exception as e:
                print(f"处理失败: {e}")
                db.rollback()
    finally:
        db.close()


async def generate_high_quality_cases(count: int = 20):
    from app.services.llm_client import llm_client
    
    print(f"\n生成 {count} 条高质量美陈设计案例...")
    
    init_db()
    db = SessionLocal()
    
    try:
        for i in range(count):
            prompt = f"""
请生成一条高质量的美陈设计案例数据。

要求：
1. 主题多样化（如：春节、中秋节、圣诞节、夏日主题、科技展、艺术展、品牌周年庆等）
2. 风格多样化（现代简约、高端奢华、创意互动、国潮新中式、复古怀旧等）
3. 空间类型多样化（中庭、入口、橱窗、快闪店、走廊、广场、电梯厅等）
4. 预算等级合理（low/medium/high/premium）
5. 摘要详细，包含设计亮点和实施要点

请输出JSON格式：
{{
  "title": "案例标题",
  "theme": "主题",
  "style": "风格",
  "space_type": "空间类型",
  "budget_level": "预算等级",
  "summary": "详细的案例摘要（100-200字）",
  "source_url": ""
}}
"""
            
            try:
                response = await llm_client.complete("你是一位资深美陈设计师，擅长创作高质量的设计案例", prompt, json_mode=True)
                result = json.loads(response)
                
                db.add(DesignCase(
                    title=result["title"],
                    theme=result["theme"],
                    style=result["style"],
                    space_type=result["space_type"],
                    budget_level=result["budget_level"],
                    summary=result["summary"],
                    source_url=result.get("source_url", "")
                ))
                db.commit()
                print(f"生成案例 {i+1}: {result['title']}")
                
            except Exception as e:
                print(f"生成失败: {e}")
                db.rollback()
    finally:
        db.close()


async def main():
    print("=== 第一步：补全现有案例字段 ===")
    await enrich_existing_cases()
    
    print("\n=== 第二步：生成高质量案例 ===")
    await generate_high_quality_cases(20)
    
    print("\n=== 完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
