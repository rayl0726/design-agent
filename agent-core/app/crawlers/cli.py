from __future__ import annotations

import logging
from pathlib import Path

import click

from app.crawlers.zcool import ZcoolCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@click.group()
@click.option(
    "--output-dir",
    default="/Users/liulei/private-work/design-data",
    help="本地数据归档根目录",
)
@click.option("--delay-min", default=2.0, help="最小延迟（秒）")
@click.option("--delay-max", default=5.0, help="最大延迟（秒）")
@click.pass_context
def cli(ctx: click.Context, output_dir: str, delay_min: float, delay_max: float) -> None:
    ctx.ensure_object(dict)
    ctx.obj["output_dir"] = output_dir
    ctx.obj["delay_min"] = delay_min
    ctx.obj["delay_max"] = delay_max


@cli.command()
@click.option("--keywords", required=True, help="关键词，逗号分隔")
@click.option("--limit", default=100, help="最大爬取数量")
@click.pass_context
def zcool(ctx: click.Context, keywords: str, limit: int) -> None:
    crawler = ZcoolCrawler(
        name="zcool",
        output_dir=ctx.obj["output_dir"],
        delay_min=ctx.obj["delay_min"],
        delay_max=ctx.obj["delay_max"],
    )
    kw_list = [k.strip() for k in keywords.split(",")]
    click.echo(f"搜索关键词: {kw_list}")
    urls = crawler.search(kw_list, limit=limit)
    click.echo(f"找到 {len(urls)} 个作品，开始爬取...")
    crawler.run(urls)
    crawler.close()
    click.echo("爬取完成。")


if __name__ == "__main__":
    cli()
