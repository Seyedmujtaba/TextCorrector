def load_dictionary(file_path):

    words = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                word = line.strip().lower()
                if word:
                    words.add(word)
                    
    except FileNotFoundError:
        print(f"Dictionary file not found: {file_path}")
    except Exception as e:
        print(f"Error loading dictionary file; {e}")

    return words


