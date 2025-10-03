#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single-file offline build for TextCorrector (keeps your UI).

- Template: src/frontend/index.html
- Inlines: style.css, app.js
- Inlines Python: src/backend/spell_checker.py
- Adds required modules: src/utils/dict_loader.py, src/utils/text_utils.py
- Inlines dictionary: libs/dictionary/en_dict.txt
- Embeds FULL Pyodide dist: libs/pyodide/0.26.1/**
- Exposes window.checkText(text) for app.js
"""

import base64, html, json, re
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ---- Paths ----
TPL_HTML    = ROOT / "src" / "frontend" / "index.html"
CSS_PATH    = ROOT / "src" / "frontend" / "style.css"
APP_JS_PATH = ROOT / "src" / "frontend" / "app.js"

PY_MAIN     = ROOT / "src" / "backend" / "spell_checker.py"
PY_UTILS1   = ROOT / "src" / "utils" / "dict_loader.py"
PY_UTILS2   = ROOT / "src" / "utils" / "text_utils.py"

DICT_PATH   = ROOT / "libs" / "dictionary" / "en_dict.txt"
PYODIDE_DIR = ROOT / "libs" / "pyodide" / "0.26.1"

OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- Helpers ----
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

# ---- Load sources ----
tpl_html   = read_text(TPL_HTML)
style_css  = read_text(CSS_PATH)
app_js     = read_text(APP_JS_PATH)
py_main    = read_text(PY_MAIN)
py_utils1  = read_text(PY_UTILS1)   # utils/dict_loader.py
py_utils2  = read_text(PY_UTILS2)   # utils/text_utils.py
dict_text  = read_text(DICT_PATH)

if not tpl_html.strip(): raise SystemExit(f"[X] Missing template: {TPL_HTML}")
if not py_main.strip():  raise SystemExit(f"[X] Missing Python: {PY_MAIN}")
if not py_utils1.strip():raise SystemExit(f"[X] Missing util: {PY_UTILS1}")
if not py_utils2.strip():raise SystemExit(f"[X] Missing util: {PY_UTILS2}")
if not PYODIDE_DIR.exists():
    raise SystemExit(f"[X] Missing Pyodide dir: {PYODIDE_DIR} (put full 0.26.1 dist here)")
if not dict_text:
    print(f"[!] Dictionary missing at {DICT_PATH}; building with empty dictionary")
    dict_text = ""

# ---- Collect Pyodide assets ----
pyodide_assets, pyodide_by_name = {}, {}
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
    raise SystemExit("[X] Could not find pyodide.mjs/js in libs/pyodide/0.26.1/")

# ---- Build injectables ----
inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""
inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text)}</script>'
inline_py    = f'<script type="text/python" id="spell-checker">\n{py_main}\n</script>'

# محتوای دو ماژول utils را در <script type=text/plain> نگه می‌داریم و موقع اجرا روی FS می‌نویسیم
inline_utils = f"""
<script type="text/plain" id="py-utils-dict-loader">{html.escape(py_utils1)}</script>
<script type="text/plain" id="py-utils-text-utils">{html.escape(py_utils2)}</script>
"""

assets_js = f"""
<script>
const PYODIDE_ASSETS_BY_PATH = {json.dumps(pyodide_assets)};
const PYODIDE_ASSETS_BY_NAME = {json.dumps(pyodide_by_name)};
const PYODIDE_MODULE_FILE = {json.dumps(module_choice)};

function b64ToBytes(b64){{
  if(!b64) return new Uint8Array();
  const bin=atob(b64), arr=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) arr[i]=bin.charCodeAt(i);
  return arr;
}}
const _pathKeys = Object.keys(PYODIDE_ASSETS_BY_PATH).sort((a,b)=>a.length-b.length);
function findAssetForUrl(url){{
  try {{
    const u=new URL(url,'https://x/'); const path=u.pathname.replace(/^\\//,''); const base=path.split('/').pop();
    if(PYODIDE_ASSETS_BY_NAME[base]) return [base,PYODIDE_ASSETS_BY_NAME[base]];
    for(let i=_pathKeys.length-1;i>=0;i--){{ const key=_pathKeys[i]; if(path.endsWith(key)) return [key,PYODIDE_ASSETS_BY_PATH[key]]; }}
  }} catch(e) {{
    const s=String(url); const base=s.split('?')[0].split('#')[0].split('/').pop();
    if(PYODIDE_ASSETS_BY_NAME[base]) return [base,PYODIDE_ASSETS_BY_NAME[base]];
  }}
  return null;
}}
const _origFetch=window.fetch.bind(window);
window.fetch=async function(input,init){{
  const url=(typeof input==='string')?input:input.url; const hit=findAssetForUrl(url);
  if(hit){{ const [name,b64]=hit; const bytes=b64ToBytes(b64);
    let mime='application/octet-stream'; const ext=(name.split('.').pop()||'').toLowerCase();
    if(ext==='wasm') mime='application/wasm';
    else if(ext==='mjs'||ext==='js') mime='text/javascript';
    else if(ext==='json'||ext==='map') mime='application/json';
    else if(ext==='zip') mime='application/zip';
    else if(ext==='txt') mime='text/plain';
    return new Response(bytes,{{status:200,headers:{{'Content-Type':mime}}}});
  }}
  return _origFetch(input,init);
}};
</script>
"""

runtime_js = f"""
<script>
(async () => {{
  // وضعیت
  const statusEl = document.getElementById('loading') || document.getElementById('status') || document.querySelector('[data-status]') || null;
  const setStatus = (t) => {{ if (statusEl) statusEl.textContent = t; }};
  setStatus('Initializing Python…');

  // لود Pyodide از Blob
  const modB64 = PYODIDE_ASSETS_BY_NAME[PYODIDE_MODULE_FILE];
  if (!modB64) {{ setStatus('Pyodide module not found.'); return; }}
  const modBlob = new Blob([b64ToBytes(modB64)], {{ type: 'text/javascript' }});
  const modUrl  = URL.createObjectURL(modBlob);

  let loadPyodide;
  if (PYODIDE_MODULE_FILE.endsWith('.mjs')) {{
    const mod = await import(modUrl);
    loadPyodide = mod.loadPyodide;
  }} else {{
    await new Promise((resolve, reject) => {{
      const s=document.createElement('script'); s.src=modUrl; s.onload=resolve; s.onerror=reject; document.head.appendChild(s);
    }});
    loadPyodide = window.loadPyodide;
  }}

  const pyodide = await loadPyodide({{ indexURL: "https://offline.local/pyodide/" }});

  // --- نوشتن فایل‌ها روی FS ---
  // 1) دیکشنری
  const dictText = (document.getElementById('english-dict')?.textContent) || '';
  pyodide.FS.writeFile('en_dict.txt', dictText);

  // 2) ماژول‌های utils
  const utilDict = (document.getElementById('py-utils-dict-loader')?.textContent) || '';
  const utilText = (document.getElementById('py-utils-text-utils')?.textContent) || '';
  // ساخت پوشه utils و نوشتن فایل‌ها
  try {{ pyodide.FS.mkdir('utils'); }} catch(_) {{}}
  pyodide.FS.writeFile('utils/dict_loader.py', utilDict);
  pyodide.FS.writeFile('utils/text_utils.py', utilText);

  // 3) اجرای پایتون اصلی (که از utils ایمپورت می‌کند)
  const pyMain = (document.getElementById('spell-checker')?.textContent) || '';
  await pyodide.runPythonAsync(pyMain);

  // API برای فرانت: window.checkText
  window.checkText = async (text) => {{
    pyodide.globals.set("js_text", text || "");
    const result = await pyodide.runPythonAsync(`
from js import js_text
ct, mc, miss, fixes = correct_text(js_text, 'en_dict.txt')
{{ "corrected_text": ct, "mistake_count": int(mc), "misspelled": list(miss), "all_fixes": [tuple(p) for p in fixes] }}
`);
    return result;
  }};

  setStatus('Ready');
}})();
</script>
"""

# ---- Merge into template ----
page = tpl_html
# حذف لینک خارجی به style.css (چون این‌لاین می‌کنیم)
page = re.sub(r'<link[^>]+href=["\'].*?style\\.css["\'][^>]*>', '', page, flags=re.I)
# تزریق <style> قبل از </head>
m = re.search(r'</head>', page, flags=re.I)
page = (page[:m.start()] + inline_style + page[m.start():]) if m else (inline_style + page)
# حذف <script src="app.js">
page = re.sub(r'<script[^>]+src=["\'].*?app\\.js["\'][^>]*>\\s*</script>', '', page, flags=re.I)
# تزریق: دیکشنری + utils + پایتون + pyodide assets + runtime + در پایان خودِ app.js
injections = "\n".join([inline_dict, inline_utils, inline_py, assets_js, runtime_js, f"<script>\n{app_js}\n</script>"])
m = re.search(r'</body>', page, flags=re.I)
page = (page[:m.start()] + injections + page[m.start():]) if m else (page + injections)

# ---- Write output ----
OUT_FILE.write_text(page, encoding="utf-8")
print(f"[OK] Built: {OUT_FILE}")
print("     Double-click this file to run offline.")
