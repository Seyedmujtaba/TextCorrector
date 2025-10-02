// src/frontend/app.js

// ---------- helpers ----------
const $ = (sel) => document.querySelector(sel);
const escapeHTML = (s) => { const d=document.createElement('div'); d.textContent=s ?? ""; return d.innerHTML; };
const debounce = (fn, ms=300) => { let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; };

// highlight misspelled words with <mark> (XSS-safe: escapes non-word chunks too)
function highlight(text, missSet) {
  if (!text) return "";
  const re = /\b([A-Za-z]+(?:'[A-Za-z]+)?(?:-[A-Za-z]+)*)\b/g;
  let out = [], last = 0, m;
  while ((m = re.exec(text))) {
    // escape everything before the word
    out.push(escapeHTML(text.slice(last, m.index)));
    const word = m[1];
    const low = word.toLowerCase();
    // escape the word itself, wrap if misspelled
    out.push(missSet.has(low) ? `<mark>${escapeHTML(word)}</mark>` : escapeHTML(word));
    last = m.index + word.length;
  }
  // tail
  out.push(escapeHTML(text.slice(last)));
  return out.join('');
}

function showLoading(on=true){
  const el = $("#loading");
  if (!el) return;
  if (on) el.classList.remove("d-none"); else el.classList.add("d-none");
}
function setErrorCount(n){
  const el = $("#errorCount");
  if (el) el.textContent = Number.isFinite(n) ? `${n} issue${n===1?"":"s"}` : "—";
}
function setOutputHTML(html){
  const el = $("#output");
  if (el) el.innerHTML = html;
}

// ---------- theme (persist) ----------
(function initTheme(){
  const btn = $("#themeToggle");
  if (!btn) return;
  const saved = localStorage.getItem("tc-theme");
  if (saved === "dark") {
    document.body.classList.remove("light-theme");
    document.body.classList.add("dark-theme");
  }
  btn.addEventListener("click", () => {
    const dark = document.body.classList.toggle("dark-theme");
    if (dark) document.body.classList.remove("light-theme");
    else document.body.classList.add("light-theme");
    localStorage.setItem("tc-theme", dark ? "dark" : "light");
  });
})();

// ---------- pyodide boot ----------
(async function boot(){
  try {
    showLoading(true);
    await window.pyodideReady; // from pyodide_setup.js
  } catch (e) {
    console.error("Pyodide failed to init:", e);
  } finally {
    showLoading(false);
  }
})();

// ---------- actions ----------
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
    const miss = Array.from(new Set((res?.misspelled ?? []).map(w=>w.toLowerCase())));
    const missSet = new Set(miss);

    setOutputHTML(highlight(text, missSet));
    setErrorCount(miss.length);
  } catch (e) {
    console.error(e);
    setErrorCount(NaN);
  } finally {
    showLoading(false);
  }
}

function clearAll(){
  const inputEl = $("#textInput");
  if (inputEl) inputEl.value = "";
  setOutputHTML("");
  setErrorCount(0);
}

async function copyOutput(){
  try {
    const text = $("#output")?.textContent ?? "";
    await navigator.clipboard.writeText(text);
    // show toast if exists (Bootstrap)
    const toastEl = $("#copyToast");
    if (toastEl && window.bootstrap?.Toast) {
      const t = new bootstrap.Toast(toastEl);
      t.show();
    }
  } catch (e) {
    console.error("Copy failed", e);
  }
}

function downloadOutput(){
  const text = $("#output")?.textContent ?? "";
  const blob = new Blob([text], {type:"text/plain;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "textcorrector_output.txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---------- wire UI ----------
$("#checkBtn")?.addEventListener("click", runCheck);
$("#clearBtn")?.addEventListener("click", clearAll);
$("#copyBtn")?.addEventListener("click", copyOutput);
$("#downloadBtn")?.addEventListener("click", downloadOutput);

// optional: live check while typing (debounced)
$("#textInput")?.addEventListener("input", debounce(runCheck, 450));
