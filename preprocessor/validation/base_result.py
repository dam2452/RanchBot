from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Dict,
    List,
)


class ValidationStatusMixin:
    errors: List[str]
    warnings: List[str]

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARNING"
        return "PASS"


@dataclass
class BaseValidationResult(ValidationStatusMixin):
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
        }
