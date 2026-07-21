#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Download static FFmpeg binary on Linux if not installed
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found. Downloading static FFmpeg build for Linux..."
    mkdir -p bin
    curl -sL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJ --strip-components=1 -C bin/ ffmpeg-*-amd64-static/ffmpeg ffmpeg-*-amd64-static/ffprobe || true
fi
