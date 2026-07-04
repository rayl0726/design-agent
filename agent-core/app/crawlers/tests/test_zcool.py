from __future__ import annotations

from app.crawlers.zcool import ZcoolCrawler


SAMPLE_DETAIL_HTML = """
<html>
<head><title>夏日海洋美陈设计 - 站酷 (ZCOOL)</title></head>
<body>
<div class="work-title"><h1>夏日海洋美陈设计</h1></div>
<div class="work-author"><a>设计师小王</a></div>
<div class="work-desc"><p>为某商场中庭设计的夏日海洋主题吊饰方案，预算约15万。</p></div>
<img src="https://img.zcool.cn/1.jpg" class="work-img"/>
<img src="https://img.zcool.cn/2.jpg" class="work-img"/>
</body>
</html>
"""


def test_zcool_parse_detail():
    c = ZcoolCrawler(name="zcool", output_dir="/tmp")
    extracted = c.parse(SAMPLE_DETAIL_HTML)
    assert extracted["title"] == "夏日海洋美陈设计"
    assert "15万" in extracted["description"]
    assert len(extracted["images"]) == 2
