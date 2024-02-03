#!/usr/bin/env python
# pyright: strict
from __future__ import annotations
import json
import re
import requests
import struct
import unicodedata
from pathlib import Path
from typing import Dict, Optional, NamedTuple, BinaryIO, Any, Tuple, List


class Desc(NamedTuple):
    name: str
    metadata: Path
    font: Path

    @staticmethod
    def from_name(name: str, root: Path) -> Desc:
        return Desc(
            name,
            root.joinpath(f"{name}.json"),
            root.joinpath(f"{name}.ttf"),
        )


def material(root: Path) -> Desc:
    desc = Desc.from_name("material", root)
    metadata = requests.get(
        "https://raw.githubusercontent.com/Templarian/MaterialDesign/master/meta.json"
    ).json()
    font = requests.get(
        "https://github.com/Templarian/MaterialDesign-Webfont/raw/master/fonts/materialdesignicons-webfont.ttf"
    ).content

    names: Dict[str, int] = {}
    for meta in metadata:
        name = meta["name"]
        codepoint = int(meta["codepoint"], 16)
        names[name] = codepoint
    with desc.metadata.open("w") as meta_file:
        json.dump(
            {
                "family": "Material Design Icons",
                "names": names,
            },
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def fluent(root: Path) -> Desc:
    desc = Desc.from_name("fluent", root)
    metadata = requests.get(
        "https://github.com/microsoft/fluentui-system-icons/raw/main/fonts/FluentSystemIcons-Resizable.json"
    ).json()
    font = requests.get(
        "https://github.com/microsoft/fluentui-system-icons/raw/main/fonts/FluentSystemIcons-Resizable.ttf"
    ).content

    names: Dict[str, int] = {}
    re_name = re.compile("ic_fluent_(.+)_20_(filled|regular)")
    for name, codepoint in metadata.items():
        match_name = re_name.match(name)
        if match_name is None:
            print(f"[fluent] unmatched: {name}")
            continue
        name = match_name.group(1).replace("_", "-")
        suffix = match_name.group(2)
        if suffix != "regular":
            name = f"{name}-{suffix}"
        names[name] = codepoint
    with desc.metadata.open("w") as meta_file:
        json.dump(
            {
                "family": "FluentSystemIcons-Resizable",
                "names": names,
            },
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def phosphor(root: Path) -> Desc:
    desc = Desc.from_name("phosphor", root)
    metadata = requests.get(
        "https://github.com/phosphor-icons/web/raw/master/src/regular/style.css"
    ).text
    font = requests.get(
        "https://github.com/phosphor-icons/web/raw/master/src/regular/Phosphor.ttf"
    ).content

    names: Dict[str, int] = {}
    for match in re.finditer(
        '^\\.ph\\.ph-([^:]*):.*\n\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        names[match.group(1)] = int(match.group(2), 16)
    with desc.metadata.open("w") as meta_file:
        json.dump(
            {"family": "Phosphor", "names": names},
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def remix(root: Path) -> Desc:
    desc = Desc.from_name("remix", root)
    metadata = requests.get(
        "https://github.com/Remix-Design/RemixIcon/raw/master/fonts/remixicon.css"
    ).text
    font = requests.get(
        "https://github.com/Remix-Design/RemixIcon/raw/master/fonts/remixicon.ttf"
    ).content

    # .ri-arrow-left-right-fill:before { content: "\ea61"; }
    names: Dict[str, int] = {}
    for match in re.finditer(
        '^\\.ri-([^:]+)-(fill|line):.*{\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        name = match.group(1)
        suffix = match.group(2)
        if suffix != "line":
            name = f"{name}-{suffix}"
        names[name] = int(match.group(3), 16)
    with desc.metadata.open("w") as meta_file:
        json.dump(
            {"family": "remixicon", "names": names},
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def typicons(root: Path) -> Desc:
    desc = Desc.from_name("typicons", root)
    metadata = requests.get(
        "https://raw.githubusercontent.com/stephenhutchings/typicons.font/master/src/font/typicons.json"
    ).json()
    font = requests.get(
        "https://github.com/stephenhutchings/typicons.font/raw/master/src/font/typicons.ttf"
    ).content

    with desc.metadata.open("w") as meta_file:
        json.dump(
            {
                "family": "typicons",
                "names": metadata,
            },
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def codicon(root: Path) -> Desc:
    desc = Desc.from_name("codicon", root)
    metadata = requests.get(
        "https://github.com/microsoft/vscode-codicons/raw/main/dist/codicon.css"
    ).text
    font = requests.get(
        "https://github.com/microsoft/vscode-codicons/raw/main/dist/codicon.ttf"
    ).content

    # .codicon-gist-new:before { content: "\ea60" }
    names: Dict[str, int] = {}
    for match in re.finditer(
        '^\\.codicon-([^:]+):.*{\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        names[match.group(1)] = int(match.group(2), 16)
    with desc.metadata.open("w") as meta_file:
        json.dump(
            {"family": "codicon", "names": names},
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def awesome(path: Path) -> Desc:
    desc = Desc.from_name("awesome", path)
    # inspect https://fontawesome.com to get this URLs
    version = "6.4.0"
    font = requests.get(
        f"https://site-assets.fontawesome.com/releases/v{version}/webfonts/fa-regular-400.ttf"
    ).content
    metadata = requests.get(
        f"https://site-assets.fontawesome.com/releases/v{version}/css/all.css"
    ).text

    # single line like .fa-fill-drip:before{content:"\f576"}
    names: Dict[str, int] = {}
    for match in re.finditer(
        '\\.fa-([^:{}\\.]+):before{\\s*content:\\s*"\\\\([^"]+)"[^}]*}',
        metadata,
        re.MULTILINE,
    ):
        names[match.group(1)] = int(match.group(2), 16)
    with desc.metadata.open("w") as meta_file:
        json.dump(
            {"family": "Font Awesome 6 Pro", "names": names},
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def weather(root: Path) -> Desc:
    desc = Desc.from_name("weather", root)
    font = requests.get(
        "https://github.com/erikflowers/weather-icons/raw/master/font/weathericons-regular-webfont.ttf"
    ).content
    metadata = requests.get(
        "https://github.com/erikflowers/weather-icons/raw/master/css/weather-icons.css"
    ).text

    names: Dict[str, int] = {}
    for match in re.finditer(
        '^\\.wi-([^:]*):.*\n\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        names[match.group(1)] = int(match.group(2), 16)
    with desc.metadata.open("w") as meta_file:
        json.dump(
            {"family": "Weather Icons", "names": names},
            meta_file,
            indent=2,
        )

    with desc.font.open("wb") as font_file:
        font_file.write(font)

    return desc


def notoemoji(root: Path) -> Desc:
    desc = Desc.from_name("notoemoji", root)
    font = Font(desc.font)

    names: Dict[str, int] = {}
    skip = {
        "uni000d",
        "zero-width-joiner",
        "variation-selector-15",
        "variation-selector-16",
    }
    bad_name_regex = re.compile("^u(ni)?([0-9A-Fa-f]+)$")
    for name, codepoint in font.name_to_codepoint.items():
        bad_match = bad_name_regex.match(name)
        if bad_match:
            char = chr(int(bad_match.group(2), 16))
            name = unicodedata.name(char, name).lower().replace(" ", "-")
        else:
            name = camel_to_dash(name)
        if name.endswith(".tag") or name in skip:
            continue
        names[name] = codepoint

    with desc.metadata.open("w") as meta_file:
        json.dump(
            {"family": font.name["family"], "names": names},
            meta_file,
            indent=2,
        )

    return desc


def camel_to_dash(value: str) -> str:
    split = list(i for i, (a, b) in enumerate(zip(value, value.lower())) if a != b)
    split = [0, *split, len(value)]
    value = value.lower()
    return "-".join(
        filter(None, (value[start:end] for start, end in zip(split, split[1:])))
    )


class Reader:
    def __init__(self, file: BinaryIO):
        self.file = file

    def read(self, size: int, at: Optional[int] = None) -> bytes:
        if at is not None:
            self.file.seek(at)
        return self.file.read(size)

    def read_string(self, size: int, at: Optional[int] = None) -> str:
        return self.read(size, at).decode()

    def seek(self, target: int, whence: int = 0) -> None:
        self.file.seek(target, whence)

    def read_struct(self, format: str, at: Optional[int] = None) -> Tuple[Any]:
        if at is not None:
            self.file.seek(at)
        st = struct.Struct(format)
        return st.unpack(self.file.read(st.size))

    def read_u8(self) -> int:
        return self.file.read(1)[0]

    def read_i8(self) -> int:
        return self.read_struct(">b")[0]

    def read_u16(self) -> int:
        return self.read_struct(">H")[0]

    def read_i16(self) -> int:
        return self.read_struct(">h")[0]

    def read_u32(self) -> int:
        return self.read_struct(">I")[0]

    def read_i32(self) -> int:
        return self.read_struct(">i")[0]

    def read_u64(self) -> int:
        return self.read_struct(">Q")[0]

    def read_fixed(self) -> float:
        return self.read_i32() / 65536


class FontTable(NamedTuple):
    checksum: int
    offset: int
    length: int


class FontHead(NamedTuple):
    versoin: Tuple[int, int]
    font_revision: int


class Font:
    """Simple font reader

    References:
        - https://tchayen.github.io/posts/ttf-file-parsing
        - https://learn.microsoft.com/en-us/typography/opentype/spec/otff#organization-of-an-opentype-font
    """

    def __init__(self, path: Path):
        reader = Reader(path.expanduser().open("rb"))
        self.reader = reader

        reader.read_u32()  # sfntVersion
        num_tables = reader.read_u16()  # numTables
        reader.read_u16()  # searchRange
        reader.read_u16()  # entrySelector
        reader.read_u16()  # rangeShift
        # at table records
        self.tables: Dict[str, FontTable] = {}
        for _ in range(num_tables):
            tag = reader.read_string(4)
            self.tables[tag] = FontTable(
                reader.read_u32(),
                reader.read_u32(),
                reader.read_u32(),
            )

        # Maximum Profile
        maxp = self.tables["maxp"]
        reader.seek(maxp.offset + 4)  # offset + version
        self.glyph_count = reader.read_u16()  # numGlyphs

        self.index_to_codepoint = self.parse_cmap()
        self.index_to_name = self.parse_post()

        self.name_to_codepoint: Dict[str, int] = {}
        for index in range(self.glyph_count):
            codepoint = self.index_to_codepoint.get(index)
            name = self.index_to_name.get(index)
            if name is None or codepoint is None or codepoint == 0:
                continue
            self.name_to_codepoint[name] = codepoint

        self.name = self.parse_name()

    def parse_cmap(self) -> Dict[int, int]:
        """Character Map

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/cmap
        """
        cmap = self.tables["cmap"]
        self.reader.seek(cmap.offset)
        self.reader.read_u16()  # version

        # find unicode sub-table
        unicode_table_offset = 0
        subtables: List[Tuple[int, int, int]] = []
        num_tables = self.reader.read_u16()
        for _ in range(num_tables):
            platform_id = self.reader.read_u16()  # 0 - unicode
            encoding_id = self.reader.read_u16()
            subtable_offset = self.reader.read_u32()
            subtables.append((platform_id, encoding_id, subtable_offset))
            if platform_id == 0 and encoding_id == 4:
                unicode_table_offset = subtable_offset + cmap.offset
        # breakpoint()
        if not unicode_table_offset:
            raise ValueError(
                f"Only support unicode (0) format (4) cmap tables: {subtables}"
            )

        # sub-table header
        self.reader.seek(unicode_table_offset)
        subtable_format = self.reader.read_u16()
        if subtable_format != 12:  # segmented coverage
            raise ValueError(
                f"Only suppor segmented coverage (12) cmap table: {subtable_format}"
            )
        self.reader.read_u16()  # reserved
        self.reader.read_u32()  # length
        self.reader.read_u32()  # language

        # groups
        num_groups = self.reader.read_u32()
        glyph_to_codepoint: Dict[int, int] = {}
        for _ in range(num_groups):
            codepoint_start = self.reader.read_u32()
            codepoint_end = self.reader.read_u32()
            glyph_index = self.reader.read_u32()
            for codepoint in range(codepoint_start, codepoint_end + 1):
                glyph_to_codepoint[glyph_index] = codepoint
                glyph_index += 1

        return glyph_to_codepoint

    def parse_post(self) -> Dict[int, str]:
        post = self.tables["post"]
        self.reader.seek(post.offset)

        version = self.reader.read_fixed()
        if version != 2:
            return {}
        self.reader.read(28)  # skip header

        # https://learn.microsoft.com/en-us/typography/opentype/spec/post#version-20
        glyph_count = self.reader.read_u16()
        glyph_to_index: Dict[int, int] = {}
        for glyph_index in range(glyph_count):
            name_index = self.reader.read_u16()
            if name_index >= 258:
                glyph_to_index[glyph_index] = name_index - 258

        names: List[str] = []
        for _ in range(max(glyph_to_index.values()) + 1):
            length = self.reader.read_u8()
            names.append(self.reader.read_string(length))

        return {glyph: names[index] for glyph, index in glyph_to_index.items()}

    def parse_name(self) -> Dict[str, str]:
        table = self.tables["name"]
        self.reader.seek(table.offset)

        self.reader.read_u16()  # version
        record_count = self.reader.read_u16()
        storage_offset = self.reader.read_u16()

        class NameRecord(NamedTuple):
            platfrom_id: int
            encoding_id: int
            langauge_id: int
            name_id: int
            lenght: int
            offset: int

        records: List[NameRecord] = []
        for _ in range(record_count):
            record = NameRecord(
                self.reader.read_u16(),
                self.reader.read_u16(),
                self.reader.read_u16(),
                self.reader.read_u16(),
                self.reader.read_u16(),
                self.reader.read_u16(),
            )
            id = (record.platfrom_id, record.langauge_id, record.encoding_id)
            if id not in {(3, 1033, 1), (3, 1033, 10)}:
                continue
            records.append(record)

        name_ids = {
            0: "copyright",
            1: "family",
            2: "subfamily",
            3: "font_id",
            4: "fullname",
            5: "version",
        }
        names: Dict[str, str] = {}
        for record in records:
            name = name_ids.get(record.name_id)
            if not name:
                continue
            names[name] = self.reader.read(
                record.lenght, table.offset + storage_offset + record.offset
            ).decode("utf-16-be")

        return names


def main() -> None:
    descriptions: List[Any] = []
    root = Path("fonts")
    root.mkdir(exist_ok=True)
    for updater in [
        material,
        fluent,
        phosphor,
        remix,
        codicon,
        awesome,
        weather,
        typicons,
        notoemoji,
    ]:
        print(updater.__name__)
        desc = updater(root)
        descriptions.append(
            {
                "name": desc.name,
                "metadata": str(desc.metadata),
                "font": str(desc.font),
            }
        )

    with open("descriptions.json", "w") as all_file:
        json.dump(descriptions, all_file, indent=2)


if __name__ == "__main__":
    main()
