from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import auth, migration, poller
from .config import BASE_PATH
from .routes import api as api_routes
from .routes import pages as page_routes
from .routes import settings as settings_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("monitorr_ii")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("monitorr-ii starting; base_path=%r", BASE_PATH)
    auth.init()
    if auth.is_open():
        log.warning("MONITORR_PASSWORD not set; settings UI is OPEN. Set it in env to protect settings.")
    try:
        migrated = migration.run()
        if migrated:
            log.info("migration produced new config with %d services", len(migrated.services))
    except Exception:
        log.exception("migration failed; continuing with whatever config exists")
    tasks = await poller.start()
    try:
        yield
    finally:
        await poller.stop(tasks)


app = FastAPI(
    title="Monitorr-II",
    lifespan=lifespan,
    root_path=BASE_PATH,
    openapi_url=None, docs_url=None, redoc_url=None,
)

_static_dir = Path(__file__).parent / "static"
_templates_dir = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.state.templates = Jinja2Templates(directory=_templates_dir)
app.state.templates.env.globals["base_path"] = BASE_PATH


def _threshold_class(value, ok, warn):
    if value is None:
        return "danger"
    if value < ok:
        return "success"
    if value < warn:
        return "warning"
    return "danger"


app.state.templates.env.filters["threshold"] = _threshold_class

app.include_router(api_routes.router)
app.include_router(page_routes.router)
app.include_router(settings_routes.router)
