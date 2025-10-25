const $ = (sel) => document.querySelector(sel);
const escapeHTML = (s) => { const d=document.createElement('div'); d.textContent=s ?? ""; return d.innerHTML; };
const debounce = (fn, ms=300) => { let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; };
function normalizeToken(w) {
  return w.replace(/[\u2018\u2019]/g, "'").replace(/[\u2013\u2014]/g, "-").toLowerCase();
}
function preserveCase(orig, repl) {
  if (!repl) return orig;
  if (orig.toUpperCase() === orig) return repl.toUpperCase();
  if (orig[0] === orig[0].toUpperCase() && orig.slice(1).toLowerCase() === orig.slice(1)) return repl[0].toUpperCase() + repl.slice(1).toLowerCase();
  return repl;
}
function buildCorrected(text, suggestionsMap) {
  if (!text) return "";
  const re = /\b([A-Za-z]+(?:['\u2019\u2018][A-Za-z]+)?(?:[-\u2013\u2014][A-Za-z]+)*)\b/g;
  let out = [], last = 0, m;
  while ((m = re.exec(text))) {
    const token = m[0];
    const key = normalizeToken(token);
    const sug = suggestionsMap?.[key];
    let replacement = token;
    if (typeof sug === "string" && sug.length > 0) replacement = preserveCase(token, sug);
    out.push(text.slice(last, m.index), replacement);
    last = m.index + token.length;
  }
  out.push(text.slice(last));
  return out.join("");
}
function highlight(text, missSet) {
  if (!text) return "";
  const re = /\b([A-Za-z]+(?:['\u2019\u2018][A-Za-z]+)?(?:[-\u2013\u2014][A-Za-z]+)*)\b/g;
  const normalizeToken = (w) => w.replace(/[\u2018\u2019]/g, "'").replace(/[\u2013\u2014]/g, "-").toLowerCase();
  let out = [], last = 0, m;
  while ((m = re.exec(text))) {
    out.push(escapeHTML(text.slice(last, m.index)));
    const word = m[1];
    const key = normalizeToken(word);
    out.push(missSet.has(key) ? `<mark>${escapeHTML(word)}</mark>` : escapeHTML(word));
    last = m.index + word.length;
  }
  out.push(escapeHTML(text.slice(last)));
  return out.join('');
}
function showLoading(on = true) {
  const el = $("#loading");
  if (!el) return;
  if (on) el.classList.remove("d-none"); else el.classList.add("d-none");
}
function setErrorCount(n) {
  const el = $("#errorCount");
  if (el) el.textContent = Number.isFinite(n) ? `${n} issue${n === 1 ? "" : "s"}` : "—";
}
function setOutputHTML(html) {
  const el = $("#output");
  if (el) el.innerHTML = html;
}
(function initTheme() {
  const btn = $("#themeToggle");
  if (!btn) return;
  const saved = localStorage.getItem("tc-theme");
  if (saved === "dark") {
    document.body.classList.remove("light-theme");
    document.body.classList.add("dark-theme");
  }
  btn.addEventListener("click", () => {
    const dark = document.body.classList.toggle("dark-theme");
    if (dark) document.body.classList.remove("light-theme"); else document.body.classList.add("light-theme");
    localStorage.setItem("tc-theme", dark ? "dark" : "light");
  });
})();
(async function boot() {
  try {
    showLoading(true);
    await window.pyodideReady;
  } catch (e) {
    console.error("Pyodide failed to init:", e);
  } finally {
    showLoading(false);
  }
})();
async function runCheck() {
  const inputEl = $("#textInput");
  const text = inputEl?.value ?? "";
  if (!text.trim()) {
    setOutputHTML("");
    setErrorCount(0);
    return;
  }
  if (typeof window.checkText !== "function") {
    console.error("checkText is not ready yet.");
    setErrorCount(NaN);
    return;
  }
  showLoading(true);
  try {
    const res = await window.checkText(text);
    const miss = new Set(res?.misspelled ?? []);
    const suggestions = res?.suggestions ?? {};
    const corrected = res?.corrected || buildCorrected(text, suggestions);
    setOutputHTML(escapeHTML(corrected));
    setErrorCount(miss.size);
  } catch (e) {
    console.error(e);
    setErrorCount(NaN);
  } finally {
    showLoading(false);
  }
}
function clearAll() {
  const inputEl = $("#textInput");
  if (inputEl) inputEl.value = "";
  setOutputHTML("");
  setErrorCount(0);
}
async function copyOutput() {
  try {
    const text = $("#output")?.textContent ?? "";
    await navigator.clipboard.writeText(text);
    const toastEl = $("#copyToast");
    if (toastEl && window.bootstrap?.Toast) {
      const t = new bootstrap.Toast(toastEl);
      t.show();
    }
  } catch (e) {
    console.error("Copy failed", e);
  }
}
function downloadOutput() {
  const text = $("#output")?.textContent ?? "";
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "textcorrector_output.txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
$("#checkBtn")?.addEventListener("click", runCheck);
$("#clearBtn")?.addEventListener("click", clearAll);
$("#copyBtn")?.addEventListener("click", copyOutput);
$("#downloadBtn")?.addEventListener("click", downloadOutput);