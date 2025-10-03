#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single-file offline build for TextCorrector (uses your UI and forces pyodide.js).

Fixes:
- Forces UMD loader (pyodide.js) to avoid dynamic import issues
- Removes external refs (style.css, app.js, pyodide_setup.js) and inlines them
- Writes utils package (with __init__.py) into Pyodide FS
- Returns plain JS object from window.checkText (not PyProxy)
"""

import base64, html, json, re
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

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

OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------- Helpers -------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

# ------- Load sources -------
tpl_html   = read_text(TPL_HTML)
style_css  = read_text(CSS_PATH)
app_js     = read_text(APP_JS_PATH)
py_main    = read_text(PY_MAIN)
py_utils_init = read_text(PY_UTILS_INIT)
py_utils1  = read_text(PY_UTILS1)
py_utils2  = read_text(PY_UTILS2)
dict_text  = read_text(DICT_PATH)

if not tpl_html.strip():      raise SystemExit(f"[X] Missing template: {TPL_HTML}")
if not py_main.strip():       raise SystemExit(f"[X] Missing Python: {PY_MAIN}")
if not py_utils_init.strip(): raise SystemExit(f"[X] Missing util: {PY_UTILS_INIT}")
if not py_utils1.strip():     raise SystemExit(f"[X] Missing util: {PY_UTILS1}")
if not py_utils2.strip():     raise SystemExit(f"[X] Missing util: {PY_UTILS2}")
if not PYODIDE_DIR.exists():
    raise SystemExit(f"[X] Missing Pyodide dir: {PYODIDE_DIR} (put full 0.26.1 dist here)")
if dict_text is None:
    dict_text = ""

# ------- Collect Pyodide assets -------
pyodide_assets, pyodide_by_name = {}, {}
for p in PYODIDE_DIR.rglob("*"):
    if p.is_file():
        rel = p.relative_to(PYODIDE_DIR).as_posix()
        enc = b64(read_bytes(p))
        pyodide_assets[rel] = enc
        pyodide_by_name[p.name] = enc

# Force pyodide.js (UMD), fallback to mjs only if js missing
if "pyodide.js" in pyodide_by_name:
    module_choice = "pyodide.js"
elif "pyodide.mjs" in pyodide_by_name:
    module_choice = "pyodide.mjs"
else:
    raise SystemExit("[X] Neither pyodide.js nor pyodide.mjs found in libs/pyodide/0.26.1/")

# ------- Injectables -------
inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""
inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text)}</script>'
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
const PYODIDE_MODULE_FILE = {json.dumps(module_choice)};

// --- fetch patch (main + globalThis) ---
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
}})();
</script>
"""

runtime_js = f"""
<script>
(async () => {{
  // status
  const statusEl = document.getElementById('loading') || document.getElementById('status') || document.querySelector('[data-status]') || null;
  const setStatus = (t) => {{ if (statusEl) statusEl.textContent = t; }};
  setStatus('Initializing Python…');

  // Load pyodide.js (UMD) via Blob to avoid any network
  const fileB64 = PYODIDE_ASSETS_BY_NAME[PYODIDE_MODULE_FILE];
  if (!fileB64) {{ setStatus('pyodide.js not found'); return; }}
  const blob = new Blob([b64ToBytes(fileB64)], {{ type: 'text/javascript' }});
  const url  = URL.createObjectURL(blob);
  await new Promise((resolve, reject) => {{
    const s = document.createElement('script');
    s.src = url; s.onload = resolve; s.onerror = reject;
    document.head.appendChild(s);
  }});
  const loadPyodide = window.loadPyodide;
  if (typeof loadPyodide !== 'function') {{ setStatus('loadPyodide not available'); return; }}

  // Important: use a fake domain with a dot (not underscore) to avoid module import errors
  const pyodide = await loadPyodide({{ indexURL: "https://x.local/pyodide/" }});

  // Write files into FS
  try {{ pyodide.FS.mkdir('/app'); }} catch(_) {{}}
  try {{ pyodide.FS.mkdir('/app/utils'); }} catch(_) {{}}
  // dictionary
  const dictText = (document.getElementById('english-dict')?.textContent) || '';
  pyodide.FS.writeFile('/app/en_dict.txt', dictText);
  // utils package
  pyodide.FS.writeFile('/app/utils/__init__.py', (document.getElementById('py-utils-init')?.textContent) || '');
  pyodide.FS.writeFile('/app/utils/dict_loader.py', (document.getElementById('py-utils-dict-loader')?.textContent) || '');
  pyodide.FS.writeFile('/app/utils/text_utils.py', (document.getElementById('py-utils-text-utils')?.textContent) || '');
  // backend module
  pyodide.FS.writeFile('/app/spell_checker.py', (document.getElementById('py-backend-spell-checker')?.textContent) || '');

  // Make /app importable
  await pyodide.runPythonAsync(`
import sys
if "/app" not in sys.path:
    sys.path.insert(0, "/app")
import spell_checker
`);

  // Expose API expected by app.js (return plain JS object)
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
}})();
</script>
"""

# ------- Merge into template -------
page = tpl_html

# 1) remove external style.css
page = re.sub(r'<link[^>]+href=[\'"][^"\']*style\\.css[\'"][^>]*\\/?>(\\s*)', '', page, flags=re.I)

# 2) remove external app.js
page = re.sub(r'<script[^>]+src=[\'"][^"\']*app\\.js[\'"][^>]*>\\s*</script>', '', page, flags=re.I)

# 3) remove any pyodide_setup.js refs
page = re.sub(r'<script[^>]+src=[\'"][^"\']*pyodide_setup\\.js[\'"][^>]*>\\s*</script>', '', page, flags=re.I)

# 4) inline <style> before </head>
m = re.search(r'</head>', page, flags=re.I)
page = (page[:m.start()] + inline_style + page[m.start():]) if m else (inline_style + page)

# 5) inject dictionary + utils + backend + pyodide assets + runtime + (finally) your app.js
injections = "\n".join([inline_dict, inline_utils, inline_py, assets_js, runtime_js, f"<script>\n{app_js}\n</script>"])
m = re.search(r'</body>', page, flags=re.I)
page = (page[:m.start()] + injections + page[m.start():]) if m else (page + injections)

OUT_FILE.write_text(page, encoding="utf-8")
print(f"[OK] Built: {OUT_FILE}")
print("     Double-click this file to run offline.")
