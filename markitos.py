#!/usr/bin/env python3
"""Markitos Editor — entry point."""

import sys
import os

# Suppress harmless Chromium/WebEngine internal log noise
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--log-level=3")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.settings import Settings
from src.window import MainWindow
from src.version import __version__, APP_NAME


def main():
    # Hi-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    settings = Settings()
    window = MainWindow(settings)
    window.show()

    # Open file passed as command-line argument
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path) and path.lower().endswith((".md", ".txt")):
            window._load_file(path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
