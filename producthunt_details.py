from datetime import datetime
import json
import os
import click
from producthunt_leads import leads_transform

from firecrawl_utils import scrape_with_firecrawl
from producthunt_tweets import tweets_transform
from utils import get_latest_cache_file


def ingest(date: datetime):
    """Ingest product details and makers information from Product Hunt."""
    # Get the cached product data
    cache_file = get_latest_cache_file("producthunt_data_cache", "json")
    with open(cache_file, "r", encoding="utf-8") as f:
        cached_data = json.load(f)

    if not cached_data:
        click.echo("❌ No cached data found")
        raise Exception("No cached data found")

    products = cached_data.get("products", [])
    if not products:
        click.echo("❌ No products found in cache")
        raise Exception("No products found in cache")

    # Create a directory for product details if it doesn't exist
    os.makedirs("producthunt_product_cache", exist_ok=True)

    # Process each product
    for product in products:
        if not product.get("url"):
            continue

        product_url = product["url"]
        makers_url = f"{product_url}/makers"

        # Scrape product details
        product_details = scrape_with_firecrawl(product_url)
        if not product_details:
            click.echo(f"⚠️  Failed to scrape product: {product_url}")
            raise Exception(f"Failed to scrape product: {product_url}")

        # Scrape makers details
        makers_details = scrape_with_firecrawl(makers_url)
        if not makers_details:
            click.echo(f"⚠️  Failed to scrape makers for: {product_url}")
            raise Exception(f"Failed to scrape makers for: {product_url}")

        # Generate a safe base filename from product name or URL
        product_name = product.get("name", "product").replace(" ", "_").lower()
        date_prefix = date.strftime("%Y-%m-%d")
        base_filename = f"{date_prefix}_{product_name}"

        # Create and save product details file
        details_filename = f"{base_filename}_details.md"
        details_filepath = os.path.join("producthunt_product_cache", details_filename)
        with open(details_filepath, "w", encoding="utf-8") as f:
            f.write(f"# Product Details\n{product_details}")

        # Create and save makers details file
        makers_filename = f"{base_filename}_makers.md"
        makers_filepath = os.path.join("producthunt_product_cache", makers_filename)
        with open(makers_filepath, "w", encoding="utf-8") as f:
            f.write(f"# Team/Makers\n{makers_details}")

        click.echo(f"✅ Saved details for: {product.get('name', 'Unknown product')} (2 files)")

    click.echo("\n🎉 Finished processing all products")


def get_product_details(date: datetime):
    ingest(date)
    tweets_transform(date)
    leads_transform(date)
