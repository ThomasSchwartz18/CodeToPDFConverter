import click
from flask.cli import with_appcontext
from app.services.file_processor import FileProcessor
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

@click.command('cleanup-uploads')
@click.option('--age-limit', default=3600, help='Maximum age of folders in seconds before cleanup (default: 3600)')
@with_appcontext
def cleanup_uploads(age_limit):
    """Clean stale upload folders."""
    try:
        logger.info(f"Starting cleanup of upload folders older than {age_limit} seconds")
        FileProcessor.cleanup_stale_uploads(age_limit_seconds=age_limit)
        click.echo('Cleanup completed successfully.')
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        click.echo(f'Error during cleanup: {str(e)}', err=True)
        raise click.Abort() 