from preprocessor.config.enums import KeyframeStrategy
from preprocessor.services.video.strategies.base_strategy import BaseKeyframeStrategy
from preprocessor.services.video.strategies.scene_changes_strategy import SceneChangesStrategy


class KeyframeStrategyFactory:
    @staticmethod
    def create(
        strategy_type: KeyframeStrategy,
        frames_per_scene: int = 1,
        scene_change_offset_seconds: float = 0.5,
    ) -> BaseKeyframeStrategy:
        if strategy_type == KeyframeStrategy.SCENE_CHANGES:
            return SceneChangesStrategy(
                frames_per_scene=frames_per_scene,
                scene_change_offset_seconds=scene_change_offset_seconds,
            )

        raise ValueError(f"Unknown strategy type: {strategy_type}")
