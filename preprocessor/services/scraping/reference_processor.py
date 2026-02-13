from datetime import datetime
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)
import warnings

import cv2
from insightface.app import FaceAnalysis
import numpy as np

from preprocessor.config.settings_instance import settings
from preprocessor.services.characters.face_detection import FaceDetector
from preprocessor.services.characters.models import (
    CandidateFace,
    FaceData,
)
from preprocessor.services.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.services.scraping.grid_visualizer import CharacterGridVisualizer
from preprocessor.services.ui.console import console

warnings.filterwarnings('ignore', category=FutureWarning, module='insightface')


class CharacterReferenceProcessor(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name='CharacterReferenceProcessor',
            error_exit_code=20,
            loglevel=logging.INFO,
        )
        self.__characters_dir: Path = args['characters_dir']
        self.__output_dir: Path = args['output_dir']
        self.__similarity_threshold: float = args['similarity_threshold']
        self.__interactive: bool = args['interactive']

        self.__face_app: Optional[FaceAnalysis] = None
        self.__visualizer = CharacterGridVisualizer(similarity_threshold=self.__similarity_threshold)

    def get_output_subdir(self) -> str:
        return 'character_references'

    def _execute(self) -> None:
        super()._execute()
        self.__generate_validation_grid()

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        char_output_dir = self.__output_dir / item.episode_id
        return [
            OutputSpec(path=char_output_dir / 'metadata.json', required=True),
            OutputSpec(path=char_output_dir / 'face_vector.npy', required=True),
        ]

    def _get_processing_items(self) -> List[ProcessingItem]:
        if not self.__characters_dir.exists():
            console.print(f'[red]Characters directory not found: {self.__characters_dir}[/red]')
            return []

        return [
            ProcessingItem(
                episode_id=char_dir.name,
                input_path=char_dir,
                metadata={'char_name': char_dir.name},
            )
            for char_dir in sorted(self.__characters_dir.iterdir()) if char_dir.is_dir()
        ]

    def _get_progress_description(self) -> str:
        return 'Processing character references'

    def _load_resources(self) -> bool:
        self.__face_app = FaceDetector.init()
        return True

    def _validate_args(self, args: Dict[str, Any]) -> None:
        required = ['characters_dir', 'output_dir', 'similarity_threshold', 'interactive']
        for key in required:
            if key not in args:
                raise ValueError(f'Missing required argument: {key}')

    def _process_item(self, item: ProcessingItem, _missing_outputs: List[OutputSpec]) -> None:
        char_dir = item.input_path
        char_name = item.metadata['char_name']
        console.print(f'[blue]Processing character: {char_name}[/blue]')

        ref_images = sorted(char_dir.glob('*.jpg'))
        if len(ref_images) < 2:
            console.print(f'[yellow]Skipping {char_name}: need >=2 images, found {len(ref_images)}[/yellow]')
            return

        all_faces = self.__detect_faces_in_references(ref_images)
        if not all_faces or not all_faces[0]:
            console.print(f'[yellow]Skipping {char_name}: no faces detected[/yellow]')
            return

        selected_faces = self.__find_common_face(all_faces, char_name, ref_images)
        if not selected_faces:
            console.print(f'[yellow]Skipping {char_name}: could not identify common face[/yellow]')
            return

        self.__save_processed_references(char_name, selected_faces, ref_images)
        console.print(f'[green]Processed {char_name}[/green]')

    def __generate_validation_grid(self) -> None:
        output_path = self.__output_dir / 'validation_grid.png'
        if output_path.exists():
            console.print(f'[dim]Skipping validation grid (exists): {output_path}[/dim]')
            return

        processed_chars = sorted([d for d in self.__output_dir.iterdir() if d.is_dir()])
        if not processed_chars:
            return

        stats = self.__visualizer.generate_grid(
            processed_chars_dir=self.__output_dir,
            output_path=output_path,
        )

        console.print(f'\n[green]Validation grid saved to: {output_path}[/green]')
        console.print(f'[green]  Size: {stats["width"]}x{stats["height"]}px | Chars: {stats["num_chars"]}[/green]')

    def __detect_faces_in_references(self, image_paths: List[Path]) -> List[List[FaceData]]:
        all_faces = []
        for idx, img_path in enumerate(image_paths):
            img = cv2.imread(str(img_path))
            if img is None:
                all_faces.append([])
                continue

            faces = self.__face_app.get(img)
            faces_data = [
                FaceData(
                    bbox=(bbox := face.bbox.astype(int)),
                    face_vector=face.normed_embedding,
                    source_image_path=img_path,
                    source_image_idx=idx,
                    face_img=img[bbox[1]:bbox[3], bbox[0]:bbox[2]],
                ) for face in faces
            ]
            all_faces.append(faces_data)
        return all_faces

    def __find_common_face(
            self,
            all_faces: List[List[FaceData]],
            char_name: str,  # pylint: disable=unused-argument
            ref_images: List[Path],  # pylint: disable=unused-argument
    ) -> Optional[List[FaceData]]:
        first_faces = all_faces[0]
        candidates = self.__find_face_candidates(first_faces, all_faces[1:], all_faces)

        if len(candidates) == 1:
            return candidates[0].faces

        if len(candidates) > 1 and not self.__interactive:
            candidates.sort(key=lambda c: c.avg_similarity, reverse=True)
            return candidates[0].faces

        return None

    def __find_face_candidates(
            self, first_faces: List[FaceData], remaining: List[List[FaceData]], all_faces: List[List[FaceData]],
    ) -> List[CandidateFace]:
        candidates = []
        for first_face in first_faces:
            matched = [first_face]
            sims = []

            for other_faces in remaining:
                best_match, best_sim = self.__get_best_match(first_face, other_faces)
                if best_match:
                    matched.append(best_match)
                    sims.append(best_sim)
                else:
                    break

            if len(matched) == len(all_faces):
                candidates.append(CandidateFace(faces=matched, avg_similarity=float(np.mean(sims))))

        return candidates

    def __get_best_match(self, ref_face: FaceData, candidates: List[FaceData]) -> Tuple[Optional[FaceData], float]:
        best_match, best_sim = None, -1.0
        for cand in candidates:
            sim = float(np.dot(ref_face.face_vector, cand.face_vector))
            if sim > best_sim:
                best_sim = sim
                best_match = cand
        return best_match, best_sim

    def __save_processed_references(
            self, char_name: str, selected_faces: List[FaceData], ref_images: List[Path],
    ) -> None:
        char_out = self.__output_dir / char_name
        char_out.mkdir(parents=True, exist_ok=True)

        face_vectors = []
        for idx, face_data in enumerate(selected_faces):
            norm_face = CharacterGridVisualizer._safe_resize(
                face_data.face_img,
                settings.character.normalized_face_size,
            )
            if norm_face is not None:
                cv2.imwrite(str(char_out / f'face_{idx:02d}.jpg'), norm_face)
                face_vectors.append(face_data.face_vector)

        mean_vector = np.mean(face_vectors, axis=0)
        np.save(char_out / 'face_vector.npy', mean_vector)

        metadata = self.__create_metadata(char_name, selected_faces, ref_images, mean_vector)
        with open(char_out / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def __create_metadata(self, name: str, faces: List[FaceData], refs: List[Path], mean_vec: np.ndarray) -> Dict[
        str, Any,
    ]:
        return {
            'character_name': name.replace('_', ' ').title(),
            'source_images': [str(img) for img in refs],
            'processed_at': datetime.now().isoformat(),
            'processing_params': {
                'similarity_threshold': self.__similarity_threshold,
                'face_model': settings.face_recognition.model_name,
            },
            'selected_face_indices': [f.source_image_idx for f in faces],
            'face_vector_dim': int(mean_vec.shape[0]),
        }
