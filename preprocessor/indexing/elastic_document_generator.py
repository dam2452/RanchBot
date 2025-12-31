import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.episode_name_embedder import EpisodeNameEmbedder
from preprocessor.utils.console import console


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

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        base_name = item.metadata["base_name"]
        season_dir = item.input_path.parent.name

        outputs = [
            OutputSpec(
                path=self.output_dir / "segments" / season_dir / f"{base_name}_segments.jsonl",
                required=True,
            ),
        ]

        if self.embeddings_dir:
            episode_info = self.episode_manager.parse_filename(item.input_path)
            if episode_info:
                episode_emb_dir = self.embeddings_dir / f"S{episode_info.season:02d}" / f"E{episode_info.relative_episode:02d}"
                text_emb_file = episode_emb_dir / "embeddings_text.json"
                video_emb_file = episode_emb_dir / "embeddings_video.json"
            else:
                text_emb_file = self.embeddings_dir / f"{base_name}_text.json"
                video_emb_file = self.embeddings_dir / f"{base_name}_video.json"

            if text_emb_file.exists():
                outputs.append(
                    OutputSpec(
                        path=self.output_dir / "text_embeddings" / season_dir / f"{base_name}_text_embeddings.jsonl",
                        required=True,
                    ),
                )

            if video_emb_file.exists():
                outputs.append(
                    OutputSpec(
                        path=self.output_dir / "video_embeddings" / season_dir / f"{base_name}_video_embeddings.jsonl",
                        required=True,
                    ),
                )

            if episode_info:
                episode_name_emb = EpisodeNameEmbedder.load_episode_name_embedding(
                    episode_info.season,
                    episode_info.relative_episode,
                )
                if episode_name_emb:
                    outputs.append(
                        OutputSpec(
                            path=self.output_dir / "episode_names" / season_dir / f"{base_name}_episode_name.jsonl",
                            required=True,
                        ),
                    )

        return outputs

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None: # pylint: disable=too-many-locals
        trans_file = item.input_path
        base_name = item.metadata["base_name"]
        season_dir = trans_file.parent.name

        console.print(f"[cyan]Processing: {trans_file.name}[/cyan]")

        with open(trans_file, "r", encoding="utf-8") as f:
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

        if self.embeddings_dir:
            episode_emb_dir = self.embeddings_dir / f"S{season:02d}" / f"E{episode_number:02d}"
            text_emb_file = episode_emb_dir / "embeddings_text.json"
            if not text_emb_file.exists():
                text_emb_file = self.embeddings_dir / f"{base_name}_text.json"

            if text_emb_file.exists() and any("_text_embeddings.jsonl" in str(o.path) for o in missing_outputs):
                self.__generate_text_embeddings(
                    text_emb_file,
                    episode_id,
                    episode_metadata,
                    video_path,
                    season_dir,
                    base_name,
                )

            video_emb_file = episode_emb_dir / "embeddings_video.json"
            if not video_emb_file.exists():
                video_emb_file = self.embeddings_dir / f"{base_name}_video.json"

            if video_emb_file.exists() and any("_video_embeddings.jsonl" in str(o.path) for o in missing_outputs):
                self.__generate_video_embeddings(
                    video_emb_file,
                    episode_id,
                    episode_metadata,
                    video_path,
                    scene_timestamps,
                    character_detections,
                    season_dir,
                    base_name,
                )

        episode_name_emb = EpisodeNameEmbedder.load_episode_name_embedding(season, episode_number)
        if episode_name_emb and any("_episode_name.jsonl" in str(o.path) for o in missing_outputs):
            self.__generate_episode_name_document(
                episode_name_emb,
                episode_id,
                episode_metadata,
                video_path,
                season_dir,
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

    def __load_character_detections(self, episode_info) -> Dict[str, List[Dict[str, Any]]]:
        if not self.character_detections_dir:
            return {}

        season = episode_info.season
        episode = episode_info.relative_episode
        detection_file = self.character_detections_dir / f"S{season:02d}" / f"E{episode:02d}" / "detections.json"

        if not detection_file.exists():
            return {}

        try:
            with open(detection_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            detections_dict = {}
            for detection in data.get("detections", []):
                frame_path = detection["frame"]
                detections_dict[frame_path] = detection["characters"]

            return detections_dict
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Error loading character detections: {e}")
            return {}

    @staticmethod
    def __get_characters_for_frame(frame_path: str, character_detections: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        characters = character_detections.get(frame_path, [])
        return [char["name"] for char in characters]

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

    def __generate_segments(
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

        output_file = self.output_dir / "segments" / season_dir / f"{base_name}_segments.jsonl"
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

    def __generate_text_embeddings(
        self,
        text_emb_file: Path,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        season_dir: str,
        base_name: str,
    ) -> None:
        with open(text_emb_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        text_embeddings = data.get("text_embeddings", [])
        if not text_embeddings:
            return

        output_file = self.output_dir / "text_embeddings" / season_dir / f"{base_name}_text_embeddings.jsonl"
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

    def __generate_video_embeddings( # pylint: disable=too-many-locals
        self,
        video_emb_file: Path,
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        scene_timestamps: Optional[Dict[str, Any]],
        character_detections: Dict[str, List[Dict[str, Any]]],
        season_dir: str,
        base_name: str,
    ) -> None:
        with open(video_emb_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_embeddings = data.get("video_embeddings", [])
        if not video_embeddings:
            return

        output_file = self.output_dir / "video_embeddings" / season_dir / f"{base_name}_video_embeddings.jsonl"
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
                frame_path = emb.get("frame_path", "")

                doc = {
                    "episode_id": episode_id,
                    "episode_metadata": episode_metadata,
                    "frame_number": frame_number,
                    "timestamp": timestamp,
                    "frame_type": emb.get("type", "unknown"),
                    "video_path": video_path,
                    "video_embedding": embedding,
                }

                if frame_path:
                    characters = self.__get_characters_for_frame(frame_path, character_detections)
                    if characters:
                        doc["character_appearances"] = characters

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

        console.print(f"[green]Generated {len(video_embeddings)} video embedding documents → {output_file.name}[/green]")

    def __generate_episode_name_document(
        self,
        episode_name_emb: Dict[str, Any],
        episode_id: str,
        episode_metadata: Dict[str, Any],
        video_path: str,
        season_dir: str,
        base_name: str,
    ) -> None:
        output_file = self.output_dir / "episode_names" / season_dir / f"{base_name}_episode_name.jsonl"
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
