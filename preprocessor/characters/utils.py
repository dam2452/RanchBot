import os
import warnings

from insightface.app import FaceAnalysis
import onnxruntime as ort

from preprocessor.config.config import settings
from preprocessor.utils.console import console


def init_face_detection() -> FaceAnalysis:
    model_root = os.getenv("INSIGHTFACE_HOME", os.path.expanduser("~/.insightface"))

    available_providers = ort.get_available_providers()
    console.print(f"[dim]Available ONNX providers: {', '.join(available_providers)}[/dim]")

    if 'CUDAExecutionProvider' not in available_providers:
        console.print("[red]✗ CUDAExecutionProvider not available in onnxruntime[/red]")
        console.print("[red]  Check if onnxruntime-gpu is installed and CUDA libraries are accessible[/red]")
        raise RuntimeError("CUDA provider not available in onnxruntime")

    providers = [
        (
            'CUDAExecutionProvider', {
                'device_id': 0,
                'arena_extend_strategy': 'kNextPowerOfTwo',
                'gpu_mem_limit': 8 * 1024 * 1024 * 1024,
                'cudnn_conv_algo_search': 'EXHAUSTIVE',
                'do_copy_in_default_stream': True,
            },
        ),
    ]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")
        warnings.filterwarnings("ignore", category=FutureWarning, module="insightface")

        console.print(f"[cyan]Loading {settings.face_recognition.model_name} face detection model (GPU-only)...[/cyan]")

        try:
            face_app = FaceAnalysis(name=settings.face_recognition.model_name, root=model_root, providers=providers)
            face_app.prepare(
                ctx_id=0,
                det_size=settings.face_recognition.detection_size,
                det_thresh=settings.character.reference_detection_threshold,
            )
        except Exception as e:
            console.print("[red]✗ Failed to initialize face detection on GPU[/red]")
            console.print(f"[red]  Error: {e}[/red]")
            console.print("[red]  Ensure CUDA and onnxruntime-gpu are properly configured[/red]")
            raise RuntimeError("GPU required but face detection initialization failed") from e

        actual_providers = face_app.models['detection'].session.get_providers()

        if 'CUDAExecutionProvider' not in actual_providers:
            console.print("[red]✗ CUDA provider not active after initialization[/red]")
            console.print(f"[red]  Active providers: {', '.join(actual_providers)}[/red]")
            raise RuntimeError("CUDA required but not available for face detection")

    console.print(f"[green]✓ Face detection initialized ({settings.face_recognition.model_name})[/green]")
    console.print("[dim]  Device: GPU (CUDA)[/dim]")
    console.print(f"[dim]  Detection size: {settings.face_recognition.detection_size}[/dim]")
    console.print(f"[dim]  Detection threshold (for reference processing): {settings.character.reference_detection_threshold}[/dim]")
    console.print(f"[dim]  Model cache: {model_root}[/dim]")

    return face_app
