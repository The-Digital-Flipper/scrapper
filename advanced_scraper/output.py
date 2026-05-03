from __future__ import annotations

import csv
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


class ResultWriter:
    def __init__(self, output: Path, fmt: str) -> None:
        self.output = output
        self.fmt = fmt
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self._csv_file = None
        self._csv_writer = None
        self._xml_root = None
        self._sqlite = None

    def __enter__(self) -> "ResultWriter":
        if self.fmt == "xml":
            self._xml_root = ET.Element("records")
        if self.fmt == "csv":
            self._csv_file = self.output.open("w", newline="", encoding="utf-8")
            self._csv_writer = csv.DictWriter(
                self._csv_file,
                fieldnames=[
                    "url",
                    "status",
                    "content_type",
                    "title",
                    "description",
                    "canonical",
                    "content_hash",
                    "word_count",
                    "link_count",
                    "media_count",
                    "comments_count",
                    "hidden_text",
                    "error",
                ],
            )
            self._csv_writer.writeheader()
        if self.fmt == "sqlite":
            self._sqlite = sqlite3.connect(self.output)
            self._sqlite.execute(
                """
                create table if not exists records (
                    id integer primary key autoincrement,
                    url text,
                    status text,
                    title text,
                    description text,
                    canonical text,
                    content_hash text,
                    word_count integer,
                    link_count integer,
                    error text,
                    record_json text not null
                )
                """
            )
            self._sqlite.commit()
        return self

    def __exit__(self, *_args: object) -> None:
        if self._xml_root is not None:
            ET.ElementTree(self._xml_root).write(self.output, encoding="utf-8", xml_declaration=True)
        if self._csv_file:
            self._csv_file.close()
        if self._sqlite:
            self._sqlite.commit()
            self._sqlite.close()

    def write(self, record: dict[str, Any]) -> None:
        if self.fmt == "jsonl":
            with self.output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            return

        if self.fmt == "sqlite":
            assert self._sqlite is not None
            self._sqlite.execute(
                """
                insert into records(url, status, title, description, canonical, content_hash, word_count, link_count, error, record_json)
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("url", ""),
                    record.get("status", ""),
                    record.get("title", ""),
                    record.get("description", ""),
                    record.get("canonical", ""),
                    record.get("content_hash", ""),
                    int(record.get("word_count") or 0),
                    len(record.get("links", [])),
                    record.get("error", ""),
                    json.dumps(record, ensure_ascii=False, sort_keys=True),
                ),
            )
            return

        if self.fmt == "xml":
            assert self._xml_root is not None
            item = ET.SubElement(self._xml_root, "record")
            for key in (
                "url",
                "depth",
                "status",
                "content_type",
                "title",
                "description",
                "canonical",
                "content_hash",
                "word_count",
                "error",
                "lang",
                "author",
                "published_time",
                "meta_keywords",
                "media_count",
                "comments_count",
                "hidden_text",
            ):
                child = ET.SubElement(item, key)
                child.text = str(record.get(key, ""))
            return

        assert self._csv_writer is not None
        self._csv_writer.writerow(
            {
                "url": record.get("url", ""),
                "status": record.get("status", ""),
                "content_type": record.get("content_type", ""),
                "title": record.get("title", ""),
                "description": record.get("description", ""),
                "canonical": record.get("canonical", ""),
                "content_hash": record.get("content_hash", ""),
                "word_count": record.get("word_count", 0),
                "link_count": len(record.get("links", [])),
                "media_count": len(record.get("media", [])),
                "comments_count": len(record.get("comments", [])),
                "hidden_text": record.get("hidden_text", ""),
                "error": record.get("error", ""),
            }
        )
