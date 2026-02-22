import os
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
from numpy.linalg import norm
import onnxruntime as ort

from preprocessor.config.settings_instance import settings
from preprocessor.services.ui.console import console

warnings.filterwarnings(
    'ignore',
    message='.*estimate.*is deprecated.*',
    category=FutureWarning,
    module='insightface',
)


class FaceDetector:
    @staticmethod
    def detect_characters_in_frame(
            frame_path: Path,
            face_app: FaceAnalysis,
            character_vectors: Dict[str, np.ndarray],
            threshold: float,
    ) -> List[Dict[str, Any]]:
        img = cv2.imread(str(frame_path))
        if img is None:
            return []

        faces = face_app.get(img)
        if not faces:
            return []

        detected = []
        for face in faces:
            match = FaceDetector.__find_best_match(
                face.normed_embedding, character_vectors, threshold,
            )
            if match:
                char_name, confidence = match
                detected.append(
                    FaceDetector.__format_detection_result(char_name, confidence, face.bbox),
                )

        detected.sort(key=lambda x: x['confidence'], reverse=True)
        return detected

    @staticmethod
    def init() -> FaceAnalysis:
        model_root = os.getenv('INSIGHTFACE_HOME', os.path.expanduser('~/.insightface'))
        FaceDetector.__check_cuda_availability()

        providers = FaceDetector.__build_providers_config()

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=UserWarning, module='onnxruntime')
            warnings.filterwarnings('ignore', category=FutureWarning, module='insightface')

            face_app = FaceDetector.__init_face_app(model_root, providers)
            FaceDetector.__verify_active_providers(face_app)

        FaceDetector.__print_init_success(model_root)
        return face_app

    @staticmethod
    def load_character_references(
            characters_dir: Path,
            face_app: FaceAnalysis,
    ) -> Dict[str, np.ndarray]:
        console.print('[blue]Loading character references...[/blue]')
        character_vectors: Dict[str, np.ndarray] = {}

        for char_dir in characters_dir.iterdir():
            if not char_dir.is_dir():
                continue

            char_name = char_dir.name.replace('_', ' ').title()
            vector = FaceDetector.__load_or_compute_vector(char_dir, char_name, face_app)

            if vector is not None:
                character_vectors[char_name] = vector

        console.print(f'[green]Loaded {len(character_vectors)} characters[/green]')
        return character_vectors

    @staticmethod
    def __find_best_match(
            face_embedding: np.ndarray,
            character_vectors: Dict[str, np.ndarray],
            threshold: float,
    ) -> Optional[Tuple[str, float]]:
        best_match = None
        best_similarity = threshold

        for char_name, char_vector in character_vectors.items():
            similarity = float(np.dot(face_embedding, char_vector))
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = char_name

        return (best_match, best_similarity) if best_match else None

    @staticmethod
    def __format_detection_result(
            char_name: str,
            confidence: float,
            bbox: np.ndarray,
    ) -> Dict[str, Any]:
        bbox_int = bbox.astype(int)
        return {
            'name': char_name,
            'confidence': confidence,
            'bbox': {
                'x1': int(bbox_int[0]),
                'y1': int(bbox_int[1]),
                'x2': int(bbox_int[2]),
                'y2': int(bbox_int[3]),
            },
        }

    @staticmethod
    def __check_cuda_availability() -> None:
        available_providers = ort.get_available_providers()
        console.print(f"[dim]Available ONNX providers: {', '.join(available_providers)}[/dim]")

        if 'CUDAExecutionProvider' not in available_providers:
            console.print('[red]CUDAExecutionProvider not available in onnxruntime[/red]')
            console.print('[red]  Check if onnxruntime-gpu is installed and CUDA libraries are accessible[/red]')
            raise RuntimeError('CUDA provider not available in onnxruntime')

    @staticmethod
    def __build_providers_config() -> List[Tuple[str, Dict[str, Any]]]:
        return [(
            'CUDAExecutionProvider',
            {
                'device_id': 0,
                'arena_extend_strategy': 'kNextPowerOfTwo',
                'gpu_mem_limit': 8 * 1024 * 1024 * 1024,
                'cudnn_conv_algo_search': 'EXHAUSTIVE',
                'do_copy_in_default_stream': True,
            },
        )]

    @staticmethod
    def __init_face_app(
            model_root: str,
            providers: List[Tuple[str, Dict[str, Any]]],
    ) -> FaceAnalysis:
        model_name = settings.face_recognition.model_name
        console.print(f'[cyan]Loading {model_name} face detection model (GPU-only)...[/cyan]')

        try:
            face_app = FaceAnalysis(name=model_name, root=model_root, providers=providers)
            face_app.prepare(
                ctx_id=0,
                det_size=settings.face_recognition.detection_size,
                det_thresh=settings.character.face_detection_threshold,
            )
            return face_app
        except Exception as e:
            console.print('[red]Failed to initialize face detection on GPU[/red]')
            console.print(f'[red]  Error: {e}[/red]')
            console.print('[red]  Ensure CUDA and onnxruntime-gpu are properly configured[/red]')
            raise RuntimeError('GPU required but face detection initialization failed') from e

    @staticmethod
    def __verify_active_providers(face_app: FaceAnalysis) -> None:
        actual_providers = face_app.models['detection'].session.get_providers()
        if 'CUDAExecutionProvider' not in actual_providers:
            console.print('[red]CUDA provider not active after initialization[/red]')
            console.print(f"[red]  Active providers: {', '.join(actual_providers)}[/red]")
            raise RuntimeError('CUDA required but not available for face detection')

    @staticmethod
    def __print_init_success(model_root: str) -> None:
        model_name = settings.face_recognition.model_name
        det_size = settings.face_recognition.detection_size
        det_thresh = settings.character.face_detection_threshold

        console.print(f'[green]Face detection initialized ({model_name})[/green]')
        console.print('[dim]  Device: GPU (CUDA)[/dim]')
        console.print(f'[dim]  Detection size: {det_size}[/dim]')
        console.print(f'[dim]  Face detection threshold: {det_thresh}[/dim]')
        console.print(f'[dim]  Model cache: {model_root}[/dim]')

    @staticmethod
    def __load_or_compute_vector(
            char_dir: Path,
            char_name: str,
            face_app: FaceAnalysis,
    ) -> Optional[np.ndarray]:
        vector_file = char_dir / 'face_vector.npy'
        if vector_file.exists():
            console.print(f'[dim]{char_name}: loaded from face_vector.npy[/dim]')
            return np.load(vector_file)

        images = list(char_dir.glob('*.jpg'))
        if not images:
            return None

        embeddings = []
        for img_path in images:
            emb = FaceDetector.__get_face_embedding(str(img_path), face_app)
            if emb is not None:
                embeddings.append(emb)

        if embeddings:
            mean_emb = np.mean(embeddings, axis=0)
            centroid = mean_emb / norm(mean_emb)
            console.print(f'[green]{char_name}: {len(embeddings)} reference images[/green]')
            return centroid

        return None

    @staticmethod
    def __get_face_embedding(img_path: str, face_app: FaceAnalysis) -> Optional[np.ndarray]:
        img = cv2.imread(img_path)
        if img is None:
            return None

        faces = face_app.get(img)
        if not faces:
            return None

        faces.sort(
            key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]),
            reverse=True,
        )
        return faces[0].normed_embedding
