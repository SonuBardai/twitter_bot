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


def get_latest_cache_file(dir_name: str) -> str:
    """
    Get the most recent cache file from the specified directory.
    
    Args:
        dir_name: Name of the directory to search for cache files
        
    Returns:
        str: Path to the most recent cache file
        
    Raises:
        FileNotFoundError: If no cache files are found in the directory
    """
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_name)
    
    if not os.path.exists(cache_dir):
        raise FileNotFoundError(f"Cache directory not found: {cache_dir}")
    
    # Get all JSON files in the directory
    cache_files = [
        os.path.join(cache_dir, f) 
        for f in os.listdir(cache_dir) 
        if f.endswith('.json')
    ]
    
    if not cache_files:
        raise FileNotFoundError(f"No cache files found in {cache_dir}")
    
    # Sort by modification time, newest first
    latest_file = max(cache_files, key=os.path.getmtime)
    return latest_file


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
