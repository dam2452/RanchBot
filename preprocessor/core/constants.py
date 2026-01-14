SUPPORTED_VIDEO_EXTENSIONS = (
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".flv",
    ".wmv",
    ".webm",
)

OUTPUT_FILE_NAMES = {
    "detections": "detections.json",
    "episode_embedding": "episode_name_embedding.json",
    "embeddings_text": "embeddings_text.json",
    "validation_report": "validation_report.json",
}

OUTPUT_FILE_PATTERNS = {
    "frame": "frame_*.jpg",
    "scenes_suffix": "_scenes.json",
}
