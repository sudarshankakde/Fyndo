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
def find_backend_dir() -> Path:
    """Locates the backend directory containing the FastAPI app."""
    candidates = [
        ROOT_DIR / "backend",
        ROOT_DIR,
        ROOT_DIR.parent / "backend",
    ]
    for c in candidates:
        if c.is_dir() and (c / "app" / "main.py").exists():
            return c
    return ROOT_DIR / "backend"


BACKEND_DIR = find_backend_dir()


def find_frontend_dir() -> Path | None:
    """Locates the frontend directory across candidate paths or env override."""
    if "--backend-only" in sys.argv or "--no-frontend" in sys.argv or os.environ.get("SKIP_FRONTEND") == "1":
        return None

    env_dir = os.environ.get("FRONTEND_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        if p.is_dir():
            return p

    candidates = [
        ROOT_DIR.parent / "frontend",
        ROOT_DIR / "frontend",
        ROOT_DIR.parent / "Fyndo-Frontend",
    ]
    for c in candidates:
        if c.is_dir() and (c / "package.json").exists():
            return c
    for c in candidates:
        if c.is_dir():
            return c
    return None


# Locate frontend: checks parent/frontend, local frontend, and sibling repo
FRONTEND_DIR = find_frontend_dir()


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
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python run_dev.py [--backend-only | --no-frontend]")
        return

    frontend_dir = find_frontend_dir()
    backend_dir = find_backend_dir()

    print("\n" + "=" * 62)
    print(" [*] Starting Fyndo Platform Services (Backend + Frontend)")
    print("=" * 62)
    print(" -> Backend API  : http://localhost:5000 (Swagger: http://localhost:5000/docs)")
    if frontend_dir and frontend_dir.is_dir():
        print(f" -> Frontend App : http://localhost:3000 ({frontend_dir})")
    else:
        print(" -> Frontend App : [Not found / Skipped - backend only mode]")
    print(" Press Ctrl+C anytime to stop all services.\n" + "-" * 62)

    py_exe = find_backend_python()
    if not Path(py_exe).exists():
        print(f"[!] Error: Backend Python executable not found at {py_exe}")
        sys.exit(1)

    if not backend_dir.is_dir():
        print(f"[!] Error: Backend directory not found at {backend_dir}")
        sys.exit(1)

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
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        encoding="utf-8",
        errors="replace"
    )

    # Start Frontend (if directory exists and npm starts successfully)
    frontend_proc = None
    if frontend_dir and frontend_dir.is_dir():
        try:
            frontend_proc = subprocess.Popen(
                npm_cmd,
                cwd=str(frontend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=use_shell,
                encoding="utf-8",
                errors="replace"
            )
        except Exception as e:
            print(f"[!] Warning: Could not start frontend dev server: {e}")
            frontend_proc = None

    # Background threads for log streaming with ANSI colors
    t1 = threading.Thread(
        target=stream_logs,
        args=(backend_proc.stdout, "[BACKEND ]", "\033[34m"),
        daemon=True
    )
    t1.start()

    if frontend_proc and frontend_proc.stdout:
        t2 = threading.Thread(
            target=stream_logs,
            args=(frontend_proc.stdout, "[FRONTEND]", "\033[32m"),
            daemon=True
        )
        t2.start()

    def shutdown(signum=None, frame=None):
        print("\n\n[!] Shutting down Fyndo services...")
        try:
            if backend_proc and backend_proc.poll() is None:
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(backend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    backend_proc.terminate()
        except Exception:
            pass

        try:
            if frontend_proc and frontend_proc.poll() is None:
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
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
        f_poll = frontend_proc.poll() if frontend_proc else None
        if b_poll is not None:
            if b_poll != 0:
                print(f"\n[!] Backend exited with code {b_poll}.")
            shutdown()
        if frontend_proc and f_poll is not None:
            if f_poll != 0:
                print(f"\n[!] Frontend exited with code {f_poll}.")
            shutdown()
        try:
            threading.Event().wait(1)
        except KeyboardInterrupt:
            shutdown()


if __name__ == "__main__":
    main()
