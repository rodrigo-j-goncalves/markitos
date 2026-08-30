import re
import html as _html
import mistune
from mistune.renderers.html import HTMLRenderer


# ---------------------------------------------------------------------------
# LaTeX / math protection
# ---------------------------------------------------------------------------

def _protect_math(text: str):
    """Replace $$...$$ and $...$ with opaque placeholders before markdown parsing.

    This prevents mistune from interpreting underscores, asterisks, or angle
    brackets that appear inside LaTeX expressions as Markdown constructs.
    Returns (modified_text, {placeholder: original}) mapping.
    """
    placeholders: dict[str, str] = {}
    counter = [0]

    def _repl(m: re.Match) -> str:
        key = f"MARKITOSMATH{counter[0]}X"
        counter[0] += 1
        placeholders[key] = m.group(0)
        return key

    # Display math first (can span multiple lines)
    text = re.sub(r'\$\$[\s\S]+?\$\$', _repl, text)
    # Inline math (single line, non-empty)
    text = re.sub(r'\$[^$\n]+?\$', _repl, text)
    return text, placeholders


def _restore_math(html: str, placeholders: dict) -> str:
    for key, value in placeholders.items():
        html = html.replace(key, value)
    return html


# ---------------------------------------------------------------------------
# YAML front matter
# ---------------------------------------------------------------------------

_FRONT_MATTER_RE = re.compile(r'\A---[ \t]*\n(.*?)\n---[ \t]*\n', re.DOTALL)


def _extract_front_matter(text: str):
    """Return (yaml_str, body) if front matter is present, else (None, text)."""
    m = _FRONT_MATTER_RE.match(text)
    if m:
        return m.group(1), text[m.end():]
    return None, text


def _render_front_matter_html(yaml_str: str) -> str:
    """Render YAML front matter as a styled metadata block."""
    rows = []
    for line in yaml_str.splitlines():
        if ': ' in line:
            key, _, val = line.partition(': ')
            rows.append(
                f'<tr>'
                f'<td class="fm-key">{_html.escape(key.strip())}</td>'
                f'<td class="fm-val">{_html.escape(val.strip())}</td>'
                f'</tr>'
            )
        elif line.strip():
            rows.append(
                f'<tr><td colspan="2" class="fm-val">{_html.escape(line.strip())}</td></tr>'
            )
    table = f'<table class="fm-table">{"".join(rows)}</table>' if rows else ''
    return f'<div class="frontmatter">{table}</div>\n'


# KaTeX CDN snippets injected into the <head> of every rendered page.
# Requires internet access; math falls back gracefully to raw $...$ when offline.
_KATEX_HEAD = (
    '<link rel="stylesheet" '
    'href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" '
    'crossorigin="anonymous">\n'
    '<script defer '
    'src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" '
    'crossorigin="anonymous"></script>\n'
    '<script defer '
    'src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" '
    r"""onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false})" """
    'crossorigin="anonymous"></script>\n'
)


class CollapsibleRenderer(HTMLRenderer):
    """HTMLRenderer that wraps list items containing children in <details>/<summary>."""

    def list_item(self, text, **attrs):
        stripped = text.strip()
        match = re.search(r"^(.*?)(<(?:ul|ol)[\s\S]*)", stripped, re.DOTALL)
        if match:
            item_content = match.group(1).strip()
            nested = match.group(2).strip()
            item_content = re.sub(
                r"^\s*<p>(.*?)</p>\s*$", r"\1", item_content, flags=re.DOTALL
            ).strip()
            return (
                f'<li><details>'
                f'<summary class="cl-toggle">{item_content}</summary>'
                f"\n{nested}\n</details></li>\n"
            )
        # Leaf item: strip the <p> wrapper that mistune adds for "loose" lists
        # so the ::before bullet stays on the same line as the text.
        clean = re.sub(r"^\s*<p>(.*?)</p>", r"\1", stripped,
                       count=1, flags=re.DOTALL).strip()
        return f"<li>{clean}</li>\n"


def _wrap_header_sections(body: str) -> str:
    """Wrap H2–H6 headings and their content in nested <details>/<summary> blocks.

    H1 is left as a plain heading (document title).
    Each heading owns all content until the next heading of equal or higher rank,
    producing a proper hierarchy: H3 nested inside H2, H4 inside H3, etc.
    """
    parts = re.split(r'(<h[2-6][^>]*>.*?</h[2-6]>)', body, flags=re.DOTALL)

    # Stack entries: [level, cls, heading_inner_html, content_parts_list]
    stack = []
    result = []

    def _flush_top():
        level, cls, heading, content = stack.pop()
        closed = (
            f'<details class="{cls}-section">'
            f'<summary class="{cls}-toggle header-toggle">{heading}</summary>'
            f'{"".join(content)}'
            f'</details>\n'
        )
        if stack:
            stack[-1][3].append(closed)
        else:
            result.append(closed)

    for part in parts:
        m = re.match(r'<h([2-6])[^>]*>(.*?)</h[2-6]>', part, re.DOTALL)
        if m:
            level = int(m.group(1))
            heading_html = m.group(2)
            cls = f"h{level}"
            # Close all open sections of same or deeper level
            while stack and stack[-1][0] >= level:
                _flush_top()
            stack.append([level, cls, heading_html, []])
        else:
            if stack:
                stack[-1][3].append(part)
            else:
                result.append(part)

    while stack:
        _flush_top()

    return "".join(result)


def _build_css(settings) -> str:
    # MD view may use its own font family / size; fall back to editor values.
    ff = settings.get("md_font_family") or settings["font_family"]
    fs = settings.get("md_font_size") or settings["font_size"]
    tc = settings["text_color"]
    bc = settings["bg_color"]
    hc = settings["heading_color"]
    ls = settings.get("line_spacing", "1.65")
    ps = settings.get("para_spacing", "0.6em")
    mw = settings.get("md_max_width", "50%")
    return f"""
body {{
    font-family: '{ff}', sans-serif;
    font-size: {fs}pt;
    color: {tc};
    background-color: {bc};
    max-width: {mw};
    margin: 24px auto;
    padding: 0 24px 80px 24px;
    line-height: {ls};
}}
p {{
    margin: {ps} 0;
}}
h1 {{
    color: {hc};
    font-size: 2em;
    line-height: 1.3;
    margin-top: 1.4em;
    margin-bottom: .4em;
    border-bottom: 1px solid rgba(128,128,128,0.25);
    padding-bottom: .3em;
}}
/* H2–H6 are rendered as summary.hN-toggle inside <details> */
summary.header-toggle {{
    cursor: pointer;
    list-style: none;
    display: block;
    user-select: none;
    outline: none;
    font-weight: bold;
    color: {hc};
    line-height: 1.3;
}}
summary.header-toggle::-webkit-details-marker {{ display: none; }}
summary.header-toggle::before {{
    content: '▶ ';
    font-size: 0.65em;
    color: {hc};
    display: inline-block;
    width: 1.1em;
    vertical-align: middle;
    opacity: 0.7;
}}
details[open] > summary.header-toggle::before {{ content: '▼ '; }}
summary.h2-toggle {{
    font-size: 1.5em;
    margin-top: 1.4em;
    margin-bottom: .4em;
}}
summary.h3-toggle {{
    font-size: 1.25em;
    margin-top: 1.2em;
    margin-bottom: .3em;
}}
summary.h4-toggle {{
    font-size: 1.1em;
    margin-top: 1em;
    margin-bottom: .25em;
}}
summary.h5-toggle {{
    font-size: 1em;
    margin-top: .9em;
    margin-bottom: .2em;
}}
summary.h6-toggle {{
    font-size: .9em;
    margin-top: .8em;
    margin-bottom: .2em;
    opacity: 0.85;
}}
ul, ol {{
    padding-left: 1.4em;
    margin: .3em 0;
    list-style: none;
}}
ol {{
    counter-reset: li;
}}
ol > li {{
    counter-increment: li;
}}
li > ul, li > ol,
details > ul, details > ol {{
    margin-left: .3em;
    padding-left: 1.1em;
}}
li {{
    margin: 3px 0;
}}
li.leaf-item {{
    padding-left: 1.2em;
}}
li.leaf-item::before {{
    content: '• ';
    color: {hc};
    font-weight: bold;
    display: inline-block;
    width: 1.2em;
    margin-left: -1.2em;
}}
ol > li.leaf-item {{
    padding-left: 2em;
}}
ol > li.leaf-item::before {{
    content: counter(li) '. ';
    display: inline-block;
    width: 2em;
    margin-left: -2em;
}}
/* Safety net: if a loose-list <p> slips through, keep it inline */
li > p {{ display: inline; margin: 0; padding: 0; }}
details {{
    display: block;
}}
details[class$="-section"] details[class$="-section"] {{
    padding-left: 1.2em;
}}
summary.cl-toggle {{
    cursor: pointer;
    display: block;
    list-style: none;
    user-select: none;
    outline: none;
    padding-left: 1.4em;
}}
summary.cl-toggle::-webkit-details-marker {{ display: none; }}
summary.cl-toggle::before {{
    content: '▶ ';
    color: {hc};
    display: inline-block;
    width: 1.4em;
    margin-left: -1.4em;
    vertical-align: middle;
}}
details[open] > summary.cl-toggle::before {{ content: '▼ '; }}
ol > li > details > summary.cl-toggle {{
    padding-left: 2.8em;
}}
ol > li > details > summary.cl-toggle::before {{
    content: counter(li) ' ▶ ';
    width: 2.8em;
    margin-left: -2.8em;
}}
ol > li > details[open] > summary.cl-toggle::before {{ content: counter(li) ' ▼ '; }}
code {{
    font-family: 'Fira Code', 'Cascadia Code', 'Courier New', monospace;
    background: rgba(128,128,128,0.12);
    padding: 2px 5px;
    border-radius: 3px;
    font-size: .88em;
}}
p code, li code, blockquote code, td code, th code {{ cursor: pointer; }}
code.code-copied {{ background: rgba(80,160,80,0.35) !important; }}
pre {{
    background: rgba(128,128,128,0.08);
    border: 1px solid rgba(128,128,128,0.2);
    padding: 14px;
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.0;
}}
pre code {{ background: none; padding: 0; font-size: .85em; line-height: 1.0; }}
blockquote {{
    border-left: 3px solid {hc};
    margin: .5em 0 .5em .5em;
    padding: .2em 0 .2em 1em;
    color: {tc};
}}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid rgba(128,128,128,0.3); padding: 6px 12px; text-align: left; }}
th {{ background: rgba(128,128,128,0.08); color: {hc}; font-weight: 600; }}
tr:nth-child(even) td {{ background: rgba(128,128,128,0.04); }}
hr {{ border: none; border-top: 1px solid {tc}; margin: 1.5em 0; }}
a {{ color: {hc}; text-decoration: underline; }}
del {{ text-decoration: line-through; opacity: .65; }}
sup {{ font-size: .75em; vertical-align: super; }}
sub {{ font-size: .75em; vertical-align: sub; }}
.nav-focus {{
    outline: 2px solid rgba(128,128,128,0.35);
    border-radius: 3px;
    background: rgba(128,128,128,0.07);
}}
.frontmatter {{
    border: 1px solid rgba(128,128,128,0.3);
    border-radius: 6px;
    background: rgba(128,128,128,0.06);
    padding: 10px 14px;
    margin-bottom: 1.5em;
    font-size: 0.85em;
}}
.fm-table {{ border-collapse: collapse; width: 100%; margin: 0; }}
.fm-table td {{ border: none; padding: 2px 8px 2px 0; background: transparent; }}
.fm-key {{ color: {hc}; font-weight: 600; white-space: nowrap; width: 1%; }}
.fm-val {{ color: {tc}; }}
"""


_JS = r"""
(function() {
    function markLeaves() {
        document.querySelectorAll('li').forEach(function(li) {
            if (!li.querySelector(':scope > details')) {
                li.classList.add('leaf-item');
            }
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', markLeaves);
    } else {
        markLeaves();
    }
})();

function collapseAll() {
    document.querySelectorAll('details').forEach(function(d) {
        d.removeAttribute('open');
    });
}

function expandAll() {
    document.querySelectorAll('details').forEach(function(d) {
        d.setAttribute('open', '');
    });
}

// ---- Keyboard navigation in MD view ----
(function() {
    var navIndex = -1;

    function visibleNavItems() {
        // Collect all candidate elements that are currently visible (not inside a closed <details>)
        return Array.from(document.querySelectorAll(
            'p, h1, summary.header-toggle, summary.cl-toggle, li.leaf-item, pre, blockquote'
        )).filter(function(el) {
            // A <summary> is always visible inside its own <details> (open or closed);
            // start the ancestor check from the grandparent so a collapsed parent
            // does not hide its own summary toggle.
            var node = (el.tagName === 'SUMMARY')
                ? (el.parentElement ? el.parentElement.parentElement : null)
                : el.parentElement;
            while (node) {
                if (node.tagName === 'DETAILS' && !node.hasAttribute('open')) return false;
                node = node.parentElement;
            }
            return true;
        });
    }

    function clearFocus(items) {
        items.forEach(function(el) { el.classList.remove('nav-focus'); });
    }

    function applyFocus(items, idx) {
        if (idx < 0 || idx >= items.length) return;
        items[idx].classList.add('nav-focus');
        items[idx].scrollIntoView({ block: 'nearest', behavior: 'instant' });
    }

    // Called from Python after a ratio-based scroll (non-heading position) so
    // that navIndex is seeded to the item nearest the viewport centre.
    // Does NOT call scrollIntoView — the page is already at the right place.
    window.__mdNavInitByScroll = function() {
        var items = visibleNavItems();
        clearFocus(items);
        navIndex = -1;
        var mid = window.innerHeight / 2;
        var bestDist = Infinity;
        for (var i = 0; i < items.length; i++) {
            var dist = Math.abs(items[i].getBoundingClientRect().top - mid);
            if (dist < bestDist) { bestDist = dist; navIndex = i; }
        }
        if (navIndex >= 0) { items[navIndex].classList.add('nav-focus'); }
    };

    // Called from Python after mode switch to pre-select the correct item so
    // that the first Down/Up keypress continues from the right place.
    window.__mdNavInit = function(headingText) {
        var items = visibleNavItems();
        for (var i = 0; i < items.length; i++) {
            if (items[i].textContent.trim() === headingText) {
                clearFocus(items);
                navIndex = i;
                items[i].classList.add('nav-focus');
                items[i].scrollIntoView({ block: 'start', behavior: 'instant' });
                return;
            }
        }
    };

    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'ArrowDown') {
            e.preventDefault();
            var lh = parseFloat(window.getComputedStyle(document.body).lineHeight) || 24;
            window.scrollBy(0, lh);
            return;
        }
        if (e.ctrlKey && e.key === 'ArrowUp') {
            e.preventDefault();
            var lh = parseFloat(window.getComputedStyle(document.body).lineHeight) || 24;
            window.scrollBy(0, -lh);
            return;
        }

        var items = visibleNavItems();
        if (!items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            clearFocus(items);
            navIndex = Math.min(navIndex + 1, items.length - 1);
            applyFocus(items, navIndex);

        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            clearFocus(items);
            navIndex = navIndex < 0 ? items.length - 1 : Math.max(navIndex - 1, 0);
            applyFocus(items, navIndex);

        } else if (e.key === 'ArrowRight') {
            if (navIndex < 0 || navIndex >= items.length) return;
            var el = items[navIndex];
            if (el.tagName === 'SUMMARY') {
                var det = el.parentElement;
                if (det && det.tagName === 'DETAILS' && !det.hasAttribute('open')) {
                    e.preventDefault();
                    det.setAttribute('open', '');
                    // Re-focus same logical item after DOM update
                    var newItems = visibleNavItems();
                    var newIdx = newItems.indexOf(el);
                    clearFocus(newItems);
                    navIndex = newIdx >= 0 ? newIdx : navIndex;
                    applyFocus(newItems, navIndex);
                }
            }

        } else if (e.key === 'ArrowLeft') {
            if (navIndex < 0 || navIndex >= items.length) return;
            var el = items[navIndex];
            if (el.tagName === 'SUMMARY') {
                var det = el.parentElement;
                if (det && det.tagName === 'DETAILS' && det.hasAttribute('open')) {
                    e.preventDefault();
                    det.removeAttribute('open');
                    var newItems = visibleNavItems();
                    var newIdx = newItems.indexOf(el);
                    clearFocus(newItems);
                    navIndex = newIdx >= 0 ? newIdx : Math.min(navIndex, newItems.length - 1);
                    applyFocus(newItems, navIndex);
                }
            }
        }
    });

    // When the user clicks a nav item (e.g. a summary heading), sync navIndex
    // so the next arrow key continues from that position instead of index 0.
    document.addEventListener('click', function(e) {
        var found = null;
        var node = e.target;
        while (node && node !== document.body) {
            if (visibleNavItems().indexOf(node) >= 0) {
                found = node;
                break;
            }
            node = node.parentElement;
        }
        if (!found) return;
        var captured = found;
        // Use setTimeout so the DOM has settled after <details> open/close
        setTimeout(function() {
            var newItems = visibleNavItems();
            var newIdx = newItems.indexOf(captured);
            if (newIdx < 0) return;
            clearFocus(newItems);
            navIndex = newIdx;
            applyFocus(newItems, navIndex);
        }, 0);
    });
})();

// Click-to-copy for inline code spans
document.addEventListener('click', function(e) {
    var t = e.target;
    if (t.tagName !== 'CODE' || (t.parentElement && t.parentElement.tagName === 'PRE')) return;
    var ta = document.createElement('textarea');
    ta.value = t.textContent;
    ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0;';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try { document.execCommand('copy'); } catch(err) {}
    document.body.removeChild(ta);
    t.classList.add('code-copied');
    setTimeout(function() { t.classList.remove('code-copied'); }, 600);
});
"""


def render_markdown(text: str, settings) -> str:
    # Handle YAML front matter before any other processing
    fm_html = ""
    yaml_str, text = _extract_front_matter(text)
    if yaml_str is not None and settings.get("frontmatter_mode", "hide") == "show":
        fm_html = _render_front_matter_html(yaml_str)

    # Protect $...$ / $$...$$ before Markdown parsing so mistune never sees
    # underscores, asterisks, or angle brackets inside LaTeX expressions.
    protected, placeholders = _protect_math(text)

    renderer = CollapsibleRenderer()
    md = mistune.create_markdown(
        renderer=renderer,
        plugins=["strikethrough", "table", "footnotes", "task_lists"],
    )
    body = md(protected) if protected.strip() else "<p><em>(empty document)</em></p>"
    body = _restore_math(body, placeholders)
    body = _wrap_header_sections(body)
    css = _build_css(settings)
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        f"<style>{css}</style>\n"
        f"{_KATEX_HEAD}"
        "</head>\n<body>\n"
        f"{fm_html}"
        f"{body}\n"
        f"<script>{_JS}</script>\n"
        "</body>\n</html>"
    )
