"""Shared Jinja2 environment for the admin panel."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.admin.registry import nav_groups
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.globals.update(
    panel_name="Fyndo Control Room",
    environment=settings.ENVIRONMENT,
    nav=nav_groups(),
)
