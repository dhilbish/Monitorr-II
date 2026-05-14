from __future__ import annotations

import time
from dataclasses import dataclass

import psutil

from .checks import tcp_probe
from .config import Drive, Site


@dataclass(slots=True)
class DriveStat:
    name: str
    path: str
    percent: float
    total_gb: float
    used_gb: float
    free_gb: float
    state: str = "ok"
    message: str = ""


@dataclass(slots=True)
class SystemStats:
    cpu_percent: float
    ram_percent: float
    uptime_seconds: int
    uptime_label: str
    ping_ms: int | None
    drives: list[DriveStat]


def _format_uptime(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    return f"{days:02d}:{hours:02d}:{minutes:02d}"


def _drive_stat(d: Drive) -> DriveStat:
    try:
        u = psutil.disk_usage(d.path)
        return DriveStat(
            name=d.name,
            path=d.path,
            percent=u.percent,
            total_gb=u.total / (1024**3),
            used_gb=u.used / (1024**3),
            free_gb=u.free / (1024**3),
        )
    except (FileNotFoundError, PermissionError, OSError) as e:
        return DriveStat(
            name=d.name, path=d.path, percent=0, total_gb=0, used_gb=0, free_gb=0,
            state="error", message=str(e),
        )


async def collect(site: Site) -> SystemStats:
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    uptime = int(time.time() - psutil.boot_time())

    ping_ms = await tcp_probe(site.ping.host, site.ping.port, timeout=2.0)

    drives = [_drive_stat(d) for d in site.drives if d.enabled]

    return SystemStats(
        cpu_percent=round(cpu, 1),
        ram_percent=round(ram, 1),
        uptime_seconds=uptime,
        uptime_label=_format_uptime(uptime),
        ping_ms=ping_ms,
        drives=drives,
    )


def threshold_class(value: float | None, ok: int, warn: int) -> str:
    if value is None:
        return "danger"
    if value < ok:
        return "success"
    if value < warn:
        return "warning"
    return "danger"
