from __future__ import annotations

from pathlib import Path

from .config import BUNDLED_ICONS_DIR, ICONS_DIR

_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp"}


def _scan(folder: Path) -> list[str]:
    if not folder.exists():
        return []
    return sorted(
        p.name for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _EXTS
    )


def list_all() -> list[dict]:
    user = _scan(ICONS_DIR)
    bundled = _scan(BUNDLED_ICONS_DIR)
    seen: set[str] = set()
    out: list[dict] = []
    for name in user:
        seen.add(name.lower())
        out.append({"filename": name, "source": "user"})
    for name in bundled:
        if name.lower() in seen:
            continue
        out.append({"filename": name, "source": "bundled"})
    out.sort(key=lambda x: x["filename"].lower())
    return out


def resolve(name: str) -> Path | None:
    """Map a bare filename to a real file path, user-icons first then bundled.

    Refuses any path traversal.
    """
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    if Path(name).name != name:
        return None
    u = ICONS_DIR / name
    if u.exists() and u.is_file():
        return u
    b = BUNDLED_ICONS_DIR / name
    if b.exists() and b.is_file():
        return b
    # Case-insensitive fallback for the case-sensitive Linux filesystem
    target = name.lower()
    if ICONS_DIR.exists():
        for p in ICONS_DIR.iterdir():
            if p.name.lower() == target:
                return p
    if BUNDLED_ICONS_DIR.exists():
        for p in BUNDLED_ICONS_DIR.iterdir():
            if p.name.lower() == target:
                return p
    return None


def save_upload(filename: str, content: bytes) -> str:
    name = Path(filename).name
    if not name or name.startswith(".") or Path(name).suffix.lower() not in _EXTS:
        raise ValueError(f"refusing icon filename: {filename!r}")
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    (ICONS_DIR / name).write_bytes(content)
    return name
