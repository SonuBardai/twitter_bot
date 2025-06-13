"""Utility functions for interacting with Firecrawl API."""

import os
import time
from typing import Optional

import click
from firecrawl import FirecrawlApp


def scrape_with_firecrawl(url: str, wait_time: int = 2) -> Optional[str]:
    """
    Scrape a URL using Firecrawl and return markdown content.

    Args:
        url: The URL to scrape

    Returns:
        str: The scraped markdown content, or None if an error occurred
    """
    api_url, api_key = os.getenv("FIRECRAWL_API_URL"), None
    if not api_url:
        click.echo("❌ FIRECRAWL_API_URL environment variable is not set")
        api_url = "https://api.firecrawl.dev"
        api_key = os.getenv("FIRECRAWL_API_KEY")

    click.echo(f"Scraping URL: {url}")
    app = FirecrawlApp(api_key=api_key, api_url=api_url)

    try:
        scrape_result = app.scrape_url(url, formats=["markdown", "html"])
        time.sleep(wait_time)
        return scrape_result.markdown
    except Exception as e:
        click.echo(f"❌ Error scraping {url}: {str(e)}")
        return None
