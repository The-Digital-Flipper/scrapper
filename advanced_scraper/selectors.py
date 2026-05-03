from __future__ import annotations

from html.parser import HTMLParser


class SelectorExtractor(HTMLParser):
    """Small dependency-free selector extractor.

    Supports useful CSS subsets: tag, .class, #id, tag.class, tag#id.
    Supports simple XPath subsets: //tag, //*[@id='x'], //tag[@class='x'].
    """

    def __init__(self, css: tuple[str, ...] = (), xpath: tuple[str, ...] = ()) -> None:
        super().__init__(convert_charrefs=True)
        self.css = css
        self.xpath = xpath
        self.matches: dict[str, list[str]] = {f"css:{item}": [] for item in css}
        self.matches.update({f"xpath:{item}": [] for item in xpath})
        self._active: list[tuple[str, str, int]] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        attrs_dict = {k.lower(): v or "" for k, v in attrs}
        for selector in self.css:
            if _matches_css(selector, tag, attrs_dict):
                self._active.append((f"css:{selector}", "", self._depth))
        for selector in self.xpath:
            if _matches_xpath(selector, tag, attrs_dict):
                self._active.append((f"xpath:{selector}", "", self._depth))

    def handle_endtag(self, _tag: str) -> None:
        remaining: list[tuple[str, str, int]] = []
        for key, text, depth in self._active:
            if depth == self._depth:
                clean = " ".join(text.split())
                if clean:
                    self.matches[key].append(clean)
            else:
                remaining.append((key, text, depth))
        self._active = remaining
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if not self._active:
            return
        self._active = [(key, text + " " + data, depth) for key, text, depth in self._active]


def _matches_css(selector: str, tag: str, attrs: dict[str, str]) -> bool:
    selector = selector.strip()
    wanted_tag = ""
    wanted_id = ""
    wanted_class = ""
    if "#" in selector:
        wanted_tag, wanted_id = selector.split("#", 1)
    elif "." in selector:
        wanted_tag, wanted_class = selector.split(".", 1)
    elif selector.startswith("#"):
        wanted_id = selector[1:]
    elif selector.startswith("."):
        wanted_class = selector[1:]
    else:
        wanted_tag = selector
    if wanted_tag and wanted_tag.lower() != tag.lower():
        return False
    if wanted_id and attrs.get("id") != wanted_id:
        return False
    if wanted_class:
        classes = set(attrs.get("class", "").split())
        if wanted_class not in classes:
            return False
    return True


def _matches_xpath(selector: str, tag: str, attrs: dict[str, str]) -> bool:
    selector = selector.strip()
    if not selector.startswith("//"):
        return False
    body = selector[2:]
    if body == "*":
        return True
    if "[@" not in body:
        return body.lower() == tag.lower()
    wanted_tag, predicate = body.split("[@", 1)
    if wanted_tag and wanted_tag != "*" and wanted_tag.lower() != tag.lower():
        return False
    predicate = predicate.rstrip("]")
    if "=" not in predicate:
        return False
    attr, value = predicate.split("=", 1)
    value = value.strip("'\"")
    if attr == "class":
        return value in set(attrs.get("class", "").split())
    return attrs.get(attr) == value

