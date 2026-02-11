from preprocessor.config.enums import KeyframeStrategy
from preprocessor.services.video.strategies.base_strategy import BaseKeyframeStrategy
from preprocessor.services.video.strategies.scene_changes_strategy import SceneChangesStrategy


class KeyframeStrategyFactory:

    @staticmethod
    def create(strategy_type: KeyframeStrategy, frames_per_scene: int=1) -> BaseKeyframeStrategy:
        if strategy_type == KeyframeStrategy.SCENE_CHANGES:
            return SceneChangesStrategy(frames_per_scene=frames_per_scene)
        raise ValueError(f'Unknown keyframe strategy: {strategy_type}')
