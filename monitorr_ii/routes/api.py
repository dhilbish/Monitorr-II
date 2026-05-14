from __future__ import annotations

import io
import logging
import time

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .. import auth, icons, poller
from .. import config as cfg_module
from ..config import BASE_PATH

router = APIRouter()
log = logging.getLogger("monitorr_ii.api")


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "services_cached": len(poller.cache.services),
        "last_services_check_age_s": (time.time() - poller.cache.services_at) if poller.cache.services_at else None,
        "system_collected": poller.cache.system is not None,
    }


@router.get("/api/services", response_class=HTMLResponse)
async def api_services(request: Request) -> HTMLResponse:
    templates = _templates(request)
    cfg = cfg_module.load()
    return templates.TemplateResponse(
        "partials/services_grid.html",
        {
            "request": request,
            "results": poller.cache.services,
            "cfg": cfg,
            "base_path": BASE_PATH,
        },
    )


@router.get("/api/system", response_class=HTMLResponse)
async def api_system(request: Request) -> HTMLResponse:
    templates = _templates(request)
    cfg = cfg_module.load()
    return templates.TemplateResponse(
        "partials/system_badges.html",
        {
            "request": request,
            "stats": poller.cache.system,
            "cfg": cfg,
        },
    )


@router.get("/api/icons")
async def api_icons() -> JSONResponse:
    return JSONResponse(icons.list_all())


@router.post("/api/icons")
async def api_icons_upload(request: Request, upload: UploadFile = File(...)) -> JSONResponse:
    auth.require(request)
    data = await upload.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="icon too large (max 5MB)")
    try:
        name = icons.save_upload(upload.filename or "", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse({"filename": name})


@router.get("/icons/{name}")
async def serve_icon(name: str) -> Response:
    p = icons.resolve(name)
    if not p:
        raise HTTPException(status_code=404, detail="icon not found")
    return FileResponse(p)
