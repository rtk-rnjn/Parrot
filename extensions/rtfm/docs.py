from __future__ import annotations

import asyncio
import builtins
import contextlib
import functools
import html
import importlib
import inspect
import io
import json
import logging
import platform
import re
import sys
import textwrap
import zlib
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urljoin, urlsplit

import aiohttp
import discord
from discord.ext import commands, tasks
from discord.utils import MISSING as _MISSING
from docstring_parser import DocstringDeprecated, DocstringParam, DocstringRaises, DocstringReturns
from docstring_parser import parse as parse_docstring

from .javadoc import JavaIndex, detail_javadoc
from .references import DETAILS as REFERENCE_DETAILS
from .references import LOADERS as REFERENCE_LOADERS
from .references import DetailInfo, Entries, Entry, search_hoogle
from .search import Index, LiveIndex, SiteIndex

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from core import Bot

log = logging.getLogger(__name__)

HTTP_OK = 200
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)

# Components V2 allows ~4000 characters of text per message in total, so keep
# the header + one page comfortably under that.
PAGE_SIZE = 1800
MAX_SIGNATURE = 800
MAX_SOURCE = 60_000


@dataclass(frozen=True)
class DocSite:
    url: str  # base URL, no trailing slash
    aliases: tuple[str, ...] = ()
    kind: str | None = None  # force a loader: sphinx | mkdocs | llms | sitemap
    # Top-level import names that are allowed to be inspected for this site.
    packages: tuple[str, ...] = ()


SITES: dict[str, DocSite] = {
    "discord": DocSite("https://discordpy.readthedocs.io/en/latest", ("dpy", "discord.py"), packages=("discord",)),
    "python": DocSite("https://docs.python.org/3", ("py",)),  # stdlib + builtins handled in is_allowed
    "aiohttp": DocSite("https://docs.aiohttp.org/en/latest", packages=("aiohttp",)),
    "requests": DocSite("https://requests.readthedocs.io/en/latest", ("req", "request"), packages=("requests",)),
    "numpy": DocSite("https://numpy.org/doc/stable", ("np",), packages=("numpy",)),
    "pandas": DocSite("https://pandas.pydata.org/docs", ("pd",), packages=("pandas",)),
    "matplotlib": DocSite("https://matplotlib.org/stable", ("plt", "mat", "matlab"), packages=("matplotlib", "mpl_toolkits")),
    "pil": DocSite("https://pillow.readthedocs.io/en/stable", ("pillow",), packages=("PIL",)),
    "flask": DocSite("https://flask.palletsprojects.com/en/latest", packages=("flask",)),
    "pymongo": DocSite("https://pymongo.readthedocs.io/en/stable", ("mongo", "pym"), packages=("pymongo", "bson", "gridfs")),
    "django": DocSite("https://docs.djangoproject.com/en/stable", packages=("django",)),
    "sqlalchemy": DocSite("https://docs.sqlalchemy.org/en/20", ("sa",), packages=("sqlalchemy",)),
    # Not Sphinx (links only, no inspect details):
    "fastapi": DocSite("https://fastapi.tiangolo.com"),
    "pydantic": DocSite("https://docs.pydantic.dev/latest"),
    "httpx": DocSite("https://www.python-httpx.org"),
    # Web platform, from MDN's sitemap with per-page JSON for details.
    "html": DocSite("https://developer.mozilla.org/en-US/docs/Web/HTML", ("html5",), kind="mdn"),
    "css": DocSite("https://developer.mozilla.org/en-US/docs/Web/CSS", ("css3",), kind="mdn"),
    "js": DocSite("https://developer.mozilla.org/en-US/docs/Web/JavaScript", ("javascript", "ecmascript", "es"), kind="mdn"),
    "webapi": DocSite("https://developer.mozilla.org/en-US/docs/Web/API", ("dom", "api", "web"), kind="mdn"),
    "http": DocSite("https://developer.mozilla.org/en-US/docs/Web/HTTP", kind="mdn"),
    # Other languages and tools.
    "c": DocSite("https://en.cppreference.com/w/c", kind="cppreference"),
    "cpp": DocSite("https://en.cppreference.com/w/cpp", ("c++", "cxx"), kind="cppreference"),
    "rust": DocSite("https://doc.rust-lang.org/std", ("rs",), kind="rust"),
    "java": DocSite("https://docs.oracle.com/en/java/javase/21/docs/api", ("jdk", "javadoc"), kind="javadoc"),
    "sql": DocSite("https://www.postgresql.org/docs/current", ("postgres", "postgresql", "pg"), kind="postgres"),
    "git": DocSite("https://git-scm.com/docs", kind="git"),
    "haskell": DocSite("https://hoogle.haskell.org", ("hs", "hoogle"), kind="hoogle"),
}

ALIASES: dict[str, str] = {}
for _name, _site in SITES.items():
    ALIASES[_name] = _name
    for _alias in _site.aliases:
        ALIASES[_alias] = _name


async def fetch(session: aiohttp.ClientSession, url: str) -> bytes | None:
    try:
        async with session.get(url, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status != HTTP_OK:
                return None
            return await resp.read()
    except TimeoutError, aiohttp.ClientError:
        return None


SPHINX_ENTRY = re.compile(r"(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")


def parse_sphinx(data: bytes, base: str) -> Entries:
    stream = io.BytesIO(data)
    if stream.readline().strip() != b"# Sphinx inventory version 2":
        msg = "not a v2 Sphinx inventory"
        raise ValueError(msg)

    stream.readline()  # "# Project: <name>" is next, version line after
    project = stream.readline().decode().strip()[11:]
    if b"zlib" not in stream.readline():
        msg = "inventory is not zlib compressed"
        raise ValueError(msg)

    body = zlib.decompress(stream.read()).decode("utf-8")
    entries: Entries = {}
    for line in body.splitlines():
        match = SPHINX_ENTRY.match(line)
        if not match:
            continue

        name, directive, _priority, location, dispname = match.groups()
        domain, _, subdirective = directive.partition(":")

        if directive == "std:doc":  # most pages have a label
            subdirective = "label"
        if location.endswith("$"):
            location = location[:-1] + name

        key = name if dispname == "-" else dispname
        if domain == "std":
            key = f"{subdirective}:{key}"
        if project == "discord.py":
            key = key.replace("discord.ext.commands.", "").replace("discord.", "")

        entries[key] = Entry(
            url=urljoin(f"{base}/", location),
            qualname=name if domain == "py" else None,  # full name, even if `key` was trimmed
            role=subdirective,
        )
    return entries


async def load_sphinx(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch(session, f"{base}/objects.inv")
    return await asyncio.to_thread(parse_sphinx, data, base) if data else None


def parse_mkdocs(data: bytes, base: str) -> Entries:
    docs = json.loads(data)["docs"]
    entries: Entries = {}
    for doc in docs:
        title, location = doc.get("title"), doc.get("location")
        if not title or location is None:
            continue
        key = title
        if key in entries:  # sections often share titles ("Example", "Usage")
            page = location.split("#")[0].strip("/") or "index"
            key = f"{title} \N{MIDDLE DOT} {page}"
        entries[key] = Entry(url=urljoin(f"{base}/", location))
    return entries


async def load_mkdocs(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch(session, f"{base}/search/search_index.json")
    return await asyncio.to_thread(parse_mkdocs, data, base) if data else None


LLMS_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


async def load_llms(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch(session, urljoin(base, "/llms.txt"))
    if not data:
        return None
    text = data.decode("utf-8", "replace")
    return {title: Entry(url=url) for title, url in LLMS_LINK.findall(text)}


SITEMAP_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>")


async def load_sitemap(session: aiohttp.ClientSession, base: str) -> Entries | None:
    parts = urlsplit(base)
    origin = f"{parts.scheme}://{parts.netloc}"

    data = None
    for candidate in (f"{base}/sitemap.xml", f"{origin}/sitemap.xml"):
        data = await fetch(session, candidate)
        if data:
            break
    if not data:
        return None

    text = data.decode("utf-8", "replace")
    urls = [html.unescape(u) for u in SITEMAP_LOC.findall(text)]

    if "<sitemapindex" in text:  # one level of nesting is enough in practice
        children = await asyncio.gather(*(fetch(session, u) for u in urls[:10]))
        urls = [html.unescape(u) for child in children if child for u in SITEMAP_LOC.findall(child.decode("utf-8", "replace"))]

    entries: Entries = {}
    for url in urls:
        if not url.startswith(base):
            continue
        key = url.removeprefix(base).strip("/").removesuffix(".html")
        if key:
            entries[key] = Entry(url=url)
    return entries


LOADERS: dict[str, Callable[[aiohttp.ClientSession, str], Awaitable[Entries | None]]] = {
    "sphinx": load_sphinx,
    "mkdocs": load_mkdocs,
    "llms": load_llms,
    "sitemap": load_sitemap,
    **REFERENCE_LOADERS,
}
DETAILS = {**REFERENCE_DETAILS, "javadoc": detail_javadoc}


async def index_hoogle(session: aiohttp.ClientSession, base: str) -> Index:
    return LiveIndex("hoogle", lambda query, limit: search_hoogle(session, query, limit))


# Sources that build their own index instead of handing back plain entries.
INDEXERS: dict[str, Callable[[aiohttp.ClientSession, str], Awaitable[Index | None]]] = {
    "hoogle": index_hoogle,
    "javadoc": JavaIndex.load,
}


async def build_index(session: aiohttp.ClientSession, name: str, site: DocSite) -> Index | None:
    if site.kind in INDEXERS:
        try:
            index = await INDEXERS[site.kind](session, site.url)
        except Exception:
            log.exception("%s: %s indexer failed", name, site.kind)
            return None
        if index is not None:
            log.info("%s: indexed via %s (%s)", name, site.kind, index.describe())
        return index

    for kind in [site.kind] if site.kind else LOADERS:
        try:
            entries = await LOADERS[kind](session, site.url)
        except Exception:
            log.debug("%s: %s loader failed", name, kind, exc_info=True)
            continue
        if entries:
            log.info("%s: indexed %d entries via %s", name, len(entries), kind)
            return SiteIndex.build(kind, entries)
    log.warning("%s: no loader worked for %s", name, site.url)
    return None


ROLE = re.compile(r":(?:[\w-]+:)?([\w-]+):`([^`]+)`")
CODE_ROLES = frozenset({"class", "meth", "func", "attr", "exc", "data", "mod", "obj", "const", "type"})
HYPERLINK = re.compile(r"`([^`<]+?)\s*<(https?://[^>\s]+)>`_{1,2}")
DOUBLE_TICK = re.compile(r"(?<!`)``([^`\n]+)``(?!`)")
DIRECTIVE = re.compile(r"^(\s*)\.\. ([\w-]+)::\s*(.*)$")
VERSION_LABELS = {
    "versionadded": "Added in",
    "versionchanged": "Changed in",
    "versionremoved": "Removed in",
    "deprecated": "Deprecated since",
}
ADMONITIONS = frozenset({"note", "warning", "important", "tip", "caution", "danger", "hint", "attention", "seealso"})
CODE_DIRECTIVES = frozenset({"code-block", "code", "sourcecode"})


def _role(match: re.Match[str], ticks: bool) -> str:
    role, text = match.groups()
    titled = re.match(r"^(.*?)\s*<([^<>]+)>$", text, re.S)
    if titled:
        text = titled.group(1)
    elif text.startswith("~"):
        text = text[1:].rsplit(".", 1)[-1]
    text = text.lstrip("!~").lstrip(".")
    return f"`{text}`" if ticks and role in CODE_ROLES else text


def clean_inline(text: str) -> str:
    """For short fragments (types) that get wrapped in backticks by the caller."""
    return ROLE.sub(lambda m: _role(m, ticks=False), text).replace("`", "")


def _convert_directives(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        match = DIRECTIVE.match(lines[i])
        if not match:
            out.append(lines[i])
            i += 1
            continue

        indent, name, arg = match.groups()
        j = i + 1
        body_lines: list[str] = []
        while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > len(indent)):
            body_lines.append(lines[j])
            j += 1
        body = textwrap.dedent("\n".join(body_lines)).strip("\n")
        i = j

        if name in VERSION_LABELS:
            version, _, rest = arg.partition(" ")
            rest = f"{rest} {body.replace(chr(10), ' ')}".strip()
            out.append(f"*{VERSION_LABELS[name]} {version}{': ' + rest if rest else ''}.*")
        elif name in ADMONITIONS:
            out.append(f"> **{name.title()}**")
            out.extend(f"> {ln}" for ln in (body or arg).splitlines())
        elif name in CODE_DIRECTIVES:
            code = "\n".join(ln for ln in body.splitlines() if not re.match(r"\s*:\w+:", ln))
            out.extend([f"```{arg or 'py'}", code, "```"])
        elif body:
            out.append(body)
        out.append("")
    return "\n".join(out)


def clean_rst(text: str) -> str:
    text = ROLE.sub(lambda m: _role(m, ticks=True), text)
    text = HYPERLINK.sub(r"[\1](\2)", text)
    text = DOUBLE_TICK.sub(r"`\1`", text)
    return _convert_directives(text).strip()


FENCE = re.compile(r"^\s*```(\w*)")


def paginate_text(text: str, size: int = PAGE_SIZE) -> list[str]:
    """Split markdown into pages <= ~size chars, closing/reopening code fences at breaks."""
    pages: list[str] = []
    buf: list[str] = []
    used = 0
    fresh = True  # buf holds nothing but a re-opened fence header
    lang: str | None = None  # language of the currently open fence

    def flush() -> None:
        nonlocal buf, used, fresh
        body = "\n".join(buf)
        if lang is not None:
            body += "\n```"
        pages.append(body)
        buf = [f"```{lang}"] if lang is not None else []
        used = sum(len(x) + 1 for x in buf)
        fresh = True

    chunk = size - 200
    for raw in text.splitlines():
        for start in range(0, max(len(raw), 1), chunk):  # hard-split absurdly long lines
            line = raw[start : start + chunk]
            fence = FENCE.match(line)
            closing = fence is not None and lang is not None
            if not fresh and not closing and used + len(line) + 1 > size:
                flush()
            buf.append(line)
            used += len(line) + 1
            fresh = False
            if fence:
                lang = None if lang is not None else fence.group(1)
    if not fresh:
        flush()
    return [p.strip("\n") for p in pages if p.strip()] or ["*Nothing here.*"]


def is_allowed(site: str, root: str) -> bool:
    if root in SITES[site].packages:
        return True
    return site == "python" and (root in sys.stdlib_module_names or hasattr(builtins, root))


def resolve(site: str, parts: list[str]) -> object:
    """Import the longest importable prefix, then getattr the rest. Never calls anything."""
    for i in range(len(parts), 0, -1):
        try:
            obj: object = importlib.import_module(".".join(parts[:i]))
        except ImportError:
            continue
        try:
            for attr in parts[i:]:
                obj = getattr(obj, attr)
        except AttributeError:
            return _MISSING
        return obj

    if site == "python" and hasattr(builtins, parts[0]):
        obj = builtins
        try:
            for attr in parts:
                obj = getattr(obj, attr)
        except AttributeError:
            return _MISSING
        return obj
    return _MISSING


def underlying(obj: object) -> object:
    if isinstance(obj, property):
        return obj.fget or obj
    if isinstance(obj, functools.cached_property):
        return obj.func
    return obj


def format_signature(prefix: str, name: str, sig: inspect.Signature) -> str:
    one_line = f"{prefix}{name}{sig}"
    if len(one_line) <= 90 or not sig.parameters:
        return one_line

    params = list(sig.parameters.values())
    lines: list[str] = []
    seen_star = False
    for idx, p in enumerate(params):
        if p.kind is p.VAR_POSITIONAL:
            seen_star = True
        if p.kind is p.KEYWORD_ONLY and not seen_star:
            lines.append("*")
            seen_star = True
        lines.append(str(p))
        if p.kind is p.POSITIONAL_ONLY and (idx + 1 == len(params) or params[idx + 1].kind is not p.POSITIONAL_ONLY):
            lines.append("/")

    body = ",\n".join(f"    {ln}" for ln in lines)
    ret = ""
    if sig.return_annotation is not inspect.Signature.empty:
        ret = f" -> {inspect.formatannotation(sig.return_annotation)}"
    return f"{prefix}{name}(\n{body},\n){ret}"


def make_signature(qualname: str, obj: object) -> str | None:
    if inspect.ismodule(obj):
        return None
    name = qualname.rsplit(".", 1)[-1]
    target = underlying(obj)
    try:
        sig: inspect.Signature | None = inspect.signature(target)  # type: ignore[arg-type]
    except TypeError, ValueError:
        sig = None

    if isinstance(obj, (property, functools.cached_property)):
        ret = ""
        if sig is not None and sig.return_annotation is not inspect.Signature.empty:
            ret = f" -> {inspect.formatannotation(sig.return_annotation)}"
        return f"property {name}{ret}"

    if inspect.isclass(obj):
        prefix = "class "
    elif inspect.iscoroutinefunction(target) or inspect.isasyncgenfunction(target):
        prefix = "async def "
    elif callable(target):
        prefix = "def "
    else:
        return None
    return f"{prefix}{name}(...)" if sig is None else format_signature(prefix, name, sig)


def get_source(obj: object) -> str | None:
    target = underlying(obj)
    with contextlib.suppress(ValueError):
        target = inspect.unwrap(target)  # type: ignore[arg-type]
    try:
        return textwrap.dedent(inspect.getsource(target))  # type: ignore[arg-type]
    except OSError, TypeError:
        return None  # C extension / builtin / dynamically created


def _fmt_item(head: str, desc: str) -> str:
    desc = clean_rst(desc or "")
    if not desc:
        return head
    return f"{head}\n{desc}" if "\n" in desc else f"{head} - {desc}"


def fmt_param(p: DocstringParam) -> str:
    head = f"**{p.arg_name}**"
    bits = []
    if p.type_name:
        bits.append(f"`{clean_inline(p.type_name)}`")
    if p.is_optional:
        bits.append("optional")
    if p.default:
        bits.append(f"default `{p.default}`")
    if bits:
        head += f" ({', '.join(bits)})"
    return _fmt_item(head, p.description or "")


def render_sections(raw: str | None) -> dict[str, str]:
    """Docstring (Google / NumPy / Sphinx, auto-detected) -> {section title: markdown}."""
    if not raw or not raw.strip():
        return {"Overview": "*No docstring.*"}
    try:
        doc = parse_docstring(raw)
    except Exception:
        return {"Overview": clean_rst(raw)}

    sections: dict[str, str] = {}
    intro = "\n".join(p for p in (doc.short_description, doc.long_description) if p)
    if doc.deprecation:
        note = f"> **Deprecated** since {doc.deprecation.version or '?'}: {doc.deprecation.description or ''}"
        intro = f"{note}\n\n{intro}".strip()
    sections["Overview"] = clean_rst(intro) if intro else "*No description.*"

    handled = (DocstringParam, DocstringReturns, DocstringRaises, DocstringDeprecated)
    params = [m for m in doc.meta if isinstance(m, DocstringParam) and m.args[:1] != ["attribute"]]
    attrs = [m for m in doc.meta if isinstance(m, DocstringParam) and m.args[:1] == ["attribute"]]
    returns = [m for m in doc.meta if isinstance(m, DocstringReturns)]
    raises = [m for m in doc.meta if isinstance(m, DocstringRaises)]

    if params:
        sections["Parameters"] = "\n".join(fmt_param(p) for p in params)
    if attrs:
        sections["Attributes"] = "\n".join(fmt_param(p) for p in attrs)
    if returns:
        title = "Yields" if any(getattr(r, "is_generator", False) for r in returns) else "Returns"
        sections[title] = "\n".join(
            _fmt_item(f"`{clean_inline(r.type_name)}`" if r.type_name else "", r.description or "").lstrip(" -\n") for r in returns
        )
    if raises:
        sections["Raises"] = "\n".join(
            _fmt_item(f"`{clean_inline(r.type_name)}`" if r.type_name else "", r.description or "").lstrip(" -\n") for r in raises
        )

    for m in doc.meta:  # Notes, See Also, Examples, Warnings, ...
        if isinstance(m, handled):
            continue
        key = (m.args[0] if m.args else "notes").lower()
        title = "Examples" if key.startswith("example") else key.replace("_", " ").title()
        text = clean_rst(m.description or "")
        if not text:
            continue
        if title == "Examples" and "```" not in text:
            text = f"```py\n{text}\n```"
        sections[title] = f"{sections[title]}\n\n{text}" if title in sections else text
    return sections


def _attribute_fallback(site: str, parts: list[str], role: str | None, version: str | None) -> DetailInfo | None:
    """Instance attributes (discord.py's `Client.user`) only exist in the class docstring."""
    if len(parts) < 2:
        return None
    owner = resolve(site, parts[:-1])
    if owner is _MISSING or not (inspect.isclass(owner) or inspect.ismodule(owner)):
        return None
    raw = inspect.getdoc(owner)
    if not raw:
        return None
    try:
        doc = parse_docstring(raw)
    except Exception:
        return None
    for m in doc.meta:
        if isinstance(m, DocstringParam) and m.arg_name == parts[-1]:
            return DetailInfo(".".join(parts), role, None, {"Overview": fmt_param(m)}, version)
    return None


@functools.lru_cache(maxsize=256)
def build_detail(site: str, qualname: str, role: str | None) -> DetailInfo | None:
    """Blocking (imports + inspect). Call through asyncio.to_thread."""
    parts = qualname.split(".")
    if not is_allowed(site, parts[0]):
        return None

    version = platform.python_version() if site == "python" else getattr(sys.modules.get(parts[0]), "__version__", None)
    obj = resolve(site, parts)
    if obj is _MISSING:
        return _attribute_fallback(site, parts, role, version)

    documentable = inspect.isclass(obj) or inspect.isroutine(obj) or inspect.ismodule(obj) or isinstance(obj, (property, functools.cached_property))
    if not documentable:  # a plain value: its type's docstring would be misleading
        try:
            value = repr(obj)[:300].replace("`", "'")
        except Exception:
            value = "<unrepresentable>"
        text = f"**Value** (`{type(obj).__name__}`): `{value}`"
        return DetailInfo(qualname, role, None, {"Overview": text}, version)

    raw = inspect.getdoc(obj) or inspect.getdoc(underlying(obj))
    sections = render_sections(raw)

    source = get_source(obj)
    if source:
        if len(source) > MAX_SOURCE:
            source = source[:MAX_SOURCE] + "\n# ... truncated"
        sections["Source"] = f"```py\n{source.replace('```', chr(39) * 3)}\n```"

    return DetailInfo(qualname, role, make_signature(qualname, obj), sections, version)


class OwnedView(discord.ui.LayoutView):
    """Author-only view that disables its own buttons on timeout."""

    def __init__(self, author_id: int, *, timeout: float = 300) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message: discord.Message | None = None
        self._live: list[discord.ui.Item] = []  # interactive items of the current render

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("This menu belongs to someone else.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        for item in self._live:
            item.disabled = True  # type: ignore[attr-defined]
        if self.message is not None:
            await self.message.edit(view=self)

    def button(self, label: str, callback, *, disabled: bool = False) -> discord.ui.Button:
        btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, disabled=disabled)
        btn.callback = callback
        self._live.append(btn)
        return btn


class DetailSource(Protocol):
    async def get_detail(self, site: str, entry: Entry) -> DetailInfo | None: ...


class ResultsView(OwnedView):
    def __init__(
        self,
        cog: DetailSource,
        site: str,
        matches: list[tuple[str, Entry]],
        author_id: int,
        footer: str,
    ) -> None:
        super().__init__(author_id)
        self.cog, self.site, self.matches, self.footer = cog, site, matches, footer
        self.render()

    def actions(self) -> list[discord.ui.Item]:
        """Extra buttons under the results; subclasses add their own."""
        return []

    def rebuild(self) -> ResultsView:
        """A fresh copy of this view, for coming back from a detail page."""
        return ResultsView(self.cog, self.site, self.matches, self.author_id, self.footer)

    def render(self) -> None:
        self.clear_items()
        self._live.clear()
        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        container.add_item(discord.ui.TextDisplay(f"## {self.site} docs"))
        container.add_item(discord.ui.Separator())
        for name, entry in self.matches:
            text = f"[`{name}`]({entry.url})"
            if entry.role:
                text += f"\n-# {entry.role}"
            if entry.qualname or entry.detail:  # python object or reference page: offer in-chat details
                accessory = self.button("Details", functools.partial(self.show_details, entry))
            else:
                accessory = discord.ui.Button(label="Open", url=entry.url)
            container.add_item(discord.ui.Section(text, accessory=accessory))
        actions = self.actions()
        if actions:
            container.add_item(discord.ui.ActionRow(*actions))
        container.add_item(discord.ui.TextDisplay(f"-# {self.footer}"))
        self.add_item(container)

    async def show_details(self, entry: Entry, interaction: discord.Interaction) -> None:
        await interaction.response.defer()  # first import of a big library can take a while
        info = await self.cog.get_detail(self.site, entry)
        if info is None:
            await interaction.followup.send("Bot could not load details for that entry. Use the link instead.", ephemeral=True)
            return
        view = DocView(info, entry.url, self, self.author_id)
        view.message = interaction.message
        self.stop()
        await interaction.edit_original_response(view=view)


class DocView(OwnedView):
    def __init__(self, info: DetailInfo, url: str, parent: ResultsView, author_id: int) -> None:
        super().__init__(author_id)
        self.info, self.url, self.parent = info, url, parent
        self.section = next(iter(info.sections))
        self.page = 0
        self._pages: dict[str, list[str]] = {}
        self.render()

    def pages_for(self, section: str) -> list[str]:
        if section not in self._pages:
            self._pages[section] = paginate_text(self.info.sections[section])
        return self._pages[section]

    def render(self) -> None:
        self.clear_items()
        self._live.clear()
        info = self.info
        pages = self.pages_for(self.section)
        self.page = max(0, min(self.page, len(pages) - 1))

        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        sub = info.role or "object"
        if info.version:
            sub += f" \N{MIDDLE DOT} installed {info.version}"
        container.add_item(discord.ui.TextDisplay(f"## {info.qualname}\n-# {sub}"))
        if info.signature:
            sig = info.signature
            if len(sig) > MAX_SIGNATURE:
                sig = sig[:MAX_SIGNATURE] + "\n\N{HORIZONTAL ELLIPSIS}"
            container.add_item(discord.ui.TextDisplay(f"```{info.language}\n{sig}\n```"))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(pages[self.page]))
        container.add_item(discord.ui.Separator())

        if len(info.sections) > 1:
            select = discord.ui.Select(
                options=[discord.SelectOption(label=n, default=n == self.section) for n in info.sections],
            )
            select.callback = functools.partial(self.on_select, select)
            self._live.append(select)
            row = discord.ui.ActionRow()
            row.add_item(select)
            container.add_item(row)

        nav = discord.ui.ActionRow()
        if len(pages) > 1:
            nav.add_item(self.button("\N{BLACK LEFT-POINTING TRIANGLE}", self.on_prev, disabled=self.page == 0))
            nav.add_item(
                discord.ui.Button(label=f"{self.page + 1}/{len(pages)}", style=discord.ButtonStyle.secondary, disabled=True),
            )
            nav.add_item(self.button("\N{BLACK RIGHT-POINTING TRIANGLE}", self.on_next, disabled=self.page == len(pages) - 1))
        nav.add_item(self.button("Results", self.on_back))
        nav.add_item(discord.ui.Button(label="Docs", url=self.url))
        container.add_item(nav)
        self.add_item(container)

    async def refresh(self, interaction: discord.Interaction) -> None:
        self.render()
        await interaction.response.edit_message(view=self)

    async def on_select(self, select: discord.ui.Select, interaction: discord.Interaction) -> None:
        self.section, self.page = select.values[0], 0
        await self.refresh(interaction)

    async def on_prev(self, interaction: discord.Interaction) -> None:
        self.page -= 1
        await self.refresh(interaction)

    async def on_next(self, interaction: discord.Interaction) -> None:
        self.page += 1
        await self.refresh(interaction)

    async def on_back(self, interaction: discord.Interaction) -> None:
        view = self.parent.rebuild()
        view.message = interaction.message
        self.stop()
        await interaction.response.edit_message(view=view)


class Docs(commands.Cog, command_attrs={"hidden": True}, name="Documentation"):
    """Documentation search with in-chat details: Python libraries, MDN, C and C++, Rust, Java, SQL, git and Haskell."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.indexes: dict[str, Index] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def cog_load(self) -> None:
        self.refresh.start()

    async def cog_unload(self) -> None:
        self.refresh.cancel()

    @tasks.loop(hours=12)
    async def refresh(self) -> None:
        await asyncio.gather(*(self.load_site(name, force=True) for name in SITES))

    async def load_site(self, name: str, *, force: bool = False) -> Index | None:
        if not force and name in self.indexes:
            return self.indexes[name]
        async with self._locks[name]:
            if not force and name in self.indexes:  # someone else finished first
                return self.indexes[name]
            index = await build_index(self.bot.http_session, name, SITES[name])
            if index is not None:  # on failure keep the old index
                self.indexes[name] = index
            return self.indexes.get(name)

    async def get_detail(self, site: str, entry: Entry) -> DetailInfo | None:
        if entry.qualname:
            return await asyncio.to_thread(build_detail, site, entry.qualname, entry.role)
        fetcher = DETAILS.get(entry.detail or "")
        if fetcher is None:
            return None
        return await fetcher(self.bot.http_session, entry)

    @staticmethod
    def normalize(site: str, query: str) -> str:
        if site != "discord":
            return query
        query = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?", "", query)
        lowered = query.lower()
        for attr in dir(discord.abc.Messageable):  # point at abc.Messageable.* properly
            if attr[0] != "_" and attr == lowered:
                return f"abc.Messageable.{attr}"
        return query

    @commands.command(name="rtfd", aliases=["rtfm", "docs"])
    async def rtfd(
        self,
        ctx: commands.Context,
        site: str | None = commands.parameter(description="Which documentation to search", default=None),
        *,
        query: str | None = commands.parameter(description="What to look for", default=None),
    ):
        """Search documentation and open details in chat.

        Python libraries come from their Sphinx inventories; `html`, `css`, `js`, `webapi` and `http` from MDN;
        `c` and `cpp` from cppreference; `rust` from the std docs; `java` from the JDK 21 Javadoc, where
        `System.out.println` follows the field to `PrintStream.println`; `sql` from PostgreSQL; `git` from
        git-scm.com; `haskell` from Hoogle.
        """
        if site is None:
            await ctx.send("Available docs: " + ", ".join(f"`{n}`" for n in SITES))
            return

        name = ALIASES.get(site.lower())
        if name is None:
            # Old habit: `!rtfd Client.send` means discord.py
            name, query = "discord", f"{site} {query or ''}".strip()

        if not query:
            await ctx.send(SITES[name].url)
            return

        async with ctx.typing():
            index = await self.load_site(name)
            if index is None:
                await ctx.send("Bot could not load those docs right now. Try again later.")
                return
            matches = await index.search_async(self.normalize(name, query))

        if not matches:
            await ctx.send("No match found.")
            return

        footer = f"Requested by {ctx.author} \N{MIDDLE DOT} {index.describe()}"
        view = ResultsView(self, name, matches, ctx.author.id, footer)
        view.message = await ctx.send(view=view)
