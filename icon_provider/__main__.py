#!/usr/bin/env python
# pyright: strict
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from collections.abc import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from icon_provider.fetch import FONT_FETCHERS, FontData
from icon_provider.store import Icon, IconStore

ROOT_DEFAULT = Path(__file__).resolve().parent.parent
DESC_FILE = "descriptions.json"
FONT_DIR = "fonts"


@contextlib.contextmanager
def timer(msg: str) -> Iterator[None]:
    start = time.time()
    try:
        sys.stderr.write(f"{msg} ")
        sys.stderr.flush()
        yield
    finally:
        end = time.time()
        sys.stderr.write(f"{end - start:.2f}s\n")


def subcommand_update(opts: argparse.Namespace) -> None:
    root: Path = opts.root
    font_root = root / FONT_DIR
    descs_path = root / DESC_FILE

    if not opts.db_only:
        font_descs: list[dict[str, str]] = []
        font_name_len = max(map(len, FONT_FETCHERS))
        for name, fetcher in FONT_FETCHERS.items():
            with timer(f"[fetching] {name.ljust(font_name_len)} "):
                font_data = fetcher()
                font_data_prev = FontData.load(name, font_root)
                if font_data_prev is None or font_data.hash() != font_data_prev.hash():
                    font_data.save(font_root)
                font_descs.append(
                    {
                        "name": name,
                        "family": font_data.family,
                        "metadata": os.path.join(FONT_DIR, f"{name}.json"),
                        "font": os.path.join(FONT_DIR, f"{name}.ttf"),
                    }
                )
        with descs_path.open("w") as desc_file:
            json.dump(font_descs, desc_file, indent=2)

    with timer("[db] updating database "):
        icon_store = IconStore(descs_path)
        icon_store.update()
    sys.stderr.write(f"[db] icons count: {icon_store.get_icon_count()}\n")


def subcommand_get(opts: argparse.Namespace) -> None:
    icon_store = IconStore(opts.root / DESC_FILE)
    icons: list[Icon] = []
    for name in opts.icon_name:
        icon = icon_store.get_icon(name)
        if icon is None:
            sys.stderr.write(f"Icon not found: {name}\n")
            continue
        icons.append(icon)
    icons_format(opts.format, icons)


def subcommand_select(opts: argparse.Namespace) -> None:
    from icon_provider.sweep_select import select

    icon_store = IconStore(opts.root / DESC_FILE)
    selected = asyncio.run(select(icon_store))
    icons_format(opts.format, selected)


def icons_format_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--format",
        choices=["svg-path", "svg", "json"],
        default="svg-path",
        help="format of the output",
    )


def icons_format(format: str, icons: list[Icon]) -> None:
    match format:
        case "svg-path":
            for icon in icons:
                print(icon.svg)
        case "svg":
            for icon in icons:
                print('<svg width="100" height="100" viewBox="0 0 100 100"')
                print('     xmlns="http://www.w3.org/2000/svg">')
                print(f'<path id="{icon.name}" d="{icon.svg}"/>')
                print("</svg>")
        case "json":
            descs: dict[str, dict[str, Any]] = {}
            for icon in icons:
                descs[icon.name] = icon.to_dict()
            json.dump(descs, sys.stdout, indent=2)
            print()
        case _:
            sys.stderr.write(f"Unkown format: {format}\n")
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Utility to update and retrieve icons")
    parser.add_argument(
        "-r",
        "--root",
        type=Path,
        default=ROOT_DEFAULT,
        help=f"path to directory with {DESC_FILE}",
    )
    subparsers = parser.add_subparsers(required=True)

    parser_update = subparsers.add_parser(
        "update", description="fetch and update fonts"
    )
    parser_update.add_argument(
        "--db-only",
        action="store_true",
        help="update database without fetching fonts",
    )
    parser_update.set_defaults(fn=subcommand_update)

    parser_get = subparsers.add_parser("get", description="get icon")
    icons_format_arg(parser_get)
    parser_get.add_argument("icon_name", nargs="+", help="icon name")
    parser_get.set_defaults(fn=subcommand_get)

    parser_select = subparsers.add_parser("select", description="select icon")
    icons_format_arg(parser_select)
    parser_select.set_defaults(fn=subcommand_select)

    opts = parser.parse_args()
    opts.fn(opts)


if __name__ == "__main__":
    main()
