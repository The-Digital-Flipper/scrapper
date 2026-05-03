from __future__ import annotations

import gzip
import hashlib
import json
import queue
import re
import socket
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener, urlopen

from .assets import download_asset, is_asset_url
from .extract import PageExtractor, normalize_url, same_domain
from .monitoring import EventLog
from .schema import build_markdown, chunk_text, extract_schema
from .privacy import redact_record, strip_tracking_params
from .rules import UrlRules
from .selectors import SelectorExtractor
from .sitemap import discover_sitemap_urls, fetch_sitemap_locations
from .output import ResultWriter
from .robots import RobotsCache
from .webhook import post_json


@dataclass
class CrawlConfig:
    seeds: list[str]
    output: Path
    output_format: str = "jsonl"
    state_file: Path | None = None
    max_pages: int = 100
    max_depth: int = 2
    workers: int = 6
    timeout: int = 20
    rate_limit: float = 1.0
    retries: int = 2
    respect_robots: bool = True
    same_domain_only: bool = True
    use_sitemaps: bool = False
    render_js: bool = False
    browser_mode: str = "http"
    click_selectors: tuple[str, ...] = ()
    wait_selectors: tuple[str, ...] = ()
    scrolls: int = 0
    scroll_pause_ms: int = 900
    wait_ms: int = 0
    css_selectors: tuple[str, ...] = ()
    xpath_selectors: tuple[str, ...] = ()
    regex_extractors: tuple[str, ...] = ()
    schema_json: str = ""
    max_images: int = 200
    max_media: int = 200
    max_api_endpoints: int = 200
    session_name: str = ""
    login_url: str = ""
    username: str = ""
    password: str = ""
    username_selector: str = ""
    password_selector: str = ""
    submit_selector: str = ""
    login_wait_selector: str = ""
    headers: tuple[str, ...] = ()
    cookies: tuple[str, ...] = ()
    download_assets: bool = False
    asset_dir: Path = Path("assets")
    save_dom: bool = False
    dom_dir: Path = Path("dom")
    save_screenshots: bool = False
    screenshot_dir: Path = Path("screenshots")
    screenshot_full_page: bool = True
    event_log: Path | None = Path("scraper-events.jsonl")
    webhook_url: str | None = None
    privacy_mode: bool = False
    strip_tracking: bool = False
    redact_pii: bool = False
    resume_failed: bool = True
    proxy: str = ""
    rules: UrlRules = UrlRules()
    user_agent: str = "AdvancedScraper/0.1 (+respectful research crawler)"


class HostThrottle:
    def __init__(self, default_delay: float) -> None:
        self.default_delay = default_delay
        self._next_allowed: dict[str, float] = {}
        self._host_delay: dict[str, float] = {}
        self._failures: dict[str, int] = {}
        self._lock = threading.Lock()

    def wait(self, url: str, override_delay: float | None = None) -> None:
        host = urlparse(url).netloc
        delay = self._delay_for(host, override_delay)
        with self._lock:
            now = time.time()
            target = self._next_allowed.get(host, 0.0)
            sleep_for = max(0.0, target - now)
            self._next_allowed[host] = max(now, target) + delay
        if sleep_for:
            time.sleep(sleep_for)

    def penalize(self, url: str, status: int | None = None) -> None:
        host = urlparse(url).netloc
        with self._lock:
            failures = self._failures.get(host, 0) + 1
            self._failures[host] = failures
            bump = 1.0
            if status in {429, 500, 502, 503, 504}:
                bump = 2.0
            self._host_delay[host] = min(max(self.default_delay, self._host_delay.get(host, self.default_delay)) * bump + 0.25, 30.0)

    def reward(self, url: str) -> None:
        host = urlparse(url).netloc
        with self._lock:
            self._failures.pop(host, None)
            current = self._host_delay.get(host, self.default_delay)
            self._host_delay[host] = max(self.default_delay, current * 0.85)

    def _delay_for(self, host: str, override_delay: float | None = None) -> float:
        with self._lock:
            host_delay = self._host_delay.get(host, self.default_delay)
        delay = host_delay if override_delay is None else max(host_delay, override_delay)
        return max(self.default_delay, delay)


class Crawler:
    def __init__(self, config: CrawlConfig) -> None:
        self.config = config
        self.allowed_hosts = {urlparse(seed).netloc.lower() for seed in config.seeds}
        self.robots = RobotsCache(config.user_agent)
        self.throttle = HostThrottle(config.rate_limit)
        self.events = EventLog(config.event_log)
        self.frontier: queue.Queue[tuple[str, int]] = queue.Queue()
        self.visited: set[str] = set()
        self.failed: set[str] = set()
        self.scheduled: set[str] = set()
        self._lock = threading.Lock()
        self._count = 0

    def load_state(self) -> None:
        if not self.config.state_file or not self.config.state_file.exists():
            return
        with self.config.state_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.visited = set(data.get("visited", []))
        self.failed = set(data.get("failed", []))

    def save_state(self) -> None:
        if not self.config.state_file:
            return
        self.config.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.config.state_file.open("w", encoding="utf-8") as handle:
            json.dump({"visited": sorted(self.visited), "failed": sorted(self.failed)}, handle, indent=2)

    def seed(self) -> None:
        for seed in self.config.seeds:
            url = self._normalize(seed)
            if url and url not in self.visited and (self.config.resume_failed or url not in self.failed):
                self.scheduled.add(url)
                self.frontier.put((url, 0))
            if self.config.use_sitemaps:
                for sitemap in discover_sitemap_urls(seed, self.config.user_agent, self.config.timeout):
                    for sitemap_url in fetch_sitemap_locations(
                        sitemap,
                        self.config.user_agent,
                        self.config.timeout,
                        max(1, self.config.max_pages - len(self.scheduled)),
                    ):
                        if not self._url_eligible(sitemap_url):
                            continue
                        if sitemap_url in self.visited or sitemap_url in self.scheduled:
                            continue
                        if not self.config.resume_failed and sitemap_url in self.failed:
                            continue
                        self.scheduled.add(sitemap_url)
                        self.frontier.put((sitemap_url, 1))

    def run(self) -> None:
        socket.setdefaulttimeout(self.config.timeout)
        self.load_state()
        self.seed()
        futures: set[Future[dict[str, Any]]] = set()

        with ResultWriter(self.config.output, self.config.output_format) as writer:
            with ThreadPoolExecutor(max_workers=self.config.workers) as pool:
                while self._count < self.config.max_pages and (not self.frontier.empty() or futures):
                    while len(futures) < self.config.workers and not self.frontier.empty():
                        url, depth = self.frontier.get()
                        with self._lock:
                            if url in self.visited or self._count >= self.config.max_pages:
                                continue
                            self._count += 1
                        futures.add(pool.submit(self.fetch_and_extract, url, depth))

                    done, futures = wait(futures, timeout=0.2, return_when="FIRST_COMPLETED")
                    for future in done:
                        record = future.result()
                        if self.config.privacy_mode or self.config.redact_pii:
                            record = redact_record(record)
                        status_text = str(record.get("status", ""))
                        if status_text not in {"error", "blocked_by_robots"}:
                            self.visited.add(str(record.get("url", "")))
                            self.failed.discard(str(record.get("url", "")))
                        else:
                            self.failed.add(str(record.get("url", "")))
                        writer.write(record)
                        if self.config.webhook_url:
                            try:
                                post_json(self.config.webhook_url, record, self.config.timeout)
                            except Exception as exc:
                                self.events.write("webhook_error", url=record.get("url", ""), error=str(exc))
                        self.enqueue_links(record)
                        if self._count % 25 == 0:
                            self.save_state()
            self.save_state()

    def enqueue_links(self, record: dict[str, Any]) -> None:
        depth = int(record.get("depth", 0))
        if depth >= self.config.max_depth:
            return
        candidates: list[str] = list(record.get("links", []))
        api_endpoints = record.get("api_endpoints")
        if isinstance(api_endpoints, list):
            candidates.extend(str(item) for item in api_endpoints if item)
        canonical = record.get("canonical")
        if isinstance(canonical, str) and canonical:
            candidates.append(canonical)
        pagination_links = record.get("pagination_links")
        if isinstance(pagination_links, list):
            candidates.extend(str(item) for item in pagination_links if item)
        hreflang = record.get("hreflang")
        if isinstance(hreflang, list):
            candidates.extend(
                item.get("href", "")
                for item in hreflang
                if isinstance(item, dict) and item.get("href")
            )
        for link in candidates:
            url = self._normalize(link)
            if not url:
                continue
            if not self._url_eligible(url):
                continue
            if self.config.download_assets and is_asset_url(url):
                try:
                    saved = download_asset(url, self.config.asset_dir, self.config.user_agent, self.config.timeout)
                    self.events.write("asset_downloaded", url=url, path=str(saved))
                except Exception as exc:
                    self.events.write("asset_error", url=url, error=str(exc))
                continue
            with self._lock:
                if url in self.visited or url in self.scheduled:
                    continue
                self.scheduled.add(url)
            self.frontier.put((url, depth + 1))

    def fetch_and_extract(self, url: str, depth: int) -> dict[str, Any]:
        if self.config.respect_robots and not self.robots.allowed(url):
            self.events.write("blocked_by_robots", url=url)
            return {"url": url, "depth": depth, "status": "blocked_by_robots", "links": []}

        delay = self.robots.crawl_delay(url) if self.config.respect_robots else None
        self.throttle.wait(url, delay)

        last_error = ""
        for attempt in range(self.config.retries + 1):
            try:
                record = self._fetch_once(url, depth)
                self.throttle.reward(url)
                return record
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
                status_code = getattr(exc, "code", None)
                self.events.write("fetch_error", url=url, attempt=attempt, error=last_error, status=status_code or "")
                self.throttle.penalize(url, status_code if isinstance(status_code, int) else None)
                if attempt < self.config.retries:
                    time.sleep(min(15, 2**attempt))
        return {"url": url, "depth": depth, "status": "error", "error": last_error, "links": []}

    def _fetch_once(self, url: str, depth: int) -> dict[str, Any]:
        custom_headers = dict(header.split(":", 1) for header in self.config.headers if ":" in header)
        if self.config.cookies:
            custom_headers["Cookie"] = "; ".join(self.config.cookies)
        request = Request(
            url,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip",
                **{key.strip(): value.strip() for key, value in custom_headers.items()},
            },
        )
        if self.config.proxy:
            opener = build_opener(ProxyHandler({"http": self.config.proxy, "https": self.config.proxy}))
            response_ctx = opener.open(request, timeout=self.config.timeout)
        else:
            response_ctx = urlopen(request, timeout=self.config.timeout)
        with response_ctx as response:
            status = getattr(response, "status", 200)
            headers = response.headers
            content_type = headers.get("Content-Type", "")
            body = response.read()

        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)

        if "application/json" in content_type or urlparse(url).path.endswith(".json"):
            try:
                api_json = json.loads(body.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                api_json = None
            return {
                "url": url,
                "depth": depth,
                "status": status,
                "content_type": content_type,
                "content_hash": hashlib.sha256(body).hexdigest(),
                "api_json": api_json,
                "api_endpoints": [url][: self.config.max_api_endpoints],
                "links": [],
            }

        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return {
                "url": url,
                "depth": depth,
                "status": status,
                "content_type": content_type,
                "content_hash": hashlib.sha256(body).hexdigest(),
                "links": [],
            }

        html = body.decode("utf-8", errors="replace")
        api_endpoints: list[str] = []
        screenshot_path = None
        browser_mode = (self.config.browser_mode or "http").lower()
        render_browser = False
        if browser_mode == "playwright":
            render_browser = True
        elif browser_mode == "mixed":
            render_browser = self._should_render_with_browser(html, browser_mode) or self.config.render_js
        elif self.config.render_js:
            render_browser = True
        if render_browser:
            from .browser import render_with_playwright

            session_path = None
            if self.config.session_name:
                session_path = Path.home() / ".advanced-scraper" / "sessions" / f"{self.config.session_name}.json"
            if self.config.save_screenshots:
                screenshot_dir = self.config.screenshot_dir
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = screenshot_dir / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.png"
            try:
                rendered = render_with_playwright(
                    url,
                    self.config.timeout * 1000,
                    click_selectors=self.config.click_selectors,
                    wait_selectors=self.config.wait_selectors,
                    scrolls=self.config.scrolls,
                    scroll_pause_ms=self.config.scroll_pause_ms,
                    wait_ms=self.config.wait_ms,
                    storage_state_path=session_path,
                    login_url=self.config.login_url,
                    username=self.config.username,
                    password=self.config.password,
                    username_selector=self.config.username_selector,
                    password_selector=self.config.password_selector,
                    submit_selector=self.config.submit_selector,
                    login_wait_selector=self.config.login_wait_selector,
                    screenshot_path=screenshot_path,
                    screenshot_full_page=self.config.screenshot_full_page,
                    capture_network=True,
                )
                if isinstance(rendered, tuple):
                    html, api_endpoints = rendered
                else:
                    html = rendered
            except RuntimeError as exc:
                if "Playwright is not installed" in str(exc):
                    self.events.write("playwright_missing", url=url, error=str(exc))
                else:
                    raise
        extractor = PageExtractor(url)
        extractor.feed(html)
        selector_extractor = SelectorExtractor(self.config.css_selectors, self.config.xpath_selectors)
        selector_extractor.feed(html)
        text = extractor.text
        hidden_text = extractor.hidden_text
        all_links = sorted(link for link in extractor.links if link)
        internal_links = [link for link in all_links if same_domain(link, {urlparse(url).netloc})]
        external_links = [link for link in all_links if link not in internal_links]
        pagination_links = sorted(link for link in extractor.pagination_links if link)
        schema_fields, validation_issues = extract_schema(html, self.config.schema_json)
        if self.config.save_dom:
            self._save_dom(url, html)
        markdown = build_markdown({
            "title": extractor.title,
            "description": extractor.meta_description,
            "headings": extractor.headings,
            "text_preview": text[:2000],
            "links": all_links,
            "images": extractor.images,
            "url": url,
        })
        return {
            "url": url,
            "depth": depth,
            "status": status,
            "content_type": content_type,
            "title": extractor.title,
            "description": extractor.meta_description,
            "canonical": extractor.canonical,
            "content_hash": extractor.content_hash,
            "lang": extractor.lang,
            "meta_keywords": extractor.meta_keywords,
            "author": extractor.author,
            "published_time": extractor.published_time,
            "headings": extractor.headings[:50],
            "json_ld": extractor.json_ld[:10],
            "open_graph": extractor.open_graph,
            "twitter_cards": extractor.twitter_cards,
            "hreflang": extractor.hreflang[:20],
            "tables": extractor.tables[:20],
            "images": extractor.images[:200],
            "media": extractor.media[:200],
            "background_images": extractor.background_images[:200],
            "comments": extractor.comments[:200],
            "api_endpoints": api_endpoints[: self.config.max_api_endpoints],
            "hidden_text": hidden_text[:2000],
            "files": sorted(extractor.files),
            "screenshot_path": str(screenshot_path) if screenshot_path else "",
            "internal_link_count": len(internal_links),
            "external_link_count": len(external_links),
            "internal_links": internal_links[:200],
            "external_links": external_links[:50],
            "pagination_links": pagination_links,
            "selector_matches": selector_extractor.matches,
            "schema_fields": schema_fields,
            "validation_issues": validation_issues,
            "regex_matches": {
                pattern: re.findall(pattern, html, flags=re.IGNORECASE | re.MULTILINE)
                for pattern in self.config.regex_extractors
            },
            "word_count": len(text.split()),
            "text_preview": text[:1000],
            "markdown": markdown,
            "content_chunks": chunk_text(text, 1200, 150),
            "links": all_links,
        }

    def _should_render_with_browser(self, html: str, browser_mode: str) -> bool:
        if browser_mode == "playwright":
            return True
        if browser_mode == "mixed":
            lower = html.lower()
            if len(html) < 5000:
                return True
            if "__next_data__" in lower or "data-reactroot" in lower or "data-v-" in lower:
                return True
            if lower.count("<script") >= 3 and lower.count("<a ") < 4:
                return True
        return False

    def _url_eligible(self, url: str) -> bool:
        if self.config.same_domain_only and not same_domain(url, self.allowed_hosts):
            return False
        return self.config.rules.allowed(url)

    def _normalize(self, url: str) -> str:
        clean = strip_tracking_params(url) if self.config.privacy_mode or self.config.strip_tracking else url
        return normalize_url(clean)

    def _save_dom(self, url: str, html: str) -> None:
        self.config.dom_dir.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"
        (self.config.dom_dir / name).write_text(html, encoding="utf-8")
