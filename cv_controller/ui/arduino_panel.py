"""
ArduinoPanel — physical controller UI panel.
Shows a painted XAC-style controller that lights up on button press,
plus per-input action mappings that save/load with profiles.
"""
from __future__ import annotations
import math

from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient, QFont,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QDialog, QPlainTextEdit,
    QDialogButtonBox,
)

try:
    import serial.tools.list_ports
    _SERIAL = True
except ImportError:
    _SERIAL = False

# ── Physical input definitions ────────────────────────────────────────────────
_INPUTS = [
    ("b1", "Button 1"),
    ("b2", "Button 2"),
    ("j1", "J1"),
    ("j2", "J2"),
    ("j3", "J3"),
    ("j4", "J4"),
]

_ACTION_TYPES = ["tap", "hold", "mouse_left", "mouse_right", "scroll_up", "scroll_down"]

_DEFAULTS: dict[str, dict] = {
    "b1": {"action_type": "tap",        "action_key": "space"},
    "b2": {"action_type": "mouse_left", "action_key": ""},
    "j1": {"action_type": "tap",        "action_key": "left"},
    "j2": {"action_type": "tap",        "action_key": "right"},
    "j3": {"action_type": "tap",        "action_key": "up"},
    "j4": {"action_type": "tap",        "action_key": "down"},
}

_ARDUINO_SKETCH = """\
// Adaptive Controller — Arduino Leonardo Sketch
// Reads 6 inputs on pins 2-7, sends JSON at 9600 baud every 20ms

void setup() {
  Serial.begin(9600);
  for (int pin = 2; pin <= 7; pin++) {
    pinMode(pin, INPUT_PULLUP);
  }
}

void loop() {
  // LOW = pressed (INPUT_PULLUP inverts the logic)
  int b1 = !digitalRead(2);   // Pin 2 = Button 1
  int b2 = !digitalRead(3);   // Pin 3 = Button 2
  int j1 = !digitalRead(4);   // Pin 4 = 3.5mm Jack 1
  int j2 = !digitalRead(5);   // Pin 5 = 3.5mm Jack 2
  int j3 = !digitalRead(6);   // Pin 6 = 3.5mm Jack 3
  int j4 = !digitalRead(7);   // Pin 7 = 3.5mm Jack 4

  Serial.print("{");
  Serial.print("\\"b1\\":"); Serial.print(b1); Serial.print(",");
  Serial.print("\\"b2\\":"); Serial.print(b2); Serial.print(",");
  Serial.print("\\"j1\\":"); Serial.print(j1); Serial.print(",");
  Serial.print("\\"j2\\":"); Serial.print(j2); Serial.print(",");
  Serial.print("\\"j3\\":"); Serial.print(j3); Serial.print(",");
  Serial.print("\\"j4\\":"); Serial.print(j4);
  Serial.println("}");

  delay(20);  // 50 Hz
}
"""


# ── Controller visualizer ─────────────────────────────────────────────────────

class _ControllerViz(QWidget):
    """Painted XAC-style controller showing live button / jack states."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.states: dict[str, bool] = {k: False for k, _ in _INPUTS}
        self.setMinimumHeight(120)
        self.setMaximumHeight(150)

    def set_states(self, states: dict):
        self.states.update({k: bool(v) for k, v in states.items()})
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        m = 10
        bw = w - 2 * m
        bh = h - 2 * m - 16   # leave room for jack labels
        radius = bh * 0.32

        # Body
        p.setBrush(QBrush(QColor("#1e1e2e")))
        p.setPen(QPen(QColor("#333344"), 2))
        p.drawRoundedRect(QRectF(m, m, bw, bh), radius, radius)

        # Subtle texture lines
        p.setPen(QPen(QColor("#25253a"), 1))
        for i in range(1, 3):
            y = m + bh * i / 3
            p.drawLine(int(m + 16), int(y), int(m + bw - 16), int(y))

        br = min(bw, bh) * 0.16   # button radius

        # Button 1 — green when active
        b1x = m + bw * 0.27
        b1y = m + bh * 0.50
        self._draw_button(p, b1x, b1y, br, "1",
                          self.states.get("b1", False), QColor("#00ff88"))

        # Button 2 — orange when active
        b2x = m + bw * 0.73
        b2y = m + bh * 0.50
        self._draw_button(p, b2x, b2y, br, "2",
                          self.states.get("b2", False), QColor("#ff8c00"))

        # Centre logo
        cx, cy = m + bw * 0.50, m + bh * 0.50
        p.setBrush(QBrush(QColor("#252535")))
        p.setPen(QPen(QColor("#333344"), 1))
        p.drawEllipse(QPointF(cx, cy), 15, 10)
        p.setPen(QPen(QColor("#555566")))
        p.setFont(QFont("Menlo", 7, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 15, cy - 10, 30, 20),
                   Qt.AlignmentFlag.AlignCenter, "AC")

        # Jack circles (J1–J4) near bottom of body
        jy = m + bh - 16
        for i, key in enumerate(["j1", "j2", "j3", "j4"]):
            jx = m + bw * (0.20 + 0.20 * i)
            active = self.states.get(key, False)
            if active:
                glow = QRadialGradient(jx, jy, 16)
                glow.setColorAt(0, QColor(0, 170, 255, 130))
                glow.setColorAt(1, QColor(0, 170, 255, 0))
                p.setBrush(QBrush(glow))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(jx, jy), 16, 16)
                p.setBrush(QBrush(QColor("#00aaff")))
                p.setPen(QPen(QColor("#00aaff"), 1))
            else:
                p.setBrush(QBrush(QColor("#222233")))
                p.setPen(QPen(QColor("#333344"), 1))
            p.drawEllipse(QPointF(jx, jy), 7, 7)

        # Jack labels below body
        p.setPen(QPen(QColor("#444455")))
        p.setFont(QFont("Menlo", 7))
        for i, lbl in enumerate(["J1", "J2", "J3", "J4"]):
            jx = m + bw * (0.20 + 0.20 * i)
            p.drawText(QRectF(jx - 10, m + bh + 2, 20, 12),
                       Qt.AlignmentFlag.AlignCenter, lbl)

        p.end()

    def _draw_button(self, p, cx, cy, r, label, active, on_color):
        if active:
            glow = QRadialGradient(cx, cy, r * 2.4)
            glow.setColorAt(0, QColor(on_color.red(), on_color.green(),
                                      on_color.blue(), 130))
            glow.setColorAt(1, QColor(on_color.red(), on_color.green(),
                                      on_color.blue(), 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r * 2.4, r * 2.4)
            p.setBrush(QBrush(on_color))
            p.setPen(QPen(on_color, 2))
        else:
            p.setBrush(QBrush(QColor("#2a2a3e")))
            p.setPen(QPen(QColor("#444455"), 2))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(QColor("#000" if active else "#777788")))
        p.setFont(QFont("Menlo", max(9, int(r * 0.85)), QFont.Weight.Bold))
        p.drawText(QRectF(cx - r, cy - r, r * 2, r * 2),
                   Qt.AlignmentFlag.AlignCenter, label)


# ── Status dot (pulsing green / static red) ───────────────────────────────────

class _StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(12, 12)

    def set_connected(self, connected: bool):
        self._connected = connected
        if connected:
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _tick(self):
        self._phase = (self._phase + 0.15) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._connected:
            alpha = int(180 + 75 * math.sin(self._phase))
            color = QColor(0, 255, 136, alpha)
        else:
            color = QColor(180, 60, 60)
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(6, 6), 5, 5)
        p.end()


# ── LED flash dot (per input row) ─────────────────────────────────────────────

class _LEDDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lit = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._off)
        self.setFixedSize(12, 12)

    def flash(self):
        self._lit = True
        self.update()
        self._timer.start(300)

    def _off(self):
        self._lit = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#00ff88") if self._lit else QColor("#2a2a3e")
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(6, 6), 5, 5)
        p.end()


# ── Main panel widget ─────────────────────────────────────────────────────────

_BTN_STYLE = (
    "QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {border};"
    " border-radius: 4px; font-size: 11px; {extra} }}"
    "QPushButton:hover {{ background: {hover}; }}"
)

_COMBO_STYLE = (
    "QComboBox { background: #252525; color: #ccc; border: 1px solid #3a3a3a;"
    " border-radius: 3px; padding: 2px 4px; font-size: 10px; }"
    "QComboBox QAbstractItemView { background: #252525; color: #ccc;"
    " selection-background-color: #3a3a3a; }"
)

_EDIT_ON = (
    "QLineEdit { background: #252525; color: #ccc; border: 1px solid #3a3a3a;"
    " border-radius: 3px; padding: 2px 4px; font-size: 10px; }"
    "QLineEdit:focus { border-color: #555; }"
)
_EDIT_OFF = (
    "QLineEdit { background: #1e1e1e; color: #444; border: 1px solid #2a2a2a;"
    " border-radius: 3px; padding: 2px 4px; font-size: 10px; }"
)


class ArduinoPanel(QWidget):
    connect_requested    = pyqtSignal(str, int)  # port, baud
    disconnect_requested = pyqtSignal()
    mappings_changed     = pyqtSignal()          # user edited a mapping

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._leds:          dict[str, _LEDDot]  = {}
        self._action_combos: dict[str, QComboBox] = {}
        self._key_edits:     dict[str, QLineEdit] = {}
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header
        hdr = QLabel("Arduino Controller")
        hdr.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #bbb;"
            " padding-bottom: 2px; letter-spacing: 1px;"
        )
        layout.addWidget(hdr)

        # Port row
        port_row = QHBoxLayout()
        port_row.setSpacing(4)

        self._port_combo = QComboBox()
        self._port_combo.setStyleSheet(
            "QComboBox { background: #2e2e2e; color: #ccc; border: 1px solid #444;"
            " border-radius: 4px; padding: 2px 6px; font-size: 11px; }"
            "QComboBox QAbstractItemView { background: #2e2e2e; color: #ccc;"
            " selection-background-color: #444; }"
        )
        self._refresh_ports()
        port_row.addWidget(self._port_combo, 1)

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(26, 24)
        refresh_btn.setStyleSheet(
            "QPushButton { background: #2e2e2e; color: #aaa; border: 1px solid #444;"
            " border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background: #3a3a3a; }"
        )
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(refresh_btn)

        self._status_dot = _StatusDot()
        port_row.addWidget(self._status_dot)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedWidth(82)
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._apply_connect_btn_style(False)
        port_row.addWidget(self._connect_btn)
        layout.addLayout(port_row)

        # Status label
        self._status_lbl = QLabel("Not connected")
        self._status_lbl.setStyleSheet("color: #555; font-size: 10px;")
        layout.addWidget(self._status_lbl)

        # Controller visualizer
        self._viz = _ControllerViz()
        layout.addWidget(self._viz)

        # Separator
        layout.addWidget(self._make_sep())

        # Mappings header
        map_lbl = QLabel("Button Mappings")
        map_lbl.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #888; padding: 2px 0;"
        )
        layout.addWidget(map_lbl)

        # One row per physical input
        for key, display_name in _INPUTS:
            row = QHBoxLayout()
            row.setSpacing(4)

            led = _LEDDot()
            self._leds[key] = led
            row.addWidget(led)

            lbl = QLabel(display_name)
            lbl.setFixedWidth(56)
            lbl.setStyleSheet("color: #aaa; font-size: 11px;")
            row.addWidget(lbl)

            action_cb = QComboBox()
            action_cb.addItems(_ACTION_TYPES)
            action_cb.setFixedWidth(94)
            action_cb.setStyleSheet(_COMBO_STYLE)
            default = _DEFAULTS.get(key, {})
            idx = action_cb.findText(default.get("action_type", "tap"))
            if idx >= 0:
                action_cb.setCurrentIndex(idx)
            action_cb.currentTextChanged.connect(
                lambda _, k=key: self._on_action_type_changed(k)
            )
            self._action_combos[key] = action_cb
            row.addWidget(action_cb)

            key_edit = QLineEdit(default.get("action_key", ""))
            key_edit.setPlaceholderText("key…")
            key_edit.setFixedWidth(66)
            needs_key = default.get("action_type", "tap") in ("tap", "hold")
            key_edit.setStyleSheet(_EDIT_ON if needs_key else _EDIT_OFF)
            key_edit.setEnabled(needs_key)
            key_edit.textChanged.connect(lambda _: self.mappings_changed.emit())
            self._key_edits[key] = key_edit
            row.addWidget(key_edit)

            layout.addLayout(row)

        # Sketch button
        layout.addWidget(self._make_sep())
        sketch_btn = QPushButton("Show Arduino Sketch")
        sketch_btn.setStyleSheet(
            "QPushButton { background: #222; color: #666; border: 1px solid #333;"
            " border-radius: 4px; font-size: 10px; padding: 4px; }"
            "QPushButton:hover { color: #999; border-color: #444; }"
        )
        sketch_btn.clicked.connect(self._show_sketch)
        layout.addWidget(sketch_btn)
        layout.addStretch()

    # ── Port management ───────────────────────────────────────────────────────

    def _refresh_ports(self):
        prev = self._port_combo.currentText() if hasattr(self, "_port_combo") else ""
        self._port_combo.clear()
        if _SERIAL:
            import serial.tools.list_ports as lp
            ports = [p.device for p in lp.comports()]
        else:
            ports = []
        if ports:
            self._port_combo.addItems(ports)
            idx = self._port_combo.findText(prev)
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)
        else:
            self._port_combo.addItem("(no ports found)")

    # ── Connect / disconnect ──────────────────────────────────────────────────

    def _toggle_connect(self):
        if self._connected:
            self.disconnect_requested.emit()
        else:
            port = self._port_combo.currentText()
            if port and "(no ports" not in port:
                self.connect_requested.emit(port, 9600)

    def set_connected(self, connected: bool, message: str = ""):
        self._connected = connected
        self._status_dot.set_connected(connected)
        self._status_lbl.setText(message or ("Connected" if connected else "Not connected"))
        self._status_lbl.setStyleSheet(
            f"color: {'#3dff7a' if connected else '#555'}; font-size: 10px;"
        )
        self._connect_btn.setText("Disconnect" if connected else "Connect")
        self._apply_connect_btn_style(connected)

    def _apply_connect_btn_style(self, connected: bool):
        if connected:
            self._connect_btn.setStyleSheet(
                "QPushButton { background: #4d1e1e; color: #ffaaaa;"
                " border: 1px solid #7a2d2d; border-radius: 4px;"
                " font-size: 11px; font-weight: bold; padding: 3px 6px; }"
                "QPushButton:hover { background: #5e2525; }"
            )
        else:
            self._connect_btn.setStyleSheet(
                "QPushButton { background: #1e4d35; color: #6dffaa;"
                " border: 1px solid #2d7a50; border-radius: 4px;"
                " font-size: 11px; font-weight: bold; padding: 3px 6px; }"
                "QPushButton:hover { background: #255e40; }"
            )

    # ── State updates ─────────────────────────────────────────────────────────

    def flash_input(self, key: str):
        """Flash the LED for a single physical input on press."""
        if key in self._leds:
            self._leds[key].flash()

    def update_states(self, states: dict):
        """Update the controller visualizer (called every serial packet)."""
        self._viz.set_states(states)

    # ── Mappings ──────────────────────────────────────────────────────────────

    def _on_action_type_changed(self, key: str):
        action_type = self._action_combos[key].currentText()
        needs_key = action_type in ("tap", "hold")
        edit = self._key_edits[key]
        edit.setEnabled(needs_key)
        edit.setStyleSheet(_EDIT_ON if needs_key else _EDIT_OFF)
        self.mappings_changed.emit()

    def get_mappings(self) -> dict:
        return {
            key: {
                "action_type": self._action_combos[key].currentText(),
                "action_key":  self._key_edits[key].text().strip(),
            }
            for key, _ in _INPUTS
        }

    def set_mappings(self, mappings: dict):
        for key, _ in _INPUTS:
            if key not in mappings:
                continue
            m = mappings[key]
            action_type = m.get("action_type", "tap")
            idx = self._action_combos[key].findText(action_type)
            if idx >= 0:
                self._action_combos[key].setCurrentIndex(idx)
            self._key_edits[key].setText(m.get("action_key", ""))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_sep() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a2a; margin: 2px 0;")
        return sep

    def _show_sketch(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Arduino Sketch — copy to Arduino IDE")
        dlg.setMinimumSize(500, 440)
        dlg.setStyleSheet("background: #1a1a1a; color: #ccc;")
        lay = QVBoxLayout(dlg)
        txt = QPlainTextEdit(_ARDUINO_SKETCH)
        txt.setReadOnly(True)
        txt.setStyleSheet(
            "QPlainTextEdit { background: #111; color: #aaa; border: 1px solid #333;"
            " border-radius: 4px; font-family: Menlo, Courier; font-size: 11px; }"
        )
        lay.addWidget(txt)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        btns.setStyleSheet(
            "QPushButton { background: #2e2e2e; color: #ccc; border: 1px solid #444;"
            " border-radius: 4px; padding: 5px 14px; }"
            "QPushButton:hover { background: #3a3a3a; }"
        )
        lay.addWidget(btns)
        dlg.exec()
