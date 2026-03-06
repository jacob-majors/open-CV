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

# Add camera permission to Info.plist (required for macOS camera access)
PLIST="dist/OpenCV.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string 'OpenCV uses your camera to detect facial movements and hand gestures for adaptive control.'" "$PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSCameraUsageDescription 'OpenCV uses your camera to detect facial movements and hand gestures for adaptive control.'" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'OpenCV does not use the microphone, but macOS may require this entry.'" "$PLIST" 2>/dev/null || true

# Re-sign after plist modification (strip resource forks first)
find dist/OpenCV.app -exec xattr -c {} \; 2>/dev/null
find dist/OpenCV.app -name "._*" -delete 2>/dev/null
codesign --force --deep --no-strict -s - dist/OpenCV.app 2>/dev/null || true

echo ""
echo "=== Build complete! ==="
echo "App is at: dist/OpenCV.app"
echo ""
echo "To distribute: zip it up"
echo "  cd dist && ditto -c -k --keepParent OpenCV.app OpenCV.app.zip"
echo ""
echo "IMPORTANT: Users must grant Accessibility permission to OpenCV.app"
echo "  System Settings → Privacy & Security → Accessibility → + OpenCV"
