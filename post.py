import os
import asyncio
import json
from typing import Dict, Any
import click
from browser_use import Agent, BrowserSession
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from utils import get_latest_cache_file

load_dotenv()

# Initialize browser session
headless = os.getenv("HEADLESS", True) in ["true", "True", "1", "t", "T", True]
browser_session = BrowserSession(
    headless=headless,
    user_data_dir=os.path.expanduser("~/Library/Application Support/Google/Chrome"),
    executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    keep_alive=True,
    launch_browser_executable=True,
)


def _get_tweet_composition_instructions(tweets_data: list) -> str:
    """Generate instructions for composing multiple tweets."""
    if not tweets_data:
        return ""

    instructions = [f"11. Find the tweet input field and type: {tweets_data[0]['content']}"]

    if len(tweets_data) > 1:
        for i, tweet in enumerate(tweets_data[1:], 2):
            instructions.extend([f"{10 + i * 2 - 1}. Click the 'Add' button to add another tweet", f"{10 + i * 2}. Type in the next tweet: {tweet['content']}"])

    return "\n".join(instructions)


async def post_async() -> Dict[str, Any]:
    """Async implementation of the post function."""
    click.echo("🚀 Starting Twitter post...")

    # Read the latest transform cache file
    try:
        cache_file = get_latest_cache_file("transform_cache")
        click.echo(f"📂 Using transform cache file: {cache_file}")

        with open(cache_file, "r", encoding="utf-8") as f:
            tweets_data = json.load(f)

        if not isinstance(tweets_data, list) or not all(isinstance(t, dict) for t in tweets_data):
            raise ValueError("Invalid transform cache format: expected a list of tweet dictionaries")

        click.echo(f"📝 Found {len(tweets_data)} tweets to post")

    except Exception as e:
        error_msg = f"Failed to read transform cache: {str(e)}"
        click.echo(f"❌ {error_msg}", err=True)
        return {"status": "error", "error": error_msg}

    # Get Twitter credentials from environment variables
    twitter_email = os.getenv("TWITTER_EMAIL")
    twitter_password = os.getenv("TWITTER_PASSWORD")

    if not twitter_email:
        raise ValueError("TWITTER_EMAIL environment variable is not set")
    if not twitter_password:
        raise ValueError("TWITTER_PASSWORD environment variable is not set")

    # Initialize the language model
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

    try:
        task = f"""
            # Phase 1: Login
            1. Go to https://x.com/i/flow/login?redirect_after_login=%2Fhome
            2. Wait for the login page to load completely
            3. Find the email input field and enter the email: {twitter_email}
            4. Click the 'Next' button
            5. Wait for the password input field to appear
            6. Find the password input field and enter the password: {twitter_password}
            7. Click the 'Log in' button
            8. Wait for the home timeline to load
            
            # Phase 2: Navigate to compose tweet
            9. Go to https://x.com/compose/post
            10. Wait for the compose dialog to appear
            
            # Phase 3: Compose tweets from the list
            {_get_tweet_composition_instructions(tweets_data)}
            
            Important:
            - If already logged in, just verify you're on the home timeline
            - If any security checks appear, wait for them to complete
            - Do NOT click the 'Post' button
        """

        # test if we're logged in
        task = """
        1. Go to https://x.com
        2. Wait until the homepage is fully loaded
        """

        # Create agent for Twitter login and tweet composition
        agent = Agent(
            task=task,
            llm=llm,
            browser_session=browser_session,
            max_failures=1,
        )

        # Execute the agent and await the result
        result = await agent.run()
        print("result: ", result)

        click.echo("✅ Successfully navigated to Twitter login page")
        return {"status": "success", "message": "Navigated to Twitter login page"}

    except Exception as e:
        click.echo(f"❌ Error during Twitter login: {str(e)}", err=True)
        raise


def post() -> Dict[str, Any]:
    """Step 3: Post data to Twitter."""
    try:
        return asyncio.run(post_async())
    except Exception as e:
        click.echo(f"❌ Error in post: {str(e)}", err=True)
        raise
