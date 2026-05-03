from __future__ import annotations

import argparse
from pathlib import Path

from .crawler import CrawlConfig, Crawler
from .rules import UrlRules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="advanced-scraper",
        description="Dependency-free ethical crawler with robots.txt, throttling, retries, extraction, and exports.",
    )
    parser.add_argument("seeds", nargs="+", help="Seed URL(s), including http:// or https://")
    parser.add_argument("-o", "--output", default="scrape-output.jsonl", help="Output file path")
    parser.add_argument("--format", choices=["jsonl", "csv", "xml", "sqlite"], default="jsonl", help="Output format")
    parser.add_argument("--state-file", default=".scraper-state.json", help="Visited URL state file")
    parser.add_argument("--max-pages", type=int, default=1000, help="Maximum pages to fetch")
    parser.add_argument("--max-depth", type=int, default=6, help="Maximum crawl depth from seeds")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent worker count")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout seconds")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Minimum seconds between requests per host")
    parser.add_argument("--retries", type=int, default=2, help="Retries per URL")
    parser.add_argument("--ignore-robots", action="store_true", help="Disable robots.txt checks")
    parser.add_argument("--cross-domain", action="store_true", help="Allow crawling links outside seed domains")
    sitemaps = parser.add_mutually_exclusive_group()
    sitemaps.add_argument("--sitemaps", dest="sitemaps", action="store_true", help="Discover and seed URLs from robots.txt sitemaps")
    sitemaps.add_argument("--no-sitemaps", dest="sitemaps", action="store_false", help="Disable sitemap discovery")
    parser.set_defaults(sitemaps=True)
    parser.add_argument("--render-js", action="store_true", help="Use optional Playwright rendering for JavaScript pages")
    parser.add_argument("--browser-mode", choices=["http", "playwright", "mixed"], default="http", help="Choose HTTP crawl, full Playwright crawl, or mixed crawl mode")
    parser.add_argument("--whole-site", action="store_true", help="Use aggressive whole-site crawl defaults")
    parser.add_argument("--authorized-owner-mode", action="store_true", help="Use stronger crawl defaults for sites you own or are permitted to crawl")
    parser.add_argument("--click", action="append", default=[], help="Playwright selector to click; repeatable")
    parser.add_argument("--wait-for", action="append", default=[], help="Playwright selector to wait for; repeatable")
    parser.add_argument("--scrolls", type=int, default=0, help="Playwright scroll passes for lazy-loaded content")
    parser.add_argument("--scroll-pause-ms", type=int, default=900, help="Pause between Playwright scrolls")
    parser.add_argument("--wait-ms", type=int, default=0, help="Extra wait after browser actions")
    parser.add_argument("--include", action="append", default=[], help="Regex URL allow rule; repeatable")
    parser.add_argument("--exclude", action="append", default=[], help="Regex URL block rule; repeatable")
    parser.add_argument("--css", action="append", default=[], help="Extract text with simple CSS selector; repeatable")
    parser.add_argument("--xpath", action="append", default=[], help="Extract text with simple XPath selector; repeatable")
    parser.add_argument("--regex", action="append", default=[], help="Extract regex matches from HTML; repeatable")
    parser.add_argument("--max-images", type=int, default=200, help="Maximum images to keep per page record")
    parser.add_argument("--max-media", type=int, default=200, help="Maximum media entries to keep per page record")
    parser.add_argument("--max-api-endpoints", type=int, default=200, help="Maximum API endpoints to keep per page record")
    parser.add_argument("--header", action="append", default=[], help="Custom request header, e.g. 'X-Token: value'; repeatable")
    parser.add_argument("--cookie", action="append", default=[], help="Cookie pair, e.g. 'session=abc'; repeatable")
    parser.add_argument("--download-assets", action="store_true", help="Download linked image/file assets")
    parser.add_argument("--asset-dir", default="assets", help="Directory for downloaded assets")
    parser.add_argument("--save-dom", action="store_true", help="Save fetched DOM snapshots")
    parser.add_argument("--dom-dir", default="dom", help="Directory for DOM snapshots")
    parser.add_argument("--save-screenshots", action="store_true", help="Save Playwright screenshots for rendered pages")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Directory for saved screenshots")
    parser.add_argument("--screenshot-full-page", action="store_true", help="Capture full-page screenshots")
    parser.add_argument("--event-log", default="scraper-events.jsonl", help="JSONL audit/error log path")
    parser.add_argument("--webhook-url", help="POST each scraped record to this webhook URL")
    parser.add_argument("--privacy-mode", action="store_true", help="Enable local privacy defaults: strip tracking params and redact common PII")
    parser.add_argument("--strip-tracking", action="store_true", help="Strip common tracking query parameters from URLs")
    parser.add_argument("--redact-pii", action="store_true", help="Redact common emails, phone numbers, and SSN-like values from output")
    parser.add_argument("--proxy", default="", help="Authorized proxy URL, e.g. http://user:pass@host:port")
    parser.add_argument("--session-name", default="", help="Persistent browser session name")
    parser.add_argument("--login-url", default="", help="Login page URL when authentication is required")
    parser.add_argument("--username", default="", help="Username or email for login testing")
    parser.add_argument("--password", default="", help="Password for login testing")
    parser.add_argument("--username-selector", default="", help="CSS selector for the login username field")
    parser.add_argument("--password-selector", default="", help="CSS selector for the login password field")
    parser.add_argument("--submit-selector", default="", help="CSS selector for the login submit button")
    parser.add_argument("--login-wait-selector", default="", help="Selector to wait for after login succeeds")
    parser.add_argument("--schema", default="", help="JSON schema fields for structured extraction")
    parser.add_argument("--resume-failed", action="store_true", default=True, help="Resume URLs that previously failed")
    parser.add_argument("--no-resume-failed", dest="resume_failed", action="store_false", help="Do not retry failed URLs from state")
    parser.add_argument("--user-agent", default="AdvancedScraper/0.1 (+respectful research crawler)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.whole_site:
        args.max_pages = max(args.max_pages, 10000)
        args.max_depth = max(args.max_depth, 10)
        args.workers = max(args.workers, 10)
        args.rate_limit = min(args.rate_limit, 0.5)
        args.sitemaps = True
        args.render_js = True
        args.browser_mode = "mixed"
        args.scrolls = max(args.scrolls, 10)
        args.scroll_pause_ms = min(args.scroll_pause_ms, 700)
        args.wait_ms = max(args.wait_ms, 500)
        if not args.click:
            args.click = [".load-more", ".next", ".show-more"]
        if not args.wait_for:
            args.wait_for = [".results", ".listing", ".posts"]
    if args.authorized_owner_mode:
        args.max_pages = max(args.max_pages, 50000)
        args.max_depth = max(args.max_depth, 20)
        args.workers = max(args.workers, 16)
        args.timeout = max(args.timeout, 30)
        args.retries = max(args.retries, 4)
        args.rate_limit = min(args.rate_limit, 0.15)
        args.sitemaps = True
        args.render_js = True
        args.browser_mode = "playwright"
        args.scrolls = max(args.scrolls, 15)
        args.scroll_pause_ms = min(args.scroll_pause_ms, 500)
        args.wait_ms = max(args.wait_ms, 1000)
        if not args.click:
            args.click = [".load-more", ".next", ".show-more", "button"]
        if not args.wait_for:
            args.wait_for = [".results", ".listing", ".posts", ".content", ".page"]
    config = CrawlConfig(
        seeds=args.seeds,
        output=Path(args.output),
        output_format=args.format,
        state_file=Path(args.state_file) if args.state_file else None,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        workers=args.workers,
        timeout=args.timeout,
        rate_limit=args.rate_limit,
        retries=args.retries,
        respect_robots=not args.ignore_robots,
        same_domain_only=not args.cross_domain,
        use_sitemaps=args.sitemaps,
        render_js=args.render_js,
        browser_mode=args.browser_mode,
        click_selectors=tuple(args.click),
        wait_selectors=tuple(args.wait_for),
        scrolls=args.scrolls,
        scroll_pause_ms=args.scroll_pause_ms,
        wait_ms=args.wait_ms,
        css_selectors=tuple(args.css),
        xpath_selectors=tuple(args.xpath),
        regex_extractors=tuple(args.regex),
        schema_json=args.schema,
        max_images=args.max_images,
        max_media=args.max_media,
        max_api_endpoints=args.max_api_endpoints,
        headers=tuple(args.header),
        cookies=tuple(args.cookie),
        download_assets=args.download_assets,
        asset_dir=Path(args.asset_dir),
        save_dom=args.save_dom,
        dom_dir=Path(args.dom_dir),
        save_screenshots=args.save_screenshots,
        screenshot_dir=Path(args.screenshot_dir),
        screenshot_full_page=args.screenshot_full_page,
        event_log=Path(args.event_log) if args.event_log else None,
        webhook_url=args.webhook_url,
        privacy_mode=args.privacy_mode,
        strip_tracking=args.strip_tracking,
        redact_pii=args.redact_pii,
        session_name=args.session_name,
        login_url=args.login_url,
        username=args.username,
        password=args.password,
        username_selector=args.username_selector,
        password_selector=args.password_selector,
        submit_selector=args.submit_selector,
        login_wait_selector=args.login_wait_selector,
        resume_failed=args.resume_failed,
        proxy=args.proxy,
        rules=UrlRules(include=tuple(args.include), exclude=tuple(args.exclude)),
        user_agent=args.user_agent,
    )
    Crawler(config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
