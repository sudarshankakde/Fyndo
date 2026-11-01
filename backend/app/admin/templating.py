import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi.templating import Jinja2Templates

from app.admin.registry import nav_groups
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def parse_kyc_docs(val: Optional[str]) -> List[Dict[str, Any]]:
    """Parses a single URL, comma-separated list, or JSON array of document URLs."""
    if not val:
        return []
    val = str(val).strip()
    if not val:
        return []
    docs: List[str] = []
    if val.startswith("["):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                docs = [str(u).strip() for u in parsed if u]
            elif isinstance(parsed, str):
                docs = [parsed.strip()]
        except Exception:
            docs = [u.strip().strip("'\"") for u in val.strip("[]").split(",") if u.strip().strip("'\"")]
    elif "," in val:
        docs = [u.strip() for u in val.split(",") if u.strip()]
    else:
        docs = [val]

    result = []
    for idx, raw_u in enumerate(docs, 1):
        u = raw_u.strip("'\"")
        clean_u = u.split("?")[0].split("#")[0].lower()
        is_pdf = clean_u.endswith(".pdf") or ".pdf?" in u.lower() or "application/pdf" in u.lower() or "/raw/upload/" in u.lower()
        result.append({
            "url": u,
            "label": f"Doc {idx} (PDF)" if is_pdf else f"Doc {idx}",
            "is_pdf": is_pdf,
            "index": idx,
        })
    return result


templates.env.filters["parse_kyc_docs"] = parse_kyc_docs

templates.env.globals.update(
    panel_name="Fyndo Control Room",
    environment=settings.ENVIRONMENT,
    nav=nav_groups(),
)
