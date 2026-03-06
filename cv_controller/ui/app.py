import json
import os
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QPushButton, QToolBar, QLabel, QComboBox, QMessageBox,
    QInputDialog, QSystemTrayIcon, QMenu, QSizePolicy,
)

from cv_controller.core.tracker import FaceTracker
from cv_controller.core.switches import SwitchDefinition, SwitchEngine
from cv_controller.core.emitter import ActionEmitter
from cv_controller.core.hotkey import HotkeyListener
from cv_controller.ui.camera_widget import CameraWidget
from cv_controller.ui.switch_list import SwitchListWidget
from cv_controller.ui.switch_dialog import SwitchDialog

PROFILES_DIR = Path.home() / "Library" / "Application Support" / "CVController" / "profiles"
_RES         = Path(__file__).parent.parent.parent / "resources"
MODEL_PATH   = _RES / "face_landmarker.task"
GESTURE_PATH = _RES / "gesture_recognizer.task"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenCV")
        self.setMinimumSize(920, 620)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #1a1a1a; }
            QToolBar { background: #222; border-bottom: 1px solid #333; spacing: 4px; padding: 4px 8px; }
            QPushButton {
                background: #2e2e2e; color: #ccc; border: 1px solid #444;
                border-radius: 5px; padding: 5px 12px; font-size: 12px;
            }
            QPushButton:hover  { background: #3a3a3a; color: #fff; }
            QPushButton:pressed { background: #252525; }
            QPushButton#startBtn { background: #1e4d35; border-color: #2d7a50; color: #6dffaa; font-weight: bold; }
            QPushButton#startBtn:hover { background: #255e40; }
            QPushButton#stopBtn  { background: #4d1e1e; border-color: #7a2d2d; color: #ffaaaa; font-weight: bold; }
            QPushButton#stopBtn:hover  { background: #5e2525; }
            QPushButton:checked { background: #1e3d5e; border-color: #2d6a9a; color: #88ccff; }
            QComboBox { background: #2e2e2e; color: #ccc; border: 1px solid #444; border-radius: 4px; padding: 3px 8px; }
            QScrollBar:vertical { background: #1a1a1a; width: 6px; border: none; }
            QScrollBar::handle:vertical { background: #444; border-radius: 3px; min-height: 20px; }
        """)

        self._tracker: FaceTracker | None = None
        self._engine  = SwitchEngine()
        self._emitter = ActionEmitter()
        self._hotkey  = HotkeyListener()
        self._current_profile_path: Path | None = None

        self._setup_ui()
        self._setup_tray()
        self._ensure_profiles_dir()
        self._load_default_profile()
        self._hotkey.triggered.connect(self._toggle_tracking)
        self._hotkey.start()

    def _setup_ui(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self.start_tracking)
        toolbar.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.stop_tracking)
        self.stop_btn.setEnabled(False)
        toolbar.addWidget(self.stop_btn)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("  Profile: "))
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        toolbar.addWidget(self.profile_combo)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_profile)
        toolbar.addWidget(save_btn)

        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new_profile)
        toolbar.addWidget(new_btn)

        toolbar.addSeparator()

        add_btn = QPushButton("＋ Add Switch")
        add_btn.clicked.connect(self._add_switch)
        toolbar.addWidget(add_btn)

        self.flip_btn = QPushButton("⇄ Flip")
        self.flip_btn.setCheckable(True)
        self.flip_btn.setChecked(True)
        self.flip_btn.setToolTip("Flip camera horizontally")
        self.flip_btn.toggled.connect(self._on_flip_toggled)
        toolbar.addWidget(self.flip_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        hotkey_label = QLabel("  ⌘⇧O  ")
        hotkey_label.setStyleSheet("color: #555; font-size: 11px;")
        hotkey_label.setToolTip("Global hotkey: Cmd+Shift+O toggles tracking from any app")
        toolbar.addWidget(hotkey_label)

        about_btn = QPushButton("ℹ")
        about_btn.setFixedWidth(32)
        about_btn.clicked.connect(self._show_about)
        toolbar.addWidget(about_btn)

        self.status_label = QLabel("● Stopped")
        self.status_label.setStyleSheet("color: #555; font-size: 11px; padding: 0 8px;")
        toolbar.addWidget(self.status_label)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        self.camera_widget = CameraWidget()
        splitter.addWidget(self.camera_widget)

        self.switch_list = SwitchListWidget()
        self.switch_list.edit_requested.connect(self._edit_switch)
        self.switch_list.delete_requested.connect(self._delete_switch)
        splitter.addWidget(self.switch_list)

        splitter.setSizes([640, 280])
        splitter.setHandleWidth(1)

    def _setup_tray(self):
        icon = self.windowIcon()
        self.tray = QSystemTrayIcon(icon, self)

        menu = QMenu()
        self._tray_toggle = QAction("▶ Start Tracking", self)
        self._tray_toggle.triggered.connect(self._toggle_tracking)
        menu.addAction(self._tray_toggle)

        show_act = QAction("Show Window", self)
        show_act.triggered.connect(lambda: (self.show(), self.raise_(), self.activateWindow()))
        menu.addAction(show_act)
        menu.addSeparator()

        quit_act = QAction("Quit OpenCV", self)
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.setToolTip("OpenCV — Stopped")
        self.tray.show()

    # ── Tracking ─────────────────────────────────────────────────────────────

    def _toggle_tracking(self):
        if self._tracker and self._tracker.isRunning():
            self.stop_tracking()
        else:
            self.start_tracking()

    def start_tracking(self):
        if self._tracker and self._tracker.isRunning():
            return
        if not MODEL_PATH.exists():
            QMessageBox.critical(self, "Model Missing",
                f"Face model not found:\n{MODEL_PATH}\n\nRun setup.sh first.")
            return

        gesture_path = str(GESTURE_PATH) if GESTURE_PATH.exists() else None
        self._tracker = FaceTracker(
            model_path=str(MODEL_PATH),
            gesture_model_path=gesture_path,
        )
        self._tracker.frame_ready.connect(self.camera_widget.update_frame)
        self._tracker.face_data.connect(self.camera_widget.update_face_data)
        self._tracker.face_data.connect(self._on_face_data)
        self._tracker.tracking_error.connect(self._on_tracking_error)
        self._tracker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_status("● Tracking", "#3dff7a")
        self._tray_toggle.setText("■ Stop Tracking")
        self.tray.setToolTip("OpenCV — Tracking active")

    def stop_tracking(self):
        if self._tracker:
            self._emitter.release_all()
            self._tracker.stop()
            self._tracker = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_status("● Stopped", "#555")
        self._tray_toggle.setText("▶ Start Tracking")
        self.tray.setToolTip("OpenCV — Stopped")

    def _set_status(self, text: str, color: str):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px; padding: 0 8px;")

    @pyqtSlot(dict)
    def _on_face_data(self, data: dict):
        if not data.get("face_detected"):
            return
        events = self._engine.evaluate(data)
        self.switch_list.update_values({e.switch.id: e.current_value for e in events})
        for event in events:
            sw = event.switch
            if event.triggered:
                self.switch_list.flash(sw.id)
                if sw.action_type in ("tap", "mouse_left", "mouse_right", "scroll_up", "scroll_down"):
                    self._emitter.execute(sw.action_type, sw.action_key, sw.id, True)
            if sw.action_type == "hold":
                self._emitter.execute("hold", sw.action_key, sw.id, event.active)

    def _on_flip_toggled(self, checked: bool):
        if self._tracker:
            self._tracker.flip_horizontal = checked

    @pyqtSlot(str)
    def _on_tracking_error(self, msg: str):
        self.stop_tracking()
        QMessageBox.warning(self, "Tracking Error", msg)

    # ── Switch management ─────────────────────────────────────────────────────

    def _add_switch(self):
        dlg = SwitchDialog(self)
        if dlg.exec():
            sw = dlg.get_switch()
            self._engine.switches.append(sw)
            self.switch_list.add_switch(sw)

    def _edit_switch(self, switch_id: str):
        sw = next((s for s in self._engine.switches if s.id == switch_id), None)
        if not sw:
            return
        dlg = SwitchDialog(self, sw)
        if dlg.exec():
            dlg.get_switch(existing=sw)
            self.switch_list.refresh_switch(sw)

    def _delete_switch(self, switch_id: str):
        self._engine.switches = [s for s in self._engine.switches if s.id != switch_id]
        self.switch_list.remove_switch(switch_id)

    # ── Profiles ─────────────────────────────────────────────────────────────

    def _ensure_profiles_dir(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        default_src = Path(__file__).parent.parent.parent / "profiles" / "default.json"
        default_dst = PROFILES_DIR / "default.json"
        if not default_dst.exists() and default_src.exists():
            shutil.copy(default_src, default_dst)
        self._refresh_profile_list()

    def _refresh_profile_list(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for f in sorted(PROFILES_DIR.glob("*.json")):
            self.profile_combo.addItem(f.stem, str(f))
        self.profile_combo.blockSignals(False)

    def _load_default_profile(self):
        default = PROFILES_DIR / "default.json"
        if default.exists():
            self._load_profile(default)

    def _load_profile(self, path: Path):
        try:
            with open(path) as f:
                data = json.load(f)
            self._current_profile_path = path
            self._engine.switches = [SwitchDefinition.from_dict(s) for s in data.get("switches", [])]
            self.switch_list.clear()
            for sw in self._engine.switches:
                self.switch_list.add_switch(sw)
            for i in range(self.profile_combo.count()):
                if self.profile_combo.itemData(i) == str(path):
                    self.profile_combo.blockSignals(True)
                    self.profile_combo.setCurrentIndex(i)
                    self.profile_combo.blockSignals(False)
                    break
        except Exception as e:
            QMessageBox.warning(self, "Load Error", str(e))

    def _save_profile(self):
        path = self._current_profile_path
        if not path:
            name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
            if not ok or not name.strip():
                return
            path = PROFILES_DIR / f"{name.strip()}.json"
            self._current_profile_path = path
        with open(path, "w") as f:
            json.dump({"name": path.stem, "version": 1,
                       "switches": [s.to_dict() for s in self._engine.switches]}, f, indent=2)
        self._refresh_profile_list()

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok or not name.strip():
            return
        self._current_profile_path = PROFILES_DIR / f"{name.strip()}.json"
        self._engine.switches = []
        self.switch_list.clear()
        self._save_profile()
        self._refresh_profile_list()

    def _on_profile_selected(self, index: int):
        path_str = self.profile_combo.itemData(index)
        if path_str:
            self._load_profile(Path(path_str))

    # ── About / tray ─────────────────────────────────────────────────────────

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    def _show_about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("About OpenCV")
        msg.setIconPixmap(self.windowIcon().pixmap(64, 64))
        msg.setText(
            "<h2 style='color:#3dff7a;'>OpenCV</h2>"
            "<p><b>Adaptive Vision Controller</b></p>"
            "<p>Made by <b>Jacob Majors</b><br>"
            "For <b>Ramsey Mussalum's</b> Design for Social Good class<br>"
            "at <b>Sonoma Academy</b> — March 2026</p>"
            "<hr>"
            "<p style='color:#888; font-size:11px;'>"
            "Global hotkey: <b>⌘ Shift O</b> — toggle tracking from any app<br>"
            "Supported: face, head pose, hand gestures, hand position<br>"
            "Powered by MediaPipe · PyQt6 · pynput</p>"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "OpenCV running in menu bar",
            "Use ⌘⇧O to toggle tracking, or click the menu bar icon.",
            QSystemTrayIcon.MessageIcon.Information, 2000,
        )

    def _quit(self):
        self._hotkey.stop()
        self.stop_tracking()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
