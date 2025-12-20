# Test NVENC w izolacji

## Buildowanie
```bash
cd test-nvenc
docker build -t test-nvenc -f Dockerfile.test .
```

## Uruchomienie testu
```bash
docker run --gpus all --rm test-nvenc bash /test-nvenc.sh
```

## Co testujemy?
1. Czy jellyfin-ffmpeg ma dostępne enkodery nvenc
2. Czy da się transkodować testowe wideo używając h264_nvenc
3. Czy NVIDIA_DRIVER_CAPABILITIES=all wystarczy do obsługi NVENC bez mapowania urządzeń z WSL2
