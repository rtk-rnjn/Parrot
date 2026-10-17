"""Language syntax and concepts: `$syntax rust match` finds the reference section, not an API entry.

Each curated language has a few references (specifications, tutorials, guides) indexed by section title, and the
matching section is rendered in chat. When none of them covers the topic, or the language is not curated, the web is
searched for documentation instead.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urljoin, urlsplit

import aiohttp
import discord
from bs4 import Tag
from bs4.element import Comment, NavigableString
from discord.ext import commands, tasks

from .docs import ResultsView, parse_sphinx
from .references import (
    CPP_ORIGIN,
    HEADERS,
    HTTP_OK,
    REQUEST_TIMEOUT,
    DetailInfo,
    Entries,
    Entry,
    attr,
    detail,
    detail_mdn,
    fetch,
    fetch_shared,
    load_mdn,
    soup_of,
    to_markdown,
    unique_name,
)
from .search import SiteIndex, tokens

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bs4 import BeautifulSoup
    from bs4.element import PageElement

    from core import Bot

log = logging.getLogger(__name__)

HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
NAV_WORDS = frozenset({"Next", "Prev", "Previous", "Up", "Home", "Contents", "Index"})
NUMBERING = re.compile(r"^\d+(?:\.\d+)*\.?\s+")  # "14.11. The switch Statement"
TOC_SCRIPT = re.compile(r"innerHTML\s*=\s*'(.*?)';", re.S)  # mdBook keeps its table of contents in a script
STOPWORDS = frozenset({"a", "an", "the", "of", "in", "to", "and", "or", "how", "do", "i", "is", "what", "with", "use", "using"})
MAX_SNIPPET = 160
WEB_RESULTS = 8
DDG_URL = "https://html.duckduckgo.com/html/"

PYTHON = "https://docs.python.org/3"
JAVA_TUTORIAL = "https://docs.oracle.com/javase/tutorial/"
JLS = "https://docs.oracle.com/javase/specs/jls/se21/html/"
RUST = "https://doc.rust-lang.org"

type Loader = Callable[[aiohttp.ClientSession], Awaitable[Entries | None]]


@dataclass(frozen=True)
class Extractor:
    """Where a source keeps a page's content and what to strip from it before rendering."""

    root: str  # selectors in order of preference; the innermost wrapper first so headings stay direct children
    junk: str = ""

    def find_root(self, page: BeautifulSoup) -> Tag:
        return next((found for selector in self.root.split(",") if (found := page.select_one(selector.strip()))), None) or page.body or page


EXTRACTORS: dict[str, Extractor] = {
    "sphinx": Extractor("div.body, [role=main]"),
    "oracle": Extractor("#PageContent"),
    "jls": Extractor("div.chapter, body", ".navheader, .navfooter"),
    "cppreference": Extractor("#mw-content-text .mw-parser-output, #mw-content-text", ".t-navbar, .toc, .t-example-live-link"),
    "mdbook": Extractor("main", ".rule, .grammar-railroad, .buttons"),
    "go": Extractor("article, main"),
}


@dataclass(frozen=True)
class Language:
    aliases: tuple[str, ...]
    sources: tuple[Loader, ...]
    domains: tuple[str, ...]  # documentation hosts that web results from are listed first


async def load_sphinx_areas(session: aiohttp.ClientSession, base: str, areas: dict[str, str]) -> Entries | None:
    """Section labels and glossary terms of a Sphinx site, kept only under the given paths."""
    data = await fetch(session, f"{base}/objects.inv")
    if not data:
        return None
    inventory = await asyncio.to_thread(parse_sphinx, data, base)
    entries: Entries = {}
    for key, found in inventory.items():
        kind, _, name = key.partition(":")
        if kind not in ("label", "term"):
            continue
        path = found.url.removeprefix(f"{base}/")
        role = next((label for prefix, label in areas.items() if path.startswith(prefix)), None)
        if role is not None:
            entries[unique_name(entries, name, role)] = Entry(url=found.url, role=role, detail="sphinx")
    return entries


async def load_links(
    session: aiohttp.ClientSession,
    page_url: str,
    selector: str,
    role: str,
    kind: str,
    resolve: Callable[[str], str | None],
) -> Entries | None:
    """Every link an index page lists, named by its text."""
    data = await fetch(session, page_url)
    if not data:
        return None
    entries: Entries = {}
    seen: set[str] = set()
    for anchor in soup_of(data).select(selector):
        name = NUMBERING.sub("", " ".join(anchor.get_text().split()))
        url = resolve(attr(anchor, "href"))
        if not name or name in NAV_WORDS or url is None or url in seen:
            continue
        seen.add(url)
        entries[unique_name(entries, name, role)] = Entry(url=url, role=role, detail=kind)
    return entries


async def load_headings(session: aiohttp.ClientSession, page_url: str, root: str, role: str, kind: str) -> Entries | None:
    """One long page whose headings carry ids, such as the Go specification."""
    data = await fetch(session, page_url)
    if not data:
        return None
    page = soup_of(data)
    container = page.select_one(root) or page
    entries: Entries = {}
    for heading in container.select("h2[id], h3[id], h4[id]"):
        name = clean_heading(heading)
        if name:
            entries[unique_name(entries, name, role)] = Entry(url=f"{page_url}#{attr(heading, 'id')}", role=role, detail=kind)
    return entries


async def load_mdbook(session: aiohttp.ClientSession, base: str, role: str) -> Entries | None:
    """An mdBook's table of contents, which lives in a hashed `toc-*.js` named by the index page."""
    index = await fetch(session, f"{base}/index.html")
    if not index:
        return None
    script = next((attr(tag, "src") for tag in soup_of(index).select("script[src]") if "toc-" in attr(tag, "src")), None)
    data = await fetch(session, urljoin(f"{base}/", script)) if script else None
    match = TOC_SCRIPT.search(data.decode("utf-8", "replace")) if data else None
    if match is None:
        return None
    entries: Entries = {}
    for anchor in soup_of(match[1].replace("\\'", "'")).select("a[href]"):
        for number in anchor.select("strong"):
            number.decompose()
        name, href = " ".join(anchor.get_text().split()), attr(anchor, "href")
        if name and href and not href.startswith(("http", "#")):
            entries[unique_name(entries, name, role)] = Entry(url=urljoin(f"{base}/", href), role=role, detail="mdbook")
    return entries


async def load_mdn_language(session: aiohttp.ClientSession) -> Entries | None:
    """MDN's JavaScript tree without the built-in objects, which `rtfd js` already covers."""
    found = await load_mdn(session, "https://developer.mozilla.org/en-US/docs/Web/JavaScript")
    if not found:
        return None
    return {name: entry for name, entry in found.items() if not (entry.role or "").startswith(("Reference / Global Objects", "Reference / Errors"))}


def tutorial_url(href: str) -> str | None:
    url = urljoin(JAVA_TUTORIAL, href)
    return url if "/tutorial/java/" in url or "/tutorial/essential/" in url else None


def cppreference_url(href: str) -> str | None:
    return f"{CPP_ORIGIN}{href}" if href.startswith("/") else None


LANGUAGES: dict[str, Language] = {
    "python": Language(
        ("py",),
        (
            functools.partial(
                load_sphinx_areas,
                base=PYTHON,
                areas={"reference/": "language reference", "tutorial/": "tutorial", "glossary": "glossary", "faq/": "FAQ"},
            ),
        ),
        ("docs.python.org", "peps.python.org"),
    ),
    "java": Language(
        ("jdk",),
        (
            functools.partial(
                load_links,
                page_url=f"{JAVA_TUTORIAL}reallybigindex.html",
                selector="a[href$='.html']",
                role="tutorial",
                kind="oracle",
                resolve=tutorial_url,
            ),
            functools.partial(
                load_links, page_url=f"{JLS}index.html", selector="a[href^='jls-']", role="JLS", kind="jls", resolve=lambda href: urljoin(JLS, href)
            ),
        ),
        ("docs.oracle.com", "dev.java"),
    ),
    "c": Language(
        (),
        (
            functools.partial(
                load_links,
                page_url=f"{CPP_ORIGIN}/c/language",
                selector="#mw-content-text a[href^='/c/language/']",
                role="language",
                kind="cppreference",
                resolve=cppreference_url,
            ),
        ),
        ("en.cppreference.com",),
    ),
    "cpp": Language(
        ("c++", "cxx"),
        (
            functools.partial(
                load_links,
                page_url=f"{CPP_ORIGIN}/cpp/language",
                selector="#mw-content-text a[href^='/cpp/language/']",
                role="language",
                kind="cppreference",
                resolve=cppreference_url,
            ),
        ),
        ("en.cppreference.com", "isocpp.org"),
    ),
    "rust": Language(
        ("rs",),
        (
            functools.partial(load_mdbook, base=f"{RUST}/reference", role="reference"),
            functools.partial(load_mdbook, base=f"{RUST}/book", role="book"),
            functools.partial(load_mdbook, base=f"{RUST}/rust-by-example", role="by example"),
        ),
        ("doc.rust-lang.org",),
    ),
    "js": Language(("javascript", "ecmascript", "es"), (load_mdn_language,), ("developer.mozilla.org", "javascript.info")),
    "go": Language(
        ("golang",),
        (
            functools.partial(load_headings, page_url="https://go.dev/ref/spec", root="article", role="specification", kind="go"),
            functools.partial(load_headings, page_url="https://go.dev/doc/effective_go", root="article", role="Effective Go", kind="go"),
        ),
        ("go.dev", "pkg.go.dev"),
    ),
}

ALIASES: dict[str, str] = {}
for _name, _language in LANGUAGES.items():
    ALIASES[_name] = _name
    for _alias in _language.aliases:
        ALIASES[_alias] = _name


async def build_language(session: aiohttp.ClientSession, name: str) -> SiteIndex | None:
    results = await asyncio.gather(*(loader(session) for loader in LANGUAGES[name].sources), return_exceptions=True)
    entries: Entries = {}
    for loader, result in zip(LANGUAGES[name].sources, results, strict=True):
        if isinstance(result, BaseException):
            log.warning("%s: %r failed: %r", name, loader, result)
            continue
        for key, entry in (result or {}).items():
            entries[unique_name(entries, key, entry.role)] = entry
    return SiteIndex.build(name, entries) if entries else None


def clean_heading(heading: Tag) -> str:
    return " ".join(heading.get_text(" ").split()).replace("\N{PILCROW SIGN}", "").strip()


def is_section(tag: Tag) -> bool:
    return tag.name == "section" or (tag.name == "div" and "section" in (tag.get("class") or []))


def locate(root: Tag, anchor: str) -> Tag | None:
    """The element an anchor names: a section, a heading, or a glossary term."""
    target = root.find(id=anchor) or root.find("a", attrs={"name": anchor})
    if target is None:
        return None
    if is_section(target) or target.name == "dt":
        return target
    # Sphinx and JLS put an empty span or <a name> next to the heading; cppreference anchors the span inside it.
    heading = target if target.name in HEADINGS else target.find_parent(HEADINGS)
    if heading is not None:
        section = heading.find_parent(is_section)
        return section if section is not None and section.find(HEADINGS) is heading else heading
    return next((ancestor for ancestor in target.parents if ancestor is root or is_section(ancestor)), None)


def part_of(target: Tag) -> tuple[str | None, list[PageElement]]:
    """The title of the anchored part and the nodes that make it up."""
    if target.name == "dt":
        definition = target.find_next_sibling("dd")
        return clean_heading(target), [definition] if definition is not None else []
    if is_section(target):
        heading = target.find(HEADINGS)
        title = clean_heading(heading) if heading is not None else None
        if heading is not None:
            heading.decompose()  # the picker shows the title; do not repeat it in the body
        return title, list(target.children)
    level = int(target.name[1])  # a heading on a flat page: everything up to the next one of its level or above
    nodes: list[PageElement] = []
    for sibling in target.next_siblings:
        if isinstance(sibling, Tag) and sibling.name in HEADINGS and int(sibling.name[1]) <= level:
            break
        nodes.append(sibling)
    return clean_heading(target), nodes


def split_sections(nodes: list[PageElement], base: str) -> tuple[str | None, dict[str, str]]:
    """Headings and nested sections become picker entries; everything else is rendered under the current one.

    A heading that comes before any content is the page's own title (an h1, or an h2 in a book whose h1 is the book).
    """
    sections: dict[str, list[str]] = {"Overview": []}
    current = "Overview"
    title: str | None = None
    for node in nodes:
        if isinstance(node, Comment):
            continue
        if isinstance(node, NavigableString):
            if text := " ".join(node.split()):
                sections[current].append(text)
            continue
        if not isinstance(node, Tag):
            continue
        if node.name in HEADINGS:
            if title is None and not any(sections.values()):
                title = clean_heading(node)
                continue
            current = clean_heading(node) or current
            sections.setdefault(current, [])
            continue
        if is_section(node) and (heading := node.find(HEADINGS)) is not None:
            current = clean_heading(heading) or current
            sections.setdefault(current, [])
            heading.decompose()
        if markdown := to_markdown(node, base):
            sections[current].append(markdown)
    return title, {name: "\n\n".join(parts) for name, parts in sections.items() if parts}


def render_page(data: bytes, url: str, anchor: str, extractor: Extractor, role: str | None) -> DetailInfo:
    page = soup_of(data)
    root = extractor.find_root(page)
    if extractor.junk:
        for junk in root.select(extractor.junk):
            junk.decompose()
    target = locate(root, anchor) if anchor else None
    if target is None:  # a Sphinx page is one top-level section: open it so its subsections become picker entries
        children = [child for child in root.children if isinstance(child, Tag)]
        tops = [child for child in children if is_section(child)]
        if len(tops) == 1 and not any(child.get_text(strip=True) for child in children if child is not tops[0]):
            target = tops[0]
    title, nodes = part_of(target) if target is not None else (None, list(root.children))
    leading, sections = split_sections(nodes, url)
    if title is None and leading is None:  # cppreference and the Java tutorials keep the title outside the content
        heading = page.find("h1") or page.title
        leading = clean_heading(heading) if heading is not None else None
    return detail(title or leading or url, role=role, signature=None, sections=sections, language="text")


async def search_web(session: aiohttp.ClientSession, query: str, domains: tuple[str, ...]) -> list[tuple[str, Entry]]:
    """DuckDuckGo's HTML results, documentation hosts first."""
    try:
        async with session.post(DDG_URL, data={"q": query}, headers=HEADERS, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status != HTTP_OK:
                return []
            data = await resp.read()
    except TimeoutError, aiohttp.ClientError:
        return []

    found: list[tuple[str, str, str]] = []
    for result in soup_of(data).select("div.result"):
        link = result.select_one("a.result__a")
        if link is None or "result--ad" in (result.get("class") or []):
            continue
        href = attr(link, "href")
        if href.startswith("//"):
            href = f"https:{href}"
        url = parse_qs(urlsplit(href).query).get("uddg", [href])[0]
        snippet = result.select_one(".result__snippet")
        text = " ".join(snippet.get_text().split()) if snippet is not None else ""
        if len(text) > MAX_SNIPPET:
            text = text[: MAX_SNIPPET - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"
        found.append((" ".join(link.get_text().split()), url, text))
    found.sort(key=lambda hit: not urlsplit(hit[1]).netloc.endswith(domains))

    entries: Entries = {}
    for title, url, text in found[:WEB_RESULTS]:
        entries[unique_name(entries, title or url, None)] = Entry(url=url.replace("(", "%28").replace(")", "%29"), role=text or None)
    return list(entries.items())


def shares_word(query_words: set[str], name: str) -> bool:
    """`pointer` counts for "Pointers" and `records` for "Record Classes": one word must be a prefix of the other."""
    name_words = tokens(name).split()
    return any(w == n or (min(len(w), len(n)) >= 3 and (n.startswith(w) or w.startswith(n))) for w in query_words for n in name_words)


def relevant(query: str, matches: list[tuple[str, Entry]]) -> bool:
    """Fuzzy search always returns something; it is only worth showing when a top hit shares a real word with the query."""
    words = set(tokens(query).split()) - STOPWORDS
    if not words:
        return bool(matches)
    return any(shares_word(words, name) for name, _entry in matches[:3])


class SyntaxResults(ResultsView):
    """Curated results with a way out to the web when they are not enough."""

    def __init__(self, cog: Syntax, site: str, matches: list[tuple[str, Entry]], author_id: int, footer: str, *, language: str, topic: str) -> None:
        self.syntax, self.language, self.topic = cog, language, topic
        super().__init__(cog, site, matches, author_id, footer)

    def actions(self) -> list[discord.ui.Item]:
        return [self.button("Search the web", self.on_web)]

    def rebuild(self) -> ResultsView:
        return SyntaxResults(self.syntax, self.site, self.matches, self.author_id, self.footer, language=self.language, topic=self.topic)

    async def on_web(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        view = await self.syntax.web_view(self.language, self.topic, interaction.user)
        if view is None:
            await interaction.followup.send("Bot found nothing on the web either.", ephemeral=True)
            return
        view.message = interaction.message
        self.stop()
        await interaction.edit_original_response(view=view)


class Syntax(commands.Cog, command_attrs={"hidden": True}, name="Language Syntax"):
    """How things are written in a language: statements, expressions, declarations and idioms, from its own references."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.indexes: dict[str, SiteIndex] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def cog_load(self) -> None:
        self.refresh.start()

    async def cog_unload(self) -> None:
        self.refresh.cancel()

    @tasks.loop(hours=12)
    async def refresh(self) -> None:
        await asyncio.gather(*(self.load_language(name, force=True) for name in LANGUAGES))

    async def load_language(self, name: str, *, force: bool = False) -> SiteIndex | None:
        if not force and name in self.indexes:
            return self.indexes[name]
        async with self._locks[name]:
            if not force and name in self.indexes:
                return self.indexes[name]
            index = await build_language(self.bot.http_session, name)
            if index is not None:  # on failure keep the old index
                self.indexes[name] = index
                log.info("%s syntax: %s", name, index.describe())
            return self.indexes.get(name)

    async def get_detail(self, site: str, entry: Entry) -> DetailInfo | None:
        if entry.detail == "mdn":
            return await detail_mdn(self.bot.http_session, entry)
        extractor = EXTRACTORS.get(entry.detail or "")
        if extractor is None:
            return None
        url, _, anchor = entry.url.partition("#")
        data = await fetch_shared(self.bot.http_session, url)
        if not data:
            return None
        return await asyncio.to_thread(render_page, data, url, anchor, extractor, entry.role)

    async def web_view(self, language: str, topic: str, requester: discord.abc.User) -> ResultsView | None:
        domains = LANGUAGES[language].domains if language in LANGUAGES else ()
        matches = await search_web(self.bot.http_session, f"{language} {topic}", domains)
        if not matches:
            return None
        footer = f"Requested by {requester} \N{MIDDLE DOT} web results from DuckDuckGo"
        return ResultsView(self, f"{language} syntax", matches, requester.id, footer)

    @commands.command(name="syntax", aliases=["lang", "howto"])
    async def syntax(
        self,
        ctx: commands.Context,
        language: str | None = commands.parameter(description="Which language", default=None),
        *,
        topic: str | None = commands.parameter(description="The statement, construct or idea to look up", default=None),
    ):
        """Look up how something is written in a language: `syntax rust match`, `syntax python comprehension`.

        `python`, `java`, `c`, `cpp`, `rust`, `js` and `go` are answered from their references, tutorials and guides,
        with the section shown in chat. Any other language, or a topic those do not cover, is searched on the web.
        """
        if language is None:
            await ctx.send("Curated languages: " + ", ".join(f"`{n}`" for n in LANGUAGES) + ". Anything else is searched on the web.")
            return
        if topic is None:
            await ctx.send(f"Bot needs a topic as well, like `{ctx.clean_prefix}syntax {language} for loop`.")
            return

        name = ALIASES.get(language.lower())
        async with ctx.typing():
            matches: list[tuple[str, Entry]] = []
            index = await self.load_language(name) if name else None
            if index is not None:
                matches = await index.search_async(topic)
            if name is not None and index is not None and relevant(topic, matches):
                footer = f"Requested by {ctx.author} \N{MIDDLE DOT} {index.describe()}"
                view: ResultsView | None = SyntaxResults(self, f"{name} syntax", matches, ctx.author.id, footer, language=name, topic=topic)
            else:
                view = await self.web_view(name or language.lower(), topic, ctx.author)
        if view is None:
            await ctx.send("Bot found no documentation for that, in its references or on the web.")
            return
        view.message = await ctx.send(view=view)
