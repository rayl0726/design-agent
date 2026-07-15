import pytest
from app.tools.search_clients import (
    BingSearchClient,
    BaiduSearchClient,
    deduplicate_results,
    is_ad_result,
    _normalize_url,
    _jaccard_similarity,
)


def test_normalize_url_strips_scheme_and_www():
    assert _normalize_url("https://www.example.com/path/?x=1") == "example.com/path"
    assert _normalize_url("http://example.com/path") == "example.com/path"


def test_jaccard_similarity():
    assert _jaccard_similarity("北京天气", "北京今天天气") > 0.3
    assert _jaccard_similarity("完全无关", "另一个标题") < 0.2


def test_deduplicate_removes_same_url():
    results = [
        {"title": "A", "link": "https://www.example.com/a", "snippet": "s", "source": "bing"},
        {"title": "A", "link": "http://example.com/a", "snippet": "s2", "source": "baidu"},
    ]
    out = deduplicate_results(results)
    assert len(out) == 1


def test_deduplicate_removes_similar_titles():
    results = [
        {"title": "2026 北京车展最新动态", "link": "https://a.com/1", "snippet": "s", "source": "bing"},
        {"title": "2026 北京车展最新动态", "link": "https://b.com/2", "snippet": "s", "source": "baidu"},
    ]
    out = deduplicate_results(results)
    assert len(out) == 1


def test_is_ad_result_detects_ad_markers():
    assert is_ad_result({"title": "广告： best product", "link": "", "snippet": ""}) is True
    assert is_ad_result({"title": "正常新闻", "link": "", "snippet": ""}) is False
    assert is_ad_result({"title": "", "link": "https://e.baidu.com/xxx", "snippet": ""}) is True


def test_baidu_client_filters_ad_html():
    html = """
    <html>
      <div class="result" data-tuiguang="1">
        <h3><a href="https://ad.com">广告商品</a></h3>
        <div class="content-right">推广文案</div>
      </div>
      <div class="result ec_xxx">
        <h3><a href="https://ad2.com">竞价商品</a></h3>
        <div class="content-right">竞价文案</div>
      </div>
      <div class="result">
        <h3><a href="https://news.com/1">正常新闻标题</a></h3>
        <div class="content-right_8ZsVx">正常摘要</div>
      </div>
    </html>
    """
    client = BaiduSearchClient()
    results = client._parse(html)
    assert len(results) == 1
    assert results[0]["title"] == "正常新闻标题"
    assert results[0]["link"] == "https://news.com/1"


def test_baidu_client_does_not_filter_rec_result():
    html = """
    <html>
      <div class="result rec_result">
        <h3><a href="https://news.com/2">推荐结果标题</a></h3>
        <div class="content-right_8ZsVx">推荐结果摘要</div>
      </div>
    </html>
    """
    client = BaiduSearchClient()
    results = client._parse(html)
    assert len(results) == 1
    assert results[0]["title"] == "推荐结果标题"
    assert results[0]["link"] == "https://news.com/2"


def test_bing_client_parse_results():
    html = """
    <html>
      <li class="b_algo">
        <h2><a href="https://example.com">Example Title</a></h2>
        <div class="b_caption"><p>Example snippet</p></div>
      </li>
    </html>
    """
    client = BingSearchClient()
    results = client._parse(html)
    assert len(results) == 1
    assert results[0]["title"] == "Example Title"
    assert results[0]["link"] == "https://example.com"
    assert results[0]["snippet"] == "Example snippet"
