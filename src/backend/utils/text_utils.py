import re

def to_lowercase(text):
    return text.lower()

def split_words(text):
    text = re.sub(r'[^a-zA-Z\s\']', ' ', text)
    words = text.split()
    return words

def clean_spaces(text):
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def join_words(words):
    return ' '.join(words)
