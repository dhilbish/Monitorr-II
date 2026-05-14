from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .config import CONFIG_PATH, LEGACY_DIR, Config, Drive, Ping, Service, Site, Thresholds, save

log = logging.getLogger("monitorr_ii.migration")

_TRUE = {"yes", "enable", "enabled", "true", "on", "1"}
_FALSE = {"no", "disable", "disabled", "false", "off", "0", ""}


def _truthy(v: object) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in _TRUE
    return False


def _falsy(v: object) -> bool:
    return isinstance(v, str) and v.strip().lower() in _FALSE


def _strip_icon_prefix(p: str) -> str:
    if not p:
        return ""
    # legacy paths look like "../img/plex.png" or "../data/usrimg/portainer.jpg"
    p = p.strip()
    p = re.sub(r"^\.\./", "", p)
    p = re.sub(r"^(img|data/usrimg|images)/", "", p)
    return Path(p).name


def _service_type(v: str) -> str:
    s = (v or "").strip().lower()
    if "ping" in s:
        return "tcp"
    return "http"


def _coerce_int(v: object, default: int) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _legacy_load(name: str) -> object:
    p = LEGACY_DIR / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as e:
        log.warning("legacy file %s unreadable: %s", p, e)
        return None


def needs_migration() -> bool:
    return not CONFIG_PATH.exists() and LEGACY_DIR.exists()


def run() -> Config | None:
    """Read legacy JSON files in LEGACY_DIR and produce a new Config.

    Idempotent: if CONFIG_PATH exists, no-op.
    """
    if CONFIG_PATH.exists():
        return None
    if not LEGACY_DIR.exists():
        log.info("no legacy dir at %s, skipping migration", LEGACY_DIR)
        return None

    site_raw = _legacy_load("site_settings-data.json") or {}
    services_raw = _legacy_load("services_settings-data.json") or []
    user_raw = _legacy_load("user_preferences-data.json") or {}

    if not site_raw and not services_raw and not user_raw:
        log.info("legacy dir %s has no recognisable files, skipping", LEGACY_DIR)
        return None

    drives: list[Drive] = []
    for i in (1, 2, 3):
        path = site_raw.get(f"disk{i}", "")
        if not path:
            continue
        enabled = _truthy(site_raw.get(f"disk{i}enable", "Enable"))
        drives.append(Drive(name=f"disk{i}", path=path, enabled=enabled))
        log.info("migrated drive #%d: path=%s enabled=%s", i, path, enabled)

    thresholds = Thresholds(
        cpu_ok=_coerce_int(site_raw.get("cpuok"), 75),
        cpu_warn=_coerce_int(site_raw.get("cpuwarn"), 90),
        ram_ok=_coerce_int(site_raw.get("ramok"), 75),
        ram_warn=_coerce_int(site_raw.get("ramwarn"), 90),
        ping_ok=_coerce_int(site_raw.get("pingok"), 50),
        ping_warn=_coerce_int(site_raw.get("pingwarn"), 500),
        hd_ok=_coerce_int(site_raw.get("hdok"), 75),
        hd_warn=_coerce_int(site_raw.get("hdwarn"), 90),
    )

    site = Site(
        title=user_raw.get("sitetitle", "Monitorr"),
        site_url=user_raw.get("siteurl", ""),
        timezone=user_raw.get("timezone", "UTC"),
        time_24h=not _truthy(user_raw.get("timestandard", "False")),
        refresh_services_ms=_coerce_int(site_raw.get("rfsysinfo"), 30000),
        refresh_system_ms=_coerce_int(site_raw.get("rftime"), 30000),
        ping=Ping(host=site_raw.get("pinghost", "8.8.8.8"), port=_coerce_int(site_raw.get("pingport"), 53)),
        thresholds=thresholds,
        drives=drives,
    )

    services: list[Service] = []
    for raw in services_raw:
        if not isinstance(raw, dict):
            continue
        services.append(
            Service(
                title=raw.get("serviceTitle", ""),
                enabled=_truthy(raw.get("enabled", "Yes")),
                type=_service_type(raw.get("type", "Standard")),
                icon=_strip_icon_prefix(raw.get("image", "")),
                check_url=raw.get("checkurl", ""),
                link_url=raw.get("linkurl", ""),
                show_link=_truthy(raw.get("link", "Yes")),
                show_ping=_truthy(raw.get("ping", "Disabled")),
            )
        )

    cfg = Config(site=site, services=services)
    save(cfg)
    log.info("migrated %d services, %d drives -> %s", len(services), len(drives), CONFIG_PATH)
    return cfg
