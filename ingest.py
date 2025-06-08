from typing import Dict, Any
import json
import click
from browser_use import Controller, Agent
import asyncio

from utils import save_to_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from typing import Optional
import os
from browser_use import BrowserSession

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
