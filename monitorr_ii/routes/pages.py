from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import auth, poller
from .. import config as cfg_module
from ..config import BASE_PATH

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    cfg = cfg_module.load()
    templates = _templates(request)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "cfg": cfg,
            "base_path": BASE_PATH,
            "results": poller.cache.services,
            "stats": poller.cache.system,
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request) -> HTMLResponse:
    templates = _templates(request)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "base_path": BASE_PATH, "error": None},
    )


@router.post("/login")
async def login_submit(request: Request, password: str = Form("")):
    templates = _templates(request)
    if not auth.verify_password(password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "base_path": BASE_PATH, "error": "Wrong password"},
            status_code=401,
        )
    redirect = RedirectResponse(url=f"{BASE_PATH}/settings", status_code=303)
    redirect.set_cookie(
        key=auth.COOKIE_NAME,
        value=auth.make_cookie(),
        max_age=auth.COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return redirect


@router.get("/logout")
async def logout(request: Request):
    redirect = RedirectResponse(url=f"{BASE_PATH}/", status_code=303)
    redirect.delete_cookie(auth.COOKIE_NAME)
    return redirect


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    if not auth.is_open():
        if not auth.validate_cookie(request.cookies.get(auth.COOKIE_NAME)):
            return RedirectResponse(url=f"{BASE_PATH}/login", status_code=303)
    cfg = cfg_module.load()
    templates = _templates(request)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "cfg": cfg,
            "base_path": BASE_PATH,
            "saved": request.query_params.get("saved") == "1",
        },
    )
