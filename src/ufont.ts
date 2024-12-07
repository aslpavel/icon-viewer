import { Iter } from "./iter.js";

export interface OutlineBuilder {
    moveTo(p: Point): void;
    lineTo(p: Point): void;
    quadTo(p1: Point, p2: Point): void;
    cubicTo(p1: Point, p2: Point, p3: Point): void;
    close(): void;
}

export class SVGOutlineBuilder implements OutlineBuilder {
    #chunks: string[];
    #relative: boolean;
    #tr: Transform;
    #pointPrev: Point | null;
    #numberFormatter: Intl.NumberFormat;

    constructor(
        relative: boolean = false,
        precision: number | null = null,
        tr: Transform | null = null
    ) {
        this.#chunks = [];
        this.#relative = relative;
        this.#tr = tr ?? Transform.identity();
        this.#pointPrev = null;
        this.#numberFormatter = new Intl.NumberFormat("en-US", {
            useGrouping: false,
            maximumFractionDigits: precision ?? 2,
        });
    }

    #writePoint(p: Point, sep: boolean): Point {
        p = this.#tr.apply(p);
        const pp = this.#relative && this.#pointPrev ? p.sub(this.#pointPrev) : p;

        if (sep && pp.x >= 0) {
            this.#chunks.push(" ");
        }
        this.#chunks.push(this.#numberFormatter.format(pp.x));
        if (pp.y >= 0) {
            this.#chunks.push(",");
        }
        this.#chunks.push(this.#numberFormatter.format(pp.y));
        return p;
    }

    moveTo(p: Point): void {
        this.#chunks.push(this.#relative && this.#pointPrev ? "m" : "M");
        this.#pointPrev = this.#writePoint(p, false);
    }

    lineTo(p: Point): void {
        this.#chunks.push(this.#relative ? "l" : "L");
        this.#pointPrev = this.#writePoint(p, false);
    }

    quadTo(p1: Point, p2: Point): void {
        this.#chunks.push(this.#relative ? "q" : "Q");
        this.#writePoint(p1, false);
        this.#pointPrev = this.#writePoint(p2, true);
    }

    cubicTo(p1: Point, p2: Point, p3: Point): void {
        this.#chunks.push(this.#relative ? "c" : "C");
        this.#writePoint(p1, false);
        this.#writePoint(p2, true);
        this.#pointPrev = this.#writePoint(p3, true);
    }

    close(): void {
        this.#chunks.push("Z");
    }

    build(): string {
        return this.#chunks.join("");
    }
}

class BBoxBuilder implements OutlineBuilder {
    constructor(public min: Point | null = null, public max: Point | null = null) {}

    extend(p: Point): void {
        if (this.min === null || this.max === null) {
            this.min = new Point(p.x, p.y);
            this.max = new Point(p.x, p.y);
            return;
        }
        if (p.x < this.min.x) {
            this.min.x = p.x;
        }
        if (p.x > this.max.x) {
            this.max.x = p.x;
        }
        if (p.y < this.min.y) {
            this.min.y = p.y;
        }
        if (p.y > this.max.y) {
            this.max.y = p.y;
        }
    }

    moveTo(p: Point): void {
        this.extend(p);
    }

    lineTo(p: Point): void {
        this.extend(p);
    }

    quadTo(p1: Point, p2: Point): void {
        this.extend(p1);
        this.extend(p2);
    }

    cubicTo(p1: Point, p2: Point, p3: Point): void {
        this.extend(p1);
        this.extend(p2);
        this.extend(p3);
    }

    close(): void {}
}

export class Point {
    constructor(public x: number, public y: number) {}
    add(other: Point): Point {
        return new Point(this.x + other.x, this.y + other.y);
    }
    sub(other: Point): Point {
        return new Point(this.x - other.x, this.y - other.y);
    }
    mul(scalar: number): Point {
        return new Point(this.x * scalar, this.y * scalar);
    }
    lerp(other: Point, ratioOther: number): Point {
        const ratioThis = 1.0 - ratioOther;
        return new Point(
            this.x * ratioThis + other.x * ratioOther,
            this.y * ratioThis + other.y * ratioOther
        );
    }
    toString(): string {
        return `Point(${this.x}, ${this.y})`;
    }
}

export class Transform {
    constructor(
        public m00: number,
        public m01: number,
        public m02: number,
        public m10: number,
        public m11: number,
        public m12: number
    ) {}
    static identity(): Transform {
        return new Transform(1.0, 0.0, 0.0, 0.0, 1.0, 0.0);
    }
    translate(tx: number, ty: number): Transform {
        return this.matmul(new Transform(1.0, 0.0, tx, 0.0, 1.0, ty));
    }
    scale(sx: number, sy: number): Transform {
        return this.matmul(new Transform(sx, 0.0, 0.0, 0.0, sy, 0.0));
    }
    rotate(angle: number): Transform {
        const cos = Math.cos(angle);
        const sin = Math.sin(angle);
        return this.matmul(new Transform(cos, -sin, 0.0, sin, cos, 0.0));
    }
    matmul(other: Transform): Transform {
        return new Transform(
            this.m00 * other.m00 + this.m01 * other.m10,
            this.m00 * other.m01 + this.m01 * other.m11,
            this.m00 * other.m02 + this.m01 * other.m12 + this.m02,
            this.m10 * other.m00 + this.m11 * other.m10,
            this.m10 * other.m01 + this.m11 * other.m11,
            this.m10 * other.m02 + this.m11 * other.m12 + this.m12
        );
    }
    apply(point: Point): Point {
        return new Point(
            point.x * this.m00 + point.y * this.m01 + this.m02,
            point.x * this.m10 + point.y * this.m11 + this.m12
        );
    }
}

interface GlyphPoint {
    coord: Point; // coordinate of the point
    isOnCurve: boolean; // whether point is on the curve
    isLast: boolean; // whether it is the last point in the contour
}

const ON_CURVE_POINT = 0x01;
const X_SHORT_VECTOR = 0x02;
const Y_SHORT_VECTOR = 0x04;
const REPEAT_FLAG = 0x08;
const X_SAME_OR_POS = 0x10;
const Y_SAME_OR_POS = 0x20;

const ARG_1_AND_2_ARE_WORDS = 0x0001;
const ARGS_ARE_XY_VALUES = 0x0002;
const WE_HAVE_A_SCALE = 0x0008;
const MORE_COMPONENTS = 0x0020;
const WE_HAVE_AN_X_AND_Y_SCALE = 0x0040;
const WE_HAVE_A_TWO_BY_TWO = 0x0080;

export class Glyph {
    font: Font;
    glyphId: GlyphId;
    contoursCount: number;
    minPoint: Point;
    maxPoint: Point;
    #reader: Reader | null;

    constructor(font: Font, glyphId: number, reader: Reader | null) {
        this.font = font;
        this.glyphId = glyphId;

        if (reader && reader.length() !== 0) {
            this.contoursCount = reader.readI16();
            this.minPoint = new Point(reader.readI16(), reader.readI16());
            this.maxPoint = new Point(reader.readI16(), reader.readI16());
            this.#reader = reader.view(10);
        } else {
            this.contoursCount = 0;
            this.minPoint = new Point(0, 0);
            this.maxPoint = new Point(0, 0);
            this.#reader = null;
        }
    }

    toString(): string {
        const { x: width, y: height } = this.maxPoint.sub(this.minPoint);
        const dataLength = this.#reader ? this.#reader.length() : 0;
        return `Glyph(size=${[width, height]}, min=${this.minPoint}, contours=${
            this.contoursCount
        }, data=${dataLength})`;
    }

    /**Generate 100x100 SVG path for the glyph */
    toSVGPath(
        tr: Transform | null = null,
        relative: boolean = false,
        precision: number | null = null
    ): [string, [Point, Point] | null] {
        const bbox = this.bbox();
        if (bbox === null) {
            return ["", null];
        }

        // move middle of the bbox to the middle of em box
        const [min, max] = bbox;
        const mid = min.add(max).mul(0.5);
        const em = Math.max(
            this.font.getHeadTable().unitsPerEm,
            (max.x - min.x) * 1.1,
            (max.y - max.y) * 1.1
        );
        const center = new Point(em / 2, em / 2).sub(mid);

        tr = tr ?? Transform.identity();
        tr = tr.matmul(
            new Transform(1, 0, 0, 0, -1, 100)
                .scale(100 / em, 100 / em)
                .translate(center.x, center.y)
        );

        const svgPath = this.buildOutline(new SVGOutlineBuilder(relative, precision, tr)).build();
        return [svgPath, bbox];
    }

    /**
     * BBox in the glyph is not always correct (i.e fluent icons)
     *
     * This is an approximate bbox based on all points (real bbox can be smaller)
     */
    bbox(): [Point, Point] | null {
        if (this.contoursCount < 0) {
            const bbox = this.buildOutline(new BBoxBuilder());
            if (bbox.min === null || bbox.max === null) {
                return null;
            }
            return [bbox.min, bbox.max];
        } else if (this.contoursCount === 0) {
            return null;
        } else {
            const bbox = Iter.from(this.#simpleOutlinePoints()).fold(
                new BBoxBuilder(),
                (bbox, point) => {
                    bbox.extend(point.coord);
                    return bbox;
                }
            );
            if (bbox.min === null || bbox.max === null) {
                return null;
            }
            return [bbox.min, bbox.max];
        }
    }

    /** Build outline fot the glyph */
    buildOutline<B extends OutlineBuilder>(builder: B, tr: Transform | null = null): B {
        if (this.contoursCount >= 0) {
            this.#buildSimpleOutline(builder, tr);
        } else {
            this.#buildCompositeOutline(builder, tr);
        }
        return builder;
    }

    /** Build simple outline
     *
     * Reference: {@link http://chanae.walon.org/pub/ttf/ttf_glyphs.htm}
     * Notes:
     *  - [on0, on1] - line
     *  - [on0, off, on1] - quad(on0, off, on1)
     *  - [on0, off0, off1, on1] - quad(on0, off0, (off0+off1)/2) quad((off0+off1)/2, off1, on1)
     */
    #buildSimpleOutline(builder: OutlineBuilder, tr: Transform | null): void {
        tr = tr ?? Transform.identity();
        let firstOnCurve: Point | null = null;
        let firstOffCurve: Point | null = null;
        let lastOffCurve: Point | null = null;
        for (const point of this.#simpleOutlinePoints()) {
            if (firstOnCurve === null) {
                if (point.isOnCurve) {
                    firstOnCurve = point.coord;
                    builder.moveTo(tr.apply(point.coord));
                } else {
                    if (firstOffCurve) {
                        const mid = firstOffCurve.lerp(point.coord, 0.5);
                        firstOnCurve = mid;
                        lastOffCurve = point.coord;
                        builder.moveTo(tr.apply(mid));
                    } else {
                        firstOffCurve = point.coord;
                    }
                }
            } else {
                if (lastOffCurve) {
                    if (point.isOnCurve) {
                        builder.quadTo(tr.apply(lastOffCurve), tr.apply(point.coord));
                        lastOffCurve = null;
                    } else {
                        const mid = lastOffCurve.lerp(point.coord, 0.5);
                        builder.quadTo(tr.apply(lastOffCurve), tr.apply(mid));
                        lastOffCurve = point.coord;
                    }
                } else {
                    if (point.isOnCurve) {
                        builder.lineTo(tr.apply(point.coord));
                    } else {
                        lastOffCurve = point.coord;
                    }
                }
            }

            if (point.isLast) {
                if (firstOffCurve && lastOffCurve) {
                    const mid = lastOffCurve.lerp(firstOffCurve, 0.5);
                    builder.quadTo(tr.apply(lastOffCurve), tr.apply(mid));
                    lastOffCurve = null;
                }
                if (firstOnCurve) {
                    if (firstOffCurve) {
                        builder.quadTo(tr.apply(firstOffCurve), tr.apply(firstOnCurve));
                    } else if (lastOffCurve) {
                        builder.quadTo(tr.apply(lastOffCurve), tr.apply(firstOnCurve));
                    } else {
                        builder.lineTo(tr.apply(firstOnCurve));
                    }
                }
                builder.close();
                firstOnCurve = null;
                firstOffCurve = null;
                lastOffCurve = null;
            }
        }
    }

    /**
     * Simple glyph outline
     *
     * Reference:
     * {@link https://learn.microsoft.com/en-us/typography/opentype/spec/glyf#simple-glyph-description}
     */
    #simpleOutlinePoints = function* (this: Glyph): Generator<GlyphPoint> {
        if (this.contoursCount == 0) {
            return;
        }

        const reader = this.#reader!;
        reader.seek(0);

        let pointsCount = 0;
        const endPoints = Iter.range(this.contoursCount)
            .map((_) => {
                let value = reader.readU16();
                pointsCount = value;
                return value;
            })
            .collectSet();
        pointsCount = pointsCount + 1;

        // should be ignored but not an error
        if (pointsCount == 1) {
            return;
        }

        // skip instructions bytecode
        const instructionsLen = reader.readU16();
        reader.advance(instructionsLen);

        let xLen = 0;
        let yLen = 0;
        let flagsLeft = pointsCount;
        let flags: number[] = [];
        while (flagsLeft > 0) {
            const flag = reader.readU8();

            let repeats = 1;
            flags.push(flag);
            if (flag & REPEAT_FLAG) {
                repeats += reader.readU8();
                for (const _ of Iter.range(repeats - 1)) {
                    flags.push(flag);
                }
            }
            if (repeats > flagsLeft) {
                break;
            }
            flagsLeft -= repeats;

            if (flag & X_SHORT_VECTOR) {
                xLen += repeats; // read u8
            } else if (!(flag & X_SAME_OR_POS)) {
                xLen += repeats * 2; // read u16
            }
            if (flag & Y_SHORT_VECTOR) {
                yLen += repeats;
            } else if (!(flag & Y_SAME_OR_POS)) {
                yLen += repeats * 2;
            }
        }

        // create x and y readers
        const xStart = reader.tell(),
            yStart = xStart + xLen,
            yEnd = yStart + yLen;
        const xRreader = reader.view(xStart, yStart);
        const yReader = reader.view(yStart, yEnd);

        // reader points
        let x = 0;
        let y = 0;
        for (const [index, flag] of Iter.from(flags).enumerate()) {
            let xDiff = 0;
            const notXSameOrPos = !(flag & X_SAME_OR_POS);
            if (flag & X_SHORT_VECTOR) {
                xDiff = xRreader.readU8();
                if (notXSameOrPos) {
                    xDiff = -xDiff;
                }
            } else if (notXSameOrPos) {
                xDiff = xRreader.readI16();
            }
            x += xDiff;

            let yDiff = 0;
            const notYSameOrPos = !(flag & Y_SAME_OR_POS);
            if (flag & Y_SHORT_VECTOR) {
                yDiff = yReader.readU8();
                if (notYSameOrPos) {
                    yDiff = -yDiff;
                }
            } else if (notYSameOrPos) {
                yDiff = yReader.readI16();
            }
            y += yDiff;

            yield {
                coord: new Point(x, y),
                isOnCurve: Boolean(flag & ON_CURVE_POINT),
                isLast: endPoints.has(index),
            };
        }
    };

    #buildCompositeOutline(builder: OutlineBuilder, tr: Transform | null): void {
        tr = tr ?? Transform.identity();

        const reader = this.#reader!;
        reader.seek(0);

        const glyfTable = this.font.getGlyfTable()!;
        while (true) {
            const flag = reader.readU16();

            // find child glyph
            const glyphId = reader.readU16();
            const glyph = glyfTable.glyphs.at(glyphId);
            if (glyph === undefined) {
                console.error(
                    `[${this.font.getNameTable().family}][${
                        this.glyphId
                    }] requested invalid glyph ${glyphId}`
                );
                if (!(flag & MORE_COMPONENTS)) {
                    break;
                }
                continue;
            }

            let [m00, m01, m02, m10, m11, m12] = [1, 0, 0, 0, 1, 0];
            if (flag & ARGS_ARE_XY_VALUES) {
                if (flag & ARG_1_AND_2_ARE_WORDS) {
                    m02 = reader.readI16();
                    m12 = reader.readI16();
                } else {
                    m02 = reader.readI8();
                    m12 = reader.readI8();
                }
            }
            if (flag & WE_HAVE_A_TWO_BY_TWO) {
                m00 = reader.read2FDot14();
                m10 = reader.read2FDot14();
                m01 = reader.read2FDot14();
                m11 = reader.read2FDot14();
            } else if (flag & WE_HAVE_AN_X_AND_Y_SCALE) {
                m00 = reader.read2FDot14();
                m11 = reader.read2FDot14();
            } else if (flag & WE_HAVE_A_SCALE) {
                m00 = reader.read2FDot14();
                m11 = m00;
            }
            const ts = new Transform(m00, m01, m02, m10, m11, m12);

            // build child glyph
            glyph.buildOutline(builder, tr.matmul(ts));

            if (!(flag & MORE_COMPONENTS)) {
                break;
            }
        }
    }
}

export class Reader {
    #view: DataView;
    #position: number;

    constructor(view: DataView) {
        this.#view = view;
        this.#position = 0;
    }

    data(): ArrayBuffer {
        const offset = this.#view.byteOffset;
        return this.#view.buffer.slice(offset, offset + this.#view.byteLength);
    }

    length(): number {
        return this.#view.byteLength;
    }

    tell(): number {
        return this.#position;
    }

    seek(pos: number, absolute: boolean = true): number {
        if (!absolute) {
            this.#position += pos;
        } else if (pos >= 0) {
            this.#position = pos;
        } else if (pos < 0) {
            this.#position = this.#view.byteLength + pos;
        }
        return this.advance(0);
    }

    advance(size: number): number {
        const position = this.#position + size;
        this.#position = Math.max(0, Math.min(position, this.#view.byteLength));
        return this.#position;
    }

    view(start: number | null = 0, end: number | null = null): Reader {
        if (start === null) {
            start = this.#position;
        } else {
            start = Math.max(0, Math.min(start, this.#view.byteLength));
        }
        if (end === null) {
            end = this.#view.byteLength;
        } else {
            end = Math.max(start, Math.min(end, this.#view.byteLength));
        }
        const view = new DataView(this.#view.buffer, this.#view.byteOffset + start, end - start);
        return new Reader(view);
    }

    read(size: number): Uint8Array {
        const result = new Uint8Array(
            this.#view.buffer,
            this.#view.byteOffset + this.#position,
            size
        );
        this.advance(size);
        return result;
    }

    readString(size: number): string {
        const decoder = new TextDecoder();
        return decoder.decode(this.read(size));
    }

    readU8(): number {
        const result = this.#view.getUint8(this.#position);
        this.advance(1);
        return result;
    }

    readI8(): number {
        const result = this.#view.getInt8(this.#position);
        this.advance(1);
        return result;
    }

    readU16(): number {
        const result = this.#view.getUint16(this.#position);
        this.advance(2);
        return result;
    }

    readI16(): number {
        const result = this.#view.getInt16(this.#position);
        this.advance(2);
        return result;
    }

    readU32(): number {
        const result = this.#view.getUint32(this.#position);
        this.advance(4);
        return result;
    }

    readI32(): number {
        const result = this.#view.getInt32(this.#position);
        this.advance(4);
        return result;
    }

    readU64(): bigint {
        const result = this.#view.getBigUint64(this.#position);
        this.advance(8);
        return result;
    }

    readI64(): bigint {
        const result = this.#view.getBigInt64(this.#position);
        this.advance(8);
        return result;
    }

    readFixed(): number {
        return this.readI32() / 65536.0;
    }

    read2FDot14(): number {
        return this.readI16() / 16384.0;
    }

    readLongDate(): Date {
        const timestamp = this.readI64() - 2082844800n; // 1904-01-01
        return new Date(Number(timestamp) * 1_000);
    }

    toString(): string {
        return `Reader(postion=${this.#position}, size=${this.#view.byteLength})`;
    }
}

class FontTable {
    constructor(public checksum: number, public offset: number, public length: number) {}

    reader(font: Font): Reader {
        return new Reader(new DataView(font.data, this.offset, this.length));
    }
}

type GlyphId = number;
type Codepoint = number;

const SPECIMEN_SIZE = 32;
const SPECIMEN_PADD = 6;
const SPECIMEN_COLS = 35;

/**
 * Simple font reader
 *
 * References:
 *     - {@link https://tchayen.github.io/posts/ttf-file-parsing}
 *     - {@link https://learn.microsoft.com/en-us/typography/opentype/spec/otff#organization-of-an-opentype-font}
 */
export class Font {
    #data: ArrayBuffer;
    #cache: Map<string, any>;
    name: NameTable;
    fontType: "ttf" | "otf";
    tables: Map<string, FontTable>;
    glyphCount: number;

    constructor(data: ArrayBuffer) {
        this.#data = data;
        this.tables = new Map();
        this.#cache = new Map();

        const headerReader = new Reader(new DataView(this.#data));
        const sfntVersion = headerReader.readU32();
        if (sfntVersion === 0x00010000) {
            this.fontType = "ttf";
        } else if (sfntVersion === 0x4f54544f) {
            this.fontType = "otf";
        } else {
            throw new Error(`Unkown font type: ${sfntVersion}`);
        }
        const numTables = headerReader.readU16();
        headerReader.readU16(); // searchRange
        headerReader.readU16(); // entrySelector
        headerReader.readU16(); // rangeShift

        // parse tables
        for (let index = 0; index < numTables; index++) {
            const tag = headerReader.readString(4);
            this.tables.set(
                tag,
                new FontTable(
                    headerReader.readU32(),
                    headerReader.readU32(),
                    headerReader.readU32()
                )
            );
        }

        // Maximum Profile (required table)
        // Reference: https://learn.microsoft.com/en-us/typography/opentype/spec/maxp
        const maxpReader = this.tables.get("maxp")!.reader(this);
        maxpReader.advance(4); // offset + version
        this.glyphCount = maxpReader.readU16(); // numGlyphs

        this.name = this.getNameTable();
    }

    get data(): ArrayBuffer {
        return this.#data;
    }

    toString(): string {
        const name = this.getNameTable();
        return `Font(family=${name.family}, subfamily=${name.subfamily}, glyph_count=${this.glyphCount})`;
    }

    /** Get glyph corresponding to the codepoint */
    glyphByCodepoint(codepoint: Codepoint): Glyph | null {
        if (this.fontType != "ttf") {
            throw new Error("Only TTF outlines are supported for now");
        }
        const glyfTable = this.getGlyfTable();
        if (glyfTable === null) {
            return null;
        }
        const cmapTable = this.getCmapTable();
        const glyphId = cmapTable.codepointToGlyphId.get(codepoint);
        if (glyphId === undefined) {
            return null;
        }
        return glyfTable.glyphs.at(glyphId)!;
    }

    /** Mapping from names to codepoints as per */
    get codepointByName(): Map<string, Codepoint> {
        const cacheName = "codepointByName";
        let nameToCodepoint = this.#cache.get(cacheName);
        if (nameToCodepoint === undefined) {
            const cmapTable = this.getCmapTable();
            const postTable = this.getPostTable();
            nameToCodepoint = new Map();
            for (const glyphId of Iter.range(this.glyphCount)) {
                const name = postTable.glyphIdToName.get(glyphId);
                const codepoint = cmapTable.glyphIdToCodepoint.get(glyphId);
                if (name === undefined || codepoint === undefined || codepoint === 0) {
                    continue;
                }
                nameToCodepoint.set(name, codepoint);
            }
            this.#cache.set(cacheName, nameToCodepoint);
        }
        return nameToCodepoint;
    }

    specimen(
        size: number | null = null,
        columns: number | null = null,
        padding: number | null = null
    ): string {
        size = size ?? SPECIMEN_SIZE;
        columns = columns ?? SPECIMEN_COLS;
        padding = padding ?? SPECIMEN_PADD;

        const glyphTable = this.getGlyfTable();
        if (glyphTable === null || this.glyphCount === 0) {
            return "";
        }

        const chunks: string[] = [];

        // mark top-left corner
        chunks.push("M0,0h1v1h-1z");

        const scale = size / 100.0;
        size += padding;
        let row = 0,
            index = 0;
        for (const glyph of glyphTable.glyphs) {
            if (glyph.contoursCount === 0) {
                continue;
            }
            row = Math.floor(index / columns);
            const col = index % columns;
            const tr = Transform.identity()
                .translate(padding + col * size, padding + row * size)
                .scale(scale, scale);
            const [svgPath, bbox] = glyph.toSVGPath(tr, true);
            if (bbox === null) {
                continue;
            }
            const bboxSize = bbox[1].sub(bbox[0]);
            if (bboxSize.x === 0 || bboxSize.y === 0) {
                continue;
            }
            chunks.push(svgPath);
            chunks.push("\n");
            index += 1;
        }

        // mark bottom-right corner
        const markX = padding + columns * size,
            markY = padding + (row + 1) * size;
        chunks.push(`M${markX},${markY}h1v1h-1z`);

        return chunks.join("");
    }

    info() {
        const nameTable = this.getNameTable();
        const headTable = this.getHeadTable();
        return {
            family: nameTable.family,
            subfamily: nameTable.subfamily,
            version: nameTable.version,
            glyph_count: this.glyphCount,
            post_count: this.getPostTable().glyphIdToName.size,
            units_per_em: headTable.unitsPerEm,
            modified_dt: headTable.modifiedDate.toISOString(),
            tables: Iter.from(this.tables)
                .map(([name, table]) => [name, table.length] as const)
                .collectObject(),
        };
    }

    #tableGet<T>(name: string, loader: (font: Font, reader: Reader) => T): T {
        let table: T = this.#cache.get(name);
        if (table === undefined) {
            const tableDesc = this.tables.get(name);
            if (tableDesc === undefined) {
                throw new Error(`Table not found: ${name}`);
            }
            table = loader(this, tableDesc.reader(this));
            this.#cache.set(name, table);
        }
        return table;
    }

    getNameTable(): NameTable {
        return this.#tableGet("name", NameTable.load);
    }

    getHeadTable(): HeadTable {
        return this.#tableGet("head", HeadTable.load);
    }

    getPostTable(): PostTable {
        return this.#tableGet("post", PostTable.load);
    }

    getCmapTable(): CmapTable {
        return this.#tableGet("cmap", CmapTable.load);
    }

    getLocaTable(): LocaTable | null {
        if (this.tables.get("loca") === undefined) {
            return null;
        }
        return this.#tableGet("loca", LocaTable.load);
    }

    getGlyfTable(): GlyfTable | null {
        if (this.tables.get("glyf") === undefined) {
            return null;
        }
        return this.#tableGet("glyf", GlyfTable.load);
    }

    getHheaTable(): HheaTable {
        return this.#tableGet("hhea", HheaTable.load);
    }

    getHmtxTable(): HmtxTable {
        return this.#tableGet("hmtx", HmtxTable.load);
    }
}

/**
 * Name table (required)
 * Reference: {@link https://learn.microsoft.com/en-us/typography/opentype/spec/name}
 */
export class NameTable {
    constructor(
        public copyright: string,
        public family: string,
        public subfamily: string,
        public fontId: string,
        public fullname: string,
        public version: string
    ) {}

    static load(_font: Font, reader: Reader): NameTable {
        reader.readU16(); // version
        const recordCount = reader.readU16();
        const storageOffset = reader.readU16();

        type NameRecord = {
            platfromId: number;
            encodingId: number;
            langaugeId: number;
            nameId: number;
            lenght: number;
            offset: number;
        };

        const records: NameRecord[] = [];
        for (let index = 0; index < recordCount; index++) {
            const record = {
                platfromId: reader.readU16(),
                encodingId: reader.readU16(),
                langaugeId: reader.readU16(),
                nameId: reader.readU16(),
                lenght: reader.readU16(),
                offset: reader.readU16(),
            };
            if (record.platfromId !== 3) {
                continue;
            }
            if (record.langaugeId !== 1033) {
                continue;
            }
            if (record.encodingId in [1, 10]) {
                records.push(record);
            }
        }

        const fields: [string, string, string, string, string, string] = ["", "", "", "", "", ""];
        const decoder = new TextDecoder("utf-16be");
        for (const record of records) {
            if (record.nameId > 5) {
                continue;
            }
            reader.seek(storageOffset + record.offset);
            const bytes = reader.read(record.lenght);
            fields[record.nameId] = decoder.decode(bytes);
        }
        return new NameTable(...fields);
    }
}

/**
 * Header Table (required)
 * Reference: {@link https://learn.microsoft.com/en-us/typography/opentype/spec/head}
 */
export class HeadTable {
    constructor(
        public revision: number,
        public flags: number,
        public unitsPerEm: number,
        public createdDate: Date,
        public modifiedDate: Date,
        public minPoint: Point,
        public maxPoint: Point,
        public macStyle: number,
        public lowestRecPpem: number,
        public fontDirectionHint: number,
        public indexToLocFormat: number,
        public glyphDataFormat: number
    ) {}

    static load(_font: Font, reader: Reader): HeadTable {
        reader.readU16(); // majorVersion = 1
        reader.readU16(); // minorVersion = 0
        const fontRevision = reader.readFixed();
        reader.readU32(); // checksum
        console.assert(reader.readU32() === 0x5f0f3cf5); // magicNumber
        const flags = reader.readU16();
        const unitsPerEm = reader.readU16();
        const createdDate = reader.readLongDate();
        const modifiedDate = reader.readLongDate();
        const minPoint = new Point(reader.readI16(), reader.readI16());
        const maxPoint = new Point(reader.readI16(), reader.readI16());
        const macStyle = reader.readU16();
        const lowestRecPpem = reader.readU16();
        const fontDirectionHint = reader.readI16();
        const indexToLocFormat = reader.readI16();
        const glyphDataFormat = reader.readI16();
        return new HeadTable(
            fontRevision,
            flags,
            unitsPerEm,
            createdDate,
            modifiedDate,
            minPoint,
            maxPoint,
            macStyle,
            lowestRecPpem,
            fontDirectionHint,
            indexToLocFormat,
            glyphDataFormat
        );
    }
}

/**
 * PostScript Table (required)
 * Reference: {@link https://learn.microsoft.com/en-us/typography/opentype/spec/post}
 */
export class PostTable {
    constructor(public glyphIdToName: Map<GlyphId, string>) {}

    toString(): string {
        return `PostTable(count=${this.glyphIdToName.size})`;
    }

    static load(_font: Font, reader: Reader): PostTable {
        const version = reader.readFixed();
        if (version !== 2) {
            return new PostTable(new Map());
        }
        reader.advance(28); // skip header

        // https://learn.microsoft.com/en-us/typography/opentype/spec/post#version-20
        const glyphCount = reader.readU16();
        const glyphIdToIndex: Map<GlyphId, number> = new Map();
        let maxIndex = 0;
        for (let glyphIndex = 0; glyphIndex < glyphCount; glyphIndex++) {
            const nameIndex = reader.readU16();
            if (nameIndex > 258) {
                const index = nameIndex - 258;
                maxIndex = Math.max(maxIndex, index);
                glyphIdToIndex.set(glyphIndex, index);
            }
        }

        const names: string[] = [];
        const namesCount = maxIndex + 1;
        for (let _i = 0; _i < namesCount; _i++) {
            const length = reader.readU8();
            names.push(reader.readString(length));
        }

        const glyphIdToName: Map<GlyphId, string> = new Map();
        for (const [glyphId, index] of glyphIdToIndex) {
            glyphIdToName.set(glyphId, names[index]!);
        }
        return new PostTable(glyphIdToName);
    }
}

/**
 * Character Map (required)
 * Reference: {@link https://learn.microsoft.com/en-us/typography/opentype/spec/cmap}
 */
export class CmapTable {
    constructor(
        public codepointToGlyphId: Map<Codepoint, GlyphId>,
        public glyphIdToCodepoint: Map<GlyphId, Codepoint>
    ) {}

    toString(): string {
        return `CmapTable(count=${this.codepointToGlyphId.size})`;
    }

    static load(_font: Font, reader: Reader): CmapTable {
        reader.readU16(); // version

        // find unicode sub-table
        let unicodeTableOffset = 0;
        const numTables = reader.readU16();
        for (let _i = 0; _i < numTables; _i++) {
            const platformId = reader.readU16(); // 0 - unicode
            const encodingId = reader.readU16();
            const subTableOffset = reader.readU32();
            if (platformId === 0 && encodingId === 4) {
                unicodeTableOffset = subTableOffset;
            } else if (!unicodeTableOffset && platformId === 0 && encodingId === 3) {
                unicodeTableOffset = subTableOffset;
            }
        }
        if (!unicodeTableOffset) {
            throw new Error("Only support unicode (0) format (4, 3) cmap tables");
        }

        // sub-table header
        reader.seek(unicodeTableOffset);
        const subtableFormat = reader.readU16();
        const cmap = new CmapTable(new Map(), new Map());

        if (subtableFormat === 12) {
            // https://learn.microsoft.com/en-us/typography/opentype/spec/cmap#format-12-segmented-coverage
            reader.readU16(); // reserved
            reader.readU32(); // length
            reader.readU32(); // language

            const numGroups = reader.readU32();
            for (let _i = 0; _i < numGroups; _i++) {
                const codepointStart = reader.readU32();
                const codepointEnd = reader.readU32() + 1;
                let glyphId = reader.readU32();
                for (let codepoint = codepointStart; codepoint < codepointEnd; codepoint++) {
                    cmap.glyphIdToCodepoint.set(glyphId, codepoint);
                    cmap.codepointToGlyphId.set(codepoint, glyphId);
                    glyphId += 1;
                }
            }
        } else if (subtableFormat == 4) {
            // https://learn.microsoft.com/en-us/typography/opentype/spec/cmap#format-4-segment-mapping-to-delta-values
            const stLength = reader.readU16();
            const stReader = reader.view(reader.tell(), reader.tell() + stLength);
            stReader.advance(2); // language

            const segmentCount = Math.floor(stReader.readU16() / 2);
            stReader.advance(6); // searchRange, entrySelector, rangeShift
            const numGroups = reader.readU32();
            const endCodes = Iter.range(segmentCount)
                .map((_) => stReader.readU16())
                .collectArray();
            stReader.readU16(); // reserved
            const startCodes = Iter.range(segmentCount)
                .map((_) => stReader.readU16())
                .collectArray();
            const idDeltas = Iter.range(segmentCount)
                .map((_) => stReader.readI16())
                .collectArray();
            const idRangeOffsets = Iter.range(segmentCount)
                .map((_) => stReader.readU16())
                .collectArray();
            const glyphIdArrayLen = (stReader.length() - stReader.tell()) / 2;
            const _glyphIdArray = Iter.range(glyphIdArrayLen)
                .map((_) => stReader.readU16())
                .collectArray();

            for (const [endCode, startCode, idDelta, idRangeOffset] of Iter.zip(
                endCodes,
                startCodes,
                idDeltas,
                idRangeOffsets
            )) {
                if (endCode === startCode && startCode === 0xffff) {
                    break;
                }
                for (const codepoint of Iter.range(startCode, endCode + 1)) {
                    if (idRangeOffset != 0) {
                        console.error("[cmap][format=4] idRangeOffset != not implemented");
                        break;
                    }
                    const glyphId = (codepoint + idDelta) % 65536;
                    cmap.glyphIdToCodepoint.set(glyphId, codepoint);
                    cmap.codepointToGlyphId.set(codepoint, glyphId);
                }
            }
        }

        return cmap;
    }
}

/**
 * Glyph index to location table (TTF)
 * Reference: {@link https://learn.microsoft.com/en-us/typography/opentype/spec/loca}
 */
export class LocaTable {
    constructor(public offsets: number[]) {}

    static load(font: Font, reader: Reader): LocaTable {
        let readOffset: (index: number) => number;
        if (font.getHeadTable().indexToLocFormat == 0) {
            readOffset = (_) => 2 * reader.readU16();
        } else {
            readOffset = (_) => reader.readU32();
        }
        const offsets = Iter.range(font.glyphCount + 1)
            .map(readOffset)
            .collectArray();
        return new LocaTable(offsets);
    }
}

/**
 * Glyph data (TTF)
 * Reference:
 *   - {@link https://learn.microsoft.com/en-us/typography/opentype/spec/glyf}
 */
export class GlyfTable {
    constructor(public glyphs: Glyph[]) {}

    toString(): string {
        return `GlyphTable(count=${this.glyphs.length})`;
    }

    static load(font: Font, reader: Reader): GlyfTable | null {
        const locaTable = font.getLocaTable();
        if (!locaTable) {
            return null;
        }
        const glyphs = Iter.range(font.glyphCount)
            .map((index) => {
                const offsetStart = locaTable.offsets[index];
                const offsetEnd = locaTable.offsets[index + 1];
                const glyphReader = reader.view(offsetStart, offsetEnd);
                return new Glyph(font, index, glyphReader);
            })
            .collectArray();
        return new GlyfTable(glyphs);
    }
}

/**
 * Horizontal header table (required)
 * Reference: {@link https://learn.microsoft.com/en-us/typography/opentype/spec/hhea}
 */
export class HheaTable {
    constructor(
        public ascender: number,
        public descender: number,
        public lineGap: number,
        public advanceWidthMax: number,
        public minLeftSideBearing: number,
        public minRightSideBearing: number,
        public xMaxExtent: number,
        public caretSlopeRise: number,
        public caretSlopeRun: number,
        public caretOffset: number,
        public numberOfMetrics: number
    ) {}

    static load(_font: Font, reader: Reader): HheaTable {
        console.assert(reader.readU16() == 1); // majorVersion
        console.assert(reader.readU16() == 0); // minorVersion
        const ascender = reader.readI16();
        const descender = reader.readI16();
        const lineGap = reader.readI16();
        const advanceWidthMax = reader.readU16();
        const minLeftSideBearing = reader.readI16();
        const minRightSideBearing = reader.readI16();
        const xMaxExtent = reader.readI16();
        const caretSlopeRise = reader.readI16();
        const caretSlopeRun = reader.readI16();
        const caretOffset = reader.readI16();
        reader.advance(10); // reserved + metric_data_format (always 0)
        const numberOfMetrics = reader.readU16();
        return new HheaTable(
            ascender,
            descender,
            lineGap,
            advanceWidthMax,
            minLeftSideBearing,
            minRightSideBearing,
            xMaxExtent,
            caretSlopeRise,
            caretSlopeRun,
            caretOffset,
            numberOfMetrics
        );
    }
}

type Metrics = { advance: number; sideBearing: number };

/**
 * Horizontal Metrics Table (required)
 * Reference: {@link https://learn.microsoft.com/en-us/typography/opentype/spec/hmtx}
 */
export class HmtxTable {
    constructor(
        public metrics: Metrics[],
        public bearings: number[],
        public numberOfMetrics: number
    ) {}

    getAdvance(glyphId: GlyphId): number | undefined {
        if (glyphId >= this.numberOfMetrics) {
            return undefined;
        }
        if (glyphId < this.metrics.length) {
            this.metrics.at(glyphId)?.advance;
        }
        return this.metrics.at(-1)?.advance;
    }

    getSideBearing(glyphId: GlyphId): number | undefined {
        if (glyphId < this.metrics.length) {
            return this.metrics.at(glyphId)?.sideBearing;
        } else {
            const bearingOffset = glyphId - this.metrics.length;
            return this.bearings.at(bearingOffset);
        }
    }

    toString(): string {
        return `HmtxTable(numberOfMetrix=${this.numberOfMetrics})`;
    }

    static load(font: Font, reader: Reader): HmtxTable {
        const hheaTable = font.getHheaTable();
        let numberOfMetrics = hheaTable.numberOfMetrics;
        const metrics = Iter.range(numberOfMetrics)
            .map((_) => {
                return {
                    advance: reader.readU16(),
                    sideBearing: reader.readI16(),
                };
            })
            .collectArray();
        const bearingCount = font.glyphCount - numberOfMetrics;
        let bearings: number[] = [];
        if (bearingCount > 0) {
            numberOfMetrics += bearingCount;
            bearings = Iter.range(bearingCount)
                .map((_) => reader.readI16())
                .collectArray();
        }
        return new HmtxTable(metrics, bearings, numberOfMetrics);
    }
}
