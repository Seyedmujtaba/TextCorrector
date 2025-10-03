#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds a SINGLE-FILE offline HTML for TextCorrector.

- Reads local sources (HTML/CSS/JS/Python/Dictionary)
- Inlines them into one HTML
- Embeds the ENTIRE Pyodide distribution (0.26.1) as base64
- Patches fetch() at runtime to serve those bytes: NO network & NO extra files.

Output: dist/text-corrector.html
"""

import base64
import html
import json
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# -------------------- Paths (tailored to your repo) --------------------
CSS_PATH     = ROOT / "src" / "frontend" / "style.css"
APP_JS_PATH  = ROOT / "src" / "frontend" / "app.js"
PYTHON_PATH  = ROOT / "src" / "backend" / "spell_checker.py"
DICT_PATH    = ROOT / "libs" / "dictionary" / "en_dict.txt"
PYODIDE_DIR  = ROOT / "libs" / "pyodide" / "0.26.1"   # full distribution extracted here

OUT_DIR  = ROOT / "dist"
OUT_FILE = OUT_DIR / "text-corrector.html"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------- Helpers --------------------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

# -------------------- Load inputs --------------------
style_css = read_text(CSS_PATH)
app_js    = read_text(APP_JS_PATH)
py_code   = read_text(PYTHON_PATH)
dict_text = read_text(DICT_PATH)

if not style_css:
    print(f"[!] CSS not found at {CSS_PATH}. Building without extra CSS.")
if not app_js:
    print(f"[!] app.js not found at {APP_JS_PATH}. Building without extra JS.")
if not py_code.strip():
    raise SystemExit(f"[X] Python source missing/empty: {PYTHON_PATH}")
if not dict_text:
    print(f"[!] Dictionary missing at {DICT_PATH}. Building with empty dictionary.")

if not PYODIDE_DIR.exists():
    raise SystemExit(f"[X] Pyodide dir missing: {PYODIDE_DIR}\n"
                     f"    Put the FULL distribution 0.26.1 extracted here.")

# -------------------- Collect Pyodide assets --------------------
pyodide_assets = {}   # rel path -> b64
pyodide_by_name = {}  # basename -> b64

for p in PYODIDE_DIR.rglob("*"):
    if p.is_file():
        rel = p.relative_to(PYODIDE_DIR).as_posix()
        data_b64 = b64(read_bytes(p))
        pyodide_assets[rel] = data_b64
        pyodide_by_name[p.name] = data_b64

module_choice = None
for name in ("pyodide.mjs", "pyodide.js"):
    if name in pyodide_by_name:
        module_choice = name
        break
if not module_choice:
    raise SystemExit("[X] pyodide.mjs/js not found inside libs/pyodide/0.26.1/")

# -------------------- HTML skeleton --------------------
html_head = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>TextCorrector – Offline Single File</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
{style_css}
  </style>
</head>
<body>
  <main class="container" style="max-width: 960px; margin: auto; padding: 1rem;">
    <h1>TextCorrector</h1>
    <textarea id="input" placeholder="Paste your English text here..." style="width:100%; height:220px;"></textarea>
    <div class="actions" style="margin: .75rem 0; display:flex; gap:.5rem; align-items:center;">
      <button id="checkBtn" disabled>Check</button>
      <button id="clearBtn">Clear</button>
      <span id="status" aria-live="polite">Loading Python…</span>
    </div>
    <div id="output" class="output" role="region" aria-label="Spell-check results" style="min-height:80px; border:1px solid #ddd; padding:.75rem; border-radius:.5rem;"></div>
  </main>
"""

inline_blocks = f"""
  <!-- Inline dictionary -->
  <script type="text/plain" id="english-dict">{html.escape(dict_text)}</script>

  <!-- Inline Python code -->
  <script type="text/python" id="spell-checker">
{py_code}
  </script>
"""

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

runtime_js = f"""
  <script>
  (async () => {{
    const statusEl = document.getElementById('status');
    const setStatus = (t) => statusEl.textContent = t;

    // Provide pyodide module via blob URL
    const modB64 = PYODIDE_ASSETS_BY_NAME[PYODIDE_MODULE_FILE];
    if (!modB64) {{
      setStatus('Pyodide module not found.');
      return;
    }}
    const modBlob = new Blob([b64ToBytes(modB64)], {{ type: 'text/javascript' }});
    const modUrl  = URL.createObjectURL(modBlob);

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

    setStatus('Initializing Python…');

    // indexURL won't hit network (fetch patched), but Pyodide needs it for relative paths
    const pyodide = await loadPyodide({{
      indexURL: "https://offline.local/pyodide/"
    }});

    // Put dictionary into FS
    const dictText = document.getElementById('english-dict').textContent || '';
    pyodide.FS.writeFile('en_dict.txt', dictText);

    // Run inline Python
    const pyCode = document.getElementById('spell-checker').textContent;
    await pyodide.runPythonAsync(pyCode);

    // Wire UI
    const input   = document.getElementById('input');
    const output  = document.getElementById('output');
    const checkBtn= document.getElementById('checkBtn');
    const clearBtn= document.getElementById('clearBtn');

    clearBtn.addEventListener('click', () => {{
      input.value = '';
      output.innerHTML = '';
      setStatus('Cleared');
    }});

    checkBtn.addEventListener('click', async () => {{
      try {{
        setStatus('Checking…');
        pyodide.globals.set("input_text", input.value);
        const result = await pyodide.runPythonAsync(`
from js import input_text
res = check_text(input_text, 'en_dict.txt')
res
`);
        if (Array.isArray(result)) {{
          output.innerHTML = result.map(x => '<mark>'+String(x)+'</mark>').join(' ');
        }} else {{
          output.textContent = String(result);
        }}
        setStatus('Done');
      }} catch (e) {{
        console.error(e);
        setStatus('Error: ' + (e && e.message ? e.message : String(e)));
      }}
    }});

    setStatus('Ready');
    checkBtn.disabled = false;

    // Optional: your existing frontend helpers
{app_js}
  }})();
  </script>
"""

html_tail = """
</body>
</html>
"""

page = html_head + inline_blocks + assets_js + runtime_js + html_tail
OUT_FILE.write_text(page, encoding="utf-8")
print(f"[OK] Built: {OUT_FILE}")
print("     Double-click this file to run offline.")
