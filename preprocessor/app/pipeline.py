from __future__ import annotations

from typing import (
    Dict,
    List,
    Optional,
    Set,
)

import networkx as nx

from preprocessor.app.step_builder import StepBuilder
from preprocessor.services.core.logging import ErrorHandlingLogger


class PipelineDefinition:
    def __init__(self, name: str) -> None:
        self.__name = name
        self.__steps: Dict[str, StepBuilder] = {}
        self.__graph: Optional[nx.DiGraph] = None

    @property
    def name(self) -> str:
        return self.__name

    def register(self, step: StepBuilder) -> None:
        if step.id in self.__steps:
            raise ValueError(
                f"DUPLICATE STEP:\n"
                f"  Step '{step.id}' is already registered in the pipeline!\n"
                f"  Check build_pipeline() in pipeline_factory.py",
            )
        self.__steps[step.id] = step

    def get_step(self, step_id: str) -> StepBuilder:
        if step_id not in self.__steps:
            raise KeyError(
                f"Step '{step_id}' not found. Available: {list(self.__steps.keys())}",
            )
        return self.__steps[step_id]

    def get_all_steps(self) -> Dict[str, StepBuilder]:
        return dict(self.__steps)

    def validate(self, logger: Optional["ErrorHandlingLogger"] = None) -> None:
        self.__graph = nx.DiGraph()

        for step_id, step in self.__steps.items():
            self.__graph.add_node(step_id, step=step)

        for step_id, step in self.__steps.items():
            for dep_id in step.dependency_ids:
                if dep_id not in self.__steps:
                    self.__raise_missing_dependency_error(step_id, dep_id)
                self.__graph.add_edge(dep_id, step_id)

        if not nx.is_directed_acyclic_graph(self.__graph):
            self.__raise_cycle_error()

        message = (
            f"Pipeline '{self.__name}' validated successfully:\n"
            f"   - {len(self.__steps)} steps registered\n"
            f"   - DAG structure confirmed\n"
            f"   - No cyclic dependencies"
        )

        if logger:
            logger.info(message)
        else:
            print(message)

    def get_execution_order(
        self, targets: Optional[List[str]] = None, skip: Optional[List[str]] = None,
    ) -> List[str]:
        if not self.__graph:
            raise RuntimeError(
                "Pipeline not validated! Call pipeline.validate() first.",
            )

        full_order: List[str] = list(nx.topological_sort(self.__graph))

        if targets:
            required: Set[str] = set()
            for target in targets:
                if target not in self.__steps:
                    raise ValueError(f"Target step '{target}' does not exist in pipeline")
                required.add(target)
                required.update(nx.ancestors(self.__graph, target))
            full_order = [s for s in full_order if s in required]

        skip_set: Set[str] = set(skip or [])
        return [s for s in full_order if s not in skip_set]

    def to_ascii_art(self) -> str:
        if not self.__graph:
            self.validate()

        lines: List[str] = [
            "=" * 80,
            f"PIPELINE: {self.__name}",
            "=" * 80,
            "",
        ]

        phases: Dict[str, List[StepBuilder]] = self.__group_steps_by_phase()

        for phase_name in ("SCRAPING", "PROCESSING", "INDEXING"):
            if phase_name not in phases:
                continue

            lines.append(f"[{phase_name}]")
            lines.append("-" * 80)

            for step in phases[phase_name]:
                deps_str = f" <- needs: {', '.join(step.dependency_ids)}" if step.dependency_ids else ""
                lines.append(f"  {step.id}{deps_str}")
                lines.append(f"    -> produces: {', '.join(step.produces)}")
                lines.append(f"    -> {step.description}\n")

        lines.append("=" * 80)
        return "\n".join(lines)

    def __group_steps_by_phase(self) -> Dict[str, List[StepBuilder]]:
        phases: Dict[str, List[StepBuilder]] = {}
        for step in self.__steps.values():
            phase_name = step.phase.name
            if phase_name not in phases:
                phases[phase_name] = []
            phases[phase_name].append(step)
        return phases

    def __raise_cycle_error(self) -> None:
        cycles = list(nx.simple_cycles(self.__graph))
        cycle_path = " -> ".join(cycles[0]) + f" -> {cycles[0][0]}"

        raise ValueError(
            f"\n{'=' * 80}\n"
            f"PIPELINE DEPENDENCY CYCLE DETECTED\n"
            f"{'=' * 80}\n\n"
            f"Cyclic dependency detected:\n"
            f"  {cycle_path}\n\n"
            f"Steps in cycle: {', '.join(cycles[0])}\n\n"
            f"Pipeline must be a DAG (Directed Acyclic Graph).\n"
            f"Remove one of the dependencies to break the cycle.\n"
            f"\n{'=' * 80}\n",
        )

    def __raise_missing_dependency_error(self, step_id: str, missing_dep_id: str) -> None:
        raise ValueError(
            f"\n{'=' * 80}\n"
            f"PIPELINE DEPENDENCY ERROR\n"
            f"{'=' * 80}\n\n"
            f"Step:           '{step_id}'\n"
            f"Needs:          '{missing_dep_id}'\n"
            f"Issue:          Step '{missing_dep_id}' is not registered!\n\n"
            f"Solution:\n"
            f"  1. Check build_pipeline() in preprocessor/app/pipeline_factory.py\n"
            f"  2. Ensure '{missing_dep_id}' is added via pipeline.register()\n"
            f"  3. Or remove '{missing_dep_id}' from needs=[...] in definition of '{step_id}'\n"
            f"\n{'=' * 80}\n",
        )

    def __repr__(self) -> str:
        return f"PipelineDefinition(name='{self.__name}', steps={len(self.__steps)})"
