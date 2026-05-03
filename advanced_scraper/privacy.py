from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "gbraid",
    "wbraid",
    "fbclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "ref",
    "ref_src",
}


PII_PATTERNS = [
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[redacted-email]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"), "[redacted-phone]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[redacted-ssn]"),
]


def strip_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    return parsed._replace(query=urlencode(query, doseq=True)).geturl()


def redact_pii_text(value: str) -> str:
    redacted = value
    for pattern, replacement in PII_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_record(record: dict[str, object]) -> dict[str, object]:
    clean: dict[str, object] = {}
    for key, value in record.items():
        if isinstance(value, str):
            clean[key] = redact_pii_text(value)
        elif isinstance(value, list):
            clean[key] = [_redact_nested(item) for item in value]
        elif isinstance(value, dict):
            clean[key] = {str(k): _redact_nested(v) for k, v in value.items()}
        else:
            clean[key] = value
    return clean


def _redact_nested(value: object) -> object:
    if isinstance(value, str):
        return redact_pii_text(value)
    if isinstance(value, list):
        return [_redact_nested(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _redact_nested(v) for k, v in value.items()}
    return value

