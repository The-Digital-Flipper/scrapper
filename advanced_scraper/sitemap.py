from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .extract import normalize_url


def discover_sitemap_urls(seed_url: str, user_agent: str, timeout: int = 20) -> list[str]:
    parsed = urlparse(seed_url)
    base = f"{parsed.scheme}://{parsed.netloc}/"
    robots_url = urljoin(base, "robots.txt")
    found: list[str] = []
    try:
        req = Request(robots_url, headers={"User-Agent": user_agent})
        with urlopen(req, timeout=timeout) as response:
            for line in response.read().decode("utf-8", errors="replace").splitlines():
                if line.lower().startswith("sitemap:"):
                    found.append(line.split(":", 1)[1].strip())
    except Exception:
        pass
    found.append(urljoin(base, "sitemap.xml"))
    return list(dict.fromkeys(found))


def fetch_sitemap_locations(sitemap_url: str, user_agent: str, timeout: int = 20, limit: int = 5000) -> list[str]:
    try:
        req = Request(sitemap_url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip"})
        with urlopen(req, timeout=timeout) as response:
            body = response.read()
        if sitemap_url.endswith(".gz") or body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        root = ET.fromstring(body)
    except Exception:
        return []

    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"

    urls: list[str] = []
    if root.tag.endswith("sitemapindex"):
        for loc in root.findall(f".//{namespace}loc"):
            if loc.text and len(urls) < limit:
                urls.extend(fetch_sitemap_locations(loc.text.strip(), user_agent, timeout, limit - len(urls)))
    else:
        for loc in root.findall(f".//{namespace}loc"):
            if loc.text:
                url = normalize_url(loc.text)
                if url:
                    urls.append(url)
            if len(urls) >= limit:
                break
    return urls[:limit]

