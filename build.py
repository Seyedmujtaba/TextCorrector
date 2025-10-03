#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds a SINGLE-FILE offline HTML for TextCorrector using your own UI template.

- Takes src/frontend/index.html as the template (keeps your exact design)
- Inlines CSS (src/frontend/style.css) and removes external <link>
- Inlines JS (src/frontend/app.js) and removes external <script src>
- Inlines Python (src/backend/spell_checker.py) and dictionary (libs/dictionary/en_dict.txt)
- Embeds the FULL Pyodide distribution (libs/pyodide/0.26.1/*) as base64
- Patches fetch() so Pyodide loads from the embedded bytes (no network)

Output: dist/text-corrector.html
"""

import base64
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ------- Paths (tailored to your repo) -------
TPL_HTML    = ROOT / "src" / "frontend" / "index.html"
CSS_PATH    = ROOT / "src" / "frontend" / "style.css"
APP_JS_PATH = ROOT / "src" / "frontend" / "app.js"
PY_PATH     = ROOT / "src" / "backend" / "spell_checker.py"
DICT_PATH   = ROOT / "libs" / "dictionary" / "en_dict.txt"
PYODIDE_DIR = ROOT / "libs" / "pyodide" / "0.26.1"

OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------- Helpers ----------------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

# --------------- Load inputs ----------------
tpl_html = read_text(TPL_HTML)
if not tpl_html.strip():
    raise SystemExit(f"[X] Template HTML not found/empty: {TPL_HTML}")

style_css = read_text(CSS_PATH)
app_js    = read_text(APP_JS_PATH)
py_code   = read_text(PY_PATH)
dict_text = read_text(DICT_PATH)

if not style_css:
    print(f"[!] CSS missing at {CSS_PATH}; page will use built-in styles only if any.")
if not app_js:
    print(f"[!] app.js missing at {APP_JS_PATH}; only minimal wiring will run.")
if not py_code.strip():
    raise SystemExit(f"[X] Python code missing/empty: {PY_PATH}")
if not dict_text:
    print(f"[!] Dictionary missing at {DICT_PATH}; proceeding with empty dictionary.")
    dict_text = ""

if not PYODIDE_DIR.exists():
    raise SystemExit(f"[X] Pyodide dir missing: {PYODIDE_DIR}\n"
                     "    Put the FULL distribution 0.26.1 extracted here.")

# --------------- Collect Pyodide assets ----------------
pyodide_assets = {}   # rel path -> b64
pyodide_by_name = {}  # basename -> b64
for p in PYODIDE_DIR.rglob("*"):
    if p.is_file():
        rel = p.relative_to(PYODIDE_DIR).as_posix()
        enc = b64(read_bytes(p))
        pyodide_assets[rel] = enc
        pyodide_by_name[p.name] = enc

module_choice = None
for name in ("pyodide.mjs", "pyodide.js"):
    if name in pyodide_by_name:
        module_choice = name
        break
if not module_choice:
    raise SystemExit("[X] pyodide.mjs/js not found in libs/pyodide/0.26.1/")

# --------------- Build injectables ----------------
inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""
inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text)}</script>'
inline_py    = f'<script type="text/python" id="spell-checker">\n{py_code}\n</script>'

assets_js = f"""
<script>
const PYODIDE_ASSETS_BY_PATH = {json.dumps(pyodide_assets)};
const PYODIDE_ASSETS_BY_NAME = {json.dumps(pyodide_by_name)};
const PYODIDE_MODULE_FILE = {json.dumps(module_choice)};

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

const _origFetch = window.fetch.bind(window);
window.fetch = async function(input, init) {{
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
  return _origFetch(input, init);
}};
</script>
"""

# NOTE: اگر امضای تابع پایتون‌ت فرق داره، فقط همین یک جا را عوض کن.
runtime_js = f"""
<script>
(async () => {{
  // وضعیت
  const statusEl = document.getElementById('status') || document.querySelector('[data-status]') || (document.createElement('span'));
  const setStatus = (t) => {{ if (statusEl) statusEl.textContent = t; }};
  setStatus('Initializing Python…');

  // pyodide module via blob
  const modB64 = PYODIDE_ASSETS_BY_NAME[PYODIDE_MODULE_FILE];
  if (!modB64) {{ setStatus('Pyodide module not found.'); return; }}
  const modBlob = new Blob([b64ToBytes(modB64)], {{ type: 'text/javascript' }});
  const modUrl = URL.createObjectURL(modBlob);

  let loadPyodide;
  if (PYODIDE_MODULE_FILE.endsWith('.mjs')) {{
    const mod = await import(modUrl);
    loadPyodide = mod.loadPyodide;
  }} else {{
    await new Promise((resolve, reject) => {{
      const s = document.createElement('script');
      s.src = modUrl; s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    }});
    loadPyodide = window.loadPyodide;
  }}

  const pyodide = await loadPyodide({{ indexURL: "https://offline.local/pyodide/" }});

  // dictionary into FS
  const dictNode = document.getElementById('english-dict');
  const dictText = dictNode ? dictNode.textContent : '';
  pyodide.FS.writeFile('en_dict.txt', dictText || '');

  // run inline Python
  const pyNode = document.getElementById('spell-checker');
  await pyodide.runPythonAsync(pyNode ? pyNode.textContent : "");

  // Wire UI: سعی می‌کنیم عناصر را هوشمند پیدا کنیم تا با UI شما جور شود
  const input = document.querySelector('#input, textarea, [data-input]') || document.createElement('textarea');
  const output = document.querySelector('#output, [data-output]') || document.createElement('div');
  const checkBtn = document.querySelector('#checkBtn, [data-check], button.check');
  const clearBtn = document.querySelector('#clearBtn, [data-clear], button.clear');

  if (clearBtn) {{
    clearBtn.addEventListener('click', () => {{
      if (input) input.value = '';
      if (output) output.innerHTML = '';
      setStatus('Cleared');
    }});
  }}

  if (checkBtn) {{
    checkBtn.addEventListener('click', async () => {{
      try {{
        setStatus('Checking…');
        pyodide.globals.set("input_text", input ? input.value : "");
        const result = await pyodide.runPythonAsync(`
from js import input_text
res = check_text(input_text, 'en_dict.txt')
res
`);
        if (output) {{
          if (Array.isArray(result)) {{
            output.innerHTML = result.map(x => '<mark>'+String(x)+'</mark>').join(' ');
          }} else {{
            output.textContent = String(result);
          }}
        }}
        setStatus('Done');
      }} catch (e) {{
        console.error(e);
        setStatus('Error: ' + (e && e.message ? e.message : String(e)));
      }}
    }});
  }}

  setStatus('Ready');
  if (checkBtn) checkBtn.disabled = false;
}})();
</script>
"""

# --------------- Merge into template ---------------
page = tpl_html

# 1) حذف لینک استایل خارجی (چون این‌لاین می‌کنیم)
page = re.sub(r'<link[^>]+href=["\'].*?style\\.css["\'][^>]*>', '', page, flags=re.I)

# 2) تزریق <style> قبل از </head> (اگر head وجود دارد)
if "</head>" in page.lower():
    # پیدا کردن نسخه‌ی حساس به حروف
    head_close_idx = page.lower().rfind("</head>")
    page = page[:head_close_idx] + (inline_style or "") + page[head_close_idx:]
else:
    # اگر head نداریم، استایل را ابتدای صفحه می‌گذاریم
    page = (inline_style or "") + page

# 3) حذف <script src="app.js"> (چون این‌لاین می‌کنیم)
page = re.sub(r'<script[^>]+src=["\'].*?app\\.js["\'][^>]*>\\s*</script>', '', page, flags=re.I)

# 4) تزریق دیکشنری و کد پایتون و Pyodide-Assets و Runtime قبل از </body>
injections = "\n".join([inline_dict, inline_py, assets_js, runtime_js, f"<script>\n{app_js}\n</script>"])
if "</body>" in page.lower():
    body_close_idx = page.lower().rfind("</body>")
    page = page[:body_close_idx] + injections + page[body_close_idx:]
else:
    page = page + injections

# --------------- Write output ---------------
OUT_FILE.write_text(page, encoding="utf-8")
print(f"[OK] Built: {OUT_FILE}")
print("     Double-click this file to run offline.")
