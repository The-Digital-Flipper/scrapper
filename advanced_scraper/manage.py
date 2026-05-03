from __future__ import annotations

import argparse
from pathlib import Path

from .archive import create_site_archive, import_site_archive, list_archives, list_imports


def main() -> int:
    parser = argparse.ArgumentParser(prog="advanced-scraper-manage")
    sub = parser.add_subparsers(dest="command", required=True)

    archive = sub.add_parser("archive", help="Create a portable site zip archive")
    archive.add_argument("--name", required=True)
    archive.add_argument("--output", required=True)
    archive.add_argument("--event-log")
    archive.add_argument("--dom-dir")
    archive.add_argument("--asset-dir")

    import_cmd = sub.add_parser("import-archive", help="Import a portable site zip archive")
    import_cmd.add_argument("zip_path")

    sub.add_parser("list-archives", help="List saved archive zips")
    sub.add_parser("list-imports", help="List imported archives")

    args = parser.parse_args()
    if args.command == "archive":
        path = create_site_archive(
            name=args.name,
            output_path=Path(args.output),
            event_log_path=Path(args.event_log) if args.event_log else None,
            dom_dir=Path(args.dom_dir) if args.dom_dir else None,
            asset_dir=Path(args.asset_dir) if args.asset_dir else None,
        )
        print(path)
        return 0
    if args.command == "import-archive":
        print(import_site_archive(Path(args.zip_path)))
        return 0
    if args.command == "list-archives":
        for path in list_archives():
            print(path)
        return 0
    if args.command == "list-imports":
        for path in list_imports():
            print(path)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

