from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

STATIC = Path(__file__).resolve().parents[2] / "static"
router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def storefront():
    return HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"))


@router.get("/admin", response_class=HTMLResponse)
def admin_panel():
    return HTMLResponse((STATIC / "admin.html").read_text(encoding="utf-8"))
