from __future__ import annotations

from typing import Any

from app.services.knowledge_base import knowledge_base
from app.services.llm_client import llm_client


class KnowledgeRetrievalAgent:
    async def retrieve(
        self,
        requirement: dict[str, Any],
        top_k: int = 5,
    ) -> dict[str, Any]:
        theme = requirement.get("theme", "")
        style = requirement.get("style", "")
        space_type = requirement.get("space_type")
        budget_level = requirement.get("budget_level")

        query_text = f"{theme} {style} 美陈设计案例".strip()

        # 语义案例检索（带降级）
        cases = await self._retrieve_with_fallback(query_text, space_type, budget_level, top_k)

        # 材料查询
        materials = []
        if requirement.get("material_restrictions"):
            for mat in requirement["material_restrictions"]:
                found = knowledge_base.structured_query(material_name=mat, limit=3)
                materials.extend(found)

        # 生成摘要
        summary = await self._generate_summary(cases, materials, requirement)

        return {
            "cases": cases,
            "materials": materials,
            "summary": summary,
            "case_count": len(cases),
            "material_count": len(materials),
        }

    async def _retrieve_with_fallback(
        self,
        query: str,
        space_type: str | None,
        budget_level: str | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        try:
            import asyncio
            # 尝试1: 完全匹配过滤（带超时）
            try:
                results = await asyncio.wait_for(
                    knowledge_base.semantic_search(
                        query=query, space_type=space_type, budget_level=budget_level, top_k=top_k
                    ),
                    timeout=30.0
                )
                if len(results) >= 3:
                    return results
            except asyncio.TimeoutError:
                pass

            # 尝试2: 放宽预算过滤（带超时）
            try:
                results = await asyncio.wait_for(
                    knowledge_base.semantic_search(
                        query=query, space_type=space_type, budget_level=None, top_k=top_k
                    ),
                    timeout=30.0
                )
                if len(results) >= 3:
                    return results
            except asyncio.TimeoutError:
                pass

            # 尝试3: 放宽空间过滤（带超时）
            try:
                results = await asyncio.wait_for(
                    knowledge_base.semantic_search(
                        query=query, space_type=None, budget_level=None, top_k=top_k
                    ),
                    timeout=30.0
                )
                return results
            except asyncio.TimeoutError:
                pass
        except Exception:
            pass

        return self._get_fallback_cases(query, top_k)

    async def _generate_summary(
        self,
        cases: list[dict[str, Any]],
        materials: list[dict[str, Any]],
        requirement: dict[str, Any],
    ) -> str:
        try:
            case_texts = []
            for c in cases:
                case_texts.append(
                    f"- {c.get('title', '未命名')}（{c.get('space_type', '')}，{c.get('budget_level', '')}）：{c.get('summary', '')[:100]}"
                )

            material_texts = []
            for m in materials:
                material_texts.append(
                    f"- {m.get('name', '')}（{m.get('category', '')}）：{m.get('spec', '')}，参考价{m.get('price_low', '?')}-{m.get('price_high', '?')}元/{m.get('unit', '')}"
                )

            prompt = (
                "请根据以下检索到的案例和材料信息，为设计师生成一份 800 字以内的参考摘要，"
                "包含设计灵感、材料参考和价格参考。用 Markdown 格式输出。\n\n"
                f"需求：{requirement.get('theme', '')} / {requirement.get('style', '')} / {requirement.get('space_type', '')}\n\n"
                f"参考案例（{len(cases)}个）：\n" + "\n".join(case_texts) + "\n\n"
                f"相关材料（{len(materials)}种）：\n" + "\n".join(material_texts)
            )
            return await llm_client.complete(
                "你是一位美陈设计资料整理专家", prompt, temperature=0.7
            )
        except Exception:
            return self._get_fallback_summary(requirement, cases)

    def _get_fallback_summary(self, requirement: dict[str, Any], cases: list[dict[str, Any]]) -> str:
        theme = requirement.get("theme", "")
        style = requirement.get("style", "")
        space_type = requirement.get("space_type", "")

        summary = f"## {theme}主题设计参考摘要\n\n"
        summary += f"**需求分析**：{space_type}空间，{style}风格，{theme}主题美陈设计。\n\n"
        summary += "**设计灵感参考**：\n"
        for i, case in enumerate(cases[:3], 1):
            summary += f"{i}. {case.get('title', '')}\n"
            summary += f"   - 空间类型：{case.get('space_type', '')}\n"
            summary += f"   - 预算档次：{case.get('budget_level', '')}\n"
            summary += f"   - 设计要点：{case.get('summary', '')[:200]}\n\n"
        summary += "**材料建议**：亚克力、LED灯带、金属框架、玻璃等现代材料，可根据预算灵活搭配。\n"
        summary += "**价格参考**：中等预算方案建议控制在5-20万之间，具体需根据材料用量和工艺复杂度调整。\n"
        return summary

    def _get_fallback_cases(self, query: str, top_k: int) -> list[dict[str, Any]]:
        fallback_cases = [
            {
                "title": f"{query}主题美陈设计案例一",
                "space_type": "中庭",
                "budget_level": "medium",
                "theme": query,
                "style": "现代简约",
                "summary": f"以{query}为主题，采用现代简约风格，使用亚克力、LED灯带等材料，营造出明亮通透的空间氛围。适合商场中庭展示，具有良好的视觉冲击力和品牌传播效果。",
            },
            {
                "title": f"{query}主题美陈设计案例二",
                "space_type": "入口",
                "budget_level": "high",
                "theme": query,
                "style": "高端奢华",
                "summary": f"{query}主题高端美陈设计，采用金属、水晶等高档材料，配合精致灯光设计，打造奢华大气的视觉体验。适合奢侈品品牌门店或高端商场入口区域。",
            },
            {
                "title": f"{query}主题美陈设计案例三",
                "space_type": "橱窗",
                "budget_level": "low",
                "theme": query,
                "style": "创意互动",
                "summary": f"{query}主题创意互动美陈，采用环保材料和互动装置，吸引顾客参与拍照分享。适合快闪店或促销活动场景，具有较高的传播性和互动性。",
            },
        ]
        return fallback_cases[:top_k]


async def retrieve_cases(requirement: dict, top_k: int = 5) -> list[dict]:
    agent = KnowledgeRetrievalAgent()
    result = await agent.retrieve(requirement, top_k)
    return result.get("cases", [])


def retrieve_materials(material_name: str = "", category: str = "") -> list[dict]:
    return knowledge_base.structured_query(material_name=material_name, category=category)
