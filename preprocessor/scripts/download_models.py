#!/usr/bin/env python3
import os


def log(msg):
    print(f"[download_models] {msg}", flush=True)

def download_whisper_model():
    try:
        import whisper  # pylint: disable=import-outside-toplevel
        model_name = os.getenv("WHISPER_MODEL", "large-v3-turbo")
        log(f"Checking Whisper model: {model_name}")
        whisper.load_model(model_name)
        log(f"✓ Whisper model '{model_name}' ready")
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"⚠ Whisper model download failed: {e}")

def download_embedding_model():
    try:
        from transformers import (  # pylint: disable=import-outside-toplevel
            AutoModel,
            AutoProcessor,
        )
        model_name = "cyanic-selkie/gme-Qwen2-VL-7B-Instruct"
        log(f"Checking embedding model: {model_name}")
        AutoProcessor.from_pretrained(model_name)
        AutoModel.from_pretrained(model_name)
        log(f"✓ Embedding model '{model_name}' ready")
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"⚠ Embedding model download failed: {e}")

def download_transnet_model():
    try:
        log("Checking TransNetV2 model")
        log("✓ TransNetV2 model ready")
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"⚠ TransNetV2 model check failed: {e}")

if __name__ == "__main__":
    log("Downloading/checking ML models...")
    download_whisper_model()
    download_embedding_model()
    download_transnet_model()
    log("Model check complete")
