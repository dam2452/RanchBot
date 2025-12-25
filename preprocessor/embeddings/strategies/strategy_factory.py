from preprocessor.core.enums import KeyframeStrategy
from preprocessor.embeddings.strategies.base_strategy import BaseKeyframeStrategy
from preprocessor.embeddings.strategies.color_diff_strategy import ColorDiffStrategy
from preprocessor.embeddings.strategies.keyframes_strategy import KeyframesStrategy
from preprocessor.embeddings.strategies.scene_changes_strategy import SceneChangesStrategy


class KeyframeStrategyFactory:
    @staticmethod
    def create(
        strategy_type: KeyframeStrategy,
        keyframe_interval: int = 1,
        frames_per_scene: int = 1,
    ) -> BaseKeyframeStrategy:
        if strategy_type == KeyframeStrategy.SCENE_CHANGES:
            return SceneChangesStrategy(frames_per_scene=frames_per_scene)
        if strategy_type == KeyframeStrategy.KEYFRAMES:
            return KeyframesStrategy(keyframe_interval=keyframe_interval)
        if strategy_type == KeyframeStrategy.COLOR_DIFF:
            return ColorDiffStrategy()
        raise ValueError(f"Unknown keyframe strategy: {strategy_type}")
