from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

from .storage import APP_DIR


ARCHIVES_DIR = APP_DIR / "archives"
IMPORTS_DIR = APP_DIR / "imports"


def ensure_archive_dirs() -> None:
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)


def create_site_archive(
    *,
    name: str,
    output_path: Path,
    event_log_path: Path | None = None,
    dom_dir: Path | None = None,
    asset_dir: Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    ensure_archive_dirs()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name).strip("-") or "site"
    archive_path = ARCHIVES_DIR / f"{safe_name}-{stamp}.zip"
    manifest = {
        "name": name,
        "created_at": time.time(),
        "output_file": output_path.name,
        "event_log_file": event_log_path.name if event_log_path else "",
        "has_dom": bool(dom_dir and dom_dir.exists()),
        "has_assets": bool(asset_dir and asset_dir.exists()),
        "config": config or {},
    }
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        if output_path.exists():
            zf.write(output_path, f"data/{output_path.name}")
        if event_log_path and event_log_path.exists():
            zf.write(event_log_path, f"logs/{event_log_path.name}")
        if dom_dir and dom_dir.exists():
            _write_tree(zf, dom_dir, "dom")
        if asset_dir and asset_dir.exists():
            _write_tree(zf, asset_dir, "assets")
    return archive_path


def import_site_archive(archive_path: Path) -> Path:
    ensure_archive_dirs()
    if not archive_path.exists():
        raise FileNotFoundError(str(archive_path))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = IMPORTS_DIR / f"{archive_path.stem}-{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as zf:
        _safe_extract(zf, target)
    return target


def list_archives() -> list[Path]:
    ensure_archive_dirs()
    return sorted(ARCHIVES_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)


def list_imports() -> list[Path]:
    ensure_archive_dirs()
    return sorted([p for p in IMPORTS_DIR.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)


def _write_tree(zf: zipfile.ZipFile, root: Path, prefix: str) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            zf.write(path, f"{prefix}/{path.relative_to(root)}")


def _safe_extract(zf: zipfile.ZipFile, target: Path) -> None:
    target_resolved = target.resolve()
    for member in zf.infolist():
        dest = (target / member.filename).resolve()
        if target_resolved not in dest.parents and dest != target_resolved:
            raise ValueError(f"Unsafe zip path: {member.filename}")
    zf.extractall(target)


def copy_import_source(src: Path) -> Path:
    ensure_archive_dirs()
    target = APP_DIR / "incoming" / src.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)
    return target

