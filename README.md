# Markitos Editor &nbsp; v1.2.0

A lightweight desktop Markdown **viewer and editor** with **website viewer**, **collapsible sections**, an **outline sidebar**, LaTeX math rendering, and live appearance customization. 

Use it to take notes, organize your lists, and share easily to any other application. 

And it's completely free and open.


![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

---

## Features

- **Embedded URL viewer** — click any `http`/`https` link in Markdown view and the website opens in a panel above your notes (50/50 vertical split); a URL bar lets you navigate further; ✕ closes the panel — watch a lecture or read a reference on top while writing below
- **View / Edit toggle** — switch instantly between a clean reading view and the raw text editor; scroll position is preserved when switching
- **Collapsible sections** — H2–H6 headings and list items with children each get a ▶/▼ toggle; toolbar buttons collapse or expand everything at once
- **Outline sidebar** — heading tree always visible on the left; click any heading to jump to it; tracks your position as you scroll or type
- **LaTeX math** — inline `$...$` and display `$$...$$` rendered via KaTeX; works online, graceful fallback when offline
- **File link navigation** — link to any `.md` or `.txt` file with a standard Markdown link; clicking it in reading view opens the file in a new window — connect your notes like Obsidian
- **Image paste** — paste a screenshot from the clipboard and it is saved automatically next to your file; a `![image](…)` link is inserted at the cursor
- **Click to copy inline code** — click any `inline code` span in reading view to copy it; the span flashes green as confirmation
- **Find** (`Ctrl+F`) and **Find & Replace** (`Ctrl+H`) — search in both modes; Replace All rewrites every match in one undo step
- **Keyboard navigation** (reading view) — `↑`/`↓` moves between elements; `→`/`←` expands/collapses sections; `Tab` moves focus to the outline and back
- **Inline formatting shortcuts** — `Ctrl+B` bold, `Ctrl+I` italic on selection or with cursor inside markers
- **Smart editing** — auto-pairs `[]`/`()`, smart Enter continues list markers, auto-renumbers ordered lists, Tab/Shift+Tab indent/dedent (4 spaces), URL-paste onto selected text creates a Markdown link, full undo/redo
- Pandoc/Quarto-flavoured Markdown — tables, strikethrough, footnotes, task lists, fenced code blocks
- Ctrl+Scroll to zoom font size (6–72 pt); word wrap toggle
- Settings panel — font, colours, line spacing, paragraph spacing, text width, line numbers, indent guides, configurable shortcuts; all settings persisted across sessions

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
