from datetime import datetime
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
import warnings

import cv2
from insightface.app import FaceAnalysis
import numpy as np

from preprocessor.config.config import settings
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

warnings.filterwarnings('ignore', message='.*estimate.*is deprecated.*', category=FutureWarning, module='insightface')

class CharacterReferenceProcessor(BaseProcessor):

    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(args=args, class_name='CharacterReferenceProcessor', error_exit_code=20, loglevel=logging.INFO)
        self.characters_dir = args['characters_dir']
        self.output_dir = args['output_dir']
        self.similarity_threshold = args['similarity_threshold']
        self.interactive = args['interactive']
        self.face_app: Optional[FaceAnalysis] = None
        self._visualizer = CharacterGridVisualizer(similarity_threshold=self.similarity_threshold)

    def generate_validation_grid(self) -> None:
        output_path = self.output_dir / 'validation_grid.png'
        if output_path.exists():
            console.print(f'[dim]Skipping validation grid (already exists): {output_path}[/dim]')
            return

        console.print('\n[blue]Generating validation grid...[/blue]')

        if not self.output_dir.exists():
            console.print('[yellow]No processed references found, skipping validation grid[/yellow]')
            return

        processed_chars = sorted([d for d in self.output_dir.iterdir() if d.is_dir()])
        if not processed_chars:
            console.print('[yellow]No processed characters found, skipping validation grid[/yellow]')
            return

        stats = self._visualizer.generate_grid(
            processed_chars_dir=self.output_dir,
            output_path=output_path,
        )

        console.print(f'[green]Validation grid saved to: {output_path}[/green]')
        console.print(f'[green]  Grid size: {stats["width"]}x{stats["height"]}px[/green]')
        console.print(f'[green]  Characters: {stats["num_chars"]}[/green]')
        console.print(f'[green]  Average similarity: {stats["avg_similarity"]:.4f}[/green]')

    def get_output_subdir(self) -> str:
        return 'character_references'

    def _execute(self) -> None:
        super()._execute()
        self.generate_validation_grid()

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        char_output_dir = self.output_dir / item.episode_id
        return [
            OutputSpec(path=char_output_dir / 'metadata.json', required=True),
            OutputSpec(path=char_output_dir / 'face_vector.npy', required=True),
        ]

    def _get_processing_items(self) -> List[ProcessingItem]:
        items = []
        if not self.characters_dir.exists():
            console.print(f'[red]Characters directory not found: {self.characters_dir}[/red]')
            return items
        for char_dir in sorted(self.characters_dir.iterdir()):
            if not char_dir.is_dir():
                continue
            items.append(ProcessingItem(episode_id=char_dir.name, input_path=char_dir, metadata={'char_name': char_dir.name}))
        return items

    def _get_progress_description(self) -> str:
        return 'Processing character references'

    def _load_resources(self) -> bool:
        self.face_app = FaceDetector.init()
        return True

    def _process_item(self, item: ProcessingItem, _missing_outputs: List[OutputSpec]) -> None:
        char_dir = item.input_path
        char_name = item.metadata['char_name']
        console.print(f'[blue]Processing character: {char_name}[/blue]')
        reference_images = sorted(char_dir.glob('*.jpg'))
        if len(reference_images) < 2:
            console.print(f'[yellow]Skipping {char_name}: need at least 2 reference images, found {len(reference_images)}[/yellow]')
            return
        all_faces = self.__detect_faces_in_references(reference_images)
        if not all_faces or not all_faces[0]:
            console.print(f'[yellow]Skipping {char_name}: no faces detected in reference images[/yellow]')
            return
        selected_faces = self.__find_common_face(all_faces, char_name, reference_images)
        if not selected_faces:
            console.print(f'[yellow]Skipping {char_name}: could not identify common face[/yellow]')
            return
        self.__save_processed_references(char_name, selected_faces, reference_images)
        console.print(f'[green]Processed {char_name}[/green]')

    def _validate_args(self, args: Dict[str, Any]) -> None:
        required = ['characters_dir', 'output_dir', 'similarity_threshold', 'interactive']
        for key in required:
            if key not in args:
                raise ValueError(f'Missing required argument: {key}')

    def __ask_user_to_select_candidate(
        self,
        candidates: List[CandidateFace],
        char_name: str,
    ) -> Optional[List[FaceData]]:
        console.print(f'[yellow]Character: {char_name}[/yellow]')
        console.print(f'[yellow]Found {len(candidates)} possible matches across all reference images.[/yellow]')
        for idx, candidate in enumerate(candidates, 1):
            console.print(f'Candidate {idx}: avg similarity = {candidate.avg_similarity:.2f}')
        grid_path = self.__create_selection_grid(candidates, 'candidates', char_name)
        console.print(f'[blue]Grid image saved to: {grid_path}[/blue]')
        while True:
            prompt = f'Select the correct character (1-{len(candidates)}) or skip (s): '
            user_input = input(prompt).strip().lower()  # pylint: disable=bad-builtin
            if user_input == 's':
                return None
            try:
                selection = int(user_input)
                if 1 <= selection <= len(candidates):
                    return candidates[selection - 1].faces
                console.print(f"[red]Invalid selection. Please enter 1-{len(candidates)} or 's'[/red]")
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or 's'[/red]")

    def __ask_user_to_select_initial_face(
        self,
        first_image_faces: List[FaceData],
        all_faces: List[List[FaceData]],
        char_name: str,
        reference_images: List[Path],
    ) -> Optional[List[FaceData]]:
        console.print(f'[yellow]Character: {char_name}[/yellow]')
        console.print('[yellow]No common face found across all reference images.[/yellow]')
        console.print(
            '[yellow]Manual selection mode: Please select the correct face '
            'from the first image.[/yellow]',
        )
        console.print(
            f'[yellow]Found {len(first_image_faces)} faces in '
            'first reference image.[/yellow]',
        )
        grid_path = self.__create_selection_grid(first_image_faces, 'manual', char_name)
        console.print(f'[blue]Grid image saved to: {grid_path}[/blue]')
        while True:
            prompt = f'Select the correct face (1-{len(first_image_faces)}) or skip (s): '
            user_input = input(prompt).strip().lower()  # pylint: disable=bad-builtin
            if user_input == 's':
                return None
            try:
                selection = int(user_input)
                if 1 <= selection <= len(first_image_faces):
                    selected_face = first_image_faces[selection - 1]
                    return self.__find_matching_faces_for_reference(
                        selected_face.face_vector,
                        all_faces[1:],
                        [selected_face],
                        reference_images,
                    )
                console.print(
                    f"[red]Invalid selection. Please enter 1-{len(first_image_faces)} or 's'[/red]",
                )
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or 's'[/red]")

    def __create_selection_grid(self, data, mode: str, char_name: str) -> Path:
        if mode == 'candidates':
            grid = self.__create_candidates_grid(data)
        else:
            grid = self.__create_manual_selection_grid(data)

        selection_grids_dir = self.output_dir.parent / 'character_selection_grids'
        selection_grids_dir.mkdir(parents=True, exist_ok=True)
        output_path = selection_grids_dir / f"{char_name.replace(' ', '_').lower()}_selection.jpg"
        cv2.imwrite(str(output_path), grid)
        return output_path

    @staticmethod
    def __create_candidates_grid(candidates: List[CandidateFace]) -> np.ndarray:
        num_refs = len(candidates[0].faces)
        num_candidates = len(candidates)
        face_size = 150
        padding = 10
        label_height = 30
        grid_width = num_refs * (face_size + padding) + padding
        grid_height = num_candidates * (face_size + label_height + padding) + padding + label_height
        grid = np.ones((grid_height, grid_width, 3), dtype=np.uint8) * 255

        for col_idx in range(num_refs):
            label = f'Ref {col_idx + 1}'
            x = padding + col_idx * (face_size + padding)
            cv2.putText(grid, label, (x + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        for cand_idx, candidate in enumerate(candidates):
            y_base = label_height + padding + cand_idx * (face_size + label_height + padding)
            for face_idx, face_data in enumerate(candidate.faces):
                x = padding + face_idx * (face_size + padding)
                face_resized = CharacterGridVisualizer._safe_resize(face_data.face_img, (face_size, face_size))
                if face_resized is not None:
                    grid[y_base:y_base + face_size, x:x + face_size] = face_resized

            label = f'Candidate {cand_idx + 1}'
            cv2.putText(grid, label, (5, y_base + face_size // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        return grid

    @staticmethod
    def __create_manual_selection_grid(faces_data: List[FaceData]) -> np.ndarray:
        num_faces = len(faces_data)
        cols = min(3, num_faces)
        rows = (num_faces + cols - 1) // cols
        face_size = 150
        padding = 10
        grid_width = cols * (face_size + padding) + padding
        grid_height = rows * (face_size + padding) + padding
        grid = np.ones((grid_height, grid_width, 3), dtype=np.uint8) * 255

        for idx, face_data in enumerate(faces_data):
            row = idx // cols
            col = idx % cols
            x = padding + col * (face_size + padding)
            y = padding + row * (face_size + padding)
            face_resized = CharacterGridVisualizer._safe_resize(face_data.face_img, (face_size, face_size))
            if face_resized is not None:
                grid[y:y + face_size, x:x + face_size] = face_resized

            label = str(idx + 1)
            cv2.putText(grid, label, (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return grid

    def __detect_faces_in_references(self, image_paths: List[Path]) -> List[List[FaceData]]:
        all_faces = []
        for idx, img_path in enumerate(image_paths):
            img = cv2.imread(str(img_path))
            if img is None:
                console.print(f'[yellow]Warning: Could not read {img_path}[/yellow]')
                all_faces.append([])
                continue
            console.print(f'[dim]  {img_path.name}: detecting faces (image size: {img.shape[1]}x{img.shape[0]})...[/dim]')
            faces = self.face_app.get(img)
            console.print(f'[dim]    Found {len(faces)} face(s)[/dim]')
            faces_data = []
            for face in faces:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                face_img = img[y1:y2, x1:x2]
                faces_data.append(
                    FaceData(
                        bbox=bbox,
                        face_vector=face.normed_embedding,
                        source_image_path=img_path,
                        source_image_idx=idx,
                        face_img=face_img,
                    ),
                )
            all_faces.append(faces_data)
        return all_faces

    def __find_common_face(
        self,
        all_faces: List[List[FaceData]],
        char_name: str,
        reference_images: List[Path],
    ) -> Optional[List[FaceData]]:
        first_image_faces = all_faces[0]
        remaining_images = all_faces[1:]
        candidates = []
        for first_face in first_image_faces:
            matched_faces = [first_face]
            similarities = []
            for other_image_faces in remaining_images:
                if not other_image_faces:
                    break
                best_match = None
                best_similarity: float = -1.0
                for other_face in other_image_faces:
                    similarity: float = float(
                        np.dot(
                            first_face.face_vector,
                            other_face.face_vector,
                        ),
                    )
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = other_face
                if best_match:
                    matched_faces.append(best_match)
                    similarities.append(best_similarity)
                    if best_similarity < self.similarity_threshold:
                        console.print(
                            f'[yellow]Warning: Low similarity {best_similarity:.2f} < '
                            f'{self.similarity_threshold:.2f}[/yellow]',
                        )
                else:
                    break
            if len(matched_faces) == len(all_faces):
                avg_similarity = np.mean(similarities) if similarities else 1.0
                candidates.append(CandidateFace(faces=matched_faces, avg_similarity=avg_similarity))
        if len(candidates) == 0:
            if self.interactive:
                return self.__ask_user_to_select_initial_face(
                    first_image_faces,
                    all_faces,
                    char_name,
                    reference_images,
                )
            return None
        if len(candidates) == 1:
            return candidates[0].faces
        if self.interactive:
            return self.__ask_user_to_select_candidate(candidates, char_name)
        candidates.sort(key=lambda c: c.avg_similarity, reverse=True)
        return candidates[0].faces

    def __find_matching_faces_for_reference(
        self,
        reference_vector: np.ndarray,
        remaining_images: List[List[FaceData]],
        matched_faces: List[FaceData],
        reference_images: List[Path],
    ) -> Optional[List[FaceData]]:
        for img_idx, other_image_faces in enumerate(remaining_images, 1):
            if not other_image_faces:
                img_path = reference_images[img_idx]
                console.print(f'[red]No faces found in image {img_idx + 1}: {img_path}[/red]')
                return None
            best_match = None
            best_sim: float = -1.0
            for other_face in other_image_faces:
                similarity: float = float(np.dot(reference_vector, other_face.face_vector))
                if similarity > best_sim:
                    best_sim = similarity
                    best_match = other_face
            if best_match:
                matched_faces.append(best_match)
                if best_sim < self.similarity_threshold:
                    img_path = reference_images[img_idx]
                    console.print(
                        f'[yellow]Warning: Low similarity in image {img_idx + 1}: '
                        f'{img_path} (similarity: {best_sim:.2f} < '
                        f'threshold: {self.similarity_threshold:.2f})[/yellow]',
                    )
            else:
                console.print(
                    f'[red]No faces detected in image {img_idx + 1}: '
                    f'{reference_images[img_idx]}[/red]',
                )
                return None
        return matched_faces



    def __save_processed_references(
        self,
        char_name: str,
        selected_faces: List[FaceData],
        reference_images: List[Path],
    ) -> None:
        char_output_dir = self.output_dir / char_name
        char_output_dir.mkdir(parents=True, exist_ok=True)

        face_vectors = []
        for idx, face_data in enumerate(selected_faces):
            face_normalized = CharacterGridVisualizer._safe_resize(
                face_data.face_img,
                settings.character.normalized_face_size,
            )
            if face_normalized is None:
                self.logger.warning(f'Skipping face {idx} for {char_name}: failed to resize (invalid dimensions)')
                continue
            face_output_path = char_output_dir / f'face_{idx:02d}.jpg'
            cv2.imwrite(str(face_output_path), face_normalized)
            face_vectors.append(face_data.face_vector)

        mean_vector = np.mean(face_vectors, axis=0)
        np.save(char_output_dir / 'face_vector.npy', mean_vector)

        metadata = self.__create_reference_metadata(
            char_name, selected_faces, reference_images, mean_vector,
        )
        with open(char_output_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def __create_reference_metadata(
        self,
        char_name: str,
        selected_faces: List[FaceData],
        reference_images: List[Path],
        mean_vector: np.ndarray,
    ) -> Dict[str, Any]:
        total_faces_detected = [
            len(faces_list) for faces_list in self.__detect_faces_in_references(reference_images)
        ]

        similarities = []
        if len(selected_faces) > 1:
            for i in range(len(selected_faces) - 1):
                similarity = np.dot(selected_faces[i].face_vector, selected_faces[i + 1].face_vector)
                similarities.append(similarity)

        return {
            'character_name': char_name.replace('_', ' ').title(),
            'source_images': [str(img) for img in reference_images],
            'processed_at': datetime.now().isoformat(),
            'processing_params': {
                'similarity_threshold': self.similarity_threshold,
                'face_model': settings.face_recognition.model_name,
                'normalized_face_size': list(settings.character.normalized_face_size),
            },
            'detection_stats': {
                'total_faces_detected': total_faces_detected,
                'candidates_found': 1,
                'selection_method': 'automatic' if len(selected_faces) == len(reference_images) else 'manual',
            },
            'selected_face_indices': [face.source_image_idx for face in selected_faces],
            'average_similarity': float(np.mean(similarities)) if similarities else 1.0,
            'face_vector_dim': int(mean_vector.shape[0]),
        }
