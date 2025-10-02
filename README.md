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

- HTML, CSS, JavaScript (frontend)
- Python (via Pyodide, runs in-browser)
- Built-in English dictionary

## Usage

1. Clone or download the repository.
2. Open `static/index.html` in any modern browser (double-click the file). It runs offline from your filesystem; no server is required.
3. Enter English text in the input box.
4. Click the check button to see highlighted errors and suggestions.

## Project Structure

TextCorrector/
├── README.md
├── libs/ # Additional resources (e.g., dictionaries)
├── scripts/ # Setup scripts (e.g., Pyodide bootstrap)
│ └── pyodide_setup.js
├── src/ # Python source code (spell checker logic)
│ └── spell_checker.py
└── static/ # Web UI files
├── index.html # Main entry point
├── style.css # Stylesheet
└── app.js # Frontend logic

## Build & Releases

The project can be used directly by opening `static/index.html`, but for end-users we also provide a **single-file offline build**.

- Developers: run `python3 build.py` to generate the bundled file at `dist/text-corrector.html`.
- End-users: simply download the latest release from [Releases](../../releases) and double-click `text-corrector.html` to run it offline in your browser.

## Future Improvements

- Support for multiple languages
- User-defined custom dictionaries
- Enhanced UI/UX with better inline suggestions

---

Developers:

- Seyedmujtaba Tabatabaee
- Ayla Rasouli
- Negin Khoshdel
