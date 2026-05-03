from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ASSET_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip", ".csv", ".xlsx", ".doc", ".docx",
    ".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi", ".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"
}


def is_asset_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in ASSET_EXTENSIONS)


def asset_name(url: str) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".bin"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    stem = Path(parsed.path).stem or "asset"
    return f"{stem[:80]}-{digest}{suffix}"


def download_asset(url: str, output_dir: Path, user_agent: str, timeout: int = 20) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / asset_name(url)
    req = Request(urljoin(url, ""), headers={"User-Agent": user_agent})
    with urlopen(req, timeout=timeout) as response:
        path.write_bytes(response.read())
    return path
