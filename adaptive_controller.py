"""
Adaptive Controller — Face + Physical Input
Connects an Arduino Leonardo adaptive controller (USB serial) to an OpenCV
face-tracking mouse system.
"""

import sys
import os
import json
import math
import time
import platform
from datetime import datetime

# ── PyQt6 (required) ──────────────────────────────────────────────────────────
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy, QScrollArea,
    QPlainTextEdit, QTextEdit, QSlider, QFileDialog, QMessageBox,
    QSplitter
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QObject, QTimer, QRect, QRectF, QPointF, QSize
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QRadialGradient, QLinearGradient,
    QPalette, QImage, QPixmap, QFontMetrics, QTextCursor
)

# ── Optional: cv2 ─────────────────────────────────────────────────────────────
try:
    import cv2
    CV2 = True
except ImportError:
    CV2 = False

# ── Optional: numpy ───────────────────────────────────────────────────────────
try:
    import numpy as np
    NUMPY = True
except ImportError:
    NUMPY = False

# ── Optional: serial ──────────────────────────────────────────────────────────
try:
    import serial
    import serial.tools.list_ports
    SERIAL = True
except ImportError:
    SERIAL = False

# ── Optional: pynput ─────────────────────────────────────────────────────────
try:
    from pynput.mouse import Button as MouseButton, Controller as MouseController
    from pynput.keyboard import Key, Controller as KeyboardController
    PYNPUT = True
except ImportError:
    PYNPUT = False

# ── Existing MediaPipe FaceTracker ────────────────────────────────────────────
try:
    from cv_controller.core.tracker import FaceTracker as _FaceTracker
    MEDIAPIPE = True
except ImportError:
    _FaceTracker = None
    MEDIAPIPE = False

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS / THEME
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK    = "#0a0a0f"
BG_PANEL   = "#111118"
BG_WIDGET  = "#1a1a24"
BG_INPUT   = "#16161e"
ACCENT     = "#00ff88"
ACCENT2    = "#00ccff"
WARN       = "#ff8c00"
DANGER     = "#ff3333"
FG         = "#e0e0e0"
FG_DIM     = "#888899"

MONO_FONT = "Menlo" if platform.system() == "Darwin" else "Courier New"

APP_TITLE = "Adaptive Controller — Face + Physical Input"

ACTIONS = [
    "None",
    "Left Click",
    "Right Click",
    "Middle Click",
    "Scroll Up",
    "Scroll Down",
    "Space Bar",
    "Enter",
    "Escape",
    "Tab",
    "Arrow Up",
    "Arrow Down",
    "Arrow Left",
    "Arrow Right",
    "Toggle Face Tracking",
    "Speed Up Cursor",
    "Slow Down Cursor",
]

META_ACTIONS = {"Toggle Face Tracking", "Speed Up Cursor", "Slow Down Cursor"}

PHYSICAL_INPUTS = ["Button 1", "Button 2", "J1", "J2", "J3", "J4"]
FACE_INPUTS = [
    "Look Left", "Look Right", "Look Up", "Look Down",
    "Mouth Open", "Blink Left Eye", "Blink Right Eye"
]

ARDUINO_SKETCH = """\
// Adaptive Controller Arduino Sketch
// Pins 2-7 as INPUT_PULLUP; sends JSON every 20ms at 9600 baud

void setup() {
  Serial.begin(9600);
  for (int pin = 2; pin <= 7; pin++) {
    pinMode(pin, INPUT_PULLUP);
  }
}

void loop() {
  int b1 = !digitalRead(2);  // LOW = pressed (inverted)
  int b2 = !digitalRead(3);
  int j1 = !digitalRead(4);
  int j2 = !digitalRead(5);
  int j3 = !digitalRead(6);
  int j4 = !digitalRead(7);

  Serial.print("{");
  Serial.print("\\"b1\\":"); Serial.print(b1); Serial.print(",");
  Serial.print("\\"b2\\":"); Serial.print(b2); Serial.print(",");
  Serial.print("\\"j1\\":"); Serial.print(j1); Serial.print(",");
  Serial.print("\\"j2\\":"); Serial.print(j2); Serial.print(",");
  Serial.print("\\"j3\\":"); Serial.print(j3); Serial.print(",");
  Serial.print("\\"j4\\":"); Serial.print(j4);
  Serial.println("}");

  delay(20);
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# ActionEmitter
# ─────────────────────────────────────────────────────────────────────────────
class ActionEmitter:
    def __init__(self):
        if PYNPUT:
            self._mouse = MouseController()
            self._keyboard = KeyboardController()
        else:
            self._mouse = None
            self._keyboard = None

    def fire(self, action: str):
        if not PYNPUT or action == "None" or action in META_ACTIONS:
            return
        if action == "Left Click":
            self._mouse.click(MouseButton.left)
        elif action == "Right Click":
            self._mouse.click(MouseButton.right)
        elif action == "Middle Click":
            self._mouse.click(MouseButton.middle)
        elif action == "Scroll Up":
            self._mouse.scroll(0, 3)
        elif action == "Scroll Down":
            self._mouse.scroll(0, -3)
        elif action == "Space Bar":
            self._keyboard.tap(Key.space)
        elif action == "Enter":
            self._keyboard.tap(Key.enter)
        elif action == "Escape":
            self._keyboard.tap(Key.esc)
        elif action == "Tab":
            self._keyboard.tap(Key.tab)
        elif action == "Arrow Up":
            self._keyboard.tap(Key.up)
        elif action == "Arrow Down":
            self._keyboard.tap(Key.down)
        elif action == "Arrow Left":
            self._keyboard.tap(Key.left)
        elif action == "Arrow Right":
            self._keyboard.tap(Key.right)

    def move_cursor_relative(self, dx: float, dy: float):
        if PYNPUT and self._mouse is not None:
            self._mouse.move(int(dx), int(dy))


# ─────────────────────────────────────────────────────────────────────────────
# SerialThread
# ─────────────────────────────────────────────────────────────────────────────
class SerialThread(QThread):
    data_received       = pyqtSignal(object)
    connection_changed  = pyqtSignal(bool, str)
    error_occurred      = pyqtSignal(str)

    def __init__(self, port: str, baud: int = 9600):
        super().__init__()
        self._port = port
        self._baud = baud
        self._running = False
        self._serial = None

    def run(self):
        self._running = True
        if not SERIAL:
            self.error_occurred.emit("pyserial not installed")
            self.connection_changed.emit(False, "pyserial not installed")
            return
        try:
            self._serial = serial.Serial(self._port, self._baud, timeout=1)
            self.connection_changed.emit(True, f"Connected on {self._port}")
        except serial.SerialException as e:
            self.error_occurred.emit(str(e))
            self.connection_changed.emit(False, str(e))
            return

        while self._running:
            try:
                if self._serial.in_waiting:
                    line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        try:
                            data = json.loads(line)
                            self.data_received.emit(data)
                        except json.JSONDecodeError:
                            pass
                else:
                    self.msleep(5)
            except serial.SerialException as e:
                self.error_occurred.emit(str(e))
                self.connection_changed.emit(False, str(e))
                break

        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass

    def stop(self):
        self._running = False
        self.wait(2000)


# ─────────────────────────────────────────────────────────────────────────────
# FaceTrackingAdapter  (wraps the existing MediaPipe-based FaceTracker)
# ─────────────────────────────────────────────────────────────────────────────
class FaceTrackingAdapter(QObject):
    """
    Wraps cv_controller.core.tracker.FaceTracker.
    Converts MediaPipe blendshapes + head-pose data into the gesture booleans
    this GUI expects, handles hold-time debounce, cursor movement, and
    draws annotations (bounding box, crosshair, overlays) onto each frame.

    Falls back to a stub that emits an error if MediaPipe is not available.
    """
    frame_ready    = pyqtSignal(object)   # annotated BGR numpy array
    face_data      = pyqtSignal(object)   # adapted dict for GUI
    gesture_fired  = pyqtSignal(str, str) # (gesture, action) after hold threshold
    error_occurred = pyqtSignal(str)

    _POSE_MAX_DEG    = 45.0
    _BLINK_THRESHOLD = 0.35   # eyeBlinkLeft/Right blendshape score
    _MOUTH_THRESHOLD = 0.55   # jawOpen blendshape score

    def __init__(self, parent=None):
        super().__init__(parent)
        self._emitter = ActionEmitter()

        # Settable from main thread
        self.tracking_enabled = True
        self.deadzone         = 0.15
        self.cursor_speed     = 8.0
        self.gesture_hold_ms  = 300
        self.mappings         = {}   # gesture → action

        # Gesture debounce state
        self._hold_start = {g: None  for g in FACE_INPUTS}
        self._fired      = {g: False for g in FACE_INPUTS}

        # FPS counter (updated in _on_raw_frame, read in _on_face_data)
        self._fps_counter  = 0
        self._fps_start    = time.time()
        self._current_fps  = 0.0
        self._latest_frame = None   # last raw BGR frame from tracker

        # Build model paths relative to this file's directory
        base          = os.path.dirname(os.path.abspath(__file__))
        face_model    = os.path.join(base, "resources", "face_landmarker.task")
        gesture_model = os.path.join(base, "resources", "gesture_recognizer.task")

        self._tracker = None
        if not MEDIAPIPE:
            return  # error emitted in start()

        if not os.path.exists(face_model):
            return  # error emitted in start()

        gm = gesture_model if os.path.exists(gesture_model) else None
        self._tracker = _FaceTracker(face_model, gm)
        self._tracker.frame_ready.connect(self._on_raw_frame)
        self._tracker.face_data.connect(self._on_face_data)
        self._tracker.tracking_error.connect(self.error_occurred)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if not MEDIAPIPE:
            self.error_occurred.emit("mediapipe not installed. Run: bash setup.sh")
            return
        if self._tracker is None:
            self.error_occurred.emit(
                "face_landmarker.task model not found.\nRun: bash setup.sh"
            )
            return
        self._fps_start = time.time()
        self._tracker.start()

    def stop(self):
        if self._tracker:
            self._tracker.stop()

    def set_params(self, deadzone: float, speed: float, hold_ms: int):
        self.deadzone        = deadzone
        self.cursor_speed    = speed
        self.gesture_hold_ms = hold_ms

    # ── Tracker signal handlers ───────────────────────────────────────────────

    def _on_raw_frame(self, frame):
        """Save the latest raw frame and update FPS counter."""
        self._latest_frame = frame
        self._fps_counter += 1
        now = time.time()
        elapsed = now - self._fps_start
        if elapsed >= 1.0:
            self._current_fps = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_start   = now

    def _on_face_data(self, data: dict):
        """
        Process MediaPipe face_data, annotate the latest frame, evaluate
        gesture debounce, move cursor, and emit adapted signals.
        """
        if self._latest_frame is None:
            return

        annotated = self._latest_frame.copy()
        h, w = annotated.shape[:2]

        face_detected = data.get("face_detected", False)
        blendshapes   = data.get("blendshapes", {})
        pose          = data.get("pose", {})
        landmarks     = data.get("landmarks", [])

        current_gestures = {g: False for g in FACE_INPUTS}
        face_x_pct = 50
        face_y_pct = 50
        zone = "CENTER"

        if face_detected and landmarks:
            xs = [pt[0] for pt in landmarks]
            ys = [pt[1] for pt in landmarks]

            # Bounding box with small padding
            fx1 = max(0, min(xs) - 5)
            fy1 = max(0, min(ys) - 5)
            fx2 = min(w, max(xs) + 5)
            fy2 = min(h, max(ys) + 5)
            cv2.rectangle(annotated, (fx1, fy1), (fx2, fy2), (0, 255, 136), 2)

            # Face centre from landmark centroid
            face_cx = sum(xs) / len(xs)
            face_cy = sum(ys) / len(ys)
            face_x_pct = int((face_cx / w) * 100)
            face_y_pct = int((face_cy / h) * 100)

            # Crosshair
            cx_int, cy_int = int(face_cx), int(face_cy)
            cv2.line(annotated, (cx_int - 20, cy_int), (cx_int + 20, cy_int), (0, 255, 136), 1)
            cv2.line(annotated, (cx_int, cy_int - 20), (cx_int, cy_int + 20), (0, 255, 136), 1)

            # Head pose → direction zone
            yaw   = pose.get("yaw",   0.0)
            pitch = pose.get("pitch", 0.0)
            dz_deg = self.deadzone * self._POSE_MAX_DEG

            if abs(yaw) < dz_deg and abs(pitch) < dz_deg:
                zone = "CENTER"
            elif abs(yaw) >= abs(pitch):
                zone = "LEFT" if yaw < 0 else "RIGHT"
            else:
                zone = "UP" if pitch > 0 else "DOWN"

            current_gestures["Look Left"]  = (zone == "LEFT")
            current_gestures["Look Right"] = (zone == "RIGHT")
            current_gestures["Look Up"]    = (zone == "UP")
            current_gestures["Look Down"]  = (zone == "DOWN")

            # Blink detection via blendshapes (far more reliable than Haar)
            current_gestures["Blink Left Eye"]  = (
                blendshapes.get("eyeBlinkLeft",  0.0) >= self._BLINK_THRESHOLD
            )
            current_gestures["Blink Right Eye"] = (
                blendshapes.get("eyeBlinkRight", 0.0) >= self._BLINK_THRESHOLD
            )

            # Mouth open via jawOpen blendshape
            current_gestures["Mouth Open"] = (
                blendshapes.get("jawOpen", 0.0) >= self._MOUTH_THRESHOLD
            )

            # Cursor movement from head pose (only when tracking enabled)
            if self.tracking_enabled:
                max_deg = self._POSE_MAX_DEG - dz_deg
                move_x = move_y = 0.0
                if max_deg > 0:
                    if abs(yaw) > dz_deg:
                        sx = 1.0 if yaw > 0 else -1.0
                        move_x = sx * min(1.0, (abs(yaw) - dz_deg) / max_deg)
                    if abs(pitch) > dz_deg:
                        # Positive pitch = look up → cursor moves up (negative y)
                        sy = -1.0 if pitch > 0 else 1.0
                        move_y = sy * min(1.0, (abs(pitch) - dz_deg) / max_deg)
                if move_x != 0.0 or move_y != 0.0:
                    self._emitter.move_cursor_relative(
                        move_x * self.cursor_speed,
                        move_y * self.cursor_speed,
                    )

        else:
            # No face overlay
            text = "NO FACE DETECTED"
            font = cv2.FONT_HERSHEY_SIMPLEX
            ts, _ = cv2.getTextSize(text, font, 0.7, 2)
            tx = (w - ts[0]) // 2
            ty = (h + ts[1]) // 2
            cv2.putText(annotated, text, (tx, ty), font, 0.7, (0, 0, 255), 2)

        # Tracking-paused overlay
        if not self.tracking_enabled:
            cv2.putText(
                annotated, "TRACKING PAUSED", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2,
            )

        # FPS overlay
        fps_text = f"FPS: {self._current_fps:.1f}"
        fps_sz, _ = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(
            annotated, fps_text,
            (w - fps_sz[0] - 10, 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 136), 1,
        )

        # Gesture debounce + fire
        now_t = time.time()
        for gesture, active in current_gestures.items():
            action = self.mappings.get(gesture, "None")
            if active:
                if self._hold_start[gesture] is None:
                    self._hold_start[gesture] = now_t
                    self._fired[gesture] = False
                elif not self._fired[gesture]:
                    elapsed_ms = (now_t - self._hold_start[gesture]) * 1000
                    if elapsed_ms >= self.gesture_hold_ms:
                        if action not in ("None", "") and action not in META_ACTIONS:
                            self._emitter.fire(action)
                        if action not in ("None", ""):
                            self.gesture_fired.emit(gesture, action)
                        self._fired[gesture] = True
            else:
                self._hold_start[gesture] = None
                self._fired[gesture] = False

        # Emit adapted signals
        self.frame_ready.emit(annotated)
        self.face_data.emit({
            "face_detected": face_detected,
            "face_x_pct":    face_x_pct,
            "face_y_pct":    face_y_pct,
            "zone":          zone,
            "gestures":      current_gestures,
            "fps":           self._current_fps,
        })

    # ── Stub methods so MainWindow can call .stop() unconditionally ────────────
    def isRunning(self) -> bool:
        return self._tracker is not None and self._tracker.isRunning()




# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────
def make_combo(items) -> QComboBox:
    cb = QComboBox()
    cb.addItems(items)
    cb.setFont(QFont(MONO_FONT, 10))
    cb.setStyleSheet(f"""
        QComboBox {{
            background: {BG_INPUT};
            color: {FG};
            border: 1px solid #2a2a3e;
            border-radius: 4px;
            padding: 3px 6px;
            min-height: 22px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox QAbstractItemView {{
            background: {BG_INPUT};
            color: {FG};
            selection-background-color: #2a2a3e;
        }}
    """)
    return cb


def make_button(text: str, accent: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setFont(QFont(MONO_FONT, 10))
    if accent:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT};
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #00ffaa;
            }}
            QPushButton:pressed {{
                background: #00cc66;
            }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {BG_WIDGET};
                color: {FG};
                border: 1px solid #2a2a3e;
                border-radius: 4px;
                padding: 5px 12px;
            }}
            QPushButton:hover {{
                background: #222233;
                border-color: #3a3a5e;
            }}
            QPushButton:pressed {{
                background: #1a1a2e;
            }}
        """)
    return btn


def make_label(text: str, color: str = FG, size: int = 10, bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    weight = "bold" if bold else "normal"
    lbl.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight};")
    lbl.setFont(QFont(MONO_FONT, size))
    return lbl


def make_slider(min_val: int, max_val: int, value: int) -> QSlider:
    sl = QSlider(Qt.Orientation.Horizontal)
    sl.setMinimum(min_val)
    sl.setMaximum(max_val)
    sl.setValue(value)
    sl.setStyleSheet(f"""
        QSlider::groove:horizontal {{
            height: 4px;
            background: #2a2a3e;
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {ACCENT};
            border: none;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        QSlider::sub-page:horizontal {{
            background: {ACCENT};
            border-radius: 2px;
        }}
    """)
    return sl


# ─────────────────────────────────────────────────────────────────────────────
# LEDIndicator
# ─────────────────────────────────────────────────────────────────────────────
class LEDIndicator(QWidget):
    def __init__(self, label: str, on_color: str = ACCENT, width: int = 90, parent=None):
        super().__init__(parent)
        self._label    = label
        self._on_color = QColor(on_color)
        self._active   = False
        self.setFixedSize(width, 34)

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        dot_r  = 7
        dot_cx = dot_r + 4
        dot_cy = self.height() // 2

        # Dot
        if self._active:
            # Radial glow
            grad = QRadialGradient(dot_cx, dot_cy, dot_r * 2)
            grad.setColorAt(0.0, self._on_color)
            glow = QColor(self._on_color)
            glow.setAlpha(0)
            grad.setColorAt(1.0, glow)
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(dot_cx, dot_cy), dot_r * 2, dot_r * 2)
            p.setBrush(QBrush(self._on_color))
        else:
            p.setBrush(QBrush(QColor("#2a2a3e")))

        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(dot_cx, dot_cy), dot_r, dot_r)

        # Label
        p.setPen(QPen(QColor(FG if self._active else FG_DIM)))
        p.setFont(QFont(MONO_FONT, 9))
        text_x = dot_cx + dot_r + 6
        text_rect = QRect(text_x, 0, self.width() - text_x - 2, self.height())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# StatusDot
# ─────────────────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._connected = False
        self._alpha     = 255
        self._timer     = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._pulse)
        self._phase = 0.0

    def set_connected(self, connected: bool):
        self._connected = connected
        if connected:
            self._timer.start()
        else:
            self._timer.stop()
            self._alpha = 255
        self.update()

    def _pulse(self):
        self._phase += 0.15
        self._alpha = int(180 + 75 * math.sin(self._phase))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2
        cy = self.height() // 2
        r  = 6
        if self._connected:
            color = QColor(0, 255, 136, self._alpha)
        else:
            color = QColor(255, 51, 51, 255)
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# ActivityLog
# ─────────────────────────────────────────────────────────────────────────────
class ActivityLog(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self._max_lines = 120
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {BG_DARK};
                color: {ACCENT};
                border: 1px solid #1a1a2e;
                border-radius: 4px;
                font-family: {MONO_FONT};
                font-size: 11px;
            }}
        """)
        self.setFont(QFont(MONO_FONT, 9))

    def log(self, source: str, action: str, color: str = ACCENT):
        now = datetime.now()
        ts  = now.strftime("%H:%M:%S") + f".{now.microsecond // 1000:03d}"
        line = (
            f'<span style="color:{FG_DIM}">[{ts}]</span> '
            f'<span style="color:{ACCENT2}">{source}</span> '
            f'<span style="color:{color}">{action}</span>'
        )
        self.append(line)

        # Trim to max_lines
        doc = self.document()
        while doc.blockCount() > self._max_lines:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # remove trailing newline

        # Auto-scroll
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


# ─────────────────────────────────────────────────────────────────────────────
# ControllerWidget
# ─────────────────────────────────────────────────────────────────────────────
class ControllerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.button_states = {k: False for k in ["b1", "b2", "j1", "j2", "j3", "j4"]}
        self.setMinimumSize(260, 180)

    def set_state(self, states: dict):
        self.button_states.update(states)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 12
        w = self.width()
        h = self.height()

        body_rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        body_h    = body_rect.height()
        body_w    = body_rect.width()
        radius    = body_h * 0.35

        # Body
        p.setBrush(QBrush(QColor("#1e1e2e")))
        p.setPen(QPen(QColor("#333344"), 2))
        p.drawRoundedRect(body_rect, radius, radius)

        # Texture lines
        tex_color = QColor("#25253a")
        for i in range(1, 4):
            y = body_rect.top() + (body_h * i / 4)
            p.setPen(QPen(tex_color, 1))
            p.drawLine(
                QPointF(body_rect.left() + radius * 0.3, y),
                QPointF(body_rect.right() - radius * 0.3, y)
            )

        # ── Button 1 (left, ~28% x, 50% y) ──────────────────────────────────
        b1_cx = body_rect.left() + body_w * 0.28
        b1_cy = body_rect.top()  + body_h * 0.50
        b1_r  = min(body_w, body_h) * 0.17
        b1_active = self.button_states.get("b1", False)

        if b1_active:
            # Radial glow
            glow = QRadialGradient(b1_cx, b1_cy, b1_r * 2.5)
            glow.setColorAt(0.0, QColor(0, 255, 136, 160))
            glow.setColorAt(1.0, QColor(0, 255, 136, 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(b1_cx, b1_cy), b1_r * 2.5, b1_r * 2.5)
            p.setBrush(QBrush(QColor("#00ff88")))
            p.setPen(QPen(QColor("#00ff88"), 2))
        else:
            p.setBrush(QBrush(QColor("#2a2a3e")))
            p.setPen(QPen(QColor("#444455"), 2))

        p.drawEllipse(QPointF(b1_cx, b1_cy), b1_r, b1_r)

        # Label "1"
        p.setPen(QPen(QColor("#000000" if b1_active else FG_DIM)))
        p.setFont(QFont(MONO_FONT, max(10, int(b1_r * 0.9)), QFont.Weight.Bold))
        p.drawText(
            QRectF(b1_cx - b1_r, b1_cy - b1_r, b1_r * 2, b1_r * 2),
            Qt.AlignmentFlag.AlignCenter, "1"
        )

        # ── Button 2 (right, ~72% x, 50% y) ─────────────────────────────────
        b2_cx = body_rect.left() + body_w * 0.72
        b2_cy = body_rect.top()  + body_h * 0.50
        b2_r  = b1_r
        b2_active = self.button_states.get("b2", False)

        if b2_active:
            glow2 = QRadialGradient(b2_cx, b2_cy, b2_r * 2.5)
            glow2.setColorAt(0.0, QColor(255, 140, 0, 160))
            glow2.setColorAt(1.0, QColor(255, 140, 0, 0))
            p.setBrush(QBrush(glow2))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(b2_cx, b2_cy), b2_r * 2.5, b2_r * 2.5)
            p.setBrush(QBrush(QColor("#ff8c00")))
            p.setPen(QPen(QColor("#ff8c00"), 2))
        else:
            p.setBrush(QBrush(QColor("#2a2a3e")))
            p.setPen(QPen(QColor("#444455"), 2))

        p.drawEllipse(QPointF(b2_cx, b2_cy), b2_r, b2_r)

        p.setPen(QPen(QColor("#000000" if b2_active else FG_DIM)))
        p.setFont(QFont(MONO_FONT, max(10, int(b2_r * 0.9)), QFont.Weight.Bold))
        p.drawText(
            QRectF(b2_cx - b2_r, b2_cy - b2_r, b2_r * 2, b2_r * 2),
            Qt.AlignmentFlag.AlignCenter, "2"
        )

        # ── Center oval ───────────────────────────────────────────────────────
        oc_cx = body_rect.left() + body_w * 0.50
        oc_cy = body_rect.top()  + body_h * 0.50
        oc_rx = 18
        oc_ry = 12
        p.setBrush(QBrush(QColor("#252535")))
        p.setPen(QPen(QColor("#333344"), 1))
        p.drawEllipse(QPointF(oc_cx, oc_cy), oc_rx, oc_ry)
        p.setPen(QPen(QColor(FG_DIM)))
        p.setFont(QFont(MONO_FONT, 7, QFont.Weight.Bold))
        p.drawText(
            QRectF(oc_cx - oc_rx, oc_cy - oc_ry, oc_rx * 2, oc_ry * 2),
            Qt.AlignmentFlag.AlignCenter, "AC"
        )

        # ── Jack circles (J1–J4) ─────────────────────────────────────────────
        jack_keys = ["j1", "j2", "j3", "j4"]
        jack_y    = body_rect.bottom() - 20
        jack_r    = 8
        for i, jk in enumerate(jack_keys):
            jx = body_rect.left() + body_w * (0.20 + 0.20 * i)
            active = self.button_states.get(jk, False)
            if active:
                jglow = QRadialGradient(jx, jack_y, jack_r * 2.5)
                jglow.setColorAt(0.0, QColor(0, 170, 255, 160))
                jglow.setColorAt(1.0, QColor(0, 170, 255, 0))
                p.setBrush(QBrush(jglow))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(jx, jack_y), jack_r * 2.5, jack_r * 2.5)
                p.setBrush(QBrush(QColor("#00aaff")))
                p.setPen(QPen(QColor("#00aaff"), 1))
            else:
                p.setBrush(QBrush(QColor("#222233")))
                p.setPen(QPen(QColor("#333344"), 1))
            p.drawEllipse(QPointF(jx, jack_y), jack_r, jack_r)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# ZoneDiagram
# ─────────────────────────────────────────────────────────────────────────────
class ZoneDiagram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._zone = "CENTER"
        self.setMinimumHeight(110)
        self.setMaximumHeight(120)

    def set_zone(self, zone: str):
        if self._zone != zone:
            self._zone = zone
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cw = w / 3
        ch = h / 3

        # Grid layout: [row][col] → (zone_name, label)
        cells = [
            [None,      "UP",      None     ],
            ["LEFT",    "CENTER",  "RIGHT"  ],
            [None,      "DOWN",    None     ],
        ]
        labels = {
            "UP":     "UP",
            "LEFT":   "LEFT",
            "RIGHT":  "RIGHT",
            "DOWN":   "DOWN",
            "CENTER": "DEAD\nZONE",
        }

        for row in range(3):
            for col in range(3):
                zone_name = cells[row][col]
                if zone_name is None:
                    continue
                rx = col * cw
                ry = row * ch
                cell_rect = QRectF(rx + 2, ry + 2, cw - 4, ch - 4)

                if zone_name == self._zone:
                    fill = QColor(ACCENT2)
                    fill.setAlpha(200)
                    p.setBrush(QBrush(fill))
                    p.setPen(QPen(QColor(ACCENT2), 1))
                else:
                    p.setBrush(QBrush(QColor(BG_WIDGET)))
                    p.setPen(QPen(QColor("#2a2a3e"), 1))

                p.drawRoundedRect(cell_rect, 5, 5)

                text_color = QColor("#000000") if zone_name == self._zone else QColor(FG_DIM)
                p.setPen(QPen(text_color))
                p.setFont(QFont(MONO_FONT, 8, QFont.Weight.Bold))
                p.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, labels[zone_name])

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# LeftPanel
# ─────────────────────────────────────────────────────────────────────────────
class LeftPanel(QWidget):
    connect_requested    = pyqtSignal(str)
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected  = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Title
        layout.addWidget(make_label("CONTROLLER", ACCENT, 13, True))

        # Port row
        port_row = QHBoxLayout()
        self._port_combo = make_combo([])
        self._refresh_ports()
        port_row.addWidget(self._port_combo, 1)
        refresh_btn = make_button("↻")
        refresh_btn.setFixedWidth(32)
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(refresh_btn)
        layout.addLayout(port_row)

        # Connect row
        conn_row = QHBoxLayout()
        self._status_dot = StatusDot()
        conn_row.addWidget(self._status_dot)
        self._status_label = make_label("Disconnected", FG_DIM, 9)
        conn_row.addWidget(self._status_label, 1)
        self._connect_btn = make_button("Connect", accent=True)
        self._connect_btn.clicked.connect(self._toggle_connect)
        conn_row.addWidget(self._connect_btn)
        layout.addLayout(conn_row)

        # Baud row
        baud_row = QHBoxLayout()
        baud_row.addWidget(make_label("Baud:", FG_DIM, 9))
        self._baud_combo = make_combo(["9600", "115200", "57600"])
        self._baud_combo.setFixedWidth(80)
        baud_row.addWidget(self._baud_combo)
        baud_row.addStretch()
        layout.addLayout(baud_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3e;")
        layout.addWidget(sep)

        # Controller widget
        self._controller_widget = ControllerWidget()
        layout.addWidget(self._controller_widget, 1)

        # Jack label row
        jack_row = QHBoxLayout()
        for jlbl in ["J1", "J2", "J3", "J4"]:
            lbl = make_label(jlbl, FG_DIM, 9)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            jack_row.addWidget(lbl, 1)
        layout.addLayout(jack_row)

        # Arduino sketch
        layout.addWidget(make_label("ARDUINO SKETCH", FG_DIM, 9))
        sketch_edit = QPlainTextEdit()
        sketch_edit.setReadOnly(True)
        sketch_edit.setPlainText(ARDUINO_SKETCH)
        sketch_edit.setMaximumHeight(140)
        sketch_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {BG_DARK};
                color: #888899;
                border: 1px solid #1a1a2e;
                border-radius: 4px;
                font-family: {MONO_FONT};
                font-size: 9px;
            }}
        """)
        layout.addWidget(sketch_edit)

    def _get_ports(self):
        if SERIAL:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            return ports if ports else ["(no devices found)"]
        else:
            return ["(pyserial not installed)"]

    def _refresh_ports(self):
        prev = self._port_combo.currentText() if hasattr(self, "_port_combo") else ""
        ports = self._get_ports()
        self._port_combo.clear()
        self._port_combo.addItems(ports)
        idx = self._port_combo.findText(prev)
        if idx >= 0:
            self._port_combo.setCurrentIndex(idx)

    def _toggle_connect(self):
        if self._connected:
            self.disconnect_requested.emit()
        else:
            port = self._port_combo.currentText()
            self.connect_requested.emit(port)

    def set_connected(self, connected: bool, message: str):
        self._connected = connected
        self._status_dot.set_connected(connected)
        self._status_label.setText(message)
        self._status_label.setStyleSheet(
            f"color: {ACCENT if connected else FG_DIM}; font-size: 9px;"
        )
        self._connect_btn.setText("Disconnect" if connected else "Connect")

    def update_controller(self, states: dict):
        self._controller_widget.set_state(states)


# ─────────────────────────────────────────────────────────────────────────────
# MiddlePanel
# ─────────────────────────────────────────────────────────────────────────────
class MiddlePanel(QWidget):
    tracking_toggled = pyqtSignal(bool)

    # Map gesture name → short symbol
    _GESTURE_SYMBOLS = {
        "Look Left":      "←",
        "Look Right":     "→",
        "Look Up":        "↑",
        "Look Down":      "↓",
        "Mouth Open":     "😮",
        "Blink Left Eye": "L👁",
        "Blink Right Eye":"R👁",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gesture_indicators = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(make_label("FACE TRACKING", ACCENT, 13, True))

        # Camera label
        self._cam_label = QLabel("Camera initializing...")
        self._cam_label.setMinimumSize(320, 240)
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_label.setStyleSheet(f"background: black; color: {FG_DIM}; font-size: 12px;")
        layout.addWidget(self._cam_label, 1)

        # Status bar row
        status_row = QHBoxLayout()
        self._track_toggle = QPushButton("● TRACKING ON")
        self._track_toggle.setCheckable(True)
        self._track_toggle.setChecked(True)
        self._track_toggle.setFont(QFont(MONO_FONT, 9))
        self._track_toggle.setStyleSheet(f"""
            QPushButton {{
                background: {BG_WIDGET};
                color: {ACCENT};
                border: 1px solid {ACCENT};
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QPushButton:checked {{
                background: {BG_WIDGET};
                color: {ACCENT};
                border-color: {ACCENT};
            }}
            QPushButton:!checked {{
                color: {FG_DIM};
                border-color: {FG_DIM};
            }}
        """)
        self._track_toggle.toggled.connect(self._on_toggle)
        status_row.addWidget(self._track_toggle)

        self._pos_label = make_label("X: 50%  Y: 50%", FG_DIM, 9)
        status_row.addWidget(self._pos_label)
        self._fps_label = make_label("0 FPS", ACCENT2, 9)
        status_row.addWidget(self._fps_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        layout.addWidget(make_label("MOVEMENT ZONES", FG_DIM, 9))
        self._zone_diagram = ZoneDiagram()
        layout.addWidget(self._zone_diagram)

        layout.addWidget(make_label("FACE ACTIONS", FG_DIM, 9))

        # Gesture indicator row
        gesture_row = QHBoxLayout()
        gesture_row.setSpacing(4)
        for gesture, symbol in self._GESTURE_SYMBOLS.items():
            ind = LEDIndicator(symbol, ACCENT2, width=50)
            self.gesture_indicators[gesture] = ind
            gesture_row.addWidget(ind)
        gesture_row.addStretch()
        layout.addLayout(gesture_row)

    def _on_toggle(self, checked: bool):
        if checked:
            self._track_toggle.setText("● TRACKING ON")
        else:
            self._track_toggle.setText("○ TRACKING OFF")
        self.tracking_toggled.emit(checked)

    def set_tracking_active(self, active: bool):
        self._track_toggle.blockSignals(True)
        self._track_toggle.setChecked(active)
        if active:
            self._track_toggle.setText("● TRACKING ON")
        else:
            self._track_toggle.setText("○ TRACKING OFF")
        self._track_toggle.blockSignals(False)

    def update_frame(self, frame):
        if not CV2 or not NUMPY:
            return
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(
                self._cam_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._cam_label.setPixmap(scaled)
        except Exception:
            pass

    def update_face_data(self, data: dict):
        x_pct = data.get("face_x_pct", 50)
        y_pct = data.get("face_y_pct", 50)
        fps   = data.get("fps", 0.0)
        zone  = data.get("zone", "CENTER")

        self._pos_label.setText(f"X: {x_pct}%  Y: {y_pct}%")
        self._fps_label.setText(f"{fps:.1f} FPS")
        self._zone_diagram.set_zone(zone)

        gestures = data.get("gestures", {})
        for gesture, active in gestures.items():
            if gesture in self.gesture_indicators:
                self.gesture_indicators[gesture].set_active(active)

    def flash_gesture(self, gesture: str):
        if gesture in self.gesture_indicators:
            self.gesture_indicators[gesture].set_active(True)
            QTimer.singleShot(250, lambda: self._clear_gesture_indicator(gesture))

    def _clear_gesture_indicator(self, gesture: str):
        if gesture in self.gesture_indicators:
            self.gesture_indicators[gesture].set_active(False)

    def show_no_camera(self, msg: str):
        self._cam_label.setPixmap(QPixmap())
        self._cam_label.setText(msg)
        self._cam_label.setStyleSheet(
            f"background: black; color: {DANGER}; font-size: 12px; font-family: {MONO_FONT};"
        )


# ─────────────────────────────────────────────────────────────────────────────
# RightPanel
# ─────────────────────────────────────────────────────────────────────────────
class RightPanel(QWidget):
    mappings_changed = pyqtSignal(object)
    params_changed   = pyqtSignal(float, float, int)

    # Map serial key → PHYSICAL_INPUTS name
    _KEY_TO_NAME = {
        "b1": "Button 1",
        "b2": "Button 2",
        "j1": "J1",
        "j2": "J2",
        "j3": "J3",
        "j4": "J4",
    }
    _NAME_TO_KEY = {v: k for k, v in _KEY_TO_NAME.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phys_indicators = {}
        self.phys_combos     = {}
        self.face_indicators = {}
        self.face_combos     = {}
        self.log = None
        self._deadzone_slider = None
        self._speed_slider    = None
        self._hold_slider     = None
        self._deadzone_lbl    = None
        self._speed_lbl       = None
        self._hold_lbl        = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {BG_WIDGET};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #2a2a3e;
                border-radius: 4px;
                min-height: 20px;
            }}
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        inner = QVBoxLayout(scroll_widget)
        inner.setContentsMargins(10, 10, 10, 10)
        inner.setSpacing(6)

        # Title
        inner.addWidget(make_label("ACTION MAPPER", ACCENT, 13, True))

        # Physical inputs
        inner.addWidget(make_label("PHYSICAL INPUTS", ACCENT2, 10, True))
        for name in PHYSICAL_INPUTS:
            row = QHBoxLayout()
            ind = LEDIndicator(name, ACCENT, width=80)
            self.phys_indicators[name] = ind
            row.addWidget(ind)
            cb = make_combo(ACTIONS)
            self.phys_combos[name] = cb
            cb.currentTextChanged.connect(self._emit_mappings)
            row.addWidget(cb, 1)
            inner.addLayout(row)

        # Separator
        inner.addWidget(self._make_sep())

        # Face tracking inputs
        inner.addWidget(make_label("FACE TRACKING INPUTS", ACCENT2, 10, True))
        for name in FACE_INPUTS:
            row = QHBoxLayout()
            ind = LEDIndicator(name, ACCENT2, width=110)
            self.face_indicators[name] = ind
            row.addWidget(ind)
            cb = make_combo(ACTIONS)
            self.face_combos[name] = cb
            cb.currentTextChanged.connect(self._emit_mappings)
            row.addWidget(cb, 1)
            inner.addLayout(row)

        # Separator
        inner.addWidget(self._make_sep())

        # Settings
        inner.addWidget(make_label("SETTINGS", ACCENT2, 10, True))

        # Deadzone
        inner.addWidget(make_label("Deadzone sensitivity:", FG_DIM, 9))
        dz_row = QHBoxLayout()
        self._deadzone_slider = make_slider(5, 50, 15)
        self._deadzone_lbl    = make_label("15%", FG, 9)
        self._deadzone_slider.valueChanged.connect(self._on_deadzone_changed)
        dz_row.addWidget(self._deadzone_slider, 1)
        dz_row.addWidget(self._deadzone_lbl)
        inner.addLayout(dz_row)

        # Speed
        inner.addWidget(make_label("Cursor speed:", FG_DIM, 9))
        sp_row = QHBoxLayout()
        self._speed_slider = make_slider(1, 30, 8)
        self._speed_lbl    = make_label("8", FG, 9)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        sp_row.addWidget(self._speed_slider, 1)
        sp_row.addWidget(self._speed_lbl)
        inner.addLayout(sp_row)

        # Hold
        inner.addWidget(make_label("Gesture hold time (ms):", FG_DIM, 9))
        hold_row = QHBoxLayout()
        self._hold_slider = make_slider(50, 1000, 300)
        self._hold_lbl    = make_label("300ms", FG, 9)
        self._hold_slider.valueChanged.connect(self._on_hold_changed)
        hold_row.addWidget(self._hold_slider, 1)
        hold_row.addWidget(self._hold_lbl)
        inner.addLayout(hold_row)

        # Separator
        inner.addWidget(self._make_sep())

        # Config
        inner.addWidget(make_label("CONFIG", ACCENT2, 10, True))
        cfg_row = QHBoxLayout()
        save_btn = make_button("Save Config", accent=True)
        save_btn.clicked.connect(self.save_config)
        cfg_row.addWidget(save_btn)
        load_btn = make_button("Load Config")
        load_btn.clicked.connect(self.load_config)
        cfg_row.addWidget(load_btn)
        inner.addLayout(cfg_row)

        # Separator
        inner.addWidget(self._make_sep())

        # Activity log
        inner.addWidget(make_label("ACTIVITY LOG", ACCENT2, 10, True))
        self.log = ActivityLog()
        self.log.setMaximumHeight(160)
        inner.addWidget(self.log)

        inner.addStretch()

        scroll_area.setWidget(scroll_widget)
        outer.addWidget(scroll_area)

    def _make_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a1a2e; margin: 2px 0;")
        return sep

    def _on_deadzone_changed(self, value: int):
        self._deadzone_lbl.setText(f"{value}%")
        self._emit_params()

    def _on_speed_changed(self, value: int):
        self._speed_lbl.setText(str(value))
        self._emit_params()

    def _on_hold_changed(self, value: int):
        self._hold_lbl.setText(f"{value}ms")
        self._emit_params()

    def _emit_mappings(self):
        mappings = {}
        for name, cb in self.phys_combos.items():
            mappings[name] = cb.currentText()
        for name, cb in self.face_combos.items():
            mappings[name] = cb.currentText()
        self.mappings_changed.emit(mappings)

    def _emit_params(self):
        dz      = self._deadzone_slider.value() / 100.0
        speed   = float(self._speed_slider.value())
        hold_ms = self._hold_slider.value()
        self.params_changed.emit(dz, speed, hold_ms)

    def update_physical_indicator(self, key: str, active: bool):
        name = self._KEY_TO_NAME.get(key)
        if name and name in self.phys_indicators:
            self.phys_indicators[name].set_active(active)

    def update_face_indicator(self, gesture: str, active: bool):
        if gesture in self.face_indicators:
            self.face_indicators[gesture].set_active(active)

    def get_face_mappings(self) -> dict:
        return {name: cb.currentText() for name, cb in self.face_combos.items()}

    def get_params(self):
        dz      = self._deadzone_slider.value() / 100.0
        speed   = float(self._speed_slider.value())
        hold_ms = self._hold_slider.value()
        return dz, speed, hold_ms

    def save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Config", "", "JSON Files (*.json)"
        )
        if not path:
            return
        cfg = {
            "physical_mappings": {name: cb.currentText() for name, cb in self.phys_combos.items()},
            "face_mappings":     {name: cb.currentText() for name, cb in self.face_combos.items()},
            "deadzone":          self._deadzone_slider.value() / 100.0,
            "cursor_speed":      float(self._speed_slider.value()),
            "hold_ms":           self._hold_slider.value(),
        }
        try:
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2)
            self.log.log("CONFIG", f"Saved to {os.path.basename(path)}", ACCENT)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", str(e))

    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Config", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path) as f:
                cfg = json.load(f)

            phys = cfg.get("physical_mappings", {})
            for name, action in phys.items():
                if name in self.phys_combos:
                    idx = self.phys_combos[name].findText(action)
                    if idx >= 0:
                        self.phys_combos[name].setCurrentIndex(idx)

            face = cfg.get("face_mappings", {})
            for name, action in face.items():
                if name in self.face_combos:
                    idx = self.face_combos[name].findText(action)
                    if idx >= 0:
                        self.face_combos[name].setCurrentIndex(idx)

            if "deadzone" in cfg:
                self._deadzone_slider.setValue(int(round(cfg["deadzone"] * 100)))
            if "cursor_speed" in cfg:
                self._speed_slider.setValue(int(round(cfg["cursor_speed"])))
            if "hold_ms" in cfg:
                self._hold_slider.setValue(int(cfg["hold_ms"]))

            self.log.log("CONFIG", f"Loaded {os.path.basename(path)}", ACCENT)
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load config:\n{e}")


# ─────────────────────────────────────────────────────────────────────────────
# MainWindow
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1150, 720)

        self._serial_thread      = None
        self._face_adapter       = None
        self._face_tracking_active = True
        self._phys_mappings      = {name: "None" for name in PHYSICAL_INPUTS}
        self._prev_states        = {k: 0 for k in ["b1", "b2", "j1", "j2", "j3", "j4"]}
        self._emitter            = ActionEmitter()

        self._apply_theme()
        self._build_ui()
        self._start_face_tracking()

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {BG_DARK};
                color: {FG};
            }}
            QSplitter::handle {{
                background: #1a1a2e;
            }}
            QToolTip {{
                background: {BG_WIDGET};
                color: {FG};
                border: 1px solid #2a2a3e;
            }}
            QScrollBar:vertical {{
                background: {BG_WIDGET};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #2a2a3e;
                border-radius: 4px;
                min-height: 20px;
            }}
        """)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window,          QColor(BG_DARK))
        palette.setColor(QPalette.ColorRole.WindowText,      QColor(FG))
        palette.setColor(QPalette.ColorRole.Base,            QColor(BG_INPUT))
        palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG_WIDGET))
        palette.setColor(QPalette.ColorRole.Text,            QColor(FG))
        palette.setColor(QPalette.ColorRole.Button,          QColor(BG_WIDGET))
        palette.setColor(QPalette.ColorRole.ButtonText,      QColor(FG))
        palette.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
        self.setPalette(palette)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(8, 8, 8, 8)
        h_layout.setSpacing(6)

        panel_style = f"""
            QFrame {{
                background: {BG_PANEL};
                border: 1px solid #1a1a2e;
                border-radius: 8px;
            }}
        """

        # Left frame
        left_frame = QFrame()
        left_frame.setStyleSheet(panel_style)
        left_frame.setMinimumWidth(255)
        left_frame.setMaximumWidth(330)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_panel = LeftPanel()
        left_layout.addWidget(self.left_panel)
        h_layout.addWidget(left_frame)

        # Middle frame
        mid_frame = QFrame()
        mid_frame.setStyleSheet(panel_style)
        mid_frame.setMinimumWidth(350)
        mid_layout = QVBoxLayout(mid_frame)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        self.mid_panel = MiddlePanel()
        mid_layout.addWidget(self.mid_panel)
        h_layout.addWidget(mid_frame, 2)

        # Right frame
        right_frame = QFrame()
        right_frame.setStyleSheet(panel_style)
        right_frame.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_panel = RightPanel()
        right_layout.addWidget(self.right_panel)
        h_layout.addWidget(right_frame, 1)

        # Connections
        self.left_panel.connect_requested.connect(self._connect_serial)
        self.left_panel.disconnect_requested.connect(self._disconnect_serial)
        self.mid_panel.tracking_toggled.connect(self._toggle_tracking)
        self.right_panel.mappings_changed.connect(self._on_mappings_changed)
        self.right_panel.params_changed.connect(self._on_params_changed)

    def _connect_serial(self, port: str):
        if self._serial_thread is not None:
            self._serial_thread.stop()
            self._serial_thread = None

        baud = int(self.left_panel._baud_combo.currentText())
        self._serial_thread = SerialThread(port, baud)
        self._serial_thread.data_received.connect(self._on_serial_data)
        self._serial_thread.connection_changed.connect(self._on_serial_status)
        self._serial_thread.error_occurred.connect(self._on_serial_error)
        self._serial_thread.start()

    def _disconnect_serial(self):
        if self._serial_thread is not None:
            self._serial_thread.stop()
            self._serial_thread = None
        self.left_panel.set_connected(False, "Disconnected")

    def _on_serial_data(self, data: dict):
        # Update controller visual
        bool_states = {k: bool(v) for k, v in data.items()}
        self.left_panel.update_controller(bool_states)

        # Update right panel physical indicators
        for key in ["b1", "b2", "j1", "j2", "j3", "j4"]:
            active = bool(data.get(key, 0))
            self.right_panel.update_physical_indicator(key, active)

        # Detect 0→1 transitions
        for key in ["b1", "b2", "j1", "j2", "j3", "j4"]:
            prev_val = self._prev_states.get(key, 0)
            curr_val = data.get(key, 0)
            if not prev_val and curr_val:
                # Rising edge
                input_name = self.right_panel._KEY_TO_NAME.get(key, key)
                action     = self._phys_mappings.get(input_name, "None")
                if action and action != "None":
                    if action in META_ACTIONS:
                        self._handle_meta_action(action)
                    else:
                        self._emitter.fire(action)
                    self.right_panel.log.log(input_name, action, ACCENT)

        # Update previous states
        self._prev_states = {k: data.get(k, 0) for k in ["b1", "b2", "j1", "j2", "j3", "j4"]}

    def _handle_meta_action(self, action: str):
        if action == "Toggle Face Tracking":
            new_state = not self._face_tracking_active
            self._toggle_tracking(new_state)
            self.mid_panel.set_tracking_active(new_state)
        elif action == "Speed Up Cursor":
            sl = self.right_panel._speed_slider
            sl.setValue(min(sl.maximum(), sl.value() + 2))
        elif action == "Slow Down Cursor":
            sl = self.right_panel._speed_slider
            sl.setValue(max(sl.minimum(), sl.value() - 2))

    def _on_serial_status(self, connected: bool, message: str):
        self.left_panel.set_connected(connected, message)
        color = ACCENT if connected else DANGER
        self.right_panel.log.log("SERIAL", message, color)

    def _on_serial_error(self, error: str):
        self.left_panel.set_connected(False, f"Error: {error}")
        self.right_panel.log.log("SERIAL", f"Error: {error}", DANGER)

    def _start_face_tracking(self):
        self._face_adapter = FaceTrackingAdapter(parent=self)

        # Apply current params + mappings before starting
        dz, speed, hold_ms = self.right_panel.get_params()
        self._face_adapter.set_params(dz, speed, hold_ms)
        self._face_adapter.mappings = self.right_panel.get_face_mappings()

        self._face_adapter.frame_ready.connect(self.mid_panel.update_frame)
        self._face_adapter.face_data.connect(self._on_face_data)
        self._face_adapter.gesture_fired.connect(self._on_gesture_fired)
        self._face_adapter.error_occurred.connect(self._on_face_error)
        self._face_adapter.start()

    def _on_face_data(self, data: dict):
        self.mid_panel.update_face_data(data)
        gestures = data.get("gestures", {})
        for gesture, active in gestures.items():
            self.right_panel.update_face_indicator(gesture, active)

    def _on_gesture_fired(self, gesture: str, action: str):
        if action == "Toggle Face Tracking":
            new_state = not self._face_tracking_active
            self._toggle_tracking(new_state)
            self.mid_panel.set_tracking_active(new_state)
        elif action == "Speed Up Cursor":
            sl = self.right_panel._speed_slider
            sl.setValue(min(sl.maximum(), sl.value() + 2))
        elif action == "Slow Down Cursor":
            sl = self.right_panel._speed_slider
            sl.setValue(max(sl.minimum(), sl.value() - 2))

        self.mid_panel.flash_gesture(gesture)
        self.right_panel.log.log(gesture, action, ACCENT2)

    def _on_face_error(self, error: str):
        self.mid_panel.show_no_camera(error)
        self.right_panel.log.log("CAMERA", error, DANGER)

    def _toggle_tracking(self, enabled: bool):
        self._face_tracking_active = enabled
        if self._face_adapter is not None:
            self._face_adapter.tracking_enabled = enabled

    def _on_mappings_changed(self, mappings: dict):
        for name in PHYSICAL_INPUTS:
            if name in mappings:
                self._phys_mappings[name] = mappings[name]

        face_mappings = {name: mappings[name] for name in FACE_INPUTS if name in mappings}
        if self._face_adapter is not None:
            self._face_adapter.mappings = face_mappings

    def _on_params_changed(self, deadzone: float, speed: float, hold_ms: int):
        if self._face_adapter is not None:
            self._face_adapter.set_params(deadzone, speed, hold_ms)

    def closeEvent(self, event):
        if self._serial_thread is not None:
            self._serial_thread.stop()
            self._serial_thread = None
        if self._face_adapter is not None:
            self._face_adapter.stop()
            self._face_adapter = None
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont(MONO_FONT, 11)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(BG_DARK))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(FG))
    palette.setColor(QPalette.ColorRole.Base,            QColor(BG_INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG_WIDGET))
    palette.setColor(QPalette.ColorRole.Text,            QColor(FG))
    palette.setColor(QPalette.ColorRole.Button,          QColor(BG_WIDGET))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(FG))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Dark,            QColor("#0a0a0f"))
    palette.setColor(QPalette.ColorRole.Mid,             QColor("#1a1a24"))
    palette.setColor(QPalette.ColorRole.Midlight,        QColor("#222233"))
    palette.setColor(QPalette.ColorRole.Shadow,          QColor("#050508"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
