from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .selectors import SelectorExtractor


@dataclass(frozen=True)
class SchemaField:
    name: str
    selector: str
    kind: str = "text"
    multiple: bool = False
    required: bool = False
    default: Any = ""


def parse_schema(schema_json: str) -> list[SchemaField]:
    raw = schema_json.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = data.get("fields", [])
    if not isinstance(data, list):
        return []
    fields: list[SchemaField] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        selector = str(item.get("selector") or "").strip()
        if not name or not selector:
            continue
        fields.append(
            SchemaField(
                name=name,
                selector=selector,
                kind=str(item.get("kind") or "text").strip().lower(),
                multiple=bool(item.get("multiple")),
                required=bool(item.get("required")),
                default=item.get("default", ""),
            )
        )
    return fields


def extract_schema(html: str, schema_json: str) -> tuple[dict[str, Any], list[str]]:
    fields = parse_schema(schema_json)
    if not fields:
        return {}, []
    css = tuple(field.selector for field in fields if field.selector and not field.selector.startswith("//"))
    xpath = tuple(field.selector for field in fields if field.selector.startswith("//"))
    extractor = SelectorExtractor(css=css, xpath=xpath)
    extractor.feed(html)
    values: dict[str, Any] = {}
    issues: list[str] = []
    for field in fields:
        key = f"css:{field.selector}" if not field.selector.startswith("//") else f"xpath:{field.selector}"
        raw = list(extractor.matches.get(key, []))
        value: Any
        if field.multiple:
            value = [coerce_value(item, field.kind) for item in raw]
            if not value and field.default != "":
                value = field.default
        else:
            value = coerce_value(raw[0], field.kind) if raw else field.default
        if field.required and (value is None or value == "" or value == []):
            issues.append(f"Missing required field: {field.name}")
        values[field.name] = value
    return values, issues


def coerce_value(value: Any, kind: str) -> Any:
    if value is None:
        return ""
    text = str(value).strip()
    if kind in {"int", "integer"}:
        try:
            return int(re.sub(r"[^0-9-]", "", text) or 0)
        except ValueError:
            return 0
    if kind in {"float", "number"}:
        try:
            return float(re.sub(r"[^0-9.\-]", "", text) or 0.0)
        except ValueError:
            return 0.0
    if kind in {"bool", "boolean"}:
        return text.lower() in {"1", "true", "yes", "on", "available", "in stock"}
    if kind == "list":
        return [part.strip() for part in re.split(r"[\n,|]+", text) if part.strip()]
    return text


def build_markdown(record: dict[str, Any]) -> str:
    title = str(record.get("title") or record.get("url") or "Untitled")
    lines = [f"# {title}"]
    if record.get("description"):
        lines.append(str(record["description"]))
    for heading in record.get("headings", [])[:20]:
        if isinstance(heading, dict):
            level = str(heading.get("level") or "h2").lower()
            text = str(heading.get("text") or "")
            if text:
                lines.append(f"{'#' * max(2, min(6, int(level[1]) if len(level) > 1 and level[1].isdigit() else 2))} {text}")
    body = str(record.get("text_preview") or record.get("text") or "")
    if body:
        lines.append(body.strip())
    hidden = str(record.get("hidden_text") or "")
    if hidden:
        lines.append("## Hidden Text")
        lines.append(hidden[:4000])
    comments = record.get("comments")
    if isinstance(comments, list) and comments:
        lines.append("## Comments")
        for comment in comments[:50]:
            lines.append(f"- {comment}")
    if record.get("links"):
        lines.append("## Links")
        for link in record.get("links", [])[:50]:
            lines.append(f"- {link}")
    if record.get("images"):
        lines.append("## Images")
        for image in record.get("images", [])[:30]:
            if isinstance(image, dict):
                lines.append(f"- {image.get('src', '')}")
            else:
                lines.append(f"- {image}")
    return "\n\n".join(line for line in lines if line)


def chunk_text(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    clean = " ".join(text.split())
    if not clean:
        return []
    if size <= 0:
        return [clean]
    chunks: list[str] = []
    start = 0
    length = len(clean)
    while start < length:
        end = min(length, start + size)
        chunks.append(clean[start:end])
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks
