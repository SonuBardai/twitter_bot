import json
import logging
from utils import save_to_cache
from typing import Dict, Any, List
from utils import get_latest_cache_file
from models import Tweets, Tweet
from langchain_google_genai import ChatGoogleGenerativeAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the language model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")


def _generate_tweet_prompt(raw_content: str, topics: List[str]) -> str:
    """Generate a prompt for the LLM to create tweets."""
    topics_str = ", ".join(topics) if topics else "general tech news"

    return f"""You are an expert social media manager creating engaging Twitter threads about {topics_str}.
    
    Here's the content to create tweets from:
    ---
    {raw_content}
    ---
    
    Create a Twitter thread (1-3 tweets) that is engaging and informative. The first tweet should indicate that this is a thread and be attractive enough to make the reader want to read the rest of the thread. Follow these rules:
    1. Each tweet must be under 280 characters
    2. Include relevant hashtags from: {", ".join(topics) if topics else "#tech #news"}
    3. Make it engaging and conversational
    4. If multiple tweets, make them flow naturally in a thread
    5. Don't include tweet numbers (1/2, 2/2, etc.)
    6. Return ONLY a JSON array of tweet objects, like this:
    
    [
        {{
            "content": "Your first tweet here...",
            "char_count": 123
        }},
        {{
            "content": "Your second tweet here...",
            "char_count": 123
        }}
    ]
    
    IMPORTANT: 
    - Only return the raw JSON array, without any markdown code blocks or additional text
    - Do not wrap the response in ```json or any other markdown
    - The response should start with [ and end with ]
    - No additional text before or after the JSON array"""


def _clean_llm_response(response: str) -> str:
    """Clean the LLM response by removing markdown code blocks and extra text."""
    # Remove markdown code blocks if present
    if "```json" in response:
        # Extract content between ```json and ```
        start = response.find("```json") + 7  # 7 is len('```json\n')
        end = response.rfind("```")
        response = response[start:end].strip()
    elif "```" in response:
        # Handle case where it's just ``` without json
        start = response.find("```") + 3
        end = response.rfind("```")
        response = response[start:end].strip()

    # Remove any remaining whitespace and newlines
    return response.strip()


def _parse_llm_response_to_tweets(response: str, topics: List[str]) -> Tweets:
    """Parse the LLM response into a Tweets object."""
    try:
        # Clean the response before parsing
        response = _clean_llm_response(response)
        # Try to parse the response as JSON
        tweets_data = json.loads(response)

        # If it's a string that looks like JSON, parse it
        if isinstance(tweets_data, str):
            tweets_data = json.loads(tweets_data)

        # Ensure we have a list of tweets
        if not isinstance(tweets_data, list):
            tweets_data = [tweets_data]

        # Convert to Tweet objects
        tweets = []
        for tweet_data in tweets_data:
            if isinstance(tweet_data, dict):
                # Ensure content exists
                if "content" not in tweet_data:
                    continue

                # Add topics as hashtags if not already present
                content = tweet_data["content"]
                existing_hashtags = {word.lower() for word in content.split() if word.startswith("#")}

                # Add missing topic hashtags
                for topic in topics:
                    topic = topic.lstrip("#")
                    if f"#{topic.lower()}" not in existing_hashtags:
                        content += f" #{topic}"

                # Ensure char_count is set
                char_count = tweet_data.get("char_count", len(content))

                tweets.append(Tweet(content=content.strip(), char_count=char_count))

        return Tweets(items=tweets, is_thread=len(tweets) > 1)

    except Exception as e:
        logger.error(f"Failed to parse LLM response: {str(e)}")
        logger.debug(f"Response content: {response}")
        raise ValueError(f"Failed to parse tweet generation response: {str(e)}")


def write_tweet(ingest_data: Dict[str, Any]) -> Tweets:
    """
    Generate tweets using LLM based on the ingested data.

    Args:
        ingest_data: The raw data from the ingest step

    Returns:
        Tweets: A Tweets object containing one or more generated tweets

    Raises:
        ValueError: If the input data is invalid or tweet generation fails
    """
    try:
        # Extract the main content and topics
        raw_content = ingest_data.get("full_content", "").strip()
        topics = [t for t in ingest_data.get("topics", []) if t and isinstance(t, str)]

        if not raw_content:
            raise ValueError("No content available to create a tweet")

        # Generate the prompt
        prompt = _generate_tweet_prompt(raw_content, topics)

        # Get response from LLM
        response = llm.invoke(prompt).content

        print("generated tweets: ", response)

        # Parse the response into Tweets object
        parsed_tweets = _parse_llm_response_to_tweets(response, topics)
        print("parsed tweets: ", parsed_tweets)

        return parsed_tweets

    except Exception as e:
        logger.error(f"Error in write_tweet: {str(e)}", exc_info=True)
        raise


def transform() -> Dict[str, Any]:
    """
    Step 2: Transform data from the latest cache file into tweet(s).

    Returns:
        Dict[str, Any]: Dictionary containing the transformation results

    Raises:
        FileNotFoundError: If no cache files are found
        ValueError: If the transformation fails
    """
    logger.info("🔄 Starting data transformation...")

    try:
        # Get the latest cache file
        cache_file = get_latest_cache_file("ingest_cache")
        logger.info(f"📂 Using cache file: {cache_file}")

        # Read and parse the cache file
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)

        # Basic validation
        if not cached_data or not isinstance(cached_data, dict):
            raise ValueError("Invalid cache data format")

        # Transform the data into tweets
        results = write_tweet(cached_data)

        logger.info(f"✅ Successfully transformed data into {len(results.items)} tweet(s)")

        # Save to transform cache
        try:
            results_dict = [item.model_dump() for item in results.items]
            cache_file = save_to_cache(results_dict, "transform_cache")
            logger.info(f"💾 Saved transform results to: {cache_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save transform cache: {str(e)}")

        return results_dict

    except FileNotFoundError as e:
        error_msg = f"Cache file not found: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg, "source": "transform"}
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse cache file: {cache_file}"
        logger.error(f"{error_msg}: {str(e)}")
        return {"status": "error", "error": error_msg, "source": "transform"}
    except Exception as e:
        error_msg = f"Unexpected error during transformation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg, "source": "transform"}
