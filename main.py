from datetime import datetime
import click
from dotenv import load_dotenv
from producthunt import producthunt as producthunt_cmd
from ingest import ingest
from transform import transform
from post import post


load_dotenv()


@click.group()
def cli():
    """A simple CLI tool for Twitter operations."""
    pass


class PipelineError(Exception):
    """Custom exception for pipeline failures."""

    pass


@click.command()
@click.option("--stage", type=click.Choice(["ingest", "transform", "post"], case_sensitive=False), help="Run only a specific stage of the pipeline")
def tweet(stage: str = None):
    """Run the tweet pipeline or a specific stage.

    If no stage is specified, runs all stages in sequence: ingest -> transform -> post
    """
    try:
        if stage is None or stage == "ingest":
            click.echo("🚀 Starting ingest stage...")
            ingest()
        else:
            click.echo("⏭️  Skipping ingest stage")

        if stage is None or stage == "transform":
            click.echo("\n🔄 Starting transform stage...")
            transform()
        else:
            click.echo("⏭️  Skipping transform stage")

        if stage is None or stage == "post":
            click.echo("\n📤 Starting post stage...")
            post()
        else:
            click.echo("⏭️  Skipping post stage")

        if stage is None:
            click.echo("\n✅ All pipeline stages completed successfully!")
        else:
            click.echo(f"\n✅ Stage '{stage}' completed successfully!")

    except Exception as e:
        stage_msg = f" in stage '{stage}'" if stage else ""
        click.echo(f"❌ Unexpected error{stage_msg}: {str(e)}", err=True)
        raise


@click.command()
def retweet():
    click.echo("🚀 Starting retweet stage...")


@click.command()
def comment():
    click.echo("🚀 Starting comment stage...")


@click.command()
def producthunt():
    click.echo("🚀 Starting product hunt scrape...")
    date = datetime.now()
    producthunt_cmd(date=date)


cli.add_command(tweet)
cli.add_command(retweet)
cli.add_command(comment)

cli.add_command(producthunt)

if __name__ == "__main__":
    cli()
