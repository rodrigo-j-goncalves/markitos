#!/usr/bin/env python3
"""Markitos Editor — entry point."""

import sys
import os
import subprocess


def _apply_rhi_fallback_if_needed():
    """Probe OpenGL before QApplication starts; if broken, switch to Vulkan + software GPU.

    Runs a subprocess so probe errors never reach the terminal and the result
    is available before any Qt state is initialised in the main process.
    No-ops when the env vars are already set (e.g. by a machine-specific .sh).
    """
    probe = (
        "from PyQt6.QtGui import QOpenGLContext, QOffscreenSurface;"
        "from PyQt6.QtWidgets import QApplication;"
        "import sys;"
        "app = QApplication(sys.argv);"
        "surf = QOffscreenSurface();"
        "surf.create();"
        "ctx = QOpenGLContext();"
        "print('ok' if ctx.create() else 'fail')"
    )
    try:
        r = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, timeout=5, text=True,
        )
        if "ok" not in r.stdout:
            os.environ.setdefault("QSG_RHI_BACKEND", "vulkan")
            os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
            existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "--log-level=3")
            if "--disable-gpu" not in existing:
                os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu " + existing
    except Exception:
        pass  # probe timed out or crashed; proceed with defaults


_apply_rhi_fallback_if_needed()

# Suppress harmless Chromium/WebEngine internal log noise
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--log-level=3")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

from src.settings import Settings
from src.window import MainWindow
from src.version import __version__, APP_NAME


def _load_svg_icon(path: str) -> QIcon:
    renderer = QSvgRenderer(path)
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def main():
    # Hi-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    _icon_path = os.path.join(os.path.dirname(__file__), "icon", "markdown-mark-solid_RG.svg")
    if os.path.isfile(_icon_path):
        app.setWindowIcon(_load_svg_icon(_icon_path))

    settings = Settings()
    window = MainWindow(settings)
    window.show()

    # Open file passed as command-line argument
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path) and path.lower().endswith((".md", ".txt")):
            window._load_file(path)

    # Optional window position override (passed by parent instance on link-open)
    x, y = None, None
    for arg in sys.argv[2:]:
        if arg.startswith("--x="):
            try: x = int(arg[4:])
            except ValueError: pass
        elif arg.startswith("--y="):
            try: y = int(arg[4:])
            except ValueError: pass
    if x is not None or y is not None:
        window.move(x if x is not None else window.x(),
                    y if y is not None else window.y())

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
