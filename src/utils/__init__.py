# --- Written by Seyedmujtaba Tabatabaee ---
# src/utils/__init__.py
"""
Utilities package for text normalization and dictionary loading.
Exposes a clean public API for the rest of the project.
"""

from .text_utils import to_lowercase, split_words, clean_spaces, join_words
from .dict_loader import load_dictionary

__all__ = [
    "to_lowercase",
    "split_words",
    "clean_spaces",
    "join_words",
    "load_dictionary",
]

__version__ = "0.1.0"
