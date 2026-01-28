import json
from pathlib import Path
from typing import Any


def atomic_write_json(output_path: Path, data: Any, **kwargs) -> None:
    kwargs.setdefault('ensure_ascii', False)
    temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, **kwargs)
    temp_path.replace(output_path)


def atomic_write_text(output_path: Path, content: str) -> None:
    temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(content)
    temp_path.replace(output_path)
