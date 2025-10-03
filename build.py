#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64, html, json, re, sys, traceback
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

try:
    print(f"[LOG] ROOT = {ROOT}")
    # --- Paths ---
    TPL_HTML    = ROOT / "src" / "frontend" / "index.html"
    CSS_PATH    = ROOT / "src" / "frontend" / "style.css"
    APP_JS_PATH = ROOT / "src" / "frontend" / "app.js"
    PY_MAIN     = ROOT / "src" / "backend" / "spell_checker.py"
    PY_UTILS_INIT = ROOT / "src" / "utils" / "__init__.py"
    PY_UTILS1   = ROOT / "src" / "utils" / "dict_loader.py"
    PY_UTILS2   = ROOT / "src" / "utils" / "text_utils.py"
    DICT_PATH   = ROOT / "libs" / "dictionary" / "en_dict.txt"

    # --- Read sources ---
    tpl_html   = read_text(TPL_HTML)
    if not tpl_html.strip():
        raise RuntimeError(f"Template not found or empty: {TPL_HTML}")

    style_css  = read_text(CSS_PATH)     # optional
    app_js     = read_text(APP_JS_PATH)  # optional
    py_main    = read_text(PY_MAIN)
    if not py_main.strip():
        raise RuntimeError(f"Python backend missing: {PY_MAIN}")

    py_utils_init = read_text(PY_UTILS_INIT)
    py_utils1  = read_text(PY_UTILS1)
    py_utils2  = read_text(PY_UTILS2)
    dict_text  = read_text(DICT_PATH)

    # --- Inline blocks (minimal) ---
    inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""
    inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text or "")}</script>'
    inline_py    = f'<script type="text/plain" id="py-backend-spell-checker">{html.escape(py_main)}</script>'

    inline_utils = ""
    if py_utils_init: inline_utils += f'\n<script type="text/plain" id="py-utils-init">{html.escape(py_utils_init)}</script>'
    if py_utils1:    inline_utils += f'\n<script type="text/plain" id="py-utils-dict-loader">{html.escape(py_utils1)}</script>'
    if py_utils2:    inline_utils += f'\n<script type="text/plain" id="py-utils-text-utils">{html.escape(py_utils2)}</script>'

    # --- Start from template and remove external links (safe; replacement ثابت ندارد) ---
    page = tpl_html
    page = re.sub(r'<link[^>]*href=["\'][^"\']*\.css[^"\']*["\'][^>]*\/?>', '', page, flags=re.I|re.S)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*(?:app\.js|pyodide[^"\']*)["\'][^>]*>\s*</script>', '', page, flags=re.I|re.S)

    # --- Inject <style> before </head> via slicing (NO regex replacement) ---
    m_head = re.search(r'</head>', page, flags=re.I|re.S)
    if m_head:
        i = m_head.start()
        page = page[:i] + (inline_style or "") + "\n" + page[i:]
    else:
        page = (inline_style or "") + page

    # --- Prepare bottom injections ---
    injections = "\n".join([inline_dict, inline_utils, inline_py, f"<script>\n{app_js}\n</script>"])

    # --- Inject before </body> via slicing (NO regex replacement) ---
    m_body = re.search(r'</body>', page, flags=re.I|re.S)
    if m_body:
        j = m_body.start()
        page = page[:j] + injections + "\n" + page[j:]
    else:
        page = page + injections

    OUT_FILE.write_text(page, encoding="utf-8")
    print(f"[OK] Built (minimal): {OUT_FILE}")
    print("[NOTE] این نسخه فقط تضمین می‌کند فایل ساخته بشه و خطای bad escape حذف بشه. اگر ساخت OK بود، می‌ریم سراغ نسخهٔ کامل Pyodide.")
except Exception as e:
    # اگر باز هم هر خطایی رخ داد، حداقل یک فایل placeholder بسازیم
    msg = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
    placeholder = f"""<!doctype html>
<html lang="en"><meta charset="utf-8">
<title>Build Placeholder</title>
<body style="font-family:system-ui;max-width:920px;margin:40px auto;line-height:1.5">
  <h1>TextCorrector – Build Placeholder</h1>
  <p>بیلد به خطا خورد؛ این خروجی موقت فقط برای اطمینان از نوشتن فایل است.</p>
  <h3>خطا</h3>
  <pre style="white-space:pre-wrap;background:#f7f7f7;border:1px solid #ddd;padding:12px;border-radius:8px">{html.escape(msg)}</pre>
</body></html>"""
    OUT_FILE.write_text(placeholder, encoding="utf-8")
    print(f"[PLACEHOLDER WRITTEN] {OUT_FILE}")
    sys.exit(1)
