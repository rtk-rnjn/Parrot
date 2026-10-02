from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import discord
from bs4 import BeautifulSoup, Comment, Tag
from bs4.element import NavigableString
from discord.utils import escape_markdown
from yaml import safe_load as yaml_load

from .tio import Tio

_MARGIN_RE = re.compile(r"margin-left:\s*(\d+)%")
_WS_RE = re.compile(r"\s+")
_SUBTITLE_RE = re.compile(r"[A-Za-z][A-Za-z ]+")
_NAME_SPLIT_RE = re.compile(r"\s[-\u2013\u2014]\s")

DEBIAN_RED = 0xD70A53
MIN_MARGIN_PERCENT = 15
MIN_TABLE_CELLS = 2
SHORT_DESCRIPTION_LIMIT = 80

quickmap: dict[str, str] = {
    "asm": "assembly",
    "c#": "cs",
    "c++": "cpp",
    "csharp": "cs",
    "f#": "fs",
    "fsharp": "fs",
    "js": "javascript",
    "nimrod": "nim",
    "py": "python",
    "q#": "qs",
    "rs": "rust",
    "sh": "bash",
    "python": "python",
}

with Path("assets/default_langs.yml").open(encoding="utf-8") as file:
    default_langs = yaml_load(file)

with Path("assets/lang.txt").open(encoding="utf-8") as file:
    languages = {line.strip() for line in file}


def resolve_language(language: str) -> str:
    language = language.lower()
    return default_langs[quickmap.get(language, language)]


def language_error(language: str) -> str:
    suggestions = [lang for lang in languages if lang.startswith(language[:3])][:10]

    message = f"`{language}` not available."

    if suggestions:
        message += " Did you mean:\n" + "\n".join(suggestions)

    return message


async def execute_run(language: str, code_string: str) -> str:
    language = resolve_language(language)

    if language not in languages:
        return language_error(language)

    result = await Tio(language, code_string).send()

    if result is None:
        return "```\n```"

    try:
        start = result.rindex("Real time: ")
        end = result.rindex("%\nExit code: ")
        result = result[:start] + result[end + 2 :]
    except ValueError:
        # Too much output removes these markers.
        pass

    return f"```\n{escape_markdown(result.strip())}```"


@dataclass
class Block:
    level: int  # 0 = normal, 1 = indented description
    text: str


@dataclass
class ManSection:
    title: str
    blocks: list[Block] = field(default_factory=list)
    raw: str = ""


@dataclass
class ManPage:
    name: str
    summary: str
    sections: list[ManSection]


def _raw(node) -> str:
    """Plain text, keeping <br> as newlines. No markdown escaping."""
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return _WS_RE.sub(" ", str(node))
    if node.name == "br":
        return "\n"
    return "".join(_raw(c) for c in node.children)


def _bold(tag: Tag) -> str:
    lines = [ln.strip() for ln in _raw(tag).split("\n")]
    if not any(lines):
        return " " if _raw(tag) else ""

    prefix = ""
    # "General options <br> -C file" -> sub-heading followed by the option
    if len(lines) > 1 and lines[0] and _SUBTITLE_RE.fullmatch(lines[0]):
        prefix = f"\n### {lines[0]}\n"
        lines = lines[1:]

    code = "\n".join(f"`{ln.replace('`', chr(39))}`" for ln in lines if ln)
    return prefix + code


def _link(tag: Tag) -> str:
    href = str(tag.get("href", ""))
    if href.startswith("mailto:"):
        return discord.utils.escape_markdown(tag.get_text())
    text = "".join(_inline(c) for c in tag.children).strip()
    if not text or href.startswith("#") or not href:
        return text
    if href.startswith("/"):
        href = "https://man.cx" + href
    href = href.replace("(", "%28").replace(")", "%29")
    return f"[{text}]({href})"


def _inline(node) -> str:  # noqa: PLR0911
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return discord.utils.escape_markdown(_WS_RE.sub(" ", str(node)))

    assert isinstance(node, Tag), f"Unexpected node type: {type(node)}"

    match node.name:
        case "br":
            return "\n"
        case "img":
            return ""
        case "b" | "strong":
            return _bold(node)
        case "i" | "em":
            inner = "".join(_inline(c) for c in node.children).strip()
            return f"*{inner}*" if inner else ""
        case "a":
            return _link(node)
        case _:
            return "".join(_inline(c) for c in node.children)


def _clean(text: str) -> str:
    lines = [re.sub(r" {2,}", " ", ln).strip() for ln in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _level(tag: Tag) -> int:
    style = tag.get("style")
    match = _MARGIN_RE.search(style if isinstance(style, str) else "")
    return 1 if match and int(match[1]) >= MIN_MARGIN_PERCENT else 0


def _code_block(tag: Tag) -> str:
    lines = [re.sub(r" {2,}", " ", ln).strip() for ln in _raw(tag).split("\n")]
    return "```\n" + "\n".join(ln for ln in lines if ln) + "\n```"


def _blocks_from(node: Tag, section_title: str) -> list[Block]:
    if node.name == "p":
        if not node.get_text(strip=True):
            return []
        if section_title == "SYNOPSIS" or node.get_text().lstrip().startswith("$ "):
            return [Block(_level(node), _code_block(node))]
        text = _clean(_inline(node))
        return [Block(_level(node), text)] if text else []

    if node.name == "pre":
        return [Block(0, _code_block(node))]

    if node.name == "table":
        out: list[Block] = []
        for row in node.find_all("tr"):
            cells = [c for c in (_clean(_inline(td)) for td in row.find_all("td")) if c]
            if len(cells) == 1:
                out.append(Block(0, cells[0]))
            elif len(cells) >= MIN_TABLE_CELLS:
                key, desc = cells[0], cells[-1]
                if len(desc) <= SHORT_DESCRIPTION_LIMIT:
                    out.append(Block(0, f"{key} \u2014 {desc}"))
                else:
                    out += [Block(0, key), Block(1, desc)]
        return out

    return []


def parse_man_page(html: str, parser: str = "lxml") -> ManPage | None:
    # Use lxml or html5lib: man.cx leaves some <p> unclosed, and html.parser nests them.
    soup = BeautifulSoup(html, parser)
    main = soup.find("main") or soup

    sections: list[ManSection] = []
    current: ManSection | None = None

    for child in main.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "h2":
            current = ManSection(child.get_text(" ", strip=True))
            sections.append(current)
        elif current is not None:
            if current.title == "NAME":
                current.raw += " " + child.get_text(" ")
            else:
                current.blocks.extend(_blocks_from(child, current.title))

    name_section = next((s for s in sections if s.title == "NAME"), None)
    if name_section is None:
        return None

    raw = _WS_RE.sub(" ", name_section.raw).strip()
    name, _, summary = [part.strip() for part in [*_NAME_SPLIT_RE.split(raw, maxsplit=1), ""]][:3] if _NAME_SPLIT_RE.search(raw) else (raw, "", "")

    return ManPage(
        name=name,
        summary=summary,
        sections=[s for s in sections if s.title != "NAME" and s.blocks],
    )


def _quote(text: str) -> str:
    return "\n".join(f"> {ln}" for ln in text.split("\n") if ln.strip())


def _render_unit(blocks: list[Block]) -> str:
    out = ""
    prev: Block | None = None
    for block in blocks:
        text = _quote(block.text) if block.level else block.text
        if prev is None:
            out = text
        elif block.level == 1 and prev.level == 0:
            out += "\n" + text
        elif block.level == 1 and prev.level == 1:
            out += "\n> \u200b\n" + text
        else:
            out += "\n\n" + text
        prev = block
    return out


def _split_long(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    pieces, buf = [], ""
    for current_line in text.split("\n"):
        remaining_line = current_line
        while len(remaining_line) > limit:
            if buf:
                pieces.append(buf)
                buf = ""
            pieces.append(remaining_line[:limit])
            remaining_line = remaining_line[limit:]
        if buf and len(buf) + 1 + len(remaining_line) > limit:
            pieces.append(buf)
            buf = remaining_line
        else:
            buf = f"{buf}\n{remaining_line}" if buf else remaining_line
    if buf:
        pieces.append(buf)
    return pieces


def paginate_section(section: ManSection, limit: int = 1800) -> list[str]:
    # A "unit" is a level-0 block plus the indented descriptions that follow it.
    units: list[list[Block]] = []
    for block in section.blocks:
        if block.level == 0 or not units:
            units.append([block])
        else:
            units[-1].append(block)

    pages: list[str] = []
    buf = ""
    for unit in units:
        for piece in _split_long(_render_unit(unit), limit):
            if buf and len(buf) + 2 + len(piece) > limit:
                pages.append(buf)
                buf = piece
            else:
                buf = f"{buf}\n\n{piece}" if buf else piece
    if buf:
        pages.append(buf)
    return pages


def build_embeds(page: ManPage, url: str) -> list[discord.Embed]:
    chunks = [(s.title, paginate_section(s)) for s in page.sections]
    chunks = [(title, pages) for title, pages in chunks if pages]

    toc, number = [], 2
    for title, pages in chunks:
        toc.append(f"`{number:>2}` \u00b7 {title.title()}")
        number += len(pages)

    def base() -> discord.Embed:
        return discord.Embed(colour=DEBIAN_RED, url=url)

    overview = base()
    overview.title = page.name
    overview.url = url
    overview.description = f"{discord.utils.escape_markdown(page.summary)}\n\n### Contents\n" + "\n".join(toc)
    overview.set_thumbnail(url="https://www.debian.org/logos/openlogo-nd-75.png")
    overview.set_footer(text="Use the buttons below to navigate")
    embeds = [overview]

    for title, pages in chunks:
        for i, text in enumerate(pages):
            heading = f"## {title}" + (" *(cont.)*" if i else "")
            embed = base()
            embed.title = page.name
            embed.url = url
            embed.description = f"{heading}\n{text}"
            embed.set_footer(text=f"{title.title()} \u00b7 man.cx")
            embeds.append(embed)

    return embeds
