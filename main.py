import click
from dotenv import load_dotenv
from ingest import ingest
from transform import transform
from post import post


# Load environment variables
load_dotenv()


@click.group()
def cli():
    """A simple CLI tool for Twitter operations."""
    pass


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
