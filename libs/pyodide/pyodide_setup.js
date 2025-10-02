//--- writed by Seyedmujtaba Tabatabaee---//

// libs/pyodide/pyodide_setup.js
// Boot Pyodide and expose checkText(text) -> {misspelled:[], suggestions:{}}

window.pyodideReady = (async () => {
  if (typeof loadPyodide !== "function") {
    throw new Error("Pyodide script not loaded. Check the CDN <script> tag in index.html.");
  }

  // 1) Load Pyodide runtime
  const pyodide = await loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.1/full/"
  });

  // 2) Install pyspellchecker (pure-Python) via micropip
  await pyodide.loadPackage("micropip");
  await pyodide.runPythonAsync(`
import micropip
await micropip.install("pyspellchecker")
`);

  // 3) Define Python-side logic: tokenize + spellcheck + JSON bridge
  await pyodide.runPythonAsync(`
from spellchecker import SpellChecker
import re, json

spell = SpellChecker()

# covers: can't, O'Reilly, co-operate
TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?(?:-[A-Za-z]+)*")

def check_text(text: str):
    words = TOKEN_RE.findall(text or "")
    lowers = [w.lower() for w in words]
    miss = spell.unknown(lowers)
    suggestions = {w: (next(iter(spell.candidates(w)), None)) for w in miss}
    return {"misspelled": list(miss), "suggestions": suggestions}

def check_text_json(text: str):
    return json.dumps(check_text(text))
`);

  // 4) JS wrapper
  async function checkText(text) {
    const pyFunc = pyodide.globals.get("check_text_json");
    try {
      const jsonStr = pyFunc(text);
      return JSON.parse(jsonStr);
    } finally {
      pyFunc.destroy();
    }
  }

  // expose
  window.pyodide = pyodide;
  window.checkText = checkText;
  return true;
})();

