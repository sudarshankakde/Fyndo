import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


def find_backend_python():
    """Finds the virtualenv Python or falls back to system Python."""
    if sys.platform == "win32":
        venv_py = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = BACKEND_DIR / ".venv" / "bin" / "python"

    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def stream_logs(pipe, prefix, color_code):
    """Streams child process stdout/stderr with a colored tag prefix."""
    reset_color = "\033[0m"
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            sys.stdout.write(f"{color_code}{prefix}{reset_color} {line}")
            sys.stdout.flush()
    except Exception:
        pass
    finally:
        pipe.close()


def main():
    print("\n" + "=" * 62)
    print(" [*] Starting Fyndo Platform Services (Backend + Frontend)")
    print("=" * 62)
    print(" -> Backend API  : http://localhost:5000 (Swagger: http://localhost:5000/docs)")
    print(" -> Frontend App : http://localhost:3000")
    print(" Press Ctrl+C anytime to stop all services.\n" + "-" * 62)

    py_exe = find_backend_python()
    backend_cmd = [py_exe, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "5000"]

    # Windows requires shell=True for npm/bat
    use_shell = sys.platform == "win32"
    npm_cmd = "npm run dev" if use_shell else ["npm", "run", "dev"]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # Start Backend
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        encoding="utf-8",
        errors="replace"
    )

    # Start Frontend
    frontend_proc = subprocess.Popen(
        npm_cmd,
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=use_shell,
        encoding="utf-8",
        errors="replace"
    )

    # Background threads for log streaming with ANSI colors
    t1 = threading.Thread(
        target=stream_logs,
        args=(backend_proc.stdout, "[BACKEND ]", "\033[34m"),
        daemon=True
    )
    t2 = threading.Thread(
        target=stream_logs,
        args=(frontend_proc.stdout, "[FRONTEND]", "\033[32m"),
        daemon=True
    )
    t1.start()
    t2.start()

    def shutdown(signum=None, frame=None):
        print("\n\n[!] Shutting down Fyndo services...")
        try:
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(backend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                backend_proc.terminate()
                frontend_proc.terminate()
        except Exception:
            pass
        print("[+] All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for any process to exit
    while True:
        b_poll = backend_proc.poll()
        f_poll = frontend_proc.poll()
        if b_poll is not None or f_poll is not None:
            shutdown()
        try:
            threading.Event().wait(1)
        except KeyboardInterrupt:
            shutdown()


if __name__ == "__main__":
    main()
