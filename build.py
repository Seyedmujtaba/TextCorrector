#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Minimal build: keep UI identical to src/frontend/index.html
# - Inline style.css (convert url(...) assets to data: URIs)
# - Inline app.js
# - Replace logo.png with Data URI
# - Inject a safe stub for window.checkText so frontend doesn't error
# No Pyodide yet.

import base64, mimetypes, re, sys
from pathlib import Path
import html
import traceback

ROOT = Path(__file__).parent.resolve()

TPL_HTML    = ROOT / "src" / "frontend" / "index.html"
CSS_PATH    = ROOT / "src" / "frontend" / "style.css"
APP_JS_PATH = ROOT / "src" / "frontend" / "app.js"

STATIC_DIR  = ROOT / "static"
LOGO_FILE   = STATIC_DIR / "logo.png"   # اگر مسیر/نام فرق دارد این را عوض کن

OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def data_uri_for(path: Path) -> str:
    if not path.exists():
        return ""
    mt, _ = mimetypes.guess_type(str(path))
    if not mt:
        if path.suffix.lower() == ".svg":
            mt = "image/svg+xml"
        elif path.suffix.lower() == ".woff2":
            mt = "font/woff2"
        elif path.suffix.lower() == ".woff":
            mt = "font/woff"
        else:
            mt = "application/octet-stream"
    return f"data:{mt};base64," + base64.b64encode(path.read_bytes()).decode("ascii")

def inline_css_assets(css_text: str, css_dir: Path, static_dir: Path) -> str:
    # تبدیل url(...) به data URI
    def repl(m):
        raw = (m.group(1) or "").strip().strip('\'"')
        if not raw or raw.startswith("data:") or raw.startswith("http"):
            return f'url("{raw}")'
        p1 = (css_dir / raw).resolve()
        p2 = (static_dir / raw).resolve()
        chosen = p1 if p1.exists() else p2
        data = data_uri_for(chosen) if chosen.exists() else ""
        return f'url("{data or raw}")'
    return re.sub(r'url\(([^)]+)\)', repl, css_text)

try:
    page = read_text(TPL_HTML)
    if not page.strip():
        raise RuntimeError(f"Template not found or empty: {TPL_HTML}")

    style_css = read_text(CSS_PATH)
    if style_css:
        style_css = inline_css_assets(style_css, CSS_PATH.parent, STATIC_DIR)
        inline_style = f"<style>\n{style_css}\n</style>"
    else:
        inline_style = ""

    app_js = read_text(APP_JS_PATH)

    # 1) جایگزینی <link href="style.css">
    # اگر تگ صریح بود، جایگزینش کن؛ وگرنه <style> را قبل از </head> تزریق کن.
    page, n_css = re.subn(
        r'<link[^>]+href=["\']\s*style\.css\s*["\'][^>]*>',
        inline_style,
        page,
        flags=re.I
    )
    if n_css == 0:
        # حذف هر لینک .css دیگر (برای جلوگیری از 404) و تزریق style در </head>
        page = re.sub(r'<link[^>]*href=["\'][^"\']*\.css[^"\']*["\'][^>]*>', '', page, flags=re.I|re.S)
        m_head = re.search(r'</head>', page, flags=re.I|re.S)
        if m_head:
            i = m_head.start()
            page = page[:i] + inline_style + "\n" + page[i:]
        else:
            page = inline_style + page

    # 2) لوگو → data URI
    if LOGO_FILE.exists():
        logo_data = data_uri_for(LOGO_FILE)
        if logo_data:
            page = re.sub(r'(<img[^>]+src=["\'])[^"\']*logo\.png(["\'])',
                          r'\1' + logo_data + r'\2',
                          page, flags=re.I)

    # 3) استاب امن برای checkText (تا app.js ارور نده)
    stub_js = """
<script>
window.checkText = async function(input){
  console.warn("[stub] checkText called (Pyodide not bundled in minimal build).");
  return { corrected_text: (input || ""), mistake_count: 0, misspelled: [], all_fixes: [] };
};
</script>""".strip()

    # 4) جایگزینی <script src="app.js"> با نسخه این‌لاین + استاب
    if app_js:
        # ابتدا استاب را قبل از app.js تزریق می‌کنیم
        inlined_app = f"{stub_js}\n<script>\n{app_js}\n</script>"
        page, n_js = re.subn(
            r'<script[^>]+src=["\']\s*app\.js\s*["\'][^>]*>\s*</script>',
            inlined_app,
            page,
            flags=re.I|re.S
        )
        if n_js == 0:
            # اگر اسکریپت خارجی نبود، خودمان انتهای بادی تزریق می‌کنیم
            m_body = re.search(r'</body>', page, flags=re.I|re.S)
            if m_body:
                j = m_body.start()
                page = page[:j] + "\n" + inlined_app + "\n" + page[j:]
            else:
                page += "\n" + inlined_app + "\n"

    # 5) هر اسکریپت خارجی Pyodide را برای این نسخه مینیمال حذف کن (که ارور ندهد)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*pyodide[^"\']*["\'][^>]*>\s*</script>', '', page, flags=re.I|re.S)

    OUT_FILE.write_text(page, encoding="utf-8")
    print(f"[OK] UI-only build written to: {OUT_FILE}")
    print("Open it and press Ctrl+F5. There should be no console errors; Check returns empty result (stub).")

except Exception as e:
    msg = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
    OUT_FILE.write_text(
        f'<!doctype html><meta charset="utf-8"><title>Build Error</title>'
        f'<pre style="white-space:pre-wrap;font:14px/1.5 system-ui,Segoe UI,Arial">{html.escape(msg)}</pre>',
        encoding="utf-8"
    )
    print("[BUILD ERROR] Placeholder written to dist/text-corrector.html")
    sys.exit(1)
