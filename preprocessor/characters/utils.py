import os

from insightface.app import FaceAnalysis

from preprocessor.config.config import settings
from preprocessor.utils.console import console


def init_face_detection(use_gpu: bool) -> FaceAnalysis:
    model_root = os.getenv("INSIGHTFACE_HOME", os.path.expanduser("~/.insightface"))
    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if use_gpu else ['CPUExecutionProvider']
    face_app = FaceAnalysis(name=settings.face_recognition.model_name, root=model_root, providers=providers)
    ctx_id = 0 if use_gpu else -1
    face_app.prepare(ctx_id=ctx_id, det_size=settings.face_recognition.detection_size)
    console.print(f"[green]✓ Face detection initialized ({settings.face_recognition.model_name})[/green]")
    console.print(f"[dim]  Model cache: {model_root}[/dim]")
    return face_app
