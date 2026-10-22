from __future__ import annotations

import ast
import asyncio
import builtins
import contextlib
import importlib.util
import inspect
import keyword
import pathlib
import platform
import re
import sys
import sysconfig
import time
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import aiohttp
import discord
import frontmatter
from bs4 import BeautifulSoup, Tag
from discord.ext import commands
from rapidfuzz.process import extractOne

from core.utils import BaseLayoutView, NoticeLayout, truncate

from ..language_utils import code, collect, dated, facts, header, pack, safe, text, valid_url, when
from .knowledge import (
    COMPLEXITY_DB,
    DUNDERS_DB,
    EXCEPTIONS_DB,
    GOTCHAS_DB,
    IDIOMS_DB,
    KEYWORDS_DB,
    OPERATORS_DB,
    STDLIB_CURATED,
    TYPING_DB,
    ExceptionInfo,
    KeywordInfo,
    lookup_dunder,
    normalise_dunder,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from core import Bot

    from .knowledge import ComplexityInfo, DunderInfo, GotchaInfo, IdiomInfo, OperatorInfo, StdlibMeta, TypingInfo

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


PYPI_JSON_URL = "https://pypi.org/pypi"
NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_DETAIL_URL = "https://nvd.nist.gov/vuln/detail"
NVD_TIMEOUT = aiohttp.ClientTimeout(total=25)
PYTHON_FTP_URL = "https://www.python.org/ftp/python"
PYTHON_RELEASES_URL = "https://www.python.org/downloads/release"
CPYTHON_REPO_URL = "https://github.com/python/cpython"
CACHE_TTL = 3600
CVES_PER_PAGE = 5
MAX_CVES = 40

PYPI_NAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$")
PYPI_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+!-]{0,39}$")
PYPI_CLASSIFIER_PATTERN = re.compile(r"^Programming Language :: Python :: (\d+\.\d+)$")
VERSION_ARG_PATTERN = re.compile(r"^(\d)\.(\d{1,2})(?:\.(\d{1,2}))?$")
FULL_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
CVE_ID_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
DOTTED_NAME_PATTERN = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
SCHEDULE_TITLE_PATTERN = re.compile(r"^Python (\d+)\.(\d+) Release Schedule$")
SCHEDULE_LINE_PATTERN = re.compile(r"^(?P<label>[^:]{3,80}):\s*(?:[A-Za-z]+day,\s*)?(?P<date>\d{4}-\d{2}-\d{2})")
VERSION_ADDED_PATTERN = re.compile(r"(?:Added|New) in version ([\d.]+)")

# `inspect_source` imports the module it is asked about, so anything with import-time side effects is refused.
SOURCE_BLOCKLIST = frozenset(
    {"__main__", "__hello__", "__phello__", "antigravity", "this", "idlelib", "turtle", "turtledemo", "tkinter", "test", "pydoc_data"}
)

NOTE_CLASSES = ("versionadded", "versionchanged", "deprecated", "versionremoved")
NOTE_LABELS = {
    "versionadded": "\N{HEAVY PLUS SIGN} Added",
    "versionchanged": "\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS} Changed",
    "deprecated": "\N{WARNING SIGN} Deprecated",
    "versionremoved": "\N{CROSS MARK} Removed",
}
SEVERITY_BADGES = {
    "CRITICAL": "\N{LARGE RED CIRCLE}",
    "HIGH": "\N{LARGE ORANGE CIRCLE}",
    "MEDIUM": "\N{LARGE YELLOW CIRCLE}",
    "LOW": "\N{LARGE GREEN CIRCLE}",
}

ZEN_LINES = [
    "Beautiful is better than ugly.",
    "Explicit is better than implicit.",
    "Simple is better than complex.",
    "Complex is better than complicated.",
    "Flat is better than nested.",
    "Sparse is better than dense.",
    "Readability counts.",
    "Special cases aren't special enough to break the rules.",
    "Although practicality beats purity.",
    "Errors should never pass silently.",
    "Unless explicitly silenced.",
    "In the face of ambiguity, refuse the temptation to guess.",
    "There should be one-- and preferably only one --obvious way to do it.",
    "Although that way may not be obvious at first unless you're Dutch.",
    "Now is better than never.",
    "Although never is often better than *right* now.",
    "If the implementation is hard to explain, it's a bad idea.",
    "If the implementation is easy to explain, it may be a good idea.",
    "Namespaces are one honking great idea -- let's do more of those!",
]


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


@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    term: str
    definition: str
    anchor: str
    aliases: tuple[str, ...] = ()

    @property
    def url(self) -> str:
        return f"{PYTHON_DOCS_URL}/glossary.html#{self.anchor}"


@dataclass(frozen=True, slots=True)
class WhatsNew:
    title: str
    highlights: tuple[str, ...]
    features: tuple[str, ...]
    sections: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CveRecord:
    cve_id: str
    summary: str
    published: str | None
    score: float | None
    severity: str | None


@dataclass(frozen=True, slots=True)
class SourceInfo:
    name: str
    kind: str
    signature: str | None
    doc: str
    relative_path: str
    start: int
    end: int
    preview: str
    url: str


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


def generate_python_release_info(cycles: list[dict[str, Any]], *, active_view: bool) -> list[discord.ui.Item]:
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


# fmt: off
FALLBACK_PYTHON_CYCLES: list[dict[str, Any]] = [
    {"cycle": "3.15", "version_num": 3.15, "releaseDate": "2026-10-09", "eol": "2031-10-31", "latest": "3.15.0", "support": "2028-10-09"},
    {"cycle": "3.14", "version_num": 3.14, "releaseDate": "2025-10-07", "eol": "2030-10-31", "latest": "3.14.8", "support": "2027-10-01"},
    {"cycle": "3.13", "version_num": 3.13, "releaseDate": "2024-10-07", "eol": "2029-10-31", "latest": "3.13.16", "support": "2026-10-01"},
    {"cycle": "3.12", "version_num": 3.12, "releaseDate": "2023-10-02", "eol": "2028-10-31", "latest": "3.12.15", "support": "2025-04-02"},
    {"cycle": "3.11", "version_num": 3.11, "releaseDate": "2022-10-24", "eol": "2027-10-31", "latest": "3.11.17", "support": "2024-04-01"},
    {"cycle": "3.10", "version_num": 3.10, "releaseDate": "2021-10-04", "eol": "2026-10-01", "latest": "3.10.22", "support": "2023-04-05"},
    {"cycle": "3.9",  "version_num": 3.09, "releaseDate": "2020-10-05", "eol": "2025-10-31", "latest": "3.9.25",  "support": "2022-05-17"},
    {"cycle": "3.8",  "version_num": 3.08, "releaseDate": "2019-10-14", "eol": "2024-10-07", "latest": "3.8.20",  "support": "2021-05-03"},
    {"cycle": "3.7",  "version_num": 3.07, "releaseDate": "2018-06-27", "eol": "2023-06-27", "latest": "3.7.17",  "support": "2020-06-27"},
    {"cycle": "3.6",  "version_num": 3.06, "releaseDate": "2016-12-23", "eol": "2021-12-23", "latest": "3.6.15",  "support": "2018-12-24"},
    {"cycle": "3.5",  "version_num": 3.05, "releaseDate": "2015-09-13", "eol": "2020-09-30", "latest": "3.5.10",  "support": None},
    {"cycle": "3.4",  "version_num": 3.04, "releaseDate": "2014-03-16", "eol": "2019-03-18", "latest": "3.4.10",  "support": None},
    {"cycle": "3.3",  "version_num": 3.03, "releaseDate": "2012-09-29", "eol": "2017-09-29", "latest": "3.3.7",   "support": None},
    {"cycle": "3.2",  "version_num": 3.02, "releaseDate": "2011-02-20", "eol": "2016-02-20", "latest": "3.2.6",   "support": None},
    {"cycle": "3.1",  "version_num": 3.01, "releaseDate": "2009-06-27", "eol": "2012-04-09", "latest": "3.1.5",   "support": None},
    {"cycle": "3.0",  "version_num": 3.00, "releaseDate": "2008-12-03", "eol": "2009-06-27", "latest": "3.0.1",   "support": None},
    {"cycle": "2.7",  "version_num": 2.07, "releaseDate": "2010-07-03", "eol": "2020-01-01", "latest": "2.7.18",  "support": None},
    {"cycle": "2.6",  "version_num": 2.06, "releaseDate": "2008-10-01", "eol": "2013-10-29", "latest": "2.6.9",   "support": None},
]
# fmt: on


def clean_text(node: Tag | None) -> str:
    """Whitespace-normalised text of a node, without Sphinx pilcrow anchors."""
    if node is None:
        return ""
    return " ".join(node.get_text().split()).replace("\N{PILCROW SIGN}", "").strip()


def today_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def normalise_key(value: str) -> str:
    return re.sub(r"[\s_]+", "-", value.strip().replace("`", "").casefold())


def curated_names(items: Sequence[Any]) -> dict[str, Any]:
    """Map every normalised key, title and alias of curated entries to the entry."""
    names: dict[str, Any] = {}
    for item in items:
        for name in (item.key, item.title, *item.aliases):
            names.setdefault(normalise_key(name), item)
    return names


def cycle_phase(cycle: dict[str, Any]) -> str:
    today = today_iso()
    released, eol, support = cycle.get("releaseDate"), cycle.get("eol"), cycle.get("support")
    if isinstance(released, str) and released > today:
        return "prerelease"
    if isinstance(eol, str) and eol <= today:
        return "end-of-life"
    if (isinstance(support, str) and support > today) or support is True:
        return "bugfix"
    return "security"


def latest_released_cycle(cycles: Sequence[dict[str, Any]]) -> dict[str, Any]:
    today = today_iso()
    released = [c for c in cycles if str(c.get("cycle", "")).startswith("3.") and isinstance(c.get("releaseDate"), str) and c["releaseDate"] <= today]
    return max(released, key=lambda c: c["releaseDate"]) if released else cycles[0]


def rank_sphinx_entries(entries: Sequence[SphinxEntry], query: str, limit: int = 12) -> list[SphinxEntry]:
    """Same ranking as ``pydoc``: exact name, exact tail, prefix, substring."""
    q_lower = query.casefold()
    ranked: list[tuple[int, SphinxEntry]] = []
    for entry in entries:
        if not entry.domain_role.startswith("py:"):
            continue
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
    return [entry for _, entry in ranked[:limit]]


def parse_glossary(html: str) -> dict[str, GlossaryTerm]:
    """Parse ``glossary.html`` into ``{casefolded term: GlossaryTerm}``."""
    soup = BeautifulSoup(html, "html.parser")
    terms: dict[str, GlossaryTerm] = {}
    for dl in soup.select("dl.glossary"):
        pending: list[Tag] = []
        for child in dl.find_all(["dt", "dd"], recursive=False):
            if child.name == "dt":
                pending.append(child)
                continue
            paragraphs = [clean_text(p) for p in child.find_all("p", recursive=False)] or [clean_text(child)]
            definition = truncate(discord.utils.escape_mentions("\n\n".join(p for p in paragraphs[:3] if p)), 1100)
            names = [clean_text(dt) for dt in pending]
            for dt, name in zip(pending, names, strict=True):
                anchor = dt.get("id")
                if name and isinstance(anchor, str):
                    terms[name.casefold()] = GlossaryTerm(name, definition, anchor, tuple(n for n in names if n and n != name))
            pending = []
    return terms


def extract_version_notes(html: str, anchor: str | None) -> list[tuple[str, str]]:
    """Collect ``versionadded`` / ``versionchanged`` / ``deprecated`` / ``versionremoved`` notes that belong to one documented object."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.body, [role=main]") or soup
    target = root.find(id=anchor) if anchor else None
    if not isinstance(target, Tag):
        return []

    selector = ", ".join(f"div.{name}" for name in NOTE_CLASSES)
    if target.name == "dt":
        owner = target.find_parent("dl")
        dd = owner.find("dd", recursive=False) if owner else None
        # nested members (methods of a class) have their own <dl>; only keep notes owned by this one
        candidates = [n for n in (dd.select(selector) if dd else []) if n.find_parent("dl") is owner]
    else:
        owner = target if target.name == "section" else target.find_parent("section")
        candidates = [n for n in (owner.select(selector) if owner else []) if n.find_parent("dl") is None and n.find_parent("section") is owner]

    notes: list[tuple[str, str]] = []
    for node in candidates:
        kind = next((c for c in NOTE_CLASSES if c in (node.get("class") or [])), None)
        body = clean_text(node)
        if kind and body and (kind, body) not in notes:
            notes.append((kind, truncate(discord.utils.escape_mentions(body), 320)))
    return notes[:8]


def extract_whatsnew(html: str) -> WhatsNew:
    soup = BeautifulSoup(html, "html.parser")
    title = clean_text(soup.select_one("h1")) or "What's New"

    highlights: list[str] = []
    summary = soup.select_one("section[id^=summary]")
    bullets = summary.find("ul") if summary else None
    for li in (bullets.find_all("li", recursive=False) if bullets else [])[:10]:
        head = li.find("p", recursive=False)
        line = clean_text(head if isinstance(head, Tag) else li)
        if line.endswith(":"):
            nested = [truncate(clean_text(sub), 70) for sub in li.select("ul > li")[:3]]
            line = f"{line} {'; '.join(nested)}" if nested else line
        if line:
            highlights.append(truncate(discord.utils.escape_mentions(line), 240))

    features_section = soup.select_one("section#new-features, section[id^=new-features]")
    features = [clean_text(h) for h in (features_section.select("h3") if features_section else [])][:14]

    sections: list[tuple[str, str]] = []
    for h2 in soup.select("section > h2")[:16]:
        section = h2.find_parent("section")
        anchor = section.get("id") if section else None
        name = clean_text(h2)
        if name and isinstance(anchor, str):
            sections.append((name, anchor))
    return WhatsNew(title, tuple(highlights), tuple(f for f in features if f), tuple(sections))


def parse_release_schedule(html: str, series: str) -> list[tuple[str, str]]:
    """Return ``[(label, 'YYYY-MM-DD')]`` for every milestone of a release-schedule PEP, oldest first."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[tuple[str, str]] = set()
    milestones: list[tuple[str, str]] = []
    for li in soup.select("li"):
        if li.find("li"):
            continue
        match = SCHEDULE_LINE_PATTERN.match(" ".join(li.get_text(" ").split()))
        if not match:
            continue
        label = match["label"].strip()
        key = (label, match["date"])
        if label.startswith(series) and key not in seen:
            seen.add(key)
            milestones.append(key)
    milestones.sort(key=lambda pair: pair[1])
    return milestones


def cvss_of(metrics: dict[str, Any]) -> tuple[float | None, str | None]:
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key) or []
        if not entries:
            continue
        entry = next((e for e in entries if e.get("type") == "Primary"), entries[0])
        data = entry.get("cvssData") or {}
        severity = data.get("baseSeverity") or entry.get("baseSeverity")
        score = data.get("baseScore")
        return (float(score) if isinstance(score, (int, float)) else None), (str(severity).upper() if severity else None)
    return None, None


def parse_nvd(data: dict[str, Any]) -> list[CveRecord]:
    records: list[CveRecord] = []
    for wrapper in data.get("vulnerabilities") or []:
        cve = wrapper.get("cve") or {}
        cve_id = cve.get("id")
        if not isinstance(cve_id, str):
            continue
        summary = next((d.get("value", "") for d in cve.get("descriptions") or [] if d.get("lang") == "en"), "")
        score, severity = cvss_of(cve.get("metrics") or {})
        records.append(CveRecord(cve_id, summary, cve.get("published"), score, severity))
    records.sort(key=lambda r: r.published or "", reverse=True)
    return records[:MAX_CVES]


def cpython_ref() -> str:
    """Git ref matching the running interpreter, so line numbers line up with the link."""
    v = sys.version_info
    return f"v{v.major}.{v.minor}.{v.micro}" if v.releaselevel == "final" else f"{v.major}.{v.minor}"


def inspect_source(target: str) -> SourceInfo:  # noqa: PLR0912, PLR0915
    """Resolve a dotted name inside the standard library and map it to a CPython source link."""
    parts = target.split(".")
    if parts[0] not in getattr(sys, "stdlib_module_names", frozenset()) or parts[0] in SOURCE_BLOCKLIST:
        msg = f"{code(target, 50)} is not an inspectable standard-library object."
        raise PythonError(msg)

    module: Any = None
    depth = len(parts)
    while depth > 0 and module is None:
        try:
            module = importlib.import_module(".".join(parts[:depth]))
        except Exception:
            depth -= 1
    if module is None:
        msg = f"Could not import {code(parts[0], 40)}."
        raise PythonError(msg)

    obj: Any = module
    for attr in parts[depth:]:
        try:
            obj = getattr(obj, attr)
        except Exception as error:
            msg = f"{code('.'.join(parts[:depth]), 50)} has no attribute {code(attr, 40)}."
            raise PythonError(msg) from error

    with contextlib.suppress(ValueError):
        obj = inspect.unwrap(obj)

    try:
        source_file = inspect.getsourcefile(obj) or inspect.getfile(obj)
        lines, start = inspect.getsourcelines(obj)
    except (TypeError, OSError) as error:
        msg = f"{code(target, 50)} is implemented in C or has no Python source. Try `python doc {target}` instead."
        raise PythonError(msg) from error

    stdlib_dir = Path(sysconfig.get_paths()["stdlib"]).resolve()
    try:
        relative = Path(source_file).resolve().relative_to(stdlib_dir)
    except ValueError as error:
        msg = f"{code(target, 50)} does not live in the standard library."
        raise PythonError(msg) from error
    if {"site-packages", "dist-packages"} & set(relative.parts):
        msg = f"{code(target, 50)} does not live in the standard library."
        raise PythonError(msg)

    start = max(start, 1)
    end = start + len(lines) - 1
    if inspect.ismodule(obj):
        kind = "module"
    elif inspect.isclass(obj):
        kind = "class"
    elif inspect.ismethod(obj):
        kind = "method"
    elif inspect.isfunction(obj):
        kind = "function"
    else:
        kind = type(obj).__name__

    try:
        signature = f"{getattr(obj, '__name__', parts[-1])}{inspect.signature(obj)}"  # pyright: ignore[reportArgumentType]
    except ValueError, TypeError:
        signature = None

    doc = (inspect.getdoc(obj) or "").split("\n\n", 1)[0].strip()
    preview = truncate("".join(lines[:14]).rstrip().replace("```", "'''"), 850)
    url = f"{CPYTHON_REPO_URL}/blob/{cpython_ref()}/Lib/{relative.as_posix()}#L{start}-L{end}"
    return SourceInfo(target, kind, signature, doc, relative.as_posix(), start, end, preview, url)


def glossary_items(entry: GlossaryTerm) -> list[discord.ui.Item]:
    aliases = ", ".join(f"`{a}`" for a in entry.aliases[:5])
    return collect(
        header(f"[{safe(entry.term, 80)}]({entry.url})", "Python Glossary"),
        discord.ui.Separator(),
        text(entry.definition),
        facts(("Also known as", aliases or None)),
    )


def keyword_items(name: str, info: KeywordInfo, *, soft: bool, doc_url: str) -> list[discord.ui.Item]:
    check = f"keyword.issoftkeyword({name!r})" if soft else f"keyword.iskeyword({name!r})"
    return collect(
        header(f"[`{name}`]({doc_url})", f"Python {'Soft Keyword' if soft else 'Keyword'}", info.summary),
        discord.ui.Separator(),
        text(f"**Example**\n```py\n{info.example}\n```"),
        facts(
            ("Introduced", f"Python {info.since}" if info.since else None),
            ("Runtime check", f"`{check}`"),
            ("Soft keyword", "only special in some contexts, still a valid identifier elsewhere" if soft else None),
        ),
    )


def dunder_items(info: DunderInfo, doc_url: str, see_also: str | None) -> list[discord.ui.Item]:
    return collect(
        header(f"[`{info.name}`]({doc_url})", f"Python Data Model{DOT}{info.group}", info.summary),
        discord.ui.Separator(),
        facts(
            ("Signature", f"`{info.signature}`"),
            ("Called by", info.called_by),
            ("Backs", info.backs or None),
            ("See also", see_also),
        ),
        discord.ui.Separator(),
        text(f"**Example**\n```py\n{info.example}\n```"),
    )


def whatsnew_highlight_items(series: str, wn: WhatsNew, cycle: dict[str, Any] | None, url: str) -> list[discord.ui.Item]:
    phase = cycle_phase(cycle) if cycle else None
    released = dated(cycle.get("releaseDate")) if cycle else None
    listing = "\n".join(f"\N{BULLET} {line}" for line in wn.highlights) or "*This page has no release-highlights section.*"
    return collect(
        header(f"[{safe(wn.title, 90)}]({url})", f"Release Highlights{DOT}Python {series}"),
        discord.ui.Separator(),
        text(listing),
        facts(("Released", released), ("Status", f"`{phase}`" if phase else None)),
    )


def whatsnew_detail_items(series: str, wn: WhatsNew, url: str) -> list[discord.ui.Item]:
    features = "\n".join(f"\N{BULLET} {safe(f, 120)}" for f in wn.features)
    sections = DOT.join(f"[{safe(name, 40)}]({url}#{anchor})" for name, anchor in wn.sections[:12])
    return collect(
        header(f"Python {series}: New Features", f"Sections of the What's New page{DOT}{len(wn.features)} headline features"),
        discord.ui.Separator(),
        text(f"**Headline Features**\n{features}") if features else None,
        text(f"**Jump To**\n{sections}") if sections else None,
    )


def since_items(entry: SphinxEntry, notes: list[tuple[str, str]]) -> list[discord.ui.Item]:
    added = next((m[1] for _, body in notes if (m := VERSION_ADDED_PATTERN.search(body))), None)
    if notes:
        lines = "\n\n".join(f"**{NOTE_LABELS[kind]}**\n{body}" for kind, body in notes)
    else:
        lines = "*The docs page has no version notes for this name, so it is probably old (3.x since early on) or documented as part of its parent.*"
    return collect(
        header(f"[`{entry.name}`]({entry.url})", f"Version History{DOT}{entry.role_label}"),
        discord.ui.Separator(),
        facts(("Added in", f"Python `{added}`" if added else None), ("Bot runtime", f"Python `{platform.python_version()}`")),
        discord.ui.Separator(),
        text(lines),
    )


def pypi_dependencies(requires_dist: list[str] | None) -> list[str]:
    names: list[str] = []
    for requirement in requires_dist or []:
        spec, _, marker = str(requirement).partition(";")
        if "extra" in marker:
            continue
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", spec.strip())
        if match and match[0] not in names:
            names.append(match[0])
    return names


def pypi_license(info: dict[str, Any]) -> str | None:
    expression = info.get("license_expression")
    if isinstance(expression, str) and expression.strip():
        return safe(expression, 60)
    raw = info.get("license")
    if isinstance(raw, str) and raw.strip() and len(raw) <= 60 and "\n" not in raw:
        return safe(raw, 60)
    for classifier in info.get("classifiers") or []:
        if str(classifier).startswith("License :: "):
            return safe(str(classifier).rsplit(" :: ", 1)[-1], 60)
    return None


def pypi_links(info: dict[str, Any], page_url: str) -> list[tuple[str, str]]:
    preferred = ("source", "repository", "homepage", "documentation", "docs", "changelog", "issues")
    urls: dict[str, str] = {str(k): str(v) for k, v in (info.get("project_urls") or {}).items() if isinstance(v, str)}
    if info.get("home_page"):
        urls.setdefault("Homepage", str(info["home_page"]))
    ordered = sorted(urls.items(), key=lambda kv: preferred.index(kv[0].casefold()) if kv[0].casefold() in preferred else len(preferred))
    links: list[tuple[str, str]] = []
    for label, url in ordered:
        if valid_url(url) and url != page_url and url not in {u for _, u in links}:
            links.append((label.title()[:40], url))
    return links[:4]


def pypi_items(data: dict[str, Any]) -> list[discord.ui.Item]:
    info = data.get("info") or {}
    name, version = safe(info.get("name"), 80), safe(info.get("version"), 40)
    page_url = str(info.get("package_url") or f"https://pypi.org/project/{quote(str(info.get('name') or ''), safe='')}/")

    files = data.get("urls") or []
    released = next((f.get("upload_time_iso_8601") for f in files if f.get("upload_time_iso_8601")), None)
    kinds = sorted({str(f.get("packagetype", "")).replace("bdist_wheel", "wheel").replace("sdist", "sdist") for f in files if f.get("packagetype")})
    versions = sorted(
        {m[1] for c in info.get("classifiers") or [] if (m := PYPI_CLASSIFIER_PATTERN.match(str(c)))},
        key=lambda v: tuple(int(p) for p in v.split(".")),
    )
    deps = pypi_dependencies(info.get("requires_dist"))
    vulns = data.get("vulnerabilities") or []
    author = info.get("author") or info.get("maintainer")

    warnings: list[str] = []
    if info.get("yanked"):
        reason = f": {safe(info.get('yanked_reason'), 120)}" if info.get("yanked_reason") else ""
        warnings.append(f"\N{WARNING SIGN} This release was **yanked**{reason}")
    if vulns:
        ids = ", ".join(f"`{safe(v.get('id'), 30)}`" for v in vulns[:3])
        warnings.append(f"\N{WARNING SIGN} **{len(vulns)}** known vulnerabilit{'y' if len(vulns) == 1 else 'ies'} for this version: {ids}")

    return collect(
        header(f"[{name}]({page_url})", f"PyPI{DOT}v{version}", safe(info.get("summary"), 220)),
        discord.ui.Separator(),
        text("\n".join(warnings)) if warnings else None,
        facts(
            ("Version", f"`{version}`"),
            ("Released", dated(released)),
            ("Requires Python", f"`{safe(info.get('requires_python'), 40)}`" if info.get("requires_python") else None),
            ("License", pypi_license(info)),
            ("Author", safe(author, 80) if author else None),
            ("Supports", pack(versions, 300) if versions else None),
            ("Files", ", ".join(f"`{k}`" for k in kinds) if kinds else None),
            ("Dependencies", f"{len(deps)}: {pack(deps[:10], 400)}" if deps else "none"),
        ),
        discord.ui.Separator(),
        text(f"**Install**\n```sh\npip install {name}\nuv add {name}\n```"),
    )


def cve_items(label: str, chunk: Sequence[CveRecord], number: int, pages: int, total: int) -> list[discord.ui.Item]:
    subtitle = f"NVD{DOT}{total} result{'' if total == 1 else 's'}{DOT}page {number}/{pages}"
    if not chunk:
        return collect(
            header(f"Security: {label}", subtitle),
            discord.ui.Separator(),
            text("*NVD lists no CVEs for this query.* That means none are recorded there, not that none exist."),
        )
    lines = []
    for record in chunk:
        badge = SEVERITY_BADGES.get(record.severity or "", "\N{MEDIUM WHITE CIRCLE}")
        rating = f"**{record.score:.1f} {record.severity}**" if record.score is not None else "*unscored*"
        published = when(record.published, "D") or "unknown date"
        summary = safe(record.summary, 190) or "*No description.*"
        lines.append(f"{badge} [{record.cve_id}]({NVD_DETAIL_URL}/{record.cve_id}) \N{EM DASH} {rating}{DOT}{published}\n-# {summary}")
    return collect(
        header(f"Security: {label}", subtitle),
        discord.ui.Separator(),
        text("\n\n".join(lines)),
        text("-# Source: National Vulnerability Database. Newest first. Check python.org/downloads for which patch release fixes what."),
    )


def download_items(version: str, cycle: dict[str, Any] | None, release_url: str, found: Sequence[str]) -> list[discord.ui.Item]:
    phase = cycle_phase(cycle) if cycle else "unknown"
    notes = {
        "bugfix": "Binaries are published for bugfix releases.",
        "security": "Security-only branch: python.org ships **source only**. Use your OS package manager, `uv`, or build from source.",
        "end-of-life": "**End of life.** No more fixes, so upgrade if you can.",
        "prerelease": "Pre-release builds can change before the final release.",
    }
    return collect(
        header(f"[Python {version}]({release_url})", f"Download{DOT}{phase}"),
        discord.ui.Separator(),
        facts(
            ("Series", f"`{cycle.get('cycle')}`" if cycle else None),
            ("Series released", dated(cycle.get("releaseDate")) if cycle else None),
            ("End of life", dated(cycle.get("eol")) if cycle and isinstance(cycle.get("eol"), str) else None),
            ("Available files", ", ".join(found) if found else "see the release page"),
        ),
        text(notes.get(phase, "")) if notes.get(phase) else None,
        text(f"-# Version managers: `uv python install {version}`{DOT}`pyenv install {version}`"),
    )


def milestone_kind(label: str) -> str:
    lowered = label.lower()
    for word, kind in (("development begins", "start"), ("alpha", "alpha"), ("beta", "beta"), ("candidate", "rc"), ("final", "final")):
        if word in lowered:
            return kind
    return "bugfix"


def countdown_items(series: str, pep_number: int, milestones: Sequence[tuple[str, str]]) -> list[discord.ui.Item]:
    today = today_iso()
    upcoming = [m for m in milestones if m[1] >= today]
    final = next((m for m in milestones if milestone_kind(m[0]) == "final"), None)

    def line(label: str, iso: str) -> str:
        return f"\N{BULLET} **{safe(label, 60)}** \N{EM DASH} {when(iso, 'D')} ({when(iso)})"

    nxt = (
        f"**Next milestone**: {safe(upcoming[0][0], 60)} {when(upcoming[0][1])} ({when(upcoming[0][1], 'D')})"
        if upcoming
        else "**No upcoming milestones** are listed in this schedule."
    )
    final_line = None
    if final:
        state = "released" if final[1] < today else when(final[1])
        final_line = f"**Final release**: {safe(final[0], 60)} \N{EM DASH} {when(final[1], 'D')} ({state})"
    return collect(
        header(f"Python {series} Countdown", f"PEP {pep_number} Release Schedule"),
        discord.ui.Separator(),
        text(nxt),
        text(final_line) if final_line else None,
        discord.ui.Separator() if len(upcoming) > 1 else None,
        text("**Coming up**\n" + "\n".join(line(*m) for m in upcoming[1:7])) if len(upcoming) > 1 else None,
        text("-# Dates are scheduled and release managers can move them."),
    )


def source_items(info: SourceInfo) -> list[discord.ui.Item]:
    return collect(
        header(f"[`{info.name}`]({info.url})", f"CPython Source{DOT}{info.kind}", safe(info.doc, 260)),
        discord.ui.Separator(),
        text(f"```py\n{info.signature}\n```") if info.signature else None,
        facts(
            ("File", f"`Lib/{info.relative_path}`"),
            ("Lines", f"`{info.start}\N{EN DASH}{info.end}` ({info.end - info.start + 1} lines)"),
            ("Git ref", f"`{cpython_ref()}` (the bot's own Python {platform.python_version()})"),
        ),
        text(f"**Preview**\n```py\n{info.preview}\n```"),
    )


def gotcha_items(info: GotchaInfo) -> list[discord.ui.Item]:
    return collect(
        header(info.title, "Python Gotcha", info.summary),
        discord.ui.Separator(),
        text(f"**\N{CROSS MARK} The trap**\n```py\n{info.bad}\n```"),
        text(f"**\N{WHITE HEAVY CHECK MARK} The fix**\n```py\n{info.good}\n```"),
        facts(("Why", info.why)),
    )


def idiom_items(info: IdiomInfo) -> list[discord.ui.Item]:
    return collect(
        header(info.title, f"Python Idiom{DOT}Python {info.since}+" if info.since else "Python Idiom", info.summary),
        discord.ui.Separator(),
        text(f"```py\n{info.example}\n```"),
        facts(("Note", info.notes or None)),
    )


def typing_items(info: TypingInfo, doc_url: str) -> list[discord.ui.Item]:
    return collect(
        header(f"[{info.title}]({doc_url})", f"Python Typing{DOT}Python {info.since}+" if info.since else "Python Typing", info.summary),
        discord.ui.Separator(),
        text(f"```py\n{info.example}\n```"),
    )


def topic_list_items(title: str, command: str, entries: Sequence[tuple[str, str]]) -> list[discord.ui.Item]:
    listing = "\n".join(f"\N{BULLET} `{key}` \N{EM DASH} {safe(name, 70)}" for key, name in entries)
    return collect(
        header(title, f"{len(entries)} topics{DOT}use `{command} <topic>`"),
        discord.ui.Separator(),
        text(listing),
    )


def zen_items() -> list[discord.ui.Item]:
    lines = "\n".join(f"\N{BULLET} {line}" for line in ZEN_LINES)
    return collect(
        header("The Zen of Python", f"{len(ZEN_LINES)} aphorisms"),
        discord.ui.Separator(),
        text(lines),
    )


class Python(commands.Cog):
    """Python tutorials, PEPs, documentation, standard library, versions, exceptions, operators, built-ins, and complexity."""

    help_emoji = "\N{SNAKE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._python_tags: dict[str, frontmatter.Post] = {}

        self._peps_cache: dict[str, dict[str, Any]] | None = None
        self._sphinx_cache: list[SphinxEntry] | None = None
        self._cache_lock = asyncio.Lock()

        self._cve_cache: dict[str, tuple[float, list[CveRecord]]] = {}
        self._cycles_cache: tuple[float, list[dict[str, Any]]] | None = None
        self._glossary_cache: dict[str, GlossaryTerm] | None = None

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
                    partial(generate_python_release_info, active[:8], active_view=True),
                    url="https://devguide.python.org/versions/",
                    label="Python Developer's Guide",
                    colour=ACTIVE_COLOUR,
                    links=[("Downloads", "https://www.python.org/downloads/"), ("endoflife.date", "https://endoflife.date/python")],
                )
            )
        if eol_list:
            pages.append(
                Page(
                    partial(generate_python_release_info, eol_list, active_view=False),
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

    async def get_cycles(self) -> list[dict[str, Any]]:
        """endoflife.date data, cached for an hour, with the bundled fallback."""
        if self._cycles_cache and time.monotonic() - self._cycles_cache[0] < CACHE_TTL:
            return self._cycles_cache[1]
        try:
            data = await self.fetch_json(ENDOFLIFE_PYTHON_URL)
            cycles = data if isinstance(data, list) and data else FALLBACK_PYTHON_CYCLES
        except PythonError:
            cycles = FALLBACK_PYTHON_CYCLES
        self._cycles_cache = (time.monotonic(), cycles)
        return cycles

    async def resolve_release(self, raw: str | None) -> tuple[str, dict[str, Any] | None]:
        """Turn ``None``, ``3.13`` or ``3.13.5`` into ``("3.13.5", cycle)``."""
        cycles = await self.get_cycles()
        if not raw or not raw.strip():
            cycle = latest_released_cycle(cycles)
            return str(cycle.get("latest")), cycle
        match = VERSION_ARG_PATTERN.match(raw.strip())
        if not match:
            msg = "Give a version like `3.13` or `3.13.5`."
            raise PythonError(msg)
        series = f"{match[1]}.{match[2]}"
        cycle = next((c for c in cycles if c.get("cycle") == series), None)
        if cycle is None:
            msg = f"Python {series} is not a known release series."
            raise PythonError(msg)
        if match[3] is not None:
            return f"{series}.{match[3]}", cycle
        latest = str(cycle.get("latest") or "")
        if not FULL_VERSION_PATTERN.match(latest):
            msg = f"Could not work out the latest release of Python {series}."
            raise PythonError(msg)
        return latest, cycle

    async def resolve_sphinx_entry(self, query: str) -> SphinxEntry:
        inventory = await self.get_sphinx_index()
        matches = await asyncio.to_thread(rank_sphinx_entries, inventory, query)
        if matches:
            return matches[0]
        names = {e.name: e for e in inventory if e.domain_role.startswith("py:")}
        fuzzy = await asyncio.to_thread(extractOne, query, list(names))
        if fuzzy is None or fuzzy[1] < 60:
            msg = f"No Python documentation entries matched {code(query, 40)}."
            raise PythonError(msg)
        return names[fuzzy[0]]

    async def find_curated(self, items: Sequence[Any], query: str, noun: str) -> Any:
        names = curated_names(items)
        cleaned = normalise_key(query)
        item = names.get(cleaned)
        if item is None:
            match = await asyncio.to_thread(extractOne, cleaned, list(names))
            if match is None or match[1] < 60:
                msg = f"No {noun} matched {code(query, 40)}. Available: {pack([i.key for i in items], 500)}"
                raise PythonError(msg)
            item = names[match[0]]
        return item

    async def url_exists(self, url: str) -> bool:
        try:
            async with self.bot.http_session.head(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT, allow_redirects=True) as response:
                return response.status < 400
        except TimeoutError, aiohttp.ClientError:
            return False

    async def retrieve_glossary_data(self) -> dict[str, GlossaryTerm]:
        if self._glossary_cache is not None:
            return self._glossary_cache
        async with self._cache_lock:
            if self._glossary_cache is None:
                raw = await self.fetch_bytes(f"{PYTHON_DOCS_URL}/glossary.html", missing="Could not load the Python glossary.")
                terms = await asyncio.to_thread(parse_glossary, raw.decode("utf-8", "replace"))
                if not terms:
                    msg = "Could not parse the Python glossary."
                    raise PythonError(msg)
                self._glossary_cache = terms
            return self._glossary_cache

    async def get_nvd_vulnerabilities(self, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            async with self.bot.http_session.get(NVD_URL, params=params, headers=headers, timeout=NVD_TIMEOUT) as response:
                if response.status in {403, 429}:
                    msg = "NVD is rate-limiting requests right now. Try again in a minute."
                    raise PythonError(msg)
                if response.status == 404:
                    msg = "NVD has no data for that query, possibly because it doesn't know that exact Python version."
                    raise PythonError(msg)
                if response.status >= 400:
                    msg = f"NVD returned HTTP {response.status}."
                    raise PythonError(msg)
                data = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as error:
            msg = "Could not reach the National Vulnerability Database right now. Try again in a moment."
            raise PythonError(msg) from error
        if not isinstance(data, dict):
            msg = "NVD returned an unexpected response."
            raise PythonError(msg)
        return data

    async def retrieve_cached_nvd_records(self, key: str, params: dict[str, Any]) -> list[CveRecord]:
        cached = self._cve_cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL:
            return cached[1]
        records = await asyncio.to_thread(parse_nvd, await self.get_nvd_vulnerabilities(params))
        if len(self._cve_cache) >= 64:
            self._cve_cache.pop(min(self._cve_cache, key=lambda k: self._cve_cache[k][0]))
        self._cve_cache[key] = (time.monotonic(), records)
        return records

    @python.command(
        name="glossary",
        aliases=["gloss", "term", "define"],
        extras={"examples": ["python glossary decorator", "python glossary GIL", "python glossary duck-typing"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_glossary(
        self,
        ctx: commands.Context[Bot],
        *,
        term: str = commands.parameter(description="The glossary term (e.g. `decorator`, `GIL`, `iterable`)."),
    ) -> discord.Message:
        """Look up a term in the official Python glossary."""
        return await self.deliver(ctx, self.fetch_glossary_entry(ctx, term))

    async def fetch_glossary_entry(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        terms = await self.retrieve_glossary_data()
        cleaned = query.strip().strip("`").casefold()
        entry = terms.get(cleaned)
        if entry is None:
            match = await asyncio.to_thread(extractOne, cleaned, list(terms))
            if match is None or match[1] < 60:
                msg = f"No glossary term matched {code(query, 40)}."
                raise PythonError(msg)
            entry = terms[match[0]]
        return self.single(
            ctx,
            Page(
                partial(glossary_items, entry),
                url=entry.url,
                label="Open Glossary Entry",
                links=[("Full Glossary", f"{PYTHON_DOCS_URL}/glossary.html")],
            ),
        )

    @python.command(
        name="keyword",
        aliases=["kw", "kwd", "keywords"],
        extras={"examples": ["python keyword yield", "python keyword match", "python keyword nonlocal", "python keyword type"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_keyword(
        self,
        ctx: commands.Context[Bot],
        *,
        word: str = commands.parameter(description="The keyword or soft keyword (e.g. `async`, `lambda`, `match`)."),
    ) -> discord.Message:
        """Explain a Python keyword or soft keyword."""
        return await self.deliver(ctx, self.fetch_keyword_details(ctx, word))

    async def fetch_keyword_details(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        cleaned = query.strip().strip("`")
        hard, soft = set(keyword.kwlist), set(keyword.softkwlist)
        known = hard | soft | set(KEYWORDS_DB)
        name = {k.casefold(): k for k in known}.get(cleaned.casefold())
        if name is None:
            match = await asyncio.to_thread(extractOne, cleaned, sorted(known))
            if match is None or match[1] < 70:
                msg = f"{code(cleaned, 30)} is not a Python keyword. Keywords: {pack(sorted(hard), 700)}"
                raise PythonError(msg)
            name = match[0]

        info = KEYWORDS_DB.get(name) or KeywordInfo(
            name, "A reserved word in this version of Python.", name, "reference/lexical_analysis.html#keywords"
        )
        is_soft = name in soft and name not in hard
        doc_url = f"{PYTHON_DOCS_URL}/{info.doc}"
        return self.single(
            ctx,
            Page(
                partial(keyword_items, name, info, soft=is_soft, doc_url=doc_url),
                url=doc_url,
                label="Language Reference",
                links=[("All Keywords", f"{PYTHON_DOCS_URL}/reference/lexical_analysis.html#keywords")],
            ),
        )

    @python.command(
        name="dunder",
        aliases=["magic", "special", "datamodel", "dunders"],
        extras={"examples": ["python dunder __enter__", "python dunder getitem", "python dunder radd", "python dunder __eq__"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_dunder(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The special method (e.g. `__init__`, `getitem`, `__radd__`)."),
    ) -> discord.Message:
        """Explain a data-model (dunder) method and what calls it."""
        return await self.deliver(ctx, self.get_special_methods(ctx, name))

    async def get_special_methods(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        info = lookup_dunder(query)
        if info is None:
            match = await asyncio.to_thread(extractOne, normalise_dunder(query), list(DUNDERS_DB))
            if match is None or match[1] < 70:
                msg = f"No special method matched {code(query, 40)}. Try `__init__`, `__getitem__`, `__enter__`, `__add__`..."
                raise PythonError(msg)
            info = DUNDERS_DB[match[0]]

        related = [op for op in OPERATORS_DB if info.name in str(op.dunder)]
        see_also = ", ".join(f"`python operator {op.symbol}`" for op in related[:3]) or None
        doc_url = f"{PYTHON_DOCS_URL}/{info.doc}"
        return self.single(
            ctx,
            Page(
                partial(dunder_items, info, doc_url, see_also),
                url=doc_url,
                label="Data Model Docs",
                links=[("Special Method Names", f"{PYTHON_DOCS_URL}/reference/datamodel.html#special-method-names")],
            ),
        )

    @python.command(
        name="whatsnew",
        aliases=["new", "wn", "whats-new"],
        extras={"examples": ["python whatsnew", "python whatsnew 3.13", "python whatsnew 3.12"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def python_whatsnew(
        self,
        ctx: commands.Context[Bot],
        version: str | None = commands.parameter(default=None, description="The Python series (e.g. `3.13`). Defaults to the newest release."),
    ) -> discord.Message:
        """Show the headline features of a Python release."""
        return await self.deliver(ctx, self.get_python_release_notes(ctx, version))

    async def get_python_release_notes(self, ctx: commands.Context[Bot], version: str | None) -> PythonView:
        cycles = await self.get_cycles()
        if version and version.strip():
            match = VERSION_ARG_PATTERN.match(version.strip())
            if not match:
                msg = "Give a version like `3.14` or `3.12`."
                raise PythonError(msg)
            series = f"{match[1]}.{match[2]}"
        else:
            series = str(latest_released_cycle(cycles).get("cycle"))

        url = f"{PYTHON_DOCS_URL}/whatsnew/{series}.html"
        raw = await self.fetch_bytes(url, missing=f"There is no What's New page for Python {series}.")
        wn = await asyncio.to_thread(extract_whatsnew, raw.decode("utf-8", "replace"))
        cycle = next((c for c in cycles if c.get("cycle") == series), None)

        links = [("All What's New", f"{PYTHON_DOCS_URL}/whatsnew/index.html"), ("Changelog", f"{PYTHON_DOCS_URL}/whatsnew/changelog.html")]
        pages = [
            Page(
                partial(whatsnew_highlight_items, series, wn, cycle, url), url=url, label=f"What's New in {series}", colour=ACTIVE_COLOUR, links=links
            )
        ]
        if wn.features or wn.sections:
            pages.append(
                Page(partial(whatsnew_detail_items, series, wn, url), url=url, label=f"What's New in {series}", colour=PYTHON_COLOUR, links=links)
            )
        return PythonView(ctx.author, pages)

    @python.command(
        name="since",
        aliases=["added", "changed", "history"],
        extras={"examples": ["python since itertools.batched", "python since asyncio.TaskGroup", "python since str.removeprefix"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_since(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The module, class, function or method (e.g. `asyncio.TaskGroup`)."),
    ) -> discord.Message:
        """Show when something was added, changed, deprecated or removed."""
        return await self.deliver(ctx, self.retrieve_sphinx_entry_view(ctx, name))

    async def retrieve_sphinx_entry_view(self, ctx: commands.Context[Bot], query: str) -> PythonView:
        cleaned = query.strip().strip("`")
        if not cleaned:
            msg = "Provide a module, class, or function name to look up."
            raise PythonError(msg)
        entry = await self.resolve_sphinx_entry(cleaned)
        page_url, _, anchor = entry.url.partition("#")
        html = await self.optional_text(page_url)
        if not html:
            msg = "Could not load the documentation page for that name."
            raise PythonError(msg)
        notes = await asyncio.to_thread(extract_version_notes, html, anchor or None)
        return self.single(
            ctx,
            Page(
                partial(since_items, entry, notes),
                url=entry.url,
                label="Open on docs.python.org",
                colour=PYTHON_GOLD,
                links=[("What's New", f"{PYTHON_DOCS_URL}/whatsnew/index.html")],
            ),
        )

    @python.command(
        name="pypi",
        aliases=["pip", "package", "pkg"],
        extras={"examples": ["python pypi requests", "python pypi numpy 1.26.4", "python pypi discord.py"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_pypi(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The PyPI project name (e.g. `requests`)."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Look up a package on PyPI."""
        return await self.deliver(ctx, self.pypi_view(ctx, package, version))

    async def pypi_view(self, ctx: commands.Context[Bot], package: str, version: str | None) -> PythonView:
        name = package.strip().strip("`")
        if not PYPI_NAME_PATTERN.match(name):
            msg = "That doesn't look like a valid PyPI project name."
            raise PythonError(msg)
        path = quote(name, safe="")
        if version:
            if not PYPI_VERSION_PATTERN.match(version.strip()):
                msg = "That doesn't look like a valid version string."
                raise PythonError(msg)
            path += f"/{quote(version.strip(), safe='')}"
        data = await self.fetch_json(
            f"{PYPI_JSON_URL}/{path}/json", missing=f"PyPI has no package {code(name, 40)}{' at that version' if version else ''}."
        )
        if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
            msg = "PyPI returned an unexpected response."
            raise PythonError(msg)

        info = data["info"]
        page_url = str(info.get("package_url") or f"https://pypi.org/project/{quote(name, safe='')}/")
        return self.single(
            ctx,
            Page(partial(pypi_items, data), url=page_url, label="Open on PyPI", colour=PYTHON_GOLD, links=pypi_links(info, page_url)),
        )

    @python.command(
        name="cve",
        aliases=["vuln", "security", "vulns"],
        extras={"examples": ["python cve", "python cve 3.12", "python cve 3.11.4", "python cve CVE-2023-24329"]},
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def python_cve(
        self,
        ctx: commands.Context[Bot],
        target: str | None = commands.parameter(
            default=None, description="A Python version (`3.12`, `3.12.4`) or a CVE id. Defaults to the newest release."
        ),
    ) -> discord.Message:
        """List known CVEs affecting a Python release, or look up one CVE."""
        return await self.deliver(ctx, self.fetch_cve_info(ctx, target))

    async def fetch_cve_info(self, ctx: commands.Context[Bot], target: str | None) -> PythonView:
        cleaned = (target or "").strip().strip("`")
        if CVE_ID_PATTERN.match(cleaned):
            cve_id = cleaned.upper()
            records = await self.retrieve_cached_nvd_records(f"id:{cve_id}", {"cveId": cve_id})
            label = cve_id
        else:
            version, _ = await self.resolve_release(cleaned or None)
            records = await self.retrieve_cached_nvd_records(
                f"cpe:{version}",
                {"cpeName": f"cpe:2.3:a:python:python:{version}:*:*:*:*:*:*:*", "resultsPerPage": 200},
            )
            label = f"Python {version}"

        chunks = [records[i : i + CVES_PER_PAGE] for i in range(0, len(records), CVES_PER_PAGE)] or [[]]
        severe = any(r.severity in {"CRITICAL", "HIGH"} for r in records)
        links = [("NVD", "https://nvd.nist.gov/"), ("Python Security", "https://www.python.org/dev/security/")]
        pages = [
            Page(
                partial(cve_items, label, chunk, number, len(chunks), len(records)),
                url="https://www.python.org/downloads/",
                label="Downloads",
                colour=EOL_COLOUR if severe else (SECURITY_COLOUR if records else ACTIVE_COLOUR),
                links=links,
            )
            for number, chunk in enumerate(chunks, start=1)
        ]
        return PythonView(ctx.author, pages)

    @python.command(
        name="download",
        aliases=["dl", "install", "get"],
        extras={"examples": ["python download", "python download 3.13", "python download 3.12.8"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def python_download(
        self,
        ctx: commands.Context[Bot],
        version: str | None = commands.parameter(default=None, description="A series (`3.13`) or exact release (`3.13.5`). Defaults to the newest."),
    ) -> discord.Message:
        """Link the installers and source for a Python release."""
        return await self.deliver(ctx, self.fetch_python_download_links(ctx, version))

    async def fetch_python_download_links(self, ctx: commands.Context[Bot], raw: str | None) -> PythonView:
        version, cycle = await self.resolve_release(raw)
        release_url = f"{PYTHON_RELEASES_URL}/python-{version.replace('.', '')}/"
        candidates = {
            "Source (.tgz)": f"{PYTHON_FTP_URL}/{version}/Python-{version}.tgz",
            "Windows installer": f"{PYTHON_FTP_URL}/{version}/python-{version}-amd64.exe",
            "macOS installer": f"{PYTHON_FTP_URL}/{version}/python-{version}-macos11.pkg",
        }
        # Only offer links that really exist: security-only releases ship no binaries.
        results = await asyncio.gather(self.url_exists(release_url), *(self.url_exists(u) for u in candidates.values()))
        if not results[0]:
            msg = f"python.org has no release page for Python {version}."
            raise PythonError(msg)

        links = [(label, url) for (label, url), ok in zip(candidates.items(), results[1:], strict=True) if ok]
        links.append(("All Downloads", "https://www.python.org/downloads/"))
        phase = cycle_phase(cycle) if cycle else "security"
        colour = {"bugfix": ACTIVE_COLOUR, "security": SECURITY_COLOUR, "end-of-life": EOL_COLOUR}.get(phase, PYTHON_COLOUR)
        return self.single(
            ctx,
            Page(
                partial(download_items, version, cycle, release_url, [label for label, _ in links[:-1]]),
                url=release_url,
                label=f"Python {version}",
                colour=colour,
                links=links,
            ),
        )

    @python.command(
        name="countdown",
        aliases=["schedule", "next", "upcoming"],
        extras={"examples": ["python countdown"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def python_countdown(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Count down to the next milestone of the upcoming Python release."""
        return await self.deliver(ctx, self.countdown_view(ctx))

    async def countdown_view(self, ctx: commands.Context[Bot]) -> PythonView:
        peps = await self.get_peps_index()
        schedules = [((int(m[1]), int(m[2])), entry) for entry in peps.values() if (m := SCHEDULE_TITLE_PATTERN.match(str(entry.get("title", ""))))]
        if not schedules:
            msg = "Could not find a Python release-schedule PEP."
            raise PythonError(msg)

        (major, minor), pep = max(schedules, key=lambda pair: pair[0])
        number = int(pep.get("number", 0))
        pep_url = pep.get("url") or f"{PEPS_BASE_URL}/pep-{number:04d}/"
        html = await self.optional_text(pep_url)
        if not html:
            msg = f"Could not load PEP {number}."
            raise PythonError(msg)
        series = f"{major}.{minor}"
        milestones = await asyncio.to_thread(parse_release_schedule, html, series)
        if not milestones:
            msg = f"Could not read the schedule from PEP {number}."
            raise PythonError(msg)

        return self.single(
            ctx,
            Page(
                partial(countdown_items, series, number, milestones),
                url=pep_url,
                label=f"Open PEP {number}",
                colour=PYTHON_GOLD,
                links=[("Developer's Guide", "https://devguide.python.org/versions/")],
            ),
        )

    @python.command(
        name="source",
        aliases=["src", "code"],
        extras={"examples": ["python source asyncio.run", "python source pathlib.Path.glob", "python source functools.lru_cache"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def python_source(
        self,
        ctx: commands.Context[Bot],
        target: str = commands.parameter(description="A dotted standard-library name (e.g. `asyncio.run`, `collections.Counter`)."),
    ) -> discord.Message:
        """Link the CPython source (with line numbers) of a standard-library object."""
        return await self.deliver(ctx, self.retrieve_source_details(ctx, target))

    async def retrieve_source_details(self, ctx: commands.Context[Bot], raw: str) -> PythonView:
        cleaned = raw.strip().strip("`").removesuffix("()")
        if len(cleaned) > 80 or not DOTTED_NAME_PATTERN.match(cleaned):
            msg = "Give a dotted name like `asyncio.run` or `pathlib.Path.glob`."
            raise PythonError(msg)
        info = await asyncio.to_thread(inspect_source, cleaned)
        top = quote(cleaned.split(".", 1)[0], safe="")
        return self.single(
            ctx,
            Page(
                partial(source_items, info),
                url=info.url,
                label="View on GitHub",
                links=[("Module Docs", f"{PYTHON_DOCS_URL}/library/{top}.html")],
            ),
        )

    @python.command(
        name="gotcha",
        aliases=["pitfall", "trap", "gotchas", "pitfalls"],
        extras={"examples": ["python gotcha", "python gotcha mutable-default", "python gotcha late binding", "python gotcha is vs =="]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_gotcha(
        self,
        ctx: commands.Context[Bot],
        *,
        topic: str | None = commands.parameter(default=None, description="The pitfall (e.g. `mutable-default`). Leave empty to list them all."),
    ) -> discord.Message:
        """Show a classic Python pitfall with the fix."""
        return await self.deliver(ctx, self.gotcha_view(ctx, topic))

    async def gotcha_view(self, ctx: commands.Context[Bot], topic: str | None) -> PythonView:
        if not topic or not topic.strip():
            entries = [(g.key, g.title) for g in GOTCHAS_DB]
            return self.single(ctx, Page(partial(topic_list_items, "Python Gotchas", "python gotcha", entries), colour=SECURITY_COLOUR))
        info = await self.find_curated(GOTCHAS_DB, topic, "gotcha")
        return self.single(
            ctx,
            Page(
                partial(gotcha_items, info),
                url=f"{PYTHON_DOCS_URL}/faq/programming.html",
                label="Programming FAQ",
                colour=SECURITY_COLOUR,
            ),
        )

    @python.command(
        name="idiom",
        aliases=["recipe", "snippet", "howto", "idioms", "recipes"],
        extras={"examples": ["python idiom", "python idiom flatten", "python idiom group-by", "python idiom read-file"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_idiom(
        self,
        ctx: commands.Context[Bot],
        *,
        topic: str | None = commands.parameter(default=None, description="The recipe (e.g. `flatten`, `dedupe`). Leave empty to list them all."),
    ) -> discord.Message:
        """Show an idiomatic Python recipe."""
        return await self.deliver(ctx, self.idiom_view(ctx, topic))

    async def idiom_view(self, ctx: commands.Context[Bot], topic: str | None) -> PythonView:
        if not topic or not topic.strip():
            entries = [(i.key, i.title) for i in IDIOMS_DB]
            return self.single(ctx, Page(partial(topic_list_items, "Python Idioms", "python idiom", entries), colour=ACTIVE_COLOUR))
        info = await self.find_curated(IDIOMS_DB, topic, "idiom")
        return self.single(
            ctx,
            Page(
                partial(idiom_items, info),
                url=f"{PYTHON_DOCS_URL}/howto/index.html",
                label="Python HOWTOs",
                colour=ACTIVE_COLOUR,
                links=[("itertools Recipes", f"{PYTHON_DOCS_URL}/library/itertools.html#itertools-recipes")],
            ),
        )

    @python.command(
        name="typing",
        aliases=["hint", "hints", "types", "annotation"],
        extras={"examples": ["python typing", "python typing protocol", "python typing paramspec", "python typing TypedDict"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def python_typing(
        self,
        ctx: commands.Context[Bot],
        *,
        topic: str | None = commands.parameter(
            default=None, description="The typing feature (e.g. `Protocol`, `TypeVar`). Leave empty to list them."
        ),
    ) -> discord.Message:
        """Cheat sheet for Python's typing features."""
        return await self.deliver(ctx, self.typing_view(ctx, topic))

    async def typing_view(self, ctx: commands.Context[Bot], topic: str | None) -> PythonView:
        if not topic or not topic.strip():
            entries = [(t.key, t.title) for t in TYPING_DB]
            return self.single(ctx, Page(partial(topic_list_items, "Python Typing", "python typing", entries)))
        info = await self.find_curated(TYPING_DB, topic, "typing topic")
        doc_url = f"{PYTHON_DOCS_URL}/{info.doc}"
        return self.single(
            ctx,
            Page(
                partial(typing_items, info, doc_url),
                url=doc_url,
                label="Typing Docs",
                links=[("Typing Cheat Sheet", "https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html")],
            ),
        )

    @python.command(
        name="zen",
        aliases=["zen-of-python", "the-zen-of-python"],
        extras={"examples": ["python zen"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def python_zen(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show the Zen of Python."""
        return await self.deliver(ctx, self.zen_view(ctx))

    async def zen_view(self, ctx: commands.Context[Bot]) -> PythonView:
        return self.single(
            ctx,
            Page(
                partial(zen_items),
                url=f"{PEPS_BASE_URL}/pep-0020/",
                label="PEP 20: The Zen of Python",
                colour=PYTHON_COLOUR,
                links=[("PEP Index", f"{PEPS_BASE_URL}/")],
            ),
        )
