from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
    QColorDialog,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
    QFrame,
    QLineEdit,
    QKeySequenceEdit,
    QCheckBox,
)
from PyQt6.QtGui import QFontDatabase, QColor, QKeySequence
from PyQt6.QtCore import pyqtSignal, Qt


class ColorButton(QPushButton):
    """Button that displays and lets the user pick a color."""

    color_changed = pyqtSignal(str)

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self._update_style()
        self.clicked.connect(self._pick_color)
        self.setFixedWidth(90)

    def color(self) -> str:
        return self._color

    def set_color(self, color: str):
        self._color = color
        self._update_style()

    def _update_style(self):
        c = QColor(self._color)
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        fg = "#000000" if lum > 128 else "#ffffff"
        self.setStyleSheet(
            f"background-color:{self._color}; color:{fg}; border:1px solid #888; padding:2px;"
        )
        self.setText(self._color)

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._color), self, "Pick Color")
        if col.isValid():
            self._color = col.name()
            self._update_style()
            self.color_changed.emit(self._color)


class AppearanceDialog(QDialog):
    """Appearance and keyboard shortcut settings dialog with live preview."""

    settings_changed = pyqtSignal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Appearance & Shortcuts")
        self.setMinimumWidth(440)
        self._build_ui()
        self._load_values()
        self._connect_live_signals()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Appearance group
        app_grp = QGroupBox("Appearance")
        form = QFormLayout(app_grp)

        self.font_combo = QComboBox()
        self.font_combo.setMaxVisibleItems(20)
        for family in sorted(QFontDatabase.families()):
            self.font_combo.addItem(family)
        form.addRow("Font family:", self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setSuffix(" pt")
        form.addRow("Font size:", self.font_size_spin)

        row = QHBoxLayout()
        self.text_color_btn = ColorButton("#000000")
        row.addWidget(self.text_color_btn)
        row.addStretch()
        form.addRow("Text color:", row)

        row2 = QHBoxLayout()
        self.bg_color_btn = ColorButton("#ffffff")
        row2.addWidget(self.bg_color_btn)
        row2.addStretch()
        form.addRow("Background color:", row2)

        row3 = QHBoxLayout()
        self.heading_color_btn = ColorButton("#2c5282")
        row3.addWidget(self.heading_color_btn)
        row3.addStretch()
        form.addRow("Heading color:", row3)

        self.line_spacing_edit = QLineEdit()
        self.line_spacing_edit.setPlaceholderText("e.g. 1.65, 2, 2em, 28px")
        self.line_spacing_edit.setToolTip("CSS line-height value for the Markdown view")
        self.line_spacing_edit.setMaximumWidth(130)
        form.addRow("Line spacing (Markdown view):", self.line_spacing_edit)

        self.para_spacing_edit = QLineEdit()
        self.para_spacing_edit.setPlaceholderText("e.g. 0.6em, 1em, 12px")
        self.para_spacing_edit.setToolTip("CSS margin between paragraphs in the Markdown view")
        self.para_spacing_edit.setMaximumWidth(130)
        form.addRow("Paragraph spacing (Markdown view):", self.para_spacing_edit)

        self.md_width_edit = QLineEdit()
        self.md_width_edit.setPlaceholderText("e.g. 67%, 80%, 860px")
        self.md_width_edit.setToolTip("CSS max-width of the text column in the Markdown view")
        self.md_width_edit.setMaximumWidth(130)
        form.addRow("Text width (Markdown view):", self.md_width_edit)

        self.line_numbers_chk = QCheckBox("Show line numbers (text editor)")
        form.addRow("", self.line_numbers_chk)

        layout.addWidget(app_grp)

        # Indent Guides group
        guide_grp = QGroupBox("Indent Guides (text editor)")
        guide_form = QFormLayout(guide_grp)

        row_gc = QHBoxLayout()
        self.guide_color_btn = ColorButton("#000000")
        row_gc.addWidget(self.guide_color_btn)
        row_gc.addStretch()
        guide_form.addRow("Line color:", row_gc)

        self.guide_opacity_spin = QSpinBox()
        self.guide_opacity_spin.setRange(5, 100)
        self.guide_opacity_spin.setSuffix(" %")
        guide_form.addRow("Opacity:", self.guide_opacity_spin)

        self.guide_width_spin = QSpinBox()
        self.guide_width_spin.setRange(1, 8)
        self.guide_width_spin.setSuffix(" px")
        guide_form.addRow("Line width:", self.guide_width_spin)

        self.symbol_opacity_spin = QSpinBox()
        self.symbol_opacity_spin.setRange(5, 100)
        self.symbol_opacity_spin.setSuffix(" %")
        self.symbol_opacity_spin.setToolTip(
            "Opacity of space · tab → and ¶ markers in text editor"
        )
        guide_form.addRow("Symbol opacity:", self.symbol_opacity_spin)

        layout.addWidget(guide_grp)

        # Shortcuts group
        sc_grp = QGroupBox("Keyboard Shortcuts")
        sc_form = QFormLayout(sc_grp)

        self.toggle_sc = QKeySequenceEdit()
        sc_form.addRow("Toggle Edit/Preview:", self.toggle_sc)

        self.collapse_sc = QKeySequenceEdit()
        sc_form.addRow("Collapse all:", self.collapse_sc)

        self.expand_sc = QKeySequenceEdit()
        sc_form.addRow("Expand all:", self.expand_sc)

        layout.addWidget(sc_grp)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_values(self):
        s = self.settings
        idx = self.font_combo.findText(s["font_family"])
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        self.font_size_spin.setValue(s["font_size"])
        self.text_color_btn.set_color(s["text_color"])
        self.bg_color_btn.set_color(s["bg_color"])
        self.heading_color_btn.set_color(s["heading_color"])
        gc = s["guide_color"] or s["text_color"]
        self.guide_color_btn.set_color(gc)
        self.guide_opacity_spin.setValue(int(s["guide_opacity"] * 100))
        self.guide_width_spin.setValue(s["guide_width"])
        self.symbol_opacity_spin.setValue(int(s["symbol_opacity"] * 100))
        self.line_spacing_edit.setText(str(s.get("line_spacing", "1.65")))
        self.para_spacing_edit.setText(str(s.get("para_spacing", "0.6em")))
        self.md_width_edit.setText(str(s.get("md_max_width", "67%")))
        self.line_numbers_chk.setChecked(bool(s.get("show_line_numbers", False)))
        self.toggle_sc.setKeySequence(QKeySequence(s.get("toggle_mode_shortcut", "Ctrl+Shift+Return")))
        self.collapse_sc.setKeySequence(QKeySequence(s["collapse_all_shortcut"]))
        self.expand_sc.setKeySequence(QKeySequence(s["expand_all_shortcut"]))

    def _connect_live_signals(self):
        self.line_spacing_edit.textChanged.connect(self._on_live_change)
        self.para_spacing_edit.textChanged.connect(self._on_live_change)
        self.md_width_edit.textChanged.connect(self._on_live_change)
        self.line_numbers_chk.toggled.connect(self._on_live_change)
        self.font_combo.currentTextChanged.connect(self._on_live_change)
        self.font_size_spin.valueChanged.connect(self._on_live_change)
        self.text_color_btn.color_changed.connect(self._on_live_change)
        self.bg_color_btn.color_changed.connect(self._on_live_change)
        self.heading_color_btn.color_changed.connect(self._on_live_change)
        self.guide_color_btn.color_changed.connect(self._on_live_change)
        self.guide_opacity_spin.valueChanged.connect(self._on_live_change)
        self.guide_width_spin.valueChanged.connect(self._on_live_change)
        self.symbol_opacity_spin.valueChanged.connect(self._on_live_change)

    def _on_live_change(self):
        self._write_to_settings()
        self.settings_changed.emit()

    def _write_to_settings(self):
        val = self.line_spacing_edit.text().strip()
        if val:
            self.settings["line_spacing"] = val
        ps = self.para_spacing_edit.text().strip()
        if ps:
            self.settings["para_spacing"] = ps
        mw = self.md_width_edit.text().strip()
        if mw:
            self.settings["md_max_width"] = mw
        self.settings["show_line_numbers"] = self.line_numbers_chk.isChecked()
        self.settings["font_family"] = self.font_combo.currentText()
        self.settings["font_size"] = self.font_size_spin.value()
        self.settings["text_color"] = self.text_color_btn.color()
        self.settings["bg_color"] = self.bg_color_btn.color()
        self.settings["heading_color"] = self.heading_color_btn.color()
        self.settings["guide_color"] = self.guide_color_btn.color()
        self.settings["guide_opacity"] = self.guide_opacity_spin.value() / 100
        self.settings["guide_width"] = self.guide_width_spin.value()
        self.settings["symbol_opacity"] = self.symbol_opacity_spin.value() / 100
        ks_toggle = self.toggle_sc.keySequence()
        if not ks_toggle.isEmpty():
            self.settings["toggle_mode_shortcut"] = ks_toggle.toString()
        ks_collapse = self.collapse_sc.keySequence()
        if not ks_collapse.isEmpty():
            self.settings["collapse_all_shortcut"] = ks_collapse.toString()
        ks_expand = self.expand_sc.keySequence()
        if not ks_expand.isEmpty():
            self.settings["expand_all_shortcut"] = ks_expand.toString()

    def apply_final(self):
        """Persist all values including shortcuts before accepting."""
        self._write_to_settings()


class FindBar(QFrame):
    """Collapsible find bar shown at the bottom of the window."""

    find_requested = pyqtSignal(str, bool)  # (text, backward)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        layout.addWidget(QLabel("Find:"))

        self._input = QLineEdit()
        self._input.setPlaceholderText("Search…")
        self._input.returnPressed.connect(self._find_forward)
        layout.addWidget(self._input)

        prev_btn = QPushButton("◀")
        prev_btn.setFixedWidth(32)
        prev_btn.setToolTip("Find previous")
        prev_btn.clicked.connect(self._find_backward)
        layout.addWidget(prev_btn)

        next_btn = QPushButton("▶")
        next_btn.setFixedWidth(32)
        next_btn.setToolTip("Find next (Enter)")
        next_btn.clicked.connect(self._find_forward)
        layout.addWidget(next_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(28)
        close_btn.clicked.connect(self._close)
        layout.addWidget(close_btn)

        self.hide()

    def show_and_focus(self):
        self.show()
        self._input.setFocus()
        self._input.selectAll()

    def _find_forward(self):
        self.find_requested.emit(self._input.text(), False)

    def _find_backward(self):
        self.find_requested.emit(self._input.text(), True)

    def _close(self):
        self.hide()
        self.closed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._close()
        else:
            super().keyPressEvent(event)
