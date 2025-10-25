import argparse
import json
import os
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

# Package-relative import; run via: python -m src.backend.server --port 8000
from .spell_checker import correct_text, _default_dict_path


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.get("/health")
    def health() -> Any:
        return jsonify({"ok": True})

    @app.post("/check")
    def check() -> Any:
        try:
            data: Dict[str, Any] = request.get_json(silent=True) or {}
            text: str = data.get("text") or ""
            dict_path: str = data.get("dict_path") or _default_dict_path()

            if not isinstance(text, str):
                return jsonify({"error": "text must be a string"}), 400

            corrected_text, mistake_count, misspelled, fixes = correct_text(text, dict_path)

            return jsonify({
                "corrected_text": corrected_text,
                "mistake_count": int(mistake_count),
                "misspelled": misspelled,
                "fixes": fixes,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="TextCorrector API server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()


