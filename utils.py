import os
import json
import datetime
from typing import Dict, Any
import click


def get_next_cache_filename(dir_name: str) -> str:
    """Generate the next available cache filename with incrementing count."""
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_name)
    os.makedirs(cache_dir, exist_ok=True)

    base_name = datetime.datetime.now().strftime("%Y-%m-%dT%H")
    count = 0

    while True:
        cache_file = os.path.join(cache_dir, f"{base_name}.{count}.json")
        if not os.path.exists(cache_file):
            return cache_file
        count += 1


def save_to_cache(data: Dict[str, Any], dir_name: str) -> str:
    """Save ingested data to a timestamped JSON file in the directory."""
    try:
        cache_file = get_next_cache_filename(dir_name)

        # Write data to file
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return cache_file
    except Exception as e:
        click.echo(f"⚠️ Error saving to cache: {str(e)}")
        return ""
