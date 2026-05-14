from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from .. import auth, config as cfg_module, poller, system as system_module
from ..config import BASE_PATH, Drive, Ping, Service, Site, Thresholds

router = APIRouter()
log = logging.getLogger("monitorr_ii.settings")


def _to_int(v: str | None, default: int) -> int:
    try:
        return int((v or "").strip())
    except ValueError:
        return default


def _to_bool(v: str | None) -> bool:
    return (v or "").lower() in {"on", "true", "1", "yes"}


def _collect_indexed(form: dict, prefix: str) -> list[dict]:
    """Parse form fields like services[0][title], services[0][enabled] into a list of dicts."""
    rows: dict[int, dict] = defaultdict(dict)
    for k, v in form.items():
        if not k.startswith(f"{prefix}["):
            continue
        try:
            rest = k[len(prefix) + 1:]  # "0][title]"
            idx_str, rest = rest.split("]", 1)
            idx = int(idx_str)
            assert rest.startswith("[") and rest.endswith("]")
            field = rest[1:-1]
        except (ValueError, AssertionError):
            continue
        rows[idx][field] = v
    return [rows[i] for i in sorted(rows)]


@router.post("/settings/site")
async def save_site(request: Request):
    auth.require(request)
    form = dict((await request.form()).multi_items())
    # multi_items gives a list of tuples; merge into a dict prioritising last value
    flat: dict[str, str] = {}
    for k, v in form.items() if False else (await request.form()).multi_items():
        flat[k] = v

    cfg = cfg_module.load()
    site = cfg.site
    site.title = flat.get("title", site.title)
    site.site_url = flat.get("site_url", site.site_url)
    site.timezone = flat.get("timezone", site.timezone)
    site.time_24h = _to_bool(flat.get("time_24h"))
    site.refresh_services_ms = _to_int(flat.get("refresh_services_ms"), site.refresh_services_ms)
    site.refresh_system_ms = _to_int(flat.get("refresh_system_ms"), site.refresh_system_ms)
    site.ping = Ping(
        host=flat.get("ping_host", site.ping.host),
        port=_to_int(flat.get("ping_port"), site.ping.port),
    )
    site.thresholds = Thresholds(
        cpu_ok=_to_int(flat.get("cpu_ok"), site.thresholds.cpu_ok),
        cpu_warn=_to_int(flat.get("cpu_warn"), site.thresholds.cpu_warn),
        ram_ok=_to_int(flat.get("ram_ok"), site.thresholds.ram_ok),
        ram_warn=_to_int(flat.get("ram_warn"), site.thresholds.ram_warn),
        ping_ok=_to_int(flat.get("ping_ok"), site.thresholds.ping_ok),
        ping_warn=_to_int(flat.get("ping_warn"), site.thresholds.ping_warn),
        hd_ok=_to_int(flat.get("hd_ok"), site.thresholds.hd_ok),
        hd_warn=_to_int(flat.get("hd_warn"), site.thresholds.hd_warn),
    )

    drive_rows = _collect_indexed(flat, "drives")
    drives: list[Drive] = []
    for row in drive_rows:
        path = (row.get("path") or "").strip()
        if not path:
            continue
        drives.append(
            Drive(
                name=(row.get("name") or path).strip(),
                path=path,
                enabled=_to_bool(row.get("enabled")),
            )
        )
    site.drives = drives
    cfg.site = site
    cfg_module.save(cfg)

    # Immediately refresh cached system stats so the new drive list shows up on the dashboard.
    try:
        import time as _t
        poller.cache.system = await system_module.collect(cfg.site)
        poller.cache.system_at = _t.time()
    except Exception:
        log.exception("post-save system refresh failed")

    return RedirectResponse(url=f"{BASE_PATH}/settings?saved=1", status_code=303)


@router.post("/settings/services")
async def save_services(request: Request):
    auth.require(request)
    form = await request.form()
    flat: dict[str, str] = {}
    for k, v in form.multi_items():
        flat[k] = v

    cfg = cfg_module.load()
    rows = _collect_indexed(flat, "services")
    services: list[Service] = []
    for row in rows:
        title = (row.get("title") or "").strip()
        if not title:
            continue
        services.append(
            Service(
                title=title,
                enabled=_to_bool(row.get("enabled")),
                type="tcp" if (row.get("type") or "http") == "tcp" else "http",
                icon=(row.get("icon") or "").strip(),
                check_url=(row.get("check_url") or "").strip(),
                link_url=(row.get("link_url") or "").strip(),
                show_link=_to_bool(row.get("show_link")),
                show_ping=_to_bool(row.get("show_ping")),
            )
        )
    cfg.services = services
    cfg_module.save(cfg)
    return RedirectResponse(url=f"{BASE_PATH}/settings?saved=1#services", status_code=303)
