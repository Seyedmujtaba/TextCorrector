#---writed by Seyedmujtaba Tabatabaee---#
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds a SINGLE-FILE offline HTML for TextCorrector.

- Reads your local sources (HTML/CSS/JS/Python/Dictionary)
- Inlines them into one HTML
- Embeds the ENTIRE Pyodide distribution (0.26.1) as base64
- Patches fetch() at runtime to serve those bytes, so NO network & NO extra files.

Output: dist/text-corrector.html
"""

import base64
import html
import json
import mimetypes
import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# ---- Project paths (adjust if different) ------------------------------------
CSS_PATH       = ROOT / "static" / "style.css"
APP_JS_PATH    = ROOT / "static" / "app.js"
PYTHON_PATH    = ROOT / "src" / "spell_checker.py"
DICT_PATH      = ROOT / "libs" / "en_dict.txt"          # اگر جای دیگری است، عوض کن
PYODIDE_DIR    = ROOT / "libs" / "pyodide" / "0.26.1"   # فول‌دیسـت Pyodide که Extract کردی
OUT_DIR        = ROOT / "dist"
OUT_FILE       = OUT_DIR / "text-corrector.html"

OUT_DIR.mkdir(parents=True, exist_ok=True)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def read_bytes(p: Path) -> bytes:
    return p.read_bytes() if p.exists() else b""

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

# ---- Load project assets -----------------------------------------------------
style_css   = read_text(CSS_PATH)
app_js      = read_text(APP_JS_PATH)
py_code     = read_text(PYTHON_PATH)
dict_text   = read_text(DICT_PATH)

if not py_code.strip():
    raise SystemExit(f"[!] Python file not found or empty: {PYTHON_PATH}")

if not dict_text:
    print(f"[!] Dictionary not found at {DICT_PATH}. Continuing with empty dictionary.")
    dict_text = ""

# ---- Collect ALL files from Pyodide distribution ----------------------------
if not PYODIDE_DIR.exists():
    raise SystemExit(f"[!] Pyodide folder missing: {PYODIDE_DIR}\n"
                     "    Put the FULL distribution (extracted) here.")

pyodide_assets = {}          # key: relative path from PYODIDE_DIR, value: base64
pyodide_by_name = {}         # key: basename only (for quick match), value: same base64

for p in PYODIDE_DIR.rglob("*"):
    if p.is_file():
        rel = p.relative_to(PYODIDE_DIR).as_posix()
        data_b64 = b64(read_bytes(p))
        pyodide_assets[rel] = data_b64
        name = p.name
        # If duplicate basenames exist, last one wins (rare in pyodide dist)
        pyodide_by_name[name] = data_b64

# Heuristics to pick module file for import:
POSSIBLE_MODULES = ["pyodide.mjs", "pyodide.js"]
module_choice = None
for m in POSSIBLE_MODULES:
    if m in pyodide_by_name:
        module_choice = m
        break
if not module_choice:
    raise SystemExit("[!] Could not find pyodide.mjs or pyodide.js in your Pyodide dir.")

# ---- Build HTML --------------------------------------------------------------
def js_string_escape(s: str) -> str:
    # For embedding as JS string literal safely
    return s.replace("\\", "\\\\").replace("</", "<\\/").replace("\n", "\\n").replace("\r", "")

# Minimal page UI (modify to taste)
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
  <main class="container">
    <h1>TextCorrector</h1>
    <textarea id="input" placeholder="Paste your English text here..."></textarea>
    <div class="actions">
      <button id="checkBtn" disabled>Check</button>
      <button id="clearBtn">Clear</button>
      <span id="status" aria-live="polite">Loading Python…</span>
    </div>
    <div id="output" class="output" role="region" aria-label="Spell-check results"></div>
  </main>
"""

# Dictionary and Python inline blocks
inline_blocks = f"""
  <!-- Inline dictionary -->
  <script type="text/plain" id="english-dict">{html.escape(dict_text)}</script>

  <!-- Inline Python code -->
  <script type="text/python" id="spell-checker">
{py_code}
  </script>
"""

def build_pyodide_assets_js() -> str:
    # Produce two JS objects: byPath and byName (both base64 strings)
    by_path_json = json.dumps(pyodide_assets)  # rel path -> b64
    by_name_json = json.dumps(pyodide_by_name) # basename -> b64
    # Small helper to infer MIME
    return f"""
  <script>
  // ---- Embedded Pyodide assets (base64) ----
  const PYODIDE_ASSETS_BY_PATH = {by_path_json};
  const PYODIDE_ASSETS_BY_NAME = {by_name_json};
  const PYODIDE_MODULE_FILE = {json.dumps(module_choice)};

  function b64ToBytes(b64) {{
    if (!b64) return new Uint8Array();
    const bin = atob(b64);
    const arr = new Uint8Array(bin.length);
    for (let i=0; i<bin.length; i++) arr[i] = bin.charCodeAt(i);
    return arr;
  }}

  function guessMime(name) {{
    const ext = (name.split('.').pop() || '').toLowerCase();
    if (ext === 'wasm') return 'application/wasm';
    if (ext === 'mjs' || ext === 'js') return 'text/javascript';
    if (ext === 'json') return 'application/json';
    if (ext === 'zip') return 'application/zip';
    if (ext === 'tar' || ext === 'bz2') return 'application/x-tar';
    if (ext === 'map') return 'application/json';
    if (ext === 'txt') return 'text/plain';
    return 'application/octet-stream';
  }}

  // Build a quick index of path suffixes for matching
  const _pathKeys = Object.keys(PYODIDE_ASSETS_BY_PATH).sort((a,b)=>a.length-b.length);

  function findAssetForUrl(url) {{
    try {{
      const u = new URL(url, 'https://x/');
      const path = u.pathname.replace(/^\\//,''); // strip leading slash
      const base = path.split('/').pop();
      if (PYODIDE_ASSETS_BY_NAME[base]) return [base, PYODIDE_ASSETS_BY_NAME[base]];
      // fallback: try by path suffix
      for (let i=_pathKeys.length-1; i>=0; i--) {{
        const key = _pathKeys[i];
        if (path.endsWith(key)) return [key, PYODIDE_ASSETS_BY_PATH[key]];
      }}
    }} catch (e) {{
      // url may be plain path or blob:... ; try basename
      const s = String(url);
      const base = s.split('?')[0].split('#')[0].split('/').pop();
      if (PYODIDE_ASSETS_BY_NAME[base]) return [base, PYODIDE_ASSETS_BY_NAME[base]];
    }}
    return null;
  }}

  // Patch fetch to serve embedded assets
  const _origFetch = window.fetch.bind(window);
  window.fetch = async function(input, init) {{
    const url = (typeof input === 'string') ? input : input.url;
    const hit = findAssetForUrl(url);
    if (hit) {{
      const [name, b64] = hit;
      const bytes = b64ToBytes(b64);
      const mime = guessMime(name);
      return new Response(bytes, {{
        status: 200,
        headers: {{ 'Content-Type': mime }}
      }});
    }}
    return _origFetch(input, init);
  }};
  </script>
"""

# Runtime JS: boot Pyodide from embedded bytes, then wire UI
runtime_js = f"""
  <script>
  (async () => {{
    const statusEl = document.getElementById('status');
    const setStatus = (t) => statusEl.textContent = t;

    // Build a Blob URL for the pyodide module (mjs or js)
    const modB64 = PYODIDE_ASSETS_BY_NAME[PYODIDE_MODULE_FILE];
    if (!modB64) {{
      setStatus('Pyodide module not found.');
      return;
    }}
    const modBytes = b64ToBytes(modB64);
    const modBlob = new Blob([modBytes], {{ type: 'text/javascript' }});
    const modUrl = URL.createObjectURL(modBlob);

    let loadPyodide;
    if (PYODIDE_MODULE_FILE.endsWith('.mjs')) {{
      // ES module
      const mod = await import(modUrl);
      loadPyodide = mod.loadPyodide;
    }} else {{
      // UMD: inject a <script> and read window.loadPyodide
      await new Promise((resolve, reject) => {{
        const s = document.createElement('script');
        s.src = modUrl;
        s.onload = resolve; s.onerror = reject;
        document.head.appendChild(s);
      }});
      loadPyodide = window.loadPyodide;
    }}

    setStatus('Initializing Python…');

    // indexURL won't actually be fetched (fetch is patched), but Pyodide uses it to build relative paths.
    const pyodide = await loadPyodide({{
      indexURL: "https://offline.local/pyodide/"  // fake; our fetch() interception serves bytes
    }});

    // Inject dictionary file into Pyodide FS
    const dictText = document.getElementById('english-dict').textContent || '';
    pyodide.FS.writeFile('en_dict.txt', dictText);

    // Run inline Python to define check function(s)
    const pyCode = document.getElementById('spell-checker').textContent;
    await pyodide.runPythonAsync(pyCode);

    // Wire UI
    const input = document.getElementById('input');
    const output = document.getElementById('output');
    const checkBtn = document.getElementById('checkBtn');
    const clearBtn = document.getElementById('clearBtn');

    clearBtn.addEventListener('click', () => {{
      input.value = '';
      output.innerHTML = '';
      setStatus('Cleared');
    }});

    // NOTE: adapt this call if your spell_checker.py uses a different API.
    checkBtn.addEventListener('click', async () => {{
      try {{
        setStatus('Checking…');
        pyodide.globals.set("input_text", input.value);
        const result = await pyodide.runPythonAsync(`
from js import input_text
res = check_text(input_text, 'en_dict.txt')
res
`);
        // Render: adjust to your function's real return shape
        if (Array.isArray(result)) {{
          output.innerHTML = result.map(x => '<mark>'+String(x)+'</mark>').join(' ');
        }} else {{
          output.textContent = String(result);
        }}
        setStatus('Done');
      }} catch (e) {{
        console.error(e);
        setStatus('Error: ' + e.message);
      }}
    }});

    setStatus('Ready');
    checkBtn.disabled = false;
  }})();

  // App JS (your UI logic/helpers) — optional merge
{app_js}
  </script>
"""

html_tail = """
</body>
</html>
"""

page = html_head + inline_blocks + build_pyodide_assets_js() + runtime_js + html_tail
OUT_FILE.write_text(page, encoding="utf-8")
print(f"[OK] Built: {OUT_FILE}")
print("     Double-click this file to run offline.")
