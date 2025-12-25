from pathlib import Path

import click


def common_params(func):
    options = [
        click.option("--name", required=True, help="Series name"),
        click.option(
            "--episodes-info-json",
            type=click.Path(exists=True, path_type=Path),
            required=True,
            help="JSON file with episode metadata",
        ),
    ]
    for option in reversed(options):
        func = option(func)
    return func


def video_input_params(func):
    return click.argument(
        "videos", type=click.Path(exists=True, file_okay=False, path_type=Path),
    )(func)


def state_params(func):
    return click.option(
        "--no-state", is_flag=True, help="Disable state management (no resume on interrupt)",
    )(func)
