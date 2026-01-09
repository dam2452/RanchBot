import os
import warnings

from insightface.app import FaceAnalysis
import onnxruntime as ort

from preprocessor.config.config import settings
from preprocessor.utils.console import console


def init_face_detection(use_gpu: bool) -> FaceAnalysis:
    model_root = os.getenv("INSIGHTFACE_HOME", os.path.expanduser("~/.insightface"))

    if use_gpu:
        available_providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in available_providers:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        else:
            console.print("[yellow]⚠ CUDA not available for ONNX Runtime, falling back to CPU[/yellow]")
            providers = ['CPUExecutionProvider']
            use_gpu = False
    else:
        providers = ['CPUExecutionProvider']

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")
        face_app = FaceAnalysis(name=settings.face_recognition.model_name, root=model_root, providers=providers)

    ctx_id = 0 if use_gpu else -1
    face_app.prepare(ctx_id=ctx_id, det_size=settings.face_recognition.detection_size)
    console.print(f"[green]✓ Face detection initialized ({settings.face_recognition.model_name})[/green]")
    console.print(f"[dim]  Model cache: {model_root}[/dim]")
    return face_app
