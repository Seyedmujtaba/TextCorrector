# TextCorrector

TextCorrector is a simple web-based spell checker for English texts that runs directly in the browser using Python (via Pyodide). It requires no server or installation.

## Features

- Runs locally on your computer — no internet or installation required  
- Detects and highlights spelling mistakes in English text  
- Provides accurate correction suggestions  
- Simple and clean graphical interface  
- Fast processing and lightweight build  
- Ready-to-use: just download and run `run.bat`


## Tech Stack

- **Python 3.9+** — core spell-checking logic  
- **HTML, CSS, JavaScript** — user interface  
- **Local execution** (runs directly on your computer)  
- **Build scripts:** `build.py`, `run_app.py`, `run.bat`, and `CMakeLists.txt`


## Usage

1. Download the latest version of **TextCorrector** from the [Releases](../../releases) page.
2. Extract the downloaded ZIP file.
3. Double-click on **`run.bat`** to start the application.
4. Enter your text in the input box.
5. Receive the corrected text instantly.


## Screenshots

### Light Mode
![Screen 1](screenshots/Light.png)

### Dark Mode
![Screen 2](screenshots/Dark.png)


## Project Structure

TextCorrector/
├── README.md                
├── build.py                 
├── run_app.py               
├── run.bat                  
├── CMakeLists.txt           
├── static/ 
│   ├── index.html
│   ├── style.css
│   └── app.js
└── libs/                    


## Build & Releases

This project can be run directly after download — no installation required.

## Future Improvements

- Support for multiple languages
- User-defined custom dictionaries
- Enhanced UI/UX with better inline suggestions


## Developers

- [Seyedmujtaba Tabatabaee](https://github.com/Seyedmujtaba)
- [Ayla Rasouli](https://github.com/aylarasouli)
- [Negin Khoshdel](https://github.com/neginkhoshdel)


