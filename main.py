import sys
import os
import traceback
import multiprocessing

# Required on macOS to prevent crashes when MediaPipe spawns subprocesses
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)

# Must be set before importing PyQt6 on macOS to avoid camera permission issues
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

# Log file for crash debugging
_LOG = os.path.expanduser("~/Desktop/opencv_error.log")


def _log(msg: str):
    try:
        with open(_LOG, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from cv_controller.ui.app import MainWindow

_ROOT = os.path.dirname(os.path.abspath(__file__))


def _app_icon():
    icon_path = os.path.join(_ROOT, "resources", "icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return QIcon()


def _excepthook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _log("=== CRASH ===\n" + msg)
    try:
        app = QApplication.instance()
        if app:
            dlg = QMessageBox()
            dlg.setWindowTitle("OpenCV Error")
            dlg.setText("OpenCV encountered an error:\n\n" + str(exc_value))
            dlg.setDetailedText(msg)
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.exec()
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook


def main():
    _log("Starting OpenCV...")
    app = QApplication(sys.argv)
    app.setApplicationName("OpenCV")
    app.setOrganizationName("OpenCV")
    app.setQuitOnLastWindowClosed(False)

    icon = _app_icon()
    app.setWindowIcon(icon)

    # Dark palette
    app.setStyle("Fusion")
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Button, QColor(55, 55, 55))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(61, 159, 94))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()

    # One-time Accessibility reminder
    shown_file = os.path.expanduser("~/.opencvcontroller_accessibility_shown")
    if not os.path.exists(shown_file):
        msg = QMessageBox(window)
        msg.setWindowTitle("Accessibility Permission")
        msg.setText(
            "To control other apps (games, browsers, etc.), OpenCV needs Accessibility access.\n\n"
            "System Settings → Privacy & Security → Accessibility → ＋ → add OpenCV\n\n"
            "Without this, face tracking works but keypresses won't reach other apps."
        )
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        open(shown_file, "w").close()

    _log("MainWindow shown, entering event loop.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
