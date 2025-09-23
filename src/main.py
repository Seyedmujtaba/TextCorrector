#--- writed by Seyedmujtaba Tabatabaee---#


# src/utils/main.py
import os
import sys
import argparse

# allow both: `python -m src.utils.main` and `python src/utils/main.py`
try:
    from .text_utils import to_lowercase, split_words, clean_spaces, join_words
    from .dict_loader import load_dictionary
except ImportError:
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    from text_utils import to_lowercase, split_words, clean_spaces, join_words
    from dict_loader import load_dictionary


def _default_dict_path():
    """libs/dictionary/en_dict.txt relative to project root"""
    utils_dir = os.path.dirname(os.path.abspath(__file__))       # .../src/utils
    project_root = os.path.abspath(os.path.join(utils_dir, "..", ".."))  # project root
    return os.path.join(project_root, "libs", "dictionary", "en_dict.txt")


def _read_input(args):
    """read from --text, --file, or STDIN"""
    if args.text is not None:
        return args.text
    if args.file is not None:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return input("Enter text: ")


def _normalize(text):
    """clean -> lowercase -> split -> join"""
    text = clean_spaces(text)
    text = to_lowercase(text)
    words = split_words(text)
    normalized = join_words(words)
    return normalized, words


def _unknown(words, dictionary):
    """tokens not present in dictionary"""
    if not dictionary:
        return []
    out = []
    for w in words:
        if w in dictionary:
            continue
        w2 = w.strip("'")
        if w2 and w2 in dictionary:
            continue
        out.append(w)
    return out


def main():
    parser = argparse.ArgumentParser(description="utils runner: normalize text + dictionary check")
    parser.add_argument("-t", "--text", help="raw text to process")
    parser.add_argument("-f", "--file", help="path to a text file")
    parser.add_argument("--dict", dest="dict_path", help="path to dictionary file")
    parser.add_argument("--show-words", action="store_true", help="print tokenized words")
    args = parser.parse_args()

    dict_path = args.dict_path or _default_dict_path()
    dictionary = load_dictionary(dict_path)

    if dictionary:
        print(f"Dictionary loaded: {len(dictionary)} words")
    else:
        print(f"Dictionary not loaded or empty: {dict_path}")

    raw = _read_input(args)
    if not raw or raw.strip() == "":
        print("No input text.")
        sys.exit(1)

    normalized, words = _normalize(raw)

    print("\n=== Normalized Text ===")
    print(normalized)

    print("\n=== Stats ===")
    print(f"Words: {len(words)}")
    print(f"Unique: {len(set(words))}")

    if dictionary:
        unk = _unknown(words, dictionary)
        print(f"Unknown: {len(unk)}")
        if unk:
            sample = sorted(set(unk))[:20]
            print(" -> " + ", ".join(sample))

    if args.show_words:
        print("\n=== Tokens ===")
        for i, w in enumerate(words, 1):
            print(f"{i:>3}: {w}")


if __name__ == "__main__":
    main()
