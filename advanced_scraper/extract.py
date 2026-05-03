from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse


VOID_TAGS = {"br", "hr", "img", "input", "meta", "link"}
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg", "canvas"}


class PageExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.meta_description = ""
        self.meta_keywords = ""
        self.author = ""
        self.published_time = ""
        self.lang = ""
        self.canonical = ""
        self.links: set[str] = set()
        self.pagination_links: set[str] = set()
        self.headings: list[dict[str, str]] = []
        self.json_ld: list[dict[str, object] | list[object]] = []
        self.open_graph: dict[str, str] = {}
        self.twitter_cards: dict[str, str] = {}
        self.hreflang: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.media: list[dict[str, str]] = []
        self.background_images: list[str] = []
        self.comments: list[str] = []
        self.hidden_text_parts: list[str] = []
        self.files: set[str] = set()
        self.tables: list[list[list[str]]] = []
        self.text_parts: list[str] = []
        self._tag_stack: list[str] = []
        self._in_title = False
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None
        self._skip_depth = 0
        self._hidden_depth = 0
        self._hidden_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): v or "" for k, v in attrs}
        tag = tag.lower()
        self._tag_stack.append(tag)

        if tag == "html" and attrs_dict.get("lang"):
            self.lang = attrs_dict.get("lang", "").strip()

        script_type = attrs_dict.get("type", "").lower()
        if tag == "script" and script_type == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_parts = []
        if tag in SKIP_TEXT_TAGS:
            self._skip_depth += 1
        if _is_hidden(attrs_dict):
            self._hidden_depth += 1
            self._hidden_stack.append(tag)
        elif tag == "title":
            self._in_title = True
        elif tag == "a" and attrs_dict.get("href"):
            href = normalize_url(urljoin(self.base_url, attrs_dict["href"]))
            self.links.add(href)
            if _looks_like_file(href):
                self.files.add(href)
            rel = attrs_dict.get("rel", "").lower()
            aria = attrs_dict.get("aria-label", "").lower()
            title = attrs_dict.get("title", "").lower()
            if "next" in rel or "prev" in rel or "page=" in href or "/page/" in href or "next" in aria or "next" in title:
                self.pagination_links.add(href)
        elif tag in {"img", "script", "source", "video", "audio", "iframe", "embed", "object"}:
            for src, kind in _media_sources(self.base_url, tag, attrs_dict):
                if not src:
                    continue
                self.links.add(src)
                self.media.append({"kind": kind, "src": src})
                if kind == "img":
                    self.images.append({"src": src, "alt": attrs_dict.get("alt", "")})
                if kind == "background":
                    self.background_images.append(src)
                if _looks_like_file(src):
                    self.files.add(src)
        elif tag == "link" and attrs_dict.get("rel") and attrs_dict.get("href"):
            rels = {part.strip().lower() for part in attrs_dict["rel"].split()}
            if "canonical" in rels:
                self.canonical = normalize_url(urljoin(self.base_url, attrs_dict["href"]))
            if "alternate" in rels and attrs_dict.get("hreflang"):
                self.hreflang.append({
                    "hreflang": attrs_dict.get("hreflang", "").strip(),
                    "href": normalize_url(urljoin(self.base_url, attrs_dict["href"])),
                })
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.meta_description = attrs_dict.get("content", "").strip()
            if name == "keywords":
                self.meta_keywords = attrs_dict.get("content", "").strip()
            if name in {"author", "article:author"}:
                self.author = attrs_dict.get("content", "").strip()
            if name in {"article:published_time", "publish_date", "pubdate"} or prop in {"article:published_time", "og:published_time"}:
                self.published_time = attrs_dict.get("content", "").strip()
            if prop.startswith("og:") and attrs_dict.get("content"):
                self.open_graph[prop] = attrs_dict["content"].strip()
            if name.startswith("twitter:") and attrs_dict.get("content"):
                self.twitter_cards[name] = attrs_dict["content"].strip()

        if tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

        if tag in VOID_TAGS and self._tag_stack:
            self._tag_stack.pop()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if self._hidden_stack and tag in self._hidden_stack:
            for index in range(len(self._hidden_stack) - 1, -1, -1):
                if self._hidden_stack[index] == tag:
                    self._hidden_stack.pop(index)
                    self._hidden_depth = max(0, self._hidden_depth - 1)
                    break
        if tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            raw = "\n".join(self._json_ld_parts).strip()
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, (dict, list)):
                        self.json_ld.append(parsed)
                except json.JSONDecodeError:
                    pass
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            self._current_row.append(" ".join(" ".join(self._current_cell).split()))
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None and self._current_table is not None:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = None
        if tag == "title":
            self._in_title = False
        if tag in self._tag_stack:
            while self._tag_stack:
                popped = self._tag_stack.pop()
                if popped == tag:
                    break

    def handle_comment(self, data: str) -> None:
        text = data.strip()
        if text:
            self.comments.append(text)

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if self._in_json_ld:
            self._json_ld_parts.append(data)
            return
        if not text:
            return
        if self._in_title:
            self.title = (self.title + " " + text).strip()
            return
        if self._skip_depth:
            return
        if self._hidden_depth:
            self.hidden_text_parts.append(text)
            return
        if self._current_cell is not None:
            self._current_cell.append(text)
        current = self._tag_stack[-1] if self._tag_stack else ""
        if current in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings.append({"level": current, "text": text})
        self.text_parts.append(text)

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)

    @property
    def hidden_text(self) -> str:
        return " ".join(self.hidden_text_parts)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8", errors="ignore")).hexdigest()


def normalize_url(url: str) -> str:
    clean, _fragment = urldefrag(url.strip())
    parsed = urlparse(clean)
    if parsed.scheme not in {"http", "https"}:
        return ""
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return parsed._replace(netloc=host, path=path, fragment="").geturl()


def same_domain(url: str, allowed_hosts: Iterable[str]) -> bool:
    host = urlparse(url).netloc.lower()
    for allowed in _scope_hosts(allowed_hosts):
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def _scope_hosts(allowed_hosts: Iterable[str]) -> set[str]:
    scoped: set[str] = set()
    for host in allowed_hosts:
        host = host.lower().strip(".")
        if not host:
            continue
        scoped.add(host)
        if host.startswith("www."):
            scoped.add(host[4:])
        else:
            scoped.add("www." + host)
    return scoped


def _looks_like_file(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith((
        ".pdf", ".csv", ".xlsx", ".xls", ".doc", ".docx", ".zip",
        ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg",
        ".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi",
        ".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac",
    ))


def _media_sources(base_url: str, tag: str, attrs: dict[str, str]) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    src = attrs.get("src", "").strip()
    data_src = attrs.get("data-src", "").strip()
    poster = attrs.get("poster", "").strip()
    srcset = attrs.get("srcset", "").strip()
    data_srcset = attrs.get("data-srcset", "").strip()
    style = attrs.get("style", "").strip()
    for candidate in (src, data_src):
        if candidate:
            sources.append((normalize_url(urljoin(base_url, candidate)), tag))
    if poster:
        sources.append((normalize_url(urljoin(base_url, poster)), "poster"))
    for candidate in _parse_srcset(srcset) + _parse_srcset(data_srcset):
        sources.append((normalize_url(urljoin(base_url, candidate)), f"{tag}-srcset"))
    for candidate in _extract_css_urls(style):
        sources.append((normalize_url(urljoin(base_url, candidate)), "background"))
    return sources


def _parse_srcset(value: str) -> list[str]:
    if not value:
        return []
    urls: list[str] = []
    for item in value.split(","):
        part = item.strip().split()[0:1]
        if part:
            urls.append(part[0])
    return urls


def _extract_css_urls(style: str) -> list[str]:
    if not style:
        return []
    return re.findall(r"url\((?:'|\")?(.*?)(?:'|\")?\)", style, flags=re.I)


def _is_hidden(attrs: dict[str, str]) -> bool:
    if attrs.get("hidden") is not None:
        return True
    if attrs.get("aria-hidden", "").lower() == "true":
        return True
    style = attrs.get("style", "").lower()
    return "display:none" in style or "visibility:hidden" in style or "opacity:0" in style
