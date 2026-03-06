#!/bin/bash
# Builds OpenCV.app — a standalone Mac application anyone can download and run.
# Run this once after setup.sh. Requires Python 3.11+.

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || true
source .venv/bin/activate

pip install --quiet pyinstaller

echo "Building OpenCV.app..."
pyinstaller \
  --noconfirm \
  --windowed \
  --name "OpenCV" \
  --icon "resources/icon.png" \
  --add-data "resources/face_landmarker.task:resources" \
  --add-data "resources/gesture_recognizer.task:resources" \
  --add-data "resources/icon.png:resources" \
  --add-data "profiles:profiles" \
  --collect-all mediapipe \
  --collect-all cv2 \
  --hidden-import pynput \
  --hidden-import pynput.keyboard \
  --hidden-import pynput.mouse \
  --hidden-import PyQt6 \
  --hidden-import PyQt6.QtWidgets \
  --hidden-import PyQt6.QtCore \
  --hidden-import PyQt6.QtGui \
  main.py

echo ""
echo "=== Build complete! ==="
echo "App is at: dist/OpenCV.app"
echo ""
echo "To distribute: zip it up"
echo "  cd dist && zip -r OpenCV.app.zip OpenCV.app"
echo ""
echo "IMPORTANT: Users must grant Accessibility permission to OpenCV.app"
echo "  System Settings → Privacy & Security → Accessibility → + OpenCV"
