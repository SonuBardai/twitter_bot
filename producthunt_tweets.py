from datetime import datetime
import os
import pandas as pd
import click
from pathlib import Path
from crewai import Agent, Task, Crew, LLM
from typing import Dict, Any
from pydantic import BaseModel


class Tweet(BaseModel):
    tweet_number: int
    content: str


class Tweets(BaseModel):
    tweets: list[Tweet]


def build_tweet_crew():
    """Build and return a CrewAI crew for generating tweet threads."""
    ollama_url = "http://localhost:11434"
    llm = LLM(model="ollama/llama3:latest", base_url=ollama_url)

    # Create a content strategist agent
    strategist = Agent(
        role="Social Media Content Strategist",
        goal="Create engaging and informative tweet threads about tech products",
        backstory="""You are an expert at creating engaging social media content for technical audiences. 
        You specialize in breaking down complex product features into digestible, engaging tweet threads
        that highlight the product's value proposition.""",
        llm=llm,
        verbose=True,
    )

    # Create a thread writer agent
    writer = Agent(
        role="Tweet Thread Writer",
        goal="Write compelling tweet threads based on product information",
        backstory="""You are a skilled writer who specializes in creating engaging Twitter threads.
        You know how to maintain a consistent tone, use effective hooks, and structure threads
        for maximum engagement and readability.""",
        llm=llm,
        verbose=True,
    )

    # Define tasks
    strategy_task = Task(
        description="""Analyze the product information and create a content strategy for the tweet thread.
        Focus on the most compelling features, benefits, and unique selling points of the product.
        Consider the target audience and what would make them interested in this product.

        Product Information:
        {product_details}
        """,
        agent=strategist,
        expected_output="A content strategy for the tweet thread, including key points to cover.",
    )

    write_task = Task(
        description="""Using the content strategy, write an engaging tweet thread about the product.
        The thread should be informative, engaging, and encourage interaction.
        Format the output as a list of tweets, where each tweet is a string.

        For each tweet return the tweet number and the content of the tweet.
        Do not make up any data.
        The output should be valid JSON that matches the Tweets schema exactly.

        Product Information:
        {product_details}
        """,
        agent=writer,
        expected_output="A list of tweets that form a coherent thread about the product.",
        output_json=Tweets,
    )

    # Create and return the crew
    return Crew(
        agents=[strategist, writer],
        tasks=[strategy_task, write_task],
        verbose=True,
    )


def process_product_details(file_path: Path) -> Dict[str, Any]:
    """Process a single product details markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "error": None}
    except Exception as e:
        return {"content": None, "error": str(e)}


def tweets_transform(date: datetime):
    """Transform product details into tweet threads."""
    cache_dir = Path("producthunt_product_cache")
    date_prefix = date.strftime("%Y-%m-%d")
    output_file = cache_dir / f"{date_prefix}_tweet_threads.xlsx"

    # Find all product detail files for the given date
    try:
        product_files = [f for f in os.listdir(cache_dir) if f.startswith(date_prefix)]
    except FileNotFoundError:
        click.echo(f"❌ No product cache directory found at {cache_dir}")
        return

    if not product_files:
        click.echo(f"ℹ️  No product detail files found for date {date_prefix}")
        return

    # Initialize Excel writer
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        processed_products = 0

        for product_file in product_files:
            file_path = cache_dir / product_file
            product_name = product_file.replace(f"{date_prefix}_", "")
            click.echo(f"📝 Processing tweets for: {product_name}")

            # Process the product details
            result = process_product_details(file_path)
            if result["error"]:
                click.echo(f"⚠️  Error reading {product_file}: {result['error']}")
                raise Exception(f"Error reading {product_file}: {result['error']}")

            try:
                # Initialize crew for this product
                crew = build_tweet_crew()

                # Run the crew to generate tweet thread
                crew_result = crew.kickoff({"product_details": result["content"]})

                if not crew_result or not crew_result.json_dict.get("tweets"):
                    click.echo(f"⚠️  Failed to generate tweets for {product_name}")
                    continue

                # Prepare data for Excel
                tweets = crew_result.json_dict["tweets"]
                df = pd.DataFrame({"Tweet Number": range(1, len(tweets) + 1), "Content": tweets})

                # Clean and validate sheet name
                sheet_name = product_name[:31].translate(str.maketrans("", "", "[]:*?/\\"))

                # Write to Excel sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
                    adjusted_width = min(max_length + 2, 100)  # Wider for tweet content
                    worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width

                processed_products += 1
                click.echo(f"✅ Successfully generated tweets for: {product_name}")

            except Exception as e:
                click.echo(f"⚠️  Error generating tweets for {product_name}: {str(e)}")
                raise Exception(f"Error generating tweets for {product_name}: {str(e)}")

    if processed_products > 0:
        click.echo(f"\n💾 Saved tweet threads to {output_file}")
        click.echo(f"🐦 Processed {processed_products} products")
    else:
        click.echo("\n⚠️  No tweet threads were generated")
