from __future__ import annotations

import asyncio
import pathlib
import re
import time
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

from .knowledge import (
    BUILTINS_DB,
    COMPLEXITY_DB,
    ERRORS_DB,
    GOTCHAS_DB,
    IDIOMS_DB,
    KEYWORDS_DB,
    OPERATORS_DB,
    STDLIB_CURATED,
    SYMBOLS_DB,
    TYPING_DB,
    BuiltinInfo,
    ErrorInfo,
    KeywordInfo,
    lookup_symbol,
    normalise_symbol,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from core import Bot

    from .knowledge import ComplexityInfo, GotchaInfo, IdiomInfo, OperatorInfo, StdlibMeta, SymbolInfo, TypingInfo

USER_AGENT = "Parrot Discord bot (https://github.com/rtk-rnjn/Parrot)"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

MDN_BASE_URL = "https://developer.mozilla.org"
MDN_JS_URL = "https://developer.mozilla.org/en-US/docs/Web/JavaScript"
MDN_SEARCH_API_URL = "https://developer.mozilla.org/api/v1/search"
MDN_GLOSSARY_URL = "https://developer.mozilla.org/en-US/docs/Glossary"
TC39_PROPOSALS_URL = "https://tc39.es/dataset/proposals.min.json"
TC39_PROPOSALS_FALLBACK_URL = "https://tc39.es/dataset/proposals.json"
TC39_BASE_URL = "https://tc39.es"
TC39_REPO_URL = "https://github.com/tc39/proposals"
ECMA262_URL = "https://tc39.es/ecma262/"
ENDOFLIFE_NODE_URL = "https://endoflife.date/api/nodejs.json"
NODE_DOCS_URL = "https://nodejs.org/api"
NODE_DIST_URL = "https://nodejs.org/dist"
NODE_RELEASES_URL = "https://nodejs.org/en/about/previous-releases"
NODE_SCHEDULE_URL = "https://raw.githubusercontent.com/nodejs/Release/main/schedule.json"
NODE_BLOB_URL = "https://github.com/nodejs/node/blob/main"
NODE_RAW_URL = "https://raw.githubusercontent.com/nodejs/node/main"
NODE_REPO_URL = "https://github.com/nodejs/node"
JS_ICON = "https://raw.githubusercontent.com/voodootikigod/logo.js/master/js.png"

DOT = " \N{MIDDLE DOT} "
MIN_TUTORIAL_SCORE = 60
BODY_LIMIT = 1500
ITEMS_PER_PAGE = 8

JS_COLOUR = discord.Colour(0xF7DF1E)
NODE_GREEN = discord.Colour(0x5FA04E)
TS_BLUE = discord.Colour(0x3178C6)
ACTIVE_COLOUR = discord.Colour(0x238636)
SECURITY_COLOUR = discord.Colour(0xD29922)
EOL_COLOUR = discord.Colour(0xDA3633)
DRAFT_COLOUR = discord.Colour(0x6E7681)

TC39_STAGE_COLOURS: dict[str, discord.Colour] = {
    "4": ACTIVE_COLOUR,
    "3": JS_COLOUR,
    "2.7": SECURITY_COLOUR,
    "2": SECURITY_COLOUR,
    "1": TS_BLUE,
    "0": DRAFT_COLOUR,
    "-1": EOL_COLOUR,
    "Inactive": EOL_COLOUR,
    "Withdrawn": EOL_COLOUR,
}

TC39_STAGE_LABELS: dict[str, str] = {
    "4": "Stage 4 (Finished)",
    "3": "Stage 3 (Candidate)",
    "2.7": "Stage 2.7 (Testing)",
    "2": "Stage 2 (Draft)",
    "1": "Stage 1 (Proposal)",
    "0": "Stage 0 (Strawperson)",
    "-1": "Inactive / Withdrawn",
}

TUTORIAL_DIR = Path("extra/tutorials/javascript")

NPM_REGISTRY_URL = "https://registry.npmjs.org"
NPM_PACKAGE_URL = "https://www.npmjs.com/package"
NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_DETAIL_URL = "https://nvd.nist.gov/vuln/detail"
NVD_TIMEOUT = aiohttp.ClientTimeout(total=25)
CACHE_TTL = 3600
CVES_PER_PAGE = 5
MAX_CVES = 40

NPM_NAME_PATTERN = re.compile(r"^(?:@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]{0,213}$")
NPM_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
NODE_VERSION_ARG_PATTERN = re.compile(r"^v?(\d{1,2})(?:\.(\d{1,2}))?(?:\.(\d{1,2}))?$", re.IGNORECASE)
FULL_VERSION_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+$")
ES_EDITION_PATTERN = re.compile(r"^(?:es|ecmascript[-_\s]*)?(20\d{2}|\d{1,2}|next)$", re.IGNORECASE)
TC39_STAGE_PATTERN = re.compile(r"^stage[-_\s]*(0|1|2\.7|2|3|4)$", re.IGNORECASE)
CVE_ID_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
DOTTED_NAME_PATTERN = re.compile(r"^(?:node:)?[A-Za-z_$][\w$]*(?:[./][A-Za-z_$][\w$]*)*$")

JS_HARD_KEYWORDS = frozenset(
    {
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "debugger",
        "default",
        "delete",
        "do",
        "else",
        "enum",
        "export",
        "extends",
        "false",
        "finally",
        "for",
        "function",
        "if",
        "import",
        "in",
        "instanceof",
        "new",
        "null",
        "return",
        "super",
        "switch",
        "this",
        "throw",
        "true",
        "try",
        "typeof",
        "var",
        "void",
        "while",
        "with",
        "yield",
    }
)

JS_CONTEXTUAL_KEYWORDS = frozenset(
    {
        "accessor",
        "as",
        "async",
        "await",
        "from",
        "get",
        "implements",
        "interface",
        "let",
        "meta",
        "of",
        "package",
        "private",
        "protected",
        "public",
        "set",
        "static",
        "target",
        "using",
    }
)

NODE_STDLIB_MODULES = frozenset(
    {
        "assert",
        "async_hooks",
        "buffer",
        "child_process",
        "cluster",
        "console",
        "crypto",
        "dgram",
        "diagnostics_channel",
        "dns",
        "events",
        "fs",
        "http",
        "http2",
        "https",
        "inspector",
        "module",
        "net",
        "os",
        "path",
        "perf_hooks",
        "process",
        "punycode",
        "querystring",
        "readline",
        "repl",
        "sea",
        "sqlite",
        "stream",
        "string_decoder",
        "test",
        "timers",
        "tls",
        "trace_events",
        "tty",
        "url",
        "util",
        "v8",
        "vm",
        "wasi",
        "worker_threads",
        "zlib",
    }
)

JS_BUILTIN_OBJECTS: dict[str, tuple[str, str]] = {
    "Array": ("Indexed Collection", "Array(element0, element1, /* …, */ elementN)"),
    "Object": ("Fundamental Object", "Object(value)"),
    "Function": ("Fundamental Object", "new Function(arg1, arg2, /* …, */ functionBody)"),
    "Boolean": ("Fundamental Object", "Boolean(value)"),
    "Symbol": ("Primitive / Well-Known Namespace", "Symbol(description)"),
    "Number": ("Numbers & Dates", "Number(value)"),
    "BigInt": ("Numbers & Dates", "BigInt(value)"),
    "Math": ("Numbers & Dates Namespace", "Math.<method>(...)"),
    "Date": ("Numbers & Dates", "new Date(year, monthIndex, day, hours, minutes, seconds, ms)"),
    "Temporal": ("Modern Date/Time Namespace", "Temporal.Now.instant()"),
    "String": ("Text Processing", "String(thing)"),
    "RegExp": ("Text Processing", "new RegExp(pattern, flags)"),
    "Map": ("Keyed Collection", "new Map(iterable)"),
    "Set": ("Keyed Collection", "new Set(iterable)"),
    "WeakMap": ("Keyed Collection", "new WeakMap(iterable)"),
    "WeakSet": ("Keyed Collection", "new WeakSet(iterable)"),
    "WeakRef": ("Memory Management", "new WeakRef(targetObject)"),
    "FinalizationRegistry": ("Memory Management", "new FinalizationRegistry(callback)"),
    "Promise": ("Control Abstraction", "new Promise((resolve, reject) => { ... })"),
    "Iterator": ("Control Abstraction", "Iterator.from(object)"),
    "AsyncIterator": ("Control Abstraction", "AsyncIterator"),
    "Generator": ("Control Abstraction", "function* generator() { yield value; }"),
    "AsyncFunction": ("Control Abstraction", "async function name(param0) { statements }"),
    "Reflect": ("Reflection Namespace", "Reflect.<trap>(target, ...)"),
    "Proxy": ("Reflection / Meta-programming", "new Proxy(target, handler)"),
    "JSON": ("Structured Data Namespace", "JSON.parse(text) / JSON.stringify(value)"),
    "ArrayBuffer": ("Structured Data", "new ArrayBuffer(length, options)"),
    "SharedArrayBuffer": ("Structured Data", "new SharedArrayBuffer(length, options)"),
    "DataView": ("Structured Data", "new DataView(buffer, byteOffset, byteLength)"),
    "Atomics": ("Structured Data Namespace", "Atomics.<operation>(typedArray, index, value)"),
    "TypedArray": ("Indexed Binary Collection", "new Int32Array(length) / new Uint8Array(buffer)"),
    "Uint8Array": ("Indexed Binary Collection", "new Uint8Array(length)"),
    "Int32Array": ("Indexed Binary Collection", "new Int32Array(length)"),
    "Float64Array": ("Indexed Binary Collection", "new Float64Array(length)"),
    "Intl": ("Internationalization Namespace", "new Intl.DateTimeFormat(locales, options)"),
    "DisposableStack": ("Explicit Resource Management", "new DisposableStack()"),
    "AsyncDisposableStack": ("Explicit Resource Management", "new AsyncDisposableStack()"),
    "globalThis": ("Global Value Property", "globalThis"),
    "undefined": ("Global Value Property", "undefined"),
    "NaN": ("Global Value Property", "NaN"),
    "Infinity": ("Global Value Property", "Infinity"),
    "parseInt": ("Global Function", "parseInt(string, radix)"),
    "parseFloat": ("Global Function", "parseFloat(string)"),
    "isNaN": ("Global Function", "isNaN(value)"),
    "isFinite": ("Global Function", "isFinite(value)"),
    "encodeURI": ("Global Function", "encodeURI(uri)"),
    "decodeURI": ("Global Function", "decodeURI(encodedURI)"),
    "encodeURIComponent": ("Global Function", "encodeURIComponent(uriComponent)"),
    "decodeURIComponent": ("Global Function", "decodeURIComponent(encodedURI)"),
    "eval": ("Global Function", "eval(script)"),
    "structuredClone": ("Web / WinterCG Global Function", "structuredClone(value, options)"),
    "fetch": ("Web / WinterCG Global Function", "fetch(resource, options)"),
    "queueMicrotask": ("Web / WinterCG Global Function", "queueMicrotask(callback)"),
    "setTimeout": ("Timer Global Function", "setTimeout(functionRef, delay, ...params)"),
    "setInterval": ("Timer Global Function", "setInterval(functionRef, delay, ...params)"),
    "atob": ("Base64 Global Function", "atob(encodedData)"),
    "btoa": ("Base64 Global Function", "btoa(stringToEncode)"),
}

JS_STANDARD_ERRORS: dict[str, tuple[str, str]] = {
    "Error": ("`Object` \N{RIGHTWARDS ARROW} `Error`", "Base constructor for all standard and custom JavaScript runtime error objects."),
    "TypeError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `TypeError`",
        "Thrown when an operation cannot be performed because a value is not of the expected type (e.g. accessing a property on `undefined` or `null`).",
    ),
    "ReferenceError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `ReferenceError`",
        "Thrown when referencing an undeclared variable or accessing a `let`/`const` binding inside its Temporal Dead Zone (TDZ).",
    ),
    "SyntaxError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `SyntaxError`",
        "Thrown when the JavaScript engine or `JSON.parse()` encounters tokens that violate the grammar of the language.",
    ),
    "RangeError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `RangeError`",
        "Thrown when a numeric value or call stack depth is outside the allowable range (e.g. `Maximum call stack size exceeded` or invalid `Array` length).",
    ),
    "URIError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `URIError`",
        "Thrown when a global URI handling function (`decodeURIComponent`, `encodeURI`) is passed a malformed percent-encoded sequence.",
    ),
    "EvalError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `EvalError`",
        "Historical error constructor related to the global `eval()` function; retained for backward compatibility in ECMAScript.",
    ),
    "AggregateError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `AggregateError`",
        "Wraps multiple errors into a single object (e.g. thrown by `Promise.any()` when all input promises reject).",
    ),
    "SuppressedError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `SuppressedError`",
        "Wraps an error thrown during explicit resource disposal (`using` / `[Symbol.dispose]()`) when another error was already active.",
    ),
    "InternalError": (
        "`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `InternalError`",
        "Non-standard SpiderMonkey error thrown when an internal engine limit is exceeded (such as excessive recursion or switch cases).",
    ),
}

NOTE_LABELS = {
    "added": "\N{HEAVY PLUS SIGN} Added",
    "changed": "\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS} Changed",
    "deprecated": "\N{WARNING SIGN} Deprecated",
    "removed": "\N{CROSS MARK} Removed",
}
SEVERITY_BADGES = {
    "CRITICAL": "\N{LARGE RED CIRCLE}",
    "HIGH": "\N{LARGE ORANGE CIRCLE}",
    "MEDIUM": "\N{LARGE YELLOW CIRCLE}",
    "LOW": "\N{LARGE GREEN CIRCLE}",
}

JS_LAWS_LINES = [
    "Always bet on JavaScript. \N{EM DASH} Brendan Eich",
    "Any application that can be written in JavaScript, will eventually be written in JavaScript. \N{EM DASH} Atwood's Law",
    "Don't break the Web: existing valid JavaScript on the public Web must keep working.",
    "One JavaScript (1JS): avoid versioned opt-in modes beyond `'use strict'` and ES modules.",
    "Prefer `const` by default, `let` when rebinding is needed, and leave `var` in history.",
    "Use strict equality (`===` and `!==`) so implicit type coercion never surprises you.",
    "Never block the single-threaded event loop; offload heavy CPU work to Worker threads.",
    "A Promise that is neither awaited nor `.catch()`-handled is a bug waiting to happen.",
    "Nullish coalescing (`??`) and optional chaining (`?.`) beat deeply nested truthiness checks.",
    "Objects and Arrays are compared and passed by reference, whereas primitives are compared by value.",
    "Prototypes are live delegation chains, not static class blueprints copied at instantiation.",
    "`this` depends on how a function is called, unless bound by an arrow function's lexical scope.",
    "Mutating shared state across async `await` boundaries is the root of subtle race conditions.",
    "Favour pure array transformations (`.map`, `.filter`, `.toSorted`) over in-place mutation.",
    "Explicit resource management (`using` and `AbortController`) prevents leaked handles and zombie requests.",
    "Parse, don't blindly trust external JSON payloads at runtime boundaries.",
    "Every `npm install` is a supply-chain dependency decision; keep your dependency tree lean.",
    "Write progressive, standards-based code that degrades gracefully across engines and runtimes.",
    "First make it work, then make it clear, and let the JIT compiler make it fast.",
]


class JavaScriptError(Exception):
    """A problem that should be shown to the user as-is."""


@dataclass(frozen=True, slots=True)
class TutorialTag:
    name: str
    content: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class MdnEntry:
    title: str
    slug: str
    url: str
    summary: str
    category: str

    @property
    def role_label(self) -> str:  # noqa: PLR0911
        parts = self.slug.split("/")
        if "Global_Objects" in parts:
            idx = parts.index("Global_Objects")
            depth = len(parts) - idx - 1
            return "built-in object" if depth <= 1 else "method / property"
        if "Statements" in parts:
            return "statement / declaration"
        if "Operators" in parts:
            return "expression / operator"
        if "Functions" in parts:
            return "functions reference"
        if "Errors" in parts:
            return "error reference"
        if "Guide" in parts:
            return "guide"
        return self.category or "reference"


@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    term: str
    definition: str
    url: str
    related: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WhatsNew:
    title: str
    edition: str
    year: str
    highlights: tuple[str, ...]
    proposals: tuple[tuple[str, str, str], ...]


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


def header(title: str, subtitle: str | None = None, *extra: str, thumbnail: str | None = JS_ICON) -> discord.ui.Item:
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
    """One screen of a :class:`JavaScriptView`. ``body`` is called on every render so items are always fresh."""

    body: Callable[[], list[discord.ui.Item]]
    url: str | None = None
    label: str = "Open Docs"
    colour: discord.Colour = JS_COLOUR
    links: list[tuple[str, str]] = field(default_factory=list)


class JavaScriptView(BaseLayoutView):
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


def clean_text(node: Tag | None) -> str:
    """Whitespace-normalised text of a node, without heading anchor symbols."""
    if node is None:
        return ""
    return " ".join(node.get_text(" ").split()).replace("\N{PILCROW SIGN}", "").replace("#", "").strip()


def clean_html_snippet(raw_html: str | None, limit: int = 800) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    flat = " ".join(soup.get_text(" ").split()).strip()
    return truncate(discord.utils.escape_mentions(flat), limit)


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


def extract_proposal_abstract(html: str) -> str | None:
    """Extract the overview or motivation paragraphs from a TC39 proposal README or spec page."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("article.markdown-body, main, #spec-container, body") or soup
    paragraphs: list[str] = []
    total = 0
    for p in root.find_all("p", recursive=True)[:10]:
        line = " ".join(p.get_text(" ").split()).strip()
        if not line or len(line) < 25:
            continue
        low = line.casefold()
        if low.startswith(("stage:", "champion:", "champions:", "author:", "authors:", "status:")):
            continue
        paragraphs.append(line)
        total += len(line)
        if total >= 700 or len(paragraphs) >= 3:
            break
    if not paragraphs:
        return None
    return truncate(discord.utils.escape_mentions("\n\n".join(paragraphs)), 900)


def extract_mdn_doc_section(html: str) -> tuple[str | None, str, list[str]]:
    """Extract syntax block, summary paragraphs, and documented methods/properties from an MDN HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("article.main-page-content, main, article") or soup

    signature: str | None = None
    syntax_section = root.select_one("section[aria-labelledby=syntax], section#syntax")
    code_node = (syntax_section.find("pre") if syntax_section else None) or root.select_one("pre.brush\\:js, pre.js, section pre")
    if code_node is not None:
        raw_sig = code_node.get_text().strip()
        if raw_sig:
            signature = truncate(raw_sig.replace("```", "'''"), 300)

    paragraphs: list[str] = []
    intro_scope = root.select_one("div.section-content") or root
    for p in intro_scope.find_all("p", recursive=True)[:6]:
        if p.find_parent(["div", "aside"], class_=re.compile(r"notecard|callout| warning|deprecated")):
            continue
        line = " ".join(p.get_text(" ").split()).strip()
        if line and len(line) > 20:
            paragraphs.append(line)
        if sum(len(x) for x in paragraphs) >= 900 or len(paragraphs) >= 3:
            break

    members: list[str] = []
    for dt in root.select("dl dt code, section[aria-labelledby*=methods] dt code, section[aria-labelledby*=properties] dt code")[:30]:
        label = dt.get_text().strip()
        if label and label not in members:
            members.append(label)

    body = "\n\n".join(paragraphs) if paragraphs else "*Open the MDN documentation link below to read the full specification.*"
    return signature, truncate(discord.utils.escape_mentions(body), 1100), members[:22]


def parse_mdn_search_results(data: dict[str, Any], *, js_only: bool = True) -> list[MdnEntry]:
    documents = data.get("documents") or []
    entries: list[MdnEntry] = []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        slug = str(doc.get("slug") or "")
        mdn_url = str(doc.get("mdn_url") or f"/en-US/docs/{slug}")
        if js_only and "Web/JavaScript" not in slug and "Web/API" not in slug:
            continue
        title = str(doc.get("title") or slug.rsplit("/", 1)[-1])
        summary = " ".join(str(doc.get("summary") or "").split()).strip()
        category = "JavaScript" if "Web/JavaScript" in slug else ("Web API" if "Web/API" in slug else "MDN")
        entries.append(
            MdnEntry(
                title=title,
                slug=slug,
                url=f"{MDN_BASE_URL}{mdn_url}" if mdn_url.startswith("/") else mdn_url,
                summary=truncate(discord.utils.escape_mentions(summary), 900),
                category=category,
            )
        )
    return entries


def extract_mdn_glossary(html: str, title_fallback: str, page_url: str) -> GlossaryTerm:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("article.main-page-content, main, article") or soup
    heading = clean_text(root.select_one("h1")) or title_fallback

    paragraphs: list[str] = []
    for p in root.find_all("p", recursive=True)[:5]:
        line = " ".join(p.get_text(" ").split()).strip()
        if line and len(line) > 15:
            paragraphs.append(line)
        if sum(len(x) for x in paragraphs) >= 950 or len(paragraphs) >= 3:
            break

    related: list[str] = []
    see_also = root.select_one("section[aria-labelledby=see_also], section#see_also")
    if see_also:
        for a in see_also.select("li a")[:6]:
            label = " ".join(a.get_text(" ").split()).strip()
            if label:
                related.append(label)

    definition = "\n\n".join(paragraphs) or "*Open the MDN Glossary link below for the full definition.*"
    return GlossaryTerm(
        term=heading,
        definition=truncate(discord.utils.escape_mentions(definition), 1100),
        url=page_url,
        related=tuple(related),
    )


def parse_node_api_json(data: dict[str, Any], module_name: str) -> tuple[str | None, list[str], str | None, list[tuple[str, str]]]:
    """Extract synopsis, public symbols, stability note, and version history from ``nodejs.org/api/<mod>.json``."""
    modules = data.get("modules") or []
    mod = modules[0] if modules and isinstance(modules[0], dict) else data

    desc_html = mod.get("desc") or ""
    synopsis = clean_html_snippet(desc_html, 850) or None

    stability: str | None = None
    if mod.get("stability") is not None:
        stab_num = mod.get("stability")
        stab_text = " ".join(str(mod.get("stabilityText") or "").split())
        stability = f"`{stab_num}` \N{EM DASH} {truncate(stab_text, 90)}" if stab_text else f"`{stab_num}`"

    exports: list[str] = []
    for bucket in ("classes", "methods", "properties", "events"):
        for item in mod.get(bucket) or []:
            if not isinstance(item, dict):
                continue
            raw_name = str(item.get("textRaw") or item.get("name") or "").strip()
            short = raw_name.split("(", 1)[0].removeprefix(f"{module_name}.")
            if short and short not in exports:
                exports.append(short)

    notes: list[tuple[str, str]] = []
    meta = mod.get("meta") or {}
    for added_ver in meta.get("added") or []:
        notes.append(("added", f"Added in Node.js `{added_ver}`"))  # noqa: PERF401
    for dep_ver in meta.get("deprecated") or []:
        notes.append(("deprecated", f"Deprecated since Node.js `{dep_ver}`"))  # noqa: PERF401
    for change in (meta.get("changes") or [])[:6]:
        if isinstance(change, dict):
            ver = change.get("version")
            ver_str = ", ".join(ver) if isinstance(ver, list) else str(ver or "")
            desc = clean_html_snippet(change.get("description"), 220)
            if ver_str or desc:
                notes.append(("changed", f"**Node.js `{ver_str}`**: {desc}"))

    return synopsis, exports[:24], stability, notes[:8]


def find_node_symbol_history(data: dict[str, Any], member_query: str | None) -> tuple[str, list[tuple[str, str]]]:  # noqa: PLR0912
    """Find version history for a Node.js module or a specific method/class inside it."""
    modules = data.get("modules") or []
    mod = modules[0] if modules and isinstance(modules[0], dict) else data
    mod_name = str(mod.get("name") or "node")

    target_obj: dict[str, Any] = mod
    resolved_label = f"node:{mod_name}"
    if member_query:
        q_low = member_query.casefold()
        candidates: list[dict[str, Any]] = []
        for bucket in ("methods", "classes", "properties"):
            for item in mod.get(bucket) or []:
                if isinstance(item, dict):
                    candidates.append(item)
                    for sub_bucket in ("methods", "classMethods", "properties"):
                        for sub in item.get(sub_bucket) or []:
                            if isinstance(sub, dict):
                                candidates.append(sub)  # noqa: PERF401
        for item in candidates:
            name = str(item.get("name") or "").casefold()
            raw = str(item.get("textRaw") or "").casefold()
            if name == q_low or q_low in raw:
                target_obj = item
                resolved_label = str(item.get("textRaw") or f"{mod_name}.{item.get('name')}")
                break

    meta = target_obj.get("meta") or {}
    notes: list[tuple[str, str]] = []
    for added_ver in meta.get("added") or []:
        notes.append(("added", f"Added in Node.js `{added_ver}`."))  # noqa: PERF401
    for dep_ver in meta.get("deprecated") or []:
        notes.append(("deprecated", f"Deprecated in Node.js `{dep_ver}`."))  # noqa: PERF401
    for change in (meta.get("changes") or [])[:6]:
        if isinstance(change, dict):
            ver = change.get("version")
            ver_str = ", ".join(ver) if isinstance(ver, list) else str(ver or "")
            desc = clean_html_snippet(change.get("description"), 240)
            if ver_str or desc:
                notes.append(("changed", f"`{ver_str}` \N{EM DASH} {desc}"))
    return resolved_label, notes[:8]


def extract_mdn_compat_notes(html: str) -> list[tuple[str, str]]:
    """Extract specification, baseline, or deprecation callouts from an MDN page."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("article.main-page-content, main, article") or soup
    notes: list[tuple[str, str]] = []

    for card in root.select("div.notecard.deprecated, div.notecard.warning, div.notecard.experimental")[:4]:
        classes = card.get("class") or []
        kind = "deprecated" if "deprecated" in classes else "changed"
        body = clean_text(card)
        if body:
            notes.append((kind, truncate(discord.utils.escape_mentions(body), 300)))

    baseline = root.select_one("details.baseline-indicator, div.baseline-indicator")
    if baseline:
        summary_text = clean_text(baseline.find("summary") or baseline)
        if summary_text:
            notes.insert(0, ("added", truncate(discord.utils.escape_mentions(summary_text), 260)))

    spec_links = [clean_text(a) for a in root.select("section#specifications a, table.standard-table a") if clean_text(a)]
    if spec_links:
        notes.append(("changed", f"Specification: {truncate(', '.join(dict.fromkeys(spec_links[:3])), 260)}"))

    return notes[:8]


def tutorial_items(name: str, content: str, score: float | None = None) -> list[discord.ui.Item]:
    subtitle = "JavaScript Tutorial" + (f"{DOT}match {score:.0f}%" if score is not None and score < 100 else "")
    return collect(
        header(f"Tutorial: `{name}`", subtitle),
        discord.ui.Separator(),
        text(truncate(content, BODY_LIMIT)),
    )


def tutorial_list_items(names: Sequence[str], chunk: Sequence[str], total: int) -> list[discord.ui.Item]:
    subtitle = f"{total} tutorial{'' if total == 1 else 's'} available{DOT}use `js tutorial <name>`"
    listing = "\n".join(f"\N{BULLET} `{name}`" for name in chunk)
    return collect(
        header("Available JavaScript Tutorials", subtitle),
        discord.ui.Separator(),
        text(listing or "*No tutorials loaded.*"),
        text(f"-# Quick lookup: {pack(names, 400)}"),
    )


def tc39_items(proposal: dict[str, Any], abstract: str | None) -> list[discord.ui.Item]:
    name = safe(proposal.get("name"), 160) or "Unnamed TC39 Proposal"
    stage_raw = str(proposal.get("stage", "?"))
    stage_label = TC39_STAGE_LABELS.get(stage_raw, f"Stage {stage_raw}")
    edition = proposal.get("edition")
    edition_label = f"ES{edition}" if edition and not str(edition).upper().startswith("ES") else (str(edition) if edition else None)

    subtitle_parts = ["TC39 Proposal", stage_label]
    if edition_label:
        subtitle_parts.append(edition_label)

    url = proposal.get("url") or proposal.get("link") or TC39_REPO_URL
    top = header(
        f"[{name}]({url})",
        DOT.join(subtitle_parts),
    )

    authors = proposal.get("authors") or []
    champions = proposal.get("champions") or []
    authors_str = ", ".join(safe(str(a), 50) for a in authors[:5]) if isinstance(authors, list) else safe(str(authors), 140)
    champions_str = ", ".join(safe(str(c), 50) for c in champions[:5]) if isinstance(champions, list) else safe(str(champions), 140)
    rationale = safe(proposal.get("rationale"), 180) if proposal.get("rationale") else None
    presented = proposal.get("last_presented") or proposal.get("lastPresented")

    body = abstract or rationale or "*No overview preview available. Select **Open Proposal** below to read the specification and explainer.*"
    details = facts(
        ("Stage", f"`{stage_label}`"),
        ("Target Edition", f"`{edition_label}`" if edition_label else None),
        ("Author(s)", authors_str or None),
        ("Champion(s)", champions_str or None),
        ("Last Presented", safe(str(presented), 40) if presented else None),
        ("Has Specification", "`Yes`" if proposal.get("has_specification") or proposal.get("spec") else None),
        ("Test262 Suite", "`Available`" if proposal.get("tests") else None),
    )
    return collect(top, discord.ui.Separator(), text(body), discord.ui.Separator(), details)


def mdn_doc_items(
    entry: MdnEntry,
    signature: str | None,
    description: str,
    members: list[str],
    related: list[MdnEntry],
) -> list[discord.ui.Item]:
    top = header(
        f"[`{entry.title}`]({entry.url})",
        f"MDN Web Docs{DOT}{entry.role_label}",
    )
    sig_block = text(f"```js\n{signature}\n```") if signature else None
    member_block = text(f"**Documented Methods & Properties**\n{pack(members, 600)}") if members else None

    related_lines = [f"\N{BULLET} [`{rel.title}`]({rel.url}) \N{EM DASH} *{rel.role_label}*" for rel in related[:5] if rel.url != entry.url]
    related_block = text("**Related MDN Entries**\n" + "\n".join(related_lines)) if related_lines else None

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
    stability: str | None,
) -> list[discord.ui.Item]:
    category = curated.category if curated else "Node.js Built-in Module"
    top = header(
        f"[`node:{name}`]({doc_url})",
        f"Node.js Standard Library{DOT}{category}",
        synopsis,
    )

    highlights = list(curated.highlights) if curated and curated.highlights else exports[:18]
    highlights_block = text(f"**Key Exports & Symbols**\n{pack(highlights, 700)}") if highlights else None
    example_block = text(f"**Example**\n```js\n{curated.example}\n```") if curated and curated.example else None

    source_label = curated.source_path if curated and curated.source_path else f"lib/{name}.js"
    details = facts(
        ("ESM Import", f"`import * as {name} from 'node:{name}';`"),
        ("CommonJS", f"`const {name} = require('node:{name}');`"),
        ("Stability", stability),
        ("Node.js Source", f"[`{source_label}`]({source_url})" if source_url else None),
    )
    return collect(
        top,
        discord.ui.Separator(),
        highlights_block,
        example_block,
        discord.ui.Separator(),
        details,
    )


def generate_node_release_info(cycles: list[dict[str, Any]], *, active_view: bool) -> list[discord.ui.Item]:
    now_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    heading = "Supported Node.js Releases & ECMAScript Editions" if active_view else "Historical / End-of-Life Node.js Releases"
    subtitle = f"ECMAScript Standard: `ES2026` (ECMA-262 17th Ed.){DOT}Data from endoflife.date & nodejs.org"

    lines: list[str] = []
    for item in cycles:
        cycle = item.get("cycle", "?")
        latest = item.get("latest", cycle)
        codename = item.get("lts")
        released = item.get("releaseDate")
        eol = item.get("eol")
        support = item.get("support")

        is_eol = isinstance(eol, str) and eol <= now_str
        is_active = (isinstance(support, str) and support > now_str) or support is True
        if is_eol:
            badge = "\N{LARGE RED CIRCLE} EOL"
        elif is_active and codename:
            badge = "\N{LARGE GREEN CIRCLE} Active LTS"
        elif is_active:
            badge = "\N{LARGE GREEN CIRCLE} Current"
        else:
            badge = "\N{LARGE YELLOW CIRCLE} Maintenance LTS"

        lts_tag = f" *({codename})*" if isinstance(codename, str) and codename else ""
        eol_str = when(eol) if isinstance(eol, str) else ("Active" if not eol else str(eol))
        rel_str = when(released, "D") if isinstance(released, str) else "TBD"
        lines.append(f"**Node.js {cycle}**{lts_tag} (`v{latest}`){DOT}{badge}\n-# Released: {rel_str}{DOT}End of life: {eol_str or 'TBD'}")

    return collect(
        header(heading, subtitle),
        discord.ui.Separator(),
        text("\n\n".join(lines) if lines else "*No release cycles found.*"),
        text(
            "-# Even-numbered Node.js majors enter Active LTS every October for 12 months, followed by 18 months of Maintenance LTS (30 months total)."
        ),
    )


def error_items(info: ErrorInfo, proto_chain: str, doc_url: str) -> list[discord.ui.Item]:
    top = header(
        f"[`{info.name}`]({doc_url})",
        f"JavaScript Error{DOT}{info.category}",
        info.summary,
    )
    causes = "\n".join(f"\N{BULLET} {cause}" for cause in info.causes)
    details = facts(
        ("Prototype Chain", proto_chain),
        ("How to Fix", info.fix),
    )
    return collect(
        top,
        discord.ui.Separator(),
        text(f"**Common Causes**\n{causes}"),
        details,
        text(f"**Example**\n```js\n{info.example}\n```"),
    )


def operator_items(info: OperatorInfo, doc_url: str) -> list[discord.ui.Item]:
    top = header(
        f"[`{info.symbol}` \N{EM DASH} {info.name}]({doc_url})",
        f"JavaScript Operator{DOT}{info.category}",
        info.summary,
    )
    behavior = getattr(info, "dunder", None) or getattr(info, "behavior", None)
    spec_hook = getattr(info, "operator_func", None) or getattr(info, "spec_hook", None)
    details = facts(
        ("Symbol / Syntax", f"`{info.symbol}`"),
        ("Precedence", info.precedence),
        ("Coercion / Protocol", f"`{behavior}`" if behavior else None),
        ("Reflect / Spec Hook", f"`{spec_hook}`" if spec_hook else None),
        ("Aliases", ", ".join(f"`{a}`" for a in info.aliases[:6]) if info.aliases else None),
    )
    return collect(
        top,
        discord.ui.Separator(),
        details,
        discord.ui.Separator(),
        text(f"**Examples**\n```js\n{info.example}\n```"),
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
        f"JavaScript Built-in{DOT}{kind}",
    )
    sig_block = text(f"```js\n{signature_str}\n```") if signature_str else None
    methods_block = text(f"**Static & Prototype Methods / Properties**\n{pack(methods, 650)}") if methods else None
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
        f"JavaScript / V8 Complexity{DOT}{info.category}",
        info.summary,
    )
    metrics = facts(
        ("Best Time", f"`{info.best}`"),
        ("Average Time", f"`{info.average}`"),
        ("Worst Time", f"`{info.worst}`"),
        ("Space Complexity", f"`{info.space}`"),
    )
    notes_block = text("**Operation Breakdown & V8 Engine Notes**\n" + "\n".join(f"\N{BULLET} {n}" for n in info.notes))
    example_block = text(f"**Idiomatic JavaScript**\n```js\n{info.example}\n```")
    return collect(
        top,
        discord.ui.Separator(),
        metrics,
        discord.ui.Separator(),
        notes_block,
        example_block,
    )


# fmt: off
FALLBACK_NODE_CYCLES: list[dict[str, Any]] = [
    {"cycle": "26", "releaseDate": "2026-04-21", "eol": "2029-04-30", "latest": "26.12.1", "support": "2027-10-20", "lts": "Oxide"},
    {"cycle": "25", "releaseDate": "2025-10-21", "eol": "2026-06-01", "latest": "25.9.0",  "support": "2026-04-01", "lts": False},
    {"cycle": "24", "releaseDate": "2025-04-22", "eol": "2028-04-30", "latest": "24.11.0", "support": "2026-10-20", "lts": "Krypton"},
    {"cycle": "23", "releaseDate": "2024-10-16", "eol": "2025-06-01", "latest": "23.11.0", "support": "2025-04-01", "lts": False},
    {"cycle": "22", "releaseDate": "2024-04-24", "eol": "2027-04-30", "latest": "22.15.0", "support": "2025-10-21", "lts": "Jod"},
    {"cycle": "21", "releaseDate": "2023-10-17", "eol": "2024-06-01", "latest": "21.7.3",  "support": "2024-04-01", "lts": False},
    {"cycle": "20", "releaseDate": "2023-04-18", "eol": "2026-04-30", "latest": "20.19.0", "support": "2024-10-22", "lts": "Iron"},
    {"cycle": "18", "releaseDate": "2022-04-19", "eol": "2025-04-30", "latest": "18.20.8", "support": "2023-10-18", "lts": "Hydrogen"},
    {"cycle": "16", "releaseDate": "2021-04-20", "eol": "2023-09-11", "latest": "16.20.2", "support": "2022-10-18", "lts": "Gallium"},
    {"cycle": "14", "releaseDate": "2020-04-21", "eol": "2023-04-30", "latest": "14.21.3", "support": "2021-10-19", "lts": "Fermium"},
    {"cycle": "12", "releaseDate": "2019-04-23", "eol": "2022-04-30", "latest": "12.22.12", "support": "2020-10-20", "lts": "Erbium"},
]

CURATED_ES_HIGHLIGHTS: dict[str, tuple[str, ...]] = {
    "2026": (
        "Explicit Resource Management (`using` and `await using` declarations with `Symbol.dispose`)",
        "`Error.isError()` reliable cross-realm error checking without `instanceof` pitfalls",
        "`Array.fromAsync()` for materializing async iterables and promises into arrays",
        "`RegExp.escape()` for safely escaping arbitrary user strings inside regular expressions",
        "`Atomics.pause()` CPU hint for spinlock waiting in shared-memory worker threads",
    ),
    "2025": (
        "Iterator Helpers (`Iterator.prototype.map`, `.filter`, `.take`, `.drop`, `.toArray`)",
        "New `Set` mathematical methods (`.union`, `.intersection`, `.difference`, `.symmetricDifference`, `.isSubsetOf`)",
        "Import Attributes (`import data from './config.json' with { type: 'json' }`)",
        "`Promise.try()` for uniformly wrapping synchronous and asynchronous callbacks",
        "Duplicate named capturing groups and inline pattern modifiers (`(?i:...)`) in `RegExp`",
        "`Float16Array` typed array and `DataView.prototype.getFloat16` / `Math.f16round`",
    ),
    "2024": (
        "`Object.groupBy()` and `Map.groupBy()` for grouping iterables without external libraries",
        "`Promise.withResolvers()` for extracting `{ promise, resolve, reject }` cleanly",
        "`RegExp` `/v` (`unicodeSets`) flag with set notation and string literal properties",
        "`String.prototype.isWellFormed()` and `.toWellFormed()` for lone surrogate handling",
        "`Atomics.waitAsync()` for non-blocking shared memory synchronization",
        "Resizable `ArrayBuffer` and growable `SharedArrayBuffer` in-place",
    ),
    "2023": (
        "Change Array by Copy (`.toSorted()`, `.toReversed()`, `.toSpliced()`, `.with()`)",
        "Array find from last (`.findLast()` and `.findLastIndex()`)",
        "Hashbang (`#!`) grammar support at the start of executable JS scripts",
        "Symbols as `WeakMap` and `WeakSet` keys",
    ),
    "2022": (
        "Top-level `await` in ECMAScript modules without an async IIFE wrapper",
        "Public and private class fields (`#field`), private methods, and `static` initialization blocks",
        "`Object.hasOwn(obj, prop)` as a safe replacement for `Object.prototype.hasOwnProperty.call`",
        "`.at(-1)` negative indexing on `Array`, `String`, and `TypedArray`",
        "Error `.cause` property (`new Error('Failed', { cause: err })`) for chaining exceptions",
    ),
    "2021": (
        "`String.prototype.replaceAll()` without requiring global regex flags",
        "`Promise.any()` and `AggregateError`",
        "Logical assignment operators (`??=`, `&&=`, `||=`)",
        "Numeric separators (`1_000_000`) and `WeakRef` / `FinalizationRegistry`",
    ),
    "2020": (
        "Optional chaining (`?.`) and Nullish coalescing (`??`) operators",
        "`BigInt` arbitrary-precision integers (`123n`)",
        "`Promise.allSettled()` and `globalThis` universal global reference",
        "Dynamic `import()` expressions and `import.meta`",
    ),
}
# fmt: on


def cycle_phase(cycle: dict[str, Any]) -> str:
    today = today_iso()
    released, eol, support, lts = cycle.get("releaseDate"), cycle.get("eol"), cycle.get("support"), cycle.get("lts")
    if isinstance(released, str) and released > today:
        return "prerelease"
    if isinstance(eol, str) and eol <= today:
        return "end-of-life"
    if (isinstance(support, str) and support > today) or support is True:
        return "active-lts" if lts else "current"
    return "maintenance-lts"


def latest_released_cycle(cycles: Sequence[dict[str, Any]]) -> dict[str, Any]:
    today = today_iso()
    released = [c for c in cycles if isinstance(c.get("releaseDate"), str) and c["releaseDate"] <= today]
    lts_released = [c for c in released if c.get("lts") and cycle_phase(c) != "end-of-life"]
    if lts_released:
        return max(lts_released, key=lambda c: int(str(c.get("cycle", "0"))))
    return max(released, key=lambda c: c["releaseDate"]) if released else cycles[0]


def glossary_items(entry: GlossaryTerm) -> list[discord.ui.Item]:
    related = ", ".join(f"`{r}`" for r in entry.related[:5])
    return collect(
        header(f"[{safe(entry.term, 80)}]({entry.url})", "MDN Web Docs Glossary"),
        discord.ui.Separator(),
        text(entry.definition),
        facts(("Related terms", related or None)),
    )


def keyword_items(name: str, info: KeywordInfo, *, contextual: bool, doc_url: str) -> list[discord.ui.Item]:
    kind_label = "JavaScript Contextual Keyword" if contextual else "JavaScript Reserved Keyword"
    return collect(
        header(f"[`{name}`]({doc_url})", kind_label, info.summary),
        discord.ui.Separator(),
        text(f"**Example**\n```js\n{info.example}\n```"),
        facts(
            ("Introduced", f"{info.since}" if info.since else "ES1 / Standard ECMAScript"),
            ("Grammar category", "Contextual / Strict-mode identifier" if contextual else "Lexical reserved keyword"),
        ),
    )


def symbol_items(info: SymbolInfo, doc_url: str, see_also: str | None) -> list[discord.ui.Item]:
    return collect(
        header(f"[`{info.name}`]({doc_url})", f"ECMAScript Protocol / Well-Known Symbol{DOT}{info.group}", info.summary),
        discord.ui.Separator(),
        facts(
            ("Property Key / Signature", f"`{info.signature}`"),
            ("Invoked by", info.called_by),
            ("Protocol / Backs", info.backs or None),
            ("See also", see_also),
        ),
        discord.ui.Separator(),
        text(f"**Example**\n```js\n{info.example}\n```"),
    )


def whatsnew_highlight_items(wn: WhatsNew, url: str) -> list[discord.ui.Item]:
    listing = "\n".join(f"\N{BULLET} {line}" for line in wn.highlights) or "*See page 2 or open the specification link below for finished proposals.*"
    return collect(
        header(f"[{safe(wn.title, 90)}]({url})", f"ECMAScript Release Highlights{DOT}{wn.edition}"),
        discord.ui.Separator(),
        text(listing),
        facts(("Standard", "`ECMA-262`"), ("Ratification Year", f"`{wn.year}`"), ("Finished Proposals", f"`{len(wn.proposals)}` in TC39 dataset")),
    )


def whatsnew_detail_items(wn: WhatsNew, url: str) -> list[discord.ui.Item]:
    lines = [
        f"\N{BULLET} [{safe(name, 75)}]({prop_url})" + (f" \N{EM DASH} *{safe(authors, 45)}*" if authors else "")
        for name, prop_url, authors in wn.proposals[:14]
    ]
    return collect(
        header(f"{wn.edition}: Stage 4 Finished Proposals", f"TC39 Proposals included in {wn.edition}"),
        discord.ui.Separator(),
        text("\n".join(lines) if lines else "*No individual proposal records listed for this edition.*"),
    )


def since_items(title: str, subtitle: str, url: str, notes: list[tuple[str, str]]) -> list[discord.ui.Item]:
    if notes:
        lines = "\n\n".join(f"**{NOTE_LABELS.get(kind, kind.title())}**\n{body}" for kind, body in notes)
    else:
        lines = "*No specific version-added or deprecation callouts were found on this page; it has likely been part of standard ECMAScript since ES5/ES6.*"
    return collect(
        header(f"[`{title}`]({url})", f"Compatibility & Version History{DOT}{subtitle}"),
        discord.ui.Separator(),
        text(lines),
    )


def npm_Author(data: dict[str, Any], ver_data: dict[str, Any]) -> str | None:
    author = ver_data.get("author") or data.get("author")
    if isinstance(author, dict) and author.get("name"):
        return safe(str(author["name"]), 80)
    if isinstance(author, str) and author.strip():
        return safe(author, 80)
    maintainers = ver_data.get("maintainers") or data.get("maintainers") or []
    if maintainers and isinstance(maintainers[0], dict):
        return safe(str(maintainers[0].get("name") or ""), 80)
    return None


def npm_links(data: dict[str, Any], ver_data: dict[str, Any], page_url: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    homepage = ver_data.get("homepage") or data.get("homepage")
    if isinstance(homepage, str) and valid_url(homepage) and homepage != page_url:
        links.append(("Homepage", homepage))

    repo = ver_data.get("repository") or data.get("repository")
    repo_url = repo.get("url") if isinstance(repo, dict) else (repo if isinstance(repo, str) else None)
    if isinstance(repo_url, str):
        clean_repo = re.sub(r"^git\+", "", repo_url).removesuffix(".git")
        if clean_repo.startswith("git://github.com/"):
            clean_repo = "https://github.com/" + clean_repo.removeprefix("git://github.com/")
        if valid_url(clean_repo) and clean_repo not in {u for _, u in links}:
            links.append(("Repository", clean_repo))

    bugs = ver_data.get("bugs") or data.get("bugs")
    bugs_url = bugs.get("url") if isinstance(bugs, dict) else (bugs if isinstance(bugs, str) else None)
    if isinstance(bugs_url, str) and valid_url(bugs_url) and bugs_url not in {u for _, u in links}:
        links.append(("Issues", bugs_url))

    return links[:4]


def npm_items(data: dict[str, Any], version: str) -> list[discord.ui.Item]:
    name = safe(str(data.get("name") or ""), 80)
    versions_map = data.get("versions") or {}
    ver_data = versions_map.get(version) if isinstance(versions_map, dict) else data
    if not isinstance(ver_data, dict):
        ver_data = data

    page_url = f"{NPM_PACKAGE_URL}/{name}"
    time_map = data.get("time") if isinstance(data.get("time"), dict) else {}
    released = time_map.get(version) if isinstance(time_map, dict) else None

    engines = ver_data.get("engines")
    node_engine = engines.get("node") if isinstance(engines, dict) else None

    pkg_type = ver_data.get("type")
    has_esm = pkg_type == "module" or bool(ver_data.get("module")) or "import" in str(ver_data.get("exports") or "")
    has_cjs = pkg_type != "module" or "require" in str(ver_data.get("exports") or "") or bool(ver_data.get("main"))
    module_kind = "ESM + CJS (Dual)" if (has_esm and has_cjs) else ("ESM (`type: module`)" if has_esm else "CommonJS")

    has_types = bool(ver_data.get("types") or ver_data.get("typings")) or ".d.ts" in str(ver_data.get("exports") or "")
    deps = list((ver_data.get("dependencies") or {}).keys()) if isinstance(ver_data.get("dependencies"), dict) else []
    dist = ver_data.get("dist") if isinstance(ver_data.get("dist"), dict) else {}
    unpacked = (dist or {}).get("unpackedSize")
    size_str = f"`{unpacked / 1024:.1f} KB`" if isinstance(unpacked, (int, float)) else None

    raw_license = ver_data.get("license") or data.get("license")
    license_str = safe(raw_license.get("type") if isinstance(raw_license, dict) else str(raw_license or ""), 60) or None

    warnings: list[str] = []
    if ver_data.get("deprecated"):
        warnings.append(f"\N{WARNING SIGN} **Deprecated**: {safe(str(ver_data.get('deprecated')), 160)}")

    return collect(
        header(f"[{name}]({page_url})", f"npm Registry{DOT}v{safe(version, 40)}", safe(ver_data.get("description") or data.get("description"), 220)),
        discord.ui.Separator(),
        text("\n".join(warnings)) if warnings else None,
        facts(
            ("Version", f"`{safe(version, 40)}`"),
            ("Published", dated(released)),
            ("Node Engine", f"`{safe(str(node_engine), 40)}`" if node_engine else None),
            ("Module Format", f"`{module_kind}`"),
            ("TypeScript", "`Bundled (.d.ts)`" if has_types else None),
            ("License", license_str),
            ("Maintainer", npm_Author(data, ver_data)),
            ("Unpacked Size", size_str),
            ("Dependencies", f"{len(deps)}: {pack(deps[:10], 400)}" if deps else "0 (zero dependencies)"),
        ),
        discord.ui.Separator(),
        text(f"**Install**\n```sh\nnpm install {name}\npnpm add {name}\nbun add {name}\n```"),
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
        text("-# Source: National Vulnerability Database. Newest first. Check nodejs.org/en/blog/vulnerability for security releases."),
    )


def download_items(version: str, cycle: dict[str, Any] | None, release_url: str, found: Sequence[str]) -> list[discord.ui.Item]:
    phase = cycle_phase(cycle) if cycle else "unknown"
    notes = {
        "active-lts": "Active LTS branch: recommended for most production deployments.",
        "current": "Current branch: includes the latest V8 and Node.js features.",
        "maintenance-lts": "Maintenance LTS: receives critical bugs and security patches only.",
        "end-of-life": "**End of life.** No more security updates are published; upgrade to an Active LTS series.",
    }
    codename = cycle.get("lts") if cycle else None
    series_label = (
        f"`v{(cycle or {}).get('cycle')}` ({codename} LTS)"
        if isinstance(codename, str) and codename
        else (f"`v{cycle.get('cycle')}`" if cycle else None)
    )
    return collect(
        header(f"[Node.js v{version}]({release_url})", f"Download{DOT}{phase}"),
        discord.ui.Separator(),
        facts(
            ("Series", series_label),
            ("Series released", dated(cycle.get("releaseDate")) if cycle else None),
            ("End of life", dated(cycle.get("eol")) if cycle and isinstance(cycle.get("eol"), str) else None),
            ("Available builds", ", ".join(found) if found else "see the distribution directory"),
        ),
        text(notes.get(phase, "")) if notes.get(phase) else None,
        text(f"-# Version managers: `fnm use {version}`{DOT}`nvm install {version}`{DOT}`volta install node@{version}`"),
    )


def countdown_items(milestones: Sequence[tuple[str, str, str]]) -> list[discord.ui.Item]:
    today = today_iso()
    upcoming = [m for m in milestones if m[1] >= today]

    def line(ver: str, iso: str, kind: str) -> str:
        return f"\N{BULLET} **Node.js {safe(ver, 20)}** ({safe(kind, 40)}) \N{EM DASH} {when(iso, 'D')} ({when(iso)})"

    nxt = (
        f"**Next milestone**: Node.js **{safe(upcoming[0][0], 20)}** {safe(upcoming[0][2], 40)} {when(upcoming[0][1])} ({when(upcoming[0][1], 'D')})"
        if upcoming
        else "**No upcoming milestones** are listed in the schedule."
    )
    return collect(
        header("JavaScript & Node.js Release Countdown", "Node.js Release WG & TC39 Annual Schedule"),
        discord.ui.Separator(),
        text(nxt),
        discord.ui.Separator() if len(upcoming) > 1 else None,
        text("**Coming up**\n" + "\n".join(line(*m) for m in upcoming[1:8])) if len(upcoming) > 1 else None,
        text("-# TC39 ratifies a new ECMAScript standard every June; Node.js cuts a new major release every April and October."),
    )


def source_items(info: SourceInfo) -> list[discord.ui.Item]:
    return collect(
        header(f"[`{info.name}`]({info.url})", f"Node.js Core Source{DOT}{info.kind}", safe(info.doc, 260)),
        discord.ui.Separator(),
        text(f"```js\n{info.signature}\n```") if info.signature else None,
        facts(
            ("File", f"`{info.relative_path}`"),
            ("Lines", f"`{info.start}\N{EN DASH}{info.end}` ({info.end - info.start + 1} lines)"),
            ("Repository", "`nodejs/node` (`main`)"),
        ),
        text(f"**Preview**\n```js\n{info.preview}\n```"),
    )


def gotcha_items(info: GotchaInfo) -> list[discord.ui.Item]:
    return collect(
        header(info.title, "JavaScript Gotcha", info.summary),
        discord.ui.Separator(),
        text(f"**\N{CROSS MARK} The trap**\n```js\n{info.bad}\n```"),
        text(f"**\N{WHITE HEAVY CHECK MARK} The fix**\n```js\n{info.good}\n```"),
        facts(("Why", info.why)),
    )


def idiom_items(info: IdiomInfo) -> list[discord.ui.Item]:
    return collect(
        header(info.title, f"JavaScript Idiom{DOT}{info.since}+" if info.since else "JavaScript Idiom", info.summary),
        discord.ui.Separator(),
        text(f"```js\n{info.example}\n```"),
        facts(("Note", info.notes or None)),
    )


def typing_items(info: TypingInfo, doc_url: str) -> list[discord.ui.Item]:
    return collect(
        header(
            f"[{info.title}]({doc_url})", f"TypeScript / JSDoc Typing{DOT}{info.since}+" if info.since else "TypeScript / JSDoc Typing", info.summary
        ),
        discord.ui.Separator(),
        text(f"```ts\n{info.example}\n```"),
    )


def topic_list_items(title: str, command: str, entries: Sequence[tuple[str, str]]) -> list[discord.ui.Item]:
    listing = "\n".join(f"\N{BULLET} `{key}` \N{EM DASH} {safe(name, 70)}" for key, name in entries)
    return collect(
        header(title, f"{len(entries)} topics{DOT}use `{command} <topic>`"),
        discord.ui.Separator(),
        text(listing),
    )


def zen_items() -> list[discord.ui.Item]:
    lines = "\n".join(f"\N{BULLET} {line}" for line in JS_LAWS_LINES)
    return collect(
        header("The Laws & Principles of JavaScript", f"{len(JS_LAWS_LINES)} aphorisms{DOT}TC39, Brendan Eich & Atwood's Law"),
        discord.ui.Separator(),
        text(lines),
    )


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


def parse_node_schedule(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return ``[(version, 'YYYY-MM-DD', milestone_label)]`` from Node.js Release ``schedule.json``."""
    milestones: list[tuple[str, str, str]] = []
    labels = {
        "start": "Initial Release",
        "lts": "Enters Active LTS",
        "maintenance": "Enters Maintenance LTS",
        "end": "End of Life (EOL)",
    }
    for ver, info in data.items():
        if not isinstance(info, dict):
            continue
        codename = f" ({info['codename']})" if info.get("codename") else ""
        for field_key, label in labels.items():
            date_str = info.get(field_key)
            if isinstance(date_str, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                milestones.append((f"{ver}{codename}", date_str, label))
    milestones.sort(key=lambda item: item[1])
    return milestones


class JavaScript(commands.Cog):
    """JavaScript & ECMAScript tutorials, TC39 proposals, MDN docs, Node.js stdlib, versions, errors, operators, built-ins, and complexity."""

    help_emoji = "\N{HIGH VOLTAGE SIGN}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._js_tags: dict[str, frontmatter.Post] = {}

        self._tc39_cache: tuple[float, list[dict[str, Any]]] | None = None
        self._cache_lock = asyncio.Lock()

        self._cve_cache: dict[str, tuple[float, list[CveRecord]]] = {}
        self._cycles_cache: tuple[float, list[dict[str, Any]]] | None = None
        self._glossary_cache: dict[str, GlossaryTerm] = {}

    @property
    def js_tags(self) -> dict[str, frontmatter.Post]:
        if self._js_tags:
            return self._js_tags

        tags_path = pathlib.Path("assets/javascript_tags")
        if tags_path.exists():
            for tag_file in tags_path.glob("*.md"):
                with tag_file.open(encoding="utf-8") as file:
                    post = frontmatter.load(file)
                    tag_name = tag_file.stem
                    self._js_tags[tag_name] = post

        return self._js_tags

    async def fetch_bytes(self, url: str, *, missing: str = "JavaScript documentation could not find that.") -> bytes:
        headers = {"User-Agent": USER_AGENT}
        try:
            async with self.bot.http_session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 404:
                    raise JavaScriptError(missing)
                if response.status >= 400:
                    msg = f"Upstream server returned HTTP {response.status}."
                    raise JavaScriptError(msg)
                return await response.read()
        except (TimeoutError, aiohttp.ClientError) as error:
            msg = "Could not reach JavaScript documentation servers right now. Try again in a moment."
            raise JavaScriptError(msg) from error

    async def fetch_json(
        self, url: str, *, params: dict[str, Any] | None = None, missing: str = "Requested JavaScript resource was not found."
    ) -> Any:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            async with self.bot.http_session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 404:
                    raise JavaScriptError(missing)
                if response.status >= 400:
                    msg = f"Upstream server returned HTTP {response.status}."
                    raise JavaScriptError(msg)
                return await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as error:
            msg = "Could not fetch data from JavaScript servers right now. Try again in a moment."
            raise JavaScriptError(msg) from error

    async def optional_text(self, url: str) -> str | None:
        try:
            raw = await self.fetch_bytes(url)
            return raw.decode("utf-8", "replace")
        except JavaScriptError:
            return None

    async def optional_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any | None:
        try:
            return await self.fetch_json(url, params=params)
        except JavaScriptError:
            return None

    async def get_tc39_proposals(self) -> list[dict[str, Any]]:
        if self._tc39_cache and time.monotonic() - self._tc39_cache[0] < CACHE_TTL:
            return self._tc39_cache[1]
        async with self._cache_lock:
            if self._tc39_cache and time.monotonic() - self._tc39_cache[0] < CACHE_TTL:
                return self._tc39_cache[1]
            data = await self.optional_json(TC39_PROPOSALS_URL)
            if not isinstance(data, list):
                data = await self.fetch_json(TC39_PROPOSALS_FALLBACK_URL, missing="Could not load the TC39 proposals dataset.")
            if not isinstance(data, list) or not data:
                msg = "Received an unexpected TC39 proposals payload."
                raise JavaScriptError(msg)
            proposals = [p for p in data if isinstance(p, dict)]
            self._tc39_cache = (time.monotonic(), proposals)
            return proposals

    async def search_mdn(self, query: str, *, js_only: bool = True) -> list[MdnEntry]:
        data = await self.fetch_json(
            MDN_SEARCH_API_URL,
            params={"q": query, "locale": "en-US"},
            missing="Could not query MDN Web Docs search.",
        )
        if not isinstance(data, dict):
            return []
        entries = await asyncio.to_thread(parse_mdn_search_results, data, js_only=js_only)
        if not entries and js_only:
            entries = await asyncio.to_thread(parse_mdn_search_results, data, js_only=False)
        return entries

    async def dispatch_view(self, ctx: commands.Context[Bot], producer: Awaitable[JavaScriptView]) -> discord.Message:
        """Await the view, then send it. Any :class:`JavaScriptError` becomes an error notice instead."""
        none = discord.AllowedMentions.none()
        async with ctx.typing():
            try:
                view = await producer
            except JavaScriptError as error:
                return await ctx.reply(view=NoticeLayout.error(str(error), title="JavaScript"), allowed_mentions=none)

        message = await ctx.reply(view=view, allowed_mentions=none)
        view.message = message
        return message

    @staticmethod
    def single(ctx: commands.Context[Bot], page: Page) -> JavaScriptView:
        return JavaScriptView(ctx.author, [page])

    @commands.group(
        name="javascript",
        aliases=["js", "ecmascript", "es", "js-tutorial", "jstut"],
        invoke_without_command=True,
        extras={
            "examples": [
                "js closures",
                "js-tutorial promises",
                "js list",
                "js error TypeError",
                "js operator ??",
                "js builtin Promise",
                "js complexity map",
            ]
        },
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def javascript(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str | None = commands.parameter(default=None, description="The tutorial to search for."),
    ) -> discord.Message | None:
        """Search for a JavaScript tutorial or invoke a JavaScript / ECMAScript / Node.js reference subcommand."""
        if not text:
            return await ctx.send_help(ctx.command)
        return await self.dispatch_view(ctx, self.fetch_java_script_tutorial(ctx, text))

    @javascript.command(
        name="tutorial",
        aliases=["tut"],
        extras={"examples": ["js tutorial promises", "js tutorial event-loop"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_tutorial(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str = commands.parameter(description="The tutorial to search for."),
    ) -> discord.Message:
        """Search for a JavaScript tutorial."""
        return await self.dispatch_view(ctx, self.fetch_java_script_tutorial(ctx, text))

    async def fetch_java_script_tutorial(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        if not self.js_tags:
            msg = "No JavaScript tutorials are currently loaded."
            raise JavaScriptError(msg)

        matched_tutorial = await asyncio.to_thread(extractOne, query.strip(), list(self.js_tags.keys()))
        if matched_tutorial is None or matched_tutorial[1] < MIN_TUTORIAL_SCORE:
            available = ", ".join(f"`{k}`" for k in list(self.js_tags.keys())[:10])
            msg = f"No such tutorial found for {code(query, 40)}. Try `js list` ({available})."
            raise JavaScriptError(msg)

        key, score = matched_tutorial[0], float(matched_tutorial[1])
        data = self.js_tags[key]
        content = data.content if hasattr(data, "content") else str(data)
        url = getattr(data, "url", None) or f"{MDN_JS_URL}/Guide"
        return self.single(
            ctx,
            Page(
                partial(tutorial_items, key, content, score),
                url=url,
                label="MDN JavaScript Guide",
                links=[("All Guides", f"{MDN_JS_URL}/Guide")],
            ),
        )

    @javascript.command(
        name="list",
        aliases=["ls", "all"],
        extras={"examples": ["js list", "js-tutorial list"]},
    )
    async def js_list(self, ctx: commands.Context[Bot]) -> discord.Message:
        """List the available JavaScript tutorials.

        This command displays the tutorial names that can be searched with the parent command.
        """
        return await self.dispatch_view(ctx, self.fetch_js_tutorials(ctx))

    async def fetch_js_tutorials(self, ctx: commands.Context[Bot]) -> JavaScriptView:
        names = sorted(self.js_tags.keys())
        if not names:
            msg = "No JavaScript tutorials are currently available."
            raise JavaScriptError(msg)

        pages = [
            Page(
                partial(tutorial_list_items, names, names[start : start + ITEMS_PER_PAGE], len(names)),
                url=f"{MDN_JS_URL}/Guide",
                label="MDN JavaScript Guide",
            )
            for start in range(0, len(names), ITEMS_PER_PAGE)
        ]
        return JavaScriptView(ctx.author, pages)

    @commands.command(
        name="tc39",
        aliases=["esproposal", "tc39proposals"],
        extras={"examples": ["tc39 temporal", "tc39 signals", "tc39 decorators", "tc39 iterator helpers"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tc39_command(
        self,
        ctx: commands.Context[Bot],
        *,
        proposal: str = commands.parameter(description="The TC39 proposal name or topic (e.g. `Temporal`, `signals`, `decorators`)."),
    ) -> discord.Message:
        """Look up an ECMAScript (TC39) proposal by name, keyword, or stage."""
        return await self.dispatch_view(ctx, self.tc39_view(ctx, proposal))

    @javascript.command(
        name="tc39",
        aliases=["proposal", "proposals", "pep"],
        extras={"examples": ["js tc39 temporal", "js tc39 pattern matching", "js proposal decorators"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_tc39(
        self,
        ctx: commands.Context[Bot],
        *,
        proposal: str = commands.parameter(description="The TC39 proposal name or topic (e.g. `Temporal`, `signals`, `decorators`)."),
    ) -> discord.Message:
        """Look up an ECMAScript (TC39) proposal by name, keyword, or stage."""
        return await self.dispatch_view(ctx, self.tc39_view(ctx, proposal))

    async def tc39_view(self, ctx: commands.Context[Bot], target: str) -> JavaScriptView:
        cleaned = target.strip().strip("`")
        proposals = await self.get_tc39_proposals()

        stage_match = TC39_STAGE_PATTERN.match(cleaned)
        if stage_match:
            wanted_stage = stage_match.group(1)
            filtered = [p for p in proposals if str(p.get("stage")) == wanted_stage]
            if not filtered:
                msg = f"No TC39 proposals found at Stage {wanted_stage}."
                raise JavaScriptError(msg)
            entries = [
                (str(p.get("id") or p.get("name") or "?").removeprefix("proposal-"), f"{p.get('name')} (Stage {p.get('stage')})")
                for p in filtered[:18]
            ]
            return self.single(
                ctx,
                Page(
                    partial(topic_list_items, f"TC39 Stage {wanted_stage} Proposals", "js tc39", entries),
                    url=TC39_REPO_URL,
                    label="TC39 Proposals Repo",
                    colour=TC39_STAGE_COLOURS.get(wanted_stage, JS_COLOUR),
                ),
            )

        q_lower = cleaned.casefold()
        selected: dict[str, Any] | None = None
        for p in proposals:
            name_low = str(p.get("name") or "").casefold()
            id_low = str(p.get("id") or "").casefold().removeprefix("proposal-")
            if q_lower in {name_low, id_low}:
                selected = p
                break

        if selected is None:
            search_map: dict[str, dict[str, Any]] = {}
            for p in proposals:
                title = str(p.get("name") or "")
                prop_id = str(p.get("id") or "").removeprefix("proposal-")
                if title:
                    search_map[title] = p
                if prop_id:
                    search_map[prop_id] = p
            best = await asyncio.to_thread(extractOne, cleaned, list(search_map.keys()))
            if best is None or best[1] < 55:
                msg = f"Could not find a TC39 proposal matching {code(cleaned, 40)}. Try keywords like `tc39 temporal`, `tc39 signals`, or `tc39 stage 3`."
                raise JavaScriptError(msg)
            selected = search_map[best[0]]

        prop_url = str(selected.get("url") or selected.get("link") or TC39_REPO_URL)
        spec_url = str(selected.get("spec") or "")
        html = await self.optional_text(prop_url) if valid_url(prop_url) else None
        abstract = await asyncio.to_thread(extract_proposal_abstract, html) if html else None

        stage_str = str(selected.get("stage", "?"))
        colour = TC39_STAGE_COLOURS.get(stage_str, JS_COLOUR)
        links = [("All TC39 Proposals", TC39_REPO_URL), ("ECMA-262 Spec", ECMA262_URL)]
        if valid_url(spec_url) and spec_url != prop_url:
            links.insert(0, ("Specification Text", spec_url))

        return self.single(
            ctx,
            Page(
                partial(tc39_items, selected, abstract),
                url=prop_url,
                label="Open Proposal",
                colour=colour,
                links=links,
            ),
        )

    @commands.command(
        name="mdn",
        aliases=["jsdoc", "jsdocs"],
        extras={"examples": ["mdn Array.prototype.map", "mdn Promise.allSettled", "mdn structuredClone"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mdn_command(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The JavaScript object, method, statement, or Web API to look up on MDN."),
    ) -> discord.Message:
        """Retrieve JavaScript or Web API documentation from MDN Web Docs."""
        return await self.dispatch_view(ctx, self.retrieve_mdn_js_docs(ctx, query))

    @javascript.command(
        name="doc",
        aliases=["docs", "mdn", "jsdoc"],
        extras={"examples": ["js doc Array.prototype.flatMap", "js doc Object.groupBy", "js doc AbortController"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_doc(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The JavaScript object, method, statement, or Web API to look up on MDN."),
    ) -> discord.Message:
        """Retrieve JavaScript or Web API documentation from MDN Web Docs."""
        return await self.dispatch_view(ctx, self.retrieve_mdn_js_docs(ctx, query))

    async def retrieve_mdn_js_docs(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        cleaned = query.strip().strip("`")
        if not cleaned:
            msg = "Provide a JavaScript object, method, or Web API name to look up."
            raise JavaScriptError(msg)

        matches = await self.search_mdn(cleaned, js_only=True)
        if not matches:
            msg = f"No MDN JavaScript documentation entries matched {code(cleaned, 40)}."
            raise JavaScriptError(msg)

        primary = matches[0]
        html = await self.optional_text(primary.url)
        if html:
            signature, description, members = await asyncio.to_thread(extract_mdn_doc_section, html)
            if description.startswith("*Open") and primary.summary:
                description = primary.summary
        else:
            signature, description, members = None, primary.summary or "*Documentation preview unavailable.*", []

        return self.single(
            ctx,
            Page(
                partial(mdn_doc_items, primary, signature, description, members, matches[1:6]),
                url=primary.url,
                label="Open on MDN Web Docs",
                links=[("JS Reference", f"{MDN_JS_URL}/Reference")],
            ),
        )

    @commands.command(
        name="nodelib",
        aliases=["nodeapi"],
        extras={"examples": ["nodelib fs", "nodelib crypto", "nodelib worker_threads"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nodelib_command(
        self,
        ctx: commands.Context[Bot],
        module: str = commands.parameter(description="The Node.js built-in module name (e.g. `fs`, `path`, `crypto`, `stream`)."),
    ) -> discord.Message:
        """Explain a Node.js built-in module and link its documentation and source."""
        return await self.dispatch_view(ctx, self.retrieve_node_api_reference(ctx, module))

    @javascript.command(
        name="stdlib",
        aliases=["lib", "module", "node", "nodelib"],
        extras={"examples": ["js stdlib fs", "js stdlib events", "js stdlib test"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_stdlib(
        self,
        ctx: commands.Context[Bot],
        module: str = commands.parameter(description="The Node.js built-in module name (e.g. `fs`, `path`, `crypto`, `stream`)."),
    ) -> discord.Message:
        """Explain a Node.js built-in module and link its documentation and source."""
        return await self.dispatch_view(ctx, self.retrieve_node_api_reference(ctx, module))

    async def retrieve_node_api_reference(self, ctx: commands.Context[Bot], module: str) -> JavaScriptView:
        cleaned = module.strip().strip("`").removeprefix("node:").split("/", 1)[0].split(".", 1)[0]
        known_modules = NODE_STDLIB_MODULES | frozenset(STDLIB_CURATED.keys())

        if cleaned not in known_modules:
            match = await asyncio.to_thread(extractOne, cleaned, sorted(known_modules))
            if match is None or match[1] < 65:
                msg = f"{code(cleaned, 40)} is not a known Node.js built-in module."
                raise JavaScriptError(msg)
            cleaned = match[0]

        curated = STDLIB_CURATED.get(cleaned)
        doc_url = f"{NODE_DOCS_URL}/{quote(cleaned, safe='')}.html"
        json_url = f"{NODE_DOCS_URL}/{quote(cleaned, safe='')}.json"

        api_json = await self.optional_json(json_url)
        scraped_synopsis: str | None = None
        exports: list[str] = []
        stability: str | None = None
        if isinstance(api_json, dict):
            scraped_synopsis, exports, stability, _ = await asyncio.to_thread(parse_node_api_json, api_json, cleaned)

        synopsis = curated.summary if curated else (scraped_synopsis or f"Node.js built-in `node:{cleaned}` module.")
        source_path = curated.source_path if curated and curated.source_path else f"lib/{cleaned}.js"
        source_url = f"{NODE_BLOB_URL}/{source_path}"

        links = [
            ("Node.js Source", source_url),
            ("Node.js API Index", f"{NODE_DOCS_URL}/index.html"),
        ]

        return self.single(
            ctx,
            Page(
                partial(stdlib_items, cleaned, doc_url, curated, synopsis, exports, source_url, stability),
                url=doc_url,
                label=f"Open node:{cleaned} Docs",
                colour=NODE_GREEN,
                links=links,
            ),
        )

    @commands.command(
        name="jsversions",
        aliases=["jsver", "nodeversions", "nodever"],
        extras={"examples": ["jsversions"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def jsversions_command(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show supported Node.js LTS versions and ECMAScript edition status."""
        return await self.dispatch_view(ctx, self.fetch_js_versions(ctx))

    @javascript.command(
        name="versions",
        aliases=["version", "releases", "eol", "status", "lts"],
        extras={"examples": ["js versions"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def js_versions(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show supported Node.js LTS versions and ECMAScript edition status."""
        return await self.dispatch_view(ctx, self.fetch_js_versions(ctx))

    async def fetch_js_versions(self, ctx: commands.Context[Bot]) -> JavaScriptView:
        cycles = await self.get_cycles()
        now_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        active = [c for c in cycles if not (isinstance(c.get("eol"), str) and c["eol"] <= now_str)]
        eol_list = [c for c in cycles if isinstance(c.get("eol"), str) and c["eol"] <= now_str][:8]

        pages: list[Page] = []
        if active:
            pages.append(
                Page(
                    partial(generate_node_release_info, active[:8], active_view=True),
                    url=NODE_RELEASES_URL,
                    label="Node.js Releases",
                    colour=ACTIVE_COLOUR,
                    links=[("Downloads", "https://nodejs.org/en/download"), ("endoflife.date", "https://endoflife.date/nodejs")],
                )
            )
        if eol_list:
            pages.append(
                Page(
                    partial(generate_node_release_info, eol_list, active_view=False),
                    url=NODE_RELEASES_URL,
                    label="Node.js Releases",
                    colour=EOL_COLOUR,
                    links=[("endoflife.date", "https://endoflife.date/nodejs")],
                )
            )
        return JavaScriptView(ctx.author, pages)

    @javascript.command(
        name="error",
        aliases=["exception", "exc", "err", "errors"],
        extras={"examples": ["js error TypeError", "js error ReferenceError", "js error SyntaxError", "js error AggregateError"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_error(
        self,
        ctx: commands.Context[Bot],
        *,
        error_name: str = commands.parameter(description="The error name (e.g. `TypeError`, `ReferenceError`, `SyntaxError`, `RangeError`)."),
    ) -> discord.Message:
        """Explain common JavaScript runtime and syntax errors."""
        return await self.dispatch_view(ctx, self.fetch_java_script_error_info(ctx, error_name))

    async def fetch_java_script_error_info(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        cleaned = query.strip().strip("`")
        lookup = {k.casefold(): k for k in ERRORS_DB}

        canonical = lookup.get(cleaned.casefold()) or lookup.get(cleaned.casefold() + "error")
        if canonical is None:
            match = await asyncio.to_thread(extractOne, cleaned, list(ERRORS_DB.keys()))
            if match and match[1] >= 65:
                canonical = match[0]

        if canonical is not None:
            info = ERRORS_DB[canonical]
            proto_chain = JS_STANDARD_ERRORS.get(canonical, (f"`Object` \N{RIGHTWARDS ARROW} `Error` \N{RIGHTWARDS ARROW} `{info.name}`", ""))[0]
            anchor = getattr(info, "anchor", None) or info.name
            doc_url = f"{MDN_JS_URL}/Reference/Global_Objects/{anchor}"
            return self.single(
                ctx,
                Page(
                    partial(error_items, info, proto_chain, doc_url),
                    url=doc_url,
                    label="MDN Error Reference",
                    colour=EOL_COLOUR,
                    links=[("JS Error Catalog", f"{MDN_JS_URL}/Reference/Errors")],
                ),
            )

        std_lookup = {k.casefold(): k for k in JS_STANDARD_ERRORS}
        found_key = std_lookup.get(cleaned.casefold()) or std_lookup.get(cleaned.casefold() + "error")
        if found_key is None:
            available = ", ".join(f"`{k}`" for k in list(ERRORS_DB.keys() or JS_STANDARD_ERRORS.keys())[:10])
            msg = f"Unknown JavaScript error {code(cleaned, 40)}. Try one of: {available}."
            raise JavaScriptError(msg)

        proto_chain, summary = JS_STANDARD_ERRORS[found_key]
        dynamic_info = ErrorInfo(
            name=found_key,
            category="Standard Built-in Error",
            summary=summary,
            causes=("Thrown by the JavaScript runtime when an operation violates this specification precondition.",),
            fix="Guard inputs before the operation or catch the error with `try { ... } catch (err) { if (err instanceof " + found_key + ") ... }`.",
            example=f"try {{\n  // operation that may throw {found_key}\n}} catch (err) {{\n  if (err instanceof {found_key}) {{\n    console.error(err.message);\n  }}\n}}",
        )
        doc_url = f"{MDN_JS_URL}/Reference/Global_Objects/{found_key}"
        return self.single(
            ctx,
            Page(
                partial(error_items, dynamic_info, proto_chain, doc_url),
                url=doc_url,
                label="MDN Error Reference",
                colour=EOL_COLOUR,
                links=[("JS Error Catalog", f"{MDN_JS_URL}/Reference/Errors")],
            ),
        )

    @javascript.command(
        name="operator",
        aliases=["op", "operators", "ops"],
        extras={"examples": ["js operator ??", "js operator ?.", "js operator ===", "js operator ..."]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_operator(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The operator symbol (e.g. `??`, `?.`, `===`, `=>`, `...`) or name (`nullish`, `spread`)."),
    ) -> discord.Message:
        """Explain a JavaScript operator and its precedence."""
        return await self.dispatch_view(ctx, self.fetch_javas_cript_operator_info(ctx, name))

    async def fetch_javas_cript_operator_info(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
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
                raise JavaScriptError(msg)
            selected = alias_map[match[0]]

        doc_url = f"{MDN_JS_URL}/Reference/Operators/{selected.anchor}" if getattr(selected, "anchor", None) else f"{MDN_JS_URL}/Reference/Operators"
        return self.single(
            ctx,
            Page(
                partial(operator_items, selected, doc_url),
                url=doc_url,
                label="MDN Operators Reference",
                links=[("Operator Precedence", f"{MDN_JS_URL}/Reference/Operators/Operator_precedence")],
            ),
        )

    @javascript.command(
        name="builtin",
        aliases=["builtins", "global", "globals", "bi", "func"],
        extras={"examples": ["js builtin Promise", "js builtin Array", "js builtin Map", "js builtin structuredClone"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_builtin(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The standard built-in object or global function (e.g. `Promise`, `Array`, `Map`, `Intl`)."),
    ) -> discord.Message:
        """Look up standard JavaScript built-in objects and global functions."""
        return await self.dispatch_view(ctx, self.get_java_script_builtin_info(ctx, name))

    async def get_java_script_builtin_info(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        cleaned = query.strip().strip("`").rstrip("()")
        if cleaned.casefold() in {k.casefold() for k in JS_HARD_KEYWORDS}:
            msg = f"`{cleaned}` is a JavaScript reserved keyword, not a built-in global object. Use `js keyword {cleaned}` instead."
            raise JavaScriptError(msg)

        err_lookup = {k.casefold(): k for k in (set(ERRORS_DB) | set(JS_STANDARD_ERRORS))}
        if cleaned.casefold() in err_lookup:
            return await self.fetch_java_script_error_info(ctx, err_lookup[cleaned.casefold()])

        curated_map = {k.casefold(): k for k in BUILTINS_DB}
        std_map = {k.casefold(): k for k in JS_BUILTIN_OBJECTS}
        all_names = list(dict.fromkeys([*BUILTINS_DB.keys(), *JS_BUILTIN_OBJECTS.keys()]))

        canonical = curated_map.get(cleaned.casefold()) or std_map.get(cleaned.casefold())
        if canonical is None:
            match = await asyncio.to_thread(extractOne, cleaned, all_names)
            if match is None or match[1] < 65:
                msg = f"{code(cleaned, 40)} is not a standard JavaScript built-in object or global function."
                raise JavaScriptError(msg)
            canonical = match[0]

        curated: BuiltinInfo | None = BUILTINS_DB.get(canonical)
        std_meta = JS_BUILTIN_OBJECTS.get(canonical)
        kind = curated.category if curated else (std_meta[0] if std_meta else "Standard Built-in Object")
        sig = curated.signature if curated else (std_meta[1] if std_meta else None)

        is_web_global = canonical in {"structuredClone", "fetch", "queueMicrotask", "setTimeout", "setInterval", "atob", "btoa"}
        doc_url = f"{MDN_BASE_URL}/en-US/docs/Web/API/{canonical}" if is_web_global else f"{MDN_JS_URL}/Reference/Global_Objects/{canonical}"

        html = await self.optional_text(doc_url)
        scraped_sig, scraped_desc, scraped_members = (None, "", [])
        if html:
            scraped_sig, scraped_desc, scraped_members = await asyncio.to_thread(extract_mdn_doc_section, html)

        final_sig = sig or scraped_sig
        doc_summary = curated.summary if curated and curated.summary else (scraped_desc or f"Standard JavaScript built-in `{canonical}`.")
        methods = list(curated.methods) if curated and getattr(curated, "methods", None) else scraped_members

        return self.single(
            ctx,
            Page(
                partial(builtin_items, canonical, kind, final_sig, doc_summary, methods, doc_url),
                url=doc_url,
                label="MDN Built-ins Reference",
                links=[("All Standard Built-ins", f"{MDN_JS_URL}/Reference/Global_Objects")],
            ),
        )

    @javascript.command(
        name="complexity",
        aliases=["bigo", "timecomplexity", "alg", "algorithm", "v8"],
        extras={"examples": ["js complexity array", "js complexity map", "js complexity set", "js complexity object"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_complexity(
        self,
        ctx: commands.Context[Bot],
        *,
        algorithm: str = commands.parameter(
            default="big-o",
            description="The algorithm or JS data structure (e.g. `array`, `map`, `set`, `object`, `typedarray`, `timsort`).",
        ),
    ) -> discord.Message:
        """Explain JavaScript / V8 data-structure and algorithmic time complexity."""
        return await self.dispatch_view(ctx, self.fetch_java_script_complexity_info(ctx, algorithm))

    async def fetch_java_script_complexity_info(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
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
                raise JavaScriptError(msg)
            selected = alias_map[match[0]]

        return self.single(
            ctx,
            Page(
                partial(complexity_items, selected),
                url=f"{MDN_JS_URL}/Guide/Indexed_collections",
                label="MDN Collections Guide",
                colour=JS_COLOUR,
                links=[("Keyed Collections (Map/Set)", f"{MDN_JS_URL}/Guide/Keyed_collections")],
            ),
        )

    async def get_cycles(self) -> list[dict[str, Any]]:
        """endoflife.date Node.js data, cached for an hour, with the bundled fallback."""
        if self._cycles_cache and time.monotonic() - self._cycles_cache[0] < CACHE_TTL:
            return self._cycles_cache[1]
        try:
            data = await self.fetch_json(ENDOFLIFE_NODE_URL)
            cycles = data if isinstance(data, list) and data else FALLBACK_NODE_CYCLES
        except JavaScriptError:
            cycles = FALLBACK_NODE_CYCLES
        self._cycles_cache = (time.monotonic(), cycles)
        return cycles

    async def resolve_release(self, raw: str | None) -> tuple[str, dict[str, Any] | None]:
        """Turn ``None``, ``22`` or ``22.15.0`` into ``("22.15.0", cycle)``."""
        cycles = await self.get_cycles()
        if not raw or not raw.strip():
            cycle = latest_released_cycle(cycles)
            return str(cycle.get("latest")).lstrip("v"), cycle
        match = NODE_VERSION_ARG_PATTERN.match(raw.strip())
        if not match:
            msg = "Give a Node.js version like `24`, `22`, or `22.15.0`."
            raise JavaScriptError(msg)
        major = match[1]
        cycle = next((c for c in cycles if str(c.get("cycle")) == major), None)
        if cycle is None:
            msg = f"Node.js {major}.x is not a known release series."
            raise JavaScriptError(msg)
        if match[2] is not None and match[3] is not None:
            return f"{major}.{match[2]}.{match[3]}", cycle
        latest = str(cycle.get("latest") or "").lstrip("v")
        if not FULL_VERSION_PATTERN.match(latest):
            msg = f"Could not work out the latest release of Node.js {major}.x."
            raise JavaScriptError(msg)
        return latest, cycle

    async def find_curated(self, items: Sequence[Any], query: str, noun: str) -> Any:
        names = curated_names(items)
        cleaned = normalise_key(query)
        item = names.get(cleaned)
        if item is None:
            match = await asyncio.to_thread(extractOne, cleaned, list(names))
            if match is None or match[1] < 60:
                msg = f"No {noun} matched {code(query, 40)}. Available: {pack([i.key for i in items], 500)}"
                raise JavaScriptError(msg)
            item = names[match[0]]
        return item

    async def url_exists(self, url: str) -> bool:
        try:
            async with self.bot.http_session.head(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT, allow_redirects=True) as response:
                return response.status < 400
        except TimeoutError, aiohttp.ClientError:
            return False

    async def fetch_nvd(self, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            async with self.bot.http_session.get(NVD_URL, params=params, headers=headers, timeout=NVD_TIMEOUT) as response:
                if response.status in {403, 429}:
                    msg = "NVD is rate-limiting requests right now. Try again in a minute."
                    raise JavaScriptError(msg)
                if response.status == 404:
                    msg = "NVD has no data for that query, possibly because it doesn't know that exact Node.js version."
                    raise JavaScriptError(msg)
                if response.status >= 400:
                    msg = f"NVD returned HTTP {response.status}."
                    raise JavaScriptError(msg)
                data = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as error:
            msg = "Could not reach the National Vulnerability Database right now. Try again in a moment."
            raise JavaScriptError(msg) from error
        if not isinstance(data, dict):
            msg = "NVD returned an unexpected response."
            raise JavaScriptError(msg)
        return data

    async def nvd_records(self, key: str, params: dict[str, Any]) -> list[CveRecord]:
        cached = self._cve_cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL:
            return cached[1]
        records = await asyncio.to_thread(parse_nvd, await self.fetch_nvd(params))
        if len(self._cve_cache) >= 64:
            self._cve_cache.pop(min(self._cve_cache, key=lambda k: self._cve_cache[k][0]))
        self._cve_cache[key] = (time.monotonic(), records)
        return records

    @javascript.command(
        name="glossary",
        aliases=["gloss", "term", "define"],
        extras={"examples": ["js glossary closure", "js glossary hoisting", "js glossary truthy", "js glossary event loop"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_glossary(
        self,
        ctx: commands.Context[Bot],
        *,
        term: str = commands.parameter(description="The glossary term (e.g. `closure`, `hoisting`, `promise`, `prototype`)."),
    ) -> discord.Message:
        """Look up a JavaScript or Web term in the official MDN Glossary."""
        return await self.dispatch_view(ctx, self.fetch_mdn_glossary_view(ctx, term))

    async def fetch_mdn_glossary_view(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        cleaned = query.strip().strip("`")
        cache_key = cleaned.casefold()
        if cache_key in self._glossary_cache:
            entry = self._glossary_cache[cache_key]
            return self.single(
                ctx,
                Page(
                    partial(glossary_items, entry),
                    url=entry.url,
                    label="Open MDN Glossary",
                    links=[("Full MDN Glossary", MDN_GLOSSARY_URL)],
                ),
            )

        data = await self.fetch_json(
            MDN_SEARCH_API_URL,
            params={"q": f"{cleaned} glossary", "locale": "en-US"},
            missing="Could not search the MDN Glossary.",
        )
        docs = data.get("documents") if isinstance(data, dict) else []
        glossary_docs = [d for d in (docs or []) if isinstance(d, dict) and str(d.get("slug", "")).startswith("Glossary/")]
        if not glossary_docs:
            glossary_docs = [d for d in (docs or []) if isinstance(d, dict) and "Web/JavaScript" in str(d.get("slug", ""))]
        if not glossary_docs:
            msg = f"No MDN glossary term matched {code(query, 40)}."
            raise JavaScriptError(msg)

        chosen = glossary_docs[0]
        mdn_url = str(chosen.get("mdn_url") or f"/en-US/docs/{chosen.get('slug')}")
        full_url = f"{MDN_BASE_URL}{mdn_url}" if mdn_url.startswith("/") else mdn_url
        title_fallback = str(chosen.get("title") or cleaned)

        html = await self.optional_text(full_url)
        if html:
            entry = await asyncio.to_thread(extract_mdn_glossary, html, title_fallback, full_url)
        else:
            entry = GlossaryTerm(
                term=title_fallback,
                definition=truncate(discord.utils.escape_mentions(str(chosen.get("summary") or "")), 1100),
                url=full_url,
            )

        self._glossary_cache[cache_key] = entry
        return self.single(
            ctx,
            Page(
                partial(glossary_items, entry),
                url=entry.url,
                label="Open MDN Glossary",
                links=[("Full MDN Glossary", MDN_GLOSSARY_URL)],
            ),
        )

    @javascript.command(
        name="keyword",
        aliases=["kw", "kwd", "keywords"],
        extras={"examples": ["js keyword const", "js keyword async", "js keyword yield", "js keyword using"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_keyword(
        self,
        ctx: commands.Context[Bot],
        *,
        word: str = commands.parameter(description="The reserved or contextual keyword (e.g. `const`, `let`, `async`, `using`)."),
    ) -> discord.Message:
        """Explain a JavaScript reserved or contextual keyword."""
        return await self.dispatch_view(ctx, self.get_java_script_keyword_details(ctx, word))

    async def get_java_script_keyword_details(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        cleaned = query.strip().strip("`")
        known = JS_HARD_KEYWORDS | JS_CONTEXTUAL_KEYWORDS | set(KEYWORDS_DB)
        name = {k.casefold(): k for k in known}.get(cleaned.casefold())
        if name is None:
            match = await asyncio.to_thread(extractOne, cleaned, sorted(known))
            if match is None or match[1] < 70:
                msg = f"{code(cleaned, 30)} is not a JavaScript keyword. Reserved keywords: {pack(sorted(JS_HARD_KEYWORDS), 700)}"
                raise JavaScriptError(msg)
            name = match[0]

        info = KEYWORDS_DB.get(name) or KeywordInfo(
            name,
            "A reserved or contextual keyword in standard ECMAScript.",
            name,
            "Reference/Lexical_grammar#keywords",
        )
        is_contextual = name in JS_CONTEXTUAL_KEYWORDS and name not in JS_HARD_KEYWORDS
        doc_url = info.doc if info.doc.startswith("http") else f"{MDN_JS_URL}/{info.doc.lstrip('/')}"
        return self.single(
            ctx,
            Page(
                partial(keyword_items, name, info, contextual=is_contextual, doc_url=doc_url),
                url=doc_url,
                label="MDN Lexical Grammar",
                links=[("All Keywords", f"{MDN_JS_URL}/Reference/Lexical_grammar#keywords")],
            ),
        )

    @javascript.command(
        name="symbol",
        aliases=["wellknown", "protocol", "dunder", "magic", "symbols"],
        extras={"examples": ["js symbol iterator", "js symbol Symbol.toPrimitive", "js symbol dispose", "js symbol asyncIterator"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_symbol(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(
            description="The well-known Symbol or object protocol method (e.g. `Symbol.iterator`, `toPrimitive`, `dispose`)."
        ),
    ) -> discord.Message:
        """Explain a JavaScript Well-Known Symbol or meta-programming protocol method."""
        return await self.dispatch_view(ctx, self.fetch_java_script_symbol_details(ctx, name))

    async def fetch_java_script_symbol_details(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        info = lookup_symbol(query)
        if info is None:
            match = await asyncio.to_thread(extractOne, normalise_symbol(query), list(SYMBOLS_DB))
            if match is None or match[1] < 65:
                msg = f"No well-known Symbol or protocol method matched {code(query, 40)}. Try `Symbol.iterator`, `Symbol.toPrimitive`, `Symbol.dispose`, `toJSON`..."
                raise JavaScriptError(msg)
            info = SYMBOLS_DB[match[0]]

        related = [op for op in OPERATORS_DB if info.name in str(getattr(op, "dunder", "") or getattr(op, "behavior", ""))]
        see_also = ", ".join(f"`js operator {op.symbol}`" for op in related[:3]) or None
        doc_url = info.doc if info.doc.startswith("http") else f"{MDN_JS_URL}/{info.doc.lstrip('/')}"
        return self.single(
            ctx,
            Page(
                partial(symbol_items, info, doc_url, see_also),
                url=doc_url,
                label="MDN Symbol Reference",
                links=[("Well-Known Symbols", f"{MDN_JS_URL}/Reference/Global_Objects/Symbol#well-known_symbols")],
            ),
        )

    @javascript.command(
        name="whatsnew",
        aliases=["new", "wn", "whats-new", "edition"],
        extras={"examples": ["js whatsnew", "js whatsnew ES2025", "js whatsnew ES2024", "js whatsnew ES2022"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def js_whatsnew(
        self,
        ctx: commands.Context[Bot],
        edition: str | None = commands.parameter(
            default=None, description="The ECMAScript edition (e.g. `ES2025`, `ES2024`, `ES2022`). Defaults to the newest."
        ),
    ) -> discord.Message:
        """Show the headline features and Stage 4 proposals of an ECMAScript release."""
        return await self.dispatch_view(ctx, self.retrieve_js_editions_summary(ctx, edition))

    async def retrieve_js_editions_summary(self, ctx: commands.Context[Bot], edition: str | None) -> JavaScriptView:  # noqa: PLR0912
        current_year = str(datetime.now(tz=UTC).year)
        if edition and edition.strip():
            match = ES_EDITION_PATTERN.match(edition.strip())
            if not match:
                msg = "Give an ECMAScript edition like `ES2026`, `ES2025`, `ES2024`, or `ES6`."
                raise JavaScriptError(msg)
            token = match.group(1).lower()
            if token == "next":  # noqa: S105
                year = current_year
            elif len(token) <= 2:
                num = int(token)
                if num < 6:
                    msg = "Give an ECMAScript edition from `ES6` (`ES2015`) onwards."
                    raise JavaScriptError(msg)
                year = str(2009 + num)
            else:
                year = token
        else:
            year = current_year if current_year in CURATED_ES_HIGHLIGHTS else "2025"

        es_label = f"ES{year}"
        proposals_raw: list[dict[str, Any]] = []
        try:
            proposals_raw = await self.get_tc39_proposals()
        except JavaScriptError:
            proposals_raw = []

        edition_proposals: list[tuple[str, str, str]] = []
        for p in proposals_raw:
            p_ed = str(p.get("edition") or "")
            if p_ed in {year, f"ES{year}", str(int(year) - 2009)} and str(p.get("stage")) == "4":
                name = str(p.get("name") or "Proposal")
                url = str(p.get("url") or p.get("link") or TC39_REPO_URL)
                authors = p.get("authors") or []
                auth_str = ", ".join(str(a) for a in authors[:2]) if isinstance(authors, list) else str(authors or "")
                edition_proposals.append((name, url, auth_str))

        curated_lines = CURATED_ES_HIGHLIGHTS.get(year, ())
        if not curated_lines and edition_proposals:
            curated_lines = tuple(f"**{name}**" + (f" ({auth})" if auth else "") for name, _, auth in edition_proposals[:8])

        if not curated_lines and not edition_proposals:
            msg = f"No ECMAScript release summary found for {code(es_label, 20)}. Try `ES2026`, `ES2025`, `ES2024`, `ES2023`, or `ES2022`."
            raise JavaScriptError(msg)

        wn = WhatsNew(
            title=f"What's New in ECMAScript {year} ({es_label})",
            edition=es_label,
            year=year,
            highlights=curated_lines,
            proposals=tuple(edition_proposals),
        )
        spec_url = f"{TC39_REPO_URL}/blob/main/finished-proposals.md"
        links = [("Finished TC39 Proposals", spec_url), ("ECMA-262 Specification", ECMA262_URL)]
        pages = [
            Page(
                partial(whatsnew_highlight_items, wn, spec_url),
                url=spec_url,
                label=f"{es_label} Finished Proposals",
                colour=ACTIVE_COLOUR,
                links=links,
            )
        ]
        if wn.proposals:
            pages.append(
                Page(
                    partial(whatsnew_detail_items, wn, spec_url),
                    url=spec_url,
                    label=f"{es_label} Finished Proposals",
                    colour=JS_COLOUR,
                    links=links,
                )
            )
        return JavaScriptView(ctx.author, pages)

    @javascript.command(
        name="since",
        aliases=["added", "changed", "history", "compat", "baseline"],
        extras={"examples": ["js since fs.readFile", "js since Array.prototype.at", "js since Object.groupBy", "js since test"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_since(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The JS feature or Node.js API (e.g. `Array.prototype.at`, `fs.promises`, `Object.groupBy`)."),
    ) -> discord.Message:
        """Show when a JavaScript feature or Node.js API was added, changed, or deprecated."""
        return await self.dispatch_view(ctx, self.fetch_java_script_feature_details(ctx, name))

    async def fetch_java_script_feature_details(self, ctx: commands.Context[Bot], query: str) -> JavaScriptView:
        cleaned = query.strip().strip("`")
        if not cleaned:
            msg = "Provide a JavaScript feature or Node.js module/method name to look up."
            raise JavaScriptError(msg)

        raw_parts = cleaned.removeprefix("node:").split(".", 1)
        head_mod = raw_parts[0]
        member_q = raw_parts[1] if len(raw_parts) > 1 else None

        if head_mod in NODE_STDLIB_MODULES:
            json_url = f"{NODE_DOCS_URL}/{quote(head_mod, safe='')}.json"
            doc_url = f"{NODE_DOCS_URL}/{quote(head_mod, safe='')}.html"
            api_json = await self.optional_json(json_url)
            if isinstance(api_json, dict):
                label, notes = await asyncio.to_thread(find_node_symbol_history, api_json, member_q)
                return self.single(
                    ctx,
                    Page(
                        partial(since_items, label, "Node.js API", doc_url, notes),
                        url=doc_url,
                        label="Open on nodejs.org",
                        colour=NODE_GREEN,
                        links=[("Node.js Changelog", "https://github.com/nodejs/node/blob/main/CHANGELOG.md")],
                    ),
                )

        matches = await self.search_mdn(cleaned, js_only=True)
        if not matches:
            msg = f"No JavaScript or Node.js documentation entries matched {code(cleaned, 40)}."
            raise JavaScriptError(msg)

        primary = matches[0]
        html = await self.optional_text(primary.url)
        notes = await asyncio.to_thread(extract_mdn_compat_notes, html) if html else []
        return self.single(
            ctx,
            Page(
                partial(since_items, primary.title, primary.role_label, primary.url, notes),
                url=f"{primary.url}#browser_compatibility",
                label="Browser & Runtime Compatibility",
                colour=JS_COLOUR,
                links=[("Can I use...", f"https://caniuse.com/?search={quote(cleaned, safe='')}")],
            ),
        )

    @javascript.command(
        name="npm",
        aliases=["pkg", "package", "pnpm", "yarn", "bun"],
        extras={"examples": ["js npm typescript", "js npm discord.js", "js npm zod 3.23.8", "js npm @types/node"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_npm(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The npm package name (e.g. `typescript`, `discord.js`, `@types/node`)."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to `latest`."),
    ) -> discord.Message:
        """Look up a package on the npm registry."""
        return await self.dispatch_view(ctx, self.fetch_npm_package_view(ctx, package, version))

    async def fetch_npm_package_view(self, ctx: commands.Context[Bot], package: str, version: str | None) -> JavaScriptView:
        name = package.strip().strip("`")
        if not NPM_NAME_PATTERN.match(name):
            msg = "That doesn't look like a valid npm package name."
            raise JavaScriptError(msg)

        encoded_name = quote(name, safe="@/")
        data = await self.fetch_json(
            f"{NPM_REGISTRY_URL}/{encoded_name}",
            missing=f"npm has no package {code(name, 40)}.",
        )
        if not isinstance(data, dict) or not isinstance(data.get("versions"), dict):
            msg = "The npm registry returned an unexpected response."
            raise JavaScriptError(msg)

        dist_tags = data.get("dist-tags") if isinstance(data.get("dist-tags"), dict) else {}
        dist_tags = dist_tags or {}
        if version and version.strip():
            ver_clean = version.strip().lstrip("v")
            if not NPM_VERSION_PATTERN.match(ver_clean):
                msg = "That doesn't look like a valid semver version string."
                raise JavaScriptError(msg)
            resolved_ver = str(dist_tags.get(ver_clean) or ver_clean)
        else:
            resolved_ver = str(dist_tags.get("latest") or next(iter(reversed(data["versions"])), ""))

        if resolved_ver not in data["versions"]:
            msg = f"npm package {code(name, 40)} has no release version {code(resolved_ver, 30)}."
            raise JavaScriptError(msg)

        ver_data = data["versions"][resolved_ver]
        page_url = f"{NPM_PACKAGE_URL}/{name}"
        return self.single(
            ctx,
            Page(
                partial(npm_items, data, resolved_ver),
                url=page_url,
                label="Open on npmjs.com",
                colour=JS_COLOUR,
                links=npm_links(data, ver_data if isinstance(ver_data, dict) else {}, page_url),
            ),
        )

    @javascript.command(
        name="cve",
        aliases=["vuln", "security", "vulns"],
        extras={"examples": ["js cve", "js cve 22", "js cve 20.11.0", "js cve CVE-2024-22019"]},
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def js_cve(
        self,
        ctx: commands.Context[Bot],
        target: str | None = commands.parameter(
            default=None, description="A Node.js version (`22`, `20.11.0`) or a CVE id. Defaults to the newest LTS release."
        ),
    ) -> discord.Message:
        """List known CVEs affecting a Node.js release, or look up one CVE."""
        return await self.dispatch_view(ctx, self.get_cve_details(ctx, target))

    async def get_cve_details(self, ctx: commands.Context[Bot], target: str | None) -> JavaScriptView:
        cleaned = (target or "").strip().strip("`")
        if CVE_ID_PATTERN.match(cleaned):
            cve_id = cleaned.upper()
            records = await self.nvd_records(f"id:{cve_id}", {"cveId": cve_id})
            label = cve_id
        else:
            version, _ = await self.resolve_release(cleaned or None)
            records = await self.nvd_records(
                f"node-cpe:{version}",
                {"cpeName": f"cpe:2.3:a:nodejs:node.js:{version}:*:*:*:*:*:*:*", "resultsPerPage": 200},
            )
            label = f"Node.js v{version}"

        chunks = [records[i : i + CVES_PER_PAGE] for i in range(0, len(records), CVES_PER_PAGE)] or [[]]
        severe = any(r.severity in {"CRITICAL", "HIGH"} for r in records)
        links = [("NVD", "https://nvd.nist.gov/"), ("Node.js Security", "https://nodejs.org/en/learn/getting-started/security-best-practices")]
        pages = [
            Page(
                partial(cve_items, label, chunk, number, len(chunks), len(records)),
                url="https://nodejs.org/en/download",
                label="Node.js Downloads",
                colour=EOL_COLOUR if severe else (SECURITY_COLOUR if records else ACTIVE_COLOUR),
                links=links,
            )
            for number, chunk in enumerate(chunks, start=1)
        ]
        return JavaScriptView(ctx.author, pages)

    @javascript.command(
        name="download",
        aliases=["dl", "install", "get"],
        extras={"examples": ["js download", "js download 24", "js download 22.15.0"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def js_download(
        self,
        ctx: commands.Context[Bot],
        version: str | None = commands.parameter(
            default=None, description="A Node.js series (`24`, `22`) or exact release (`22.15.0`). Defaults to Active LTS."
        ),
    ) -> discord.Message:
        """Link the official installers and binaries for a Node.js release."""
        return await self.dispatch_view(ctx, self.retrieve_node_distribution(ctx, version))

    async def retrieve_node_distribution(self, ctx: commands.Context[Bot], raw: str | None) -> JavaScriptView:
        version, cycle = await self.resolve_release(raw)
        release_url = f"{NODE_DIST_URL}/v{version}/"
        candidates = {
            "Windows (.msi)": f"{NODE_DIST_URL}/v{version}/node-v{version}-x64.msi",
            "macOS (.pkg)": f"{NODE_DIST_URL}/v{version}/node-v{version}.pkg",
            "Linux x64 (.tar.xz)": f"{NODE_DIST_URL}/v{version}/node-v{version}-linux-x64.tar.xz",
            "Source (.tar.gz)": f"{NODE_DIST_URL}/v{version}/node-v{version}.tar.gz",
        }
        results = await asyncio.gather(self.url_exists(release_url), *(self.url_exists(u) for u in candidates.values()))
        if not results[0]:
            msg = f"nodejs.org has no distribution directory for Node.js v{version}."
            raise JavaScriptError(msg)

        links = [(label, url) for (label, url), ok in zip(candidates.items(), results[1:], strict=True) if ok]
        links.append(("All Downloads", "https://nodejs.org/en/download"))
        phase = cycle_phase(cycle) if cycle else "active-lts"
        colour = {
            "active-lts": ACTIVE_COLOUR,
            "current": NODE_GREEN,
            "maintenance-lts": SECURITY_COLOUR,
            "end-of-life": EOL_COLOUR,
        }.get(phase, JS_COLOUR)
        return self.single(
            ctx,
            Page(
                partial(download_items, version, cycle, release_url, [label for label, _ in links[:-1]]),
                url=release_url,
                label=f"Node.js v{version}",
                colour=colour,
                links=links,
            ),
        )

    @javascript.command(
        name="countdown",
        aliases=["schedule", "next", "upcoming"],
        extras={"examples": ["js countdown"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def js_countdown(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Count down to upcoming Node.js release and LTS milestones."""
        return await self.dispatch_view(ctx, self.fetch_node_release_schedule(ctx))

    async def fetch_node_release_schedule(self, ctx: commands.Context[Bot]) -> JavaScriptView:
        data = await self.fetch_json(NODE_SCHEDULE_URL, missing="Could not load the Node.js Release schedule.")
        if not isinstance(data, dict):
            msg = "Received an unexpected Node.js schedule payload."
            raise JavaScriptError(msg)
        milestones = await asyncio.to_thread(parse_node_schedule, data)
        if not milestones:
            msg = "Could not parse any milestones from the Node.js release schedule."
            raise JavaScriptError(msg)

        return self.single(
            ctx,
            Page(
                partial(countdown_items, milestones),
                url="https://github.com/nodejs/Release",
                label="Node.js Release WG",
                colour=JS_COLOUR,
                links=[("TC39 Calendar", "https://tc39.es/"), ("Previous Releases", NODE_RELEASES_URL)],
            ),
        )

    @javascript.command(
        name="source",
        aliases=["src", "code"],
        extras={"examples": ["js source fs", "js source events.EventEmitter", "js source util.promisify", "js source path"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def js_source(
        self,
        ctx: commands.Context[Bot],
        target: str = commands.parameter(
            description="A Node.js built-in module or dotted symbol (e.g. `fs`, `events.EventEmitter`, `util.promisify`)."
        ),
    ) -> discord.Message:
        """Link and preview the Node.js core source code of a built-in module or symbol."""
        return await self.dispatch_view(ctx, self.fetch_java_script_source(ctx, target))

    async def fetch_java_script_source(self, ctx: commands.Context[Bot], raw: str) -> JavaScriptView:
        cleaned = raw.strip().strip("`").removesuffix("()").removeprefix("node:")
        if len(cleaned) > 80 or not DOTTED_NAME_PATTERN.match(cleaned):
            msg = "Give a Node.js module or dotted symbol like `fs`, `events.EventEmitter`, or `util.promisify`."
            raise JavaScriptError(msg)

        parts = re.split(r"[./]", cleaned)
        mod_name = parts[0]
        member_name = parts[-1] if len(parts) > 1 else None
        if mod_name not in NODE_STDLIB_MODULES:
            msg = f"{code(mod_name, 40)} is not a Node.js core standard-library module."
            raise JavaScriptError(msg)

        rel_path = f"lib/{mod_name}.js"
        raw_source = await self.optional_text(f"{NODE_RAW_URL}/{rel_path}")
        if not raw_source:
            msg = f"Could not fetch the JavaScript source for `node:{mod_name}` from `nodejs/node`."
            raise JavaScriptError(msg)

        lines = raw_source.splitlines()
        start_line = 1
        kind = "module"
        signature: str | None = None
        if member_name:
            patterns = [
                (re.compile(rf"^\s*(?:async\s+)?function\s+{re.escape(member_name)}\s*\("), "function"),
                (re.compile(rf"^\s*class\s+{re.escape(member_name)}\b"), "class"),
                (re.compile(rf"^\s*(?:const|let|var)\s+{re.escape(member_name)}\s*="), "binding"),
                (re.compile(rf"\b{re.escape(member_name)}\s*\([^)]*\)\s*\{{"), "method"),
            ]
            for idx, line in enumerate(lines, start=1):
                for regex, matched_kind in patterns:
                    if regex.search(line):
                        start_line = idx
                        kind = matched_kind
                        signature = truncate(line.strip().rstrip("{").strip(), 180)
                        break
                if start_line > 1:
                    break

        end_line = min(len(lines), start_line + 13)
        snippet_lines = lines[start_line - 1 : end_line]
        preview = truncate("\n".join(snippet_lines).rstrip().replace("```", "'''"), 850)

        curated = STDLIB_CURATED.get(mod_name)
        doc_summary = curated.summary if curated else f"Node.js core implementation in `{rel_path}`."
        url = f"{NODE_BLOB_URL}/{rel_path}#L{start_line}-L{end_line}"
        info = SourceInfo(
            name=f"node:{cleaned}",
            kind=kind,
            signature=signature,
            doc=doc_summary,
            relative_path=rel_path,
            start=start_line,
            end=end_line,
            preview=preview,
            url=url,
        )
        return self.single(
            ctx,
            Page(
                partial(source_items, info),
                url=info.url,
                label="View on GitHub",
                colour=NODE_GREEN,
                links=[("Module Docs", f"{NODE_DOCS_URL}/{mod_name}.html")],
            ),
        )

    @javascript.command(
        name="gotcha",
        aliases=["pitfall", "trap", "gotchas", "pitfalls", "wtf", "wtfjs"],
        extras={"examples": ["js gotcha", "js gotcha equality", "js gotcha typeof-null", "js gotcha array-sort"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_gotcha(
        self,
        ctx: commands.Context[Bot],
        *,
        topic: str | None = commands.parameter(
            default=None, description="The pitfall (e.g. `equality`, `typeof-null`, `this`). Leave empty to list them all."
        ),
    ) -> discord.Message:
        """Show a classic JavaScript pitfall with the fix."""
        return await self.dispatch_view(ctx, self.show_java_script_gotchas(ctx, topic))

    async def show_java_script_gotchas(self, ctx: commands.Context[Bot], topic: str | None) -> JavaScriptView:
        if not topic or not topic.strip():
            entries = [(g.key, g.title) for g in GOTCHAS_DB]
            return self.single(ctx, Page(partial(topic_list_items, "JavaScript Gotchas", "js gotcha", entries), colour=SECURITY_COLOUR))
        info = await self.find_curated(GOTCHAS_DB, topic, "gotcha")
        return self.single(
            ctx,
            Page(
                partial(gotcha_items, info),
                url=f"{MDN_JS_URL}/Equality_comparisons_and_sameness",
                label="MDN Comparisons Guide",
                colour=SECURITY_COLOUR,
            ),
        )

    @javascript.command(
        name="idiom",
        aliases=["recipe", "snippet", "howto", "idioms", "recipes"],
        extras={"examples": ["js idiom", "js idiom dedupe", "js idiom group-by", "js idiom clone"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_idiom(
        self,
        ctx: commands.Context[Bot],
        *,
        topic: str | None = commands.parameter(
            default=None, description="The recipe (e.g. `dedupe`, `group-by`, `debounce`). Leave empty to list them all."
        ),
    ) -> discord.Message:
        """Show an idiomatic modern JavaScript (ES6+) recipe."""
        return await self.dispatch_view(ctx, self.retrieve_js_idiom_view(ctx, topic))

    async def retrieve_js_idiom_view(self, ctx: commands.Context[Bot], topic: str | None) -> JavaScriptView:
        if not topic or not topic.strip():
            entries = [(i.key, i.title) for i in IDIOMS_DB]
            return self.single(ctx, Page(partial(topic_list_items, "JavaScript Idioms", "js idiom", entries), colour=ACTIVE_COLOUR))
        info = await self.find_curated(IDIOMS_DB, topic, "idiom")
        return self.single(
            ctx,
            Page(
                partial(idiom_items, info),
                url=f"{MDN_JS_URL}/Guide",
                label="MDN JavaScript Guide",
                colour=ACTIVE_COLOUR,
                links=[("JS Reference", f"{MDN_JS_URL}/Reference")],
            ),
        )

    @javascript.command(
        name="typing",
        aliases=["typescript", "ts", "types", "hint", "hints"],
        extras={"examples": ["js typing", "js typing utility-types", "js typing satisfies", "js typing generics"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def js_typing(
        self,
        ctx: commands.Context[Bot],
        *,
        topic: str | None = commands.parameter(
            default=None, description="The TypeScript or JSDoc feature (e.g. `satisfies`, `generics`, `Pick`). Leave empty to list them."
        ),
    ) -> discord.Message:
        """Cheat sheet for TypeScript and JSDoc type annotations."""
        return await self.dispatch_view(ctx, self.get_type_script_typing_info(ctx, topic))

    async def get_type_script_typing_info(self, ctx: commands.Context[Bot], topic: str | None) -> JavaScriptView:
        if not topic or not topic.strip():
            entries = [(t.key, t.title) for t in TYPING_DB]
            return self.single(ctx, Page(partial(topic_list_items, "TypeScript & JSDoc Typing", "js typing", entries), colour=TS_BLUE))
        info = await self.find_curated(TYPING_DB, topic, "typing topic")
        doc_url = info.doc if info.doc.startswith("http") else f"https://www.typescriptlang.org/docs/{info.doc.lstrip('/')}"
        return self.single(
            ctx,
            Page(
                partial(typing_items, info, doc_url),
                url=doc_url,
                label="TypeScript Handbook",
                colour=TS_BLUE,
                links=[("TS Cheat Sheets", "https://www.typescriptlang.org/cheatsheets/")],
            ),
        )

    @javascript.command(
        name="zen",
        aliases=["laws", "principles", "atwood", "always-bet-on-js"],
        extras={"examples": ["js zen", "js laws"]},
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def js_zen(self, ctx: commands.Context[Bot]) -> discord.Message:
        """Show the Laws and Principles of JavaScript."""
        return await self.dispatch_view(ctx, self.show_tc39_guidelines(ctx))

    async def show_tc39_guidelines(self, ctx: commands.Context[Bot]) -> JavaScriptView:
        return self.single(
            ctx,
            Page(
                partial(zen_items),
                url=TC39_BASE_URL,
                label="TC39: Specifying JavaScript",
                colour=JS_COLOUR,
                links=[("ECMA-262 Standard", ECMA262_URL)],
            ),
        )
