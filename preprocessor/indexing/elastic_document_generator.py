import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.episode_name_embedder import EpisodeNameEmbedder
from preprocessor.utils.console import console

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs


class ElasticDocumentGenerator(BaseProcessor):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=10,
            loglevel=logging.DEBUG,
        )

        self.transcription_jsons: Path = self._args["transcription_jsons"]
        self.embeddings_dir: Optional[Path] = self._args.get("embeddings_dir")
        self.scene_timestamps_dir: Optional[Path] = self._args.get("scene_timestamps_dir")
        self.character_detections_dir: Optional[Path] = self._args.get("character_detections_dir")
        self.object_detections_dir: Optional[Path] = self._args.get("object_detections_dir")
        self.output_dir: Path = self._args.get("output_dir", Path("/app/output_data/elastic_documents"))

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "transcription_jsons" not in args:
            raise ValueError("transcription_jsons is required")

    def _get_processing_items(self) -> List[ProcessingItem]:
        all_transcription_files = list(self.transcription_jsons.glob("**/*_segmented.json"))
        items = []

        for trans_file in all_transcription_files:
            items.append(self._create_transcription_processing_item(trans_file))

        return items

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:  # pylint: disable=too-many-locals
        base_name = item.metadata["base_name"]
        episode_info = self.episode_manager.parse_filename(item.input_path)

        outputs = []

        if episode_info:
            segments_file = self.episode_manager.build_episode_output_path(
                episode_info,
                f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.segments}",
                f"{base_name}_segments.jsonl",
            )
            outputs.append(OutputSpec(path=segments_file, required=True))

            trans_dir = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.transcriptions)
            sound_events_json = trans_dir / f"{base_name}_sound_events.json"
            if sound_events_json.exists():
                sound_events_file = self.episode_manager.build_episode_output_path(
                    episode_info,
                    f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.sound_events}",
                    f"{base_name}_sound_events.jsonl",
                )
                outputs.append(OutputSpec(path=sound_events_file, required=False))
        else:
            season_dir = item.input_path.parent.name
            outputs.append(
                OutputSpec(
                    path=self.output_dir / ELASTIC_SUBDIRS.segments / season_dir / f"{base_name}_segments.jsonl",
                    required=True,
                ),
            )

        if self.embeddings_dir and episode_info:
            episode_emb_dir = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.embeddings)
            text_emb_file = episode_emb_dir / "embeddings_text.json"
            video_emb_file = episode_emb_dir / "embeddings_video.json"

            if text_emb_file.exists():
                text_embeddings_file = self.episode_manager.build_episode_output_path(
                    episode_info,
                    f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.text_embeddings}",
                    f"{base_name}_text_embeddings.jsonl",
                )
                outputs.append(OutputSpec(path=text_embeddings_file, required=True))

            if video_emb_file.exists():
                video_frames_file = self.episode_manager.build_episode_output_path(
                    episode_info,
                    f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.video_frames}",
                    f"{base_name}_video_frames.jsonl",
                )
                outputs.append(OutputSpec(path=video_frames_file, required=True))

            episode_name_emb = EpisodeNameEmbedder.load_episode_name_embedding(
                episode_info.season,
                episode_info.relative_episode,
                output_dir=self.embeddings_dir,
            )
            if episode_name_emb:
                episode_name_file = self.episode_manager.build_episode_output_path(
                    episode_info,
                    f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.episode_names}",
                    f"{base_name}_episode_name.jsonl",
                )
                outputs.append(OutputSpec(path=episode_name_file, required=True))

            trans_dir = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.transcriptions)
            text_stats_file = trans_dir / f"{base_name}_text_stats.json"
            if text_stats_file.exists():
                text_stats_elastic_file = self.episode_manager.build_episode_output_path(
                    episode_info,
                    f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.text_statistics}",
                    f"{base_name}_text_statistics.jsonl",
                )
                outputs.append(OutputSpec(path=text_stats_elastic_file, required=True))

            full_episode_emb_file = episode_emb_dir / "embeddings_full_episode.json"
            if full_episode_emb_file.exists():
                full_episode_elastic_file = self.episode_manager.build_episode_output_path(
                    episode_info,
                    f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.full_episode_embeddings}",
                    f"{base_name}_full_episode_embedding.jsonl",
                )
                outputs.append(OutputSpec(path=full_episode_elastic_file, required=True))

            sound_event_emb_file = episode_emb_dir / "embeddings_sound_events.json"
            if sound_event_emb_file.exists():
                sound_event_elastic_file = self.episode_manager.build_episode_output_path(
                    episode_info,
                    f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.sound_event_embeddings}",
                    f"{base_name}_sound_event_embeddings.jsonl",
                )
                outputs.append(OutputSpec(path=sound_event_elastic_file, required=False))

        return outputs

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None: # pylint: disable=too-many-locals,too-many-statements
        trans_file = item.input_path
        base_name = item.metadata["base_name"]
        season_dir = trans_file.parent.name

        console.print(f"[cyan]Processing: {trans_file.name}[/cyan]")

        clean_transcription_file = trans_file.parent / trans_file.name.replace("_segmented.json", "_clean_transcription.json")
        if not clean_transcription_file.exists():
            self.logger.warning(f"Clean transcription not found: {clean_transcription_file}, skipping")
            return
        trans_file_for_segments = clean_transcription_file

        with open(trans_file_for_segments, "r", encoding="utf-8") as f:
            transcription_data = json.load(f)

        episode_info_dict = transcription_data.get("episode_info", {})
        season = episode_info_dict.get("season")
        episode_number = episode_info_dict.get("episode_number")

        if season is None or episode_number is None:
            console.print(f"[red]Missing episode info in {trans_file.name}[/red]")
            return

        episode_info = self.episode_manager.get_episode_by_season_and_relative(season, episode_number)
        if not episode_info:
            console.print(f"[red]Cannot find episode info for S{season:02d}E{episode_number:02d}[/red]")
            return

        episode_metadata = self.__build_episode_metadata(episode_info)
        episode_id = f"S{season:02d}E{episode_number:02d}"
        video_path = self.episode_manager.build_video_path_for_elastic(episode_info)

        scene_timestamps = self.__load_scene_timestamps(episode_info)
        character_detections = self.__load_character_detections(episode_info)
        object_detections = self.__load_object_detections(episode_info)

        if any("_segments.jsonl" in str(o.path) for o in missing_outputs):
            self.__generate_segments(
                transcription_data,
                episode_id,
                episode_metadata,
                video_path,
                scene_timestamps,
                season_dir,
                base_name,
            )

        trans_dir = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.transcriptions)
        sound_events_json = trans_dir / f"{base_name}_sound_events.json"
        if sound_events_json.exists() and any("_sound_events.jsonl" in str(o.path) for o in missing_outputs):
            with open(sound_events_json, "r", encoding="utf-8") as f:
                sound_events_data = json.load(f)

            self.__generate_sound_events(
                sound_events_data,
                episode_id,
                episode_metadata,
                video_path,
                scene_timestamps,
                episode_info,
                base_name,
            )

        if self.embeddings_dir:
            episode_emb_dir = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.embeddings)
            text_emb_file = episode_emb_dir / "embeddings_text.json"

            if text_emb_file.exists() and any("_text_embeddings.jsonl" in str(o.path) for o in missing_outputs):
                self.__generate_text_embeddings(
                    text_emb_file,
                    episode_id,
                    episode_metadata,
                    video_path,
                    episode_info,
                    base_name,
                )

            video_emb_file = episode_emb_dir / "embeddings_video.json"

            if video_emb_file.exists() and any("_video_frames.jsonl" in str(o.path) for o in missing_outputs):
                self.__generate_video_frames(
                    video_emb_file,
                    episode_id,
                    episode_metadata,
                    video_path,
                    scene_timestamps,
                    character_detections,
                    object_detections,
                    episode_info,
                    base_name,
                )

        episode_name_emb = EpisodeNameEmbedder.load_episode_name_embedding(
            season,
            episode_number,
            output_dir=self.embeddings_dir,
        )
        if episode_name_emb and any("_episode_name.jsonl" in str(o.path) for o in missing_outputs):
            self.__generate_episode_name_document(
                episode_name_emb,
                episode_id,
                episode_metadata,
                video_path,
                episode_info,
                base_name,
            )

        trans_dir = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.transcriptions)
        text_stats_file = trans_dir / f"{base_name}_text_stats.json"
        if text_stats_file.exists() and any("_text_statistics.jsonl" in str(o.path) for o in missing_outputs):
            self.__generate_text_statistics_document(
                text_stats_file,
                episode_id,
                episode_metadata,
                video_path,
                episode_info,
                base_name,
            )

        if self.embeddings_dir:
            episode_emb_dir = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.embeddings)
            full_episode_emb_file = episode_emb_dir / "embeddings_full_episode.json"

            if full_episode_emb_file.exists() and any("_full_episode_embedding.jsonl" in str(o.path) for o in missing_outputs):
                self.__generate_full_episode_embedding_document(
                    full_episode_emb_file,
                    episode_id,
                    episode_metadata,
                    video_path,
                    episode_info,
                    base_name,
                )

            sound_event_emb_file = episode_emb_dir / "embeddings_sound_events.json"

            if sound_event_emb_file.exists() and any("_sound_event_embeddings.jsonl" in str(o.path) for o in missing_outputs):
                self.__generate_sound_event_embeddings_document(
                    sound_event_emb_file,
                    episode_id,
                    episode_metadata,
                    video_path,
                    episode_info,
                    base_name,
                )

        console.print(f"[green]Completed: {trans_file.name}[/green]")

    def __build_episode_metadata(self, episode_info) -> Dict[str, Any]:
        metadata = self.episode_manager.get_metadata(episode_info)
        return {
            "season": episode_info.season,
            "episode_number": episode_info.relative_episode,
            "title": metadata.get("title"),
            "premiere_date": metadata.get("premiere_date"),
            "series_name": self.series_name,
            "viewership": metadata.get("viewership"),
        }

    def __load_scene_timestamps(self, episode_info) -> Optional[Dict[str, Any]]:
        return EpisodeManager.load_scene_timestamps(episode_info, self.scene_timestamps_dir, self.logger)

    def __load_character_detections(self, episode_info) -> Dict[int, List[Dict[str, Any]]]:
        if not self.character_detections_dir:
            return {}

        detection_file = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.character_detections) / "detections.json"

        if not detection_file.exists():
            return {}

        try:
            with open(detection_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            detections_dict = {}
            for detection in data.get("detections", []):
                frame_number = detection.get("frame_number")
                if frame_number is not None:
                    detections_dict[frame_number] = detection.get("characters", [])
                elif "frame" in detection:
                    frame_file = detection["frame"]
                    detections_dict[frame_file] = detection.get("characters", [])

            return detections_dict
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Error loading character detections: {e}")
            return {}

    def __load_object_detections(self, episode_info) -> Dict[str, List[Dict[str, Any]]]:
        if not self.object_detections_dir:
            return {}

        detection_file = self.episode_manager.get_episode_subdir(episode_info, settings.output_subdirs.object_detections) / "detections.json"

        if not detection_file.exists():
            return {}

        try:
            with open(detection_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            detections_dict = {}
            for frame_data in data.get("detections", []):
                frame_name = frame_data["frame_name"]
                detections_dict[frame_name] = frame_data.get("detections", [])

            return detections_dict
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Error loading object detections: {e}")
            return {}

    @staticmethod
    def __get_characters_for_frame(
        frame_identifier,
        character_detections: Dict,
    ) -> List[Dict[str, Any]]:
        characters = character_detections.get(frame_identifier, [])

        character_list = []
        for char in characters:
            char_data = {
                "name": char["name"],
                "confidence": char.get("confidence"),
            }

            if "emotion" in char:
                char_data["emotion"] = {
                    "label": char["emotion"]["label"],
                    "confidence": char["emotion"]["confidence"],
                }

            character_list.append(char_data)

        return character_list

    @staticmethod
    def __get_objects_for_frame(frame_name: str, object_detections: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        detections = object_detections.get(frame_name, [])
        objects_summary = {}
        for det in detections:
            class_name = det["class_name"]
            if class_name in objects_summary:
                objects_summary[class_name] += 1
            else:
                objects_summary[class_name] = 1

        return [{"class": cls, "count": cnt} for cls, cnt in objects_summary.items()]

    @staticmethod
    def __find_scene_for_timestamp(timestamp: float, scene_timestamps: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not scene_timestamps or "scenes" not in scene_timestamps:
            return None

        scenes = scene_timestamps["scenes"]
        for scene in scenes:
            start_time = scene["start"]["seconds"]
            end_time = scene["end"]["seconds"]

            if start_time <= timestamp < end_time:
                return {
                    "scene_number": scene["scene_number"],
                    "scene_start_time": start_time,
                    "scene_end_time": end_time,
                    "scene_start_frame": scene["start"]["frame"],
                    "scene_end_frame": scene["end"]["frame"],
                }

        return None

    def __generate_segments(  # pylint: disable=too-many-locals
        self,
        transcription_data: Dict[str, Any],
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        scene_timestamps: Optional[Dict[str, Any]],
        season_dir: str,
        base_name: str,
    ) -> None:
        segments = transcription_data.get("segments", [])
        if not segments:
            return

        season = episode_metadata.get("season")
        episode = episode_metadata.get("episode_number")
        episode_info = self.episode_manager.get_episode_by_season_and_relative(season, episode)

        if episode_info:
            output_file = self.episode_manager.build_episode_output_path(
                episode_info,
                f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.segments}",
                f"{base_name}_segments.jsonl",
            )
        else:
            output_file = self.output_dir / ELASTIC_SUBDIRS.segments / season_dir / f"{base_name}_segments.jsonl"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments):
                if "text" not in segment:
                    continue

                words = segment.get("words", [])
                if not words:
                    continue

                start_time = words[0].get("start", 0.0)
                end_time = words[-1].get("end", 0.0)
                speaker = words[0].get("speaker_id", "unknown")

                scene_info = self.__find_scene_for_timestamp(start_time, scene_timestamps)

                doc = {
                    "episode_id": episode_id,
                    "episode_metadata": episode_metadata,
                    "segment_id": i,
                    "text": segment.get("text", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "speaker": speaker,
                    "video_path": video_path,
                }

                if scene_info:
                    doc["scene_info"] = scene_info

                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated {len(segments)} segment documents → {output_file.name}[/green]")

    def __generate_sound_events(
        self,
        sound_events_data: Dict[str, Any],
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        scene_timestamps: Optional[Dict[str, Any]],
        episode_info,
        base_name: str,
    ) -> None:
        segments = sound_events_data.get("segments", [])
        if not segments:
            return

        output_file = self.episode_manager.build_episode_output_path(
            episode_info,
            f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.sound_events}",
            f"{base_name}_sound_events.jsonl",
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments):
                if "text" not in segment:
                    continue

                words = segment.get("words", [])
                if not words:
                    start_time = segment.get("start", 0.0)
                    end_time = segment.get("end", 0.0)
                else:
                    start_time = words[0].get("start", 0.0)
                    end_time = words[-1].get("end", 0.0)

                scene_info = self.__find_scene_for_timestamp(start_time, scene_timestamps)

                doc = {
                    "episode_id": episode_id,
                    "episode_metadata": episode_metadata,
                    "segment_id": i,
                    "text": segment.get("text", ""),
                    "sound_type": segment.get("sound_type", "sound"),
                    "start_time": start_time,
                    "end_time": end_time,
                    "video_path": video_path,
                }

                if scene_info:
                    doc["scene_info"] = scene_info

                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated {len(segments)} sound event documents → {output_file.name}[/green]")

    def __generate_text_embeddings(
        self,
        text_emb_file: Path,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        episode_info,
        base_name: str,
    ) -> None:
        with open(text_emb_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        text_embeddings = data.get("text_embeddings", [])
        if not text_embeddings:
            return

        output_file = self.episode_manager.build_episode_output_path(
            episode_info,
            f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.text_embeddings}",
            f"{base_name}_text_embeddings.jsonl",
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for i, emb in enumerate(text_embeddings):
                segment_range = emb.get("segment_range", [])
                text = emb.get("text", "")
                embedding = emb.get("embedding", [])

                if not embedding:
                    continue

                doc = {
                    "episode_id": episode_id,
                    "episode_metadata": episode_metadata,
                    "embedding_id": i,
                    "segment_range": segment_range,
                    "text": text,
                    "text_embedding": embedding,
                    "video_path": video_path,
                }

                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated {len(text_embeddings)} text embedding documents → {output_file.name}[/green]")

    def __generate_video_frames( # pylint: disable=too-many-locals
        self,
        video_emb_file: Path,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        scene_timestamps: Optional[Dict[str, Any]],
        character_detections: Dict[str, List[Dict[str, Any]]],
        object_detections: Dict[str, List[Dict[str, Any]]],
        episode_info,
        base_name: str,
    ) -> None:
        with open(video_emb_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_embeddings = data.get("video_embeddings", [])
        if not video_embeddings:
            return

        output_file = self.episode_manager.build_episode_output_path(
            episode_info,
            f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.video_frames}",
            f"{base_name}_video_frames.jsonl",
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for emb in video_embeddings:
                frame_number = emb.get("frame_number")
                timestamp = emb.get("timestamp")
                embedding = emb.get("embedding")

                if embedding is None or timestamp is None:
                    continue

                scene_info = self.__find_scene_for_timestamp(timestamp, scene_timestamps)

                perceptual_hash = emb.get("perceptual_hash")
                frame_path = emb.get("frame_path", f"frame_{frame_number:06d}.jpg" if frame_number is not None else "")

                doc = {
                    "episode_id": episode_id,
                    "episode_metadata": episode_metadata,
                    "frame_number": frame_number,
                    "timestamp": timestamp,
                    "frame_type": emb.get("type", "unknown"),
                    "video_path": video_path,
                    "video_embedding": embedding,
                }

                if frame_number is not None:
                    characters = self.__get_characters_for_frame(frame_number, character_detections)
                    if characters:
                        doc["character_appearances"] = characters

                if frame_path:
                    frame_name = Path(frame_path).name if isinstance(frame_path, str) else frame_path
                    objects = self.__get_objects_for_frame(frame_name, object_detections)
                    if objects:
                        doc["detected_objects"] = objects

                if perceptual_hash:
                    doc["perceptual_hash"] = perceptual_hash
                    try:
                        doc["perceptual_hash_int"] = int(perceptual_hash, 16)
                    except (ValueError, TypeError):
                        pass

                if "scene_number" in emb:
                    doc["scene_number"] = emb["scene_number"]

                if scene_info:
                    doc["scene_info"] = scene_info

                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated {len(video_embeddings)} video frame documents → {output_file.name}[/green]")

    def __generate_episode_name_document(
        self,
        episode_name_emb: Dict[str, Any],
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        episode_info,
        base_name: str,
    ) -> None:
        output_file = self.episode_manager.build_episode_output_path(
            episode_info,
            f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.episode_names}",
            f"{base_name}_episode_name.jsonl",
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        title_embedding = episode_name_emb.get("title_embedding", [])
        if not title_embedding:
            return

        doc = {
            "episode_id": episode_id,
            "episode_metadata": episode_metadata,
            "title": episode_name_emb.get("title", ""),
            "title_embedding": title_embedding,
            "video_path": video_path,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated episode name document → {output_file.name}[/green]")

    def __generate_text_statistics_document(
        self,
        text_stats_file: Path,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        episode_info,
        base_name: str,
    ) -> None:
        with open(text_stats_file, "r", encoding="utf-8") as f:
            stats_data = json.load(f)

        basic_stats = stats_data.get("basic_statistics", {})
        advanced_stats = stats_data.get("advanced_statistics", {})

        if not basic_stats:
            return

        output_file = self.episode_manager.build_episode_output_path(
            episode_info,
            f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.text_statistics}",
            f"{base_name}_text_statistics.jsonl",
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        doc = {
            "episode_id": episode_id,
            "episode_metadata": episode_metadata,
            "video_path": video_path,
            "language": stats_data.get("metadata", {}).get("language", "pl"),
            "analyzed_at": stats_data.get("metadata", {}).get("analyzed_at"),
            "basic_statistics": basic_stats,
            "advanced_statistics": advanced_stats,
            "word_frequency": stats_data.get("word_frequency", [])[:20],
            "bigrams": stats_data.get("bigrams", [])[:10],
            "trigrams": stats_data.get("trigrams", [])[:10],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated text statistics document → {output_file.name}[/green]")

    def __generate_full_episode_embedding_document(
        self,
        full_episode_emb_file: Path,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        episode_info,
        base_name: str,
    ) -> None:
        with open(full_episode_emb_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        full_episode_embedding_data = data.get("full_episode_embedding", {})
        if not full_episode_embedding_data or "embedding" not in full_episode_embedding_data:
            return

        output_file = self.episode_manager.build_episode_output_path(
            episode_info,
            f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.full_episode_embeddings}",
            f"{base_name}_full_episode_embedding.jsonl",
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        doc = {
            "episode_id": episode_id,
            "episode_metadata": episode_metadata,
            "full_transcript": full_episode_embedding_data.get("text", ""),
            "transcript_length": full_episode_embedding_data.get("transcript_length", 0),
            "full_episode_embedding": full_episode_embedding_data.get("embedding", []),
            "video_path": video_path,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated full episode embedding document → {output_file.name}[/green]")

    def __generate_sound_event_embeddings_document(
        self,
        sound_event_emb_file: Path,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        episode_info,
        base_name: str,
    ) -> None:
        with open(sound_event_emb_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        sound_event_embeddings = data.get("sound_event_embeddings", [])
        if not sound_event_embeddings:
            return

        output_file = self.episode_manager.build_episode_output_path(
            episode_info,
            f"{settings.output_subdirs.elastic_documents}/{ELASTIC_SUBDIRS.sound_event_embeddings}",
            f"{base_name}_sound_event_embeddings.jsonl",
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for i, emb in enumerate(sound_event_embeddings):
                segment_range = emb.get("segment_range", [])
                text = emb.get("text", "")
                embedding = emb.get("embedding", [])
                sound_types = emb.get("sound_types", [])
                start_time = emb.get("start_time", 0.0)
                end_time = emb.get("end_time", 0.0)

                if not embedding:
                    continue

                doc = {
                    "episode_id": episode_id,
                    "episode_metadata": episode_metadata,
                    "embedding_id": i,
                    "segment_range": segment_range,
                    "text": text,
                    "sound_types": sound_types,
                    "start_time": start_time,
                    "end_time": end_time,
                    "sound_event_embedding": embedding,
                    "video_path": video_path,
                }

                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        console.print(f"[green]Generated {len(sound_event_embeddings)} sound event embedding documents → {output_file.name}[/green]")
