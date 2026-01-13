import logging
import sys

logging.getLogger('matplotlib').setLevel(logging.WARNING)

from preprocessor.cli import cli
from preprocessor.utils.console import console

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
