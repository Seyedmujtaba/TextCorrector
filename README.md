# TextCorrector  

**TextCorrector** is a simple web-based spell checker for English texts that runs directly in the browser using Python (via Pyodide). It requires no server or installation.  

## Features  
- Runs directly in the browser  
- Detects and highlights spelling mistakes  
- Provides correction suggestions  
- Clear button to reset input/output boxes  
- Supports Dark Mode and Light Mode  
- Simple UI with smooth animations  

## Tech Stack  
- **Frontend:** HTML, CSS, JavaScript  
- **Backend:** Python (Pyodide)  
- **Libraries:** spellchecker with built-in English dictionary  

## Usage  
1. Clone or download the repository.  
2. Open `index.html` in any modern browser.  
3. Enter English text in the input box.  
4. Click the check button to see highlighted errors and suggestions.  

## Project Structure  

TextCorrector/
│
├── README.md
│
├── src/ # Source code
│ ├── frontend/ # Frontend (UI)
│ │ ├── index.html # Main HTML file
│ │ ├── style.css # Stylesheet
│ │ └── app.js # Frontend logic
│ │
│ ├── backend/ # Backend logic (Python via Pyodide)
│ │ ├── spell_checker.py # Core spell checking functions
│ │ └── init.py # Module initializer
│ │
│ └── utils/ # Utility functions
│ ├── text_utils.py # Text processing helpers
│ ├── dict_loader.py # Dictionary loader
│ ├── main.py # Entry point for utilities
│ └── init.py # Module initializer
│
├── libs/ # Libraries and dependencies
│ ├── dictionary/
│ │ └── en_dict.txt # English dictionary file
│ │
│ ├── spellchecker/
│ │ └── requirements.txt # Python dependencies
│ │
│ └── pyodide/
│ └── pyodide_setup.js # Pyodide setup script
│
├── static/ # Static assets
│ ├── logo.png # Project logo
│ └── theme.css # Theme styles (Dark/Light)




## Future Improvements  
- Support for multiple languages  
- User-defined custom dictionaries  
- Enhanced UI/UX with better inline suggestions  

---

👤 Developers:
 - Seyedmujtaba Tabatabaee
 - Ayla Rasouli
 - Negin Khoshdel

   
