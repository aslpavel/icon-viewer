#!/usr/bin/env python
# pyright: strict
from __future__ import annotations
import json
import re
import requests
from typing import Dict, NamedTuple


class Desc(NamedTuple):
    name: str
    metadata: str
    font: str


def material() -> Desc:
    desc = Desc("material", "material.json", "material.ttf")
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
    with open(desc.metadata, "w") as meta_file:
        json.dump(
            {
                "family": "Material Design Icons",
                "names": names,
            },
            meta_file,
            indent=2,
        )

    with open(desc.font, "wb") as font_file:
        font_file.write(font)

    return desc


def fluent() -> Desc:
    desc = Desc("fluent", "fluent.json", "fluent.ttf")
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
    with open(desc.metadata, "w") as meta_file:
        json.dump(
            {
                "family": "FluentSystemIcons-Resizable",
                "names": names,
            },
            meta_file,
            indent=2,
        )

    with open(desc.font, "wb") as font_file:
        font_file.write(font)

    return desc


def phosphor() -> Desc:
    desc = Desc("phosphor", "phosphor.json", "phosphor.ttf")
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
    with open(desc.metadata, "w") as meta_file:
        json.dump(
            {"family": "Phosphor", "names": names},
            meta_file,
            indent=2,
        )

    with open(desc.font, "wb") as font_file:
        font_file.write(font)

    return desc


def remix() -> Desc:
    desc = Desc("remix", "remix.json", "remix.ttf")
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
    with open(desc.metadata, "w") as meta_file:
        json.dump(
            {"family": "remixicon", "names": names},
            meta_file,
            indent=2,
        )

    with open(desc.font, "wb") as font_file:
        font_file.write(font)

    return desc


def codicon() -> Desc:
    desc = Desc("codicon", "codicon.json", "codicon.ttf")
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
    with open(desc.metadata, "w") as meta_file:
        json.dump(
            {"family": "codicon", "names": names},
            meta_file,
            indent=2,
        )

    with open(desc.font, "wb") as font_file:
        font_file.write(font)

    return desc


def awesome() -> Desc:
    desc = Desc("awesome", "awesome.json", "awesome.ttf")
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
    with open(desc.metadata, "w") as meta_file:
        json.dump(
            {"family": "Font Awesome 6 Pro", "names": names},
            meta_file,
            indent=2,
        )

    with open(desc.font, "wb") as font_file:
        font_file.write(font)

    return desc


def weather() -> Desc:
    desc = Desc("weather", "weather.json", "weather.ttf")
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
    with open(desc.metadata, "w") as meta_file:
        json.dump(
            {"family": "Weather Icons", "names": names},
            meta_file,
            indent=2,
        )

    with open(desc.font, "wb") as font_file:
        font_file.write(font)

    return desc


def main() -> None:
    descriptions = [
        desc._asdict()
        for desc in [
            material(),
            fluent(),
            phosphor(),
            remix(),
            codicon(),
            awesome(),
            weather(),
        ]
    ]
    with open("descriptions.json", "w") as all_file:
        json.dump(descriptions, all_file, indent=2)


if __name__ == "__main__":
    main()
