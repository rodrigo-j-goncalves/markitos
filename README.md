# Markitos Editor &nbsp; v1.0.3

A lightweight desktop Markdown viewer and editor with **collapsible bullet lists**, live appearance customization, and persistent settings. Built with Python and PyQt6.


![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

---

## Features

- **View / Edit toggle** — rendered Markdown preview or raw text editor, switch instantly
- **Collapsible lists** — any bullet or numbered item with children gets a ▶/▼ toggle; click to collapse/expand; toolbar buttons for collapse all / expand all
- **Pandoc-flavoured Markdown** — tables, strikethrough, footnotes, task lists, fenced code blocks
- **Ctrl+Scroll** to zoom font size (8–48 pt), persisted between sessions
- **Appearance panel** — font family, font size, text/background/heading colours with live preview
- **Configurable shortcuts** — toggle Edit/Preview, collapse all, expand all (set in Appearance)
- **File handling** — Open, Save, Save As, Recent Files (last 10), drag-and-drop, unsaved-changes prompt
- **Find bar** — Ctrl+F, works in both view and edit mode
- **Line numbers** (text editor) — gutter with distinct background; current line highlighted in bold; toggle in Appearance
- **Non-printing characters** (text editor) — space `·`, tab `→`, and paragraph `¶` markers shown at configurable opacity
- **Indent guide lines** (text editor) — faint vertical lines visualise indentation depth; colour, opacity, and width configurable
- **Smart editing** — auto-pair `[]`/`()`, smart Enter continues list markers, auto-renumbers ordered lists on deletion, Tab/Shift+Tab indent/dedent, full undo/redo (Ctrl+Z / Ctrl+Y), URL-paste onto selected text creates a Markdown link
- Settings and window geometry persisted across sessions (`~/.config/markitos/settings.json`)

---

## Requirements

| Package | Version |
|---------|---------|
| Python | 3.10+ |
| PyQt6 | ≥ 6.4 |
| PyQt6-WebEngine | ≥ 6.4 |
| mistune | ≥ 3.0 |
| platformdirs | ≥ 3.0 |

---

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd text-editor

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Running

```bash
# Open with no file (starts in edit mode)
python markitos.py

# Open a specific file
python markitos.py myfile.md
```

### Convenience script (Linux / macOS)

A `mdeditor` shell script is included that activates the bundled venv automatically:

```bash
./mdeditor myfile.md
```

Edit the `source` line inside `mdeditor` to point to your virtual environment if needed.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open file |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Shift+Enter` | Toggle Edit / Preview *(configurable; works on main keyboard and numpad)* |
| `Ctrl+E` | Toggle Edit / Preview (menu) |
| `Ctrl+Scroll` | Zoom font size |
| `Ctrl+Shift+C` | Collapse all list items *(configurable)* |
| `Ctrl+Shift+X` | Expand all list items *(configurable)* |
| `Ctrl+F` | Find |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+A` | Select all |

Configurable shortcuts can be changed in **View → Appearance → Keyboard Shortcuts**.

---

## Project Structure

```
text-editor/
├── markitos.py       # Entry point
├── mdeditor          # Shell launcher script (Linux/macOS)
├── requirements.txt
└── src/
    ├── settings.py   # Persistent settings (JSON)
    ├── renderer.py   # Markdown → HTML with collapsible lists
    ├── dialogs.py    # Appearance dialog, Find bar
    └── window.py     # Main window
```

---

## Appearance settings

All appearance options live in **View → Appearance** (or the toolbar button).

| Setting | Description |
|---------|-------------|
| Font family / size | Editor font |
| Text / Background / Heading colour | Palette for both edit and rendered view |
| Line spacing (Markdown view) | CSS `line-height` value for the Markdown view (e.g. `1.65`, `2`, `2em`) |
| Paragraph spacing (Markdown view) | CSS margin between paragraphs in the Markdown view (e.g. `0.6em`, `1em`, `12px`) |
| Show line numbers | Toggle gutter with line numbers in text editor |
| Symbol opacity | Opacity of `·` `→` `¶` markers in text editor (0–100 %) |
| Indent guide colour / opacity / width | Style of the vertical indent guide lines |

---

## Developer Notes

**Framework:** PyQt6 with `QWebEngineView` for the rendered view. The WebEngine (Chromium-based) provides full HTML5/CSS3 support, which is needed for the native `<details>`/`<summary>` collapsible elements and JavaScript.

**Markdown parser:** [mistune 3](https://github.com/lepture/mistune). A custom `HTMLRenderer` subclass intercepts `list_item` rendering to wrap items that have nested children in `<details>`/`<summary>` tags.

**Collapsible lists:** Implemented via HTML5 `<details>`/`<summary>`. No custom JavaScript is needed for individual item toggling — it is native browser behaviour. JavaScript is only used for "collapse all" / "expand all" (`querySelectorAll('details')`).

**Non-printing characters:** `ShowTabsAndSpaces` and `ShowLineAndParagraphSeparators` flags on the document's `QTextOption` render the markers. `QPalette::Text` is set to the dim colour so all markers (including `¶`) appear faded; a `QSyntaxHighlighter` subclass then restores non-whitespace character runs to the full text colour.

**Indent guides:** A transparent `QWidget` overlay on the editor viewport draws vertical lines block-by-block in `paintEvent`, using `blockBoundingGeometry` for positioning.

**Line numbers:** Standard Qt "Code Editor" pattern — `_LineNumberArea` widget sets left viewport margin via `setViewportMargins`; `blockCountChanged` and `updateRequest` signals keep it in sync. Current line number is drawn bold in the full text colour; other lines use a dim colour. The gutter background is a 20 % text / 80 % background blend for a subtle visual separation. Numpad Enter support for the toggle shortcut is added by registering a second `QShortcut` for `Ctrl+Shift+Enter` alongside the configurable one.

**Auto-renumber:** `document().contentsChanged` triggers a debounced (120 ms) pass that walks all blocks, tracks the expected number per indentation level, and silently fixes any out-of-sequence ordered list item. The pass uses `QTextCursor.joinPreviousEditBlock()` so renumbering is merged into the same undo step as the triggering edit — a single Ctrl+Z undoes both the deletion and the renumber together.

**Known limitations (v1):**
- Embedded HTML inside Markdown is not rendered.
- No export to PDF or HTML.
- No spell check or multiple tabs.
