import gc
import json
import logging
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import numpy as np
import torch

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.episode_name_embedder import EpisodeNameEmbedder
from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.embeddings.qwen3_vl_embedding import Qwen3VLEmbedder
from preprocessor.utils.batch_processing_utils import compute_embeddings_in_batches
from preprocessor.utils.console import console
from preprocessor.utils.image_hash_utils import load_image_hashes_for_episode
from preprocessor.utils.metadata_utils import create_processing_metadata

# pylint: disable=duplicate-code



class EmbeddingGenerator(BaseProcessor): # pylint: disable=too-many-instance-attributes
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=9,
            loglevel=logging.DEBUG,
        )

        self.transcription_jsons: Path = self._args["transcription_jsons"]
        self.frames_dir: Path = self._args.get("frames_dir", settings.frame_export.output_dir)
        self.output_dir: Path = self._args.get("output_dir", settings.embedding.default_output_dir)

        self.model_name: str = self._args.get("model", settings.embedding.model_name)
        self.model_revision: str = self._args.get("model_revision", settings.embedding.model_revision)
        self.batch_size: int = self._args.get("batch_size", settings.embedding.batch_size)
        self.device: str = "cuda"

        self.segments_per_embedding: int = self._args.get("segments_per_embedding", settings.embedding.segments_per_embedding)
        self.use_sentence_based_chunking: bool = self._args.get("use_sentence_based_chunking", settings.embedding.use_sentence_based_chunking)
        self.text_sentences_per_chunk: int = self._args.get("text_sentences_per_chunk", settings.embedding.text_sentences_per_chunk)
        self.text_chunk_overlap: int = self._args.get("text_chunk_overlap", settings.embedding.text_chunk_overlap)
        self.generate_text: bool = self._args.get("generate_text", True)
        self.generate_video: bool = self._args.get("generate_video", True)

        self.image_hashes_dir: Path = Path(self._args.get("image_hashes_dir", settings.image_hash.output_dir))

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.model = None
        self.processor = None
        self.gpu_processor: Optional[GPUBatchProcessor] = None
        self.episode_name_embedder: Optional[EpisodeNameEmbedder] = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "transcription_jsons" not in args:
            raise ValueError("transcription_jsons is required")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. This application requires GPU.")

    def cleanup(self) -> None:
        console.print("[cyan]Unloading embedding model...[/cyan]")
        self.model = None
        self.processor = None
        self._cleanup_memory()
        console.print("[green]✓ Model unloaded[/green]")

    def _get_processing_items(self) -> List[ProcessingItem]:
        all_transcription_files = list(self.transcription_jsons.glob("**/*.json"))
        items = []

        for trans_file in all_transcription_files:
            if "_simple.json" in trans_file.name:
                continue
            if not trans_file.name.endswith("_segmented.json"):
                segmented_version = trans_file.parent / f"{trans_file.stem}_segmented.json"
                if segmented_version.exists():
                    continue

            items.append(self._create_transcription_processing_item(trans_file))

        return items

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        outputs = []
        episode_dir = self._get_episode_output_dir(item.input_path)

        if self.generate_text:
            text_output = episode_dir / "embeddings_text.json"
            outputs.append(OutputSpec(path=text_output, required=True))

            episode_name_output = episode_dir / "episode_name_embedding.json"
            outputs.append(OutputSpec(path=episode_name_output, required=True))

        if self.generate_video:
            video_output = episode_dir / "embeddings_video.json"
            outputs.append(OutputSpec(path=video_output, required=True))

        return outputs

    def _execute_processing(self, items: List[ProcessingItem]) -> None:
        console.print(f"[cyan]Loading model: {self.model_name}[/cyan]")
        console.print(f"[cyan]Device: {self.device}[/cyan]")
        console.print(f"[cyan]Batch size: {self.batch_size}[/cyan]")

        self._load_model()
        self.gpu_processor = GPUBatchProcessor(self.model, self.batch_size, self.logger, self.device)
        self.episode_name_embedder = EpisodeNameEmbedder(
            model=self.model,
            episode_manager=self.episode_manager,
            series_name=self.series_name,
            logger=self.logger,
        )

        super()._execute_processing(items)
        console.print("[green]Embedding generation completed[/green]")

    def _load_model(self) -> None:
        try:
            self.model = Qwen3VLEmbedder(
                model_name_or_path=self.model_name,
                dtype=torch.float16,
            )
            console.print("[green]Qwen3-VL-Embedding model loaded successfully[/green]")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        trans_file = item.input_path

        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        has_segments = bool(data.get("segments"))
        segmented_file = trans_file.parent / f"{trans_file.stem}_segmented.json"

        if not has_segments and segmented_file.exists():
            return

        need_text = any("embeddings_text.json" in str(o.path) for o in missing_outputs)
        need_video = any("embeddings_video.json" in str(o.path) for o in missing_outputs)
        need_episode_name = any("episode_name_embedding.json" in str(o.path) for o in missing_outputs)

        text_embeddings = []
        if need_text:
            text_embeddings = self.__generate_text_embeddings(data)

        video_embeddings = []
        if need_video:
            episode_info = data.get("episode_info", {})
            frame_metadata = self.__load_frame_metadata(episode_info)
            if frame_metadata:
                video_embeddings = self.__generate_video_embeddings(episode_info, frame_metadata)

        if need_episode_name and self.episode_name_embedder:
            self.episode_name_embedder.generate_and_save_for_transcription(data)

        episode_dir = self._get_episode_output_dir(trans_file)
        text_output = episode_dir / "embeddings_text.json"
        video_output = episode_dir / "embeddings_video.json"
        self.__save_embeddings(data, text_embeddings, video_embeddings, text_output, video_output)
        self._cleanup_memory()

    def __generate_text_embeddings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:  # pylint: disable=too-many-locals
        segments = data.get("segments", [])
        if not segments:
            return []

        text_chunks = []
        chunk_metadata = []

        if self.use_sentence_based_chunking:
            full_text = " ".join([seg.get("text", "") for seg in segments])
            sentences = self.__split_into_sentences(full_text)

            sentences_per_chunk = self.text_sentences_per_chunk
            overlap = self.text_chunk_overlap
            step = sentences_per_chunk - overlap

            for i in range(0, len(sentences), step):
                chunk_sentences = sentences[i:i + sentences_per_chunk]
                if not chunk_sentences:
                    continue

                chunk_text = " ".join(chunk_sentences).strip()
                if not chunk_text:
                    continue

                char_start = sum(len(s) + 1 for s in sentences[:i])
                char_end = char_start + len(chunk_text)

                start_seg_id = self.__find_segment_at_position(segments, char_start)
                end_seg_id = self.__find_segment_at_position(segments, char_end)

                text_chunks.append(chunk_text)
                chunk_metadata.append({
                    "segment_range": [start_seg_id, end_seg_id],
                    "text": chunk_text,
                })
        else:
            for i in range(0, len(segments), self.segments_per_embedding):
                chunk = segments[i: i + self.segments_per_embedding]
                combined_text = " ".join([seg.get("text", "") for seg in chunk])

                if combined_text.strip():
                    text_chunks.append(combined_text)
                    chunk_metadata.append({
                        "segment_range": [i, i + len(chunk) - 1],
                        "text": combined_text,
                    })

        if not text_chunks:
            return []

        embeddings = []
        text_batch_size = 16

        with self.progress.track_operation(
            f"Text embeddings ({len(text_chunks)} chunks)",
            (len(text_chunks) + text_batch_size - 1) // text_batch_size,
        ) as tracker:
            for batch_idx in range(0, len(text_chunks), text_batch_size):
                batch_texts = text_chunks[batch_idx: batch_idx + text_batch_size]
                batch_meta = chunk_metadata[batch_idx: batch_idx + text_batch_size]

                try:
                    batch_embeddings = self.__encode_text_batch(batch_texts)
                    for meta, embedding in zip(batch_meta, batch_embeddings):
                        embeddings.append({
                            **meta,
                            "embedding": embedding.tolist(),
                        })
                except (RuntimeError, ValueError, OSError) as e:
                    self.logger.error(f"Failed text embedding batch {batch_idx}: {e}")

                tracker.update((batch_idx // text_batch_size) + 1, interval=5)

        return embeddings

    def __split_into_sentences(self, text: str) -> List[str]:
        normalized_text = re.sub(r'\.{2,}', '.', text)
        normalized_text = re.sub(r'!{2,}', '!', normalized_text)
        normalized_text = re.sub(r'\?{2,}', '?', normalized_text)

        sentences = re.split(r'([.!?]+(?:\s+|$))', normalized_text)
        raw_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
            sentence = sentence.strip()
            if sentence:
                raw_sentences.append(sentence)
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            raw_sentences.append(sentences[-1].strip())

        result = []
        buffer = ""
        min_sentence_length = 30

        for sentence in raw_sentences:
            buffer = (buffer + " " + sentence).strip() if buffer else sentence

            if len(buffer) >= min_sentence_length:
                result.append(buffer)
                buffer = ""

        if buffer:
            if result:
                result[-1] = result[-1] + " " + buffer
            else:
                result.append(buffer)

        return result

    def __find_segment_at_position(self, segments: List[Dict[str, Any]], char_pos: int) -> int:
        cumulative_length = 0
        for idx, seg in enumerate(segments):
            seg_text = seg.get("text", "")
            seg_length = len(seg_text) + 1
            if cumulative_length <= char_pos < cumulative_length + seg_length:
                return idx
            cumulative_length += seg_length
        return len(segments) - 1 if segments else 0

    def __encode_text_batch(self, texts: List[str]) -> List[np.ndarray]:
        inputs = [{"text": text} for text in texts]
        embeddings_tensor = self.model.process(inputs, normalize=True)
        embeddings = [emb.cpu().numpy() for emb in embeddings_tensor]
        del embeddings_tensor
        return embeddings

    def __load_frame_metadata(self, episode_info_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        season = episode_info_dict.get("season")
        episode = episode_info_dict.get("episode_number")
        if season is None or episode is None:
            return None

        frames_episode_dir = self.frames_dir / f"S{season:02d}" / f"E{episode:02d}"
        metadata_file = frames_episode_dir / "frame_metadata.json"

        if not metadata_file.exists():
            self.logger.warning(f"Frame metadata not found: {metadata_file}")
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def __load_image_hashes(self, episode_info_dict: Dict[str, Any]) -> Dict[int, str]:
        return load_image_hashes_for_episode(episode_info_dict, self.logger)

    def __generate_video_embeddings(self, episode_info_dict: Dict[str, Any], frame_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        frame_requests = frame_metadata.get("frames", [])
        if not frame_requests:
            return []

        season = episode_info_dict.get("season")
        episode = episode_info_dict.get("episode_number")
        frames_episode_dir = self.frames_dir / f"S{season:02d}" / f"E{episode:02d}"
        episode_output_dir = self.output_dir / f"S{season:02d}" / f"E{episode:02d}"
        checkpoint_file = episode_output_dir / "embeddings_video_checkpoint.json"

        image_hashes = self.__load_image_hashes(episode_info_dict)
        embeddings = compute_embeddings_in_batches(
            frames_episode_dir,
            frame_requests,
            self.gpu_processor,
            self.batch_size,
            image_hashes,
            checkpoint_file=checkpoint_file,
            checkpoint_interval=20,
            prefetch_count=settings.embedding.prefetch_chunks,
        )
        self._cleanup_memory()
        return embeddings

    def _get_episode_output_dir(self, transcription_file: Path) -> Path:
        episode_info_from_file = self.episode_manager.parse_filename(transcription_file)
        if episode_info_from_file:
            season = episode_info_from_file.season
            episode = episode_info_from_file.relative_episode
            return self.output_dir / f"S{season:02d}" / f"E{episode:02d}"
        return self.output_dir / "unknown"

    def __save_embeddings(
            self,
            data,
        text_embeddings,
        video_embeddings,
        text_output,
        video_output,
    ):
        episode_info = data.get("episode_info", {})
        text_output.parent.mkdir(parents=True, exist_ok=True)

        if text_embeddings:
            text_data = create_processing_metadata(
                episode_info=type(
                    'obj', (object,), {
                        'season': episode_info.get("season"),
                        'relative_episode': episode_info.get("episode_number"),
                    },
                )(),
                processing_params={
                    "model_name": self.model_name,
                    "model_revision": self.model_revision,
                    "segments_per_embedding": self.segments_per_embedding,
                    "use_sentence_based_chunking": self.use_sentence_based_chunking,
                    "text_sentences_per_chunk": self.text_sentences_per_chunk if self.use_sentence_based_chunking else None,
                    "text_chunk_overlap": self.text_chunk_overlap if self.use_sentence_based_chunking else None,
                    "device": self.device,
                },
                statistics={
                    "total_embeddings": len(text_embeddings),
                    "embedding_dimension": len(text_embeddings[0]["embedding"]) if text_embeddings else 0,
                },
                results_key="text_embeddings",
                results_data=text_embeddings,
            )
            with open(text_output, "w", encoding="utf-8") as f:
                json.dump(text_data, f, indent=2, ensure_ascii=False)

        if video_embeddings:
            video_data = create_processing_metadata(
                episode_info=type(
                    'obj', (object,), {
                        'season': episode_info.get("season"),
                        'relative_episode': episode_info.get("episode_number"),
                    },
                )(),
                processing_params={
                    "model_name": self.model_name,
                    "model_revision": self.model_revision,
                    "batch_size": self.batch_size,
                    "device": self.device,
                },
                statistics={
                    "total_embeddings": len(video_embeddings),
                    "embedding_dimension": len(video_embeddings[0]["embedding"]) if video_embeddings else 0,
                    "frames_with_hash": sum(1 for e in video_embeddings if "perceptual_hash" in e),
                },
                results_key="video_embeddings",
                results_data=video_embeddings,
            )
            with open(video_output, "w", encoding="utf-8") as f:
                json.dump(video_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
