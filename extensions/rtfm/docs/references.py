# references.py

from __future__ import annotations

import asyncio
import gzip
import io
import json
import logging
import re
import textwrap
import time
import zlib
from collections import OrderedDict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, unquote, urljoin

import aiohttp
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from markdownify import MarkdownConverter

if TYPE_CHECKING:
    from collections.abc import Awaitable

log = logging.getLogger(__name__)

HTTP_OK = 200
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=60, sock_connect=10)
SHARED_CACHE_TTL = 3600
SHARED_CACHE_SIZE = 32
MAX_SECTION = 16_000  # DocView pages this, so verbose references stay readable instead of being clipped
MAX_SECTIONS = 20
MAX_SECTION_TITLE = 90
MAX_SIGNATURE = 800
MAX_DECLARATIONS = 4
MAX_PARAGRAPHS = 4
SUBINDEX_CONCURRENCY = 4

HEADERS = {}

MDN_SITEMAP = "https://developer.mozilla.org/sitemaps/en-us/sitemap.xml.gz"
HOOGLE_URL = "https://hoogle.haskell.org/"
CELL = "\x00"
DOT = " \N{MIDDLE DOT} "
FENCE_LANGUAGES = {"python3": "py", "pycon": "py", "pycon3": "py", "default": "py", "none": "", "text": ""}  # Sphinx class names

DEFAULT_CONTENT = ("main article", "article", "main", "[role=main]")
BOILERPLATE = (
    "nav, aside, footer, button, form, input, select, [role=navigation], [aria-label=breadcrumb], .breadcrumb, .header-anchor, .hash-link, .edit-link"
)
MARK = "\x01"


@dataclass(frozen=True, slots=True)
class Entry:
    url: str
    qualname: str | None = None  # dotted import path, python-domain entries only
    role: str | None = None
    detail: str | None = None  # key into DETAILS for sources that render pages in chat
    signature: str | None = None  # prefilled by live sources
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class PageSite:
    language: str  # code fence for the signature
    content: tuple[str, ...] = DEFAULT_CONTENT  # first selector that matches is the article body
    drop: str = ""  # extra selectors to remove


Entries = dict[str, Entry]  # display name -> entry


@dataclass(frozen=True)
class DetailInfo:
    qualname: str
    role: str | None
    signature: str | None
    sections: dict[str, str]  # ordered: Overview first
    version: str | None
    language: str = "py"  # code fence used for the signature


_shared: OrderedDict[str, tuple[float, bytes]] = OrderedDict()


PAGE_SITES: dict[str, PageSite] = {
    "react": PageSite("jsx"),
    "nextjs": PageSite("tsx"),
    "vue": PageSite("js", (".vp-doc", *DEFAULT_CONTENT)),
    "angular": PageSite("ts", ("docs-viewer", ".docs-viewer", *DEFAULT_CONTENT)),
    "mysql": PageSite("sql", ("#docs-body", "body"), "div.navheader, div.navfooter, div.toc"),
    "sqlite": PageSite("sql", ("div.fancy", "body"), ".fancy_toc, #toc"),
    "mongodb": PageSite("js"),
    "redis": PageSite("sh"),
    "fastapi": PageSite("py", ("article.md-content__inner", *DEFAULT_CONTENT)),
    "pydantic": PageSite("py", ("article.md-content__inner", *DEFAULT_CONTENT)),
    "httpx": PageSite("py", ("article.md-content__inner", *DEFAULT_CONTENT)),
}


def anchored(root: Tag, fragment: str) -> tuple[str, Tag] | None:
    """One entry of a long page (`lang_corefunc.html#abs`): its term or heading, and what follows it."""
    target = root.find(id=fragment) or root.find("a", attrs={"name": fragment})
    if target is None:
        return None
    start = next((node for node in (target, *target.parents) if node.name == "dt" or node.name in HEADINGS), None)
    if start is None and target.name == "a":  # an empty anchor placed just before its term or heading
        start = target.find_next_sibling(["dt", *HEADINGS])
    if start is None or start.name == "h1":
        return None

    for noise in start.select(NOISE):
        noise.decompose()

    body: list[Tag | NavigableString] = []
    if start.name == "dt":
        definition = start.find_next_sibling("dd")
        body = [definition] if definition is not None else []
    else:
        level = int(start.name[1])
        for sibling in start.next_siblings:
            if isinstance(sibling, Tag) and sibling.name in HEADINGS and int(sibling.name[1]) <= level:
                break
            body.append(sibling)
    holder = soup_of("").new_tag("div")
    for node in body:
        holder.append(node.extract())
    return " ".join(start.get_text().split()), holder


def render_page(data: bytes, url: str, fragment: str, role: str | None, site: PageSite) -> DetailInfo | None:  # noqa: PLR0912
    page = soup_of(data)
    heading = page.select_one("h1")
    if heading is not None:
        for noise in heading.select(NOISE):
            noise.decompose()
    title = " ".join(heading.get_text().split()) if heading else url
    root = page
    for selector in site.content:
        selected = page.select_one(selector)
        if selected is not None:
            root = selected
            break
    for tag in root.select(f"{BOILERPLATE}, {site.drop}" if site.drop else BOILERPLATE):
        tag.decompose()

    signature = None
    found = anchored(root, fragment) if fragment else None
    if fragment and found is None:
        return None
    if found is not None:
        title, root = found
        signature = title if "(" in title else None
    elif heading is not None:
        heading.decompose()  # the title is already shown above the signature

    # Sections follow h2, or h3 on pages that start at h3 (SQLite). Headings become markers so nested wrappers don't matter.
    level = "h2" if root.find("h2") else "h3"
    names: list[str] = []
    for node in root.find_all(level):
        for noise in node.select(NOISE):
            noise.decompose()
        names.append(" ".join(node.get_text().split()) or "Section")
        marker = page.new_tag("p")
        marker.string = f"{MARK}{len(names) - 1}{MARK}"
        node.replace_with(marker)

    chunks = re.split(rf"{MARK}(\d+){MARK}", to_markdown(root, url))
    sections = {"Overview": chunks[0].strip()}
    for index, body in zip(chunks[1::2], chunks[2::2], strict=True):
        name, count = names[int(index)], 2
        while name in sections:  # "Example" often repeats
            name = f"{names[int(index)]} ({count})"
            count += 1
        sections[name] = body.strip()

    if signature is None:  # a short code block right under the intro is the call form (`useState(initialState)`)
        fence = re.search(r"```[^\n]*\n(.*?)```\n?", sections["Overview"], re.S)
        if fence and fence[1].strip().count("\n") < 4:
            signature = fence[1].strip()
            sections["Overview"] = sections["Overview"].replace(fence[0], "", 1).strip()
    return detail(title, role=role, signature=signature, sections=sections, language=site.language)


async def detail_page(session: aiohttp.ClientSession, entry: Entry, site: PageSite) -> DetailInfo | None:
    url, _, fragment = entry.url.partition("#")
    data = await fetch_shared(session, url)  # shared cache: several entries live on the same SQLite or MySQL page
    if not data:
        return None
    return await asyncio.to_thread(render_page, data, url, unquote(fragment), entry.role, site)


async def fetch(session: aiohttp.ClientSession, url: str, *, retries: int = 2) -> bytes | None:
    for attempt in range(retries + 1):
        try:
            async with session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS) as resp:
                if resp.status == HTTP_OK:
                    return await resp.read()
                log.warning("GET %s -> HTTP %s", url, resp.status)  # 404 included, while debugging
                if resp.status not in (429, 500, 502, 503, 504):
                    return None
        except (TimeoutError, aiohttp.ClientError) as exc:
            log.warning("GET %s failed (attempt %d): %s: %s", url, attempt + 1, type(exc).__name__, exc)
        if attempt < retries:
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


async def fetch_shared(session: aiohttp.ClientSession, url: str) -> bytes | None:
    """Fetch once per hour: several sites are carved out of the same MDN sitemap and Javadoc pages are revisited."""
    cached = _shared.get(url)
    if cached and time.monotonic() - cached[0] < SHARED_CACHE_TTL:
        _shared.move_to_end(url)
        return cached[1]
    data = await fetch(session, url)
    if data:
        _shared[url] = (time.monotonic(), data)
        _shared.move_to_end(url)
        while len(_shared) > SHARED_CACHE_SIZE:
            _shared.popitem(last=False)
    return data


def soup_of(data: bytes | str) -> BeautifulSoup:
    return BeautifulSoup(data, "lxml")


def attr(tag: Tag, name: str) -> str:
    """A tag attribute as one string; bs4 may hand back a list for multi-valued attributes."""
    value = tag.get(name)
    if isinstance(value, list):
        return " ".join(value)
    return value or ""


class DocConverter(MarkdownConverter):
    """markdownify tuned for reference pages: fenced code, no images."""

    def convert_pre(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        code = textwrap.dedent(el.get_text()).strip("\n").rstrip()
        if not code:
            return ""
        # The language may sit on the <pre>, its <code> (mdBook), or a wrapper div (Sphinx, cppreference).
        carriers = (el, el.find("code"), el.parent, el.parent.parent if el.parent is not None else None)
        classes = " ".join(attr(node, "class") for node in carriers if isinstance(node, Tag))
        language_match = re.search(r"(?:brush:|language-|lang-)\s*([\w+#]+)", classes) or re.search(r"highlight-([\w+#]+)", classes)
        lang = language_match[1] if language_match else ""
        return f"\n```{FENCE_LANGUAGES.get(lang, lang)}\n{code}\n```\n"

    def convert_img(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        return ""

    def convert_a(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        el.attrs.pop("title", None)  # Discord shows a link title as literal text
        return super().convert_a(el, text, parent_tags)  # type: ignore[attr-defined]  # markdownify's stub omits it

    def convert_blockquote(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        if "```" in text:  # Discord cannot quote a code block; Javadoc wraps its samples this way
            return f"\n{text.strip()}\n\n"
        return super().convert_blockquote(el, text, parent_tags)  # type: ignore[attr-defined]  # markdownify's stub omits it

    def convert_hN(self, n: int, el: Tag, text: str, parent_tags: set[str]) -> str:
        """Discord stops at ###, and the page title already sits at ##, so deeper headings become bold lines."""
        if "_inline" in parent_tags:
            return text
        text = " ".join(text.split())
        if not text:
            return ""
        return f"\n\n### {text}\n\n" if n <= 3 else f"\n\n**{text}**\n\n"

    # Discord renders neither definition lists nor tables, so flatten both into plain lines.

    def convert_dt(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        return f"\n**{text.strip()}**"

    def convert_dd(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        body = text.strip()
        if not body:
            return "\n"
        return f"\n{body}\n" if "\n" in body else f" - {body}\n"

    def convert_dl(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        return f"\n{text.strip()}\n\n"

    def convert_td(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        body = text.strip() if "```" in text else " ".join(text.split())  # a fenced block keeps its lines
        return body + CELL

    def convert_th(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        return f"**{' '.join(text.split())}**{CELL}"

    def convert_tr(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        cells = [cell.strip() for cell in text.split(CELL) if cell.strip()]
        if not cells:
            return ""
        if any("```" in cell for cell in cells):  # cppreference puts version-specific code in table cells
            return "\n".join(cells) + "\n"
        if len(cells) == 3 and cells[1] == "-":  # cppreference's parameter tables: name, dash, description
            return f"**{cells[0]}** - {cells[2]}\n"
        if el.find("th") is not None and len(cells) > 1:
            return f"{cells[0]} - {DOT.join(cells[1:])}\n"
        return DOT.join(cells) + "\n"

    def convert_table(self, el: Tag, text: str, *args: Any, **kwargs: Any) -> str:
        return f"\n{text.strip()}\n\n"


LINK = re.compile(r"\[([^\]]*)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")  # allows one level of parentheses in the URL
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
# MDN's code-example language labels and live-sample frames, Sphinx's pilcrow links, MediaWiki's [edit] links.
NOISE = ".example-header, iframe, script, style, svg, a.headerlink, .mw-editsection"


def _fix_link(match: re.Match[str], base: str) -> str:
    text, href = match[1], match[2]
    if href.startswith("#"):  # an in-page anchor cannot be followed from a Discord message
        return text
    if "://" not in href and not href.startswith("mailto:"):
        href = urljoin(base, href)
    escaped_href = href.replace("(", "%28").replace(")", "%29")
    return f"[{text}]({escaped_href})"  # a parenthesis would end the link early


def _has_content_after(heading: Tag) -> bool:
    for sibling in heading.next_siblings:
        if isinstance(sibling, Tag):
            if sibling.name in HEADINGS:
                return False
            if sibling.get_text(strip=True):
                return True
        elif isinstance(sibling, NavigableString) and sibling.strip():
            return True
    return False


def prune(root: Tag) -> None:
    """Drop what Discord cannot show, then any heading left with nothing under it (MDN's "Result" frames)."""
    for tag in root.select(NOISE):
        tag.decompose()
    for heading in root.find_all(HEADINGS):
        if not _has_content_after(heading):
            heading.decompose()


def to_markdown(source: Tag | str, base: str) -> str:
    """HTML to Discord-friendly markdown with links made absolute. A tag is pruned in place."""
    root = soup_of(source) if isinstance(source, str) else source
    prune(root)
    text = DocConverter(bullets="\N{BULLET}").convert_soup(root)
    text = LINK.sub(lambda m: _fix_link(m, base), text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clip(text: str, limit: int = MAX_SECTION) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"


def paragraphs(nodes: Iterable[Tag], base: str, limit: int = MAX_PARAGRAPHS) -> str:
    chunks = [to_markdown(node, base) for node in list(nodes)[:limit]]
    return "\n\n".join(chunk for chunk in chunks if chunk)


def unique_name(entries: Entries, name: str, qualifier: str | None) -> str:
    if name not in entries:
        return name
    if qualifier and f"{name} ({qualifier})" not in entries:
        return f"{name} ({qualifier})"
    index = 2
    while f"{name} ({index})" in entries:
        index += 1
    return f"{name} ({index})"


def detail(title: str, *, role: str | None, signature: str | None, sections: dict[str, str], language: str) -> DetailInfo:
    """Section pickers hold at most 25 options and 100-character labels, so cap both."""
    cleaned = {name[:MAX_SECTION_TITLE]: clip(body) for name, body in list(sections.items())[:MAX_SECTIONS] if body and body.strip()}
    if not cleaned:
        cleaned["Overview"] = "*No description on the page.*"
    return DetailInfo(title, role, clip(signature, MAX_SIGNATURE) if signature else None, cleaned, None, language)


SITEMAP_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>")
MDN_BUCKETS = frozenset(
    {
        "Reference",
        "Guides",
        "Guide",
        "Global_Objects",
        "Elements",
        "Element",
        "Attributes",
        "Properties",
        "Statements",
        "Operators",
        "Functions",
        "Classes",
        "Errors",
        "Headers",
        "Methods",
        "Status",
        "Selectors",
        "At-rules",
        "Types",
        "Values",
        "Tutorials",
        "Howto",
        "Web",
        "Learn",
        "Resources",
    }
)
MDN_SKIPPED_SECTIONS = frozenset({"Try it", "Specifications", "Browser compatibility", "See also"})


async def load_mdn(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch_shared(session, MDN_SITEMAP)
    if not data:
        return None
    if data[:2] == b"\x1f\x8b":
        data = await asyncio.to_thread(gzip.decompress, data)
    prefix = base.rstrip("/") + "/"
    entries: Entries = {}
    for url in SITEMAP_LOC.findall(data.decode("utf-8", "replace")):
        if not url.startswith(prefix):
            continue
        segments = url[len(prefix) :].strip("/").split("/")
        if not segments or not segments[-1]:
            continue
        name = segments[-1].replace("_", " ")
        if len(segments) > 1 and segments[-2] not in MDN_BUCKETS:
            name = f"{segments[-2].replace('_', ' ')}.{name}"
        qualifier = " / ".join(segment.replace("_", " ") for segment in segments[:-1]) or None
        entries[unique_name(entries, name, qualifier)] = Entry(url=url, role=qualifier, detail="mdn")
    return entries


async def detail_mdn(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    data = await fetch(session, f"{entry.url.rstrip('/')}/index.json")
    if not data:
        return None
    try:
        doc = json.loads(data)["doc"]
    except ValueError, KeyError, TypeError:
        return None

    base = "https://developer.mozilla.org"
    sections: dict[str, str] = {}
    overview: list[str] = []
    signature = None
    current: str | None = None
    for block in doc.get("body", []):
        if block.get("type") != "prose":
            continue
        value = block.get("value", {})
        title, content = value.get("title"), value.get("content", "")
        markdown = to_markdown(content, base) if content else ""
        if not title:
            if markdown:
                overview.append(markdown)
            continue
        if value.get("isH3"):  # a subsection stays under its h2 instead of becoming a picker entry
            if current is not None and markdown:
                sections[current] = f"{sections[current]}\n\n### {title}\n{markdown}".strip()
            continue
        if title in MDN_SKIPPED_SECTIONS:
            current = None
            continue
        if title == "Syntax" and signature is None:
            fence = re.search(r"```[^\n]*\n(.*?)```", markdown, re.S)
            signature = fence[1].strip() if fence else None
        sections[title] = markdown  # "Examples" is often empty until its h3 subsections arrive
        current = title
    page_type = doc.get("pageType") or ""
    language = next((lang for lang in ("css", "html", "http") if page_type.startswith(lang)), "js")
    if not overview:  # the summary is a plain-text copy of the first paragraph, so only fall back to it
        overview = [doc.get("summary", "").strip()]
    return detail(
        doc.get("title", entry.url),
        role=page_type.replace("-", " ") or None,
        signature=signature,
        sections={"Overview": "\n\n".join(filter(None, overview)), **sections},
        language=language,
    )


CPP_ORIGIN = "https://en.cppreference.com/w"


def _cpp_symbols(page: BeautifulSoup, lang: str) -> dict[str, str]:
    content = page.select_one("#mw-content-text")
    if content is None:
        return {}
    symbols: dict[str, str] = {}
    for anchor in content.select("a[href]"):
        href, text = attr(anchor, "href"), anchor.get_text(strip=True)
        rel = href.removeprefix("/w")
        if not rel.startswith(f"/{lang}/") or "symbol_index" in href or not text:
            continue
        symbols.setdefault(text.removesuffix("()").removesuffix("<>()").removesuffix("<>"), rel)
    return symbols


async def load_cppreference(session: aiohttp.ClientSession, base: str) -> Entries | None:
    lang = base.rstrip("/").rsplit("/", 1)[-1]
    data = await fetch(session, f"{base}/symbol_index")
    if not data:
        return None
    page = soup_of(data)
    symbols = _cpp_symbols(page, lang)

    sub_pages = sorted({attr(a, "href").removeprefix("/w") for a in page.select("#mw-content-text a[href]") if "/symbol_index/" in attr(a, "href")})
    semaphore = asyncio.Semaphore(SUBINDEX_CONCURRENCY)

    async def load_sub(rel: str) -> dict[str, str]:
        async with semaphore:
            sub = await fetch(session, f"{CPP_ORIGIN}{rel}")
        return _cpp_symbols(soup_of(sub), lang) if sub else {}

    for found in await asyncio.gather(*(load_sub(rel) for rel in sub_pages)):
        for name, rel in found.items():
            symbols.setdefault(name, rel)

    entries: Entries = {}
    for name, rel in symbols.items():
        parts = rel.strip("/").split("/")
        role = parts[1].replace("_", " ") if len(parts) > 2 else None
        entries[unique_name(entries, name, role)] = Entry(url=f"{CPP_ORIGIN}{rel}", role=role, detail="cppreference")
    return entries


async def detail_cppreference(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    data = await fetch(session, entry.url)
    if not data:
        return None
    page = soup_of(data)
    content = page.select_one("#mw-content-text")
    if content is None:
        return None
    content = content.select_one(".mw-parser-output") or content
    title = page.select_one("#firstHeading") or page.select_one("h1")
    heading = title.get_text(strip=True) if title else entry.url

    lines: list[str] = []
    header = content.select_one("table.t-dcl-begin tr.t-dsc-header")
    if header is not None:
        lines.append(f"// {header.get_text(' ', strip=True)}")
    rows = content.select("table.t-dcl-begin tr.t-dcl")
    for row in rows[:MAX_DECLARATIONS]:
        code_cell, number_cell, version_cell = [*row.find_all("td"), None, None, None][:3]
        code = code_cell.get_text().strip() if code_cell is not None else ""
        if not code:
            continue
        number = number_cell.get_text(strip=True) if number_cell is not None else ""
        version = version_cell.get_text(" ", strip=True) if version_cell is not None else ""
        note = " ".join(part for part in (number, version) if part)
        lines.append(f"{code}  // {note}" if note else code)
    if len(rows) > MAX_DECLARATIONS:
        lines.append(f"// \N{HORIZONTAL ELLIPSIS} {len(rows) - MAX_DECLARATIONS} more overloads on the page")
    signature = "\n".join(lines) or None
    language = "c" if "/w/c/" in entry.url else "cpp"

    intro: list[Tag] = []
    for child in content.children:
        if not isinstance(child, Tag):
            continue
        if child.name in ("h2", "h3"):
            break
        if child.name == "p":
            intro.append(child)

    sections = {"Overview": paragraphs(intro, CPP_ORIGIN)}
    example = content.select_one("div.t-example pre")
    if example is not None:
        sections["Example"] = f"```{language}\n{example.get_text().strip()}\n```"
    return detail(heading, role=entry.role, signature=signature, sections=sections, language=language)


async def load_rust(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch(session, f"{base}/all.html")
    if not data:
        return None
    entries: Entries = {}
    for anchor in soup_of(data).select("ul.all-items li a[href]"):
        href, name = attr(anchor, "href"), anchor.get_text(strip=True)
        kind = href.rsplit("/", 1)[-1].split(".", 1)[0]
        role = {"fn": "function", "mod": "module", "primitive": "primitive type"}.get(kind, kind.replace("_", " "))
        entries[unique_name(entries, name, role)] = Entry(url=f"{base}/{href}", role=role, detail="rust")
    return entries


def _docblock_sections(block: Tag, base: str) -> dict[str, str]:
    """A rustdoc docblock is flat: h2 headings split it into sections."""
    sections: dict[str, list[Tag]] = {"Overview": []}
    current = "Overview"
    for child in block.children:
        if not isinstance(child, Tag):
            continue
        if child.name in ("h2", "h3"):
            current = child.get_text(strip=True).lstrip("\N{SECTION SIGN} ")
            sections.setdefault(current, [])
            continue
        sections[current].append(child)
    return {name: paragraphs(nodes, base, limit=6) for name, nodes in sections.items() if nodes}


async def detail_rust(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    data = await fetch(session, entry.url)
    if not data:
        return None
    page = soup_of(data)
    heading = page.select_one("h1")
    if heading is not None:
        for button in heading.select("button"):
            button.decompose()
    declaration = page.select_one("pre.rust.item-decl")
    block = page.select_one(".top-doc .docblock") or page.select_one(".docblock")
    sections = _docblock_sections(block, entry.url) if block is not None else {}
    return detail(
        heading.get_text(" ", strip=True) if heading else entry.url,
        role=entry.role,
        signature=declaration.get_text().strip() if declaration else None,
        sections=sections,
        language="rust",
    )


async def load_postgres(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch(session, f"{base}/sql-commands.html")
    if not data:
        return None
    entries: Entries = {}
    for anchor in soup_of(data).select("a[href^='sql-']"):
        text = anchor.get_text(" ", strip=True)
        href = attr(anchor, "href")
        if not text or text in ("Next", "Prev", "Up", "Home") or href in {e.url.rsplit("/", 1)[-1] for e in entries.values()}:
            continue
        entries[unique_name(entries, text, None)] = Entry(url=f"{base}/{href}", role="SQL command", detail="postgres")
    return entries


def _section_after(page: BeautifulSoup, title: str) -> Tag | None:
    heading = page.find("h2", string=re.compile(rf"^\s*{re.escape(title)}\s*$"))
    return heading.find_parent("div") if heading else None


async def detail_postgres(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    data = await fetch(session, entry.url)
    if not data:
        return None
    page = soup_of(data)
    purpose = page.select_one("div.refnamediv p")
    synopsis = page.select_one("pre.synopsis")
    description = _section_after(page, "Description")
    examples = _section_after(page, "Examples")

    sections = {"Overview": purpose.get_text(" ", strip=True) if purpose else ""}
    if description is not None:
        sections["Description"] = paragraphs(description.find_all("p"), entry.url)
    if examples is not None:
        sections["Examples"] = paragraphs(examples.find_all(["p", "pre"], limit=6), entry.url, limit=6)
    heading = page.select_one("h1") or page.select_one("div.refnamediv h2")
    return detail(
        heading.get_text(" ", strip=True) if heading else entry.url,
        role="SQL command (PostgreSQL)",
        signature=synopsis.get_text().strip() if synopsis else None,
        sections=sections,
        language="sql",
    )


MYSQL_SECTION_NUM = re.compile(r"^\d+(?:\.\d+)*\s+")


async def load_mysql(session: aiohttp.ClientSession, base: str) -> Entries | None:
    pages = await asyncio.gather(
        fetch(session, f"{base}/index.html"),
        fetch(session, f"{base}/sql-statements.html"),
        fetch(session, f"{base}/func-op-summary-ref.html"),
    )
    if not any(pages):
        return None
    entries: Entries = {}
    for data in pages:
        if not data:
            continue
        for anchor in soup_of(data).select("a[href]"):
            href = attr(anchor, "href")
            if not href or "://" in href or href.startswith("#") or not href.split("#")[0].endswith(".html"):
                continue
            text = MYSQL_SECTION_NUM.sub("", anchor.get_text(" ", strip=True))
            if not text or text in ("Next", "Prev", "Up", "Home"):
                continue
            entries[unique_name(entries, text, None)] = Entry(url=urljoin(f"{base}/", href), role="MySQL manual")
    return entries or None


async def load_sqlite(session: aiohttp.ClientSession, base: str) -> Entries | None:
    pages = await asyncio.gather(
        fetch(session, f"{base}/keyword_index.html"),
        fetch(session, f"{base}/doclist.html"),
    )
    if not any(pages):
        return None
    entries: Entries = {}
    for data in pages:
        if not data:
            continue
        for anchor in soup_of(data).select("a[href]"):
            href = attr(anchor, "href")
            text = anchor.get_text(" ", strip=True)
            if not href or not text or href.startswith(("http://", "https://", "javascript:", "#")):
                continue
            if not href.split("#")[0].endswith(".html"):
                continue
            entries[unique_name(entries, text, None)] = Entry(url=urljoin(f"{base}/", href), role="SQLite docs")
    return entries or None


SPHINX_LINE = re.compile(r"(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
LLMS_ENTRY = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _parse_mongodb_inv(data: bytes, base: str) -> Entries:
    stream = io.BytesIO(data)
    if stream.readline().strip() != b"# Sphinx inventory version 2":
        return {}
    stream.readline()
    stream.readline()
    if b"zlib" not in stream.readline():
        return {}
    body = zlib.decompress(stream.read()).decode("utf-8", "replace")
    entries: Entries = {}
    for line in body.splitlines():
        match = SPHINX_LINE.match(line)
        if not match:
            continue
        name, directive, _prio, location, dispname = match.groups()
        if directive not in ("std:label", "std:doc", "mongodb:dbcommand", "mongodb:method", "mongodb:operator", "mongodb:pipeline"):
            continue
        if location.endswith("$"):
            location = location[:-1] + name
        title = name if dispname == "-" else dispname
        role = directive.partition(":")[2]
        entries[unique_name(entries, title, role)] = Entry(url=urljoin(f"{base}/", location), role=role)
    return entries


async def load_mongodb(session: aiohttp.ClientSession, base: str) -> Entries | None:
    inv = await fetch(session, f"{base}/objects.inv")
    if inv:
        entries = await asyncio.to_thread(_parse_mongodb_inv, inv, base)
        if entries:
            return entries
    llms = await fetch(session, "https://www.mongodb.com/docs/llms.txt")
    if not llms:
        return None
    entries = {}
    for title, url in LLMS_ENTRY.findall(llms.decode("utf-8", "replace")):
        clean_url = url.removesuffix(".md")
        if clean_url.startswith(base):
            entries[unique_name(entries, title.strip(), None)] = Entry(url=clean_url, role="MongoDB manual")
    return entries or None


async def load_git(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch(session, base)
    if not data:
        return None
    entries: Entries = {}
    for anchor in soup_of(data).select("a[href^='/docs/git']"):
        slug = attr(anchor, "href").rstrip("/").rsplit("/", 1)[-1]
        if not slug or slug in entries:
            continue
        entries[slug] = Entry(url=f"https://git-scm.com/docs/{slug}", role="git manual page", detail="git")
    return entries


async def detail_git(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    data = await fetch(session, entry.url)
    if not data:
        return None
    page = soup_of(data)
    sections: dict[str, str] = {}
    signature = None
    title = entry.url.rsplit("/", 1)[-1]
    for sect in page.select("div.sect1"):
        heading = sect.find("h2")
        name = heading.get_text(strip=True) if heading else ""
        if name == "NAME":
            first = sect.find("p")
            if first is not None:
                title = first.get_text(" ", strip=True)
        elif name == "SYNOPSIS":
            pre = sect.find("pre")
            signature = pre.get_text().strip() if pre else None
        elif name in ("DESCRIPTION", "OPTIONS", "EXAMPLES"):
            sections[name.capitalize()] = paragraphs(sect.find_all(["p", "pre", "dl"], limit=8), entry.url, limit=8)
    overview = sections.pop("Description", "")
    return detail(title, role=entry.role, signature=signature, sections={"Overview": overview, **sections}, language="sh")


async def search_hoogle(session: aiohttp.ClientSession, query: str, limit: int) -> list[tuple[str, Entry]]:
    url = f"{HOOGLE_URL}?mode=json&hoogle={quote(query)}&start=1&count={limit}"
    data = await fetch(session, url)
    if not data:
        return []
    try:
        results = json.loads(data)
    except ValueError:
        return []

    matches: list[tuple[str, Entry]] = []
    seen: set[str] = set()
    for item in results:
        signature = BeautifulSoup(item.get("item", ""), "lxml").get_text(" ", strip=True)
        url = item.get("url") or ""
        if not signature or url in seen:
            continue
        seen.add(url)
        package = (item.get("package") or {}).get("name")
        module = (item.get("module") or {}).get("name")
        role = DOT.join(part for part in (package, module) if part) or None
        name = signature.split(" :: ", 1)[0]
        matches.append((name, Entry(url=url, role=role, detail="hoogle", signature=signature, summary=to_markdown(item.get("docs", ""), HOOGLE_URL))))
    return matches


async def detail_hoogle(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    return detail(
        entry.signature or entry.url, role=entry.role, signature=entry.signature, sections={"Overview": entry.summary or ""}, language="haskell"
    )


Loader = Callable[["aiohttp.ClientSession", str], "Awaitable[Entries | None]"]
Fetcher = Callable[["aiohttp.ClientSession", Entry], "Awaitable[DetailInfo | None]"]

LOADERS: dict[str, Loader] = {
    "mdn": load_mdn,
    "cppreference": load_cppreference,
    "rust": load_rust,
    "postgres": load_postgres,
    "mysql": load_mysql,
    "sqlite": load_sqlite,
    "mongodb": load_mongodb,
    "git": load_git,
}

DETAILS: dict[str, Fetcher] = {
    "mdn": detail_mdn,
    "cppreference": detail_cppreference,
    "cpp": detail_cppreference,
    "c": detail_cppreference,
    "rust": detail_rust,
    "postgres": detail_postgres,
    "git": detail_git,
    "hoogle": detail_hoogle,
}


NODE_PAGES_SKIPPED = frozenset({"index.html", "all.html"})
NODE_PREFIX = re.compile(r"^(Class|Event|Type|Static method|Namespace|Constructor)\s*:\s*(.+)$")
NODE_HEADINGS = "h1, h2, h3, h4, h5"


def _node_entries(data: bytes, page: str) -> list[tuple[str, str, str]]:
    """``(name, role, anchor)`` for every heading of one API page. The anchor is empty for the page itself."""
    module = page.removesuffix(".html")
    root = soup_of(data)
    content = root.select_one("#apicontent") or root
    found: list[tuple[str, str, str]] = []
    owner = module  # events are named after the class they sit under: `net.Socket 'close'`
    for heading in content.select(NODE_HEADINGS):
        mark = heading.select_one("a.mark[id]")
        if mark is None:
            continue
        text = " ".join(heading.get_text().split()).rstrip("#").strip()
        if not text:
            continue
        anchor = attr(mark, "id")
        if heading.name == "h1":
            found.append((module, "module", ""))
            if text.lower() != module.lower():
                found.append((text, "module", ""))
            continue

        prefixed = NODE_PREFIX.match(text)
        if prefixed:
            role, name = prefixed[1].lower(), prefixed[2]
        elif text.startswith("new "):
            role, name = "constructor", text[4:]
        elif "(" in text:
            role, name = "method", text
        elif " " not in text and "." in text:  # `process.argv`
            role, name = "property", text
        else:
            found.append((f"{module}: {text}", "section", anchor))
            continue

        name = name.split("(", 1)[0].strip() or name
        if role == "class":
            owner = name
        elif role == "event":
            name = f"{owner} {name}"
        found.append((name, role, anchor))
    return found


async def load_nodejs(session: aiohttp.ClientSession, base: str) -> Entries | None:
    index = await fetch(session, f"{base}/index.html")
    if not index:
        return None
    pages: list[str] = []
    for anchor in soup_of(index).select("a[href$='.html']"):
        href = attr(anchor, "href").partition("#")[0]
        if href and "/" not in href and href not in NODE_PAGES_SKIPPED and href not in pages:
            pages.append(href)

    semaphore = asyncio.Semaphore(SUBINDEX_CONCURRENCY)

    async def load_page(page: str) -> tuple[str, list[tuple[str, str, str]]]:
        async with semaphore:
            data = await fetch(session, f"{base}/{page}")
        return page, (await asyncio.to_thread(_node_entries, data, page) if data else [])

    entries: Entries = {}
    for page, found in await asyncio.gather(*(load_page(page) for page in pages)):
        module = page.removesuffix(".html")
        for name, role, anchor in found:
            url = f"{base}/{page}" + (f"#{anchor}" if anchor else "")
            entries[unique_name(entries, name, module)] = Entry(url=url, role=role)
    return entries or None


GO_ORIGIN = "https://pkg.go.dev"
GO_API_LISTING = "https://api.github.com/repos/golang/go/contents/api"
GO_API_RAW = "https://raw.githubusercontent.com/golang/go/master/api"
GO_API_FILE = re.compile(r"go1(?:\.\d+)?\.txt")
GO_API_LINE = re.compile(r"^pkg (\S+?)(?: \([^)]*\))?, (const|func|method|type|var) (.+)$")  # `(darwin-amd64)` is optional
GO_NAME = re.compile(r"\w+")
GO_METHOD = re.compile(r"\(\*?(\w+)(?:\[[^\]]*\])?\)\s*(\w+)")
GO_TYPE_MEMBER = re.compile(r"\w+(?:\[.*?\])?\s+(?:struct|interface),")  # `type Header struct, Name string`
GO_VERSION_SEGMENT = re.compile(r"v\d+")
GO_API_CDN = "https://cdn.jsdelivr.net/gh/golang/go@master/api"
GO_SITE = PageSite(
    "go",
    (".Documentation-content", ".UnitDetails-content", *DEFAULT_CONTENT),
    ".Documentation-sinceVersion, .Documentation-idLink, .Documentation-exampleButtonsContainer",
)


def _go_symbols(text: str) -> dict[tuple[str, str], tuple[str, str]]:
    """One ``api/*.txt`` file as ``{(package, anchor): (kind, signature)}``."""
    found: dict[tuple[str, str], tuple[str, str]] = {}
    for line in text.splitlines():
        match = GO_API_LINE.match(line)
        if match is None:
            continue
        package, kind, rest = match.groups()
        if kind == "method":
            parts = GO_METHOD.match(rest)
            if parts is None:
                continue
            anchor = f"{parts[1]}.{parts[2]}"
        else:
            if kind == "type" and GO_TYPE_MEMBER.match(rest):  # a field or interface method, not the type itself
                continue
            name = GO_NAME.match(rest)
            if name is None:
                continue
            anchor = name[0]
        signature = f"func {rest}" if kind in ("func", "method") else f"{kind} {rest}"
        found.setdefault((package, anchor), (kind, signature))
    return found


def _go_short(package: str) -> str:
    """`net/http` is called `http`, and `math/rand/v2` is called `rand`."""
    parts = package.split("/")
    return parts[-2] if len(parts) > 1 and GO_VERSION_SEGMENT.fullmatch(parts[-1]) else parts[-1]


async def load_go(session: aiohttp.ClientSession, base: str) -> Entries | None:
    listing = await fetch(session, GO_API_LISTING)
    try:
        parsed = json.loads(listing) if listing else []
        names = [item["name"] for item in parsed if isinstance(item, dict) and "name" in item] if isinstance(parsed, list) else []
    except ValueError, KeyError, TypeError:
        names = []
    files = [name for name in names if GO_API_FILE.fullmatch(name)]
    if not files:
        files = ["go1.txt", *(f"go1.{version}.txt" for version in range(1, 28))]

    semaphore = asyncio.Semaphore(SUBINDEX_CONCURRENCY)

    async def load_file(name: str) -> dict[tuple[str, str], tuple[str, str]]:
        async with semaphore:
            data = await fetch(session, f"{GO_API_RAW}/{name}", retries=1)
            if not data:
                data = await fetch(session, f"{GO_API_CDN}/{name}", retries=1)
        return await asyncio.to_thread(_go_symbols, data.decode("utf-8", "replace")) if data else {}

    symbols: dict[tuple[str, str], tuple[str, str]] = {}
    for found in await asyncio.gather(*(load_file(name) for name in files)):
        for key, value in found.items():
            symbols.setdefault(key, value)

    entries: Entries = {}
    if symbols:
        for package in sorted({package for package, _ in symbols}):
            entries[unique_name(entries, package, "package")] = Entry(url=f"{GO_ORIGIN}/{package}", role="package", detail="go")
        for (package, anchor), (kind, signature) in sorted(symbols.items()):
            name = unique_name(entries, f"{_go_short(package)}.{anchor}", package)
            entries[name] = Entry(
                url=f"{GO_ORIGIN}/{package}#{anchor}",
                role=f"{kind} {DOT} {package}",
                detail="go",
                signature=signature,
            )
        return entries

    # Fallback: scrape standard library packages from https://pkg.go.dev/std if GitHub/CDN are unreachable
    std_page = await fetch(session, base)
    if not std_page:
        return None
    for anchor in soup_of(std_page).select("div.StdLib-directories a[href], table a[href]"):
        pkg = attr(anchor, "href").strip("/")
        if pkg and not pkg.startswith(("http", "std", "internal")) and "/internal" not in pkg:
            entries[unique_name(entries, pkg, "package")] = Entry(url=f"{GO_ORIGIN}/{pkg}", role="package", detail="go")
    return entries or None


async def detail_go(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    path, _, anchor = entry.url.removeprefix(f"{GO_ORIGIN}/").partition("#")
    title = f"{path}.{anchor}" if anchor else path
    info = await detail_page(session, entry, GO_SITE)
    if info is None:
        if not entry.signature:
            return None
        text = f"Documented in the [{path}]({GO_ORIGIN}/{path}) package."
        return detail(title, role=entry.role, signature=entry.signature, sections={"Overview": text}, language="go")
    return replace(info, qualname=title, signature=info.signature or entry.signature)


PHP_SKIPPED_SECTIONS = frozenset({"See Also", "User Contributed Notes"})
PHP_NAMESPACE_OR_UNDERSCORE = re.compile(r"[\\_]")

PHP_SITE = PageSite(
    "php",
    ("#layout-content", *DEFAULT_CONTENT),
    "#usernotes, .manualnavbar, .page-tools, .up, .prev, .next",
)


def _php_entries(data: bytes, base: str) -> Entries:
    page = soup_of(data)
    root = page.select_one("#layout-content") or page
    entries: Entries = {}
    classes: set[str] = set()
    for item in root.select("li"):
        link = item.find("a", href=True)
        if link is None:
            continue
        href = attr(link, "href")
        if not href.endswith(".php") or "/" in href or "://" in href:
            continue
        name = link.get_text(strip=True).removesuffix("()")
        if not name:
            continue
        if "::" in name:
            role = "method"
            classes.add(name.partition("::")[0])
        else:
            role = "function"
        entries[unique_name(entries, name, role)] = Entry(url=f"{base}/{href}", role=role, detail="php")

    for name in sorted(classes):  # the index lists methods only, so derive the class pages from them
        slug = PHP_NAMESPACE_OR_UNDERSCORE.sub("-", name.lower())
        entries.setdefault(name, Entry(url=f"{base}/class.{slug}.php", role="class", detail="php"))
    return entries


async def load_php(session: aiohttp.ClientSession, base: str) -> Entries | None:
    data = await fetch(session, f"{base}/indexes.functions.php")
    if not data:
        return None
    entries = await asyncio.to_thread(_php_entries, data, base)
    return entries or None


def _php_code_blocks(page: BeautifulSoup) -> None:
    """php.net writes code as `<div class="phpcode"><code>..<br/>..</code></div>`, which would flatten to one line."""
    for block in page.select("div.phpcode, div.cdata"):
        for line_break in block.find_all("br"):
            line_break.replace_with("\n")
        code = block.get_text().replace("\xa0", " ").strip("\n")
        pre = page.new_tag("pre", attrs={"class": "language-php"})
        pre.string = code
        block.replace_with(pre)


def _render_php(data: bytes, entry: Entry) -> DetailInfo | None:
    page = soup_of(data)
    refsections = page.select("div.refsect1")
    if not refsections:  # class pages and book pages have no refentry
        return None
    heading = page.select_one("h1.refname") or page.select_one("h1")
    purpose = page.select_one(".refpurpose .dc-title")
    synopsis = page.select_one("div.methodsynopsis")
    signature = " ".join(synopsis.get_text().split()) if synopsis is not None else None
    _php_code_blocks(page)

    sections: dict[str, str] = {"Overview": purpose.get_text(" ", strip=True) if purpose is not None else ""}
    for section in refsections:
        title = section.select_one("h3.title")
        label = " ".join(title.get_text().split()) if title is not None else "Section"
        if label in PHP_SKIPPED_SECTIONS:
            continue
        if title is not None:
            title.decompose()
        for shown in section.select("div.methodsynopsis"):  # already used as the signature
            shown.decompose()
        text = to_markdown(section, entry.url)
        if not text:
            continue
        if label == "Description":
            sections["Overview"] = f"{sections['Overview']}\n\n{text}".strip()
        else:
            sections[label] = text
    name = heading.get_text(strip=True) if heading is not None else entry.url
    return detail(name, role=entry.role, signature=signature, sections=sections, language="php")


async def detail_php(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    data = await fetch(session, entry.url)
    if not data:
        return None
    info = await asyncio.to_thread(_render_php, data, entry)
    return info if info is not None else await detail_page(session, entry, PHP_SITE)


EXTRA_LOADERS = {
    "nodejs": load_nodejs,
    "go": load_go,
    "php": load_php,
}

EXTRA_DETAILS = {
    "go": detail_go,
    "php": detail_php,
}

MKDOCS_CONTENT = ("article.md-content__inner", *DEFAULT_CONTENT)

# Sites rendered by the generic page renderer. Python-library sites are listed too so their code fences are right.
EXTRA_PAGE_SITES: dict[str, PageSite] = {
    "nodejs": PageSite("js", ("#apicontent", *DEFAULT_CONTENT)),
    "php": PHP_SITE,
    "go": GO_SITE,
    "svelte": PageSite("js"),
    "typescript": PageSite("ts"),
    "tailwind": PageSite("css"),
    "bootstrap": PageSite("html"),
    "starlette": PageSite("py", MKDOCS_CONTENT),
    "uvicorn": PageSite("py", MKDOCS_CONTENT),
    "typer": PageSite("py", MKDOCS_CONTENT),
    "sqlmodel": PageSite("py", MKDOCS_CONTENT),
    "textual": PageSite("py", MKDOCS_CONTENT),
    "ruff": PageSite("py", MKDOCS_CONTENT),
    "uv": PageSite("sh", MKDOCS_CONTENT),
    "mkdocs": PageSite("py", MKDOCS_CONTENT),
}

GENERIC_SITE = PageSite(
    "py",
    ("article.md-content__inner", "[role=main]", "article.bd-article", "div.body", "main", "article"),
    ".viewcode-link, .sphinxsidebar",
)
GENERIC_KINDS = frozenset({"sphinx", "mkdocs", "llms", "sitemap"})

# Inject
PAGE_SITES: dict[str, PageSite] = {**PAGE_SITES, **EXTRA_PAGE_SITES, **dict.fromkeys(GENERIC_KINDS, GENERIC_SITE)}
LOADERS: dict[str, Loader] = {**LOADERS, **EXTRA_LOADERS}
DETAILS: dict[str, Fetcher] = {**DETAILS, **EXTRA_DETAILS}
