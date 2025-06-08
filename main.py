import os
import click
import asyncio
import json
import datetime
from typing import Dict, Any, Optional
from browser_use import Agent, BrowserSession, Controller
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

# Load environment variables
load_dotenv()


@click.group()
def cli():
    """A simple CLI tool for Twitter operations."""
    pass


headless = os.getenv("HEADLESS", True) in ["true", "True", "1", "t", "T", True]
browser_session_dict = {
    "headless": headless,
}
browser_session = BrowserSession(
    **browser_session_dict,
)


class Article(BaseModel):
    title: str
    full_content: str
    url: str
    author: Optional[str] = None


async def fetch_tech_news() -> Dict[str, Any]:
    """Fetch tech news from daily.dev using browser automation."""
    # Initialize the language model
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

    controller = Controller(output_model=Article)

    # Create agent with explicit navigation steps
    agent = Agent(
        task="""
        1. Go to https://www.developer-tech.com/categories/developer-ai/
        2. Click on the first article
        4. Read the contents of the article
        5. For that article, extract the contents of the article in the following format and return only JSON type result in the following format. Do not return anything extra. Do not return placeholder data, only return real data.

        class Article(BaseModel):
            title: str
            full_content: str
            url: str
            author: Optional[str] = None

        """,
        llm=llm,
        browser_session=browser_session,
        controller=controller,
        use_vision=False,  # don't take screenshots
    )

    try:
        result = await agent.run()
        raw_dict = result.model_dump()
        save_to_cache(raw_dict, "raw_cache")
        final_result = json.loads(result.final_result())
        return final_result
    except Exception as e:
        click.echo(f"❌ Error fetching tech news: {str(e)}")
        return {"raw_content": "", "topics": [], "links": []}


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


def ingest() -> Dict[str, Any]:
    """Step 1: Ingest data from daily.dev and cache the results."""
    click.echo("📥 Fetching tech news from daily.dev...")

    try:
        # Run the async function
        agent_result = asyncio.run(fetch_tech_news())

        # Save to cache
        cache_file = save_to_cache(agent_result, "ingest_cache")
        click.echo(f"✅ Successfully fetched and cached tech news to {cache_file}")

    except Exception as e:
        error_msg = str(e)
        click.echo(f"❌ Error in ingest: {error_msg}")
        raise


def transform() -> Dict[str, Any]:
    """Step 2: Transform data."""
    click.echo("🔄 Transforming data...")


def post() -> Dict[str, Any]:
    """Step 3: Post data."""
    click.echo("🚀 Posting data...")


class PipelineError(Exception):
    """Custom exception for pipeline failures."""

    pass


@click.command()
def tweet():
    """Simple tweet command with three steps."""
    try:
        ingest()
        transform()
        post()
    except Exception as e:
        click.echo(f"❌ Unexpected error in tweet pipeline: {str(e)}", err=True)
        raise


cli.add_command(tweet)

if __name__ == "__main__":
    cli()
