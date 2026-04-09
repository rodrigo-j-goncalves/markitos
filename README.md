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

1. Clone the repo
2. Create and activate a virtual environment (recommended)
3. Install dependencies

## Running

# Open with no file (starts in edit mode)
`python markitos.py`

# Open a specific file
`python markitos.py myfile.md`

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

