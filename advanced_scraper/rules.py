from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class UrlRules:
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()

    def allowed(self, url: str) -> bool:
        if self.include and not any(re.search(pattern, url) for pattern in self.include):
            return False
        if self.exclude and any(re.search(pattern, url) for pattern in self.exclude):
            return False
        return True

