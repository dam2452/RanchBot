from typing import (
    Any,
    Dict,
    List,
    Type,
)

from preprocessor.core.base_processor import BaseProcessor

PROCESSOR_REGISTRY: Dict[str, Type[BaseProcessor]] = {}


def register_processor(name: str):
    def decorator(cls: Type[BaseProcessor]):
        if name in PROCESSOR_REGISTRY:
            raise ValueError(f"Processor '{name}' already registered!")

        PROCESSOR_REGISTRY[name] = cls
        cls.PROCESSOR_NAME = name

        return cls
    return decorator


def get_processor_class(name: str) -> Type[BaseProcessor]:
    if name not in PROCESSOR_REGISTRY:
        available = ", ".join(sorted(PROCESSOR_REGISTRY.keys()))
        raise ValueError(
            f"Unknown processor: '{name}'\n"
            f"Available processors: {available}"
        )
    return PROCESSOR_REGISTRY[name]


def list_processors() -> List[str]:
    return sorted(PROCESSOR_REGISTRY.keys())


def get_processor_info(name: str) -> Dict[str, Any]:
    processor_class = get_processor_class(name)
    return {
        "name": name,
        "class": processor_class.__name__,
        "requires": getattr(processor_class, "REQUIRES", []),
        "produces": getattr(processor_class, "PRODUCES", []),
        "priority": getattr(processor_class, "PRIORITY", 100),
        "description": getattr(processor_class, "DESCRIPTION", ""),
    }
