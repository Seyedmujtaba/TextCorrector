#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64, html, json, re, sys, traceback
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
print(f"[LOG] ROOT = {ROOT}")

# --- Paths ---
TPL_HTML    = ROOT / "src" / "frontend" / "index.html"
CSS_PATH    = ROOT / "src" / "frontend" / "style.css"
APP_JS_PATH = ROOT / "src" / "frontend" / "app.js"

PY_MAIN       = ROOT / "src" / "backend" / "spell_checker.py"
PY_UTILS_INIT = ROOT / "src" / "utils" / "__init__.py"
PY_UTILS1     = ROOT / "src" / "utils" / "dict_loader.py"
PY_UTILS2     = ROOT / "src" / "utils" / "text_utils.py"

DICT_PATH   = ROOT / "libs" / "dictionary" / "en_dict.txt"
PYODIDE_DIR = ROOT / "libs" / "pyodide" / "0.26.1"

OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def read_text(p: Path) -> str:
    print(f"[READ] {p}")
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    print(f"[READ BIN] {p}")
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

try:
    # ---- Read sources (اگر چیزی نبود، خطا می‌گیریم فقط برای ضروری‌ها) ----
    tpl_html   = read_text(TPL_HTML)
    if not tpl_html.strip():
        print("[ERROR] Template not found or empty:", TPL_HTML); sys.exit(1)

    style_css  = read_text(CSS_PATH)  # می‌تواند خالی بماند
    app_js     = read_text(APP_JS_PATH)  # می‌تواند خالی بماند

    py_main    = read_text(PY_MAIN)
    if not py_main.strip():
        print("[ERROR] Python backend missing:", PY_MAIN); sys.exit(1)

    py_utils_init = read_text(PY_UTILS_INIT)
    py_utils1  = read_text(PY_UTILS1)
    py_utils2  = read_text(PY_UTILS2)
    if not py_utils_init or not py_utils1 or not py_utils2:
        print("[WARN] utils package missing files; ادامه می‌دهیم (فقط برای ساخت خروجی)")

    dict_text  = read_text(DICT_PATH)  # می‌تواند خالی باشد

    # ---- Collect Pyodide assets (الان فقط برای تست ساخت فایل، اگر نبود هم ادامه می‌دیم) ----
    pyodide_assets, pyodide_by_name = {}, {}
    if PYODIDE_DIR.exists():
        for p in PYODIDE_DIR.rglob("*"):
            if p.is_file():
                rel = p.relative_to(PYODIDE_DIR).as_posix()
                pyodide_assets[rel] = b64(read_bytes(p))
                pyodide_by_name[p.name] = pyodide_assets[rel]
        print(f"[OK] Collected {len(pyodide_assets)} pyodide files")
    else:
        print("[WARN] Pyodide dir not found; فعلاً ادامه می‌دهیم تا فقط فایل خروجی ساخته شود.")

    # ---- Build inline blocks ----
    inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""
    inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text or "")}</script>'
    inline_py    = f'<script type="text/plain" id="py-backend-spell-checker">{html.escape(py_main)}</script>'
    inline_utils = ""
    if py_utils_init:
        inline_utils += f'\n<script type="text/plain" id="py-utils-init">{html.escape(py_utils_init)}</script>'
    if py_utils1:
        inline_utils += f'\n<script type="text/plain" id="py-utils-dict-loader">{html.escape(py_utils1)}</script>'
    if py_utils2:
        inline_utils += f'\n<script type="text/plain" id="py-utils-text-utils">{html.escape(py_utils2)}</script>'

    # (در این مرحله فعلاً runtime/pyodide را حذف می‌کنیم تا مطمئن شویم فایل نهایی ساخته می‌شود)
    # بعد که ساختن فایل OK شد، دوباره runtime را اضافه می‌کنیم.

    page = tpl_html

    # حذف لینک‌های css خارجی؛ اگر حذف نشد هم مهم نیست
    before = len(page)
    page = re.sub(r'<link[^>]*href=["\'][^"\']*\.css[^"\']*["\'][^>]*\/?>', '', page, flags=re.I|re.S)
    print("[LOG] removed CSS bytes:", before - len(page))

    # حذف اسکریپت‌های خارجی app/pyodide؛ اگر حذف نشد هم مهم نیست
    before = len(page)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*(app\.js|pyodide[^"\']*)["\'][^>]*>\s*</script>', '', page, flags=re.I|re.S)
    print("[LOG] removed external JS bytes:", before - len(page))

    # تزریق <style> قبل از </head>
    if re.search(r'</head>', page, flags=re.I|re.S):
        page = re.sub(r'</head>', (inline_style + "\n</head>"), page, count=1, flags=re.I|re.S)
        print("[LOG] inlined <style> into <head>")
    else:
        page = (inline_style or "") + page
        print("[LOG] no </head>; prepended <style>")

    # در انتهای body فقط دیکشنری + پایتون + utils + app.js خام را می‌گذاریم
    injections = "\n".join([inline_dict, inline_utils, inline_py, f"<script>\n{app_js}\n</script>"])
    if re.search(r'</body>', page, flags=re.I|re.S):
        page = re.sub(r'</body>', injections + "\n</body>", page, count=1, flags=re.I|re.S)
        print("[LOG] injected blocks before </body>")
    else:
        page = page + injections
        print("[LOG] no </body>; appended blocks")

    OUT_FILE.write_text(page, encoding="utf-8")
    print(f"[OK] Built (minimal): {OUT_FILE}")
    print("** فعلاً فقط برای اطمینان از ساخت فایل بود. اگر این درست شد، می‌ریم سراغ افزودن Pyodide runtime. **")

except Exception as e:
    print("[EXCEPTION]", e)
    traceback.print_exc()
    sys.exit(1)
