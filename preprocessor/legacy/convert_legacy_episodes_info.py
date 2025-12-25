import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
)

import click

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("EpisodesInfoConverter")


@click.command()
@click.argument("input_json", type=click.Path(exists=True, path_type=Path))
@click.argument("output_json", type=click.Path(path_type=Path))
def convert(input_json: Path, output_json: Path) -> None:
    with input_json.open("r", encoding="utf-8") as f:
        old_data: Dict[str, Any] = json.load(f)

    new_data: Dict[str, Any] = {"seasons": []}

    for season_str, season_data in old_data.items():
        try:
            season_number: int = int(season_str)
        except ValueError:
            logger.error(f"Invalid season key '{season_str}' — must be integer as string.")
            continue

        episodes = season_data.get("episodes", [])
        new_data["seasons"].append({
            "season_number": season_number,
            "episodes": episodes,
        })

    new_data["seasons"].sort(key=lambda s: s["season_number"])

    with output_json.open("w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    logger.info(f"Converted episodes info written to: {output_json}")


if __name__ == "__main__":
    convert.main(standalone_mode=False)
