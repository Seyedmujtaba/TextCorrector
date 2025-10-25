#--- written by Seyedmujtaba Tabatabaee---#
# src/utils/__init__.py

from .utils.text_utils import to_lowercase, split_words, clean_spaces, join_words
from .utils.dict_loader import load_dictionary

__all__ = [
    "to_lowercase",
    "split_words",
    "clean_spaces",
    "join_words",
    "load_dictionary",
]
