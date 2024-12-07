# pyright: strict
from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
import unicodedata
from pathlib import Path
from typing import NamedTuple, Any
from collections.abc import Callable

from .ufont import Font


class Desc(NamedTuple):
    name: str
    metadata: Path
    font: Path
    family: str

    @staticmethod
    def from_name(root: Path, name: str, family: str) -> Desc:
        return Desc(
            name,
            root.joinpath(f"{name}.json"),
            root.joinpath(f"{name}.ttf"),
            family,
        )


class FontData:
    name: str
    family: str
    icon_to_codepoint: dict[str, int]
    font_data: bytes

    def __init__(
        self,
        name: str,
        icon_to_codepoint: dict[str, int],
        font_data: bytes,
    ) -> None:
        self.name = name
        self.font_data = font_data
        font = Font(self.font_data)
        self.icon_to_codepoint = {}
        for icon, codepoint in icon_to_codepoint.items():
            glyph = font.glyph_by_codepoint(codepoint)
            if glyph is None or glyph.contours_count == 0:
                continue
            self.icon_to_codepoint[icon] = codepoint
        self.family = font.name.family

    def __repr__(self) -> str:
        return f"FontData(name={self.name}, family={self.family}, glyph_count={len(self.icon_to_codepoint)})"

    def save(self, root: Path) -> None:
        with open(root / f"{self.name}.json", "w") as metadata_file:
            json.dump(
                {
                    "family": self.family,
                    "names": self.icon_to_codepoint,
                },
                metadata_file,
                indent=2,
            )
        with open(root / f"{self.name}.ttf", "wb") as font_file:
            font_file.write(self.font_data)

    @staticmethod
    def load(name: str, root: Path) -> FontData | None:
        metadata_path = root / f"{name}.json"
        if not metadata_path.exists():
            return None
        with metadata_path.open() as metadata_file:
            metadata = json.load(metadata_file)

        font_path = root / f"{name}.ttf"
        if not font_path.exists():
            return None
        font_data = font_path.read_bytes()

        return FontData(name, metadata["names"], font_data)

    def hash(self) -> str:
        h = hashlib.sha256()
        h.update(self.name.encode())
        for name, codepoint in self.icon_to_codepoint.items():
            h.update(name.encode())
            h.update(str(codepoint).encode())
        h.update(self.font_data)
        return h.hexdigest()


def fetch_material() -> FontData:
    metadata = http_get(
        "https://raw.githubusercontent.com/Templarian/MaterialDesign/master/meta.json",
        json=True,
    )
    font_data = http_get(
        "https://github.com/Templarian/MaterialDesign-Webfont/raw/master/fonts/materialdesignicons-webfont.ttf"
    )

    icon_to_codepoint: dict[str, int] = {}
    for meta in metadata:
        name = meta["name"]
        codepoint = int(meta["codepoint"], 16)
        icon_to_codepoint[name] = codepoint

    return FontData("material", icon_to_codepoint, font_data)


def fetch_fluent() -> FontData:
    metadata = http_get(
        "https://github.com/microsoft/fluentui-system-icons/raw/main/fonts/FluentSystemIcons-Resizable.json",
        json=True,
    )
    font_data = http_get(
        "https://github.com/microsoft/fluentui-system-icons/raw/main/fonts/FluentSystemIcons-Resizable.ttf"
    )

    icon_to_codepoint: dict[str, int] = {}
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
        icon_to_codepoint[name] = codepoint

    return FontData("fluent", icon_to_codepoint, font_data)


def fetch_phosphor() -> FontData:
    metadata = http_get(
        "https://github.com/phosphor-icons/web/raw/master/src/regular/style.css"
    ).decode()
    font_data = http_get(
        "https://github.com/phosphor-icons/web/raw/master/src/regular/Phosphor.ttf"
    )

    icon_to_codepoint: dict[str, int] = {}
    for match in re.finditer(
        '^\\.ph\\.ph-([^:]*):.*\n\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        icon_to_codepoint[match.group(1)] = int(match.group(2), 16)

    return FontData("phosphor", icon_to_codepoint, font_data)


def fetch_remix() -> FontData:
    metadata = http_get(
        "https://github.com/Remix-Design/RemixIcon/raw/master/fonts/remixicon.css"
    ).decode()
    font_data = http_get(
        "https://github.com/Remix-Design/RemixIcon/raw/master/fonts/remixicon.ttf"
    )

    # .ri-arrow-left-right-fill:before { content: "\ea61"; }
    icon_to_codepoint: dict[str, int] = {}
    for match in re.finditer(
        '^\\.ri-([^:]+)-(fill|line):.*{\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        name = match.group(1)
        suffix = match.group(2)
        if suffix != "line":
            name = f"{name}-{suffix}"
        icon_to_codepoint[name] = int(match.group(3), 16)

    return FontData("remix", icon_to_codepoint, font_data)


def fetch_typicons() -> FontData:
    metadata = http_get(
        "https://raw.githubusercontent.com/stephenhutchings/typicons.font/master/src/font/typicons.json",
        json=True,
    )
    font_data = http_get(
        "https://github.com/stephenhutchings/typicons.font/raw/master/src/font/typicons.ttf"
    )

    return FontData("typicons", metadata, font_data)


def fetch_codicons() -> FontData:
    metadata, font_data = npm_get(
        "@vscode/codicons",
        ["dist/codicon.css", "dist/codicon.ttf"],
    )

    # .codicon-gist-new:before { content: "\ea60" }
    icon_to_codepoint: dict[str, int] = {}
    for match in re.finditer(
        '^\\.codicon-([^:]+):.*{\\s+content:\\s+"\\\\(.*)"',
        metadata.decode(),
        re.MULTILINE,
    ):
        icon_to_codepoint[match.group(1)] = int(match.group(2), 16)

    return FontData("codicon", icon_to_codepoint, font_data)


def fetch_awesome() -> FontData:
    # inspect https://fontawesome.com to get this URLs
    version = "6.5.1"
    font_data = http_get(
        f"https://site-assets.fontawesome.com/releases/v{version}/webfonts/fa-regular-400.ttf"
    )
    metadata = http_get(
        f"https://site-assets.fontawesome.com/releases/v{version}/css/all.css"
    ).decode()

    # single line like .fa-fill-drip:before{content:"\f576"}
    icon_to_codepoint: dict[str, int] = {}
    for match in re.finditer(
        '\\.fa-([^:{}\\.]+):before{\\s*content:\\s*"\\\\([^"]+)"[^}]*}',
        metadata,
        re.MULTILINE,
    ):
        icon_to_codepoint[match.group(1)] = int(match.group(2), 16)

    return FontData("awesome", icon_to_codepoint, font_data)


def fetch_weather() -> FontData:
    font_data = http_get(
        "https://github.com/erikflowers/weather-icons/raw/master/font/weathericons-regular-webfont.ttf"
    )
    metadata = http_get(
        "https://github.com/erikflowers/weather-icons/raw/master/css/weather-icons.css"
    ).decode()

    icon_to_codepoint: dict[str, int] = {}
    for match in re.finditer(
        '^\\.wi-([^:]*):.*\n\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        icon_to_codepoint[match.group(1)] = int(match.group(2), 16)

    return FontData("weather", icon_to_codepoint, font_data)


def fetch_notoemoji() -> FontData:
    # If github link is broken in the future
    #   - GET https://fonts.google.com/download/list?family=Noto%20Emoji
    #   - first line is garbage for some reason the rest is JSON
    #   - find "filename": "NotoEmoji-VariableFont_wght.ttf"
    font_data = http_get(
        "https://github.com/google/fonts/raw/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf"
    )

    font = Font(font_data)
    icon_to_codepoint: dict[str, int] = {}
    skip = {
        "uni000d",
        "zero-width-joiner",
        "variation-selector-15",
        "variation-selector-16",
    }
    bad_name_regex = re.compile("^u(ni)?([0-9A-Fa-f]+)$")
    for name, codepoint in font.codepoint_by_name().items():
        bad_match = bad_name_regex.match(name)
        if bad_match:
            char = chr(int(bad_match.group(2), 16))
            name = unicodedata.name(char, name).lower().replace(" ", "-")
        else:
            name = camel_to_kebab(name)
        if name.endswith(".tag") or name in skip:
            continue
        icon_to_codepoint[name] = codepoint

    return FontData("notoemoji", icon_to_codepoint, font_data)


def fetch_tabler() -> FontData:
    font_data = npm_get("@tabler/icons-webfont", ["dist/fonts/tabler-icons.ttf"])[0]

    font = Font(font_data)
    icon_to_codepoint = font.codepoint_by_name()
    return FontData("tabler", icon_to_codepoint, font_data)


def fetch_tabler_filled() -> FontData:
    font_data = npm_get(
        "@tabler/icons-webfont", ["dist/fonts/tabler-icons-filled.ttf"]
    )[0]

    font = Font(font_data)
    icon_to_codepoint = font.codepoint_by_name()
    return FontData("tabler-filled", icon_to_codepoint, font_data)


FONT_FETCHERS: dict[str, Callable[[], FontData]] = {
    "material": fetch_material,
    "fluent": fetch_fluent,
    "phosphor": fetch_phosphor,
    "remix": fetch_remix,
    "codicon": fetch_codicons,
    "tabler": fetch_tabler,
    # conflicts with `tabler`
    # "tabler-filled": fetch_tabler_filled,
    "awesome": fetch_awesome,
    "weather": fetch_weather,
    "typicons": fetch_typicons,
    "notoemoji": fetch_notoemoji,
}


def camel_to_kebab(value: str) -> str:
    """Convert CamelCase to kebab-case"""
    split = list(i for i, (a, b) in enumerate(zip(value, value.lower())) if a != b)
    split = [0, *split, len(value)]
    value = value.lower()
    return "-".join(
        filter(None, (value[start:end] for start, end in zip(split, split[1:])))
    )


def npm_get(name: str, files: list[str]) -> list[bytes]:
    """Fetch latest npm package with the provided name and extract files"""
    desc = http_get(f"https://registry.npmjs.org/{name}/latest", json=True)
    tarball_url = desc["dist"]["tarball"]
    tarball_file = io.BytesIO(http_get(tarball_url))
    tar = tarfile.open(fileobj=tarball_file)
    result: list[bytes] = []
    for file in files:
        file = f"package/{file}"
        data = tar.extractfile(file)
        if data is None:
            raise ValueError(f"[npm] {name}: file not found {file}")
        result.append(data.read())
    return result


def http_get(url: str, json: bool = False) -> Any:
    import requests

    response = requests.get(url)
    if json:
        return response.json()
    return response.content
