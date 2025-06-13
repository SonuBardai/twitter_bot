from datetime import datetime
import click
from producthunt_list import get_products_list
from producthunt_details import get_product_details


def producthunt(date: datetime):
    get_products_list(date)
    get_product_details(date)

    click.echo("✅ Product hunt scrape saved to producthunt_cache")
