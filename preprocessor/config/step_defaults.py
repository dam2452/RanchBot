from typing import Dict

from preprocessor.config.step_configs import (
    ArchiveConfig,
    CharacterDetectionConfig,
    DocumentGenerationConfig,
    ElasticsearchConfig,
    EmotionDetectionConfig,
    FaceClusteringConfig,
    FrameExportConfig,
    ImageHashConfig,
    ObjectDetectionConfig,
    SceneDetectionConfig,
    SoundSeparationConfig,
    TextAnalysisConfig,
    TextEmbeddingConfig,
    TranscodeConfig,
    VideoEmbeddingConfig,
    WhisperTranscriptionConfig,
)


class DefaultConfigFactory:
    @staticmethod
    def get_configs(series_name: str) -> Dict[str, object]:
        return {
            'transcode': TranscodeConfig(
                max_bitrate_file_size_mb=50.0,
                max_bitrate_duration_seconds=100.0,
                keyframe_interval_seconds=0.5,
                min_upscale_bitrate_ratio=0.52,
            ),
            'transcribe': WhisperTranscriptionConfig(
                model='large-v3-turbo',
                language='pl',
                device='cuda',
                beam_size=5,
                temperature=0.0,
            ),
            'separate_sounds': SoundSeparationConfig(),
            'analyze_text': TextAnalysisConfig(language='pl'),
            'detect_scenes': SceneDetectionConfig(threshold=0.5, min_scene_len=10),
            'export_frames': FrameExportConfig(frames_per_scene=3),
            'text_embeddings': TextEmbeddingConfig(
                model_name='Qwen/Qwen3-VL-Embedding-8B',
                batch_size=8,
                device='cuda',
                text_sentences_per_chunk=5,
                text_chunk_overlap=1,
            ),
            'image_hashing': ImageHashConfig(batch_size=32),
            'video_embeddings': VideoEmbeddingConfig(
                model_name='Qwen/Qwen3-VL-Embedding-8B',
                batch_size=8,
                device='cuda',
            ),
            'character_detection': CharacterDetectionConfig(threshold=0.7),
            'emotion_detection': EmotionDetectionConfig(),
            'face_clustering': FaceClusteringConfig(),
            'object_detection': ObjectDetectionConfig(),
            'generate_elastic_documents': DocumentGenerationConfig(generate_segments=True),
            'generate_archives': ArchiveConfig(),
            'index': ElasticsearchConfig(
                index_name=f'{series_name}_clips',
                host='localhost:9200',
                dry_run=False,
                append=False,
            ),
        }
