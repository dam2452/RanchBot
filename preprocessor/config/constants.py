SUPPORTED_VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm')
DEFAULT_VIDEO_EXTENSION = '.mp4'

FILE_SUFFIXES = {
    'segmented': '_segmented',
    'text_segments': '_text_segments',
    'simple': '_simple',
    'clean': '_clean_transcription',
    'clean_alt': '_clean',
    'scenes': '_scenes',
    'sound_events': '_sound_events',
    'text_stats': '_text_stats',
    'embeddings_text': '_embeddings_text',
    'embeddings_video': '_embeddings_video',
    'embeddings_full': 'embeddings_full_episode',
    'embeddings_sound': 'embeddings_sound_events',
    'episode_name': 'episode_name_embedding',
    'image_hashes': '_image_hashes',
    'detections': 'detections',
    'character_detections': '_character_detections',
}

FILE_EXTENSIONS = {
    'json': '.json',
    'jsonl': '.jsonl',
    'txt': '.txt',
    'srt': '.srt',
    'mp4': '.mp4',
    'jpg': '.jpg',
}

OUTPUT_FILE_NAMES = {
    'detections': 'detections.json',
    'episode_embedding': 'episode_name_embedding.json',
    'embeddings_text': 'embeddings_text.json',
}

OUTPUT_FILE_PATTERNS = {
    'frame': '*_frame_*.jpg',
    'scenes_suffix': '_scenes.json',
}

class EpisodesDataKeys:
    EPISODES = 'episodes'
    SEASONS = 'seasons'
    SEASON_NUMBER = 'season'

class EpisodeMetadataKeys:
    EPISODE_NUMBER = 'episode_number'
    PREMIERE_DATE = 'premiere_date'
    TITLE = 'title'
    VIEWERSHIP = 'viewership'

class FfprobeKeys:
    FORMAT = 'format'
    STREAMS = 'streams'
