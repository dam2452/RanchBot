import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.constants import ELASTIC_DOC_TYPES
from preprocessor.config.step_configs import DocumentGenerationConfig
from preprocessor.core.artifacts import (
    ElasticDocuments,
    EmbeddingCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import FileOutput
from preprocessor.core.temp_files import StepTempFile
from preprocessor.services.episodes.types import EpisodeInfo
from preprocessor.services.io.files import FileOperations


class DocumentGeneratorStep(
    PipelineStep[EmbeddingCollection, ElasticDocuments, DocumentGenerationConfig],
):
    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[EmbeddingCollection], context: ExecutionContext,
    ) -> List[ElasticDocuments]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: EmbeddingCollection, context: ExecutionContext,
    ) -> ElasticDocuments:
        episode_info = input_data.episode_info
        episode_id = input_data.episode_id
        episode_metadata = self.__build_episode_metadata(episode_info, context)
        video_path = self.__build_video_path(episode_info, context)

        scene_data = self.__load_optional(context, "scene_detections", episode_info)
        char_data = self.__load_optional(context, "detections/characters", episode_info)
        emotion_data = self.__load_optional(context, "detections/emotions", episode_info)
        object_data = self.__load_optional(context, "detections/objects", episode_info)

        char_by_frame = self.__index_characters_by_frame(char_data, emotion_data)
        objects_by_frame = self.__index_objects_by_frame(object_data)

        total_docs = sum([
            self.__write_text_segments(context, episode_info, episode_id, episode_metadata, video_path, scene_data),
            self.__write_sound_events(context, episode_info, episode_id, episode_metadata, video_path, scene_data),
            self.__write_text_embeddings(context, episode_info, episode_id, episode_metadata, video_path),
            self.__write_video_frames(context, episode_info, episode_id, episode_metadata, video_path, scene_data, char_by_frame, objects_by_frame),
            self.__write_episode_name(context, episode_info, episode_id, episode_metadata, video_path),
            self.__write_text_statistics(context, episode_info, episode_id, episode_metadata, video_path),
            self.__write_full_episode_embedding(context, episode_info, episode_id, episode_metadata, video_path),
            self.__write_sound_event_embeddings(context, episode_info, episode_id, episode_metadata, video_path),
        ])

        context.logger.info(f"Generated {total_docs} documents for {episode_id}")

        return ElasticDocuments(
            episode_id=episode_id,
            episode_info=episode_info,
            path=self._get_cache_path(input_data, context),
            document_count=total_docs,
        )

    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern=f"{{season}}/{{episode}}_{suffix}.jsonl",
                subdir=f"elastic_documents/{folder}",
                min_size_bytes=10,
            )
            for folder, suffix in ELASTIC_DOC_TYPES
        ]

    def _get_cache_path(
        self, input_data: EmbeddingCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0, context, self.__path_vars(input_data.episode_info),
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: EmbeddingCollection, context: ExecutionContext,
    ) -> ElasticDocuments:
        return ElasticDocuments(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=cache_path,
            document_count=0,
        )

    @staticmethod
    def __path_vars(episode_info: EpisodeInfo) -> Dict[str, str]:
        return {
            "season": episode_info.season_code(),
            "episode": episode_info.episode_code(),
        }

    @staticmethod
    def __input_path(
        context: ExecutionContext, subdir: str, episode_info: EpisodeInfo,
    ) -> Path:
        return (
            context.base_output_dir
            / subdir
            / episode_info.season_code()
            / f"{episode_info.episode_code()}.json"
        )

    def __output_path(
        self, context: ExecutionContext, episode_info: EpisodeInfo, descriptor_index: int,
    ) -> Path:
        return self._resolve_output_path(
            descriptor_index, context, self.__path_vars(episode_info),
        )

    def __load_optional(
        self, context: ExecutionContext, subdir: str, episode_info: EpisodeInfo,
    ) -> Optional[Dict[str, Any]]:
        path = self.__input_path(context, subdir, episode_info)
        return FileOperations.load_json(path) if path.exists() else None

    @staticmethod
    def __build_episode_metadata(
        episode_info: EpisodeInfo, context: ExecutionContext,
    ) -> Dict[str, Any]:
        return {
            "season": episode_info.season,
            "episode_number": episode_info.relative_episode,
            "title": episode_info.title,
            "premiere_date": episode_info.premiere_date,
            "series_name": context.series_name,
            "viewership": episode_info.viewership,
        }

    @staticmethod
    def __build_video_path(episode_info: EpisodeInfo, context: ExecutionContext) -> str:
        filename = f"{context.series_name}_{episode_info.episode_code()}.mp4"
        return f"bot/{context.series_name.upper()}-WIDEO/{episode_info.season_code()}/{filename}"

    @staticmethod
    def __find_scene(
        timestamp: float, scene_data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not scene_data:
            return None
        for scene in scene_data.get("scenes", []):
            start = scene["start"]["seconds"]
            end = scene["end"]["seconds"]
            if start is None or end is None:
                continue
            if start <= timestamp < end:
                return {
                    "scene_number": scene["scene_number"],
                    "scene_start_time": start,
                    "scene_end_time": end,
                    "scene_start_frame": scene["start"]["frame"],
                    "scene_end_frame": scene["end"]["frame"],
                }
        return None

    @staticmethod
    def __index_characters_by_frame(
        char_data: Optional[Dict[str, Any]],
        emotion_data: Optional[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not char_data:
            return {}

        emotion_by_frame: Dict[str, Dict[str, Dict[str, Any]]] = {}
        if emotion_data:
            for det in emotion_data.get("detections", []):
                frame = det["frame"]
                emotion_by_frame[frame] = {
                    face["name"]: face.get("emotion")
                    for face in det.get("faces", [])
                    if face.get("emotion")
                }

        result: Dict[str, List[Dict[str, Any]]] = {}
        for det in char_data.get("detections", []):
            frame = det["frame"]
            faces = []
            for face in det.get("faces", []):
                name = face["name"]
                entry: Dict[str, Any] = {"name": name, "confidence": face.get("confidence")}
                emotion = emotion_by_frame.get(frame, {}).get(name)
                if emotion:
                    entry["emotion"] = {
                        "label": emotion["label"],
                        "confidence": emotion["confidence"],
                    }
                faces.append(entry)
            if faces:
                result[frame] = faces
        return result

    @staticmethod
    def __index_objects_by_frame(
        object_data: Optional[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not object_data:
            return {}
        result: Dict[str, List[Dict[str, Any]]] = {}
        for det in object_data.get("detections", []):
            frame = det["frame"]
            counts: Dict[str, int] = {}
            for obj in det.get("objects", []):
                cls = obj["class_name"]
                counts[cls] = counts.get(cls, 0) + 1
            if counts:
                result[frame] = [{"class": k, "count": v} for k, v in counts.items()]
        return result

    @staticmethod
    def __write_ndjson(output_path: Path, docs: List[Dict[str, Any]]) -> int:
        if not docs:
            return 0
        with StepTempFile(output_path) as tmp:
            with open(tmp, "w", encoding="utf-8") as f:
                for doc in docs:
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        return len(docs)

    def __write_text_segments(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        scene_data: Optional[Dict[str, Any]],
    ) -> int:
        clean_data = self.__load_optional(context, "transcriptions/clean", episode_info)
        if not clean_data:
            return 0

        docs = []
        for i, seg in enumerate(clean_data.get("segments", [])):
            text = seg.get("text", "").strip()
            if not text:
                continue
            words = seg.get("words", [])
            start = (words[0].get("start") or seg.get("start", 0.0)) if words else seg.get("start", 0.0)
            end = (words[-1].get("end") or seg.get("end", 0.0)) if words else seg.get("end", 0.0)
            speaker = (words[0].get("speaker_id") or seg.get("speaker", "unknown")) if words else seg.get("speaker", "unknown")
            doc: Dict[str, Any] = {
                "episode_id": episode_id,
                "episode_metadata": episode_metadata,
                "segment_id": i,
                "text": text,
                "start_time": start,
                "end_time": end,
                "speaker": speaker,
                "video_path": video_path,
            }
            scene_info = self.__find_scene(start, scene_data)
            if scene_info:
                doc["scene_info"] = scene_info
            docs.append(doc)

        return self.__write_ndjson(self.__output_path(context, episode_info, 0), docs)

    def __write_sound_events(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        scene_data: Optional[Dict[str, Any]],
    ) -> int:
        sound_data = self.__load_optional(context, "transcriptions/sound_events", episode_info)
        if not sound_data:
            return 0

        docs = []
        for i, seg in enumerate(sound_data.get("segments", [])):
            if "text" not in seg:
                continue
            words = seg.get("words", [])
            start = (words[0].get("start") or seg.get("start", 0.0)) if words else seg.get("start", 0.0)
            end = (words[-1].get("end") or seg.get("end", 0.0)) if words else seg.get("end", 0.0)
            doc: Dict[str, Any] = {
                "episode_id": episode_id,
                "episode_metadata": episode_metadata,
                "segment_id": i,
                "text": seg.get("text", ""),
                "sound_type": seg.get("sound_type", "sound"),
                "start_time": start,
                "end_time": end,
                "video_path": video_path,
            }
            scene_info = self.__find_scene(start, scene_data)
            if scene_info:
                doc["scene_info"] = scene_info
            docs.append(doc)

        return self.__write_ndjson(self.__output_path(context, episode_info, 1), docs)

    def __write_text_embeddings(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
    ) -> int:
        emb_data = self.__load_optional(context, "embeddings/text", episode_info)
        if not emb_data:
            return 0

        docs = []
        for i, emb in enumerate(emb_data.get("text_embeddings", [])):
            embedding = emb.get("embedding", [])
            if not embedding:
                continue
            segment_range = emb.get("segment_range", [])
            docs.append({
                "episode_id": episode_id,
                "episode_metadata": episode_metadata,
                "embedding_id": i,
                "segment_range": segment_range[0] if segment_range else 0,
                "text": emb.get("text", ""),
                "text_embedding": embedding,
                "video_path": video_path,
            })

        return self.__write_ndjson(self.__output_path(context, episode_info, 2), docs)

    def __write_video_frames(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        scene_data: Optional[Dict[str, Any]],
        char_by_frame: Dict[str, List[Dict[str, Any]]],
        objects_by_frame: Dict[str, List[Dict[str, Any]]],
    ) -> int:
        emb_data = self.__load_optional(context, "embeddings/vision", episode_info)
        if not emb_data:
            return 0

        docs = []
        for emb in emb_data.get("video_embeddings", []):
            embedding = emb.get("embedding")
            timestamp = emb.get("timestamp")
            if embedding is None or timestamp is None:
                continue

            frame_path = emb.get("frame_path", "")
            frame_name = Path(frame_path).name if frame_path else ""

            doc: Dict[str, Any] = {
                "episode_id": episode_id,
                "episode_metadata": episode_metadata,
                "frame_number": emb.get("frame_number"),
                "timestamp": timestamp,
                "frame_type": emb.get("type", "unknown"),
                "video_path": video_path,
                "video_embedding": embedding,
            }

            if frame_name and frame_name in char_by_frame:
                doc["character_appearances"] = char_by_frame[frame_name]
            if frame_name and frame_name in objects_by_frame:
                doc["detected_objects"] = objects_by_frame[frame_name]

            perceptual_hash = emb.get("perceptual_hash")
            if perceptual_hash:
                doc["perceptual_hash"] = perceptual_hash
                try:
                    doc["perceptual_hash_int"] = int(perceptual_hash, 16)
                except (ValueError, TypeError):
                    pass

            if "scene_number" in emb:
                doc["scene_number"] = emb["scene_number"]

            scene_info = self.__find_scene(timestamp, scene_data)
            if scene_info:
                doc["scene_info"] = scene_info

            docs.append(doc)

        return self.__write_ndjson(self.__output_path(context, episode_info, 3), docs)

    def __write_episode_name(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
    ) -> int:
        emb_data = self.__load_optional(context, "embeddings/episode_names", episode_info)
        if not emb_data or not emb_data.get("title_embedding"):
            return 0

        doc: Dict[str, Any] = {
            "episode_id": episode_id,
            "episode_metadata": episode_metadata,
            "title": emb_data.get("title", ""),
            "title_embedding": emb_data.get("title_embedding", []),
            "video_path": video_path,
        }
        return self.__write_ndjson(self.__output_path(context, episode_info, 4), [doc])

    def __write_text_statistics(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
    ) -> int:
        stats_data = self.__load_optional(context, "text_analysis", episode_info)
        if not stats_data or not stats_data.get("basic_statistics"):
            return 0

        doc: Dict[str, Any] = {
            "episode_id": episode_id,
            "episode_metadata": episode_metadata,
            "video_path": video_path,
            "language": stats_data.get("metadata", {}).get("language", "pl"),
            "analyzed_at": stats_data.get("metadata", {}).get("analyzed_at"),
            "basic_statistics": stats_data.get("basic_statistics", {}),
            "advanced_statistics": stats_data.get("advanced_statistics", {}),
            "word_frequency": stats_data.get("word_frequency", [])[:20],
            "bigrams": stats_data.get("bigrams", [])[:10],
            "trigrams": stats_data.get("trigrams", [])[:10],
        }
        return self.__write_ndjson(self.__output_path(context, episode_info, 5), [doc])

    def __write_full_episode_embedding(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
    ) -> int:
        emb_data = self.__load_optional(context, "embeddings/full_episode", episode_info)
        if not emb_data:
            return 0

        full_emb = emb_data.get("full_episode_embedding", {})
        if not full_emb or "embedding" not in full_emb:
            return 0

        doc: Dict[str, Any] = {
            "episode_id": episode_id,
            "episode_metadata": episode_metadata,
            "full_transcript": full_emb.get("text", ""),
            "transcript_length": full_emb.get("transcript_length", 0),
            "full_episode_embedding": full_emb.get("embedding", []),
            "video_path": video_path,
        }
        return self.__write_ndjson(self.__output_path(context, episode_info, 6), [doc])

    def __write_sound_event_embeddings(
        self,
        context: ExecutionContext,
        episode_info: EpisodeInfo,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
    ) -> int:
        emb_data = self.__load_optional(context, "embeddings/sound_events", episode_info)
        if not emb_data:
            return 0

        docs = []
        for i, emb in enumerate(emb_data.get("sound_event_embeddings", [])):
            embedding = emb.get("embedding", [])
            if not embedding:
                continue
            segment_range = emb.get("segment_range", [])
            if isinstance(segment_range, list) and len(segment_range) == 2:
                segment_range = {"gte": segment_range[0], "lte": segment_range[1]}
            docs.append({
                "episode_id": episode_id,
                "episode_metadata": episode_metadata,
                "embedding_id": i,
                "segment_range": segment_range,
                "text": emb.get("text", ""),
                "sound_types": emb.get("sound_types", []),
                "start_time": emb.get("start_time", 0.0),
                "end_time": emb.get("end_time", 0.0),
                "sound_event_embedding": embedding,
                "video_path": video_path,
            })

        return self.__write_ndjson(self.__output_path(context, episode_info, 7), docs)
