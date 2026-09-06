from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["web"])
ROOT = Path(__file__).resolve().parent.parent / "web"

@router.get("/web", include_in_schema=False)
def web_index() -> FileResponse:
    return FileResponse(ROOT / "index.html")

@router.get("/web/app.js", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(ROOT / "app.js", media_type="text/javascript")

@router.get("/web/styles.css", include_in_schema=False)
def web_styles() -> FileResponse:
    return FileResponse(ROOT / "styles.css", media_type="text/css")
