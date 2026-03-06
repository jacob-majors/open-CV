"""Global hotkey listener — runs in a background thread via pynput."""
import threading
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyListener(QObject):
    """Listens for a global hotkey and emits a signal when triggered."""
    triggered = pyqtSignal()

    # Default: Cmd+Shift+O
    DEFAULT_HOTKEY = "<cmd>+<shift>+o"

    def __init__(self, hotkey: str = None, parent=None):
        super().__init__(parent)
        self._hotkey_str = hotkey or self.DEFAULT_HOTKEY
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self):
        try:
            self._listener = keyboard.GlobalHotKeys({
                self._hotkey_str: self._on_triggered,
            })
            self._listener.start()
        except Exception:
            pass  # Accessibility permission not granted — fail silently

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def set_hotkey(self, hotkey: str):
        self.stop()
        self._hotkey_str = hotkey
        self.start()

    def _on_triggered(self):
        self.triggered.emit()
