import os
import sys
import time
import subprocess
import threading
import webbrowser
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox
except Exception:  # headless fallback
    tk = None
    messagebox = None


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_MODULE = "src.backend.server"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000

FRONTEND_PORT = 5500
FRONTEND_ENTRY = f"http://{BACKEND_HOST}:{FRONTEND_PORT}/src/frontend/index.html"

# Hide extra console windows on Windows
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class ProcessManager:
    def __init__(self):
        self.backend_proc = None
        self.frontend_proc = None
        self._lock = threading.Lock()

    def _start_proc(self, args, cwd):
        return subprocess.Popen(
            args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )

    def start_backend(self):
        with self._lock:
            if self.backend_proc and self.backend_proc.poll() is None:
                return
            args = [sys.executable, "-m", BACKEND_MODULE, "--host", BACKEND_HOST, "--port", str(BACKEND_PORT)]
            self.backend_proc = self._start_proc(args, PROJECT_ROOT)

    def start_frontend(self):
        with self._lock:
            if self.frontend_proc and self.frontend_proc.poll() is None:
                return
            # Serve the project root so relative paths like ../../libs/... resolve
            args = [sys.executable, "-m", "http.server", str(FRONTEND_PORT), "-d", str(PROJECT_ROOT)]
            self.frontend_proc = self._start_proc(args, PROJECT_ROOT)

    def stop_all(self, timeout=3.0):
        with self._lock:
            procs = [p for p in [self.frontend_proc, self.backend_proc] if p is not None]
            for p in procs:
                if p.poll() is None:
                    try:
                        p.terminate()
                    except Exception:
                        pass
            # wait briefly
            end = time.time() + timeout
            for p in procs:
                if p.poll() is None:
                    remaining = max(0.0, end - time.time())
                    try:
                        p.wait(timeout=remaining)
                    except Exception:
                        pass
            # force kill if still alive
            for p in procs:
                if p.poll() is None:
                    try:
                        p.kill()
                    except Exception:
                        pass


def open_browser_when_ready(url, check_fn, timeout=15.0, interval=0.3):
    start = time.time()
    while time.time() - start < timeout:
        if check_fn():
            webbrowser.open(url)
            return
        time.sleep(interval)


def can_connect(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False


def main_headful():
    mgr = ProcessManager()

    # Pre-flight check: dependencies
    try:
        import flask  # noqa: F401
        import spellchecker  # noqa: F401
    except Exception as e:
        if messagebox:
            messagebox.showerror(
                "Missing dependencies",
                "Required packages not installed.\n\n"
                "Run:\n    pip install -r libs/spellchecker/requirements.txt\n\n"
                f"Details: {e}",
            )
        else:
            print("Missing dependencies. Please run: pip install -r libs/spellchecker/requirements.txt")
        return

    # Start processes
    try:
        mgr.start_backend()
        mgr.start_frontend()
    except Exception as e:
        if messagebox:
            messagebox.showerror("Failed to start", str(e))
        else:
            print(f"Failed to start: {e}")
        mgr.stop_all()
        return

    # Open browser when frontend port is ready
    threading.Thread(
        target=open_browser_when_ready,
        args=(FRONTEND_ENTRY, lambda: can_connect(BACKEND_HOST, FRONTEND_PORT)),
        daemon=True,
    ).start()

    # Build simple UI
    root = tk.Tk()
    root.title("TextCorrector Launcher")
    root.geometry("380x160")
    root.resizable(False, False)

    status = tk.Label(root, text=f"Backend: http://{BACKEND_HOST}:{BACKEND_PORT}\nFrontend: {FRONTEND_ENTRY}")
    status.pack(pady=16)

    def on_open_browser():
        webbrowser.open(FRONTEND_ENTRY)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=8)

    open_btn = tk.Button(btn_frame, text="Open Frontend", command=on_open_browser)
    open_btn.pack(side=tk.LEFT, padx=6)

    def on_exit():
        try:
            mgr.stop_all()
        finally:
            root.destroy()

    exit_btn = tk.Button(btn_frame, text="Exit", command=on_exit)
    exit_btn.pack(side=tk.LEFT, padx=6)

    def on_close():
        on_exit()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def main_headless():
    mgr = ProcessManager()
    try:
        mgr.start_backend()
        mgr.start_frontend()
        print("Servers started. Press Ctrl+C to stop.")
        webbrowser.open(FRONTEND_ENTRY)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        mgr.stop_all()


if __name__ == "__main__":
    if tk is None:
        main_headless()
    else:
        main_headful()


