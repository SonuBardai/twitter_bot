from datetime import datetime
from firecrawl import FirecrawlApp
import click
import os

from utils import save_to_cache


def producthunt(date: datetime):
    api_url, api_key = os.getenv("FIRECRAWL_API_URL"), None
    if not api_url:
        click.echo("❌ FIRECRAWL_API_URL environment variable is not set")
        api_url = "https://api.firecrawl.dev"
        api_key = os.getenv("FIRECRAWL_API_KEY")
    click.echo(f"Using API URL: {api_url}")
    app = FirecrawlApp(
        api_key=api_key,
        api_url=api_url,
    )

    year, month, day = date.year, date.month, date.day
    url = f"https://www.producthunt.com/leaderboard/daily/{year}/{month}/{day}"
    scrape_result = app.scrape_url(url, formats=["markdown", "html"])

    save_to_cache(scrape_result.markdown, "producthunt_cache", "md")

    click.echo("✅ Product hunt scrape saved to producthunt_cache")
