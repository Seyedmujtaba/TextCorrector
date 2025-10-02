# TextCorrector

TextCorrector is a simple web-based spell checker for English texts that runs directly in the browser using Python (via Pyodide). It requires no server or installation.

## Features

- Runs directly in the browser
- Detects and highlights spelling mistakes
- Provides correction suggestions
- Clear button to reset input/output boxes
- Supports Dark Mode and Light Mode
- Simple UI with smooth animations

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python (Pyodide)
- Libraries: spellchecker with built-in English dictionary

## Usage

1. Clone or download the repository.
2. Open `static/index.html` in any modern browser (double-click the file). It runs offline from your filesystem; no server is required.
3. Enter English text in the input box.
4. Click the check button to see highlighted errors and suggestions.

## Project Structure

TextCorrector/
├── README.md
├── libs/ # Libraries and dependencies
├── scripts/ # Setup scripts (e.g., Pyodide bootstrap)
│ └── pyodide_setup.js
├── src/ # Python source code (spell checker logic, etc.)
│ └── spell_checker.py
└── static/ # Static assets for the web UI
├── index.html # Main HTML file (open this)
├── style.css # Stylesheet
└── app.js # Frontend logic

## Future Improvements

- Support for multiple languages
- User-defined custom dictionaries
- Enhanced UI/UX with better inline suggestions

---

Developers:

- Seyedmujtaba Tabatabaee
- Ayla Rasouli
- Negin Khoshdel
