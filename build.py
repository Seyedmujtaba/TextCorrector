#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64, html, json, re, sys, traceback
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
print(f"[LOG] ROOT = {ROOT}")

# ------- Paths -------
TPL_HTML    = ROOT / "src" / "frontend" / "index.html"
CSS_PATH    = ROOT / "src" / "frontend" / "style.css"
APP_JS_PATH = ROOT / "src" / "frontend" / "app.js"

PY_MAIN       = ROOT / "src" / "backend" / "spell_checker.py"
PY_UTILS_INIT = ROOT / "src" / "utils" / "__init__.py"
PY_UTILS1     = ROOT / "src" / "utils" / "dict_loader.py"
PY_UTILS2     = ROOT / "src" / "utils" / "text_utils.py"

DICT_PATH   = ROOT / "libs" / "dictionary" / "en_dict.txt"
PYODIDE_DIR = ROOT / "libs" / "pyodide" / "0.26.1"
LOGO_PATH   = ROOT / "static" / "logo.png"  # optional

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

def fail(msg: str):
    print("[ERROR]", msg)
    sys.exit(1)

try:
    # ------- Load sources -------
    tpl_html   = read_text(TPL_HTML);         print("[OK] template length:", len(tpl_html))
    style_css  = read_text(CSS_PATH);         print("[OK] css length:", len(style_css))
    app_js     = read_text(APP_JS_PATH);      print("[OK] app.js length:", len(app_js))

    py_main    = read_text(PY_MAIN);          print("[OK] spell_checker.py length:", len(py_main))
    py_utils_init = read_text(PY_UTILS_INIT); print("[OK] utils __init__ length:", len(py_utils_init))
    py_utils1  = read_text(PY_UTILS1);        print("[OK] dict_loader length:", len(py_utils1))
    py_utils2  = read_text(PY_UTILS2);        print("[OK] text_utils length:", len(py_utils2))

    dict_text  = read_text(DICT_PATH);        print("[OK] dict length:", len(dict_text))
    logo_bytes = read_bytes(LOGO_PATH) if LOGO_PATH.exists() else b""
    if logo_bytes: print("[OK] logo.png size:", len(logo_bytes))

    if not tpl_html.strip():   fail(f"Missing template: {TPL_HTML}")
    if not py_main.strip():    fail(f"Missing Python: {PY_MAIN}")
    if not py_utils_init.strip(): fail(f"Missing util: {PY_UTILS_INIT}")
    if not py_utils1.strip():  fail(f"Missing util: {PY_UTILS1}")
    if not py_utils2.strip():  fail(f"Missing util: {PY_UTILS2}")
    if not PYODIDE_DIR.exists(): fail(f"Missing Pyodide dir: {PYODIDE_DIR}")

    # ------- Collect Pyodide assets -------
    print("[LOG] Collecting Pyodide assets…")
    pyodide_assets, pyodide_by_name = {}, {}
    count = 0
    for p in PYODIDE_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(PYODIDE_DIR).as_posix()
            pyodide_assets[rel] = b64(read_bytes(p))
            pyodide_by_name[p.name] = pyodide_assets[rel]
            count += 1
    print(f"[OK] collected {count} pyodide files")
    print("[CHECK] has pyodide.js:", "pyodide.js" in pyodide_by_name)
    print("[CHECK] has pyodide.mjs:", "pyodide.mjs" in pyodide_by_name)
    print("[CHECK] has pyodide.asm.js:", "pyodide.asm.js" in pyodide_by_name)
    print("[CHECK] has python_stdlib.zip:", "python_stdlib.zip" in pyodide_by_name)

    if "pyodide.asm.js" not in pyodide_by_name:
        fail("pyodide.asm.js not found in libs/pyodide/0.26.1/")

    # ------- Build injectables -------
    inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""
    inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text or "")}</script>'
    inline_py    = f'<script type="text/plain" id="py-backend-spell-checker">{html.escape(py_main)}</script>'
    inline_utils = f"""
<script type="text/plain" id="py-utils-init">{html.escape(py_utils_init)}</script>
<script type="text/plain" id="py-utils-dict-loader">{html.escape(py_utils1)}</script>
<script type="text/plain" id="py-utils-text-utils">{html.escape(py_utils2)}</script>
"""

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

const _pathKeys = Object.keys(PYODIDE_ASSETS_BY_PATH).sort((a,b)=>a.length-b.length);
function findAssetForUrl(url) {{
  try {{
    const u = new URL(url, 'https://x/');
    const path = u.pathname.replace(/^\\//,'');
    const base = path.split('/').pop();
    if (PYODIDE_ASSETS_BY_NAME[base]) return [base, PYODIDE_ASSETS_BY_NAME[base]];
    for (let i=_pathKeys.length-1; i>=0; i--) {{
      const key = _pathKeys[i];
      if (path.endsWith(key)) return [key, PYODIDE_ASSETS_BY_PATH[key]];
    }}
  }} catch (e) {{
    const s = String(url);
    const base = s.split('?')[0].split('#')[0].split('/').pop();
    if (PYODIDE_ASSETS_BY_NAME[base]) return [base, PYODIDE_ASSETS_BY_NAME[base]];
  }}
  return null;
}}

// Patch fetch globally
(function patchFetch() {{
  const orig = (globalThis.fetch || window.fetch).bind(globalThis);
  async function patched(input, init) {{
    const url = (typeof input === 'string') ? input : input.url;
    const hit = findAssetForUrl(url);
    if (hit) {{
      const [name, b64] = hit;
      const bytes = b64ToBytes(b64);
      let mime = 'application/octet-stream';
      const ext = (name.split('.').pop()||'').toLowerCase();
      if (ext === 'wasm') mime = 'application/wasm';
      else if (ext === 'mjs' || ext === 'js') mime = 'text/javascript';
      else if (ext === 'json' || ext === 'map') mime = 'application/json';
      else if (ext === 'zip') mime = 'application/zip';
      else if (ext === 'txt') mime = 'text/plain';
      return new Response(bytes, {{ status: 200, headers: {{ 'Content-Type': mime }} }});
    }}
    return orig(input, init);
  }}
  globalThis.fetch = patched;
  if (window) window.fetch = patched;
  console.log("[JS] fetch patched");
}})();
</script>
"""

    runtime_js = f"""
<script>
(async () => {{
  const statusEl = document.getElementById('loading') || document.getElementById('status') || document.querySelector('[data-status]') || null;
  const setStatus = (t) => {{ if (statusEl) statusEl.textContent = t; }};
  setStatus('Initializing Python…');

  // Prepare Blob URL for pyodide.asm.js
  const asmB64 = PYODIDE_ASSETS_BY_NAME["pyodide.asm.js"];
  const asmBlob = new Blob([b64ToBytes(asmB64)], {{ type: 'text/javascript' }});
  const asmUrl  = URL.createObjectURL(asmBlob);

  // Rewrite pyodide.js (or .mjs) to import(asmUrl) instead of "pyodide.asm.js"
  const jsName = "pyodide.js" in PYODIDE_ASSETS_BY_NAME ? "pyodide.js" : "pyodide.mjs";
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
  if (typeof loadPyodide !== 'function') {{ setStatus('loadPyodide not available'); return; }}

  const pyodide = await loadPyodide({{ indexURL: "https://x.local/pyodide/" }});

  // FS
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

  setStatus('Ready');
  console.log("[JS] Pyodide ready; checkText exposed");
}})();
</script>
"""

    # ------- Merge into template -------
    page = tpl_html

    # Optional logo → data URI
    if logo_bytes:
        logo_datauri = "data:image/png;base64," + b64(logo_bytes)
        page = re.sub(r'(<img[^>]+src=["\'])[^\']*logo\\.png(["\'])',
                      rf'\\1{logo_datauri}\\2', page, flags=re.I|re.S)

    # Aggressive removal of ALL external CSS links (any .css, including preload)
    before = len(page)
    page = re.sub(r'<link[^>]*href=["\'][^"\']*\\.css[^"\']*["\'][^>]*>', '', page, flags=re.I|re.S)
    print("[LOG] removed CSS tags bytes:", before - len(page))

    # Remove any external scripts that might exist for app.js or pyodide setup
    before = len(page)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*app\\.js[^"\']*["\'][^>]*>\\s*</script>', '', page, flags=re.I|re.S)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*pyodide[^"\']*["\'][^>]*>\\s*</script>', '', page, flags=re.I|re.S)
    print("[LOG] removed external JS tags bytes:", before - len(page))

    # Inject <style> before </head>
    m = re.search(r'</head>', page, flags=re.I|re.S)
    if m:
        page = page[:m.start()] + (f"{inline_style}\n" if inline_style else "") + page[m.start():]
        print("[LOG] inlined <style>")
    else:
        page = (inline_style or "") + page
        print("[LOG] no </head> found; prepended <style>")

    # Inject scripts before </body>
    injections = "\n".join([inline_dict, inline_utils, inline_py, assets_js, runtime_js, f"<script>\n{app_js}\n</script>"])
    m = re.search(r'</body>', page, flags=re.I|re.S)
    if m:
        page = page[:m.start()] + injections + page[m.start():]
        print("[LOG] injected scripts before </body>")
    else:
        page = page + injections
        print("[LOG] no </body> found; appended scripts")

    OUT_FILE.write_text(page, encoding="utf-8")
    print(f"[OK] Built: {OUT_FILE}")

except SystemExit:
    raise
except Exception as e:
    print("[EXCEPTION]", e)
    traceback.print_exc()
    sys.exit(1)
