from dataclasses import (
    dataclass,
    field,
)
import importlib
from typing import (
    TYPE_CHECKING,
    Any,
    List,
)

if TYPE_CHECKING:
    from preprocessor.core.base_step import PipelineStep


@dataclass
class Phase:
    name: str
    color: str


@dataclass
class StepBuilder:
    description: str
    id: str
    module: str
    phase: Phase
    produces: List[str]
    config: Any = None
    needs: List["StepBuilder"] = field(default_factory=list)

    @property
    def dependency_ids(self) -> List[str]:
        return [step.id for step in self.needs]

    def load_class(self) -> type:
        module_path, class_name = self.module.split(":")

        try:
            mod = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(
                f"Cannot load module '{module_path}' for step '{self.id}': {e}",
            ) from e

        try:
            return getattr(mod, class_name)
        except AttributeError as e:
            raise AttributeError(
                f"Class '{class_name}' not found in module '{module_path}' for step '{self.id}': {e}",
            ) from e

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StepBuilder):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __post_init__(self) -> None:
        if not self.id.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Invalid step_id: '{self.id}'. Use only alphanumeric and underscores.",
            )
        if not self.module or ":" not in self.module:
            raise ValueError(
                f"Invalid module format for '{self.id}'. Expected 'package.module:ClassName'",
            )

    def __repr__(self) -> str:
        deps = f", needs={self.dependency_ids}" if self.needs else ""
        return f"StepBuilder(id='{self.id}'{deps})"
