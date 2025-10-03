#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TextCorrector - single-file offline build
# UI = EXACTLY src/frontend/index.html (no layout change)
# - Inline style.css (and convert url(...) assets to Data URI)
# - Inline app.js
# - Replace logo.png with Data URI
# - Embed Pyodide 0.26.1 dist and patch fetch
# - Rewrite pyodide.js to import pyodide.asm.js from a Blob (no network)
# - Expose window.checkText and then run your app.js

import base64, html, json, mimetypes, re, sys, traceback
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ---- Project paths
TPL_HTML    = ROOT / "src" / "frontend" / "index.html"
CSS_PATH    = ROOT / "src" / "frontend" / "style.css"
APP_JS_PATH = ROOT / "src" / "frontend" / "app.js"

PY_MAIN       = ROOT / "src" / "backend" / "spell_checker.py"
PY_UTILS_INIT = ROOT / "src" / "utils" / "__init__.py"
PY_UTILS1     = ROOT / "src" / "utils" / "dict_loader.py"
PY_UTILS2     = ROOT / "src" / "utils" / "text_utils.py"

DICT_PATH   = ROOT / "libs" / "dictionary" / "en_dict.txt"
PYODIDE_DIR = ROOT / "libs" / "pyodide" / "0.26.1"

STATIC_DIR  = ROOT / "static"         # برای لوگو/فونت/تصویرها
LOGO_FILE   = STATIC_DIR / "logo.png" # اگر نام یا مسیر فرق دارد، اصلاح کن

OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- helpers ----------------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

def data_uri_for(path: Path) -> str:
    if not path.exists():
        return ""
    mt, _ = mimetypes.guess_type(str(path))
    if not mt:
        # چند مورد رایج
        if path.suffix.lower() == ".svg":
            mt = "image/svg+xml"
        elif path.suffix.lower() in (".woff", ".woff2"):
            mt = "font/woff2" if path.suffix.lower() == ".woff2" else "font/woff"
        else:
            mt = "application/octet-stream"
    return f"data:{mt};base64," + b64(path.read_bytes())

def inline_css_assets(css_text: str, css_dir: Path, static_dir: Path) -> str:
    # url("...") یا url('...') یا url(...)
    def repl(m):
        raw = (m.group(1) or "").strip().strip('\'"')
        if not raw or raw.startswith("data:") or raw.startswith("http"):
            return f'url("{raw}")'
        # تلاش برای یافتن فایل
        # اگر آدرس نسبیِ داخل CSS باشد
        p1 = (css_dir / raw).resolve()
        # اگر دارایی‌ها داخل static باشند
        p2 = (static_dir / raw).resolve()
        # اگر path با ../ یا ./ شروع شود، هر دو را تست می‌کنیم
        chosen = p1 if p1.exists() else p2
        data = data_uri_for(chosen) if chosen.exists() else ""
        return f'url("{data or raw}")'
    return re.sub(r'url\(([^)]+)\)', repl, css_text)

print(f"[LOG] ROOT = {ROOT}")

try:
    # ---- Read sources
    tpl_html   = read_text(TPL_HTML)
    if not tpl_html.strip():
        raise RuntimeError(f"Template not found or empty: {TPL_HTML}")

    style_css  = read_text(CSS_PATH)
    app_js     = read_text(APP_JS_PATH)

    py_main    = read_text(PY_MAIN)
    if not py_main.strip():
        raise RuntimeError(f"Python backend missing: {PY_MAIN}")
    py_utils_init = read_text(PY_UTILS_INIT)
    py_utils1  = read_text(PY_UTILS1)
    py_utils2  = read_text(PY_UTILS2)
    dict_text  = read_text(DICT_PATH)

    # ---- Inline CSS assets & build <style>
    if style_css:
        style_css = inline_css_assets(style_css, CSS_PATH.parent, STATIC_DIR)
    inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""

    # ---- Inline Python sources and dictionary (kept hidden in text/plain)
    inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text or "")}</script>'
    inline_py    = f'<script type="text/plain" id="py-backend-spell-checker">{html.escape(py_main)}</script>'
    inline_utils = ""
    if py_utils_init: inline_utils += f'\n<script type="text/plain" id="py-utils-init">{html.escape(py_utils_init)}</script>'
    if py_utils1:    inline_utils += f'\n<script type="text/plain" id="py-utils-dict-loader">{html.escape(py_utils1)}</script>'
    if py_utils2:    inline_utils += f'\n<script type="text/plain" id="py-utils-text-utils">{html.escape(py_utils2)}</script>'

    # ---- Collect Pyodide files (full dist 0.26.1)
    if not PYODIDE_DIR.exists():
        raise RuntimeError(f"Missing Pyodide dist: {PYODIDE_DIR}")
    pyodide_assets, pyodide_by_name = {}, {}
    for p in PYODIDE_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(PYODIDE_DIR).as_posix()
            enc = b64(read_bytes(p))
            pyodide_assets[rel] = enc
            pyodide_by_name[p.name] = enc
    print(f"[OK] Collected {len(pyodide_assets)} pyodide files")

    if "pyodide.asm.js" not in pyodide_by_name or ("pyodide.js" not in pyodide_by_name and "pyodide.mjs" not in pyodide_by_name):
        raise RuntimeError("pyodide.asm.js / pyodide.js (.mjs) not found inside libs/pyodide/0.26.1")

    # ---- JS that exposes assets + robust fetch patch
    assets_js = f"""
<script>
const PYODIDE_ASSETS_BY_PATH = {json.dumps(pyodide_assets)};
const PYODIDE_ASSETS_BY_NAME = {json.dumps(pyodide_by_name)};

function b64ToBytes(b64) {{
  if (!b64) return new Uint8Array();
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i=0; i<bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}}

function findAssetForUrl(inputUrl) {{
  const s = String(inputUrl || "");
  const clean = s.split("?")[0].split("#")[0];
  for (const name in PYODIDE_ASSETS_BY_NAME) {{
    if (clean.endsWith("/"+name) || clean.endsWith(name) || clean.includes("/"+name)) {{
      return [name, PYODIDE_ASSETS_BY_NAME[name]];
    }}
  }}
  for (const rel in PYODIDE_ASSETS_BY_PATH) {{
    if (clean.endsWith("/"+rel) || clean.endsWith(rel) || clean.includes("/"+rel)) {{
      return [rel, PYODIDE_ASSETS_BY_PATH[rel]];
    }}
  }}
  return null;
}}

(function patchFetch() {{
  const orig = (globalThis.fetch || window.fetch).bind(globalThis);
  async function patched(input, init) {{
    const url = (typeof input === 'string') ? input : input.url;
    const hit = findAssetForUrl(url);
    if (hit) {{
      const [name, b64] = hit;
      console.debug("[fetch HIT]", url, "->", name);
      const bytes = b64ToBytes(b64);
      let mime = 'application/octet-stream';
      const ext = (name.split('.').pop()||'').toLowerCase();
      if (ext === 'wasm') mime = 'application/wasm';
      else if (ext === 'mjs' || ext === 'js') mime = 'text/javascript';
      else if (ext === 'json' || ext === 'map') mime = 'application/json';
      else if (ext === 'zip') mime = 'application/zip';
      else if (ext === 'txt') mime = 'text/plain';
      return new Response(bytes, {{ status: 200, headers: {{ 'Content-Type': mime }} }});
    }} else {{
      console.debug("[fetch MISS]", url);
    }}
    return orig(input, init);
  }}
  globalThis.fetch = patched;
  if (window) window.fetch = patched;
  console.log("[JS] fetch patched");
}})();
</script>
"""

    # ---- Runtime: load (rewritten) pyodide.js, init, expose window.checkText
    runtime_js = f"""
<script>
(async () => {{
  const statusEl = document.getElementById('loading') || document.getElementById('status');
  const setStatus = (t) => {{ if (statusEl) statusEl.textContent = t; }};
  setStatus && setStatus('Initializing Python…');

  // Prepare Blob URL for pyodide.asm.js
  const asmB64 = PYODIDE_ASSETS_BY_NAME["pyodide.asm.js"];
  const asmBlob = new Blob([b64ToBytes(asmB64)], {{ type: 'text/javascript' }});
  const asmUrl  = URL.createObjectURL(asmBlob);

  // Rewrite pyodide.(m)js to import(asmUrl)
  const jsName = ("pyodide.js" in PYODIDE_ASSETS_BY_NAME) ? "pyodide.js" : "pyodide.mjs";
  let jsText = new TextDecoder().decode(b64ToBytes(PYODIDE_ASSETS_BY_NAME[jsName]));
  jsText = jsText
    .replace(/import\\((['"`]).*?pyodide\\.asm\\.js\\1\\)/g, 'import("'+asmUrl+'")')
    .replace(/["'`]pyodide\\.asm\\.js["'`]/g, JSON.stringify(asmUrl));

  const jsBlob = new Blob([jsText], {{ type: 'text/javascript' }});
  const jsUrl  = URL.createObjectURL(jsBlob);
  await new Promise((resolve, reject) => {{
    const s = document.createElement('script');
    s.src = jsUrl; s.onload = resolve; s.onerror = reject;
    document.head.appendChild(s);
  }});

  const loadPyodide = window.loadPyodide;
  if (typeof loadPyodide !== 'function') {{
    console.error("loadPyodide not available");
    setStatus && setStatus('Pyodide load error');
    return;
  }}

  // Important: relative indexURL so our patched fetch catches everything
  const pyodide = await loadPyodide({{ indexURL: "pyodide/" }});

  // Write files to FS
  try {{ pyodide.FS.mkdir('/app'); }} catch(_) {{}}
  try {{ pyodide.FS.mkdir('/app/utils'); }} catch(_) {{}}

  const dictText = (document.getElementById('english-dict')?.textContent) || '';
  pyodide.FS.writeFile('/app/en_dict.txt', dictText);

  pyodide.FS.writeFile('/app/utils/__init__.py', (document.getElementById('py-utils-init')?.textContent) || '');
  pyodide.FS.writeFile('/app/utils/dict_loader.py', (document.getElementById('py-utils-dict-loader')?.textContent) || '');
  pyodide.FS.writeFile('/app/utils/text_utils.py', (document.getElementById('py-utils-text-utils')?.textContent) || '');
  pyodide.FS.writeFile('/app/spell_checker.py', (document.getElementById('py-backend-spell-checker')?.textContent) || '');

  await pyodide.runPythonAsync(`
import sys
if "/app" not in sys.path:
    sys.path.insert(0, "/app")
import spell_checker
`);

  // JS API expected by your frontend
  window.checkText = async (text) => {{
    pyodide.globals.set("js_text", text || "");
    const pyRes = await pyodide.runPythonAsync(`
from js import js_text
import spell_checker
ct, mc, miss, fixes = spell_checker.correct_text(js_text, "/app/en_dict.txt")
{{ "corrected_text": ct, "mistake_count": int(mc), "misspelled": list(miss), "all_fixes": [tuple(p) for p in fixes] }}
`);
    const jsRes = pyRes.toJs({{ dict_converter: Object.fromEntries }});
    if (pyRes.destroy) pyRes.destroy();
    if (!Array.isArray(jsRes.misspelled)) {{
      try {{ jsRes.misspelled = Array.from(jsRes.misspelled ?? []); }} catch(_) {{ jsRes.misspelled = []; }}
    }}
    return jsRes;
  }};

  setStatus && setStatus('Ready');
  console.log("[JS] Pyodide ready; checkText exposed");
}})();
</script>
"""

    # ---- Start from template (keep UI identical)
    page = tpl_html

    # 1) Replace <link href="style.css"> with inline <style> … </style>
    if style_css:
        page, n1 = re.subn(
            r'<link[^>]+href=["\']\s*style\.css\s*["\'][^>]*>',
            inline_style,
            page,
            flags=re.I
        )
        if n1 == 0:
            # اگر لینک با شکل دیگری است (rel=stylesheet و …)، همهٔ لینک‌های .css صفحه را برداریم و جای اولی style را بگذاریم
            page = re.sub(r'<link[^>]*href=["\'][^"\']*\.css[^"\']*["\'][^>]*>', '', page, flags=re.I|re.S)
            # قبل از </head> بگذار
            m_head = re.search(r'</head>', page, flags=re.I|re.S)
            if m_head:
                i = m_head.start()
                page = page[:i] + inline_style + "\n" + page[i:]
            else:
                page = inline_style + page

    # 2) Replace <script src="app.js"> with inline <script> … </script>
    if app_js:
        page, n2 = re.subn(
            r'<script[^>]+src=["\']\s*app\.js\s*["\'][^>]*>\s*</script>',
            f"<script>\n{app_js}\n</script>",
            page,
            flags=re.I|re.S
        )
        if n2 == 0:
            # اگر نبود، چیزی حذف نکن؛ app.js را در انتها تزریق خواهیم کرد (پس UI بهم نمی‌ریزد)
            pass

    # 3) Replace logo.png with Data URI
    if LOGO_FILE.exists():
        logo_data = data_uri_for(LOGO_FILE)
        if logo_data:
            page = re.sub(
                r'(<img[^>]+src=["\'])[^"\']*logo\.png(["\'])',
                r'\1' + logo_data + r'\2',
                page,
                flags=re.I
            )

    # 4) Remove any external pyodide script tags if present (safety)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*pyodide[^"\']*["\'][^>]*>\s*</script>', '', page, flags=re.I|re.S)

    # 5) Inject our blocks before </body> using slicing (avoid regex replacement backslash issues)
    bottom = "\n".join([inline_dict, inline_utils, assets_js, runtime_js, f"<script>\n{app_js}\n</script>"])
    m_body = re.search(r'</body>', page, flags=re.I|re.S)
    if m_body:
        j = m_body.start()
        page = page[:j] + bottom + "\n" + page[j:]
    else:
        page += bottom

    OUT_FILE.write_text(page, encoding="utf-8")
    print(f"[OK] Built: {OUT_FILE}")
    print("Open dist/text-corrector.html (Ctrl+F5). Console should show [JS] fetch patched → [JS] Pyodide ready.")

except Exception as e:
    msg = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
    # Always write a placeholder so you have a file to open
    OUT_FILE.write_text(f"""<!doctype html><meta charset="utf-8"><title>Build Error</title>
<pre style="white-space:pre-wrap;font:14px/1.5 system-ui,Segoe UI,Arial">{html.escape(msg)}</pre>""", encoding="utf-8")
    print("[BUILD ERROR] A placeholder HTML was written to dist/text-corrector.html")
    sys.exit(1)
