# OpenCV — Release Notes

---

## v1.0.0 — March 2026

**Initial public release.**

OpenCV is a free, open-source adaptive controller for macOS that turns your webcam into a full input device using facial movements and hand gestures.

### Features
- **Eye blinks** — blink left, right, or both eyes to trigger any key
- **Head movement** — turn, tilt, and roll in 6 directions with adjustable sensitivity
- **Mouth & brows** — open mouth, raise eyebrows, or smile — each maps to a separate action
- **Hand gestures** — thumbs up, peace sign, fist, open palm, point up, ILY sign
- **Hand position** — move your hand left, right, up, or down in frame for directional control
- **Full keyboard support** — tap, hold, or combo any key (space, arrows, WASD, F-keys, Cmd+anything)
- **Configurable switches** — set threshold and cooldown independently per switch
- **Profile system** — save and load named profiles (stored in ~/Library/Application Support/CVController)
- **Default profile** — ships with 9 pre-configured switches (blinks, head turns, head tilts, head rolls)
- **System tray** — runs silently in the menu bar; close the window and it keeps tracking
- **Global hotkey** — press **8** from any app to toggle tracking on/off
- **Standalone .app** — no Python or Terminal required; double-click to launch
- **Camera flip** — horizontal mirror toggle for front-facing cameras

### Technical
- Built with Python 3.11, MediaPipe, OpenCV, PyQt6, pynput
- Face detection: MediaPipe FaceLandmarker (478 landmarks, blendshapes, head pose matrix)
- Hand detection: MediaPipe GestureRecognizer (21 landmarks, 7 gesture classes)
- Detection smoothing: 5-frame rolling average to reduce noise and false triggers
- Camera capture runs on main thread (macOS requirement); MediaPipe runs in background thread
- Bundled as standalone macOS .app via PyInstaller

### Requirements
- macOS 12 Monterey or later
- Built-in or external webcam
- Camera permission (prompted on first launch)
- Accessibility permission (System Settings → Privacy & Security → Accessibility → + OpenCV)

### Known Limitations
- macOS only (no Windows or Linux support in this release)
- Single camera only (index 0)
- Hand gesture detection requires good lighting and a clear view of the hand

---

*Made by Jacob Majors for Ramsey Mussalum's Design for Social Good class at Sonoma Academy, March 2026.*
*Source code: https://github.com/jacob-majors/open-CV*
