const els = {
  themeToggle: document.getElementById("themeToggle"),
  input: document.getElementById("textInput"),
  output: document.getElementById("output"),
  checkBtn: document.getElementById("checkBtn"),
  clearBtn: document.getElementById("clearBtn"),
  copyBtn: document.getElementById("copyBtn"),
  downloadBtn: document.getElementById("downloadBtn"),
  errorCount: document.getElementById("errorCount"),
  loading: document.getElementById("loading"),
};

let lastCorrectedText = "";

// Theme toggle
els.themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("dark-theme");
  document.body.classList.toggle("light-theme");
  const icon = els.themeToggle.querySelector(".material-symbols-rounded");
  if (document.body.classList.contains("dark-theme")) {
    icon.textContent = "light_mode";
  } else {
    icon.textContent = "dark_mode";
  }
});

// Busy state
function setBusy(busy) {
  [els.checkBtn, els.clearBtn, els.copyBtn, els.downloadBtn].forEach(b => b.disabled = busy);
  els.loading.classList.toggle("d-none", !busy);
}

// Normalize errors
function normalizeErrors(errors) {
  if (!errors) return [];
  if (Array.isArray(errors) && typeof errors[0] === "string") {
    return errors.map(w => ({ word: w, suggestions: [] }));
  }
  if (Array.isArray(errors) && typeof errors[0] === "object") {
    return errors.map(e => ({ word: e.word || "", suggestions: e.suggestions || [] }));
  }
  return [];
}

// Render output
function renderCorrected(corrected, errors) {
  lastCorrectedText = corrected || "";
  const wrongSet = new Set(errors.map(e => e.word.toLowerCase()));
  const suggestionMap = {};
  errors.forEach(e => { suggestionMap[e.word.toLowerCase()] = e.suggestions; });

  const tokens = corrected.split(/(\s+)/);
  const html = tokens.map(tok => {
    if (!tok.trim()) return tok;
    const key = tok.toLowerCase();
    if (wrongSet.has(key)) {
      const sugg = suggestionMap[key] || [];
      const title = sugg.length ? `Suggestions: ${sugg.join(", ")}` : "Possible error";
      return `<span class="highlight-wrong" data-bs-toggle="tooltip" title="${title}">${tok}</span>`;
    }
    return tok;
  }).join("");

  els.output.innerHTML = html;
  els.errorCount.textContent = errors.length > 0 ? `${errors.length} error(s)` : "No errors found";

  // init Bootstrap tooltips
  const triggerList = [].slice.call(els.output.querySelectorAll('[data-bs-toggle="tooltip"]'));
  triggerList.map(el => new bootstrap.Tooltip(el));
}

// Clear
els.clearBtn.addEventListener("click", () => {
  els.input.value = "";
  els.output.innerHTML = "";
  els.errorCount.textContent = "—";
  lastCorrectedText = "";
});

// Check
els.checkBtn.addEventListener("click", async () => {
  const text = els.input.value.trim();
  if (!text) {
    els.output.innerHTML = `<p class="text-danger">Please enter some text!</p>`;
    return;
  }
  try {
    setBusy(true);
    const res = await fetch("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    const corrected = data.corrected || text;
    const errors = normalizeErrors(data.errors);
    renderCorrected(corrected, errors);
  } catch (e) {
    els.output.innerHTML = `<p class="text-danger">Error: ${e.message}</p>`;
  } finally {
    setBusy(false);
  }
});

// Copy with toast
const copyToast = new bootstrap.Toast(document.getElementById("copyToast"));
els.copyBtn.addEventListener("click", async () => {
  const text = lastCorrectedText || els.input.value || "";
  if (!text) return;
  await navigator.clipboard.writeText(text);
  copyToast.show();
});

// Download
els.downloadBtn.addEventListener("click", () => {
  const text = lastCorrectedText || els.input.value || "";
  if (!text) return;
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "textcorrector.txt";
  a.click();
  URL.revokeObjectURL(url);
});
