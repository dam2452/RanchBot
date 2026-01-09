import gc
import sys


class ResourceScope:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        gc.collect()
        if "torch" in sys.modules:
            import torch  # pylint: disable=import-outside-toplevel

            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
