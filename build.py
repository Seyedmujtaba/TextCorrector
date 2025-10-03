pyodide.FS.writeFile('/app/utils/init.py', (document.getElementById('py-utils-init')?.textContent) || '');
  pyodide.FS.writeFile('/app/utils/dict_loader.py', (document.getElementById('py-utils-dict-loader')?.textContent) || '');
  pyodide.FS.writeFile('/app/utils/text_utils.py', (document.getElementById('py-utils-text-utils')?.textContent) || '');
  pyodide.FS.writeFile('/app/spell_checker.py', (document.getElementById('py-backend-spell-checker')?.textContent) || '');

  await pyodide.runPythonAsync(
import sys
if "/app" not in sys.path:
    sys.path.insert(0, "/app")
import spell_checker
);

  window.checkText = async (text) => {{
    pyodide.globals.set("js_text", text || "");
    const pyRes = await pyodide.runPythonAsync(
from js import js_text
import spell_checker
ct, mc, miss, fixes = spell_checker.correct_text(js_text, "/app/en_dict.txt")
{{ "corrected_text": ct, "mistake_count": int(mc), "misspelled": list(miss), "all_fixes": [tuple(p) for p in fixes] }}
);
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

    # Optional logo → data URI
    if logo_bytes:
        logo_datauri = "data:image/png;base64," + b64(logo_bytes)
        page = re.sub(r'(<img[^>]+src=["\'])[^\']*logo\\.png(["\'])',
                      rf'\\1{logo_datauri}\\2', page, flags=re.I|re.S)

    # Aggressive remove ALL external CSS <link ... .css ...>
    before = len(page)
    page = re.sub(r'<link[^>]*href=["\'][^"\']*\\.css[^"\']*["\'][^>]*\/?>(?:\\s*)', '', page, flags=re.I|re.S)
    print("[LOG] removed CSS tags bytes:", before - len(page))

    # Remove ANY external script tags that could load app/pyodide (CDN or local paths)
    before = len(page)
    page = re.sub(r'<script[^>]*src=["\'][^"\']*(?:app\\.js|pyodide[^"\']*|cdn\\.jsdelivr[^"\']*|googleapis[^"\']*)[^"\']*["\'][^>]*>(?:\\s*</script>)?', '', page, flags=re.I|re.S)
    print("[LOG] removed external JS tags bytes:", before - len(page))

    # inline <style> before </head>
    m = re.search(r'</head>', page, flags=re.I|re.S)
    if m:
        page = page[:m.start()] + (f"{inline_style}\n" if inline_style else "") + page[m.start():]
        print("[LOG] inlined <style>")
    else:
        page = (inline_style or "") + page
        print("[LOG] no </head> found; prepended <style>")

    # inject before </body>
    injections = "\n".join([inline_dict, inline_utils, inline_py, assets_js, runtime_js, f"<script>\n{app_js}\n</script>"])
    m = re.search(r'</body>', page, flags=re.I|re.S)
    if m:
        page = page[:m.start()] + injections + page[m.start():]
        print("[LOG] injected scripts before </body>")
    else:
        page = page + injections
        print("[LOG] no </body> found; appended scripts")

    OUT_FILE.write_text(page, encoding="utf-8")
    print(f"[OK] Built: {OUT_FILE}")

except SystemExit:
    raise
except Exception as e:
    print("[EXCEPTION]", e)
    traceback.print_exc()
    sys.exit(1)
