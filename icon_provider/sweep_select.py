# pyright: strict
from __future__ import annotations

from typing import NamedTuple, Optional

from sweep import Candidate, Container, Justify, Field, Flex, sweep
from sweep import Icon as SweepIcon

from .store import Icon, IconStore

VIEW_BOX = (0.0, 0.0, 100.0, 100.0)


class IconCandidate(NamedTuple):
    ref: int
    icon: Icon

    def to_candidate(self) -> Candidate:
        result = Candidate()
        result.target_push(self.icon.name)

        result.preview_flex_set(1.0)
        result.preview_push("Family:    ", face="bold")
        result.preview_push(f"{self.icon.font.family}\n")
        result.preview_push("Codepoint: ", face="bold")
        result.preview_push(f"{self.icon.codepoint} ({hex(self.icon.codepoint)})\n")
        result.preview_push("\n")
        result.preview_push(ref=self.ref)

        result.right_push(glyph=self.to_sweep_icon((1, 2)))

        return result

    def to_sweep_icon(self, size: Optional[tuple[int, int]] = None) -> SweepIcon:
        return SweepIcon(path=self.icon.svg, view_box=VIEW_BOX, size=size)


async def select(store: IconStore) -> list[Icon]:
    prompt_icon = store.get_icon("material-cat")
    if prompt_icon is not None:
        prompt_icon = SweepIcon(prompt_icon.svg, VIEW_BOX, size=(1, 3))

    async def field_resolver(ref: int) -> Field:
        icon = icons_all[ref].to_sweep_icon((6, 14))
        view = (
            Flex.row().justify(Justify.CENTER).push(Container(icon).face("fg=fg,bg=bg"))
            # .trace_layout("icon-layout")
        )
        return Field(view=view)

    icons_all = [
        IconCandidate(index, icon) for index, icon in enumerate(store.get_icons())
    ]
    icons = await sweep(
        icons_all,
        field_resolver=field_resolver,
        scorer="substr",
        prompt="ICON",
        prompt_icon=prompt_icon,
        log="/tmp/icon-provider-select.log",
    )
    return [icon.icon for icon in icons]
