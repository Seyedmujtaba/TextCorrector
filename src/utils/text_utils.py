import re

def to_lowercase(text):
    """Convert all letters to lowercase"""
    return text.lower()

def split_words(text):
    """Separating words from text and removing invalid characters"""
    text = re.sub(r'[^a-zA-Z\s\']', ' ', text)
    words = text.split()
    return words

def clean_spaces(text):
    """Remove extra spaces at the beginning and end of text and convert extra spaces to single spaces"""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def join_words(words):
    """Combine a list of words into a single text with spaces"""
    return ' '.join(words)

