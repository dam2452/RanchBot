import os
import warnings

from insightface.app import FaceAnalysis
import onnxruntime as ort

from preprocessor.config.config import settings
from preprocessor.utils.console import console


def init_face_detection() -> FaceAnalysis:
    model_root = os.getenv("INSIGHTFACE_HOME", os.path.expanduser("~/.insightface"))

    available_providers = ort.get_available_providers()
    if 'CUDAExecutionProvider' not in available_providers:
        console.print("[red]✗ CUDA not available for ONNX Runtime[/red]")
        console.print(f"[red]  Available providers: {', '.join(available_providers)}[/red]")
        console.print("[red]  Please install onnxruntime-gpu and ensure CUDA is available[/red]")
        raise RuntimeError("CUDA required but not available for ONNX Runtime")

    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")
        face_app = FaceAnalysis(name=settings.face_recognition.model_name, root=model_root, providers=providers)

    face_app.prepare(ctx_id=0, det_size=settings.face_recognition.detection_size)

    console.print(f"[green]✓ Face detection initialized ({settings.face_recognition.model_name})[/green]")
    console.print("[dim]  Device: GPU (CUDA)[/dim]")
    console.print(f"[dim]  Model cache: {model_root}[/dim]")
    return face_app
