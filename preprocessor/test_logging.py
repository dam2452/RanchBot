import logging
import sys

from preprocessor.utils.console import console

console.print("[bold green]Console print test - to powinno być widoczne w docker logs[/bold green]")
console.print("[yellow]Warning from console[/yellow]")
console.print("[red]Error from console[/red]")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

logger.info("Info log - to też powinno być widoczne")
logger.warning("Warning log")
logger.error("Error log")

print("Regular print() - też widoczne", file=sys.stderr)
print("Regular print() do stdout - też widoczne", file=sys.stdout)

console.print("[bold cyan]Test zakończony pomyślnie![/bold cyan]")
