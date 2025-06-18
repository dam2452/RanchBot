from dataclasses import (
    dataclass,
    fields,
)
from datetime import (
    date,
    datetime,
)
from enum import Enum
from pathlib import Path


@dataclass
class Serializable:
    def to_dict(self):
        result = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, (date, datetime)):
                result[field.name] = value.isoformat()
            elif isinstance(value, bytes):
                result[field.name] = None
            elif isinstance(value, Enum):
                result[field.name] = value.value
            elif isinstance(value, Path):
                result[field.name] = str(value)
            elif isinstance(value, Serializable):
                result[field.name] = value.to_dict()
            elif isinstance(value, list):
                result[field.name] = [
                    v.to_dict() if isinstance(v, Serializable) else v for v in value
                ]
            else:
                result[field.name] = value
        return result
