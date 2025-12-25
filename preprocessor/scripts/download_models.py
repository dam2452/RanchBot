#!/usr/bin/env python3
import logging

from preprocessor.config.config import settings

logger = logging.getLogger(__name__)


def log(msg):
    logger.info(f"[download_models] {msg}")

def download_whisper_model():
    try:
        from faster_whisper import WhisperModel  # pylint: disable=import-outside-toplevel
        model_name = settings.whisper.model
        log(f"Checking Whisper model: {model_name}")
        WhisperModel(model_name, device="cuda", compute_type="float16")
        log(f"✓ Whisper model '{model_name}' ready")
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"⚠ Whisper model download failed: {e}")

def download_embedding_model():
    try:
        import torch  # pylint: disable=import-outside-toplevel
        from transformers import AutoModel  # pylint: disable=import-outside-toplevel

        model_name = settings.embedding.model_name
        log(f"Checking embedding model: {model_name}")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available, GPU is required for embedding model")
        AutoModel.from_pretrained(
            model_name,
            torch_dtype="float16",
            device_map="cuda",
            trust_remote_code=True,
        )
        log(f"✓ Embedding model '{model_name}' ready on cuda")
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"⚠ Embedding model download failed: {e}")

def download_transnet_model():
    try:
        import torch  # pylint: disable=import-outside-toplevel
        from transnetv2_pytorch import TransNetV2  # pylint: disable=import-outside-toplevel

        log("Checking TransNetV2 model")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available, GPU is required")
        model = TransNetV2()
        _ = model.cuda()
        log("✓ TransNetV2 model ready on cuda")
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"⚠ TransNetV2 model check failed: {e}")

if __name__ == "__main__":
    log("Downloading/checking ML models...")
    download_whisper_model()
    download_embedding_model()
    download_transnet_model()
    log("Model check complete")
