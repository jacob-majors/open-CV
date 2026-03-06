from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QSlider, QSpinBox,
    QDialogButtonBox, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QWidget,
)
from cv_controller.core.switches import (
    SwitchDefinition, MOVEMENT_LABELS, ACTION_LABELS, MOVEMENTS, ACTIONS,
)


class KeyCaptureEdit(QLineEdit):
    """QLineEdit that captures the next keypress as a key string."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._capturing = False

    def start_capture(self):
        self._capturing = True
        self.setPlaceholderText("Press a key…")
        self.clear()
        self.setFocus()

    def keyPressEvent(self, event):
        if not self._capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        parts = []
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("cmd")
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")

        key_map = {
            Qt.Key.Key_Space: "space", Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter", Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Escape: "escape", Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete", Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right", Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end", Qt.Key.Key_PageUp: "page_up",
            Qt.Key.Key_PageDown: "page_down",
            Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4", Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8", Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
        }

        if key in key_map:
            parts.append(key_map[key])
        elif key not in (
            Qt.Key.Key_Meta, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift
        ):
            char = event.text()
            if char:
                parts.append(char.lower())

        if parts:
            self.setText("+".join(parts))
            self._capturing = False


class SwitchDialog(QDialog):
    def __init__(self, parent=None, switch: SwitchDefinition = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Switch" if switch else "Add Switch")
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog { background: #252525; }
            QLabel { color: #ccc; }
            QLineEdit, QComboBox, QSpinBox {
                background: #333; color: #eee; border: 1px solid #555;
                border-radius: 4px; padding: 4px 6px;
            }
            QSlider::groove:horizontal { background: #444; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #3d9f5e; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px;
            }
            QSlider::sub-page:horizontal { background: #3d9f5e; border-radius: 2px; }
            QPushButton {
                background: #3a3a3a; color: #ccc; border: 1px solid #555;
                border-radius: 4px; padding: 4px 12px;
            }
            QPushButton:hover { background: #444; }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        # Name
        self.name_edit = QLineEdit(switch.name if switch else "")
        self.name_edit.setPlaceholderText("e.g. Blink Left → Space")
        form.addRow("Name:", self.name_edit)

        # Movement
        self.movement_combo = QComboBox()
        for mv in MOVEMENTS:
            self.movement_combo.addItem(MOVEMENT_LABELS.get(mv, mv), mv)
        if switch:
            idx = MOVEMENTS.index(switch.movement) if switch.movement in MOVEMENTS else 0
            self.movement_combo.setCurrentIndex(idx)
        form.addRow("Movement:", self.movement_combo)

        # Threshold
        threshold_row = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(1, 99)
        self.threshold_slider.setValue(int((switch.threshold if switch else 0.6) * 100))
        self.threshold_value_label = QLabel(f"{self.threshold_slider.value()}%")
        self.threshold_value_label.setFixedWidth(36)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_value_label.setText(f"{v}%")
        )
        threshold_row.addWidget(self.threshold_slider)
        threshold_row.addWidget(self.threshold_value_label)
        threshold_widget = QWidget()
        threshold_widget.setLayout(threshold_row)
        form.addRow("Threshold:", threshold_widget)

        # Action type
        self.action_combo = QComboBox()
        for act in ACTIONS:
            self.action_combo.addItem(ACTION_LABELS.get(act, act), act)
        if switch:
            idx = ACTIONS.index(switch.action_type) if switch.action_type in ACTIONS else 0
            self.action_combo.setCurrentIndex(idx)
        self.action_combo.currentIndexChanged.connect(self._on_action_changed)
        form.addRow("Action:", self.action_combo)

        # Key
        key_row = QHBoxLayout()
        self.key_edit = KeyCaptureEdit()
        self.key_edit.setText(switch.action_key if switch else "space")
        self.key_edit.setPlaceholderText("e.g. space, cmd+c, left")
        self.capture_btn = QPushButton("Capture")
        self.capture_btn.setFixedWidth(70)
        self.capture_btn.clicked.connect(self.key_edit.start_capture)
        key_row.addWidget(self.key_edit)
        key_row.addWidget(self.capture_btn)
        key_widget = QWidget()
        key_widget.setLayout(key_row)
        self.key_row_label = QLabel("Key:")
        form.addRow(self.key_row_label, key_widget)

        # Cooldown
        self.cooldown_spin = QSpinBox()
        self.cooldown_spin.setRange(50, 5000)
        self.cooldown_spin.setSingleStep(50)
        self.cooldown_spin.setSuffix(" ms")
        self.cooldown_spin.setValue(switch.cooldown_ms if switch else 500)
        form.addRow("Cooldown:", self.cooldown_spin)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("QPushButton { min-width: 70px; }")
        layout.addWidget(buttons)

        self._on_action_changed()

    def _on_action_changed(self):
        action = self.action_combo.currentData()
        key_needed = action in ("tap", "hold")
        self.key_row_label.setVisible(key_needed)
        self.key_edit.setVisible(key_needed)
        self.capture_btn.setVisible(key_needed)

    def get_switch(self, existing: SwitchDefinition = None) -> SwitchDefinition:
        name = self.name_edit.text().strip() or "Unnamed Switch"
        movement = self.movement_combo.currentData()
        threshold = self.threshold_slider.value() / 100.0
        action_type = self.action_combo.currentData()
        action_key = self.key_edit.text().strip() or "space"
        cooldown_ms = self.cooldown_spin.value()

        if existing:
            existing.name = name
            existing.movement = movement
            existing.threshold = threshold
            existing.action_type = action_type
            existing.action_key = action_key
            existing.cooldown_ms = cooldown_ms
            return existing

        return SwitchDefinition(
            name=name,
            movement=movement,
            threshold=threshold,
            action_type=action_type,
            action_key=action_key,
            cooldown_ms=cooldown_ms,
        )
