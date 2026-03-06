#!/bin/bash
set -e
echo "=== OpenCV Controller Setup ==="

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Downloading models..."
mkdir -p resources

curl -L -o resources/face_landmarker.task \
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

curl -L -o resources/gesture_recognizer.task \
  "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"

echo ""
echo "=== Done! Run: source .venv/bin/activate && python main.py ==="
