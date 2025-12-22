# spell_checker.py
#written by Ayla Rasouli
import os
import sys
import argparse
import re
from spellchecker import SpellChecker
from .utils.dict_loader import load_dictionary
from .utils.text_utils import to_lowercase, split_words, clean_spaces, join_words


def _default_dict_path():
    backend_dir = os.path.dirname(os.path.abspath(__file__)) 
    project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))
    return os.path.join(project_root, "libs", "dictionary", "en_dict.txt")


def fix_special_cases(text):
    changes = []
    words = text.split()

    fixed_words = []
    for word in words:
        fixed = word

        fixed = re.sub(r"[‘’]{2,}", "’", fixed)
        fixed = re.sub(r"[']{2,}", "’", fixed)

        if fixed != word:
            changes.append((word, fixed))

        fixed_words.append(fixed)

    fixed_text = " ".join(fixed_words)
    return fixed_text, changes


def correct_text(text, dict_path):
    text, quote_fixes = fix_special_cases(text)

    text = clean_spaces(text)
    text = to_lowercase(text)
    words = split_words(text)

    dictionary = load_dictionary(dict_path)

    spell = SpellChecker()
    spell.word_frequency.load_words(dictionary)
    misspelled = spell.unknown(words)

    corrected_text = []
    spelling_fixes = []

    for word in words:
        if word in misspelled:
            corrected_word = spell.correction(word)
            if corrected_word and corrected_word != word:
                spelling_fixes.append((word, corrected_word))
                corrected_text.append(corrected_word)
            else:
                corrected_text.append(word)
        else:
            corrected_text.append(word)

    final_text = " ".join(corrected_text)
    all_fixes = quote_fixes + spelling_fixes

    return final_text, len(misspelled), list(misspelled), all_fixes


def _read_input(args):
    if args.text is not None:
        return args.text
    if args.file is not None:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return input("Enter text: ")


def main():
    parser = argparse.ArgumentParser(description="Spell checker: normalize text + dictionary check")
    parser.add_argument("-t", "--text", help="Raw text to process")
    parser.add_argument("-f", "--file", help="Path to a text file")
    parser.add_argument("--dict", dest="dict_path", help="Path to dictionary file")
    parser.add_argument("--show-words", action="store_true", help="Print tokenized words")
    args = parser.parse_args()

    dict_path = args.dict_path or _default_dict_path()
    raw = _read_input(args)

    if not raw or raw.strip() == "":
        print("No input text.")
        sys.exit(1)

    corrected_text, mistake_count, misspelled, all_fixes = correct_text(raw, dict_path)

    print("\n Corrected Text ")
    print(corrected_text)

    print("\n Stats ")
    print(f"Number of words: {len(raw.split())}")
    print(f"Number of mistakes: {mistake_count}")

    if all_fixes:
        print("\n Corrections ")
        for wrong, fixed in all_fixes:
            print(f"{wrong} → {fixed}")

    if args.show_words:
        print("\n Tokens ")
        for i, w in enumerate(split_words(to_lowercase(clean_spaces(raw))), 1):
            print(f"{i:>3}: {w}")


if __name__ == "__main__":
    main()

