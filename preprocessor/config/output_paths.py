from pathlib import Path
from typing import Optional

from preprocessor.services.core.environment import Environment

BASE_OUTPUT_DIR = Path('/app/output_data') if Environment.is_docker() else Path('preprocessor/output_data')

def get_base_output_dir(series_name: Optional[str]=None) -> Path:
    base = Path('/app/output_data') if Environment.is_docker() else Path('preprocessor/output_data')
    if series_name:
        return base / series_name.lower()
    return base

def get_output_path(relative_path: str, series_name: Optional[str]=None) -> Path:
    return get_base_output_dir(series_name) / relative_path
