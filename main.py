import sys
import os
import multiprocessing

# Required on macOS to prevent crashes when MediaPipe spawns subprocesses
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)

# Must be set before importing PyQt6 on macOS to avoid camera permission issues
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from cv_controller.ui.app import MainWindow

_ROOT = os.path.dirname(os.path.abspath(__file__))


def _app_icon():
    icon_path = os.path.join(_ROOT, "resources", "icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return QIcon()


def main():
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
            "To send keypresses to other apps, Open CV needs Accessibility access.\n\n"
            "System Settings → Privacy & Security → Accessibility → add Terminal.\n\n"
            "You can skip this for now — tracking still works, keypresses just won't "
            "reach other apps until permission is granted."
        )
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        open(shown_file, "w").close()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
