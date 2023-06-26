#!/usr/bin/env python
# pyright: strict
from __future__ import annotations
import json
import re
import requests
from typing import Dict


def material() -> None:
    font_name = "material"
    metadata = requests.get(
        "https://raw.githubusercontent.com/Templarian/MaterialDesign/master/meta.json"
    ).json()
    font = requests.get(
        "https://github.com/Templarian/MaterialDesign-Webfont/raw/master/fonts/materialdesignicons-webfont.ttf"
    ).content

    names: Dict[str, str] = {}
    for meta in metadata:
        name = meta["name"]
        codepoint = chr(int(meta["codepoint"], 16))
        names[name] = codepoint
    with open(f"{font_name}.json", "w") as meta_file:
        json.dump(
            {
                "family": "Material Design Icons",
                "names": names,
            },
            meta_file,
            indent=2,
        )

    with open(f"{font_name}.ttf", "wb") as font_file:
        font_file.write(font)


def fluent() -> None:
    font_name = "fluent"
    metadata = requests.get(
        "https://github.com/microsoft/fluentui-system-icons/raw/main/fonts/FluentSystemIcons-Resizable.json"
    ).json()
    font = requests.get(
        "https://github.com/microsoft/fluentui-system-icons/raw/main/fonts/FluentSystemIcons-Resizable.ttf"
    ).content

    names: Dict[str, str] = {}
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
        names[name] = chr(codepoint)
    with open(f"{font_name}.json", "w") as meta_file:
        json.dump(
            {
                "family": "FluentSystemIcons-Resizable",
                "names": names,
            },
            meta_file,
            indent=2,
        )

    with open(f"{font_name}.ttf", "wb") as font_file:
        font_file.write(font)


def phosphor() -> None:
    font_name = "phosphor"
    metadata = requests.get(
        "https://github.com/phosphor-icons/web/raw/master/src/regular/style.css"
    ).text
    font = requests.get(
        "https://github.com/phosphor-icons/web/raw/master/src/regular/Phosphor.ttf"
    ).content

    names: Dict[str, str] = {}
    for match in re.finditer(
        '^\\.ph\\.ph-([^:]*):.*\n\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        names[match.group(1)] = chr(int(match.group(2), 16))
    with open(f"{font_name}.json", "w") as meta_file:
        json.dump(
            {"family": "Phosphor", "names": names},
            meta_file,
            indent=2,
        )

    with open(f"{font_name}.ttf", "wb") as font_file:
        font_file.write(font)


def remix() -> None:
    font_name = "remix"
    metadata = requests.get(
        "https://github.com/Remix-Design/RemixIcon/raw/master/fonts/remixicon.css"
    ).text
    font = requests.get(
        "https://github.com/Remix-Design/RemixIcon/raw/master/fonts/remixicon.ttf"
    ).content

    # .ri-arrow-left-right-fill:before { content: "\ea61"; }
    names: Dict[str, str] = {}
    for match in re.finditer(
        '^\\.ri-([^:]+)-(fill|line):.*{\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        name = match.group(1)
        suffix = match.group(2)
        if suffix != "line":
            name = f"{name}-{suffix}"
        names[name] = chr(int(match.group(3), 16))
    with open(f"{font_name}.json", "w") as meta_file:
        json.dump(
            {"family": "remixicon", "names": names},
            meta_file,
            indent=2,
        )

    with open(f"{font_name}.ttf", "wb") as font_file:
        font_file.write(font)


def codicon() -> None:
    font_name = "codicon"
    metadata = requests.get(
        "https://github.com/microsoft/vscode-codicons/raw/main/dist/codicon.css"
    ).text
    font = requests.get(
        "https://github.com/microsoft/vscode-codicons/raw/main/dist/codicon.ttf"
    ).content

    # .codicon-gist-new:before { content: "\ea60" }
    names: Dict[str, str] = {}
    for match in re.finditer(
        '^\\.codicon-([^:]+):.*{\\s+content:\\s+"\\\\(.*)"',
        metadata,
        re.MULTILINE,
    ):
        names[match.group(1)] = chr(int(match.group(2), 16))
    with open(f"{font_name}.json", "w") as meta_file:
        json.dump(
            {"family": "codicon", "names": names},
            meta_file,
            indent=2,
        )

    with open(f"{font_name}.ttf", "wb") as font_file:
        font_file.write(font)


def awesome() -> None:
    font_name = "awesome"
    # inspect https://fontawesome.com to get this URLs
    version = "6.4.0"
    font = requests.get(
        f"https://site-assets.fontawesome.com/releases/v{version}/webfonts/fa-regular-400.ttf"
    ).content
    metadata = requests.get(
        f"https://site-assets.fontawesome.com/releases/v{version}/css/all.css"
    ).text

    # single line like .fa-fill-drip:before{content:"\f576"}
    names: Dict[str, str] = {}
    for match in re.finditer(
        '\\.fa-([^:{}\\.]+):before{\\s*content:\\s*"\\\\([^"]+)"[^}]*}',
        metadata,
        re.MULTILINE,
    ):
        names[match.group(1)] = chr(int(match.group(2), 16))
    with open(f"{font_name}.json", "w") as meta_file:
        json.dump(
            {"family": "Font Awesome 6 Pro", "names": names},
            meta_file,
            indent=2,
        )

    with open(f"{font_name}.ttf", "wb") as font_file:
        font_file.write(font)


def main() -> None:
    material()
    fluent()
    phosphor()
    remix()
    codicon()
    awesome()


if __name__ == "__main__":
    main()
