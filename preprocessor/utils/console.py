import os
import sys

from rich.console import Console

_console_instance = None


def get_console() -> Console:
    global _console_instance  # pylint: disable=global-statement
    if _console_instance is None:
        in_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER', 'false') == 'true'

        _console_instance = Console(
            force_terminal=True if in_docker else None,
            force_interactive=False,
            file=sys.stderr,
            color_system="standard" if in_docker else "auto",
        )
    return _console_instance


console = get_console()
