import { Iter } from "./iter.js";
import { Font as UFont, Glyph as UGlyph } from "./ufont.js";

export class Font {
    family: string;
    ufont: UFont;
    icons: Map<string, Icon>;

    constructor(family: string, ufont: UFont, nameToCodepoint: { [k: string]: number }) {
        const icons = new Iter(Object.entries(nameToCodepoint))
            .filterMap(([name, codepoint]) => {
                const glyph = ufont.glyphByCodepoint(codepoint);
                if (glyph) {
                    return [name, new Icon(this, name, codepoint, glyph)] as const;
                }
            })
            .collectMap();

        this.family = family;
        this.ufont = ufont;
        this.icons = icons;
    }

    // Create and register font from description
    static async load(fontDesc: { name: string; metadata: string; font: string }): Promise<Font> {
        const [metadata, fontData] = await Promise.all([
            fetch(fontDesc.metadata).then((r) => r.json()),
            fetch(fontDesc.font).then((r) => r.arrayBuffer()),
        ]);

        // register font
        document.fonts.add(new FontFace(fontDesc.name, fontData));

        // create style
        const style = document.createElement("style");
        style.innerText = `.${fontDesc.name} {font-family: "${fontDesc.name}"}`;
        document.getElementsByTagName("head")[0]!.appendChild(style);

        const font = new UFont(fontData);
        return new Font(fontDesc.name, font, metadata.names);
    }

    getIcon(name: string): Icon | undefined {
        return this.icons.get(name);
    }
}

class Icon {
    font: Font;
    glyph: UGlyph;
    name: string;
    codepoint: number;
    content: string;

    constructor(font: Font, name: string, codepoint: number, uglyph: UGlyph) {
        this.font = font;
        this.glyph = uglyph;
        this.name = name;
        this.codepoint = codepoint;
        this.content = String.fromCodePoint(this.codepoint);
    }

    get fullName(): string {
        return `${this.font.family}-${this.name}`;
    }

    toSVGString(): string {
        const [svgPath, _bbox] = this.glyph.toSVGPath();
        return [
            '<?xml version="1.0"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">',
            `  <path d="${svgPath}"/>`,
            "</svg>",
        ].join("\n");
    }

    toHTMLElement(): HTMLDivElement {
        const div = document.createElement("div");
        div.textContent = this.content;
        div.style.fontFamily = this.font.family;
        div.classList.add("icon-resolve");
        return div;
    }
}

export class IconSet {
    icons: Map<string, Map<string, Icon>>;
    size: number;

    constructor(icons: Map<string, Map<string, Icon>>) {
        this.icons = icons;
        this.size = new Iter(icons.values()).fold(0, (size, nameToIcon) => size + nameToIcon.size);
    }

    static fromFonts(fonts: Iterable<Font>) {
        const icons = new Iter(fonts)
            .map((font) => [font.family, font.icons] as const)
            .collectMap();
        return new IconSet(icons);
    }

    // Create new IconSet only containing icons with names matching selector
    filter(selector: string): IconSet {
        if (selector.length == 0) {
            return this;
        }
        const regex = new RegExp(selector);
        const icons = new Iter(this.icons)
            .filterMap(([fontFamily, icons]) => {
                const iconsFiltered = new Iter(icons)
                    .filter(([iconName, icon]) => {
                        return iconName.search(regex) >= 0;
                    })
                    .collectMap();
                return iconsFiltered.size == 0
                    ? null
                    : ([fontFamily, iconsFiltered] as [string, Map<string, Icon>]);
            })
            .collectMap();
        return new IconSet(icons);
    }

    find(iconFullName: string): Icon | null {
        const match = iconFullName.match(/(?<fontFamily>[^-]*)-(?<iconName>.*)/);
        if (!match) {
            return null;
        }
        const { fontFamily, iconName } = match.groups!;
        return this.icons.get(fontFamily!)?.get(iconName!) ?? null;
    }

    toHTMLElement(ctx: {
        sectionsExpanded: Map<string, boolean>;
        iconUI: { fold: Icon; unfold: Icon };
    }): HTMLDivElement {
        const sections = document.createElement("div");
        sections.classList.add("sections");
        new Iter(this.icons).forEach(([fontName, names]) => {
            // section
            const section = document.createElement("div");
            section.classList.add("section");
            sections.appendChild(section);

            // header
            const sectionHeader = document.createElement("div");
            sectionHeader.appendChild(
                (ctx.sectionsExpanded.get(fontName)
                    ? ctx.iconUI.fold
                    : ctx.iconUI.unfold
                ).toHTMLElement()
            );
            const fontNameCapital = fontName.charAt(0).toUpperCase() + fontName.slice(1);
            sectionHeader.appendChild(
                document.createTextNode(`${fontNameCapital} (${names.size})`)
            );
            sectionHeader.classList.add("section-header");
            sectionHeader.addEventListener("click", (event) => {
                if (ctx.sectionsExpanded.get(fontName)) {
                    ctx.sectionsExpanded.set(fontName, false);
                    sectionIcons.style.display = "none";
                    sectionHeader.replaceChild(
                        ctx.iconUI.unfold.toHTMLElement(),
                        sectionHeader.firstChild!
                    );
                } else {
                    ctx.sectionsExpanded.set(fontName, true);
                    sectionIcons.style.display = "";
                    sectionHeader.replaceChild(
                        ctx.iconUI.fold.toHTMLElement(),
                        sectionHeader.firstChild!
                    );
                }
            });
            section.appendChild(sectionHeader);

            // icons
            const headerIconName = document.getElementById("header-icon-name")!;
            const sectionIcons = document.createElement("div");
            sectionIcons.classList.add("section-icons");
            sectionIcons.classList.add(fontName);
            sectionIcons.style.display = ctx.sectionsExpanded.get(fontName) ? "" : "none";
            new Iter(names).forEach(([name, icon]) => {
                const iconElement = document.createElement("div");
                const iconName = `${fontName}-${name}`;
                iconElement.textContent = icon.content;
                iconElement.dataset.name = iconName;
                iconElement.addEventListener("click", () => previewShow(icon));
                iconElement.addEventListener("mouseover", (event) => {
                    const target = event.target as HTMLDivElement;
                    headerIconName.innerText = target.dataset.name!;
                });
                iconElement.addEventListener("mouseleave", (event) => {
                    headerIconName.innerText = "";
                });
                sectionIcons.appendChild(iconElement);
            });
            section.appendChild(sectionIcons);
        });
        return sections;
    }
}

function debounce<A extends any[]>(
    this: any,
    func: (...args: A) => void,
    timeout: number = 300
): (...args: A) => void {
    let timer: number;
    return (...args) => {
        clearTimeout(timer);
        timer = window.setTimeout(() => {
            func.apply(this, args);
        }, timeout);
    };
}

function previewShow(icon: Icon): void {
    const previewSVG = document.getElementById("preview-svg")!;
    previewSVG.innerHTML = icon.toSVGString();

    const previewName = document.getElementById("preview-name")!;
    const hexCodepoint = icon.codepoint.toString(16).toUpperCase();
    previewName.innerHTML = `${icon.fullName} <span class="codepoint">U+${hexCodepoint}<span>`;

    const previewDialog = document.getElementById("preview-dialog") as HTMLDialogElement;
    previewDialog.dataset.name = icon.fullName;
    previewDialog.showModal();
}

export function setup(iconSet: IconSet) {
    // setup context
    const iconUI = {
        close: iconSet.find("material-close-circle-outline")!,
        clipboard: iconSet.find("material-clipboard-outline")!,
        copySVG: iconSet.find("material-vector-curve")!,
        fold: iconSet.find("material-minus-box-outline")!,
        foldAll: iconSet.find("material-collapse-all-outline")!,
        unfold: iconSet.find("material-plus-box-outline")!,
        unfoldAll: iconSet.find("material-expand-all-outline")!,
        theme: iconSet.find("material-theme-light-dark")!,
    };
    const sectionsExpanded = new Iter(iconSet.icons.keys())
        .map((name) => [name, true] as [string, boolean])
        .collectMap();
    const ctx = { iconUI, sectionsExpanded };

    // preview dialog
    const previewDialog = document.getElementById("preview-dialog") as HTMLDialogElement;
    previewDialog.addEventListener("click", (event) => {
        const dialogDims = previewDialog.getBoundingClientRect();
        if (
            event.clientX < dialogDims.left ||
            event.clientX > dialogDims.right ||
            event.clientY < dialogDims.top ||
            event.clientX > dialogDims.bottom
        ) {
            previewDialog.close();
        }
    });
    const previewClose = document.getElementById("preview-close") as HTMLButtonElement;
    previewClose.replaceChildren(ctx.iconUI.close.toHTMLElement());
    previewClose.addEventListener("click", () => {
        previewDialog.close();
    });
    const previewCopyName = document.getElementById("preview-copy-name") as HTMLButtonElement;
    previewCopyName.replaceChildren(ctx.iconUI.clipboard.toHTMLElement());
    previewCopyName.addEventListener("click", () => {
        navigator.clipboard.writeText(previewDialog.dataset.name!);
    });
    const previewCopySVG = document.getElementById("preview-copy-svg") as HTMLButtonElement;
    previewCopySVG.replaceChildren(ctx.iconUI.copySVG.toHTMLElement());
    previewCopySVG.addEventListener("click", () => {
        let icon = iconSet.find(previewDialog.dataset.name!)!;
        navigator.clipboard.writeText(icon.toSVGString());
    });

    // search
    const searchResult = document.getElementById("search-result")!;
    const searchInput = document.getElementById("header-search-input") as HTMLInputElement;
    const resultUpdate = () => {
        let iconSetFilter = iconSet.filter(searchInput.value).toHTMLElement(ctx);
        searchResult.replaceChildren(iconSetFilter);
    };
    searchInput.addEventListener("input", debounce(resultUpdate));

    // expand/collapse
    const collapse = document.getElementById("collapse")!;
    collapse.appendChild(ctx.iconUI.foldAll.toHTMLElement());
    collapse.addEventListener("click", () => {
        const hide = new Iter(ctx.sectionsExpanded.values()).fold(
            false,
            (acc, item) => acc || item
        );
        for (const name of ctx.sectionsExpanded.keys()) {
            ctx.sectionsExpanded.set(name, !hide);
        }
        collapse.replaceChildren(
            (hide ? ctx.iconUI.unfoldAll : ctx.iconUI.foldAll).toHTMLElement()
        );
        resultUpdate();
    });

    // Light/Dark theme button
    const themeToggleButton = document.getElementById("theme-button") as HTMLButtonElement;
    themeToggleButton.replaceChildren(ctx.iconUI.theme.toHTMLElement());
    themeToggleButton.addEventListener("click", () => {
        // apply theme without search results as it is much faster
        searchResult.replaceChildren();
        localStorage.setItem(
            "theme-dark",
            document.documentElement.classList.toggle("theme-dark").toString()
        );
        resultUpdate();
    });

    resultUpdate();
}
