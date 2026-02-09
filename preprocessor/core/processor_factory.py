from typing import (
    Any,
    Dict,
    List,
    Set,
    Tuple,
)

from preprocessor.core.processor_registry import (
    get_processor_class,
    get_processor_info,
    list_processors,
)


class ProcessorFactory:
    @staticmethod
    def create(processor_name: str, args: Dict[str, Any]):
        processor_class = get_processor_class(processor_name)
        return processor_class(args)

    @staticmethod
    def list_available() -> List[str]:
        return list_processors()

    @staticmethod
    def get_info(processor_name: str) -> Dict[str, Any]:
        return get_processor_info(processor_name)

    @staticmethod
    def get_all_info() -> List[Dict[str, Any]]:
        return [
            ProcessorFactory.get_info(name)
            for name in ProcessorFactory.list_available()
        ]

    @staticmethod
    def build_dependency_graph() -> Dict[str, List[str]]:
        graph = {}
        for name in list_processors():
            info = get_processor_info(name)
            graph[name] = info["requires"]
        return graph

    @staticmethod
    def validate_dependencies(
        processor_name: str,
        available_data: Set[str],
    ) -> Tuple[bool, List[str]]:
        info = get_processor_info(processor_name)
        required = set(info["requires"])
        missing = required - available_data
        return len(missing) == 0, sorted(missing)

    @staticmethod
    def sort_by_priority(processors: List[str]) -> List[str]:
        processor_info = {
            name: get_processor_info(name)
            for name in processors
        }
        return sorted(
            processors,
            key=lambda name: processor_info[name]["priority"],
        )
