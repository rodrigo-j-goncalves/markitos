import os
import re
from datetime import datetime

from PyQt6.QtCore import Qt, QUrl, QEvent, QRect, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QImage,
    QKeySequence,
    QFont,
    QFontMetrics,
    QColor,
    QPalette,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextOption,
    QShortcut,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QStackedWidget,
    QPlainTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QMessageBox,
    QFileDialog,
    QMenu,
    QStatusBar,
    QLabel,
    QDialog,
    QPushButton,
    QSizePolicy,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from .settings import Settings
from .renderer import render_markdown
from .dialogs import AppearanceDialog, FindBar
from .version import __version__, APP_NAME


ZOOM_MIN = 6
ZOOM_MAX = 72

# ---------------------------------------------------------------------------
# Custom widgets — intercept Ctrl+Scroll before the widget consumes it
# ---------------------------------------------------------------------------

class _WebView(QWebEngineView):
    ctrl_scroll = pyqtSignal(int)  # positive = up, negative = down

    def childEvent(self, event):
        super().childEvent(event)
        # WebEngine renders inside a native child widget; install an event
        # filter on every child so Ctrl+Scroll reaches us even from there.
        if event.type() == QEvent.Type.ChildAdded:
            child = event.child()
            if isinstance(child, QWidget):
                child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.ctrl_scroll.emit(event.angleDelta().y())
                return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.ctrl_scroll.emit(event.angleDelta().y())
            event.accept()
        else:
            super().wheelEvent(event)

    # Let the main window handle drops
    def dragEnterEvent(self, event):
        event.ignore()

    def dropEvent(self, event):
        event.ignore()


class _WhitespaceFader(QSyntaxHighlighter):
    """Makes space/tab/¶ glyphs dim and keeps regular text at full brightness.

    How it works: QPalette::Text is set to the dim color, so Qt renders the
    ¶ glyph (ShowLineAndParagraphSeparators) and the · / → markers
    (ShowTabsAndSpaces) in that dim color automatically.  This highlighter
    then overrides every run of *non*-whitespace characters back to the full
    text color, so readable text is never dimmed.
    """

    def __init__(self, document):
        super().__init__(document)
        self._normal_fmt = QTextCharFormat()

    def set_normal_color(self, color: QColor):
        self._normal_fmt.setForeground(color)
        self.rehighlight()

    def highlightBlock(self, text: str):
        # Restore non-whitespace runs to the full text color.
        start = None
        for i, ch in enumerate(text):
            if ch not in (' ', '\t'):
                if start is None:
                    start = i
            else:
                if start is not None:
                    self.setFormat(start, i - start, self._normal_fmt)
                    start = None
        if start is not None:
            self.setFormat(start, len(text) - start, self._normal_fmt)


class _IndentGuides(QWidget):
    """Transparent overlay that draws indent guide lines on the editor viewport."""

    def __init__(self, editor: 'QPlainTextEdit'):
        super().__init__(editor.viewport())
        self._ed = editor
        self._color = QColor(128, 128, 128, 128)
        self._width = 1
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.setGeometry(editor.viewport().rect())
        self.raise_()
        self.show()
        editor.updateRequest.connect(self._on_update)
        editor.document().contentsChanged.connect(self.update)
        editor.cursorPositionChanged.connect(self.update)
        editor.viewport().installEventFilter(self)

    def set_style(self, color_hex: str, opacity: float, width: int):
        c = QColor(color_hex)
        c.setAlphaF(max(0.0, min(1.0, opacity)))
        self._color = c
        self._width = max(1, width)
        self.update()

    def _on_update(self, rect, dy):
        # Transparent overlay must always do a full repaint; scroll() corrupts it.
        # Use update() not repaint(): repaint() is synchronous and re-enters
        # paintEvent via updateRequest, causing recursive repaint → segfault.
        self.update()

    def eventFilter(self, obj, event):
        if obj is self._ed.viewport() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._ed.viewport().rect())
        return False

    def _detect_indent_unit(self) -> int:
        """Return the smallest non-zero leading-whitespace count in the document (min 1).
        Tabs are counted as 4 spaces."""
        unit = 4
        doc = self._ed.document()
        for i in range(min(doc.blockCount(), 400)):
            text = doc.findBlockByNumber(i).text()
            n = 0
            for ch in text:
                if ch == ' ':
                    n += 1
                elif ch == '\t':
                    n += 4
                else:
                    break
            if 0 < n < unit:
                unit = n
                if unit == 1:
                    break
        return unit

    def paintEvent(self, event):
        ed = self._ed
        fm = ed.fontMetrics()
        char_w = fm.horizontalAdvance(' ')
        doc_margin = int(ed.document().documentMargin())
        offset = ed.contentOffset()
        vp_height = ed.viewport().height()

        indent_unit = self._detect_indent_unit()

        painter = QPainter(self)
        guide_pen = QPen(self._color)
        guide_pen.setWidth(self._width)

        block = ed.firstVisibleBlock()
        while block.isValid():
            geom = ed.blockBoundingGeometry(block).translated(offset)
            top = int(geom.top())
            if top > vp_height:
                break
            bot = int(geom.bottom()) + 1
            text = block.text()

            # Indent guides only
            n = 0
            for ch in text:
                if ch == ' ':
                    n += 1
                elif ch == '\t':
                    n += indent_unit
                else:
                    break
            levels = n // indent_unit
            if levels:
                painter.setPen(guide_pen)
                for lvl in range(1, levels + 1):
                    x = doc_margin + (lvl * indent_unit - indent_unit // 2) * char_w
                    painter.drawLine(x, top, x, bot)

            block = block.next()

        painter.end()


class _LineNumberArea(QWidget):
    """Gutter widget — delegates all painting to the editor."""

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class _Editor(QPlainTextEdit):
    ctrl_scroll = pyqtSignal(int)
    paste_done  = pyqtSignal()
    paste_image = pyqtSignal(object)  # QImage

    def __init__(self):
        super().__init__()
        self._show_line_numbers = False
        self._ln_color = QColor(128, 128, 128)
        self._ln_bg    = QColor(240, 240, 240)
        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_ln_width)
        self.updateRequest.connect(self._update_ln_area)
        # Intercept drag-and-drop on the viewport so URL drops propagate to
        # the main window rather than being inserted as text (or crashing).
        self.viewport().installEventFilter(self)
        # Auto-renumber ordered lists
        self._renumbering = False
        self._renumber_timer = QTimer(self)
        self._renumber_timer.setSingleShot(True)
        self._renumber_timer.setInterval(120)
        self._renumber_timer.timeout.connect(self._renumber_lists)
        self.document().contentsChanged.connect(self._schedule_renumber)

    # --------------------------------------------------------- line numbers

    def set_line_numbers(self, show: bool):
        self._show_line_numbers = show
        self._line_number_area.setVisible(show)
        self._update_ln_width()

    def set_line_number_colors(self, fg: QColor, bg: QColor):
        self._ln_color = fg
        self._ln_bg    = bg
        self._line_number_area.update()

    def line_number_area_width(self) -> int:
        if not self._show_line_numbers:
            return 0
        digits = len(str(max(1, self.blockCount())))
        return 6 + QFontMetrics(self.font()).horizontalAdvance('9' * digits)

    def _update_ln_width(self, _=0):
        w = self.line_number_area_width()
        self.setViewportMargins(w, 0, 0, 0)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), w, cr.height()))

    def _update_ln_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_ln_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self._ln_bg)
        painter.setPen(self._ln_color)
        painter.setFont(self.font())

        block     = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top    = round(self.blockBoundingGeometry(block)
                           .translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    QRect(0, top,
                          self._line_number_area.width() - 4,
                          round(self.blockBoundingRect(block).height())),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    str(block_num + 1)
                )
            block     = block.next()
            block_num += 1
            top    = bottom
            bottom = top + (round(self.blockBoundingRect(block).height())
                            if block.isValid() else 0)

        painter.end()

    # --------------------------------------------------------- events

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.ctrl_scroll.emit(event.angleDelta().y())
            event.accept()
        else:
            super().wheelEvent(event)


    def keyPressEvent(self, event):
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if ctrl and not shift and key == Qt.Key.Key_B:
            self._toggle_format("**")
        elif ctrl and not shift and key == Qt.Key.Key_I:
            self._toggle_format("*")
        elif ctrl and not shift and key == Qt.Key.Key_Up:
            sb = self.verticalScrollBar()
            sb.setValue(sb.value() - 1)
        elif ctrl and not shift and key == Qt.Key.Key_Down:
            sb = self.verticalScrollBar()
            sb.setValue(sb.value() + 1)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not ctrl:
            if not self._smart_enter():
                super().keyPressEvent(event)
        elif key == Qt.Key.Key_Tab and not event.modifiers():
            self._indent_line()
        elif key == Qt.Key.Key_Backtab:
            self._dedent_line()
        elif event.text() == "[":
            self._auto_pair("[", "]")
        elif event.text() == "(":
            self._auto_pair("(", ")")
        elif key == Qt.Key.Key_Backspace and self._between_pair():
            c = self.textCursor()
            c.deleteChar()
            c.deletePreviousChar()
            self.setTextCursor(c)
        elif key == Qt.Key.Key_Backspace and self._at_bullet_marker():
            self._dedent_bullet_to_parent()
        else:
            super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        """Paste plain text; images → signal; URLs onto selection → [text](uri)."""
        if source.hasImage():
            img = source.imageData()
            if isinstance(img, QImage) and not img.isNull():
                self.paste_image.emit(img)
                return
        text = source.text().strip()
        cursor = self.textCursor()
        if cursor.hasSelection() and re.match(r"^https?://|^ftp://|^file://", text):
            selected = cursor.selectedText()
            cursor.insertText(f"[{selected}]({text})")
            self.setTextCursor(cursor)
        else:
            # Always insert as plain text to prevent pasted rich content from
            # overriding the editor font/size set by the zoom level.
            self.insertPlainText(source.text())
        self.paste_done.emit()

    def eventFilter(self, obj, event):
        # QPlainTextEdit routes drag events through its viewport widget, so
        # we intercept them here and forward file-URL drops to the MainWindow.
        # Returning True stops Qt's default handler (which would insert text);
        # we accept the drag so the OS shows a valid drop cursor, then hand
        # the actual drop off to the main window's existing handler.
        if obj is self.viewport():
            if event.type() == QEvent.Type.DragEnter and event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if urls and urls[0].toLocalFile().lower().endswith((".md", ".txt")):
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True
            if event.type() == QEvent.Type.Drop and event.mimeData().hasUrls():
                self.window().dropEvent(event)
                return True
        return super().eventFilter(obj, event)

    def _between_pair(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        pos = cursor.position()
        doc = self.document()
        pairs = {"[": "]", "(": ")"}
        return (pos > 0 and
                doc.characterAt(pos - 1) in pairs and
                doc.characterAt(pos) == pairs[doc.characterAt(pos - 1)])

    def _at_bullet_marker(self) -> bool:
        """True when cursor is right before the list marker (or at col 0 of an indented bullet)."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        pos = cursor.positionInBlock()
        line = cursor.block().text()
        m = re.match(r"^( *)([-*+]|\d+\.) ", line)
        if not m:
            return False
        marker_start = len(m.group(1))
        # trigger when cursor is right before the marker, or at col 0 on an indented bullet
        return pos == marker_start or (pos == 0 and marker_start > 0)

    def _dedent_bullet_to_parent(self):
        """Dedent current bullet to the indentation level of its nearest parent bullet."""
        cursor = self.textCursor()
        line = cursor.block().text()
        m = re.match(r"^( *)([-*+]|\d+\.)", line)
        if not m:
            return
        current_indent = len(m.group(1))
        if current_indent == 0:
            return

        # Scan upward for the nearest bullet with strictly less indentation
        target_indent = 0
        block = cursor.block().previous()
        while block.isValid():
            bm = re.match(r"^( *)([-*+]|\d+\.) ", block.text())
            if bm and len(bm.group(1)) < current_indent:
                target_indent = len(bm.group(1))
                break
            block = block.previous()

        spaces_to_remove = current_indent - target_indent
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        for _ in range(spaces_to_remove):
            cursor.deleteChar()
        self.setTextCursor(cursor)

    def _auto_pair(self, open_ch: str, close_ch: str):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(f"{open_ch}{selected}{close_ch}")
        else:
            cursor.insertText(f"{open_ch}{close_ch}")
            cursor.movePosition(QTextCursor.MoveOperation.Left)
        self.setTextCursor(cursor)

    def _toggle_format(self, marker: str):
        """Wrap/unwrap the current selection with a Markdown inline marker.

        marker="*"  → italic,  marker="**" → bold.
        If the selection is already wrapped, the markers are removed instead.
        With no selection, inserts the marker pair and places the cursor between them.
        """
        cursor = self.textCursor()
        ml = len(marker)
        if cursor.hasSelection():
            selected = cursor.selectedText()
            if (selected.startswith(marker) and selected.endswith(marker)
                    and len(selected) > 2 * ml):
                cursor.insertText(selected[ml:-ml])
            else:
                cursor.insertText(f"{marker}{selected}{marker}")
            self.setTextCursor(cursor)
        else:
            pos = cursor.position()
            cursor.insertText(f"{marker}{marker}")
            cursor.setPosition(pos + ml)
            self.setTextCursor(cursor)

    def _smart_enter(self) -> bool:
        """Handle Enter key for list continuation.

        Returns True if the event was handled (list context), False to let
        the caller fall through to the default Qt key handler (plain lines).
        """
        cursor = self.textCursor()
        line = cursor.block().text()

        indent_len = len(line) - len(line.lstrip())
        indent_str = line[:indent_len]
        stripped = line.lstrip()

        # Detect list marker (unordered or ordered)
        m = re.match(r"^([-*+]) +", stripped)
        if m:
            marker = m.group(1) + " "
        else:
            m = re.match(r"^(\d+)\. +", stripped)
            marker = (str(int(m.group(1)) + 1) + ". ") if m else ""

        # No list marker → let Qt insert a plain newline
        if not marker:
            return False

        # Empty list item (marker with no content) → remove marker, stop list
        if not stripped[len(marker):].strip():
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(indent_str)
            self.setTextCursor(cursor)
            return True

        cursor.insertText("\n" + indent_str + marker)
        self.setTextCursor(cursor)
        return True

    def _indent_line(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            self._indent_selection(cursor, indent=True)
        else:
            pos = cursor.positionInBlock()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.insertText("    ")
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.Right,
                                QTextCursor.MoveMode.MoveAnchor, pos + 4)
            self.setTextCursor(cursor)

    def _dedent_line(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            self._indent_selection(cursor, indent=False)
        else:
            line = cursor.block().text()
            pos = cursor.positionInBlock()
            spaces = min(len(line) - len(line.lstrip(" ")), 4)
            if spaces:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                for _ in range(spaces):
                    cursor.deleteChar()
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QTextCursor.MoveOperation.Right,
                                    QTextCursor.MoveMode.MoveAnchor,
                                    max(0, pos - spaces))
                self.setTextCursor(cursor)

    def _indent_selection(self, cursor, indent: bool):
        doc = self.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        first_block = doc.findBlock(start).blockNumber()
        last_block  = doc.findBlock(end).blockNumber()
        # Don't indent the last block if the selection ends at its very start
        end_cursor = QTextCursor(doc)
        end_cursor.setPosition(end)
        if end_cursor.positionInBlock() == 0 and last_block > first_block:
            last_block -= 1

        cursor.beginEditBlock()
        for bn in range(first_block, last_block + 1):
            block = doc.findBlockByNumber(bn)
            c = QTextCursor(block)
            if indent:
                c.insertText("    ")
            else:
                spaces = min(len(block.text()) - len(block.text().lstrip(" ")), 4)
                c.movePosition(QTextCursor.MoveOperation.Right,
                               QTextCursor.MoveMode.KeepAnchor, spaces)
                c.removeSelectedText()
        cursor.endEditBlock()

    def _schedule_renumber(self):
        if not self._renumbering:
            self._renumber_timer.start()

    def _renumber_lists(self):
        self._renumbering = True
        try:
            doc = self.document()
            cursor = QTextCursor(doc)
            counters = {}  # indent -> next expected number
            edit_started = False
            b = doc.begin()
            while b.isValid():
                text = b.text()
                m = re.match(r'^(\s*)(\d+)\. ', text)
                if m:
                    indent = len(m.group(1))
                    actual = int(m.group(2))
                    for k in list(counters.keys()):
                        if k > indent:
                            del counters[k]
                    expected = counters.get(indent, 1)
                    counters[indent] = expected + 1
                    if actual != expected:
                        if not edit_started:
                            cursor.joinPreviousEditBlock()
                            edit_started = True
                        c = QTextCursor(b)
                        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                        old_len = indent + len(m.group(2)) + 2
                        c.movePosition(QTextCursor.MoveOperation.Right,
                                       QTextCursor.MoveMode.KeepAnchor, old_len)
                        c.insertText(' ' * indent + str(expected) + '. ')
                elif text.strip() and not text[:1] == ' ':
                    counters.clear()
                b = b.next()
            if edit_started:
                cursor.endEditBlock()
        finally:
            self._renumbering = False


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.current_file: str | None = None
        self.modified = False
        self.view_mode = True  # True = view, False = edit

        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_shortcuts()
        self._restore_geometry()

        self.setAcceptDrops(True)
        self._update_title()
        self._render_view()  # paint correct background immediately

        if self.settings["reopen_last_file"]:
            last = self.settings["last_file"]
            if last and os.path.isfile(last):
                self._load_file(last)

        # No file loaded → default to edit mode
        if not self.current_file:
            self.switch_to_edit_mode()

        # Style application (setDefaultTextOption, rehighlight) fires textChanged
        # and spuriously marks the document modified.  Clear it now that setup is done.
        self.modified = False
        self._update_title()

    # ------------------------------------------------------------------ setup

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self._stack = QStackedWidget()
        vbox.addWidget(self._stack)

        self._viewer = _WebView()
        self._viewer.ctrl_scroll.connect(self._on_ctrl_scroll)
        self._viewer.page().setBackgroundColor(QColor(self.settings["bg_color"]))
        self._viewer.loadFinished.connect(self._on_view_loaded)
        self._pending_scroll = None
        self._view_scroll_ratio = 0.0   # kept in sync by scrollPositionChanged
        self._viewer.page().scrollPositionChanged.connect(self._on_viewer_scroll)
        self._stack.addWidget(self._viewer)

        self._editor = _Editor()
        self._editor.ctrl_scroll.connect(self._on_ctrl_scroll)
        self._editor.paste_done.connect(self._apply_editor_style)
        self._editor.paste_image.connect(self._on_paste_image)
        self._editor.textChanged.connect(self._mark_modified)
        self._editor.textChanged.connect(self._update_status_counts)
        self._editor.cursorPositionChanged.connect(self._update_status_counts)
        self._guides = _IndentGuides(self._editor)
        self._ws_fader = _WhitespaceFader(self._editor.document())
        self._stack.addWidget(self._editor)

        self._find_bar = FindBar()
        self._find_bar.find_requested.connect(self._do_find)
        self._find_bar.closed.connect(self._focus_current)
        vbox.addWidget(self._find_bar)

        self._status = QStatusBar()
        self.setStatusBar(self._status)

        # Left: mode indicator (read-only label — use the toolbar button to toggle).
        self._lbl_mode = QLabel("Ready")
        self._lbl_mode.setContentsMargins(4, 0, 8, 0)
        self._status.addWidget(self._lbl_mode)

        # Right: permanent info labels — always visible regardless of messages.
        self._lbl_zoom  = QLabel()
        self._lbl_chars = QLabel()
        self._lbl_words = QLabel()
        for lbl in (self._lbl_zoom, self._lbl_chars, self._lbl_words):
            lbl.setContentsMargins(8, 0, 8, 0)
            self._status.addPermanentWidget(lbl)

        self._stack.setCurrentWidget(self._viewer)
        self._apply_editor_style()
        self._update_status_zoom()
        self._update_status_counts()

    def _setup_menus(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")

        act = QAction("&Open…", self)
        act.setShortcut(QKeySequence.StandardKey.Open)
        act.triggered.connect(self.open_file_dialog)
        file_menu.addAction(act)

        file_menu.addSeparator()

        act = QAction("&Save", self)
        act.setShortcut(QKeySequence.StandardKey.Save)
        act.triggered.connect(self.save_file)
        file_menu.addAction(act)

        act = QAction("Save &As…", self)
        act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act.triggered.connect(self.save_as_file)
        file_menu.addAction(act)

        file_menu.addSeparator()

        self._recent_menu = QMenu("Recent &Files", self)
        file_menu.addMenu(self._recent_menu)
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        act = QAction("E&xit", self)
        act.setShortcut(QKeySequence.StandardKey.Quit)
        act.triggered.connect(self.close)
        file_menu.addAction(act)

        # View
        view_menu = mb.addMenu("&View")

        self._toggle_act = QAction("Switch to &Text editor", self)
        self._toggle_act.setShortcut(QKeySequence("Ctrl+E"))
        self._toggle_act.triggered.connect(self.toggle_mode)
        view_menu.addAction(self._toggle_act)

        self._wrap_act = QAction("&Word Wrap", self)
        self._wrap_act.setCheckable(True)
        self._wrap_act.setChecked(bool(self.settings.get("word_wrap", True)))
        self._wrap_act.triggered.connect(self._toggle_word_wrap)
        view_menu.addAction(self._wrap_act)

        view_menu.addSeparator()

        act = QAction("&Settings…", self)
        act.triggered.connect(self.show_appearance_dialog)
        view_menu.addAction(act)

        # Help
        help_menu = mb.addMenu("&Help")
        act = QAction("&About", self)
        act.triggered.connect(self._show_about)
        help_menu.addAction(act)

    def _setup_toolbar(self):
        tb = QToolBar("Main toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        def _act(label, tip, slot):
            a = QAction(label, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            tb.addAction(a)
            return a

        _act("Open", "Open file  (Ctrl+O)", self.open_file_dialog)
        _act("Save", "Save file  (Ctrl+S)", self.save_file)
        tb.addSeparator()

        self._mode_btn = _act("Text", "Toggle Text / Markdown  (Ctrl+E)", self.toggle_mode)
        tb.addSeparator()

        _act("⊟ Collapse all", "Collapse all list items", self.collapse_all)
        _act("⊞ Expand all", "Expand all list items", self.expand_all)
        tb.addSeparator()

        self._wrap_tb_act = QAction("Word Wrap", self)
        self._wrap_tb_act.setCheckable(True)
        self._wrap_tb_act.setChecked(bool(self.settings.get("word_wrap", True)))
        self._wrap_tb_act.setToolTip("Toggle word wrap")
        self._wrap_tb_act.triggered.connect(self._toggle_word_wrap)
        tb.addAction(self._wrap_tb_act)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        _act("Settings", "Settings & shortcuts", self.show_appearance_dialog)

    def _setup_shortcuts(self):
        # Escape: dismiss find bar → switch to text editor → exit
        esc_sc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_sc.activated.connect(self._on_escape)

        # Find bar
        find_sc = QShortcut(QKeySequence.StandardKey.Find, self)
        find_sc.activated.connect(self._show_find_bar)

        # Configurable toggle mode shortcut (default Ctrl+Shift+Return)
        self._toggle_sc = QShortcut(
            QKeySequence(self.settings.get("toggle_mode_shortcut", "Ctrl+Shift+Return")), self
        )
        self._toggle_sc.activated.connect(self.toggle_mode)
        # Also match numpad Enter — derive from the saved setting
        _kp_key = self.settings.get("toggle_mode_shortcut", "Ctrl+Shift+Return").replace("Return", "Enter")
        self._toggle_sc_kp = QShortcut(QKeySequence(_kp_key), self)
        self._toggle_sc_kp.activated.connect(self.toggle_mode)

        # Configurable collapse / expand
        self._collapse_sc = QShortcut(
            QKeySequence(self.settings["collapse_all_shortcut"]), self
        )
        self._collapse_sc.activated.connect(self.collapse_all)

        self._expand_sc = QShortcut(
            QKeySequence(self.settings["expand_all_shortcut"]), self
        )
        self._expand_sc.activated.connect(self.expand_all)

    def _on_escape(self):
        if self._find_bar.isVisible():
            self._find_bar.hide()
            self._focus_current()
        elif self.view_mode:
            self.switch_to_edit_mode()
        else:
            self.close()

    def _update_configurable_shortcuts(self):
        toggle_key = self.settings.get("toggle_mode_shortcut", "Ctrl+Shift+Return")
        self._toggle_sc.setKey(QKeySequence(toggle_key))
        # Keep numpad Enter variant in sync: replace Return→Enter in the key string
        kp_key = toggle_key.replace("Return", "Enter")
        self._toggle_sc_kp.setKey(QKeySequence(kp_key))
        self._collapse_sc.setKey(QKeySequence(self.settings["collapse_all_shortcut"]))
        self._expand_sc.setKey(QKeySequence(self.settings["expand_all_shortcut"]))

    # ---------------------------------------------------------------- geometry

    def _restore_geometry(self):
        self.setGeometry(
            self.settings["window_x"],
            self.settings["window_y"],
            self.settings["window_width"],
            self.settings["window_height"],
        )

    def _save_geometry(self):
        g = self.geometry()
        self.settings["window_x"] = g.x()
        self.settings["window_y"] = g.y()
        self.settings["window_width"] = g.width()
        self.settings["window_height"] = g.height()

    # ---------------------------------------------------------------- file ops

    def open_file_dialog(self):
        if not self._confirm_discard():
            return
        start_dir = self.settings.get("open_dir", "") or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            start_dir,
            "Markdown / Text (*.md *.txt);;All files (*)",
        )
        if path:
            self.settings["open_dir"] = os.path.dirname(path)
            self._load_file(path)

    def _load_file(self, path: str):
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Cannot open file:\n{exc}")
            return

        self._editor.textChanged.disconnect(self._mark_modified)
        self._editor.setPlainText(content)
        self._editor.textChanged.connect(self._mark_modified)

        self.current_file = path
        self.modified = False
        self.settings.add_recent_file(path)
        self.settings["last_file"] = path
        self._rebuild_recent_menu()
        self._update_title()
        self._status.showMessage(f"Opened: {os.path.basename(path)}", 3000)

        # Always show the rendered view after opening
        if not self.view_mode:
            self.view_mode = True
            self._stack.setCurrentWidget(self._viewer)
            self._mode_btn.setText("Text")
            self._toggle_act.setText("Switch to &Text editor")
        self._lbl_mode.setText("Markdown view")
        self._render_view()

    def save_file(self):
        if not self.current_file:
            self.save_as_file()
            return
        self._write_file(self.current_file)

    def save_as_file(self):
        if self.current_file:
            default = self.current_file
        else:
            start_dir = self.settings.get("open_dir", "") or os.path.expanduser("~")
            default = os.path.join(start_dir, "untitled.md")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            default,
            "Markdown (*.md);;Text (*.txt);;All files (*)",
        )
        if path:
            if not os.path.splitext(path)[1]:
                path += ".md"
            self._write_file(path)
            self.current_file = path
            self.settings.add_recent_file(path)
            self.settings["last_file"] = path
            self.settings["open_dir"] = os.path.dirname(path)
            self._rebuild_recent_menu()
            self._update_title()

    def _on_paste_image(self, img: QImage):
        """Save a pasted image to the configured folder and insert a Markdown image link."""
        if not self.current_file:
            self._status.showMessage("Save the document first to paste images.", 4000)
            return
        folder = self.settings.get("image_paste_folder", "assets").strip() or "assets"
        img_dir = os.path.join(os.path.dirname(self.current_file), folder)
        os.makedirs(img_dir, exist_ok=True)
        name = "image-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".png"
        dest = os.path.join(img_dir, name)
        if not img.save(dest, "PNG"):
            self._status.showMessage("Failed to save pasted image.", 4000)
            return
        self._editor.insertPlainText(f"![image]({folder}/{name})")
        self._status.showMessage(f"Image saved: {folder}/{name}", 3000)

    def _write_file(self, path: str):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._editor.toPlainText())
            self.modified = False
            self._update_title()
            self._status.showMessage(f"Saved: {os.path.basename(path)}", 3000)
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Cannot save file:\n{exc}")

    def _confirm_discard(self) -> bool:
        """Return True if safe to proceed (no unsaved changes, or user confirms)."""
        if not self.modified:
            return True

        dlg = QDialog(self)
        dlg.setWindowTitle("Unsaved changes")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("You have unsaved changes."))

        btn_row = QHBoxLayout()
        save_btn    = QPushButton("Save  [S]")
        discard_btn = QPushButton("Discard  [D]")
        cancel_btn  = QPushButton("Cancel  [Esc]")
        btn_row.addWidget(save_btn)
        btn_row.addWidget(discard_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        result = [None]

        def _save():
            result[0] = "save"
            dlg.accept()

        def _discard():
            result[0] = "discard"
            dlg.accept()

        save_btn.clicked.connect(_save)
        discard_btn.clicked.connect(_discard)
        cancel_btn.clicked.connect(dlg.reject)
        QShortcut(QKeySequence("S"), dlg).activated.connect(_save)
        QShortcut(QKeySequence("D"), dlg).activated.connect(_discard)

        dlg.exec()

        if result[0] == "save":
            self.save_file()
            return not self.modified
        if result[0] == "discard":
            return True
        return False

    # --------------------------------------------------------------- mode toggle

    def toggle_mode(self):
        if self.view_mode:
            self.switch_to_edit_mode()
        else:
            self.switch_to_view_mode()

    def switch_to_view_mode(self):
        self.view_mode = True
        self._render_view(sync_scroll=True)
        self._stack.setCurrentWidget(self._viewer)
        self._mode_btn.setText("Markdown")
        self._mode_btn.setToolTip("Switch to text editor  (Ctrl+E)")
        self._toggle_act.setText("Switch to &Text editor")
        self._lbl_mode.setText("Markdown view")

    def switch_to_edit_mode(self):
        self.view_mode = False
        self._stack.setCurrentWidget(self._editor)
        self._mode_btn.setText("Text")
        self._mode_btn.setToolTip("Switch to Markdown view  (Ctrl+E)")
        self._toggle_act.setText("Switch to &Markdown view")
        self._apply_editor_style()
        self._lbl_mode.setText("Text editor")

        # Restore editor position using the scroll ratio we track synchronously.
        # If the page hasn't finished loading/scrolling yet (_pending_scroll still
        # set), use the intended ratio and discard the pending scroll so the now-
        # hidden viewer is not scrolled after we leave.
        if self._pending_scroll is not None:
            ratio = self._pending_scroll
            self._pending_scroll = None
        else:
            ratio = self._view_scroll_ratio
        self._restore_editor_scroll(ratio)

        # Give focus directly if the window is already active (normal case).
        # If not active (e.g. after drag-and-drop), changeEvent(WindowActivate)
        # will give focus once the user activates the window.
        self._editor.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_viewer_scroll(self, pos):
        """Keep _view_scroll_ratio in sync whenever the viewer scrolls."""
        cs = self._viewer.page().contentsSize()
        denom = max(1.0, cs.height() - self._viewer.height())
        self._view_scroll_ratio = min(1.0, max(0.0, pos.y() / denom))

    def _restore_editor_scroll(self, ratio):
        """Position the editor at the block corresponding to the viewer's scroll ratio.

        The cursor is set synchronously (so a subsequent text→MD switch captures
        the right position).  The viewport scroll is deferred one event-loop tick
        so Qt has time to finish the layout invalidation triggered by setFont()
        inside _apply_editor_style — otherwise centerCursor() uses stale geometry
        and snaps to the top of the document.
        """
        if not ratio:
            ratio = 0.0
        doc = self._editor.document()
        total = max(doc.blockCount() - 1, 1)
        target_block = round(ratio * total)
        block = doc.findBlockByNumber(target_block)
        cursor = QTextCursor(block)
        self._editor.setTextCursor(cursor)   # synchronous — captured by next toggle

        def _apply_scroll():
            sb = self._editor.verticalScrollBar()
            sb.setValue(round(ratio * sb.maximum()))
        QTimer.singleShot(0, _apply_scroll)

    # ---------------------------------------------------------------- rendering

    def _render_view(self, sync_scroll=False):
        if sync_scroll:
            cur = self._editor.textCursor()
            total = max(self._editor.document().blockCount() - 1, 1)
            self._pending_scroll = cur.blockNumber() / total
        html = render_markdown(self._editor.toPlainText(), self.settings)
        if self.current_file:
            base_url = QUrl.fromLocalFile(os.path.dirname(self.current_file) + os.sep)
        else:
            base_url = QUrl("about:blank")
        self._viewer.setHtml(html, base_url)

    def _on_view_loaded(self, ok):
        if ok and self._pending_scroll is not None:
            ratio = self._pending_scroll
            # Pre-seed the synchronous tracker so switch_to_edit_mode has a
            # valid ratio even in the brief window before scrollPositionChanged fires.
            self._view_scroll_ratio = ratio
            self._viewer.page().runJavaScript(
                f"var t = document.body.scrollHeight * {ratio:.4f};"
                f"window.scrollTo(0, Math.max(0, t - window.innerHeight / 2));"
            )
        self._pending_scroll = None

    def collapse_all(self):
        if self.view_mode:
            self._viewer.page().runJavaScript("collapseAll()")

    def expand_all(self):
        if self.view_mode:
            self._viewer.page().runJavaScript("expandAll()")

    # ----------------------------------------------------------- editor style

    def _apply_editor_style(self):
        _was_modified = self.modified
        font = QFont(self.settings["font_family"], self.settings["font_size"])
        self._editor.setFont(font)
        self._editor.setTabStopDistance(4 * self._editor.fontMetrics().horizontalAdvance(' '))

        # Enable both space/tab dots AND the ¶ end-of-line marker.
        opt = QTextOption()
        opt.setFlags(
            QTextOption.Flag.ShowTabsAndSpaces
            | QTextOption.Flag.ShowLineAndParagraphSeparators
        )
        self._editor.document().setDefaultTextOption(opt)

        tc = QColor(self.settings["text_color"])
        bc = QColor(self.settings["bg_color"])
        op = max(0.0, min(1.0, self.settings["symbol_opacity"]))
        dim = QColor(
            int(tc.red()   * op + bc.red()   * (1 - op)),
            int(tc.green() * op + bc.green() * (1 - op)),
            int(tc.blue()  * op + bc.blue()  * (1 - op)),
        )

        # Qt renders ¶ (and · →) using QPalette::Text.  Set it to dim so all
        # non-printing markers appear faded.  The highlighter then restores
        # every non-whitespace character run to the full text color.
        pal = self._editor.palette()
        pal.setColor(QPalette.ColorRole.Base, bc)
        pal.setColor(QPalette.ColorRole.Text, dim)
        self._editor.setPalette(pal)
        self._editor.viewport().setPalette(pal)

        guide_color = self.settings["guide_color"] or self.settings["text_color"]
        self._guides.set_style(guide_color, self.settings["guide_opacity"], self.settings["guide_width"])

        self._ws_fader.set_normal_color(tc)

        # Line number colors: guide_color × symbol_opacity blended onto bg_color.
        guide_hex = self.settings["guide_color"] or self.settings["text_color"]
        gc = QColor(guide_hex)
        ln_fg = QColor(
            int(gc.red()   * op + bc.red()   * (1 - op)),
            int(gc.green() * op + bc.green() * (1 - op)),
            int(gc.blue()  * op + bc.blue()  * (1 - op)),
        )
        ln_bg_hex = self.settings.get("ln_bg_color", "")
        if ln_bg_hex:
            ln_bg = QColor(ln_bg_hex)
        else:
            ln_bg = QColor(
                int(gc.red()   * 0.12 + bc.red()   * 0.88),
                int(gc.green() * 0.12 + bc.green() * 0.88),
                int(gc.blue()  * 0.12 + bc.blue()  * 0.88),
            )
        self._editor.set_line_numbers(self.settings.get("show_line_numbers", False))
        self._editor.set_line_number_colors(ln_fg, ln_bg)

        self._apply_word_wrap()
        self.modified = _was_modified

    # -------------------------------------------------------------- status bar

    def _update_status_zoom(self):
        self._lbl_zoom.setText(f"{self.settings['font_size']} pt")

    def _update_status_counts(self):
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            text   = cursor.selectedText()
            suffix = " (sel)"
        else:
            text   = self._editor.toPlainText()
            suffix = ""
        chars = len(text)
        words = len(text.split()) if text.strip() else 0
        self._lbl_chars.setText(f"{chars:,} chars{suffix}")
        self._lbl_words.setText(f"{words:,} words{suffix}")

    # -------------------------------------------------------------- Ctrl+Scroll

    def _on_ctrl_scroll(self, delta: int):
        # Clamp on read too — guards against a corrupted settings value.
        size = max(ZOOM_MIN, min(ZOOM_MAX, int(self.settings["font_size"])))
        new_size = max(ZOOM_MIN, min(ZOOM_MAX, size + (1 if delta > 0 else -1)))
        if new_size != size:
            self.settings["font_size"] = new_size
            self._update_status_zoom()
            if self.view_mode:
                self._render_view()
            else:
                self._apply_editor_style()

    # ------------------------------------------------------------------- find

    def _show_find_bar(self):
        self._find_bar.show_and_focus()

    def _do_find(self, text: str, backward: bool):
        if self.view_mode:
            flags = QWebEnginePage.FindFlag.FindBackward if backward else QWebEnginePage.FindFlag(0)
            self._viewer.findText(text, flags)
        else:
            doc_flags = QTextDocument.FindFlag(0)
            if backward:
                doc_flags = QTextDocument.FindFlag.FindBackward
            found = self._editor.find(text, doc_flags)
            if not found:
                # Wrap around
                cur = self._editor.textCursor()
                if backward:
                    cur.movePosition(QTextCursor.MoveOperation.End)
                else:
                    cur.movePosition(QTextCursor.MoveOperation.Start)
                self._editor.setTextCursor(cur)
                self._editor.find(text, doc_flags)

    def _focus_current(self):
        if self.view_mode:
            self._viewer.setFocus()
        else:
            self._editor.setFocus()

    # --------------------------------------------------------------- appearance

    def show_appearance_dialog(self):
        saved = self.settings.copy()
        dlg = AppearanceDialog(self.settings, self)
        dlg.settings_changed.connect(self._on_appearance_live)
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted:
            dlg.apply_final()
            self._update_configurable_shortcuts()
        else:
            self.settings.restore(saved)
        self._on_appearance_live()

    def _toggle_word_wrap(self, checked: bool):
        self.settings["word_wrap"] = checked
        self._apply_word_wrap()

    def _apply_word_wrap(self):
        on = bool(self.settings.get("word_wrap", True))
        mode = (QPlainTextEdit.LineWrapMode.WidgetWidth if on
                else QPlainTextEdit.LineWrapMode.NoWrap)
        self._editor.setLineWrapMode(mode)
        if hasattr(self, "_wrap_act"):
            self._wrap_act.setChecked(on)
        if hasattr(self, "_wrap_tb_act"):
            self._wrap_tb_act.setChecked(on)

    def _on_appearance_live(self):
        self._viewer.page().setBackgroundColor(QColor(self.settings["bg_color"]))
        self._apply_editor_style()
        self._update_status_zoom()
        if self.view_mode:
            self._render_view()

    # ------------------------------------------------------------------ title

    def _update_title(self):
        name = os.path.basename(self.current_file) if self.current_file else "Untitled"
        self.setWindowTitle(f"{name}{' *' if self.modified else ''} — {APP_NAME} v{__version__}")

    def _mark_modified(self):
        if not self.modified:
            self.modified = True
            self._update_title()

    # ---------------------------------------------------------------- drag-drop

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if path.lower().endswith((".md", ".txt")):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith((".md", ".txt")) and self._confirm_discard():
                self._load_file(path)
                # Defer activation: calling activateWindow() during the drop
                # event is ignored on X11/Wayland (focus-stealing prevention).
                # Deferring lets the OS finish the drag-drop protocol first.
                QTimer.singleShot(0, lambda: (
                    QApplication.setActiveWindow(self),
                    self.activateWindow(),
                    self.raise_(),
                ))

    def changeEvent(self, event):
        super().changeEvent(event)
        # When the window becomes active (e.g. user clicks it after drag-drop),
        # ensure the editor has focus if we're in text-editor mode.
        if event.type() == QEvent.Type.WindowActivate and not self.view_mode:
            self._editor.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    # ----------------------------------------------------------------- recent

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        recent = self.settings["recent_files"]
        if not recent:
            empty = QAction("(no recent files)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
        else:
            for path in recent:
                act = QAction(os.path.basename(path), self)
                act.setToolTip(path)
                act.triggered.connect(lambda _checked, p=path: self._open_recent(p))
                self._recent_menu.addAction(act)

    def _open_recent(self, path: str):
        if not os.path.isfile(path):
            QMessageBox.warning(self, "File not found", f"File not found:\n{path}")
            recent = self.settings["recent_files"]
            if path in recent:
                recent.remove(path)
            self._rebuild_recent_menu()
            return
        if self._confirm_discard():
            self._load_file(path)

    # ------------------------------------------------------------------ about

    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<b>{APP_NAME}</b> &nbsp; v{__version__}<br><br>"
            "A lightweight Markdown viewer and editor with collapsible lists.<br><br>"
            "Built with <b>PyQt6</b> and <b>mistune 3</b>.",
        )

    # ------------------------------------------------------------------ close

    def closeEvent(self, event):
        if self._confirm_discard():
            self._save_geometry()
            self.settings.save()
            event.accept()
        else:
            event.ignore()
