#!/usr/bin/env python3
"""Micro font parser"""

# pyright: strict
from __future__ import annotations

import io
import struct
import sys
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, NamedTuple, Protocol, Iterator


class OutlineBuilder(Protocol):
    def move_to(self, p: Point, /) -> None: ...
    def line_to(self, p: Point, /) -> None: ...
    def quad_to(self, p1: Point, p2: Point, /) -> None: ...
    def cubic_to(self, p1: Point, p2: Point, p3: Point, /) -> None: ...
    def close(self) -> None: ...


class PrintOutlineBuilder:
    def move_to(self, p: Point) -> None:
        print(f"M{p.x},{p.y}")

    def line_to(self, p: Point) -> None:
        print(f"L{p.x},{p.y}")

    def quad_to(self, p1: Point, p2: Point) -> None:
        print(f"Q{p1.x},{p1.y} {p2.x},{p2.y}")

    def cubic_to(self, p1: Point, p2: Point, p3: Point) -> None:
        print(f"C{p1.x},{p1.y} {p2.x},{p2.y} {p3.x},{p3.y}")

    def close(self) -> None:
        print("Z")


class BBoxBuilder:
    __slots__ = ["min", "max"]

    def __init__(self):
        self.min: Point | None = None
        self.max: Point | None = None

    def __repr__(self) -> str:
        if self.min is None or self.max is None:
            return "BBox(None)"
        return (
            f"BBox(min=({self.min.x}, {self.min.y}), max=({self.max.x}, {self.max.y}))"
        )

    def _extend(self, p: Point) -> None:
        if self.min is None or self.max is None:
            self.min = p.copy()
            self.max = p.copy()
            return
        if p.x < self.min.x:
            self.min.x = p.x
        if p.x > self.max.x:
            self.max.x = p.x
        if p.y < self.min.y:
            self.min.y = p.y
        if p.y > self.max.y:
            self.max.y = p.y

    def move_to(self, p: Point) -> None:
        pass

    def line_to(self, p: Point) -> None:
        self._extend(p)

    def quad_to(self, p1: Point, p2: Point) -> None:
        self._extend(p1)
        self._extend(p2)

    def cubic_to(self, p1: Point, p2: Point, p3: Point) -> None:
        self._extend(p1)
        self._extend(p2)
        self._extend(p3)

    def close(self) -> None:
        pass


class SVGOutlineBuilder:
    def __init__(
        self,
        relative: bool = False,
        precision: int = 2,
        tr: Transform | None = None,
    ) -> None:
        self._file = io.StringIO()
        self._relative = relative
        self._precision = precision
        self._tr = tr or Transform.identity()
        self._point_prev: Point = Point(0, 0)

    def __str__(self) -> str:
        return self._file.getvalue()

    def _write_point(self, p: Point, sep: bool) -> Point:
        p = self._tr(p)
        pp = p - self._point_prev if self._relative else p

        x = round(pp.x, self._precision)
        y = round(pp.y, self._precision)
        if sep and x >= 0:
            self._file.write(" ")
        self._file.write(f"{x:g}")
        if y >= 0:
            self._file.write(",")
        self._file.write(f"{y:g}")

        return p

    def move_to(self, p: Point) -> None:
        self._file.write("m" if self._relative else "M")
        self._point_prev = self._write_point(p, False)

    def line_to(self, p: Point) -> None:
        self._file.write("l" if self._relative else "L")
        self._point_prev = self._write_point(p, False)

    def quad_to(self, p1: Point, p2: Point) -> None:
        self._file.write("q" if self._relative else "Q")
        self._write_point(p1, False)
        self._point_prev = self._write_point(p2, True)

    def cubic_to(self, p1: Point, p2: Point, p3: Point) -> None:
        self._file.write("c" if self._relative else "C")
        self._write_point(p1, False)
        self._write_point(p2, True)
        self._point_prev = self._write_point(p3, True)

    def close(self) -> None:
        self._file.write("Z")


class Point:
    __slots__ = ["x", "y"]
    x: float
    y: float

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def copy(self) -> Point:
        return Point(self.x, self.y)

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def lerp(self, other: Point, ratio_other: float) -> Point:
        """Linear interpolation between self and other point"""
        ratio_self = 1.0 - ratio_other
        return Point(
            self.x * ratio_self + other.x * ratio_other,
            self.y * ratio_self + other.y * ratio_other,
        )

    def transfrom(self, tr: Transform) -> Point:
        """Apply transformation to self point"""
        return tr(self)


class Transform(NamedTuple):
    m00: float
    m01: float
    m02: float
    m10: float
    m11: float
    m12: float

    @staticmethod
    def identity() -> Transform:
        return Transform(1, 0, 0, 0, 1, 0)

    def translate(self, tx: float, ty: float) -> Transform:
        return self @ Transform(1, 0, tx, 0, 1, ty)

    def scale(self, sx: float, sy: float) -> Transform:
        return self @ Transform(sx, 0.0, 0.0, 0.0, sy, 0.0)

    def rotate(self, angle: float) -> Transform:
        cos = math.cos(angle)
        sin = math.sin(angle)
        return self @ Transform(cos, -sin, 0.0, sin, cos, 0.0)

    def __matmul__(self, other: Transform) -> Transform:
        s00, s01, s02, s10, s11, s12 = self
        o00, o01, o02, o10, o11, o12 = other
        return Transform(
            s00 * o00 + s01 * o10,
            s00 * o01 + s01 * o11,
            s00 * o02 + s01 * o12 + s02,
            s10 * o00 + s11 * o10,
            s10 * o01 + s11 * o11,
            s10 * o02 + s11 * o12 + s12,
        )

    def __call__(self, point: Point) -> Point:
        """Apply transform to a point"""
        return Point(
            point.x * self.m00 + point.y * self.m01 + self.m02,
            point.x * self.m10 + point.y * self.m11 + self.m12,
        )

    def __repr__(self) -> str:
        file = io.StringIO()
        file.write("Transform(\n")
        file.write(f"    {self.m00} {self.m01} {self.m02}\n")
        file.write(f"    {self.m10} {self.m11} {self.m12}\n")
        file.write(")")
        return file.getvalue()


class GlyphPoint(NamedTuple):
    coord: Point  # coordinate of the point
    on_curve: bool  # point in on the curve
    last: bool  # last point in the contour


class Glyph:
    __slots__ = [
        "font",
        "glyph_id",
        "contours_count",
        "min_point",
        "max_point",
        "_reader",
    ]

    def __init__(self, font: Font, glyph_id: int, reader: Reader):
        self.font = font
        self.glyph_id = glyph_id
        if reader:
            self.contours_count = reader.read_i16()
            self.min_point = Point(reader.read_i16(), reader.read_i16())
            self.max_point = Point(reader.read_i16(), reader.read_i16())
            self._reader = reader.view(10)
        else:
            self.contours_count = 0
            self.min_point = Point(0, 0)
            self.max_point = Point(0, 0)
            self._reader = Reader(memoryview(b""))

    def __repr__(self) -> str:
        width = self.max_point.x - self.min_point.x
        height = self.max_point.y - self.min_point.y
        return f"Glyph(size={(width, height)}, min={self.min_point}, contours={self.contours_count}, data={len(self._reader)})"

    def to_svg_path(
        self,
        relative: bool = False,
        tr: Transform | None = None,
    ) -> str:
        """Generate 100x100 SVG path for the glyph"""

        # move middle of the bbox to the middle of em box
        bbox = self.bbox()
        if bbox is None:
            return ""
        mid = (bbox[0] + bbox[1]) * 0.5
        em = max(
            self.font.head.units_per_em,
            (bbox[1].x - bbox[0].x) * 1.1,
            (bbox[1].y - bbox[0].y) * 1.1,
        )
        center = Point(em / 2, em / 2) - mid

        tr = tr or Transform.identity()
        tr @= (
            Transform(1, 0, 0, 0, -1, 100)
            .scale(100 / em, 100 / em)
            .translate(center.x, center.y)
        )
        return str(self.build_outline(SVGOutlineBuilder(relative=relative, tr=tr)))

    def build_outline[OB: OutlineBuilder](
        self,
        builder: OB,
        tr: Transform | None = None,
    ) -> OB:
        """Build outline for the glyph"""
        if self.contours_count >= 0:
            self._simple_outline(builder, tr)
        else:
            self._composite_outline(builder, tr)
        return builder

    def bbox(self) -> tuple[Point, Point] | None:
        """BBox in the glyph is not always correct (i.e fluent icons)

        This is an approximate bbox based on all points (real bbox can be smaller)
        """
        if self.contours_count < 0:
            bbox = self.build_outline(BBoxBuilder())
            if bbox.min is None or bbox.max is None:
                return None
            return bbox.min, bbox.max
        elif self.contours_count == 0:
            return None
        xs: list[float] = []
        ys: list[float] = []
        for point in self._simple_outline_points():
            xs.append(point.coord.x)
            ys.append(point.coord.y)
        if not xs:
            return None
        return Point(min(xs), min(ys)), Point(max(xs), max(ys))

    def _simple_outline(
        self,
        builder: OutlineBuilder,
        tr: Transform | None = None,
    ) -> None:
        """Build simple outline

        Reference: http://chanae.walon.org/pub/ttf/ttf_glyphs.htm
        Notes:
            - [on0, on1] - line
            - [on0, off, on1] - quad(on0, off, on1)
            - [on0, off0, off1, on1] - quad(on0, off0, (off0+off1)/2) quad((off0+off1)/2, off1, on1)
        """
        tr = tr or Transform.identity()
        first_on_curve: Point | None = None
        first_off_curve: Point | None = None
        last_off_curve: Point | None = None
        for point in self._simple_outline_points():
            if first_on_curve is None:
                if point.on_curve:
                    first_on_curve = point.coord
                    builder.move_to(tr(point.coord))
                else:
                    if first_off_curve:
                        mid = first_off_curve.lerp(point.coord, 0.5)
                        first_on_curve = mid
                        last_off_curve = point.coord
                        builder.move_to(tr(mid))
                    else:
                        first_off_curve = point.coord
            else:
                if last_off_curve:
                    if point.on_curve:
                        builder.quad_to(tr(last_off_curve), tr(point.coord))
                        last_off_curve = None
                    else:
                        mid = last_off_curve.lerp(point.coord, 0.5)
                        builder.quad_to(tr(last_off_curve), tr(mid))
                        last_off_curve = point.coord
                else:
                    if point.on_curve:
                        builder.line_to(tr(point.coord))
                    else:
                        last_off_curve = point.coord

            if point.last:
                if first_off_curve and last_off_curve:
                    mid = last_off_curve.lerp(first_off_curve, 0.5)
                    builder.quad_to(tr(last_off_curve), tr(mid))
                    last_off_curve = None
                if first_on_curve:
                    if first_off_curve:
                        builder.quad_to(tr(first_off_curve), tr(first_on_curve))
                    elif last_off_curve:
                        builder.quad_to(tr(last_off_curve), tr(first_on_curve))
                    else:
                        builder.line_to(tr(first_on_curve))
                builder.close()
                first_on_curve = None
                first_off_curve = None
                last_off_curve = None

    def _simple_outline_points(self) -> Iterator[GlyphPoint]:
        """Simple glyph outline

        Reference:
            - https://learn.microsoft.com/en-us/typography/opentype/spec/glyf#simple-glyph-description
        """
        if self.contours_count == 0:
            return

        self._reader.seek(0)
        reader = self._reader

        endpoints = [reader.read_u16() for _ in range(self.contours_count)]
        points_count = endpoints[-1] + 1

        # should be ignored but not an error
        if points_count == 1:
            return

        # skip instructions byte code
        instructions_len = reader.read_u16()
        reader.advance(instructions_len)

        ON_CURVE_POINT = 0x01
        X_SHORT_VECTOR = 0x02
        Y_SHORT_VECTOR = 0x04
        REPEAT_FLAG = 0x08
        X_SAME_OR_POS = 0x10
        Y_SAME_OR_POS = 0x20

        # collect flags and calculate size of x and y buffers
        x_len = 0
        y_len = 0
        flags_left = points_count
        flags: bytearray = bytearray()
        while flags_left > 0:
            flag = reader.read_u8()

            repeats = 1
            flags.append(flag)
            if flag & REPEAT_FLAG:
                repeats += reader.read_u8()
                for _ in range(repeats - 1):
                    flags.append(flag)
            if repeats > flags_left:
                break
            flags_left -= repeats

            if flag & X_SHORT_VECTOR:
                x_len += repeats  # read u8
            elif not flag & X_SAME_OR_POS:
                x_len += repeats * 2  # read i16
            if flag & Y_SHORT_VECTOR:
                y_len += repeats
            elif not flag & Y_SAME_OR_POS:
                y_len += repeats * 2

        # create x and y readers
        x_start = reader.tell()
        y_start = x_start + x_len
        y_end = y_start + y_len
        x_reader = Reader(reader.data[x_start:y_start])
        y_reader = Reader(reader.data[y_start:y_end])

        # reader points
        x = 0
        y = 0
        endpoints = set(endpoints)
        for index, flag in enumerate(flags):
            x_diff = 0
            if flag & X_SHORT_VECTOR:
                x_diff = x_reader.read_u8()
                if not flag & X_SAME_OR_POS:
                    x_diff = -x_diff
            elif not flag & X_SAME_OR_POS:
                x_diff = x_reader.read_i16()
            x += x_diff

            y_diff = 0
            if flag & Y_SHORT_VECTOR:
                y_diff = y_reader.read_u8()
                if not flag & Y_SAME_OR_POS:
                    y_diff = -y_diff
            elif not flag & Y_SAME_OR_POS:
                y_diff = y_reader.read_i16()
            y += y_diff

            yield GlyphPoint(
                Point(x, y),
                bool(flag & ON_CURVE_POINT),
                index in endpoints,
            )

    def _composite_outline(
        self,
        builder: OutlineBuilder,
        tr: Transform | None = None,
    ) -> None:
        tr = tr or Transform.identity()

        self._reader.seek(0)
        reader = self._reader

        ARG_1_AND_2_ARE_WORDS = 0x0001
        ARGS_ARE_XY_VALUES = 0x0002
        WE_HAVE_A_SCALE = 0x0008
        MORE_COMPONENTS = 0x0020
        WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
        WE_HAVE_A_TWO_BY_TWO = 0x0080

        glyf = self.font.parse_glyf()
        assert glyf is not None, "Failed to get glyf table from glyph builder"
        while True:
            flag = reader.read_u16()

            # find child glyph
            glyph_id = reader.read_u16()
            glyph = glyf.get(glyph_id)
            if glyph is None:
                sys.stderr.write(
                    f"[{self.font.name.family}][{self.glyph_id}] "
                    "requested invalid glyph {glyph_id}\n"
                )
                if not flag & MORE_COMPONENTS:
                    break
                continue

            # parse transformation
            m00, m01, m02, m10, m11, m12 = 1, 0, 0, 0, 1, 0
            if flag & ARGS_ARE_XY_VALUES:
                if flag & ARG_1_AND_2_ARE_WORDS:
                    m02 = reader.read_i16()
                    m12 = reader.read_i16()
                else:
                    m02 = reader.read_i8()
                    m12 = reader.read_i8()
            if flag & WE_HAVE_A_TWO_BY_TWO:
                m00 = reader.read_f2dot14()
                m10 = reader.read_f2dot14()
                m01 = reader.read_f2dot14()
                m11 = reader.read_f2dot14()
            elif flag & WE_HAVE_AN_X_AND_Y_SCALE:
                m00 = reader.read_f2dot14()
                m11 = reader.read_f2dot14()
            elif flag & WE_HAVE_A_SCALE:
                m00 = reader.read_f2dot14()
                m11 = m00
            ts = Transform(m00, m01, m02, m10, m11, m12)

            # build child glyph
            glyph.build_outline(builder, tr @ ts)

            if not flag & MORE_COMPONENTS:
                break


class FontTable(NamedTuple):
    checksum: int
    offset: int
    length: int

    def reader(self, font: Font) -> Reader:
        return Reader(memoryview(font.data[self.offset : self.offset + self.length]))


def cached_table[F: Font, T](
    name: str,
) -> Callable[[Callable[[F], T]], Callable[[F], T]]:
    def cached_table_named(parse_table: Callable[[F], T]) -> Callable[[F], T]:
        def cached_parse_table(font: F) -> T:
            table = font.cached_tables.get(name)
            if table is None:
                table = parse_table(font)
                font.cached_tables[name] = table
            return table

        return cached_parse_table

    return cached_table_named


SPECIMEN_SIZE = 32
SPECIMEN_PADD = 6
SPECIMEN_COLS = 35


class Font:
    """Simple font reader

    References:
        - https://tchayen.github.io/posts/ttf-file-parsing
        - https://learn.microsoft.com/en-us/typography/opentype/spec/otff#organization-of-an-opentype-font
    """

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.cached_tables: dict[str, Any] = {}

        # parser header
        header_reader = Reader(memoryview(self.data))
        sfnt_version = header_reader.read_u32()
        if sfnt_version == 0x00010000:
            self.font_type = "ttf"
        elif sfnt_version == 0x4F54544F:
            self.font_type = "otf"
        else:
            raise ValueError(f"Unknown font type: {sfnt_version}")
        num_tables = header_reader.read_u16()  # numTables
        header_reader.read_u16()  # searchRange
        header_reader.read_u16()  # entrySelector
        header_reader.read_u16()  # rangeShift

        # parse tables
        self.tables: dict[str, FontTable] = {}
        for _ in range(num_tables):
            tag = header_reader.read_string(4)
            self.tables[tag] = FontTable(
                header_reader.read_u32(),
                header_reader.read_u32(),
                header_reader.read_u32(),
            )

        # Maximum Profile (required)
        # Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/maxp
        maxp_reader = self.tables["maxp"].reader(self)
        maxp_reader.advance(4)  # offset + version
        self.glyph_count = maxp_reader.read_u16()  # numGlyphs

        self.name = self.parse_name()
        self.head = self.parse_head()

    def __repr__(self) -> str:
        return f"Font(family={self.name.family}, subfamily={self.name.subfamily}, glyph_count={self.glyph_count})"

    @classmethod
    def from_path(cls, path: Path | str) -> Font:
        if isinstance(path, str):
            path = Path(path)
        return cls(path.expanduser().read_bytes())

    def info(self) -> dict[str, Any]:
        return {
            "family": self.name.family,
            "subfamily": self.name.subfamily,
            "version": self.name.version,
            "glyph_count": self.glyph_count,
            "post_count": len(self.parse_post().glyph_id_to_name),
            "units_per_em": self.head.units_per_em,
            "modified_dt": self.head.modified_dt.isoformat(),
            "tables": {name: table.length for name, table in self.tables.items()},
        }

    def specimen(
        self,
        size: int | None = None,
        columns: int | None = None,
        padding: int | None = None,
    ) -> str:
        """Generate SVG path specimen of all glyphs"""
        size = size or SPECIMEN_SIZE
        columns = columns or SPECIMEN_COLS
        padding = padding or SPECIMEN_PADD

        glyph_table = self.parse_glyf()
        if glyph_table is None or self.glyph_count == 0:
            return ""

        buf = io.StringIO()
        buf.write("M0,0h1v1h-1z")  # mark top-left corner
        scale = size / 100
        size += padding
        row, col = 0, 0
        glyphs = filter(lambda glyph: glyph.contours_count != 0, glyph_table.glyphs)
        for index, glyph in enumerate(glyphs):
            row, col = divmod(index, columns)
            tr = (
                Transform.identity()
                .translate(padding + col * size, padding + row * size)
                .scale(scale, scale)
            )
            buf.write(glyph.to_svg_path(tr=tr))
            buf.write("\n")
        # mark bottom-right corner
        mark_x = padding + columns * size
        mark_y = padding + (row + 1) * size
        buf.write(f"M{mark_x},{mark_y}h1v1h-1z")
        return buf.getvalue()

    def glyph_by_codepoint(self, codepoint: int) -> Glyph | None:
        """Get glyph corresponding to the codepoint"""
        if self.font_type != "ttf":
            raise ValueError("Only TTF outlines are supported for now")
        glyf = self.parse_glyf()
        if glyf is None:
            return None
        cmap = self.parse_cmap()
        glyph_id = cmap.codepoint_to_glyph_id.get(codepoint)
        if glyph_id is None:
            return None
        return glyf.get(glyph_id)

    @cached_table("name_to_codpoint")
    def codepoint_by_name(self) -> dict[str, int]:
        """Mapping from names to codepoints"""
        cmap = self.parse_cmap()
        post = self.parse_post()
        name_to_codepoint: dict[str, int] = {}
        for glyph_id in range(self.glyph_count):
            codepoint = cmap.glyph_id_to_codepoint.get(glyph_id)
            name = post.glyph_id_to_name.get(glyph_id)
            if name is None or codepoint is None or codepoint == 0:
                continue
            name_to_codepoint[name] = codepoint
        return name_to_codepoint

    @cached_table("head")
    def parse_head(self) -> HeadTable:
        """Header Table

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/head
        """
        reader = self.tables["head"].reader(self)

        reader.read_u16()  # majorVersion = 1
        reader.read_u16()  # minorVersion = 0
        font_revision = reader.read_fixed()
        reader.read_u32()  # checksum
        assert reader.read_u32() == 0x5F0F3CF5  # magicNumber
        flags = reader.read_u16()
        units_per_em = reader.read_u16()
        created_dt = reader.read_longdatetime()
        modified_dt = reader.read_longdatetime()
        x_min = reader.read_i16()
        y_min = reader.read_i16()
        x_max = reader.read_i16()
        y_max = reader.read_i16()
        mac_style = reader.read_u16()
        lowest_rec_ppem = reader.read_u16()
        font_direction_hint = reader.read_i16()
        index_to_loc_format = reader.read_i16()
        glyph_data_format = reader.read_i16()
        return HeadTable(
            revision=font_revision,
            flags=flags,
            units_per_em=units_per_em,
            created_dt=created_dt,
            modified_dt=modified_dt,
            min_point=Point(x_min, y_min),
            max_point=Point(x_max, y_max),
            mac_style=mac_style,
            lowest_rec_ppem=lowest_rec_ppem,
            font_direction_hint=font_direction_hint,
            index_to_loc_format=index_to_loc_format,
            glyph_data_format=glyph_data_format,
        )

    @cached_table("loca")
    def parse_loca(self) -> list[int] | None:
        """Glyph index to location table (TTF)

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/loca
        """
        loca = self.tables.get("loca")
        if loca is None:
            return None
        reader = loca.reader(self)
        read_index: Callable[[], int]
        if self.head.index_to_loc_format == 0:
            read_index = reader.read_u16
            mult = 2
        else:
            read_index = reader.read_u32
            mult = 1
        return [mult * read_index() for _ in range(self.glyph_count + 1)]

    @cached_table("glyf")
    def parse_glyf(self) -> GlyfTable | None:
        """Glyph data (TTF)

        Reference:
            - https://learn.microsoft.com/en-us/typography/opentype/spec/glyf
        """
        glyf = self.tables.get("glyf")
        if glyf is None:
            return None
        data = glyf.reader(self).data
        loca = self.parse_loca()
        if loca is None:
            return None

        glyphs: list[Glyph] = []
        for index, (start, end) in enumerate(zip(loca, loca[1:])):
            glyph_data = data[start:end]
            glyphs.append(Glyph(self, index, Reader(glyph_data)))
        return GlyfTable(glyphs)

    @cached_table("hhea")
    def parse_hhea(self) -> HheaTable:
        """Horizontal header table (required)

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/hhea
        """
        reader = self.tables["hhea"].reader(self)
        assert reader.read_u16() == 1  # majorVersion
        assert reader.read_u16() == 0  # minorVersion
        ascender = reader.read_i16()
        descender = reader.read_i16()
        line_gap = reader.read_i16()
        advance_width_max = reader.read_u16()
        min_left_side_bearing = reader.read_i16()
        min_right_side_bearing = reader.read_i16()
        x_max_extent = reader.read_i16()
        caret_slope_rise = reader.read_i16()
        caret_slope_run = reader.read_i16()
        caret_offset = reader.read_i16()
        reader.advance(10)  # reserved + metric_data_format (always 0)
        number_of_metrics = reader.read_u16()
        return HheaTable(
            ascender,
            descender,
            line_gap,
            advance_width_max,
            min_left_side_bearing,
            min_right_side_bearing,
            x_max_extent,
            caret_slope_rise,
            caret_slope_run,
            caret_offset,
            number_of_metrics,
        )

    @cached_table("hmtx")
    def parse_hmtx(self) -> HmtxTable:
        """Horizontal Metrics Table (required)

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/hmtx
        """
        reader = self.tables["hmtx"].reader(self)
        hhea = self.parse_hhea()
        number_of_metrics = hhea.number_of_metrics
        metrics = [
            Metrics(reader.read_u16(), reader.read_i16())
            for _ in range(number_of_metrics)
        ]
        bearings_count = self.glyph_count - number_of_metrics
        bearings: list[int] = []
        if bearings_count > 0:
            number_of_metrics += bearings_count
            for _ in range(bearings_count):
                bearings.append(reader.read_i16())
        return HmtxTable(metrics, bearings, number_of_metrics)

    @cached_table("cmap")
    def parse_cmap(self) -> CmapTable:
        """Character Map (required)

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/cmap
        """
        reader = self.tables["cmap"].reader(self)
        reader.read_u16()  # version

        # find unicode sub-table
        unicode_table_offset = 0
        subtables: list[tuple[int, int, int]] = []
        num_tables = reader.read_u16()
        for _ in range(num_tables):
            platform_id = reader.read_u16()  # 0 - unicode
            encoding_id = reader.read_u16()
            subtable_offset = reader.read_u32()
            subtables.append((platform_id, encoding_id, subtable_offset))
            if platform_id == 0 and encoding_id == 4:
                unicode_table_offset = subtable_offset
            elif not unicode_table_offset and platform_id == 0 and encoding_id == 3:
                unicode_table_offset = subtable_offset
        if not unicode_table_offset:
            raise ValueError(
                f"Only support unicode (0) format (4, 3) cmap tables: {subtables}"
            )

        # sub-table header
        reader.seek(unicode_table_offset)
        subtable_format = reader.read_u16()

        cmap = CmapTable({}, {})

        # https://learn.microsoft.com/en-us/typography/opentype/spec/cmap#format-12-segmented-coverage
        if subtable_format == 12:  # segmented coverage
            reader.read_u16()  # reserved
            reader.read_u32()  # length
            reader.read_u32()  # language

            # groups
            num_groups = reader.read_u32()
            for _ in range(num_groups):
                codepoint_start = reader.read_u32()
                codepoint_end = reader.read_u32()
                glyph_id = reader.read_u32()
                for codepoint in range(codepoint_start, codepoint_end + 1):
                    cmap.glyph_id_to_codepoint[glyph_id] = codepoint
                    cmap.codepoint_to_glyph_id[codepoint] = glyph_id
                    glyph_id += 1

        # https://learn.microsoft.com/en-us/typography/opentype/spec/cmap#format-4-segment-mapping-to-delta-values
        elif subtable_format == 4:
            st_length = reader.read_u16()
            st_reader = reader.view(reader.tell(), reader.tell() + st_length)
            st_reader.advance(2)  # language

            segment_count = st_reader.read_u16() // 2
            # legacy fields: searchRange, entrySelector, rangeShift
            st_reader.advance(6)

            end_codes = [st_reader.read_u16() for _ in range(segment_count)]
            st_reader.read_u16()  # reservedPad
            start_codes = [st_reader.read_u16() for _ in range(segment_count)]
            id_deltas = [st_reader.read_i16() for _ in range(segment_count)]
            id_range_offsets = [st_reader.read_u16() for _ in range(segment_count)]
            glyph_id_array_len = (len(st_reader) - st_reader.tell()) // 2
            _glyph_id_array = [st_reader.read_u16() for _ in range(glyph_id_array_len)]

            for end_code, start_code, id_delta, id_range_offset in zip(
                end_codes, start_codes, id_deltas, id_range_offsets
            ):
                if end_code == start_code and start_code == 0xFFFF:
                    break
                for codepoint in range(start_code, end_code + 1):
                    if id_range_offset == 0:
                        glyph_id = (codepoint + id_delta) % 65536
                    else:
                        sys.stderr.write(
                            "[cmap][format=4] id_range_offset != 0 not implemented\n"
                        )
                        break
                    cmap.glyph_id_to_codepoint[glyph_id] = codepoint
                    cmap.codepoint_to_glyph_id[codepoint] = glyph_id
        else:
            raise ValueError(f"unsupported cmap table: {subtable_format}")

        return cmap

    @cached_table("post")
    def parse_post(self) -> PostTable:
        """PostScript Table (required)

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/post
        """
        reader = self.tables["post"].reader(self)

        version = reader.read_fixed()
        if version != 2:
            return PostTable({})
        reader.advance(28)  # skip header

        # https://learn.microsoft.com/en-us/typography/opentype/spec/post#version-20
        glyph_count = reader.read_u16()
        glyph_id_to_index: dict[int, int] = {}
        for glyph_index in range(glyph_count):
            name_index = reader.read_u16()
            if name_index >= 258:
                glyph_id_to_index[glyph_index] = name_index - 258

        names: list[str] = []
        for _ in range(max(glyph_id_to_index.values()) + 1):
            length = reader.read_u8()
            names.append(reader.read_string(length))

        glyph_id_to_name = {
            glyph_id: names[index] for glyph_id, index in glyph_id_to_index.items()
        }
        return PostTable(glyph_id_to_name)

    @cached_table("parse")
    def parse_name(self) -> NameTable:
        """Naming table (required)

        Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/name
        """
        reader = self.tables["name"].reader(self)

        reader.read_u16()  # version
        record_count = reader.read_u16()
        storage_offset = reader.read_u16()

        class NameRecord(NamedTuple):
            platfrom_id: int
            encoding_id: int
            langauge_id: int
            name_id: int
            lenght: int
            offset: int

        records: list[NameRecord] = []
        for _ in range(record_count):
            record = NameRecord(
                reader.read_u16(),
                reader.read_u16(),
                reader.read_u16(),
                reader.read_u16(),
                reader.read_u16(),
                reader.read_u16(),
            )
            id = (record.platfrom_id, record.langauge_id, record.encoding_id)
            if id not in {(3, 1033, 1), (3, 1033, 10)}:
                continue
            records.append(record)

        fields = [""] * 6
        for record in records:
            if record.name_id > 5:
                continue
            fields[record.name_id] = reader.read(
                record.lenght, storage_offset + record.offset
            ).decode("utf-16-be")
        return NameTable(*fields)


class NameTable(NamedTuple):
    copyright: str
    family: str
    subfamily: str
    font_id: str
    fullname: str
    version: str


class CmapTable(NamedTuple):
    codepoint_to_glyph_id: dict[int, int]
    glyph_id_to_codepoint: dict[int, int]

    def __repr__(self) -> str:
        return f"CmapTable(count={len(self.codepoint_to_glyph_id)})"


class PostTable(NamedTuple):
    glyph_id_to_name: dict[int, str]

    def __repr__(self) -> str:
        return f"PostTable(count={len(self.glyph_id_to_name)})"


class HeadTable(NamedTuple):
    revision: float
    flags: int
    units_per_em: int
    created_dt: datetime
    modified_dt: datetime
    min_point: Point
    max_point: Point
    mac_style: int
    lowest_rec_ppem: int
    font_direction_hint: int
    index_to_loc_format: int
    glyph_data_format: int


class HheaTable(NamedTuple):
    ascender: int
    descender: int
    line_gap: int
    advance_width_max: int
    min_left_side_bearing: int
    min_right_side_bearing: int
    x_max_extent: int
    caret_slope_rise: int
    caret_slope_run: int
    caret_offset: int
    number_of_metrics: int


class Metrics(NamedTuple):
    advance: int
    side_bearing: int


class HmtxTable(NamedTuple):
    metrics: list[Metrics]
    bearings: list[int]
    number_of_metrics: int

    def get_advance(self, glyph_id: int) -> int | None:
        if glyph_id >= self.number_of_metrics:
            return None
        if glyph_id < len(self.metrics):
            return self.metrics[glyph_id].advance
        return self.metrics[-1].advance

    def get_side_bearing(self, glyph_id: int) -> int | None:
        if glyph_id < len(self.metrics):
            return self.metrics[glyph_id].side_bearing
        else:
            bearing_offset = glyph_id - len(self.metrics)
            if 0 <= bearing_offset < len(self.bearings):
                return self.bearings[bearing_offset]

    def __repr__(self) -> str:
        return f"HmtxTable(number_of_metrics={self.number_of_metrics})"


class GlyfTable:
    __slots__ = ["glyphs"]
    glyphs: list[Glyph]

    def __init__(self, glyphs: list[Glyph]) -> None:
        self.glyphs = glyphs

    def __iter__(self) -> Iterator[Glyph]:
        yield from self.glyphs

    def __len__(self) -> int:
        return len(self.glyphs)

    def __getitem__(self, glyph_id: int) -> Glyph:
        return self.glyphs[glyph_id]

    def get(self, glyph_id: int) -> Glyph | None:
        if 0 <= glyph_id < len(self.glyphs):
            return self.glyphs[glyph_id]

    def __repr__(self) -> str:
        return f"GlyfTable(count={len(self.glyphs)})"


class Reader:
    __slots__ = ["data", "file"]

    def __init__(self, data: memoryview):
        self.data = data
        self.file = io.BytesIO(data)

    def __len__(self) -> int:
        return self.data.nbytes

    def __bool__(self) -> bool:
        return self.data.nbytes != 0

    def __repr__(self) -> str:
        return f"Reader(pos={self.file.tell()}, size={len(self.data)})"

    def view(self, start: int | None = 0, end: int | None = None) -> Reader:
        if start is None:
            start = self.file.tell()
        if end is None:
            end = len(self.data)
        return Reader(self.data[start:end])

    def read(self, size: int, at: int | None = None) -> bytes:
        if at is not None:
            self.file.seek(at)
        return self.file.read(size)

    def read_string(self, size: int, at: int | None = None) -> str:
        return self.read(size, at).decode(errors="backslashreplace")

    def advance(self, size: int) -> None:
        return self.seek(size, 1)

    def seek(self, target: int, whence: int = 0) -> None:
        self.file.seek(target, whence)

    def tell(self) -> int:
        return self.file.tell()

    def read_struct(self, format: str, at: int | None = None) -> tuple[Any, ...]:
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

    def read_i64(self) -> int:
        return self.read_struct(">q")[0]

    def read_fixed(self) -> float:
        return self.read_i32() / 65536.0

    def read_f2dot14(self) -> float:
        return self.read_i16() / 16384.0

    def read_longdatetime(self) -> datetime:
        return datetime(1904, 1, 1) + timedelta(seconds=self.read_i64())


def main() -> None:
    import argparse
    import json

    args = argparse.ArgumentParser(
        description="Render single glyph from the font by codepoint"
    )
    args.add_argument("font", help="font file")
    args.add_argument(
        "codepoint",
        nargs="*",
        help="codepoint (specimen/info is rendered if not set)",
    )
    args.add_argument(
        "-f",
        "--format",
        default="json",
        choices=["path", "json"],
        help="output format",
    )
    opts = args.parse_args()

    font = Font.from_path(opts.font)
    if not opts.codepoint:
        match opts.format:
            case "path":
                print(font.specimen())
            case "json":
                print(json.dumps(font.info(), indent=2))
            case format:
                raise RuntimeError(f"Unkown format: {format}")
        return

    for codepoint_str in opts.codepoint:
        if codepoint_str.startswith("0x"):
            codepoint = int(codepoint_str[2:], 16)
        else:
            codepoint = int(codepoint_str)

        glyph = font.glyph_by_codepoint(codepoint)
        if glyph is None:
            sys.stderr.write(f"Font does not have codepoint: {codepoint}\n")
            return

        match opts.format:
            case "path":
                print(glyph.to_svg_path())
            case "json":
                cmap = font.parse_cmap()
                post = font.parse_post()
                hmtx = font.parse_hmtx()
                glyph_id = cmap.codepoint_to_glyph_id[codepoint]
                glyph_dict = {
                    "glyph_id": glyph_id,
                    "name": post.glyph_id_to_name.get(glyph_id),
                    "bearing": hmtx.get_side_bearing(glyph_id),
                    "advance": hmtx.get_advance(glyph_id),
                    "bbox": (
                        glyph.min_point.x,
                        glyph.min_point.y,
                        glyph.max_point.x,
                        glyph.max_point.y,
                    ),
                    "path": glyph.to_svg_path(),
                }
                print(json.dumps(glyph_dict, indent=2))
            case format:
                raise RuntimeError(f"Unkown format: {format}")


if __name__ == "__main__":
    main()
