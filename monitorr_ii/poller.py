from __future__ import annotations

import asyncio
import logging
import time

from . import config as cfg_module
from . import system as system_module
from .checks import CheckResult, check_all

log = logging.getLogger("monitorr_ii.poller")


class Cache:
    def __init__(self) -> None:
        self.services: list[CheckResult] = []
        self.services_at: float = 0.0
        self.system: system_module.SystemStats | None = None
        self.system_at: float = 0.0


cache = Cache()


async def _services_loop() -> None:
    while True:
        cfg = cfg_module.load()
        try:
            cache.services = await check_all(cfg.services)
            cache.services_at = time.time()
        except Exception:
            log.exception("services check cycle failed")
        await asyncio.sleep(max(5.0, cfg.site.refresh_services_ms / 1000.0))


async def _system_loop() -> None:
    while True:
        cfg = cfg_module.load()
        try:
            cache.system = await system_module.collect(cfg.site)
            cache.system_at = time.time()
        except Exception:
            log.exception("system collect failed")
        await asyncio.sleep(max(5.0, cfg.site.refresh_system_ms / 1000.0))


async def start(loop: asyncio.AbstractEventLoop | None = None) -> list[asyncio.Task]:
    return [asyncio.create_task(_services_loop()), asyncio.create_task(_system_loop())]


async def stop(tasks: list[asyncio.Task]) -> None:
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass
