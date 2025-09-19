#!/usr/bin/env python3
"""
Builds an English dictionary file (~200,000 unique words) for TextCorrector
from reputable open-source sources (SCOWL + optional fallback).

Output: libs/dictionary/en_dict.txt

Usage examples:
    python build_en_dict.py --target 200000 --dialects both --include-names --include-contractions
    python build_en_dict.py --target 200000 --dialects us
    python build_en_dict.py --target 200000 --dialects gb --no-names --no-contractions

Notes:
- Requires internet access on first run to download source lists.
- Sources:
  * SCOWL 2020.12.07 (Kevin Atkinson): https://sourceforge.net/projects/wordlist/files/SCOWL/2020.12.07/
  * (fallback) dwyl/english-words (Unlicense): words_alpha.txt
"""

from __future__ import annotations
import argparse
import io
import os
import re
import sys
import zipfile
import unicodedata
from pathlib import Path
from typing import Iterable, Set, List, Tuple

try:
    import requests
except ImportError as e:
    print("This script needs the 'requests' package. Install it with:\n    pip install requests\n", file=sys.stderr)
    raise

SCOWL_ZIP_URL = "https://sourceforge.net/projects/wordlist/files/SCOWL/2020.12.07/scowl-2020.12.07.zip/download"
# Fallback list of purely alphabetic words
DWYL_WORDS_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"

BASE_SIZES = [10, 20, 35, 40, 50, 55, 60, 70]
EXTRA_SIZES = [80]  # used only if we still haven't reached the target
DEFAULT_TARGET = 200_000

DIALECTS = {
    "us": ["english", "american"],
    "gb": ["english", "british", "british_z"],
    "both": ["english", "american", "british", "british_z"],
}

SUBCATS_BASE = ["words"]
SUBCATS_OPTIONAL = {
    "names": "proper-names",
    "contractions": "contractions",
}

ALPHA_ONLY_RE = re.compile(r"^[A-Za-z]+$")


def download(url: str, timeout: int = 60) -> bytes:
    headers = {"User-Agent": "TextCorrector-DictBuilder/1.0"}
    with requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True) as r:
        r.raise_for_status()
        return r.content


def strip_diacritics(s: str) -> str:
    # Normalize to NFKD and remove combining marks
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_token(token: str, diacritics: str = "strip", alpha_only: bool = True) -> str | None:
    t = token.strip()
    if not t:
        return None
    # SCOWL files are in ISO-8859-1; decoding is handled when reading
    # Lowercase all terms for matching
    t = t.lower()
    if diacritics == "strip":
        t = strip_diacritics(t)
    # Filter forms you probably don't want in a simple spell-checker
    if alpha_only and not ALPHA_ONLY_RE.match(t):
        return None
    # Very short tokens are usually not useful (keep 'a' and 'i' though)
    if len(t) == 1 and t not in {"a", "i"}:
        return None
    return t


def collect_from_scowl(zdata: bytes,
                       dialects: List[str],
                       include_names: bool,
                       include_contractions: bool,
                       target: int,
                       diacritics: str,
                       alpha_only: bool) -> Tuple[Set[str], List[str]]:
    """Parse SCOWL zip and collect words according to filters. Returns (words, debug_paths)."""
    debug_paths: List[str] = []
    words: Set[str] = set()
    with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
        names = zf.namelist()
        # Find files under final/ matching our categories
        def want(path: str) -> bool:
            return "/final/" in path and not path.endswith("/")

        final_files = [n for n in names if want(n)]
        chosen_subcats = set(SUBCATS_BASE)
        if include_names:
            chosen_subcats.add(SUBCATS_OPTIONAL["names"])
        if include_contractions:
            chosen_subcats.add(SUBCATS_OPTIONAL["contractions"])

        chosen_cats = set()
        for d in dialects:
            chosen_cats.update(DIALECTS[d])

        chosen_sizes = set(BASE_SIZES)

        def parse_one(path: str) -> Iterable[str]:
            # Read raw bytes and decode as latin-1 per SCOWL README
            raw = zf.read(path)
            text = raw.decode("latin-1", errors="ignore")
            for line in text.splitlines():
                if not line or line.startswith("#"):
                    continue
                yield line.strip()

        # First pass: sizes up to 70
        for path in final_files:
            base_name = path.split("/")[-1]  # english-words.70, british-words.50, etc.
            try:
                cat, rest = base_name.split("-", 1)
                subcat, size_str = rest.split(".")
                size = int(size_str)
            except Exception:
                continue
            if cat not in chosen_cats or subcat not in chosen_subcats or size not in chosen_sizes:
                continue

            debug_paths.append(base_name)
            for tok in parse_one(path):
                nt = normalize_token(tok, diacritics=diacritics, alpha_only=alpha_only)
                if nt:
                    words.add(nt)

        # If still short of target, top up from size 80 "words" only (no names/contractions)
        if len(words) < target:
            for path in final_files:
                base_name = path.split("/")[-1]
                try:
                    cat, rest = base_name.split("-", 1)
                    subcat, size_str = rest.split(".")
                    size = int(size_str)
                except Exception:
                    continue
                if subcat != "words" or size not in EXTRA_SIZES:
                    continue
                if cat not in chosen_cats:
                    continue
                debug_paths.append(base_name)
                for tok in normalize_iter(parse_one(path), diacritics=diacritics, alpha_only=alpha_only):
                    if len(words) >= target:
                        break
                    words.add(tok)
                if len(words) >= target:
                    break

    return words, debug_paths


def normalize_iter(tokens: Iterable[str], diacritics: str, alpha_only: bool) -> Iterable[str]:
    for t in tokens:
        nt = normalize_token(t, diacritics=diacritics, alpha_only=alpha_only)
        if nt:
            yield nt


def topup_from_dwyl(existing: Set[str], target: int, diacritics: str, alpha_only: bool) -> Tuple[Set[str], int]:
    """Add more words from DWYL list if still below target. Returns (set, added_count)."""
    try:
        raw = download(DWYL_WORDS_URL)
    except Exception as e:
        print(f"[warn] Could not download DWYL list: {e}")
        return existing, 0
    added = 0
    text = raw.decode("utf-8", errors="ignore")
    for line in text.splitlines():
        if len(existing) >= target:
            break
        nt = normalize_token(line, diacritics=diacritics, alpha_only=alpha_only)
        if nt and nt not in existing:
            existing.add(nt)
            added += 1
    return existing, added


def main():
    ap = argparse.ArgumentParser(description="Build ~200k English dictionary for TextCorrector (SCOWL-based).")
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET, help="Approximate target size (default: 200000)")
    ap.add_argument("--dialects", nargs="+", choices=list(DIALECTS.keys()), default=["both"],
                    help="Dialects to include (us, gb, both). Default: both")
    ap.add_argument("--include-names", dest="names", action="store_true", default=True, help="Include proper names")
    ap.add_argument("--no-names", dest="names", action="store_false", help="Exclude proper names")
    ap.add_argument("--include-contractions", dest="contractions", action="store_true", default=False, help="Include contractions like don't, it's")
    ap.add_argument("--no-contractions", dest="contractions", action="store_false", help="Exclude contractions (default)")
    ap.add_argument("--diacritics", choices=["strip", "keep"], default="strip", help="Handle accents (default: strip)")
    ap.add_argument("--alpha-only", action="store_true", default=True, help="Keep only [A-Za-z]+ tokens (default: True)")
    ap.add_argument("--output", type=str, default="libs/dictionary/en_dict.txt", help="Output path")
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("[1/3] Downloading SCOWL zip ...")
    zdata = download(SCOWL_ZIP_URL)

    print("[2/3] Collecting words from SCOWL ...")
    words, used_files = collect_from_scowl(
        zdata=zdata,
        dialects=args.dialects,
        include_names=args.names,
        include_contractions=args.contractions,
        target=args.target,
        diacritics=args.diacritics,
        alpha_only=args.alpha_only,
    )
    print(f"    Included SCOWL files: {len(used_files)}")
    print("    Examples:", ", ".join(sorted(set(used_files))[:6]), "...")
    print(f"    Collected {len(words):,} unique tokens from SCOWL.")

    if len(words) < args.target:
        print(f"[2b] Topping up from DWYL list to reach ~{args.target:,} ...")
        words, added = topup_from_dwyl(words, args.target, args.diacritics, args.alpha_only)
        print(f"    Added {added:,} tokens from DWYL. New total: {len(words):,}")

    print("[3/3] Writing output ...")
    final = sorted(words)
    # If still above target (rare), trim deterministically
    if len(final) > args.target:
        final = final[:args.target]
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for w in final:
            f.write(w + "\n")

    print(f"Done ✅  Wrote {len(final):,} words to {out_path}")

if __name__ == "__main__":
    main()
