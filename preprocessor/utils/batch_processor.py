from typing import (
    Callable,
    Generic,
    List,
    TypeVar,
)

T = TypeVar('T')
R = TypeVar('R')

class BatchProcessor(Generic[T, R]):
    def __init__(self, batch_size: int):
        self.batch_size = batch_size

    def process(
        self,
        items: List[T],
        process_fn: Callable[[List[T]], List[R]],
    ) -> List[R]:
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i+self.batch_size]
            results.extend(process_fn(batch))
        return results
