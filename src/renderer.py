import re
import mistune
from mistune.renderers.html import HTMLRenderer


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
                f'<li><details open>'
                f'<summary class="cl-toggle">{item_content}</summary>'
                f"\n{nested}\n</details></li>\n"
            )
        # Leaf item: strip the <p> wrapper that mistune adds for "loose" lists
        # so the ::before bullet stays on the same line as the text.
        clean = re.sub(r"^\s*<p>(.*?)</p>", r"\1", stripped,
                       count=1, flags=re.DOTALL).strip()
        return f"<li>{clean}</li>\n"


def _wrap_h2_sections(body: str) -> str:
    """Wrap each H2 heading and the content that follows it in <details>/<summary>."""
    # Split on <h2> tags (with possible attributes)
    parts = re.split(r'(<h2[^>]*>.*?</h2>)', body, flags=re.DOTALL)
    result = []
    i = 0
    while i < len(parts):
        part = parts[i]
        m = re.match(r'<h2[^>]*>(.*?)</h2>', part, re.DOTALL)
        if m:
            heading_html = m.group(1)
            content = parts[i + 1] if i + 1 < len(parts) else ""
            result.append(
                f'<details open class="h2-section">'
                f'<summary class="h2-toggle">{heading_html}</summary>'
                f'{content}'
                f'</details>\n'
            )
            i += 2
        else:
            result.append(part)
            i += 1
    return "".join(result)


def _build_css(settings) -> str:
    ff = settings["font_family"]
    fs = settings["font_size"]
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
h1, h3, h4, h5, h6 {{
    color: {hc};
    line-height: 1.3;
    margin-top: 1.4em;
    margin-bottom: .4em;
}}
h1 {{
    font-size: 2em;
    border-bottom: 1px solid rgba(128,128,128,0.25);
    padding-bottom: .3em;
}}
/* H2 is rendered as summary.h2-toggle — styles below */
summary.h2-toggle {{
    cursor: pointer;
    list-style: none;
    display: block;
    user-select: none;
    outline: none;
    font-size: 1.5em;
    font-weight: bold;
    color: {hc};
    border-bottom: 1px solid rgba(128,128,128,0.15);
    padding-bottom: .2em;
    margin-top: 1.4em;
    margin-bottom: .4em;
    line-height: 1.3;
}}
summary.h2-toggle::-webkit-details-marker {{ display: none; }}
summary.h2-toggle::before {{
    content: '▶ ';
    font-size: 0.65em;
    color: {hc};
    display: inline-block;
    width: 1.1em;
    vertical-align: middle;
    opacity: 0.7;
}}
details[open] > summary.h2-toggle::before {{ content: '▼ '; }}
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
/* Indentation guide lines for nested levels */
li > ul, li > ol,
details > ul, details > ol {{
    border-left: 1px solid rgba(128,128,128,0.25);
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
pre {{
    background: rgba(128,128,128,0.08);
    border: 1px solid rgba(128,128,128,0.2);
    padding: 14px;
    border-radius: 6px;
    overflow-x: auto;
}}
pre code {{ background: none; padding: 0; font-size: .85em; }}
blockquote {{
    border-left: 3px solid {hc};
    margin: .5em 0 .5em .5em;
    padding: .2em 0 .2em 1em;
    color: rgba(0,0,0,0.55);
}}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid rgba(128,128,128,0.3); padding: 6px 12px; text-align: left; }}
th {{ background: rgba(128,128,128,0.08); color: {hc}; font-weight: 600; }}
tr:nth-child(even) td {{ background: rgba(128,128,128,0.04); }}
hr {{ border: none; border-top: 1px solid rgba(128,128,128,0.25); margin: 1.5em 0; }}
a {{ color: {hc}; text-decoration: underline; }}
del {{ text-decoration: line-through; opacity: .65; }}
sup {{ font-size: .75em; vertical-align: super; }}
sub {{ font-size: .75em; vertical-align: sub; }}
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
"""


def render_markdown(text: str, settings) -> str:
    renderer = CollapsibleRenderer()
    md = mistune.create_markdown(
        renderer=renderer,
        plugins=["strikethrough", "table", "footnotes", "task_lists"],
    )
    body = md(text) if text.strip() else "<p><em>(empty document)</em></p>"
    body = _wrap_h2_sections(body)
    css = _build_css(settings)
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        f"<style>{css}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        f"<script>{_JS}</script>\n"
        "</body>\n</html>"
    )
