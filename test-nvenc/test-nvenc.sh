#!/bin/bash

echo "=== Test 1: Sprawdzanie dostępności enkoderów NVENC ==="
ffmpeg -encoders | grep nvenc

echo ""
echo "=== Test 2: Próba transkodowania testowego wideo ==="
ffmpeg -y -vsync 0 -hwaccel cuda -hwaccel_output_format cuda \
  -f lavfi -i testsrc=size=1920x1080:rate=30:duration=5 \
  -c:v h264_nvenc -preset p4 -cq 20 /tmp/test_output.mp4

if [ -f /tmp/test_output.mp4 ]; then
    echo ""
    echo "=== SUCCESS: Plik testowy został utworzony ==="
    ls -lh /tmp/test_output.mp4
    ffprobe /tmp/test_output.mp4 2>&1 | grep "Video:"
else
    echo ""
    echo "=== FAILED: Plik testowy nie został utworzony ==="
    exit 1
fi
