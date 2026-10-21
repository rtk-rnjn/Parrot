from __future__ import annotations

import ast
import asyncio
import builtins
import importlib.util
import inspect
import keyword
import pathlib
import platform
import re
import sys
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote

import aiohttp
import arrow
import discord
import frontmatter
from bs4 import BeautifulSoup, Tag
from discord.ext import commands
from rapidfuzz.process import extractOne

from core.utils import BaseLayoutView, NoticeLayout, truncate

from .knowledge import COMPLEXITY_DB, EXCEPTIONS_DB, OPERATORS_DB, STDLIB_CURATED, ExceptionInfo

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from core import Bot

    from .knowledge import ComplexityInfo, OperatorInfo, StdlibMeta

USER_AGENT = "Parrot Discord bot (https://github.com/rtk-rnjn/Parrot)"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

PYTHON_DOCS_URL = "https://docs.python.org/3"
PEPS_API_URL = "https://peps.python.org/api/peps.json"
PEPS_BASE_URL = "https://peps.python.org"
ENDOFLIFE_PYTHON_URL = "https://endoflife.date/api/python.json"
CPYTHON_BLOB_URL = "https://github.com/python/cpython/blob/main"
PYTHON_ICON = "https://www.python.org/static/community_logos/python-logo-only.png"

DOT = " \N{MIDDLE DOT} "
MIN_TUTORIAL_SCORE = 60
BODY_LIMIT = 1500
ITEMS_PER_PAGE = 8

PYTHON_COLOUR = discord.Colour(0x3776AB)
PYTHON_GOLD = discord.Colour(0xFFD43B)
ACTIVE_COLOUR = discord.Colour(0x238636)
SECURITY_COLOUR = discord.Colour(0xD29922)
EOL_COLOUR = discord.Colour(0xDA3633)
DRAFT_COLOUR = discord.Colour(0x6E7681)

PEP_STATUS_COLOURS: dict[str, discord.Colour] = {
    "Final": ACTIVE_COLOUR,
    "Active": ACTIVE_COLOUR,
    "Accepted": ACTIVE_COLOUR,
    "Provisional": SECURITY_COLOUR,
    "Draft": PYTHON_COLOUR,
    "Deferred": DRAFT_COLOUR,
    "Rejected": EOL_COLOUR,
    "Withdrawn": EOL_COLOUR,
    "Superseded": DRAFT_COLOUR,
}

SPHINX_INV_LINE = re.compile(r"(?x)(.+?)\s+(\S+:\S+)\s+(-?\d+)\s+(\S+)\s+(.*)")
PEP_ARG_PATTERN = re.compile(r"^(?:pep[-#\s]*)?(\d{1,5})$", re.IGNORECASE)
TUTORIAL_DIR = Path("extra/tutorials/python")


class PythonError(Exception):
    """A problem that should be shown to the user as-is."""


@dataclass(frozen=True, slots=True)
class TutorialTag:
    name: str
    content: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class SphinxEntry:
    name: str
    domain_role: str
    priority: int
    url: str
    dispname: str

    @property
    def role_label(self) -> str:
        _, _, role = self.domain_role.partition(":")
        return {
            "module": "module",
            "function": "function",
            "class": "class",
            "method": "method",
            "classmethod": "classmethod",
            "staticmethod": "staticmethod",
            "exception": "exception",
            "attribute": "attribute",
            "data": "constant / data",
            "label": "section",
            "term": "glossary term",
        }.get(role, role)


def safe(text_value: str | None, limit: int = 200) -> str:
    """One escaped, mention-free line of user-provided text."""
    flat = " ".join((text_value or "").split())
    return truncate(discord.utils.escape_markdown(discord.utils.escape_mentions(flat)), limit)


def code(text_value: str, limit: int = 60) -> str:
    return f"`{truncate(text_value.replace('`', chr(39)), limit)}`"


def parse_time(iso: str | None) -> datetime | None:
    if not iso or not isinstance(iso, str):
        return None
    try:
        return arrow.get(iso).datetime
    except ValueError, TypeError:
        return None


def when(iso: str | None, style: Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"] = "R") -> str | None:
    moment = parse_time(iso)
    return discord.utils.format_dt(moment, style) if moment else None


def dated(iso: str | None) -> str | None:
    return f"{when(iso, 'D')} ({when(iso)})" if parse_time(iso) else None


def valid_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("http://", "https://")) and len(url) <= 512


def text(content: str) -> discord.ui.TextDisplay:
    return discord.ui.TextDisplay(content)


def facts(*pairs: tuple[str, str | None]) -> discord.ui.TextDisplay | None:
    lines = [f"**{label}**: {value}" for label, value in pairs if value]
    return text("\n".join(lines)) if lines else None


def collect(*items: discord.ui.Item | None) -> list[discord.ui.Item]:
    return [item for item in items if item is not None]


def header(title: str, subtitle: str | None = None, *extra: str, thumbnail: str | None = PYTHON_ICON) -> discord.ui.Item:
    """Title block, with an optional thumbnail on the right."""
    parts = [text(f"## {title}" + (f"\n-# {subtitle}" if subtitle else ""))]
    parts.extend(text(line) for line in extra if line)
    if thumbnail and valid_url(thumbnail):
        return discord.ui.Section(*parts, accessory=discord.ui.Thumbnail(thumbnail))
    return text("\n".join(part.content for part in parts))


def pack(entries: Sequence[str], limit: int = 900) -> str:
    """Inline-code chips that fit in ``limit`` characters, followed by how many were left out."""
    shown: list[str] = []
    used = 0
    for entry in entries:
        piece = f"`{entry.replace('`', chr(39))}`"
        if used + len(piece) + 1 > limit:
            break
        shown.append(piece)
        used += len(piece) + 1
    left = len(entries) - len(shown)
    return " ".join(shown) + (f" *+{left} more*" if left else "")


@dataclass(slots=True)
class Page:
    """One screen of a :class:`PythonView`. ``body`` is called on every render so items are always fresh."""

    body: Callable[[], list[discord.ui.Item]]
    url: str | None = None
    label: str = "Open Docs"
    colour: discord.Colour = PYTHON_COLOUR
    links: list[tuple[str, str]] = field(default_factory=list)


class PythonView(BaseLayoutView):
    """A single container with the page content, optional Previous/Next buttons and link buttons."""

    def __init__(self, author: discord.User | discord.Member, pages: Sequence[Page], *, timeout: float = 180) -> None:
        super().__init__(author, timeout=timeout)
        self.pages = list(pages)
        self.index = 0
        self.container = discord.ui.Container(accent_colour=self.pages[0].colour)
        self.add_item(self.container)
        self.render()

    def render(self) -> None:
        page = self.pages[self.index]
        self.container.clear_items()
        self.container.accent_colour = page.colour
        for item in page.body():
            self.container.add_item(item)

        rows: list[discord.ui.ActionRow] = []
        if len(self.pages) > 1:
            rows.append(
                discord.ui.ActionRow(
                    self._nav_button("Previous", -1, "\N{BLACK LEFT-POINTING TRIANGLE}", disabled=self.index == 0),
                    discord.ui.Button(label=f"{self.index + 1} / {len(self.pages)}", disabled=True),
                    self._nav_button("Next", 1, "\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=self.index >= len(self.pages) - 1),
                )
            )

        links = ([(page.label, page.url)] if page.url else []) + page.links
        buttons = [discord.ui.Button(label=label[:80], url=url) for label, url in links if valid_url(url)][:5]
        if buttons:
            rows.append(discord.ui.ActionRow(*buttons))

        if rows:
            self.container.add_item(discord.ui.Separator())
            for row in rows:
                self.container.add_item(row)

    def _nav_button(self, label: str, step: int, emoji: str, *, disabled: bool) -> discord.ui.Button:
        button = discord.ui.Button(label=label, emoji=emoji, disabled=disabled)

        async def callback(interaction: discord.Interaction) -> None:
            self.index = max(0, min(len(self.pages) - 1, self.index + step))
            self.render()
            await interaction.response.edit_message(view=self)

        button.callback = callback
        return button


def parse_sphinx_inventory(raw: bytes, base_url: str) -> list[SphinxEntry]:
    """Parse a Sphinx v2 ``objects.inv`` file into structured :class:`SphinxEntry` items."""
    lines = raw.splitlines()
    if len(lines) < 4 or not lines[0].startswith(b"# Sphinx inventory version 2"):
        return []
    compressed = b"\n".join(lines[4:])
    try:
        decompressed = zlib.decompress(compressed).decode("utf-8", "replace")
    except zlib.error:
        return []

    entries: list[SphinxEntry] = []
    for line in decompressed.splitlines():
        match = SPHINX_INV_LINE.match(line.strip())
        if not match:
            continue
        name, domain_role, prio_str, location, dispname = match.groups()
        if location.endswith("$"):
            location = location[:-1] + name
        if dispname == "-":
            dispname = name
        entries.append(
            SphinxEntry(
                name=name,
                domain_role=domain_role,
                priority=int(prio_str),
                url=f"{base_url.rstrip('/')}/{location.lstrip('/')}",
                dispname=dispname,
            )
        )
    return entries


def extract_pep_abstract(html: str) -> str | None:
    """Extract the Abstract or first overview paragraphs from a PEP HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("section#abstract, #abstract, section#overview")
    if section is None:
        article = soup.select_one("article, section#pep-content, div.document")
        paragraphs = article.select("p") if article else []
    else:
        paragraphs = section.select("p")

    chunks: list[str] = []
    total = 0
    for p in paragraphs[:4]:
        line = " ".join(p.get_text(" ").split()).strip()
        if not line:
            continue
        chunks.append(line)
        total += len(line)
        if total >= 700:
            break
    if not chunks:
        return None
    joined = "\n\n".join(chunks)
    return truncate(discord.utils.escape_mentions(joined), 900)


def extract_sphinx_doc_section(html: str, page_url: str, anchor: str | None) -> tuple[str | None, str, list[str]]:  # noqa: PLR0912
    """Extract signature, description, and sub-items from a Python documentation HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.body, [role=main]") or soup

    target: Tag | None = None
    if anchor:
        found = root.find(id=anchor)
        if isinstance(found, Tag):
            target = found.find_parent("dl") if found.name == "dt" else found

    signature: str | None = None
    paragraphs: list[str] = []
    members: list[str] = []

    if target is not None and target.name == "dl":
        dt = target.find("dt", id=anchor) or target.find("dt")  # pyright: ignore[reportArgumentType, reportCallIssue]
        if dt is not None:
            sig_text = " ".join(dt.get_text(" ").split()).replace("\N{PILCROW SIGN}", "").strip()
            signature = truncate(sig_text, 240)
        dd = target.find("dd")
        search_scope = dd or target
    else:
        scope = target if target is not None else root
        first_dl = scope.find("dl", class_=re.compile(r"py\s+(function|class|method|exception)"))
        if first_dl is not None and anchor is None:
            dt = first_dl.find("dt")
            if dt is not None:
                sig_text = " ".join(dt.get_text(" ").split()).replace("\N{PILCROW SIGN}", "").strip()
                signature = truncate(sig_text, 240)
        search_scope = scope

    for p in search_scope.find_all("p", recursive=True)[:6]:
        if p.find_parent("div", class_="admonition"):
            continue
        clean = " ".join(p.get_text(" ").split()).strip()
        if clean and len(clean) > 15:
            paragraphs.append(clean)
        if sum(len(x) for x in paragraphs) >= 900:
            break

    for dt in root.select("dl.py > dt[id]")[:25]:
        dt_id = dt.get("id")
        if isinstance(dt_id, str) and dt_id != anchor:
            members.append(dt_id)

    body = "\n\n".join(paragraphs) if paragraphs else "*Open the documentation link below to read the full specification.*"
    return signature, truncate(discord.utils.escape_mentions(body), 1100), members


def tutorial_items(name: str, content: str, score: float | None = None) -> list[discord.ui.Item]:
    subtitle = "Python Tutorial" + (f"{DOT}match {score:.0f}%" if score is not None and score < 100 else "")
    return collect(
        header(f"Tutorial: `{name}`", subtitle),
        discord.ui.Separator(),
        text(truncate(content, BODY_LIMIT)),
    )


def tutorial_list_items(names: Sequence[str], chunk: Sequence[str], total: int) -> list[discord.ui.Item]:
    subtitle = f"{total} tutorial{'' if total == 1 else 's'} available{DOT}use `python-tutorial <name>`"
    listing = "\n".join(f"\N{BULLET} `{name}`" for name in chunk)
    return collect(
        header("Available Python Tutorials", subtitle),
        discord.ui.Separator(),
        text(listing or "*No tutorials loaded.*"),
        text(f"-# Quick lookup: {pack(names, 400)}"),
    )


def pep_items(pep: dict[str, Any], abstract: str | None) -> list[discord.ui.Item]:
    number = pep.get("number", 0)
    title = safe(pep.get("title"), 180)
    status = pep.get("status") or "Unknown"
    kind = pep.get("type") or "PEP"
    topic = pep.get("topic")
    subtitle_parts = [f"PEP {number:04d}", status, kind]
    if topic:
        subtitle_parts.append(topic)

    top = header(
        f"[PEP {number} \N{EM DASH} {title}]({pep.get('url') or f'{PEPS_BASE_URL}/pep-{number:04d}/'})",
        DOT.join(subtitle_parts),
    )

    body = abstract or "*No abstract preview available. Select **Open PEP** below to read the full document.*"
    details = facts(
        ("Author(s)", safe(pep.get("authors"), 160)),
        ("Status", f"`{status}` ({kind})"),
        ("Python Version", f"`{pep['python_version']}`" if pep.get("python_version") else None),
        ("Created", safe(pep.get("created"), 40)),
        ("Requires", f"PEP {pep['requires']}" if pep.get("requires") else None),
        ("Replaces", f"PEP {pep['replaces']}" if pep.get("replaces") else None),
        ("Superseded By", f"PEP {pep['superseded_by']}" if pep.get("superseded_by") else None),
    )
    return collect(top, discord.ui.Separator(), text(body), discord.ui.Separator(), details)


def pydoc_items(
    entry: SphinxEntry,
    signature: str | None,
    description: str,
    members: list[str],
    related: list[SphinxEntry],
) -> list[discord.ui.Item]:
    top = header(
        f"[`{entry.name}`]({entry.url})",
        f"Python 3 Documentation{DOT}{entry.role_label}",
    )
    sig_block = text(f"```py\n{signature}\n```") if signature else None
    member_block = text(f"**Documented Symbols**\n{pack(members, 600)}") if members else None

    related_lines = [f"\N{BULLET} [`{rel.name}`]({rel.url}) \N{EM DASH} *{rel.role_label}*" for rel in related[:5] if rel.url != entry.url]
    related_block = text("**Related Entries**\n" + "\n".join(related_lines)) if related_lines else None

    return collect(
        top,
        discord.ui.Separator(),
        sig_block,
        text(description),
        discord.ui.Separator() if (member_block or related_block) else None,
        member_block,
        related_block,
    )


def stdlib_items(
    name: str,
    doc_url: str,
    curated: StdlibMeta | None,
    synopsis: str,
    exports: list[str],
    source_url: str | None,
    is_builtin_c: bool,
) -> list[discord.ui.Item]:
    category = curated.category if curated else ("Built-in C Module" if is_builtin_c else "Standard Library Module")
    top = header(
        f"[`{name}`]({doc_url})",
        f"Python Standard Library{DOT}{category}",
        synopsis,
    )

    highlights = list(curated.highlights) if curated and curated.highlights else exports[:18]
    highlights_block = text(f"**Key Exports & Symbols**\n{pack(highlights, 700)}") if highlights else None
    example_block = text(f"**Example**\n```py\n{curated.example}\n```") if curated and curated.example else None

    details = facts(
        ("Import", f"`import {name}`"),
        ("Implementation", "Built-in C Extension" if is_builtin_c else "Python Standard Library"),
        ("CPython Source", f"[`{curated.source_path}`]({source_url})" if curated and curated.source_path and source_url else None),
    )
    return collect(
        top,
        discord.ui.Separator(),
        highlights_block,
        example_block,
        discord.ui.Separator(),
        details,
    )


def versions_items(cycles: list[dict[str, Any]], *, active_view: bool) -> list[discord.ui.Item]:
    now_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    heading = "Supported Python Releases" if active_view else "Historical / End-of-Life Python Releases"
    subtitle = f"Runtime: Python `{platform.python_version()}`{DOT}Data from endoflife.date & python.org"

    lines: list[str] = []
    for item in cycles:
        cycle = item.get("cycle", "?")
        latest = item.get("latest", cycle)
        released = item.get("releaseDate")
        eol = item.get("eol")
        support = item.get("support")

        is_eol = isinstance(eol, str) and eol <= now_str
        is_bugfix = (isinstance(support, str) and support > now_str) or support is True
        if is_eol:
            badge = "\N{LARGE RED CIRCLE} EOL"
        elif is_bugfix:
            badge = "\N{LARGE GREEN CIRCLE} Bugfix"
        else:
            badge = "\N{LARGE YELLOW CIRCLE} Security"

        eol_str = when(eol) if isinstance(eol, str) else ("Active" if not eol else str(eol))
        rel_str = when(released, "D") if isinstance(released, str) else "TBD"
        lines.append(f"**Python {cycle}** (`{latest}`){DOT}{badge}\n-# Released: {rel_str}{DOT}End of life: {eol_str or 'TBD'}")

    return collect(
        header(heading, subtitle),
        discord.ui.Separator(),
        text("\n\n".join(lines) if lines else "*No release cycles found.*"),
        text(
            "-# Each Python minor release receives ~2 years of full bugfix support followed by ~3 years of security fixes (5 years total, PEP 602)."
        ),
    )


def exception_items(info: ExceptionInfo, mro_chain: str, doc_url: str) -> list[discord.ui.Item]:
    top = header(
        f"[`{info.name}`]({doc_url})",
        f"Python Exception{DOT}{info.category}",
        info.summary,
    )
    causes = "\n".join(f"\N{BULLET} {cause}" for cause in info.causes)
    details = facts(
        ("Hierarchy (MRO)", mro_chain),
        ("How to Fix", info.fix),
    )
    return collect(
        top,
        discord.ui.Separator(),
        text(f"**Common Causes**\n{causes}"),
        details,
        text(f"**Example**\n```py\n{info.example}\n```"),
    )


def operator_items(info: OperatorInfo, doc_url: str) -> list[discord.ui.Item]:
    top = header(
        f"[`{info.symbol}` \N{EM DASH} {info.name}]({doc_url})",
        f"Python Operator{DOT}{info.category}",
        info.summary,
    )
    details = facts(
        ("Symbol / Syntax", f"`{info.symbol}`"),
        ("Precedence", info.precedence),
        ("Special Methods (Dunder)", f"`{info.dunder}`"),
        ("`operator` Module", f"`{info.operator_func}`" if info.operator_func else None),
        ("Aliases", ", ".join(f"`{a}`" for a in info.aliases[:6])),
    )
    return collect(
        top,
        discord.ui.Separator(),
        details,
        discord.ui.Separator(),
        text(f"**Examples**\n```py\n{info.example}\n```"),
    )


def builtin_items(
    name: str,
    kind: str,
    signature_str: str | None,
    doc_summary: str,
    methods: list[str],
    doc_url: str,
) -> list[discord.ui.Item]:
    top = header(
        f"[`{name}`]({doc_url})",
        f"Python Built-in{DOT}{kind}",
    )
    sig_block = text(f"```py\n{signature_str}\n```") if signature_str else None
    methods_block = text(f"**Public Attributes & Methods**\n{pack(methods, 650)}") if methods else None
    return collect(
        top,
        discord.ui.Separator(),
        sig_block,
        text(doc_summary),
        discord.ui.Separator() if methods_block else None,
        methods_block,
    )


def complexity_items(info: ComplexityInfo) -> list[discord.ui.Item]:
    top = header(
        info.title,
        f"Python Complexity{DOT}{info.category}",
        info.summary,
    )
    metrics = facts(
        ("Best Time", f"`{info.best}`"),
        ("Average Time", f"`{info.average}`"),
        ("Worst Time", f"`{info.worst}`"),
        ("Space Complexity", f"`{info.space}`"),
    )
    notes_block = text("**Operation Breakdown & CPython Notes**\n" + "\n".join(f"\N{BULLET} {n}" for n in info.notes))
    example_block = text(f"**Idiomatic Python**\n```py\n{info.example}\n```")
    return collect(
        top,
        discord.ui.Separator(),
        metrics,
        discord.ui.Separator(),
        notes_block,
        example_block,
    )


FALLBACK_PYTHON_CYCLES: list[dict[str, Any]] = [
    {"cycle": "3.15", "version_num": 3.15, "releaseDate": "2026-10-09", "eol": "2031-10-31", "latest": "3.15.0", "support": "2028-10-09"},
    {"cycle": "3.14", "version_num": 3.14, "releaseDate": "2025-10-07", "eol": "2030-10-31", "latest": "3.14.8", "support": "2027-10-01"},
    {"cycle": "3.13", "version_num": 3.13, "releaseDate": "2024-10-07", "eol": "2029-10-31", "latest": "3.13.16", "support": "2026-10-01"},
    {"cycle": "3.12", "version_num": 3.12, "releaseDate": "2023-10-02", "eol": "2028-10-31", "latest": "3.12.15", "support": "2025-04-02"},
    {"cycle": "3.11", "version_num": 3.11, "releaseDate": "2022-10-24", "eol": "2027-10-31", "latest": "3.11.17", "support": "2024-04-01"},
    {"cycle": "3.10", "version_num": 3.10, "releaseDate": "2021-10-04", "eol": "2026-10-01", "latest": "3.10.22", "support": "2023-04-05"},
    {"cycle": "3.9", "version_num": 3.09, "releaseDate": "2020-10-05", "eol": "2025-10-31", "latest": "3.9.25", "support": "2022-05-17"},
    {"cycle": "3.8", "version_num": 3.08, "releaseDate": "2019-10-14", "eol": "2024-10-07", "latest": "3.8.20", "support": "2021-05-03"},
    {"cycle": "3.7", "version_num": 3.07, "releaseDate": "2018-06-27", "eol": "2023-06-27", "latest": "3.7.17", "support": "2020-06-27"},
    {"cycle": "3.6", "version_num": 3.06, "releaseDate": "2016-12-23", "eol": "2021-12-23", "latest": "3.6.15", "support": "2018-12-24"},
]


class Python(commands.Cog):
    """Python tutorials, PEPs, documentation, standard library, versions, exceptions, operators, built-ins, and complexity."""

    help_emoji = "\N{SNAKE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._python_tags: dict[str, frontmatter.Post] = {}

        self._peps_cache: dict[str, dict[str, Any]] | None = None
        self._sphinx_cache: list[SphinxEntry] | None = None
        self._cache_lock = asyncio.Lock()

    @property
    def python_tags(self) -> dict[str, frontmatter.Post]:
        if self._python_tags:
            return self._python_tags

        tags_path = pathlib.Path("assets/python_tags")
        for tag_file in tags_path.glob("*.md"):
            with tag_file.open(encoding="utf-8") as file:
                post = frontmatter.load(file)
                tag_name = tag_file.stem
                self._python_tags[tag_name] = post

        return self._python_tags

    async def fetch_bytes(self, url: str, *, missing: str = "Python documentation could not find that.") -> bytes:
        headers = {"User-Agent": USER_AGENT}
        try:
            async with self.bot.http_session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 404:
                    raise PythonError(missing)
                if response.status >= 400:
                    msg = f"Upstream server returned HTTP {response.status}."
                    raise PythonError(msg)
                return await response.read()
        except (TimeoutError, aiohttp.ClientError) as error:
            msg = "Could not reach Python documentation servers right now. Try again in a moment."
            raise PythonError(msg) from error

    async def fetch_json(self, url: str, *, missing: str = "Requested Python resource was not found.") -> Any:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            async with self.bot.http_session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 404:
                    raise PythonError(missing)
                if response.status >= 400:
                    msg = f"Upstream server returned HTTP {response.status}."
                    raise PythonError(msg)
                return await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as error:
            msg = "Could not fetch data from Python servers right now. Try again in a moment."
            raise PythonError(msg) from error

    async def optional_text(self, url: str) -> str | None:
        try:
            raw = await self.fetch_bytes(url)
            return raw.decode("utf-8", "replace")
        except PythonError:
            return None

    async def get_peps_index(self) -> dict[str, dict[str, Any]]:
        if self._peps_cache is not None:
            return self._peps_cache
        async with self._cache_lock:
            if self._peps_cache is None:
                data = await self.fetch_json(PEPS_API_URL, missing="Could not load the PEP index from peps.python.org.")
                if isinstance(data, dict):
                    self._peps_cache = data
                else:
                    msg = "Received an unexpected PEP index payload."
                    raise PythonError(msg)
            return self._peps_cache

    async def get_sphinx_index(self) -> list[SphinxEntry]:
        if self._sphinx_cache is not None:
            return self._sphinx_cache
        async with self._cache_lock:
            if self._sphinx_cache is None:
                raw = await self.fetch_bytes(f"{PYTHON_DOCS_URL}/objects.inv", missing="Could not load Python 3 Sphinx inventory.")
                entries = await asyncio.to_thread(parse_sphinx_inventory, raw, PYTHON_DOCS_URL)
                if not entries:
                    msg = "Could not parse the Python 3 documentation inventory."
                    raise PythonError(msg)
                self._sphinx_cache = entries
            return self._sphinx_cache

    async def deliver(self, ctx: commands.Context[Bot], producer: Awaitable[PythonView]) -> discord.Message:
        """Await the view, then send it. Any :class:`PythonError` becomes an error notice instead."""
        none = discord.AllowedMentions.none()
        async with ctx.typing():
            try:
                view = await producer
            except PythonError as error:
                return await ctx.reply(view=NoticeLayout.error(str(error), title="Python"), allowed_mentions=none)

        message = await ctx.reply(view=view, allowed_mentions=none)
        view.message = message
        return message

    @staticmethod
    def single(ctx: commands.Context[Bot], page: Page) -> PythonView:
        return PythonView(ctx.author, [page])

    @commands.group(
        name="python",
        aliases=["py", "python-tutorial", "pytut", "python3-tutorial"],
        invoke_without_command=True,
        extras={
            "examples": [
                "python decorators",
                "python-tutorial async-await",
                "python list",
                "python error KeyError",
                "python operator :=",
                "python builtin enumerate",
                "python complexity list",
            ]
        },
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str | None = commands.parameter(default=None, description="The tutorial to search for."),
    ) -> discord.Message | None:
        """Search for a Python tutorial or invoke a Python reference subcommand."""
        if not text:
            return await ctx.send_help(ctx.command)
        return await self.deliver(ctx, self.tutorial_view(ctx, text))

    @python.command(
        name="tutorial",
        aliases=["tut"],
        extras={"examples": ["python tutorial list-comprehension", "python tutorial decorators"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_tutorial(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str = commands.parameter(description="The tutorial to search for."),
    ) -> discord.Message:
        """Search for a Python tutorial."""
        return await self.deliver(ctx, self.tutorial_view(ctx, text))

    async def tutorial_view(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        if not self.python_tags:
            msg = "No Python tutorials are currently loaded."
            raise PythonError(msg)

        matched_tutorial = await asyncio.to_thread(extractOne, query.strip(), list(self.python_tags.keys()))
        if matched_tutorial is None or matched_tutorial[1] < MIN_TUTORIAL_SCORE:
            available = ", ".join(f"`{k}`" for k in list(self.python_tags.keys())[:10])
            msg = f"No such tutorial found for {code(query, 40)}. Try `python list` ({available})."
            raise PythonError(msg)

        key, score = matched_tutorial[0], float(matched_tutorial[1])
        data = self.python_tags[key]
        content = data.content if hasattr(data, "content") else str(data)
        url = getattr(data, "url", None) or f"{PYTHON_DOCS_URL}/tutorial/index.html"
        return self.single(
            ctx,
            Page(
                partial(tutorial_items, key, content, score),
                url=url,
                label="Python Tutorial",
                links=[("All Tutorials", f"{PYTHON_DOCS_URL}/tutorial/index.html")],
            ),
        )

    @python.command(
        name="list",
        aliases=["ls", "all"],
        extras={"examples": ["python list", "python-tutorial list"]},
    )
    async def python_list(self, ctx: commands.Context[Bot]) -> discord.Message:
        """List the available Python tutorials.

        This command displays the tutorial names that can be searched with the parent command.
        """
        return await self.deliver(ctx, self.tutorial_list_view(ctx))

    async def tutorial_list_view(self, ctx: commands.Context[Bot]) -> PythonView:
        names = sorted(self.python_tags.keys())
        if not names:
            msg = "No Python tutorials are currently available."
            raise PythonError(msg)

        pages = [
            Page(
                partial(tutorial_list_items, names, names[start : start + ITEMS_PER_PAGE], len(names)),
                url=f"{PYTHON_DOCS_URL}/tutorial/index.html",
                label="Official Python Tutorial",
            )
            for start in range(0, len(names), ITEMS_PER_PAGE)
        ]
        return PythonView(ctx.author, pages)

    @commands.command(
        name="pep",
        aliases=["peps"],
        extras={"examples": ["pep 8", "pep 20", "pep 484", "pep walrus"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pep_command(
        self,
        ctx: commands.Context[Bot],
        *,
        number: str = commands.parameter(description="The PEP number (e.g. `8`, `484`) or title keywords."),
    ) -> discord.Message:
        """Look up a Python Enhancement Proposal (PEP) by number or topic."""
        return await self.deliver(ctx, self.pep_view(ctx, number))

    @python.command(
        name="pep",
        aliases=["peps"],
        extras={"examples": ["python pep 8", "python pep 695"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_pep(
        self,
        ctx: commands.Context[Bot],
        *,
        number: str = commands.parameter(description="The PEP number (e.g. `8`, `484`) or title keywords."),
    ) -> discord.Message:
        """Look up a Python Enhancement Proposal (PEP) by number or topic."""
        return await self.deliver(ctx, self.pep_view(ctx, number))

    async def pep_view(self, ctx: commands.Context[Bot], target: str) -> PythonView:
        cleaned = target.strip()
        peps = await self.get_peps_index()

        pep_data: dict[str, Any] | None = None
        match = PEP_ARG_PATTERN.match(cleaned)
        if match:
            num = str(int(match.group(1)))
            pep_data = peps.get(num) or peps.get(f"{int(num):04d}")
            if pep_data is None:
                msg = f"PEP {num} does not exist."
                raise PythonError(msg)
        else:
            title_map = {f"PEP {entry.get('number')}: {entry.get('title', '')}": key for key, entry in peps.items()}
            best = await asyncio.to_thread(extractOne, cleaned, list(title_map.keys()))
            if best is None or best[1] < 55:
                msg = f"Could not find a PEP matching {code(cleaned, 40)}. Give a number like `pep 8` or keywords like `pep type hints`."
                raise PythonError(msg)
            pep_data = peps[title_map[best[0]]]

        number = int(pep_data.get("number", 0))
        pep_url = pep_data.get("url") or f"{PEPS_BASE_URL}/pep-{number:04d}/"
        html = await self.optional_text(pep_url)
        abstract = await asyncio.to_thread(extract_pep_abstract, html) if html else None

        status = pep_data.get("status") or ""
        colour = PEP_STATUS_COLOURS.get(status, PYTHON_COLOUR)
        links = [("PEP Index (PEP 0)", f"{PEPS_BASE_URL}/pep-0000/")]
        if pep_data.get("discussions_to") and valid_url(pep_data.get("discussions_to")):
            links.append(("Discussion", pep_data["discussions_to"]))

        return self.single(
            ctx,
            Page(
                partial(pep_items, pep_data, abstract),
                url=pep_url,
                label=f"Open PEP {number}",
                colour=colour,
                links=links,
            ),
        )

    @commands.command(
        name="pydoc",
        aliases=["pydocs"],
        extras={"examples": ["pydoc asyncio.gather", "pydoc pathlib.Path", "pydoc json.loads"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pydoc_command(
        self,
        ctx: commands.Context[Bot],
        *,
        module: str = commands.parameter(description="The Python module, class, function, or method to look up."),
    ) -> discord.Message:
        """Retrieve Python module, class, or function documentation."""
        return await self.deliver(ctx, self.pydoc_view(ctx, module))

    @python.command(
        name="doc",
        aliases=["docs", "pydoc"],
        extras={"examples": ["python doc asyncio.TaskGroup", "python doc itertools.batched"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_doc(
        self,
        ctx: commands.Context[Bot],
        *,
        module: str = commands.parameter(description="The Python module, class, function, or method to look up."),
    ) -> discord.Message:
        """Retrieve Python module, class, or function documentation."""
        return await self.deliver(ctx, self.pydoc_view(ctx, module))

    async def pydoc_view(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        cleaned = query.strip().strip("`")
        if not cleaned:
            msg = "Provide a module, class, or function name to look up."
            raise PythonError(msg)

        inventory = await self.get_sphinx_index()
        api_entries = [e for e in inventory if e.domain_role.startswith("py:")]

        q_lower = cleaned.casefold()
        ranked: list[tuple[int, SphinxEntry]] = []
        for entry in api_entries:
            name_lower = entry.name.casefold()
            tail_lower = name_lower.rsplit(".", 1)[-1]
            if name_lower == q_lower:
                ranked.append((0 if entry.domain_role == "py:module" else 1, entry))
            elif tail_lower == q_lower:
                ranked.append((2, entry))
            elif name_lower.startswith(q_lower):
                ranked.append((3, entry))
            elif q_lower in name_lower:
                ranked.append((4, entry))

        ranked.sort(key=lambda pair: (pair[0], len(pair[1].name)))
        matches = [entry for _, entry in ranked[:12]]

        if not matches:
            name_map = {e.name: e for e in api_entries}
            fuzzy = await asyncio.to_thread(extractOne, cleaned, list(name_map.keys()))
            if fuzzy is None or fuzzy[1] < 60:
                msg = f"No Python documentation entries matched {code(cleaned, 40)}."
                raise PythonError(msg)
            matches = [name_map[fuzzy[0]]]

        primary = matches[0]
        page_url, _, anchor = primary.url.partition("#")
        html = await self.optional_text(page_url)
        if html:
            signature, description, members = await asyncio.to_thread(extract_sphinx_doc_section, html, page_url, anchor or None)
        else:
            signature, description, members = None, "*Documentation preview unavailable.*", []

        return self.single(
            ctx,
            Page(
                partial(pydoc_items, primary, signature, description, members, matches[1:6]),
                url=primary.url,
                label="Open on docs.python.org",
                links=[("Library Reference", f"{PYTHON_DOCS_URL}/library/index.html")],
            ),
        )

    @commands.command(
        name="stdlib",
        aliases=["pylib"],
        extras={"examples": ["stdlib pathlib", "stdlib itertools", "stdlib collections"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stdlib_command(
        self,
        ctx: commands.Context[Bot],
        module: str = commands.parameter(description="The standard library module name (e.g. `pathlib`, `asyncio`)."),
    ) -> discord.Message:
        """Explain a standard-library module and link its documentation and source."""
        return await self.deliver(ctx, self.stdlib_view(ctx, module))

    @python.command(
        name="stdlib",
        aliases=["lib", "module"],
        extras={"examples": ["python stdlib functools", "python stdlib contextlib"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_stdlib(
        self,
        ctx: commands.Context[Bot],
        module: str = commands.parameter(description="The standard library module name (e.g. `pathlib`, `asyncio`)."),
    ) -> discord.Message:
        """Explain a standard-library module and link its documentation and source."""
        return await self.deliver(ctx, self.stdlib_view(ctx, module))

    async def stdlib_view(self, ctx: commands.Context[Bot], module: str) -> PythonView:
        cleaned = module.strip().strip("`").split(".", 1)[0]
        stdlib_names: frozenset[str] = getattr(sys, "stdlib_module_names", frozenset(STDLIB_CURATED.keys()))

        if cleaned not in stdlib_names and cleaned not in STDLIB_CURATED:
            match = await asyncio.to_thread(extractOne, cleaned, sorted(stdlib_names))
            if match is None or match[1] < 65:
                msg = f"{code(cleaned, 40)} is not a standard-library module in Python {platform.python_version()}."
                raise PythonError(msg)
            cleaned = match[0]

        curated = STDLIB_CURATED.get(cleaned)
        doc_url = f"{PYTHON_DOCS_URL}/library/{quote(cleaned, safe='')}.html"

        ast_doc, exports, is_builtin_c = await asyncio.to_thread(self._inspect_stdlib_module, cleaned)
        html = await self.optional_text(doc_url)
        scraped_synopsis = None
        if html:
            _, scraped_body, scraped_members = await asyncio.to_thread(extract_sphinx_doc_section, html, doc_url, f"module-{cleaned}")
            if scraped_body and not scraped_body.startswith("*Open"):
                scraped_synopsis = scraped_body
            if not exports and scraped_members:
                exports = [m.removeprefix(f"{cleaned}.") for m in scraped_members]

        synopsis = curated.summary if curated else (scraped_synopsis or ast_doc or f"Standard library `{cleaned}` module.")
        source_path = curated.source_path if curated else None
        source_url = f"{CPYTHON_BLOB_URL}/{source_path}" if source_path else f"{CPYTHON_BLOB_URL}/Lib/{cleaned}.py"

        links = [("Standard Library Index", f"{PYTHON_DOCS_URL}/library/index.html")]
        if not is_builtin_c or (curated and curated.source_path):
            links.insert(0, ("CPython Source", source_url))

        return self.single(
            ctx,
            Page(
                partial(stdlib_items, cleaned, doc_url, curated, synopsis, exports, source_url, is_builtin_c),
                url=doc_url,
                label=f"Open {cleaned} Docs",
                links=links,
            ),
        )

    @staticmethod
    def _inspect_stdlib_module(name: str) -> tuple[str | None, list[str], bool]:
        """Safely extract docstring and public symbol names from a stdlib module."""
        is_builtin_c = name in sys.builtin_module_names
        if name in sys.modules:
            mod = sys.modules[name]
            doc = inspect.getdoc(mod)
            first_para = doc.split("\n\n", 1)[0].strip() if doc else None
            all_names = getattr(mod, "__all__", None)
            if isinstance(all_names, (list, tuple)):
                exports = [str(x) for x in all_names if not str(x).startswith("_")][:25]
            else:
                exports = [k for k in dir(mod) if not k.startswith("_")][:25]
            return first_para, exports, is_builtin_c

        try:
            spec = importlib.util.find_spec(name)
        except ImportError, ValueError:
            spec = None
        if spec is None or not spec.origin or spec.origin in {"built-in", "frozen"} or not spec.origin.endswith(".py"):
            return None, [], True

        try:
            source = Path(spec.origin).read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
            doc = ast.get_docstring(tree)
            first_para = doc.split("\n\n", 1)[0].strip() if doc else None
            exports = [
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_")
            ][:25]
            return first_para, exports, False
        except OSError, SyntaxError:
            return None, [], is_builtin_c

    @commands.command(
        name="pyversions",
        aliases=["pyver", "pythonversions"],
        extras={"examples": ["pyversions"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def pyversions_command(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show supported Python versions and release status."""
        return await self.deliver(ctx, self.fetch_python_versions(ctx))

    @python.command(
        name="versions",
        aliases=["version", "releases", "eol", "status"],
        extras={"examples": ["python versions"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def python_versions(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show supported Python versions and release status."""
        return await self.deliver(ctx, self.fetch_python_versions(ctx))

    async def fetch_python_versions(self, ctx: commands.Context[Bot]) -> PythonView:
        try:
            data = await self.fetch_json(ENDOFLIFE_PYTHON_URL)
            cycles = data if isinstance(data, list) and data else FALLBACK_PYTHON_CYCLES
        except PythonError:
            cycles = FALLBACK_PYTHON_CYCLES

        now_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        active = [c for c in cycles if not (isinstance(c.get("eol"), str) and c["eol"] <= now_str)]
        eol_list = [c for c in cycles if isinstance(c.get("eol"), str) and c["eol"] <= now_str][:8]

        pages: list[Page] = []
        if active:
            pages.append(
                Page(
                    partial(versions_items, active[:8], active_view=True),
                    url="https://devguide.python.org/versions/",
                    label="Python Developer's Guide",
                    colour=ACTIVE_COLOUR,
                    links=[("Downloads", "https://www.python.org/downloads/"), ("endoflife.date", "https://endoflife.date/python")],
                )
            )
        if eol_list:
            pages.append(
                Page(
                    partial(versions_items, eol_list, active_view=False),
                    url="https://devguide.python.org/versions/",
                    label="Python Developer's Guide",
                    colour=EOL_COLOUR,
                    links=[("endoflife.date", "https://endoflife.date/python")],
                )
            )
        return PythonView(ctx.author, pages)

    @python.command(
        name="error",
        aliases=["exception", "exc", "err", "errors"],
        extras={"examples": ["python error KeyError", "python error TypeError", "python error UnboundLocalError"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_error(
        self,
        ctx: commands.Context[Bot],
        *,
        exception: str = commands.parameter(description="The exception name (e.g. `KeyError`, `TypeError`, `SyntaxError`)."),
    ) -> discord.Message:
        """Explain common Python exceptions."""
        return await self.deliver(ctx, self.error_view(ctx, exception))

    async def error_view(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        cleaned = query.strip().strip("`")
        lookup = {k.casefold(): k for k in EXCEPTIONS_DB}

        canonical = lookup.get(cleaned.casefold()) or lookup.get(cleaned.casefold() + "error")
        if canonical is None:
            match = await asyncio.to_thread(extractOne, cleaned, list(EXCEPTIONS_DB.keys()))
            if match and match[1] >= 65:
                canonical = match[0]

        if canonical is not None:
            info = EXCEPTIONS_DB[canonical]
            exc_cls = getattr(builtins, canonical, None)
            if isinstance(exc_cls, type) and issubclass(exc_cls, BaseException):
                mro_chain = " \N{RIGHTWARDS ARROW} ".join(f"`{cls.__name__}`" for cls in reversed(exc_cls.__mro__[:-1]))
            else:
                mro_chain = f"`BaseException` \N{RIGHTWARDS ARROW} `Exception` \N{RIGHTWARDS ARROW} `{info.name}`"
            doc_url = f"{PYTHON_DOCS_URL}/library/exceptions.html#{info.anchor or info.name}"
            return self.single(
                ctx,
                Page(
                    partial(exception_items, info, mro_chain, doc_url),
                    url=doc_url,
                    label="Built-in Exceptions Docs",
                    colour=EOL_COLOUR,
                ),
            )

        builtin_excs = {
            name.casefold(): (name, obj) for name, obj in vars(builtins).items() if isinstance(obj, type) and issubclass(obj, BaseException)
        }
        found = builtin_excs.get(cleaned.casefold())
        if found is None:
            available = ", ".join(f"`{k}`" for k in list(EXCEPTIONS_DB.keys())[:10])
            msg = f"Unknown exception {code(cleaned, 40)}. Try one of: {available}."
            raise PythonError(msg)

        exc_name, exc_cls = found
        mro_chain = " \N{RIGHTWARDS ARROW} ".join(f"`{cls.__name__}`" for cls in reversed(exc_cls.__mro__[:-1]))
        doc = inspect.getdoc(exc_cls) or "Built-in Python exception."
        dynamic_info = ExceptionInfo(
            name=exc_name,
            category="Built-in Exception",
            summary=doc,
            causes=("Raised when an operation encounters this specific runtime or system condition.",),
            fix="Catch this exception specifically with `try ... except` or prevent the triggering precondition.",
            example=f"try:\n    ...\nexcept {exc_name} as exc:\n    print(f'Handled: {{exc}}')",
        )
        doc_url = f"{PYTHON_DOCS_URL}/library/exceptions.html#{exc_name}"
        return self.single(
            ctx,
            Page(
                partial(exception_items, dynamic_info, mro_chain, doc_url),
                url=doc_url,
                label="Built-in Exceptions Docs",
                colour=EOL_COLOUR,
            ),
        )

    @python.command(
        name="operator",
        aliases=["op", "operators", "ops"],
        extras={"examples": ["python operator :=", "python operator //", "python operator @", "python operator is"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_operator(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The operator symbol (e.g. `:=`, `//`, `**`, `@`) or name (`walrus`, `matmul`)."),
    ) -> discord.Message:
        """Explain a Python operator."""
        return await self.deliver(ctx, self.operator_view(ctx, name))

    async def operator_view(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        cleaned = query.strip().strip("`").casefold()
        selected: OperatorInfo | None = None
        for entry in OPERATORS_DB:
            if cleaned == entry.symbol.casefold() or cleaned == entry.name.casefold() or cleaned in entry.aliases:
                selected = entry
                break

        if selected is None:
            alias_map: dict[str, OperatorInfo] = {}
            for entry in OPERATORS_DB:
                alias_map[entry.name] = entry
                for alias in entry.aliases:
                    alias_map[alias] = entry
            match = await asyncio.to_thread(extractOne, cleaned, list(alias_map.keys()))
            if match is None or match[1] < 60:
                symbols = " ".join(f"`{op.symbol}`" for op in OPERATORS_DB)
                msg = f"Unknown operator {code(query, 30)}. Supported operators: {symbols}"
                raise PythonError(msg)
            selected = alias_map[match[0]]

        doc_url = f"{PYTHON_DOCS_URL}/reference/{selected.anchor}"
        return self.single(
            ctx,
            Page(
                partial(operator_items, selected, doc_url),
                url=doc_url,
                label="Language Reference",
                links=[("operator Module", f"{PYTHON_DOCS_URL}/library/operator.html")],
            ),
        )

    @python.command(
        name="builtin",
        aliases=["builtins", "bi", "func"],
        extras={"examples": ["python builtin enumerate", "python builtin zip", "python builtin sorted", "python builtin dict"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_builtin(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The built-in function, type, or constant (e.g. `enumerate`, `zip`, `len`)."),
    ) -> discord.Message:
        """Look up built-in functions and types."""
        return await self.deliver(ctx, self.get_builtin_info(ctx, name))

    async def get_builtin_info(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        cleaned = query.strip().strip("`").rstrip("()")
        public_builtins = {k: v for k, v in vars(builtins).items() if not k.startswith("_")}
        lower_map = {k.casefold(): k for k in public_builtins}

        canonical = lower_map.get(cleaned.casefold())
        if canonical is None:
            if keyword.iskeyword(cleaned):
                msg = f"`{cleaned}` is a Python reserved keyword, not a built-in object. Use `syntax python {cleaned}` instead."
                raise PythonError(msg)
            match = await asyncio.to_thread(extractOne, cleaned, list(public_builtins.keys()))
            if match is None or match[1] < 65:
                msg = f"{code(cleaned, 40)} is not a Python built-in function or type."
                raise PythonError(msg)
            canonical = match[0]

        obj = public_builtins[canonical]
        if isinstance(obj, type) and issubclass(obj, BaseException):
            return await self.error_view(ctx, canonical)

        kind = "Built-in Type / Class" if isinstance(obj, type) else ("Built-in Function" if callable(obj) else "Built-in Constant")
        try:
            sig = f"{canonical}{inspect.signature(obj)}"
        except ValueError, TypeError:
            sig = None

        raw_doc = inspect.getdoc(obj) or f"Python built-in `{canonical}`."
        doc_lines = [line for line in raw_doc.splitlines() if line.strip()]
        if sig is None and doc_lines and ("(" in doc_lines[0] and ")" in doc_lines[0]):
            sig = doc_lines[0]
            raw_doc = "\n".join(doc_lines[1:]).strip() or raw_doc

        doc_summary = truncate(discord.utils.escape_mentions(raw_doc), 1100)
        methods = [m for m in dir(obj) if not m.startswith("_")] if isinstance(obj, type) else []

        is_stdtype = canonical in {
            "int",
            "float",
            "complex",
            "bool",
            "str",
            "bytes",
            "bytearray",
            "memoryview",
            "list",
            "tuple",
            "range",
            "dict",
            "set",
            "frozenset",
        }
        doc_url = f"{PYTHON_DOCS_URL}/library/stdtypes.html#{canonical}" if is_stdtype else f"{PYTHON_DOCS_URL}/library/functions.html#{canonical}"

        return self.single(
            ctx,
            Page(
                partial(builtin_items, canonical, kind, sig, doc_summary, methods, doc_url),
                url=doc_url,
                label="Built-in Functions Docs",
                links=[("Built-in Types", f"{PYTHON_DOCS_URL}/library/stdtypes.html")],
            ),
        )

    @python.command(
        name="complexity",
        aliases=["bigo", "timecomplexity", "alg", "algorithm"],
        extras={"examples": ["python complexity list", "python complexity dict", "python complexity timsort", "python complexity dijkstra"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_complexity(
        self,
        ctx: commands.Context[Bot],
        *,
        algorithm: str = commands.parameter(
            default="big-o",
            description="The algorithm or data structure (e.g. `list`, `dict`, `set`, `deque`, `heapq`, `timsort`, `bfs`, `dijkstra`).",
        ),
    ) -> discord.Message:
        """Explain common algorithmic and data-structure complexity."""
        return await self.deliver(ctx, self.fetch_complexity_info(ctx, algorithm))

    async def fetch_complexity_info(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        cleaned = query.strip().strip("`").casefold()
        selected: ComplexityInfo | None = None
        for entry in COMPLEXITY_DB:
            if cleaned == entry.key or cleaned == entry.title.casefold() or cleaned in entry.aliases:
                selected = entry
                break

        if selected is None:
            alias_map: dict[str, ComplexityInfo] = {}
            for entry in COMPLEXITY_DB:
                alias_map[entry.key] = entry
                alias_map[entry.title] = entry
                for alias in entry.aliases:
                    alias_map[alias] = entry
            match = await asyncio.to_thread(extractOne, cleaned, list(alias_map.keys()))
            if match is None or match[1] < 55:
                topics = ", ".join(f"`{c.key}`" for c in COMPLEXITY_DB)
                msg = f"No complexity entry matched {code(query, 30)}. Available topics: {topics}."
                raise PythonError(msg)
            selected = alias_map[match[0]]

        return self.single(
            ctx,
            Page(
                partial(complexity_items, selected),
                url="https://wiki.python.org/moin/TimeComplexity",
                label="Python TimeComplexity Wiki",
                colour=PYTHON_GOLD,
                links=[("Collections Docs", f"{PYTHON_DOCS_URL}/library/collections.html")],
            ),
        )
