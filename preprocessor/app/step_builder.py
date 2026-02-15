from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from preprocessor.core.base_step import PipelineStep
from preprocessor.core.output_descriptors import (
    OutputDescriptor,
    ValidationResult,
)


@dataclass(frozen=True)
class Phase:
    name: str
    color: str


@dataclass
class StepBuilder:
    description: str
    step_class: Type[PipelineStep]
    phase: Phase
    produces: Union[List[str], List[OutputDescriptor]]
    id: Optional[str] = None
    config: Any = None
    needs: List[StepBuilder] = field(default_factory=list)

    @property
    def dependency_ids(self) -> List[str]:
        return [step.id for step in self.needs]

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        if not self.produces:
            return []

        if isinstance(self.produces[0], OutputDescriptor):
            return self.produces

        return []

    def validate_outputs(
            self,
            base_dir: Path,
            context_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, ValidationResult]:
        results = {}
        for idx, descriptor in enumerate(self.get_output_descriptors()):
            result = descriptor.validate(base_dir, context_vars)
            results[f'{self.id}_output_{idx}'] = result
        return results

    def get_dependency_outputs(self) -> Dict[str, List[OutputDescriptor]]:
        return {
            dep.id: dep.get_output_descriptors()
            for dep in self.needs
        }

    def __post_init__(self) -> None:
        if self.id is None:
            object.__setattr__(self, 'id', self.__generate_id_from_class())
        self.__validate_id()

    def __generate_id_from_class(self) -> str:
        class_name = self.step_class.__name__
        class_name_without_step = re.sub(r'Step$', '', class_name)
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name_without_step).lower()
        return snake_case

    def __validate_id(self) -> None:
        if not self.id or not self.id.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Invalid step_id: '{self.id}'. Use only alphanumeric and underscores.",
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StepBuilder):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        deps = f", needs={self.dependency_ids}" if self.needs else ""
        return f"StepBuilder(id='{self.id}'{deps})"
