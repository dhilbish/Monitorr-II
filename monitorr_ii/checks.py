from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

import httpx

from .config import Service

State = Literal["up", "down", "unresponsive", "disabled"]

_HTTP_OK_EXTRA = {401, 403, 405}
_HTTP_TIMEOUT = 15.0
_TCP_TIMEOUT = 3.0


@dataclass(slots=True)
class CheckResult:
    title: str
    state: State
    http_code: int | None = None
    ping_ms: int | None = None
    checked_at: float = 0.0


def _http_ok(status: int) -> bool:
    return 200 <= status < 400 or status in _HTTP_OK_EXTRA


def _host_port(url: str) -> tuple[str, int] | None:
    try:
        p = urlparse(url)
    except ValueError:
        return None
    if not p.hostname:
        return None
    if p.port:
        port = p.port
    else:
        port = 443 if p.scheme == "https" else 80
    return p.hostname, port


async def tcp_probe(host: str, port: int, timeout: float = _TCP_TIMEOUT) -> int | None:
    """Open a TCP connection, return latency in ms or None on failure."""
    loop = asyncio.get_running_loop()
    start = loop.time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except (asyncio.TimeoutError, OSError):
        return None
    try:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
    finally:
        pass
    return int((loop.time() - start) * 1000)


async def check_http(svc: Service, client: httpx.AsyncClient) -> CheckResult:
    started = time.time()
    code: int | None = None
    try:
        r = await client.head(
            svc.check_url, follow_redirects=True, timeout=_HTTP_TIMEOUT
        )
        code = r.status_code
        if _http_ok(code):
            ping_ms = None
            if svc.show_ping:
                hp = _host_port(svc.check_url)
                if hp:
                    ping_ms = await tcp_probe(*hp)
            return CheckResult(svc.title, "up", code, ping_ms, started)
    except httpx.HTTPError:
        pass

    # Fallback: TCP probe to distinguish offline vs unresponsive
    hp = _host_port(svc.check_url)
    if hp:
        ms = await tcp_probe(*hp)
        if ms is not None:
            return CheckResult(svc.title, "unresponsive", code, ms, started)
    return CheckResult(svc.title, "down", code, None, started)


async def check_tcp(svc: Service) -> CheckResult:
    started = time.time()
    hp = _host_port(svc.check_url)
    if not hp:
        return CheckResult(svc.title, "down", None, None, started)
    ms = await tcp_probe(*hp, timeout=5.0)
    if ms is None:
        return CheckResult(svc.title, "down", None, None, started)
    return CheckResult(svc.title, "up", None, ms, started)


async def check_one(svc: Service, client: httpx.AsyncClient) -> CheckResult:
    if not svc.enabled:
        return CheckResult(svc.title, "disabled", None, None, time.time())
    if svc.type == "tcp":
        return await check_tcp(svc)
    return await check_http(svc, client)


async def check_all(services: list[Service]) -> list[CheckResult]:
    async with httpx.AsyncClient(verify=False, timeout=_HTTP_TIMEOUT) as client:
        coros = [check_one(s, client) for s in services]
        results = await asyncio.gather(*coros, return_exceptions=True)
    out: list[CheckResult] = []
    for svc, r in zip(services, results):
        if isinstance(r, CheckResult):
            out.append(r)
        else:
            out.append(CheckResult(svc.title, "down", None, None, time.time()))
    return out
