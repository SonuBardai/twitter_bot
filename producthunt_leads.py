from datetime import datetime
import json
import os
import click
from typing import Optional, Union, List, Dict, Any
from pydantic import BaseModel
from crewai import Agent, LLM, Crew, Task
import pandas as pd
from pathlib import Path


class MakerLink(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None


class MakerDetails(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    followers: Optional[int] = None
    links: Optional[list[MakerLink]] = None


class ProductMakers(BaseModel):
    product_name: Optional[str] = None
    product_url: Optional[str] = None
    makers: Optional[list[MakerDetails]] = None


def validate_json_output(result: str) -> tuple[bool, Union[dict, str]]:
    """Validate that the output is valid JSON."""
    try:
        json_data = json.loads(result)
        return (True, json_data)
    except json.JSONDecodeError as e:
        return (False, f"Output must be valid JSON. Error: {str(e)}")


def build_makers_crew(markdown_file_path: str):
    """Build and return a CrewAI crew for extracting makers' details."""
    ollama_url = "http://localhost:11434"
    llm = LLM(model="ollama/llama3:latest", base_url=ollama_url)

    # config = {
    #     "llm": {
    #         "provider": "ollama",
    #         "config": {
    #             "model": "llama3",
    #         },
    #     },
    #     "embedder": {
    #         "provider": "ollama",
    #         "config": {
    #             "model": "all-minilm",
    #         },
    #     },
    # }
    # rag_tool = MDXSearchTool(mdx=markdown_file_path, config=config)

    maker_agent = Agent(
        role="Product Hunt Makers Data Extractor",
        goal="Extract detailed information about product makers from the provided markdown content",
        backstory="""You are an expert at analyzing product maker profiles and extracting structured information 
        including their names, roles, descriptions, follower counts, and social/professional links.
        
        When asked to provide JSON output, you return ONLY the JSON data without any additional text,
        explanations, or code block markers. Your output is always valid JSON that can be parsed directly.""",
        allow_delegation=False,
        llm=llm,
        verbose=True,
    )
    extraction_task = Task(
        agent=maker_agent,
        description="""
        Analyze the provided product and makers markdown content and extract structured information about each maker.
        The content is divided into two sections: Product Details and Team/Makers.
        
        For each maker, extract the following information:
        - Name
        - Role (if mentioned)
        - Description/bio
        - Number of followers (if available)
        - List of links (each with name and URL)
        
        The markdown content is:
        {markdown_file_content}

        IMPORTANT: Return ONLY the structured data as specified by the ProductMakers model.
        Do not include any explanatory text, code blocks, or markdown formatting.
        Do not make up any data.
        The output should be valid JSON that matches the ProductMakers schema exactly.
        """,
        expected_output="A ProductMakers object containing the extracted makers' information in the exact format specified by the Pydantic model",
        output_json=ProductMakers,
    )

    return Crew(
        agents=[maker_agent],
        tasks=[extraction_task],
        verbose=True,
    )


def process_makers_data(makers_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process makers data into a flat structure for Excel export."""
    processed_data = []

    for maker in makers_data:
        # Convert links list to a string representation
        links_str = ", ".join(f"{link.get('name', '')} ({link.get('url', '')})" for link in (maker.get("links") or []))

        processed_data.append(
            {"Name": maker.get("name", ""), "Role": maker.get("role", ""), "Description": maker.get("description", ""), "Followers": maker.get("followers", ""), "Links": links_str}
        )

    return processed_data


def leads_transform(date: datetime):
    """Transform product makers' data using CrewAI and export to Excel."""
    click.echo("🔄 Starting leads transformation stage...")

    # Directory where product cache files are stored
    cache_dir = Path("producthunt_product_cache")
    date_prefix = date.strftime("%Y-%m-%d")
    excel_file = cache_dir / f"{date_prefix}_product_makers.xlsx"

    # Create Excel writer object
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        # Find all product makers files for the given date
        try:
            product_files = [f for f in os.listdir(cache_dir) if f.startswith(date_prefix) and f.endswith("_makers.md")]
        except FileNotFoundError:
            click.echo(f"❌ No product cache directory found at {cache_dir}")
            return

        if not product_files:
            click.echo(f"ℹ️  No product cache files found for date {date_prefix}")
            return

        processed_products = 0

        for product_file in product_files:
            crew = build_makers_crew(product_file)
            click.echo(f"🔍 Processing makers for: {product_file}")
            file_path = cache_dir / product_file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    markdown_content = f.read()

                # Extract product name from filename (remove date prefix and _makers suffix)
                product_name = product_file.replace(f"{date_prefix}_", "").replace("_makers.md", "")
                click.echo(f"🔍 Processing makers for: {product_name}")

                # Run the crew to extract makers' information
                result = crew.kickoff({"markdown_file_content": markdown_content})

                if not result or not result.json_dict.get("makers"):
                    click.echo(f"⚠️  No makers data found for {product_name}")
                    continue

                # Process the makers data for Excel
                makers_data = result.json_dict["makers"]
                df = pd.DataFrame(process_makers_data(makers_data))

                # Get product URL from the result if available, otherwise use empty string
                product_url = result.json_dict.get("product_url", "")

                # Create a new DataFrame for the header
                header_data = {"Product": [f"Name: {product_name}"], " ": [f"URL: {product_url}"]}
                header_df = pd.DataFrame(header_data)

                # Create a blank row for spacing
                blank_row = pd.DataFrame([[""] * len(df.columns)], columns=df.columns)

                # Combine header, blank row, and makers data
                df_final = pd.concat([header_df, blank_row, df], ignore_index=True)

                # Write to Excel sheet (sheet name max 31 chars, no special chars)
                sheet_name = product_name[:31].translate(str.maketrans("", "", "[]:*?/\\"))

                # Write the combined data to Excel
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df_final.columns):
                    # Set column width to max of data length or header length
                    max_length = max(df_final[col].astype(str).apply(len).max(), len(str(col)))
                    # Add a little extra space
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                    worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width

                # Merge cells for the header row for better appearance
                worksheet.merge_cells("A1:B1")
                worksheet.merge_cells("A2:B2")

                processed_products += 1
                click.echo(f"✅ Successfully processed makers for: {product_name}")

            except Exception as e:
                click.echo(f"⚠️  Error processing {product_file}: {str(e)}")
                raise

    if processed_products > 0:
        click.echo(f"\n💾 Saved makers data to {excel_file}")
        click.echo(f"📊 Processed {processed_products} products with makers data")
    else:
        click.echo("\n⚠️  No makers data was processed")
