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


class Post(BaseModel):
    post_title: str
    post_full_content: str
    post_url: str
    author: Optional[str] = None


async def fetch_tech_news() -> Dict[str, Any]:
    """Fetch tech news from daily.dev using browser automation."""
    # Initialize the language model
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

    controller = Controller(output_model=Post)

    # Create agent with explicit navigation steps
    agent = Agent(
        task="""
        1. Go to https://www.developer-tech.com/categories/developer-ai/
        2. Find the most interesting post to tweet about
        3. Click on the post
        4. Read the contents of the post
        5. For that post, extract the contents in the following format and return only JSON type result in the following format. Do not return anything extra.

        class Post(BaseModel):
            post_title: str
            post_full_content: str
            post_url: str
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


def extract_news_data(agent_result) -> Dict[str, Any]:
    """Extract relevant data from the agent's result."""
    try:
        # Check if the agent result has the expected structure
        if hasattr(agent_result, "all_results") and agent_result.all_results:
            # Look through results in reverse to find the most recent extraction
            for result in reversed(agent_result.all_results):
                if hasattr(result, "extracted_content"):
                    content = result.extracted_content
                    if not content:
                        continue

                    # Debug output
                    click.echo(f"🔍 Extracted content: {content}")

                    # Handle different response formats
                    if isinstance(content, dict):
                        # Format 1: Direct format from the agent
                        if "raw_content" in content and "topics" in content and "link" in content:
                            return {"raw_content": content["raw_content"], "topics": content["topics"], "links": [content["link"]] if content["link"] else [], "source": "daily.dev"}
                        # Format 2: From the page extraction
                        elif "title" in content and "description" in content:
                            topics = content.get("topics", content.get("main_topics", []))
                            # Filter out any None values and ensure we have a list
                            topics = [t for t in topics if t is not None] if isinstance(topics, list) else []

                            return {
                                "raw_content": f"{content['title']} - {content['description']}",
                                "topics": topics,
                                "links": [content.get("link")] if content.get("link") else [],
                                "source": "daily.dev",
                            }
                        # Format 3: Most upvoted posts format
                        elif "most_upvoted_posts" in content:
                            posts = content["most_upvoted_posts"]
                            if posts and len(posts) > 0:
                                most_upvoted = posts[0] if isinstance(posts, list) else posts
                                return {
                                    "raw_content": most_upvoted.get("title", ""),
                                    "topics": ["tech-news"],
                                    "links": [f"https://app.daily.dev{most_upvoted.get('link', '')}" if most_upvoted.get("link") else ""],
                                    "source": "daily.dev",
                                }

        click.echo("⚠️ No valid post data found in agent results")
        return {"raw_content": "", "topics": [], "links": [], "source": "daily.dev"}
    except Exception as e:
        click.echo(f"⚠️ Error extracting news data: {str(e)}")
        return {"raw_content": "", "topics": [], "links": [], "source": "daily.dev"}


def ingest() -> Dict[str, Any]:
    """Step 1: Ingest data from daily.dev and cache the results."""
    click.echo("📥 Fetching tech news from daily.dev...")

    try:
        # Run the async function
        agent_result = asyncio.run(fetch_tech_news())

        # Save to cache
        cache_file = save_to_cache(agent_result, "ingest_cache")
        click.echo(f"✅ Successfully fetched and cached tech news to {cache_file}")

        return {"status": "success", "data": agent_result, "source": "daily.dev", "cache_file": cache_file}
    except Exception as e:
        error_msg = str(e)
        click.echo(f"❌ Error in ingest: {error_msg}")
        return {"status": "error", "error": error_msg, "data": None}


def transform(data: Dict[str, Any]) -> Dict[str, Any]:
    """Step 2: Transform data."""
    click.echo("🔄 Transforming data...")
    return {**data, "status": "transformed"}


def post(data: Dict[str, Any]) -> Dict[str, Any]:
    """Step 3: Post data."""
    click.echo("🚀 Posting data...")
    return {**data, "status": "posted"}


class PipelineError(Exception):
    """Custom exception for pipeline failures."""

    pass


@click.command()
def tweet():
    """Simple tweet command with three steps."""
    try:
        # Step 1: Ingest
        data = ingest()
        if data.get("status") == "error":
            raise PipelineError(f"❌ Ingestion failed: {data.get('error', 'Unknown error')}")

        # Step 2: Transform
        transformed_data = transform(data)
        if transformed_data.get("status") == "error" or "error" in transformed_data:
            raise PipelineError(f"❌ Transformation failed: {transformed_data.get('error', 'Unknown error')}")

        # Step 3: Post
        result = post(transformed_data)
        if result.get("status") == "error" or "error" in result:
            raise PipelineError(f"❌ Posting failed: {result.get('error', 'Unknown error')}")

        click.echo(f"✅ Success: {result}")
        return result

    except PipelineError as e:
        click.echo(str(e), err=True)
        raise
    except Exception as e:
        click.echo(f"❌ Unexpected error in tweet pipeline: {str(e)}", err=True)
        raise


@click.command()
@click.argument("tweet_id", type=str)
@click.argument("message", type=str)
@click.option("--image", "-i", type=click.Path(exists=True), help="Path to an image to include in the comment")
def comment(tweet_id, message, image):
    """Post a comment on a tweet."""
    click.echo(f"Commenting on tweet {tweet_id}: {message}")
    if image:
        click.echo(f"Including image: {image}")
    # Add your Twitter API integration here


# Register commands with the CLI group
cli.add_command(tweet)
cli.add_command(comment)

if __name__ == "__main__":
    cli()
