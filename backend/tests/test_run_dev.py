import os
import sys
from pathlib import Path
import pytest

# Ensure Fyndo root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import run_dev


def test_find_frontend_dir_resolves():
    """Verify that find_frontend_dir finds the actual repository frontend."""
    frontend_dir = run_dev.find_frontend_dir()
    assert frontend_dir is not None
    assert frontend_dir.is_dir()
    assert (frontend_dir / "package.json").exists()


def test_find_frontend_dir_env_override(monkeypatch, tmp_path):
    """Verify that FRONTEND_DIR env override is respected when valid."""
    fake_frontend = tmp_path / "custom_frontend"
    fake_frontend.mkdir()
    (fake_frontend / "package.json").write_text('{"name": "custom"}')

    monkeypatch.setenv("FRONTEND_DIR", str(fake_frontend))
    found = run_dev.find_frontend_dir()
    assert found == fake_frontend.resolve()


def test_find_frontend_dir_returns_none_when_missing(monkeypatch, tmp_path):
    """Verify that when no frontend exists, find_frontend_dir returns None without crashing."""
    empty_root = tmp_path / "empty_proj"
    empty_root.mkdir()

    monkeypatch.setattr(run_dev, "ROOT_DIR", empty_root)
    monkeypatch.delenv("FRONTEND_DIR", raising=False)

    found = run_dev.find_frontend_dir()
    assert found is None


def test_find_frontend_dir_skip_env_or_flag(monkeypatch):
    """Verify that skip env var or CLI flags cause find_frontend_dir to return None."""
    monkeypatch.setenv("SKIP_FRONTEND", "1")
    assert run_dev.find_frontend_dir() is None

    monkeypatch.delenv("SKIP_FRONTEND", raising=False)
    monkeypatch.setattr(sys, "argv", ["run_dev.py", "--backend-only"])
    assert run_dev.find_frontend_dir() is None

    monkeypatch.setattr(sys, "argv", ["run_dev.py", "--no-frontend"])
    assert run_dev.find_frontend_dir() is None


def test_find_backend_dir():
    """Verify that backend directory resolves to directory with app/main.py."""
    backend_dir = run_dev.find_backend_dir()
    assert backend_dir.is_dir()
    assert (backend_dir / "app" / "main.py").exists()


def test_find_backend_python():
    """Verify backend python returns an executable path."""
    py_path = run_dev.find_backend_python()
    assert py_path is not None
    assert Path(py_path).exists()
