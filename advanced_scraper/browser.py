from __future__ import annotations

from pathlib import Path
from typing import Any


def render_with_playwright(
    url: str,
    timeout_ms: int = 30000,
    *,
    click_selectors: tuple[str, ...] = (),
    wait_selectors: tuple[str, ...] = (),
    scrolls: int = 0,
    scroll_pause_ms: int = 900,
    wait_ms: int = 0,
    storage_state_path: Path | None = None,
    capture_network: bool = False,
    login_url: str = "",
    username: str = "",
    password: str = "",
    username_selector: str = "",
    password_selector: str = "",
    submit_selector: str = "",
    login_wait_selector: str = "",
    screenshot_path: Path | None = None,
    screenshot_full_page: bool = True,
) -> str | tuple[str, list[str]]:
    """Render a page with Playwright when the optional dependency is installed."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Playwright is not installed. Install it with: python3 -m pip install playwright && python3 -m playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_kwargs = {}
        if storage_state_path and storage_state_path.exists():
            context_kwargs["storage_state"] = str(storage_state_path)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        api_urls: set[str] = set()
        if capture_network:
            page.on("response", lambda response: _capture_api_response(response, api_urls))
        target_url = url
        if login_url or username or password:
            page.goto(login_url or url, wait_until="networkidle", timeout=timeout_ms)
            if username and username_selector:
                try:
                    page.locator(username_selector).first.fill(username, timeout=timeout_ms)
                except Exception:
                    pass
            if password and password_selector:
                try:
                    page.locator(password_selector).first.fill(password, timeout=timeout_ms)
                except Exception:
                    pass
            if submit_selector:
                try:
                    page.locator(submit_selector).first.click(timeout=timeout_ms)
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                except Exception:
                    pass
            if login_wait_selector:
                try:
                    page.wait_for_selector(login_wait_selector, timeout=timeout_ms)
                except Exception:
                    pass
            if target_url != (login_url or url):
                try:
                    page.goto(target_url, wait_until="networkidle", timeout=timeout_ms)
                except Exception:
                    pass
        else:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        for selector in wait_selectors:
            try:
                page.wait_for_selector(selector, timeout=timeout_ms)
            except Exception:
                pass
        for selector in click_selectors:
            try:
                page.locator(selector).first.click(timeout=timeout_ms)
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except Exception:
                pass
        for _ in range(max(0, scrolls)):
            try:
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(max(100, scroll_pause_ms))
            except Exception:
                break
        if wait_ms > 0:
            page.wait_for_timeout(wait_ms)
        if screenshot_path is not None:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(screenshot_path), full_page=screenshot_full_page)
            except Exception:
                pass
        html = page.content()
        if storage_state_path:
            storage_state_path.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(storage_state_path))
        context.close()
        browser.close()
        if capture_network:
            return html, sorted(api_urls)
        return html


def _capture_api_response(response: Any, api_urls: set[str]) -> None:
    try:
        headers = {k.lower(): v for k, v in response.headers.items()}
        content_type = headers.get("content-type", "")
        url = str(response.url or "")
        if "application/json" in content_type or "/api/" in url or "graphql" in url or url.endswith(".json"):
            api_urls.add(url)
    except Exception:
        pass
