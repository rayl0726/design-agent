from datetime import datetime
from pathlib import Path

from app.core.config import settings


class HtmlGenerator:
    TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - 设计方案</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: #f5f5f7; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 36px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 16px; }}
        .header .meta {{ margin-top: 15px; font-size: 14px; opacity: 0.8; }}
        .section {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
        .section-title {{ font-size: 22px; color: #1a1a1a; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #667eea; }}
        .story-title {{ font-size: 20px; color: #333; margin-bottom: 15px; }}
        .story-text {{ font-size: 15px; line-height: 2; color: #555; margin-bottom: 15px; }}
        .concept-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 15px; }}
        .concept-label {{ font-weight: 600; color: #667eea; margin-bottom: 8px; }}
        .keywords {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }}
        .keyword {{ background: #e8f4fd; color: #3b82f6; padding: 6px 14px; border-radius: 20px; font-size: 13px; }}
        .atmosphere-box {{ background: #fef3c7; padding: 20px; border-radius: 8px; }}
        .moodboard-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }}
        .mood-image {{ width: 100%; height: 200px; object-fit: cover; border-radius: 8px; }}
        .color-palette {{ display: flex; gap: 15px; flex-wrap: wrap; }}
        .color-item {{ width: 80px; height: 80px; border-radius: 8px; display: flex; align-items: flex-end; padding: 8px; color: white; font-size: 12px; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }}
        .render-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 16px; }}
        .render-image {{ width: 100%; height: 250px; object-fit: cover; border-radius: 8px; }}
        .budget-table {{ width: 100%; border-collapse: collapse; }}
        .budget-table th, .budget-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        .budget-table th {{ background: #f8f9fa; font-weight: 600; }}
        .total-row {{ background: #e8f4fd; font-weight: 600; }}
        .footer {{ text-align: center; padding: 30px; color: #999; font-size: 14px; }}
        .level-badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .level-l1 {{ background: #dbeafe; color: #1d4ed8; }}
        .level-l2 {{ background: #dcfce7; color: #166534; }}
        .level-l3 {{ background: #fef3c7; color: #92400e; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="level-badge level-{current_level}">{current_level} 方案</div>
            <h1>{project_name}</h1>
            <p>{description}</p>
            <div class="meta">生成时间: {generated_at}</div>
        </div>

        <!-- L1 概念方向 -->
        {l1_section}

        <!-- L2 视觉方案 -->
        {l2_section}

        <!-- L3 可落地方案 -->
        {l3_section}

        <div class="footer">
            <p>美陈设计方案 - 由 AI 自动生成</p>
        </div>
    </div>
</body>
</html>"""

    L1_TEMPLATE = """
        <div class="section">
            <h2 class="section-title">L1 概念方向</h2>
            
            <div class="story-title">{story_title}</div>
            <div class="story-text">{story_content}</div>
            
            <div class="concept-box">
                <div class="concept-label">核心概念</div>
                <div class="story-text">{concept}</div>
            </div>
            
            <div class="concept-box">
                <div class="concept-label">场景叙事</div>
                <div class="story-text">{narrative}</div>
            </div>
            
            <div class="keywords">
                {keywords_html}
            </div>
            
            <div style="margin-top: 30px;">
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">氛围描述</h3>
                <div class="atmosphere-box">
                    <div class="story-text">{atmosphere_paragraph}</div>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">视觉关键词</h3>
                <div class="keywords">
                    {visual_keywords_html}
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">参考情绪板</h3>
                <div class="moodboard-grid">
                    {moodboard_images_html}
                </div>
            </div>
        </div>
    """

    L2_TEMPLATE = """
        <div class="section">
            <h2 class="section-title">L2 视觉方案</h2>
            
            <div style="margin-bottom: 30px;">
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">AI 概念效果图</h3>
                <div class="render-grid">
                    {concept_images_html}
                </div>
            </div>
            
            <div>
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">色彩材质板</h3>
                <img src="{color_material_board}" style="max-width: 600px; border-radius: 8px;" />
            </div>
        </div>
    """

    L3_TEMPLATE = """
        <div class="section">
            <h2 class="section-title">L3 可落地方案</h2>
            
            <div style="margin-bottom: 30px;">
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">点位平面布置图</h3>
                {layout_image_html}
            </div>
            
            <div style="margin-bottom: 30px;">
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">物料清单</h3>
                {material_list_html}
            </div>
            
            <div>
                <h3 style="font-size: 18px; margin-bottom: 15px; color: #333;">预算表</h3>
                <table class="budget-table">
                    <tr>
                        <th>项目</th>
                        <th>金额 (CNY)</th>
                    </tr>
                    <tr><td>材料费用</td><td>¥{material_cost}</td></tr>
                    <tr><td>制作费用</td><td>¥{production_cost}</td></tr>
                    <tr><td>安装费用</td><td>¥{installation_cost}</td></tr>
                    <tr><td>设计费用</td><td>¥{design_fee}</td></tr>
                    <tr class="total-row"><td>总预算</td><td>¥{total}</td></tr>
                </table>
            </div>
        </div>
    """

    @staticmethod
    def generate(project_name: str, description: str, current_level: str, 
                 l1_data: dict = None, l2_data: dict = None, l3_data: dict = None) -> str:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        l1_section = HtmlGenerator._generate_l1_section(l1_data)
        l2_section = HtmlGenerator._generate_l2_section(l2_data)
        l3_section = HtmlGenerator._generate_l3_section(l3_data)
        
        html = HtmlGenerator.TEMPLATE.format(
            project_name=project_name,
            description=description,
            current_level=current_level,
            generated_at=generated_at,
            l1_section=l1_section,
            l2_section=l2_section,
            l3_section=l3_section,
        )
        
        return html

    @staticmethod
    def _generate_l1_section(l1_data: dict) -> str:
        if not l1_data:
            return '<div class="section"><h2 class="section-title">L1 概念方向</h2><p>尚未生成</p></div>'
        
        story = l1_data.get('story', {})
        atmosphere = l1_data.get('atmosphere', {})
        moodboard = l1_data.get('moodboard', {})
        
        keywords_html = ''.join(f'<span class="keyword">{kw}</span>' for kw in story.get('keywords', []))
        visual_keywords_html = ''.join(f'<span class="keyword">{kw}</span>' for kw in atmosphere.get('visual', []))
        
        images_html = ''
        for img_path in moodboard.get('generated_images', []):
            images_html += f'<img src="{img_path}" class="mood-image" />'
        
        return HtmlGenerator.L1_TEMPLATE.format(
            story_title=story.get('title', ''),
            story_content=story.get('story', ''),
            concept=story.get('concept', ''),
            narrative=story.get('narrative', ''),
            keywords_html=keywords_html,
            atmosphere_paragraph=atmosphere.get('paragraph', ''),
            visual_keywords_html=visual_keywords_html,
            moodboard_images_html=images_html,
        )

    @staticmethod
    def _generate_l2_section(l2_data: dict) -> str:
        if not l2_data:
            return '<div class="section"><h2 class="section-title">L2 视觉方案</h2><p>尚未生成</p></div>'
        
        concept_images_html = ''
        for img in l2_data.get('concept_images', []):
            concept_images_html += f'<img src="{img.get("path", "")}" class="render-image" />'
        
        color_material_board = l2_data.get('color_material_board', '')
        
        return HtmlGenerator.L2_TEMPLATE.format(
            concept_images_html=concept_images_html,
            color_material_board=color_material_board,
        )

    @staticmethod
    def _generate_l3_section(l3_data: dict) -> str:
        if not l3_data:
            return '<div class="section"><h2 class="section-title">L3 可落地方案</h2><p>尚未生成</p></div>'
        
        layout_annotation = l3_data.get('layout_annotation', {})
        svg_content = layout_annotation.get('layout_svg', '')
        
        layout_image_html = ''
        if svg_content:
            layout_image_html = f'<div style="background: #f5f5f7; padding: 20px; border-radius: 8px;">{svg_content}</div>'
        else:
            layout_image_html = '<p>暂无布局图</p>'
        
        material_list_html = '<table class="budget-table"><tr><th>材料名称</th><th>规格</th><th>数量</th><th>单价</th><th>小计</th></tr>'
        for mat in l3_data.get('material_list', []):
            material_list_html += f'<tr><td>{mat.get("name", "")}</td><td>{mat.get("spec", "")}</td><td>{mat.get("quantity", "")}</td><td>{mat.get("unit_price", "")}</td><td>{mat.get("total_price", "")}</td></tr>'
        material_list_html += '</table>'
        
        budget = l3_data.get('budget', {})
        
        return HtmlGenerator.L3_TEMPLATE.format(
            layout_image_html=layout_image_html,
            material_list_html=material_list_html,
            material_cost=budget.get('material_cost', 0),
            production_cost=budget.get('production_cost', 0),
            installation_cost=budget.get('installation_cost', 0),
            design_fee=budget.get('design_fee', 0),
            total=budget.get('total', 0),
        )

    @staticmethod
    def save_html(project_id: str, html_content: str) -> str:
        output_dir = Path(settings.html_cache_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        full_path = output_dir / f"{project_id}.html"
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return f"/data/html/{project_id}.html"
