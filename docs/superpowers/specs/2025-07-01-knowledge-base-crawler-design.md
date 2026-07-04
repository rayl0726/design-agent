# 知识库爬虫设计方案

## 1. 目标

为美陈设计 Agent 的 RAG 知识库填充真实、高质量的数据，目标 1 万条：
- **设计案例** ~6000 条（商场公众号文章 + 站酷/Behance 作品）
- **参考图集** ~2000 条（Pinterest/小红书公开收藏）
- **材料价格** ~2000 条（1688 商品数据）

## 2. 数据来源与获取方式

| 类型 | 来源 | 技术方案 | 预估数量 |
|------|------|---------|---------|
| 商场案例 | 搜狗微信搜索「商场美陈」「中庭吊饰」等关键词 | Playwright 模拟搜索 → 点击进入文章页 → 提取标题、正文、图片 | 3000-4000 |
| 设计作品 | 站酷搜索「美陈」「商业空间」 | requests + BeautifulSoup 抓列表页 + 详情页 | 2000-3000 |
| 参考图集 | Pinterest / 小红书（公开收藏页/分享链接） | 先人工导出分享链接列表，再用 Playwright 抓图片+描述 | 2000 |
| 材料价格 | 1688 搜索「美陈道具」「亚克力」「发光字」等 | Playwright 抓搜索列表 → 进详情页取规格、价格区间 | 1000-2000 |

## 3. 反爬策略（核心要求）

为避免被封 IP 或账号，采用以下多层防护：

### 3.1 请求频率控制
- **随机延迟**：每次请求间隔 2-5 秒（正态分布随机）
- **单源并发限制**：同一域名最多 2 个并发请求
- **时段分散**：支持配置爬取时段（如 09:00-18:00），模拟真人作息

### 3.2 请求指纹伪装
- **User-Agent 轮换**：维护 10-20 个常见浏览器 UA，每次请求随机切换
- **Accept-Language / Referer**：设置合理的请求头，模拟真实浏览器
- **Cookie 管理**：Playwright 自动处理 Cookie，requests 使用 Session 保持会话

### 3.3 行为模拟（Playwright 专用）
- **鼠标移动**：在页面加载后模拟随机鼠标移动和滚动
- **页面停留**：详情页停留 3-8 秒后再提取数据
- **点击路径**：模拟从搜索页 → 列表页 → 详情页的完整点击路径，而非直接打开详情页 URL

### 3.4 失败与封禁检测
- **HTTP 状态码检测**：遇到 403/429/503 时立即暂停该源 5 分钟
- **验证码检测**：检测到验证码页面（关键词如 "captcha", "验证"）时暂停并告警
- **内容异常检测**：返回内容明显异常（如空页面、仅包含 "访问频繁"）时视为被封
- **指数退避重试**：失败后等待 1s → 2s → 4s → 8s，最多重试 3 次，仍失败则标记为废弃 URL

### 3.5 数据去重与增量更新
- **URL MD5 去重**：已爬取的 URL 存入 SQLite `crawled_urls` 表，重复 URL 直接跳过
- **增量模式**：每次运行只爬取新出现的 URL，支持 `--since-days 7` 参数只爬最近 N 天的新内容
- **断点续爬**：每爬 50 条自动保存进度（cursor/offset），中断后从断点继续

## 4. 技术架构

```
python-ai/app/crawlers/
├── __init__.py
├── base.py              # 基础爬虫类（反爬逻辑、重试、延迟）
├── wechat_article.py    # 公众号文章爬虫
├── zcool.py             # 站酷作品爬虫
├── pinterest.py         # Pinterest/小红书图集爬虫
├── alibaba_1688.py      # 1688 材料价格爬虫
├── cli.py               # 统一 CLI 入口
└── utils.py             # URL 去重、进度保存、UA 轮换等工具
```

### 4.1 基础爬虫类 (`BaseCrawler`)
所有具体爬虫继承此类，内置：
- `self.delay_range = (2, 5)` — 延迟范围
- `self.max_concurrent = 2` — 并发限制
- `self.retry_times = 3` — 重试次数
- `self.session` — 带 UA 轮换的 requests Session
- `self.playwright` — Playwright 浏览器实例（按需启动）
- 方法：`fetch(url)`, `parse(html)`, `save(item)`, `run()`

### 4.2 Playwright 与 requests 切换策略
- 静态 HTML 页面（站酷列表页）→ `requests`（轻量、快）
- JS 渲染页面（公众号文章、1688 详情）→ `Playwright`（真实浏览器）
- 图片密集型页面（Pinterest）→ `Playwright` + 拦截图片请求

## 5. 存储方案

已就绪，沿用现有架构：

- **SQLite** (`data/sqlite/meichen.db`)：
  - `design_cases` 表 — 案例元数据（标题、空间类型、预算、风格、摘要、图片路径 JSON）
  - `material_prices` 表 — 材料价格（名称、规格、单位、价格区间、供应商）
  - `crawled_urls` 表 — 已爬 URL 去重 + 爬取时间戳

- **Milvus** (`knowledge_base` collection)：
  - 案例摘要的 `bge-m3` Embedding（1024 维）
  - 图片描述文本的 Embedding（可选）

- **本地文件系统** (`data/images/`, `data/crawler_downloads/`)：
  - 原始图片按来源分类存放
  - 爬虫进度文件（JSON）

## 6. 数据质量控制

1. **字段校验**：LLM 提取后检查必须字段（案例至少需有标题+空间类型+摘要；材料至少需有名称+价格）
2. **缺失率过滤**：关键字段缺失率 > 30% 的数据丢弃
3. **价格清洗**：1688 价格统一转换为元/单位，去除异常值（如 0 元或 >100 万元）
4. **人工抽检**：每批次 100 条随机抽 10 条人工复核，合格率 < 70% 时暂停调优 Prompt

## 7. CLI 使用方式

```bash
# 爬取公众号文章（商场美陈关键词）
python -m app.crawlers.cli wechat --keywords "商场美陈,中庭吊饰,入口装置" --limit 500

# 爬取站酷作品
python -m app.crawlers.cli zcool --keywords "美陈,商业空间,快闪店" --limit 300

# 爬取 1688 材料价格
python -m app.crawlers.cli 1688 --keywords "美陈道具,亚克力,发光字" --limit 500

# 从文件批量导入 Pinterest/小红书链接
python -m app.crawlers.cli pinterest --url-file data/pinterest_links.txt

# 通用参数
--delay-min 2          # 最小延迟（秒）
--delay-max 5          # 最大延迟（秒）
--since-days 7         # 只爬最近 7 天的新内容
--output-dir data/crawler_downloads/  # 下载目录
```

## 8. 实施计划

1. **Phase 1**：实现 `BaseCrawler` 基础类和反爬工具（UA 轮换、延迟、重试、去重）
2. **Phase 2**：实现站酷爬虫（静态页面，最简单，先验证链路）
3. **Phase 3**：实现公众号文章爬虫（Playwright，最复杂，需要搜索→列表→详情链路）
4. **Phase 4**：实现 1688 材料爬虫（Playwright，价格清洗逻辑）
5. **Phase 5**：实现 Pinterest/小红书爬虫（图片批量下载）
6. **Phase 6**：跑通首批 100 条数据，人工抽检质量，调优 Prompt

## 9. 风险与规避

| 风险 | 规避措施 |
|------|---------|
| 源站封 IP | 严格限速 2-5 秒/请求，单源 2 并发，检测 403/429 自动暂停 |
| 页面结构变化 | 使用相对稳定的 CSS 选择器，失败时记录日志便于快速修复 |
| 数据质量差 | LLM 提取后字段校验 + 缺失率过滤 + 人工抽检 |
| 法律合规 | 只爬公开可访问内容，不爬登录后内容，数据仅用于内部 RAG 不对外商用 |
