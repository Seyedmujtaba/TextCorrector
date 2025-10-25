window.pyodideReady = (async () => {
  if (typeof loadPyodide !== "function") throw new Error("Pyodide script not loaded.");
  const pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.1/full/" });
  await pyodide.loadPackage("micropip");
  await pyodide.runPythonAsync(`
import micropip
await micropip.install("pyspellchecker")
`);
  await pyodide.runPythonAsync(`
from spellchecker import SpellChecker
import re, json, unicodedata
spell = SpellChecker()
SMART_MAP = {'\\u2018': "'", '\\u2019': "'", '\\u201C': '"', '\\u201D': '"', '\\u2013': '-', '\\u2014': '-', '\\u2026': '...', '\\u00A0': ' '}
ZERO_WIDTH_RE = re.compile('[\\u200B\\u200C\\u200D\\u2060]')
def normalize_text(s: str) -> str:
    if not s: return ''
    s = unicodedata.normalize('NFKC', s)
    for k, v in SMART_MAP.items(): s = s.replace(k, v)
    s = re.sub(r"('{2,})", "'", s)
    s = re.sub(r'("{2,})', '"', s)
    s = ZERO_WIDTH_RE.sub('', s)
    s = re.sub(r'\\s+', ' ', s).strip()
    return s
TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?(?:-[A-Za-z]+)*")
def check_text(text: str):
    norm = normalize_text(text or '')
    words = TOKEN_RE.findall(norm)
    lowers = [w.lower() for w in words]
    miss = spell.unknown(lowers)
    def _suggestion_for(w: str):
        try:
            corr = None
            try: corr = spell.correction(w)
            except Exception: corr = None
            if corr and corr != w: return corr
            cands = spell.candidates(w) or set()
            for c in cands:
                if c != w: return c
            return None
        except Exception: return None
    suggestions = {w: _suggestion_for(w) for w in miss}
    def apply_suggestions(text: str, suggs: dict):
        def repl(match):
            word = match.group(0)
            lw = word.lower()
            if lw in suggs and suggs[lw]:
                repl_word = suggs[lw]
                if word.isupper(): return repl_word.upper()
                elif word[0].isupper(): return repl_word.capitalize()
                else: return repl_word
            return word
        return re.sub(TOKEN_RE, repl, text)
    corrected = apply_suggestions(norm, suggestions)
    return {"misspelled": list(miss), "suggestions": suggestions, "corrected": corrected}
def check_text_json(text: str):
    return json.dumps(check_text(text))
`);
  async function checkText(text) {
    const pyFunc = pyodide.globals.get("check_text_json");
    try {
      const jsonStr = pyFunc(text);
      return JSON.parse(jsonStr);
    } finally {
      pyFunc.destroy();
    }
  }
  window.pyodide = pyodide;
  window.checkText = checkText;
  return true;
})();