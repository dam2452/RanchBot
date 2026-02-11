from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Set,
)

import networkx as nx

from preprocessor.app.step_builder import StepBuilder

if TYPE_CHECKING:
    from preprocessor.lib.core.logging import ErrorHandlingLogger


class PipelineDefinition:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self._steps: Dict[str, StepBuilder] = {}
        self._graph: Optional[nx.DiGraph] = None

    def register(self, step: StepBuilder) -> None:
        if step.id in self._steps:
            raise ValueError(
                f"❌ DUPLICATE STEP:\n"
                f"  Step '{step.id}' is already registered in the pipeline!\n"
                f"  Check build_pipeline() in pipeline_factory.py",
            )
        self._steps[step.id] = step

    def validate(self, logger: Optional["ErrorHandlingLogger"] = None) -> None:
        self._graph = nx.DiGraph()

        for step_id, step in self._steps.items():
            self._graph.add_node(step_id, step=step)

        for step_id, step in self._steps.items():
            for dep_id in step.dependency_ids:
                if dep_id not in self._steps:
                    self._raise_missing_dependency_error(step_id, dep_id)
                self._graph.add_edge(dep_id, step_id)

        if not nx.is_directed_acyclic_graph(self._graph):
            self._raise_cycle_error()

        message = (
            f"✅ Pipeline '{self.name}' validated successfully:\n"
            f"   - {len(self._steps)} steps registered\n"
            f"   - DAG structure confirmed\n"
            f"   - No cyclic dependencies"
        )

        if logger:
            logger.info(message)
        else:
            print(message)

    def _raise_missing_dependency_error(
        self, step_id: str, missing_dep_id: str,
    ) -> None:
        raise ValueError(
            f"\n{'=' * 80}\n"
            f"❌ PIPELINE DEPENDENCY ERROR\n"
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

    def _raise_cycle_error(self) -> None:
        cycles: List[List[str]] = list(nx.simple_cycles(self._graph))
        cycle_path: str = " → ".join(cycles[0]) + f" → {cycles[0][0]}"

        raise ValueError(
            f"\n{'=' * 80}\n"
            f"❌ PIPELINE DEPENDENCY CYCLE DETECTED\n"
            f"{'=' * 80}\n\n"
            f"Cyclic dependency detected:\n"
            f"  {cycle_path}\n\n"
            f"Steps in cycle: {', '.join(cycles[0])}\n\n"
            f"Pipeline must be a DAG (Directed Acyclic Graph).\n"
            f"Remove one of the dependencies to break the cycle.\n"
            f"\n{'=' * 80}\n",
        )

    def get_execution_order(
        self, targets: Optional[List[str]] = None, skip: Optional[List[str]] = None,
    ) -> List[str]:
        if not self._graph:
            raise RuntimeError(
                "Pipeline not validated! Call pipeline.validate() first.",
            )

        full_order: List[str] = list(nx.topological_sort(self._graph))

        if targets:
            required: Set[str] = set()
            for target in targets:
                if target not in self._steps:
                    raise ValueError(
                        f"Target step '{target}' does not exist in pipeline",
                    )
                required.add(target)
                required.update(nx.ancestors(self._graph, target))
            full_order = [s for s in full_order if s in required]

        skip_set: Set[str] = set(skip or [])
        return [s for s in full_order if s not in skip_set]

    def get_step(self, step_id: str) -> StepBuilder:
        if step_id not in self._steps:
            raise KeyError(
                f"Step '{step_id}' not found. Available: {list(self._steps.keys())}",
            )
        return self._steps[step_id]

    def to_ascii_art(self) -> str:
        if not self._graph:
            self.validate()

        lines: List[str] = [
            "=" * 80,
            f"PIPELINE: {self.name}",
            "=" * 80,
            "",
        ]

        phases: Dict[str, List[StepBuilder]] = {}
        for _, step in self._steps.items():
            phase_name: str = step.phase.name
            if phase_name not in phases:
                phases[phase_name] = []
            phases[phase_name].append(step)

        for phase_name in ("SCRAPING", "PROCESSING", "INDEXING"):
            if phase_name not in phases:
                continue

            lines.append(f"[{phase_name}]")
            lines.append("-" * 80)

            for step in phases[phase_name]:
                deps_str: str = ""
                if step.dependency_ids:
                    deps_str = f" ← needs: {', '.join(step.dependency_ids)}"

                lines.append(f"  {step.id}{deps_str}")
                lines.append(f"    → produces: {', '.join(step.produces)}")
                lines.append(f"    → {step.description}")
                lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    def get_all_steps(self) -> Dict[str, StepBuilder]:
        return dict(self._steps)

    def __repr__(self) -> str:
        return f"PipelineDefinition(name='{self.name}', steps={len(self._steps)})"
