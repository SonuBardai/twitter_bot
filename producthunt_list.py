from datetime import datetime
import click
from crewai import Agent, LLM, Crew, Task
from pydantic import BaseModel

from firecrawl_utils import scrape_with_firecrawl
from utils import get_latest_cache_file, save_to_cache


class Product(BaseModel):
    name: str | None
    description: str | None
    url: str | None


class Products(BaseModel):
    products: list[Product]


def build_crew():
    ollama_url = "http://localhost:11434"
    llm = LLM(model="ollama/llama3:latest", base_url=ollama_url)

    csv_agent = Agent(
        role="Product Hunt Data Extractor",
        goal="Extract the data from the provided markdown file in the expected format",
        backstory="You are a data extractor. You are given a markdown file and you need to extract the data from it in the expected format which is provided to you in the prompt.",
        allow_delegation=False,
        llm=llm,
        verbose=True,
    )

    data_extractor_task = Task(
        agent=csv_agent,
        description="""
        Read the markdown file and extract the data from it in the expected format which is provided to you.

        The expected format is:

        class Product(BaseModel):
            name: str | None
            description: str | None
            url: str | None

        class Products(BaseModel):
            products: list[Product]


        The markdown content is:
        {markdown_file_content}

        """,
        expected_output="A list of objects of type Product",
        output_json=Products,
    )

    data_extraction_crew = Crew(
        agents=[csv_agent],
        tasks=[data_extractor_task],
        verbose=True,
    )

    return data_extraction_crew


def ingest(date: datetime):
    year, month, day = date.year, date.month, date.day
    url = f"https://www.producthunt.com/leaderboard/daily/{year}/{month}/{day}"

    markdown_content = scrape_with_firecrawl(url)
    if markdown_content:
        save_to_cache(markdown_content, "producthunt_cache", "md", date)
        return markdown_content
    return None


def transform(date: datetime):
    click.echo("🔄 Starting transform stage...")

    cache_file = get_latest_cache_file("producthunt_cache", "md")
    with open(cache_file, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    crew = build_crew()
    result = crew.kickoff({"markdown_file_content": markdown_content})

    print("result: ", result)
    save_to_cache(result.json_dict, "producthunt_data_cache", "json", date)


def get_products_list(date: datetime):
    ingest(date)
    transform(date)
