"""build-finished hook: inline coll-diagram SVGs, strip Breathe clutter."""
from __future__ import annotations
import pathlib, re, shutil

from .state import DOXYGEN_BASE_URL, _API_XML_DIR


def _inline_collaboration_svgs(api_dir: pathlib.Path,
                              image_dir: pathlib.Path) -> None:
    """Inline coll-diagram SVGs so their links work; idempotent."""
    import re
    if not api_dir.is_dir():
        return
    img_re = re.compile(
        r'<img alt="(?P<alt>[^"]*)" '
        r'class="(?P<cls>opencv-coll-graph[^"]*)" '
        r'src="\.\./_images/(?P<file>[^"]+\.svg)"\s*/?>')
    href_re = re.compile(r'xlink:href="(?P<path>[^"]+)"')

    def _rewrite_href(m: "re.Match") -> str:
        path = m.group("path")
        if "://" in path:
            return m.group(0)
        base = path.rsplit("/", 1)[-1]
        if (api_dir / base).is_file():
            return f'xlink:href="{base}"'
        rel = path.lstrip("./")
        return f'xlink:href="{DOXYGEN_BASE_URL}{rel}"'

    for html in api_dir.glob("*.html"):
        text = html.read_text(encoding="utf-8")
        if "opencv-coll-graph" not in text:
            continue

        def _inline(m: "re.Match") -> str:
            svg_path = image_dir / m.group("file")
            if not svg_path.is_file():
                return m.group(0)
            svg = svg_path.read_text(encoding="utf-8")
            start = svg.find("<svg")
            if start < 0:
                return m.group(0)
            svg = href_re.sub(_rewrite_href, svg[start:])
            # carry theme classes + alt for dark mode / a11y
            return svg.replace(
                "<svg ",
                f'<svg class="{m.group("cls")}" role="img" '
                f'aria-label="{m.group("alt")}" ', 1)

        new = img_re.sub(_inline, text)
        if new != text:
            html.write_text(new, encoding="utf-8")


def _strip_breathe_class_clutter(api_dir: pathlib.Path) -> None:
    """Drop Breathe's duplicate class signature header; idempotent."""
    import re
    if not api_dir.is_dir():
        return
    section_re = re.compile(
        r'(<section id="detailed-description"[^>]*>)'
        r'(?P<body>[\s\S]*?)'
        r'(</section>)'
    )
    dl_re = re.compile(
        r'<dl[^>]*\bclass="[^"]*\bclass\b[^"]*"[^>]*>\s*'
        r'<dt[^>]*>[\s\S]*?</dt>\s*'
        r'<dd>(?P<dd>[\s\S]*?)</dd>\s*'
        r'</dl>'
    )
    subclassed_re = re.compile(r'<p>Subclassed by[\s\S]*?</p>\s*')

    for h in api_dir.glob("classcv*.html"):
        text = h.read_text(encoding="utf-8")
        if "detailed-description" not in text:
            continue

        def _strip_section(sm):
            head, body, tail = sm.group(1), sm.group("body"), sm.group(3)

            def _strip_dl(dm):
                dd_body = dm.group("dd").strip()
                dd_body = subclassed_re.sub("", dd_body).strip()
                return dd_body

            new_body = dl_re.sub(_strip_dl, body, count=1)
            return head + new_body + tail

        new = section_re.sub(_strip_section, text, count=1)
        if new != text:
            h.write_text(new, encoding="utf-8")


def _generate_search_map(out_dir: pathlib.Path) -> None:
    """Write _static/search_map.js: stem→Sphinx-path for every built HTML page."""
    import json
    skip = {"_static", "_sources", "_images", "_sphinx_design_static"}
    mapping = {}
    for f in out_dir.rglob("*.html"):
        rel = f.relative_to(out_dir)
        if rel.parts[0] in skip:
            continue
        mapping[f.stem] = rel.as_posix()
    lines = ["var sphinxPageMap = {"]
    for k, v in sorted(mapping.items()):
        lines.append(f"  {json.dumps(k)}: {json.dumps(v)},")
    lines.append("};")
    (out_dir / "_static" / "search_map.js").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Re-theme the copied Doxygen HTML (api-docs/) to match the PyData site.
# The legacy Doxygen pages (Related Pages, Namespaces, Classes, …) are raw
# Doxygen output. We copy them under the Sphinx output's api-docs/ and rewrite
# each page: force doxygen-awesome dark, bridge its palette to PyData's, hide
# Doxygen's own chrome, relocate the (functional) search box into a PyData-style
# navbar, and add a matching footer. Source dir = sibling of the Doxygen XML.
# ---------------------------------------------------------------------------
_DOXY_MARKER = "<!-- pydata-bridge -->"
_BRIDGE_CSS = "doxygen-pydata-bridge.css"
_REPO_URL = "https://github.com/opencv/opencv"
_FONTS_LINK = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500'
    '&display=swap"/>'
)
_INTER = ('Inter,"Source Sans Pro",-apple-system,BlinkMacSystemFont,'
          '"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif')

_GITHUB_SVG = (
    '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 '
    '8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01'
    '.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63'
    '-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2'
    '-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67'
    '-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2'
    '-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 '
    '3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 '
    '8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>'
)
_MOON_SVG = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12.1 22C6.6 22 2.1 '
    '17.5 2.1 12c0-4.7 3.3-8.8 7.9-9.8-1 2.3-.9 5 .4 7.2 1.3 2.3 3.6 3.8 6.2 '
    '4.1.9.1 1.8.05 2.7-.15C18 19.3 14.2 22 12.1 22z"/></svg>'
)
_CHEVRON_LEFT_SVG = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M15.4 7.4 14 6l-6 6 6 6 1.4-1.4-4.6-4.6z"/></svg>'
)
_THEME_TOGGLE_JS = (
    '<script>(function(){var r=document.documentElement,K="opencv-doxy-theme";'
    'try{if(localStorage.getItem(K)==="light")r.classList.remove("dark-mode");}'
    'catch(e){}var b=document.getElementById("pst-doxy-theme");if(b)'
    'b.addEventListener("click",function(){var d=r.classList.toggle("dark-mode");'
    'try{localStorage.setItem(K,d?"dark":"light");}catch(e){}});})();</script>'
)
# Verbatim text + versions from tutorials/tutorials.html's .bd-footer.
_DOXY_FOOTER = (
    '<footer class="pst-doxyfoot">'
    '<p>Created using <a href="https://www.sphinx-doc.org/">Sphinx</a> 8.1.3.</p>'
    '<p>Built with the '
    '<a href="https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html">'
    'PyData Sphinx Theme</a> 0.17.1.</p>'
    '</footer>'
)


def _doxy_prevnext(sroot):
    # Mirrors .prev-next-area. Flat Doxygen pages have no toctree sequence, so
    # this is a single "back to docs home" link in that style.
    return (
        '<nav class="pst-doxy-prevnext">'
        f'<a href="{sroot}tutorials/tutorials.html">{_CHEVRON_LEFT_SVG}'
        '<span class="pn-info"><span class="pn-subtitle">back to</span>'
        '<span class="pn-title">OpenCV Tutorials</span></span></a></nav>'
    )

# Values mirror _static/custom.css (header, nav links, footer) + the PyData
# dark palette, so api-docs pages match tutorials/tutorials.html.
_BRIDGE_CSS_CONTENT = """\
/* doxygen-pydata-bridge.css - GENERATED. Do not edit. */

/* Sphinx fonts/sizing (theme-independent) */
html, html body, html #top, html .contents {
    font-family: Inter,"Source Sans Pro",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
html body { font-size: 16px; }
/* page title = .headertitle .title (NOT .contents h1) -> match Sphinx h1 */
.contents h1, div.header .title, .headertitle .title {
    font-family: Inter,"Source Sans Pro",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size: 2.25rem; font-weight: 700; line-height: 1.2; letter-spacing: -.02em;
    color: var(--page-foreground-color);
}
.contents h2 { font-size: 1.5rem; font-weight: 600; }

/* doxygen-awesome dark vars -> PyData palette + Pygments token remap */
html.dark-mode {
    --page-background-color: #14181e;
    --page-foreground-color: #ced6dd;
    --page-secondary-foreground-color: #9ca4af;
    --separator-color: #48566b;
    --side-nav-background: #222832;
    --code-background: #222832;
    --fragment-background: #222832;
    --tablehead-background: #222832;
    --primary-color: #539bf5;
    --primary-dark-color: #6cb6ff;
    --primary-light-color: #a4c9ff;
    --fragment-comment: #e3b341;
    --fragment-keyword: #f47067;
    --fragment-keywordtype: #f47067;
    --fragment-keywordflow: #f47067;
    --fragment-string: #96d0ff;
    --fragment-token: #96d0ff;
}

/* hide Doxygen's own chrome */
#titlearea, #main-nav, #nav-path, .sm.sm-dox,
#navrow1, #navrow2, #navrow3, #navrow4,
.tabs, .tabs2, .tabs3, address.footer { display: none !important; }

/* [detail level 1 2 3 ...] toggle -> themed */
div.levels {
    font-family: Inter,"Source Sans Pro",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size: .875rem; margin: .25rem 0 .5rem;
}
div.levels span { color: #539bf5 !important; cursor: pointer; padding: 0 .2rem; }
div.levels span:hover { color: #6cb6ff !important; text-decoration: underline; }

/* non-link namespace labels (e.g. external `std`) -> themed text, not broken link */
html.dark-mode table.directory td.entry b { color: #ced6dd; font-weight: 600; }

/* flatten the Related Pages list (no boxy rows) - both themes */
#doc-content, .contents, div.header { background: transparent !important; }
table.directory, table.directory tr,
table.directory tr.even, table.directory td {
    background: transparent !important; border: none !important; box-shadow: none !important;
}
/* list/prose text -> Inter, 1rem, normal weight, airy (both themes) */
.textblock, div.contents > p,
table.directory, table.directory td,
table.directory a, table.directory a.el {
    font-family: Inter,"Source Sans Pro",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif !important;
}
.textblock, div.contents > p,
table.directory td, table.directory a, table.directory a.el {
    font-size: 1rem !important; font-weight: 400 !important;
}
table.directory td.entry, .textblock { line-height: 1.6 !important; }

/* code blocks: JetBrains Mono in both themes; dark surface only in dark mode */
html.dark-mode div.fragment, html.dark-mode pre.fragment {
    background: #222832 !important; border: 1px solid #48566b !important; border-radius: .4rem;
}
.fragment, .fragment .line, pre, code, tt, .memname, .memItemLeft, .memItemRight,
.memTemplItemLeft, .memTemplItemRight, .paramtype, .paramname {
    font-family: "JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace !important;
}
html.dark-mode span.comment { color: #e3b341 !important; }
html.dark-mode span.keyword, html.dark-mode span.keywordtype, html.dark-mode span.keywordflow { color: #f47067 !important; }
html.dark-mode span.stringliteral, html.dark-mode span.charliteral { color: #96d0ff !important; }
html.dark-mode span.preprocessor { color: #6cb6ff !important; }

/* member/summary tables -> surface card, themed borders */
html.dark-mode table.memberdecls, html.dark-mode table.fieldtable,
html.dark-mode .memitem, html.dark-mode .memproto {
    background: #222832 !important; border-color: #48566b !important;
}
html.dark-mode .memSeparator { border-color: #48566b !important; }

/* navbar (mirrors .bd-header) */
.pst-doxynav {
    position: sticky; top: 0; z-index: 1050;
    display: flex; align-items: center; gap: 1rem;
    min-height: 3.25rem; padding: .25rem 1.5rem;
    background: #222832; border-bottom: 1px solid #48566b;
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    font-family: Inter,"Source Sans Pro",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
/* NOTE: doxygen-awesome forces `a {color: var(--primary-color) !important}`,
   so every navbar/footer color below needs !important to win. */
.pst-doxynav .pst-doxynav-brand { font-weight: 500; font-size: 1.4rem; color: #ced6dd !important; text-decoration: none !important; white-space: nowrap; }
.pst-doxynav .pst-doxynav-center { flex: 1 1 auto; display: flex; justify-content: center; min-width: 0; }
.pst-doxynav nav { overflow: visible; }
.pst-doxynav ul { display: flex; align-items: center; gap: .25rem; flex-wrap: wrap; margin: 0; padding: 0; list-style: none; }
.pst-doxynav a.pst-doxynav-link {
    display: block; padding: .4rem .75rem; border-radius: .35rem;
    color: #9ca4af !important; text-decoration: none !important;
    text-transform: uppercase; letter-spacing: .06em;
    font-size: .78rem; font-weight: 500; white-space: nowrap;
}
.pst-doxynav a.pst-doxynav-link:hover { color: #a4c9ff !important; background: #29313d; }
.pst-doxynav a.pst-doxynav-link[aria-current="page"] { color: #a4c9ff !important; font-weight: 600; }
.pst-doxynav .pst-doxynav-end { display: flex; align-items: center; gap: 1.12rem; flex: 0 0 auto; }
.pst-doxynav .pst-icon-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 2.15rem; height: 2.15rem; padding: 0; border: none; cursor: pointer;
    background: transparent; color: #9ca4af !important; border-radius: .35rem;
}
/* muted icon; light-purple boundary box on hover/focus (matches :focus-visible outline) */
.pst-doxynav .pst-icon-btn:hover { color: #ced6dd !important; background: #29313d; box-shadow: 0 0 0 1.5px #b388ff; }
.pst-doxynav .pst-icon-btn:focus-visible { outline: 2px solid #b388ff; outline-offset: 2px; }
.pst-doxynav .pst-icon-btn svg { width: 1.1rem; height: 1.1rem; fill: currentColor; }
/* theme toggle: purple icon in a persistent light-purple boundary box */
.pst-doxynav #pst-doxy-theme { color: #b388ff !important; box-shadow: 0 0 0 1.5px #9c5ffd; }
.pst-doxynav #pst-doxy-theme:hover { color: #c4a7ff !important; background: #29313d; box-shadow: 0 0 0 2px #b388ff; }

/* relocated search box -> match .search-button-field */
.pst-doxynav #MSearchBox {
    position: static !important; display: inline-flex !important; align-items: center;
    margin: 0 !important; padding: .4em .6em !important;
    background: #29313d !important; border: 1px solid #48566b !important;
    border-radius: 1.5em !important; box-shadow: none !important; white-space: nowrap;
}
.pst-doxynav #MSearchBox .left { display: inline-flex; align-items: center; gap: .4rem; }
.pst-doxynav #MSearchSelect { width: 1rem !important; height: 1rem !important; opacity: .7; vertical-align: middle; }
.pst-doxynav #MSearchField {
    background: transparent !important; border: none !important; outline: none;
    color: #9ca4af !important; font-size: .85rem !important; width: 5.5rem !important;
    height: auto !important; vertical-align: middle; line-height: 1.4 !important;
}
.pst-doxynav #MSearchBox .right { display: none; }
/* "Ctrl + K" as two key-caps (like .search-button__kbd-shortcut) */
.pst-doxynav .pst-kbd { display: inline-flex; align-items: center; gap: .2rem; margin-left: .6rem; color: #9ca4af; font-size: .72rem; }
.pst-doxynav .pst-kbd kbd {
    padding: .05rem .35rem; border: 1px solid #48566b; border-radius: .25rem;
    background: transparent; color: #9ca4af; font-size: .68rem; line-height: 1.3;
    font-family: "JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;
}

/* prev/next (mirrors .prev-next-area) */
.pst-doxy-prevnext { width: 100%; padding: 0 1.5rem; margin-top: 2rem; }
.pst-doxy-prevnext a {
    align-items: center; border: none; color: #9ca4af !important; display: inline-flex;
    max-width: 45%; padding: 10px; text-decoration: none !important;
}
.pst-doxy-prevnext .pn-info { display: flex; flex-direction: column; margin: 0 .5em; }
.pst-doxy-prevnext .pn-subtitle { text-transform: capitalize; color: #9ca4af !important; }
.pst-doxy-prevnext .pn-title {
    color: #3fb1c5 !important; font-size: 1.1em; font-weight: 600;
    text-decoration: underline; text-underline-offset: .15em;
}
.pst-doxy-prevnext svg { width: 1em; height: 1em; fill: currentColor; }

/* footer (mirrors .bd-footer: page bg, top border only) */
.pst-doxyfoot {
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
    padding: 1rem 1.5rem; margin-top: 1.5rem;
    border-top: 1px solid #48566b;
    color: #9ca4af; font-size: .875rem;
    font-family: Inter,"Source Sans Pro",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.pst-doxyfoot p { margin: 0; }
.pst-doxyfoot a { color: #3fb1c5 !important; text-decoration: none !important; }
.pst-doxyfoot a:hover { text-decoration: underline !important; }

/* ---- light mode (toggle off): recolor injected components to PyData light.
   The body itself is handled by doxygen-awesome's own light theme. ---- */
html:not(.dark-mode) .pst-doxynav { background: #fff; border-bottom-color: #d1d5da; }
html:not(.dark-mode) .pst-doxynav .pst-doxynav-brand { color: #222832 !important; }
html:not(.dark-mode) .pst-doxynav a.pst-doxynav-link { color: #48566b !important; }
html:not(.dark-mode) .pst-doxynav a.pst-doxynav-link:hover,
html:not(.dark-mode) .pst-doxynav a.pst-doxynav-link[aria-current="page"] { color: #003a6b !important; }
html:not(.dark-mode) .pst-doxynav .pst-icon-btn { color: #48566b !important; }
html:not(.dark-mode) .pst-doxynav .pst-icon-btn:hover { color: #222832 !important; background: #f3f4f5; }
html:not(.dark-mode) .pst-doxynav #pst-doxy-theme { color: #8045e5 !important; box-shadow: 0 0 0 1.5px #8045e5; }
html:not(.dark-mode) .pst-doxynav #MSearchBox { background: #f3f4f5 !important; border-color: #d1d5da !important; }
html:not(.dark-mode) .pst-doxynav #MSearchField { color: #48566b !important; }
html:not(.dark-mode) .pst-doxynav .pst-kbd,
html:not(.dark-mode) .pst-doxynav .pst-kbd kbd { color: #48566b; border-color: #d1d5da; }
html:not(.dark-mode) .pst-doxyfoot { border-top-color: #d1d5da; color: #48566b; }
html:not(.dark-mode) .pst-doxyfoot a { color: #0a7d91 !important; }
html:not(.dark-mode) .pst-doxy-prevnext a { color: #48566b !important; }
html:not(.dark-mode) .pst-doxy-prevnext .pn-title { color: #0a7d91 !important; }

#MSearchResultsWindow { z-index: 1060 !important; }
"""

_DOXY_NAV = [
    ("Main Page",          lambda p, s: f"{s}tutorials/tutorials.html"),
    ("Related Pages",      lambda p, s: f"{p}pages.html"),
    ("Namespaces",         lambda p, s: f"{p}namespaces.html"),
    ("Classes",            lambda p, s: f"{p}annotated.html"),
    ("Files",              lambda p, s: f"{p}files.html"),
    ("Examples",           lambda p, s: f"{p}examples.html"),
    ("Java Documentation", lambda p, s: f"{p}javadoc/index.html"),
]
_DOXY_ACTIVE = {
    "pages.html": "Related Pages", "namespaces.html": "Namespaces",
    "annotated.html": "Classes", "files.html": "Files", "examples.html": "Examples",
}
_DOXY_HTML_TAG = re.compile(r"<html\b([^>]*)>", re.I)
_DOXY_BODY_TAG = re.compile(r"<body\b[^>]*>", re.I)
_DOXY_CLASS_ATTR = re.compile(r'class\s*=\s*"([^"]*)"', re.I)
_DOXY_SEARCHBOX = re.compile(r'<div\b[^>]*\bid="MSearchBox".*?</div>', re.I | re.S)


def _doxy_force_dark(text):
    def repl(m):
        attrs = m.group(1).replace('lang="$langISO"', 'lang="en"')
        if _DOXY_CLASS_ATTR.search(attrs):
            attrs = _DOXY_CLASS_ATTR.sub(
                lambda c: f'class="{c.group(1)} dark-mode"', attrs, count=1)
        else:
            attrs = f'{attrs.rstrip()} class="dark-mode"'
        return f"<html{attrs}>"
    return _DOXY_HTML_TAG.sub(repl, text, count=1)


def _doxy_navbar(filename, prefix, sroot, search_html):
    active = _DOXY_ACTIVE.get(filename)
    items = []
    for label, build in _DOXY_NAV:
        cur = ' aria-current="page"' if label == active else ""
        items.append(f'<li><a class="pst-doxynav-link" '
                     f'href="{build(prefix, sroot)}"{cur}>{label}</a></li>')
    end = search_html + (
        '<button id="pst-doxy-theme" class="pst-icon-btn" type="button" '
        f'title="Toggle dark mode" aria-label="Toggle dark mode">{_MOON_SVG}</button>'
        f'<a class="pst-icon-btn" href="{_REPO_URL}" target="_blank" rel="noopener" '
        f'title="GitHub" aria-label="GitHub">{_GITHUB_SVG}</a>'
    )
    return (
        '<header class="pst-doxynav">'
        f'<a class="pst-doxynav-brand" href="{sroot}tutorials/tutorials.html">'
        'OpenCV 5.x</a>'
        '<div class="pst-doxynav-center"><nav><ul>' + "".join(items)
        + '</ul></nav></div><div class="pst-doxynav-end">' + end + '</div></header>'
    )


def _retheme_doxy_page(path, root, site_root_up):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if _DOXY_MARKER in text:
        return
    if "doxygen-awesome.css" not in text or "</head>" not in text:
        return
    if not _DOXY_BODY_TAG.search(text):
        return
    depth = len(path.relative_to(root).parts) - 1
    prefix = "../" * depth
    sroot = "../" * (depth + site_root_up)
    # Lift the (functional) search box out of #titlearea into the navbar.
    search_html = ""
    m = _DOXY_SEARCHBOX.search(text)
    if m:
        search_html = m.group(0)
        if search_html.endswith("</div>"):     # add a "Ctrl + K" key-cap badge inside the pill
            search_html = (search_html[:-6]
                           + '<span class="pst-kbd"><kbd>Ctrl</kbd>+<kbd>K</kbd></span></div>')
        text = text[:m.start()] + text[m.end():]
    text = _doxy_force_dark(text)
    text = text.replace("$darkmode", "")
    head = (f'  {_FONTS_LINK}\n  <link rel="stylesheet" type="text/css" '
            f'href="{prefix}{_BRIDGE_CSS}"/>\n  {_DOXY_MARKER}\n')
    text = text.replace("</head>", head + "</head>", 1)
    navbar = _doxy_navbar(path.name, prefix, sroot, search_html)
    text = _DOXY_BODY_TAG.sub(lambda mm: mm.group(0) + "\n" + navbar, text, count=1)
    text = text.replace(
        "</body>",
        _doxy_prevnext(sroot) + _DOXY_FOOTER + _THEME_TOGGLE_JS + "</body>", 1)
    path.write_text(text, encoding="utf-8")


def _retheme_doxygen_html(outdir: pathlib.Path) -> None:
    """Copy the Doxygen HTML into outdir/api-docs and re-theme each page.
    Idempotent; skips quietly if the Doxygen HTML build is absent."""
    src = _API_XML_DIR.parent / "html"      # sibling of the Doxygen XML dir
    if not src.is_dir():
        return
    dst = outdir / "api-docs"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    (dst / _BRIDGE_CSS).write_text(_BRIDGE_CSS_CONTENT, encoding="utf-8")
    for html in dst.rglob("*.html"):
        if "search" in html.relative_to(dst).parts:
            continue
        _retheme_doxy_page(html, dst, site_root_up=1)   # api-docs is 1 below html/


def _inline_coll_graphs_on_finish(app, exception):
    """build-finished entry point."""
    if exception is not None:
        return
    out = pathlib.Path(app.outdir)
    _inline_collaboration_svgs(out / "api", out / "_images")
    _strip_breathe_class_clutter(out / "api")
    _generate_search_map(out)
    _retheme_doxygen_html(out)
