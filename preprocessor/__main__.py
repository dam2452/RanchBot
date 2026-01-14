import logging
import sys

from preprocessor.cli import cli
from preprocessor.utils.console import console

logging.getLogger('matplotlib').setLevel(logging.WARNING)

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
