# Markitos Editor &nbsp; v1.2.0

A lightweight desktop Markdown viewer and editor with **collapsible sections**, an **outline sidebar**, **website viewer**, LaTeX math rendering, and live appearance customization. 

Use it to take notes, organize your lists, and share easily to any other application. 

And it's completely free and open.


![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

---

## Features

- Pandoc/Quarto-flavoured Markdown — tables, strikethrough, footnotes, task lists, fenced code blocks
- **LaTeX math** — inline `$...$` and display `$$...$$` rendered via KaTeX (requires internet; graceful fallback when offline)
- View / Edit toggle — rendered Markdown preview or raw text editor, switch instantly; scroll position preserved when switching
- **Collapsible sections** — H2–H6 headings and bullet/numbered list items with children each get a ▶/▼ toggle; click to collapse/expand; toolbar buttons for collapse all / expand all
- **Outline sidebar** — left panel showing the heading tree (H1→H2→H3…); click any heading to jump to it in either mode; clicking a heading inside a collapsed section automatically expands it; tracks cursor position in text editor and scroll position in Markdown view; toggle via View → Sidebar; width persisted across sessions
- Ctrl+Scroll to zoom font size (6–72 pt)
- Word wrap toggle
- **Inline formatting shortcuts** — `Ctrl+B` bold, `Ctrl+I` italic on selected text (or inserts markers with cursor positioned inside)
- Settings panel
    - editor font family / size
    - Markdown view font family / size (independent; defaults to editor font)
    - text / background / heading colours
    - line-number gutter colour with live preview
    - configurable shortcuts (toggle Edit/Preview, collapse all, expand all)
- **Find** (`Ctrl+F`, works in both modes) and **Find & Replace** (`Ctrl+H`, text editor only) — Replace advances through matches one at a time; Replace All replaces every occurrence in a single undo step and reports the count in the status bar
- Line numbers (text editor), configurable background colour (or auto-derived from theme)
- Smart editing — auto-pair `[]`/`()`, smart Enter continues list markers (plain lines use default newline), auto-renumbers ordered lists on deletion, Tab/Shift+Tab indent/dedent (4 spaces), full undo/redo (Ctrl+Z / Ctrl+Y), URL-paste onto selected text creates a Markdown link
- **Image paste** (text editor) — paste an image from the clipboard and it is saved automatically as `assets/image-YYYYMMDD-HHMMSS.png` next to the open file; a `![image](assets/…)` link is inserted at the cursor
- **Keyboard navigation** (Markdown view) — `↑`/`↓` moves focus between paragraphs, headings, list items, code blocks, and blockquotes; `→` expands the focused collapsed section or list item; `←` collapses the focused open section or list item; `Tab` shifts keyboard focus to the outline sidebar (`Tab` again returns to the view)
- **Click to copy inline code** — click any `inline code` span in Markdown view to copy its text to the clipboard; the span flashes green as confirmation
- **Embedded URL viewer** — clicking any `http`/`https` link in Markdown view opens the website in a panel above the markdown area (50/50 vertical split); a URL bar lets you navigate further; close with the ✕ button; ideal for taking notes while watching a presentation or reading a page side-by-side
- **File link navigation** — write a standard Markdown link to any `.md` or `.txt` file (relative or absolute path); clicking it in Markdown view opens the file in a new Markitos window, cascaded 30 px from the current one
- Settings persisted immediately when the settings dialog is confirmed; window geometry saved on close (`settings.json` in the project folder)
- PyQt6 with `QWebEngineView` (Chromium) for full HTML5/CSS3 rendering

---

## Requirements

| Package | Version |
|---------|---------|
| Python | 3.10+ |
| PyQt6 | ≥ 6.4 |
| PyQt6-WebEngine | ≥ 6.4 |
| mistune | ≥ 3.0 |

---

## Running

```bash
# Open with no file (starts in edit mode)
python markitos.py

# Open a specific file
python markitos.py myfile.md
```

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
| `Ctrl+B` | Bold (wraps selection or inserts `**...**`) |
| `Ctrl+I` | Italic (wraps selection or inserts `*...*`) |
| `Ctrl+Shift+C` | Collapse all list items *(configurable)* |
| `Ctrl+Shift+X` | Expand all list items *(configurable)* |
| `Ctrl+F` | Find (Edit menu) |
| `Ctrl+H` | Find and Replace (text editor only) |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+A` | Select all |
| `Tab` | Toggle keyboard focus between Markdown view and outline sidebar |
| `↑` / `↓` | Move focus to previous/next element *(Markdown view / outline only)* |
| `→` | Expand focused collapsed section or list item *(Markdown view / outline only)* |
| `←` | Collapse focused open section or list item *(Markdown view / outline only)* |

Configurable shortcuts can be changed in **View → Settings → Keyboard Shortcuts**.

> **Sidebar** has no default keyboard shortcut; toggle it from **View → Sidebar**.

---

## Toolbar

```
Open | Save | ─ | Text | ─ | ⊟ Collapse all | ⊞ Expand all | ─ | Word Wrap |  …space…  | Settings
```

- **Text/Markdown button** — toggles between text editor and rendered view
- **Word Wrap** — checkable toggle; stays in sync with View → Word Wrap menu item
- **Settings** — pushed to the far right by an expanding spacer

---

## Settings panel

All appearance options live in **View → Settings** (or the toolbar Settings button).

| Setting | Description |
|---------|-------------|
| Editor font family / size | Font used in the text editor |
| Markdown font family / size | Font used in the rendered view ("same as editor" to inherit) |
| Text / Background / Heading colour | Palette for both edit and rendered view |
| Line spacing (Markdown view) | CSS `line-height` value (e.g. `1.65`, `2`, `2em`) |
| Paragraph spacing (Markdown view) | CSS margin between paragraphs (e.g. `0.6em`, `1em`, `12px`) |
| Text width (Markdown view) | CSS `max-width` of the text column (e.g. `67%`, `860px`) |
| Word wrap | Toggle line wrapping in the text editor |
| Show line numbers | Toggle gutter with line numbers in text editor |
| Line number background | Custom gutter colour, or "Auto" to derive from text/background blend |
| Symbol opacity | Opacity of `·` `→` `¶` markers in text editor (0–100 %) |
| Indent guide colour / opacity / width | Style of the vertical indent guide lines |

---

## LaTeX math

Uses [KaTeX](https://katex.org/) loaded from CDN. Works whenever the machine is online; when offline, `$...$` and `$$...$$` are shown as plain text without errors.

Examples:

This MD code:

```
Inline: The viscosity ranges from $0.7 \text{ to } 2.0 \text{ mPa}\cdot\text{s}$.

Display:
$$
E = mc^2
$$
```
is redered as:

Inline: The viscosity ranges from $0.7 \text{to} 2.0 \text{mPa}\cdot\text{s}$.

Display:

$$
E = mc^2
$$



Math expressions are protected from Markdown parsing before rendering, so underscores and asterisks inside `$...$` are treated as LaTeX, not Markdown emphasis.

---
