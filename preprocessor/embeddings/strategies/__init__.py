from preprocessor.embeddings.strategies.base_strategy import BaseKeyframeStrategy
from preprocessor.embeddings.strategies.color_diff_strategy import ColorDiffStrategy
from preprocessor.embeddings.strategies.keyframes_strategy import KeyframesStrategy
from preprocessor.embeddings.strategies.scene_changes_strategy import SceneChangesStrategy

__all__ = [
    "BaseKeyframeStrategy",
    "ColorDiffStrategy",
    "KeyframesStrategy",
    "SceneChangesStrategy",
]
