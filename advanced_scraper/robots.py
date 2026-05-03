from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


@dataclass
class RobotsEntry:
    parser: RobotFileParser
    fetched_at: float
    crawl_delay: float | None
    available: bool


class RobotsCache:
    def __init__(self, user_agent: str, ttl_seconds: int = 3600) -> None:
        self.user_agent = user_agent
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, RobotsEntry] = {}

    def _robots_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def get(self, url: str) -> RobotsEntry:
        robots_url = self._robots_url(url)
        entry = self._cache.get(robots_url)
        now = time.time()
        if entry and now - entry.fetched_at < self.ttl_seconds:
            return entry

        parser = RobotFileParser(robots_url)
        available = False
        try:
            parser.read()
            available = True
            delay = parser.crawl_delay(self.user_agent)
        except Exception:
            delay = None
        entry = RobotsEntry(parser=parser, fetched_at=now, crawl_delay=delay, available=available)
        self._cache[robots_url] = entry
        return entry

    def allowed(self, url: str) -> bool:
        entry = self.get(url)
        if not entry.available:
            return True
        try:
            return bool(entry.parser.can_fetch(self.user_agent, url))
        except Exception:
            return True

    def crawl_delay(self, url: str) -> float | None:
        return self.get(url).crawl_delay
