# pyright: strict
from __future__ import annotations

import json
import math
import sqlite3
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple, Optional

from .ufont import Font

DB_PATH = Path("~/.cache/icons.sqlite").expanduser()
DESCS_PATH = Path(__file__).parent.parent / "descriptions.json"


class FontDesc(NamedTuple):
    font_id: int
    name: str
    family: str
    file: str
    modified: datetime


class Icon(NamedTuple):
    icon_id: int
    name: str
    codepoint: int
    svg: str
    font: FontDesc

    def __repr__(self) -> str:
        return f"Icon(name='{self.name}', codepoint={self.codepoint})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "font": self.font.name,
            "family": self.font.family,
            "codepoint": self.codepoint,
            "svg": self.svg,
        }


class IconStore:
    __slots__ = ["descs_path", "db_path", "_conn", "_font_descs"]
    descs_path: Path
    db_path: Path
    _conn: sqlite3.Connection

    def __init__(
        self,
        descs_path: Optional[Path] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.descs_path = descs_path or DESCS_PATH
        self.db_path = db_path or DB_PATH
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(CREATE_TABLES)
        self._font_descs: Optional[dict[int, FontDesc]] = None
        if not self.get_icon_count():
            self.update()

    def get_icon_count(self) -> int:
        """Get number of stored icons"""
        result = self._conn.execute("SELECT count(*) FROM icons").fetchone()
        return result[0]

    def get_icon_names(self) -> list[str]:
        """Get all icon names"""
        result = self._conn.execute("SELECT name FROM icons").fetchall()
        return [fields[0] for fields in result]

    def get_icon(self, name: str) -> Optional[Icon]:
        """Get single icon by its name"""
        curr = self._conn.execute("SELECT * FROM icons WHERE name=?", (name,))
        icon_attrs = curr.fetchone()
        if icon_attrs is None:
            return None
        icon_id, icon_name, codepoint, svg_bin, font_id = icon_attrs
        font_desc = self.get_fonts().get(font_id)
        if font_desc is None:
            raise ValueError(f"Missing {font_id=}")
        return Icon(
            icon_id,
            icon_name,
            codepoint,
            zlib.decompress(svg_bin).decode(),
            font_desc,
        )

    def get_icons(self) -> list[Icon]:
        """Get all icons"""
        fonts_desc = self.get_fonts()
        curr = self._conn.execute("SELECT * FROM icons")
        icons_attrs = curr.fetchall()
        icons: list[Icon] = []
        for icon_id, icon_name, codepoint, svg_bin, font_id in icons_attrs:
            icon = Icon(
                icon_id,
                icon_name,
                codepoint,
                zlib.decompress(svg_bin).decode(),
                fonts_desc[font_id],
            )
            icons.append(icon)
        return icons

    def get_fonts(self) -> dict[int, FontDesc]:
        """List all available font descriptions"""
        if self._font_descs is not None:
            return self._font_descs
        self._font_descs = {}
        curr = self._conn.execute("SELECT * FROM fonts")
        for font_id, name, family, file, epoch in curr.fetchall():
            self._font_descs[font_id] = FontDesc(
                font_id,
                name,
                family,
                file,
                datetime.fromtimestamp(epoch),
            )
        return self._font_descs

    def update(self) -> None:
        """Ensures that sqlite db is up to date"""
        if not self.descs_path.exists():
            raise ValueError(f"descriptions file not found: {self.descs_path}")
        descs: list[dict[str, str]] = json.loads(self.descs_path.read_bytes())
        font_descs = {
            font_desc.name: font_desc for font_desc in self.get_fonts().values()
        }

        for desc in descs:
            font_name = desc["name"]
            metadata_path = self.descs_path.parent / desc["metadata"]
            font_path = self.descs_path.parent / desc["font"]
            modified = datetime.fromtimestamp(
                max(metadata_path.stat().st_mtime, font_path.stat().st_mtime)
            )
            metadata: Any = None

            # create font entry
            font_desc = font_descs.get(font_name)
            if font_desc is None:
                metadata = json.loads(metadata_path.read_bytes())
                font_desc = FontDesc(
                    font_id=-1,
                    name=font_name,
                    family=metadata["family"],
                    file=str(font_path),
                    modified=modified,
                )

            # update icons
            if font_desc.font_id < 0 or font_desc.modified < modified:
                # update font
                font_id = self._conn.execute(
                    UPSERT_FONTS,
                    (
                        font_desc.name,
                        font_desc.family,
                        font_desc.file,
                        math.ceil(modified.timestamp()),
                    ),
                ).fetchone()[0]
                font_desc = font_desc._replace(font_id=font_id)

                # update icons
                font = Font(font_path.read_bytes())
                if metadata is None:
                    metadata = json.loads(metadata_path.read_bytes())
                icons: list[tuple[str, int, bytes, int]] = []
                for icon_name, codepoint in metadata["names"].items():
                    glyph = font.glyph_by_codepoint(codepoint)
                    if glyph is None:
                        continue
                    icon_full_name = f"{font_name}-{icon_name}"
                    svg = zlib.compress(glyph.to_svg_path().encode())
                    icons.append((icon_full_name, codepoint, svg, font_desc.font_id))
                self._conn.executemany(UPSERT_ICONS, icons)
            self._conn.commit()

        # prune font descriptions cache
        self._font_descs = None


UPSERT_FONTS: str = """
INSERT INTO fonts(name, family, file, modified) VALUES(?, ?, ?, ?)
ON CONFLICT(name)
DO UPDATE SET
    family=excluded.family,
    file=excluded.file,
    modified=excluded.modified
RETURNING id;
"""

UPSERT_ICONS: str = """
INSERT INTO icons(name, codepoint, svg, font_id) VALUES(?, ?, ?, ?)
ON CONFLICT(name)
DO UPDATE SET
    codepoint=excluded.codepoint,
    svg=excluded.svg,
    font_id=excluded.font_id
;
"""

CREATE_TABLES: str = """
PRAGMA journal_mode=wal;

CREATE TABLE IF NOT EXISTS icons (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    codepoint INTEGER NOT NULL,
    svg       BLOB NOT NULL,
    font_id   INTEGER NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS icon_name ON icons(name);

CREATE TABLE IF NOT EXISTS fonts (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    family    TEXT NOT NULL,
    file      TEXT NOT NULL,
    modified  INTEGER NOT NULL
) STRICT;
"""
