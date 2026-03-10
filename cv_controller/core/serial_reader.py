from __future__ import annotations
import json

from PyQt6.QtCore import QThread, pyqtSignal

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


def list_serial_ports() -> list[str]:
    if not SERIAL_AVAILABLE:
        return []
    return [p.device for p in serial.tools.list_ports.comports()]


class SerialThread(QThread):
    """
    Reads JSON packets from an Arduino Leonardo at 9600 baud.
    Emits data_received for every packet received.
    Edge detection (0→1 transitions) is handled by the caller.
    """
    data_received      = pyqtSignal(dict)   # raw {"b1":0,"b2":1,...}
    connection_changed = pyqtSignal(bool, str)
    error_occurred     = pyqtSignal(str)

    def __init__(self, port: str, baud: int = 9600, parent=None):
        super().__init__(parent)
        self._port    = port
        self._baud    = baud
        self._running = False

    def run(self):
        if not SERIAL_AVAILABLE:
            self.error_occurred.emit("pyserial not installed — run: pip install pyserial")
            self.connection_changed.emit(False, "pyserial not installed")
            return

        self._running = True
        try:
            ser = serial.Serial(self._port, self._baud, timeout=1)
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.connection_changed.emit(False, str(e))
            return

        self.connection_changed.emit(True, f"Connected on {self._port}")

        try:
            while self._running:
                try:
                    if ser.in_waiting:
                        line = ser.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            try:
                                self.data_received.emit(json.loads(line))
                            except json.JSONDecodeError:
                                pass
                    else:
                        self.msleep(5)
                except serial.SerialException as e:
                    self.error_occurred.emit(str(e))
                    break
        finally:
            try:
                ser.close()
            except Exception:
                pass

        self.connection_changed.emit(False, "Disconnected")

    def stop(self):
        self._running = False
        self.wait(2000)
