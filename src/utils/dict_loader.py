def load_dictionary(file_path):

    """
    Reads a dictionary file and returns a set of words.
    
    Args:
        file_path (str): Path to the dictionary text file.

    Returns:
        set: A set containing all words from the dictionary file in lowercase.
    """

    #Create an empty set to store words
    words = set()
    
    try:
        #Open the dictionary file with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                #Remove leading/trailing whitespaces and convert to lowercase
                word = line.strip().lower()
                if word: #If the line was not empty
                words.add(word)
    
    except FileNotFoundError:
        #Handle the case where the file does not exist
        print(f"Dictionary file not found: {file_path}")

    except Exception as e:
        #Handle any other exceptions that might occur
        print(f"Error loading dictionary file: {e}")

    return words