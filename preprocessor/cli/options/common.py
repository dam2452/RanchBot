from pathlib import Path

import click

from preprocessor.config.config import settings


def episodes_info_option(required=True):
    return click.option(
        "--episodes-info-json",
        type=click.Path(exists=True, path_type=Path),
        required=required,
        help="JSON file with episode metadata",
    )


def name_option(required=True):
    return click.option(
        "--name",
        required=required,
        help="Series name for state management and resume support",
    )


def state_option():
    return click.option(
        "--no-state",
        is_flag=True,
        help="Disable state management (no resume on interrupt)",
    )


def max_workers_option(default=None):
    default_val = default or settings.transcode.max_workers
    return click.option(
        "--max-workers",
        type=int,
        default=default_val,
        help=f"Number of parallel workers (default: {default_val})",
    )


def videos_argument():
    return click.argument(
        "videos",
        type=click.Path(exists=True, file_okay=False, path_type=Path),
    )
