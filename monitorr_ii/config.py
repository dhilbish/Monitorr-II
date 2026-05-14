from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

CONFIG_PATH = Path(os.environ.get("MONITORR_CONFIG", "/config/monitorr.json"))
LEGACY_DIR = Path(os.environ.get("MONITORR_LEGACY_DIR", "/config/legacy"))
ICONS_DIR = Path(os.environ.get("MONITORR_ICONS_DIR", "/config/icons"))
BUNDLED_ICONS_DIR = Path(__file__).parent / "static" / "icons"
BASE_PATH = os.environ.get("MONITORR_BASE_PATH", "").rstrip("/")


class Ping(BaseModel):
    host: str = "8.8.8.8"
    port: int = 53


class Thresholds(BaseModel):
    cpu_ok: int = 75
    cpu_warn: int = 90
    ram_ok: int = 75
    ram_warn: int = 90
    ping_ok: int = 50
    ping_warn: int = 500
    hd_ok: int = 75
    hd_warn: int = 90


class Drive(BaseModel):
    name: str
    path: str
    enabled: bool = True


class Site(BaseModel):
    title: str = "Monitorr"
    site_url: str = ""
    timezone: str = "UTC"
    time_24h: bool = True
    refresh_services_ms: int = 30000
    refresh_system_ms: int = 30000
    ping: Ping = Field(default_factory=Ping)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    drives: list[Drive] = Field(default_factory=list)


class Service(BaseModel):
    title: str
    enabled: bool = True
    type: Literal["http", "tcp"] = "http"
    icon: str = ""
    check_url: str = ""
    link_url: str = ""
    show_link: bool = True
    show_ping: bool = False


class Config(BaseModel):
    site: Site = Field(default_factory=Site)
    services: list[Service] = Field(default_factory=list)


def load() -> Config:
    if not CONFIG_PATH.exists():
        return Config()
    raw = json.loads(CONFIG_PATH.read_text())
    return Config.model_validate(raw)


def save(cfg: Config) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg.model_dump(), indent=2))
    tmp.replace(CONFIG_PATH)
