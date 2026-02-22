from pathlib import Path
from typing import Optional

from preprocessor.services.core.environment import Environment


def get_base_output_dir(series_name: Optional[str] = None) -> Path:
    if Environment.is_docker():
        base = Path('/app/output_data')
    else:
        base = Path('preprocessor/output_data')

    if series_name:
        return base / series_name.lower()
    return base


def get_output_path(relative_path: str, series_name: Optional[str] = None) -> Path:
    return get_base_output_dir(series_name) / relative_path
