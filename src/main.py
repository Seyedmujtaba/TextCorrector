#--- writed by Seyedmujtaba Tabatabaee---#


# src/utils/main.py
import sys
import os
import argparse

# Import text_utils whether running as a module or a script
try:
    from .text_utils import to_lowercase, split_words, clean_spaces, join_words
except ImportError:
    # fallback for direct execution: python src/utils/main.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from text_utils import to_lowercase, split_words, clean_spaces, join_words


def process_text(text):
    """Run a simple normalization pipeline using utils functions"""
    text = clean_spaces(text)
    text = to_lowercase(text)
    words = split_words(text)
    normalized = join_words(words)
    return normalized, words


def read_input(args):
    """Read text from --text, --file, or STDIN"""
    if args.text is not None:
        return args.text
    if args.file is not None:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return input("Enter text: ")


def main():
    parser = argparse.ArgumentParser(description="Utility runner for text_utils.py")
    parser.add_argument("-t", "--text", help="Raw text to process")
    parser.add_argument("-f", "--file", help="Path to a text file")
    parser.add_argument("--show-words", action="store_true", help="Print tokenized words")
    args = parser.parse_args()

    raw = read_input(args)
    if not raw or raw.strip() == "":
        print("No input text.")
        sys.exit(1)

    normalized, words = process_text(raw)

    print("=== Normalized Text ===")
    print(normalized)

    print("\n=== Stats ===")
    print("Words:", len(words))
    print("Unique:", len(set(words)))

    if args.show_words:
        print("\n=== Tokens ===")
        for i, w in enumerate(words, 1):
            print(f"{i:>3}: {w}")


if __name__ == "__main__":
    main()
