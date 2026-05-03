from __future__ import annotations

import json
from urllib.request import Request, urlopen


def post_json(url: str, payload: dict[str, object], timeout: int = 20) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout):
        pass

