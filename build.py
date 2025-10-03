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
    tpl_html   = read_text(TPL_HTML);         
    style_css  = read_text(CSS_PATH);         
    app_js     = read_text(APP_JS_PATH);      

    py_main    = read_text(PY_MAIN);          
    py_utils_init = read_text(PY_UTILS_INIT); 
    py_utils1  = read_text(PY_UTILS1);        
    py_utils2  = read_text(PY_UTILS2);        

    dict_text  = read_text(DICT_PATH);        
    logo_bytes = read_bytes(LOGO_PATH) if LOGO_PATH.exists() else b""

    if not tpl_html.strip():   fail(f"Missing template: {TPL_HTML}")
    if not py_main.strip():    fail(f"Missing Python: {PY_MAIN}")
    if not PYODIDE_DIR.exists(): fail(f"Missing Pyodide dir: {PYODIDE_DIR}")

    # ------- Collect Pyodide assets -------
    pyodide_assets, pyodide_by_name = {}, {}
    for p in PYODIDE_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(PYODIDE_DIR).as_posix()
            pyodide_assets[rel] = b64(read_bytes(p))
            pyodide_by_name[p.name] = pyodide_assets[rel]
    print(f"[OK] collected {len(pyodide_assets)} pyodide files")

    # ------- Build injectables -------
    inline_style = f"<style>\n{style_css}\n</style>" if style_css else ""
    inline_dict  = f'<script type="text/plain" id="english-dict">{html.escape(dict_text or "")}</script>'
    inline_py    = f'<script type="text/plain" id="py-backend-spell-checker">{html.escape(py_main)}</script>'
    inline_utils = f"""
<script type="text/plain" id="py-utils-init">{html.escape(py_utils_init)}</script>
<script type="text/plain" id="py-utils-dict-loader">{html.escape(py_utils1)}</script>
<script type="text/plain" id="py-utils-text-utils">{html.escape(py_utils2)}</script>
"""

    # --- Assets JS ---
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
    if (clean.endsWith("/" + name) || clean.endsWith(name) || clean.includes("/" + name) || clean.includes(name)) {{
      return [name, PYODIDE_ASSETS_BY_NAME[name]];
    }}
  }}
  for (const rel in PYODIDE_ASSETS_BY_PATH) {{
    if (clean.endsWith("/" + rel) || clean.endsWith(rel) || clean.includes("/" + rel) || clean.includes(rel)) {{
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

    # --- Runtime JS ---
    runtime_js = f"""
<script>
(async () => {{
  const statusEl = document.getElementById('loading') || document.getElementById('status');
  const setStatus = (t) => {{ if (statusEl) statusEl.textContent = t; }};
  setStatus('Initializing Python…');

  const asmB64 = PYODIDE_ASSETS_BY_NAME["pyodide.asm.js"];
  const asmBlob = new Blob([b64ToBytes(asmB64)], {{ type: 'text/javascript' }});
  const asmUrl  = URL.createObjectURL(asmBlob);

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
  const pyodide = await loadPyodide({{ indexURL: "pyodide/" }});

  pyodide.FS.mkdir('/app').catch(()=>{});
  pyodide.FS.mkdir('/app/utils').catch(()=>{});
  pyodide.FS.writeFile('/app/en_dict.txt', document.getElementById('english-dict').textContent);
  pyodide.FS.writeFile('/app/utils/__init__.py', document.getElementById('py-utils-init').textContent);
  pyodide.FS.writeFile('/app/utils/dict_loader.py', document.getElementById('py-utils-dict-loader').textContent);
  pyodide.FS.writeFile('/app/utils/text_utils.py', document.getElementById('py-utils-text-utils').textContent);
  pyodide.FS.writeFile('/app/spell_checker.py', document.getElementById('py-backend-spell-checker').textContent);

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

    # حذف لینک css و js خارجی
    page = re.sub(r'<link[^>]*href=["\'][^"\']*\.css[^"\']*["\'][^>]*>', '', page, flags=re.I|re.S)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*(app\.js|pyodide[^"\']*)["\'][^>]*>\s*</script>', '', page, flags=re.I|re.S)

    # inline style
    page = re.sub(r'</head>', inline_style + '\n</head>', page, flags=re.I|re.S)

    # inject scripts
    injections = "\n".join([inline_dict, inline_utils, inline_py, assets_js, runtime_js, f"<script>\n{app_js}\n</script>"])
    page = re.sub(r'</body>', injections + '\n</body>', page, flags=re.I|re.S)

    OUT_FILE.write_text(page, encoding="utf-8")
    print(f"[OK] Built: {OUT_FILE}")

except Exception as e:
    traceback.print_exc()
    sys.exit(1)
