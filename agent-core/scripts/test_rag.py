import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.knowledge_base import knowledge_base


async def test_rag():
    print("=== RAG 检索测试 ===")
    
    queries = [
        ("春节 国潮新中式 中庭", "中庭", "high"),
        ("圣诞节 高端奢华 橱窗", "橱窗", "premium"),
        ("科技未来 现代简约", "中庭", None),
        ("夏日清凉 快闪店", "快闪店", "medium"),
        ("环保主题", None, None),
    ]
    
    for query, space_type, budget_level in queries:
        print(f"\n查询: {query}")
        print(f"空间类型: {space_type or '不限'}, 预算等级: {budget_level or '不限'}")
        
        results = await knowledge_base.semantic_search(
            query=query,
            space_type=space_type,
            budget_level=budget_level,
            top_k=3
        )
        
        print(f"找到 {len(results)} 条结果:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['title']}")
            print(f"     - 主题: {r['theme']}, 风格: {r['style']}")
            print(f"     - 空间: {r['space_type']}, 预算: {r['budget_level']}")
            print(f"     - 摘要: {r['summary'][:100]}...")


async def test_materials():
    print("\n=== 材料查询测试 ===")
    
    queries = ["亚克力", "LED", "金属"]
    
    for query in queries:
        print(f"\n查询材料: {query}")
        results = knowledge_base.structured_query(material_name=query, limit=3)
        
        print(f"找到 {len(results)} 条结果:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['name']} ({r['category']})")
            print(f"     - 规格: {r['spec']}")
            print(f"     - 价格: {r['price_low']}-{r['price_high']}元/{r['unit']}")


async def main():
    await test_rag()
    await test_materials()
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
