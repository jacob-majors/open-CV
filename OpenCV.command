#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Load Homebrew into PATH
eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || true

# Find Python 3.11+
PYTHON=""
for p in \
    /opt/homebrew/bin/python3.13 \
    /opt/homebrew/bin/python3.12 \
    /opt/homebrew/bin/python3.11 \
    /usr/local/bin/python3.13 \
    /usr/local/bin/python3.12 \
    /usr/local/bin/python3.11 \
    $(which python3 2>/dev/null); do
    if [ -x "$p" ]; then
        VER=$("$p" -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
        MAJOR=$("$p" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        if [ "$MAJOR" = "3" ] && [ "$VER" -ge 11 ] 2>/dev/null; then
            PYTHON="$p"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo "ERROR: Python 3.11 or newer not found."
    echo ""
    echo "Fix: run these in Terminal:"
    echo "  eval \"\$(/opt/homebrew/bin/brew shellenv)\""
    echo "  brew install python@3.11"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo "Using Python: $PYTHON ($("$PYTHON" --version))"

# Rebuild venv if it uses the wrong Python
if [ -f ".venv/bin/python" ]; then
    VENV_MINOR=$(.venv/bin/python -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
    if [ -z "$VENV_MINOR" ] || [ "$VENV_MINOR" -lt 11 ] 2>/dev/null; then
        echo "Upgrading Python environment..."
        rm -rf .venv
    fi
fi

# Create venv if missing
if [ ! -f ".venv/bin/python" ]; then
    echo "Setting up environment (first time — takes ~1 minute)..."
    "$PYTHON" -m venv .venv
    source .venv/bin/activate
    pip install --quiet -r requirements.txt
    echo "Done!"
else
    source .venv/bin/activate
fi

# Download model if missing
if [ ! -f "resources/face_landmarker.task" ]; then
    echo "Downloading face tracking model..."
    mkdir -p resources
    curl -L -o resources/face_landmarker.task \
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
fi

echo "Launching OpenCV..."
python main.py

# Keep window open if app crashed
if [ $? -ne 0 ]; then
    echo ""
    echo "App exited with an error. See above for details."
    read -p "Press Enter to close..."
fi
