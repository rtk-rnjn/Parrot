"""JDK Javadoc: packages, types and members from its search indexes, with dotted chains resolved through the pages.

``System.out.println`` walks from ``System`` through the type of its ``out`` field to ``PrintStream.println``, and a
member a class only inherits is followed to the class that declares it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import quote, unquote, urljoin

from .references import DetailInfo, Entries, Entry, attr, detail, fetch, fetch_shared, soup_of, to_markdown, unique_name
from .search import MAX_RESULTS, SiteIndex

if TYPE_CHECKING:
    import aiohttp
    from bs4 import BeautifulSoup, Tag

log = logging.getLogger(__name__)

MAX_HOPS = 4
ONE_LINE_SIGNATURE = 90
WELL_KNOWN = ("java.lang", "java.util", "java.io")
# Notes under a description: short facts stay in the overview, "All ..." and "Direct ..." describe the hierarchy,
# and anything else (Parameters, Returns, Throws, See Also, API Note, ...) becomes a section of its own.
INLINE_NOTES = frozenset({"Since", "Specified by", "Overrides", "Enclosing class", "Enclosing interface", "Functional Interface"})
KINDS = {
    "field-details": "field",
    "constant-details": "enum constant",
    "constructor-details": "constructor",
    "method-details": "method",
    "element-details": "element",
}
PARAM = re.compile(r"^`([^`\n]+)` - ", re.M)  # Javadoc writes parameters as `name` - description
GENERICS = re.compile(r"<[^<>]*>")
SEGMENT = re.compile(r"[^.#:\s()]+(?:\([^()]*\)?)?")  # a name with its argument list, if any, kept together


class Member(NamedTuple):
    name: str  # display name in the index, `PrintStream.println(String)`
    entry: Entry
    label: str  # `println(String)`
    anchor: str  # `println(java.lang.String)`: the section id on the class page


@dataclass(frozen=True, slots=True)
class JavaType:
    package: str
    name: str  # simple name, dotted for nested classes
    url: str
    display: str
    entry: Entry

    @property
    def qualname(self) -> str:
        return f"{self.package}.{self.name}"


def package_rank(package: str) -> tuple[int, str]:
    """The plain display name goes to the package people mean first: java.lang, java.util, java.io, java.*, javax.*."""
    if package in WELL_KNOWN:
        return (WELL_KNOWN.index(package), package)
    if package.startswith("java."):
        return (len(WELL_KNOWN), package)
    if package.startswith("javax."):
        return (len(WELL_KNOWN) + 1, package)
    return (len(WELL_KNOWN) + 2, package)


def js_index(data: bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8", "replace")
    start, end = text.find("["), text.rfind("]")
    return json.loads(text[start : end + 1]) if start >= 0 and end > start else []


def page_url(base: str, module: str | None, path: str) -> str:
    return f"{base}/{module}/{path}" if module else f"{base}/{path}"


def split_query(query: str) -> list[str]:
    """``java.io.PrintStream#println(java.lang.String)`` -> ``["java", "io", "PrintStream", "println(java.lang.String)"]``."""
    parts = SEGMENT.findall(GENERICS.sub("", query))
    if parts and parts[0] == "new":
        parts.pop(0)
    return parts


def squash(text: str) -> str:
    """`add(int, E)`, `add(int,E)` and `ADD(int,e)` name the same overload."""
    return "".join(text.split()).lower()


class JavaIndex:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        fuzzy: SiteIndex,
        types: dict[str, JavaType],
        members: dict[str, dict[str, list[Member]]],
        packages: dict[str, tuple[str, Entry]],
    ) -> None:
        self.session = session
        self.fuzzy = fuzzy
        self.types = types  # qualified name -> type
        self.members = members  # qualified name -> lower-cased member name -> overloads
        self.packages = packages  # lower-cased package name -> (display name, entry)
        self.by_qualname = {qualname.lower(): qualname for qualname in types}
        self.by_url: dict[str, str] = {}
        self.by_name: defaultdict[str, list[str]] = defaultdict(list)  # lower-cased simple name -> best-known package first
        for qualname, jtype in types.items():
            self.by_url[jtype.url] = qualname
            self.by_name[jtype.name.lower()].append(qualname)
            if "." in jtype.name:  # `Entry` finds `Map.Entry` too
                self.by_name[jtype.name.rsplit(".", 1)[-1].lower()].append(qualname)

    @classmethod
    async def load(cls, session: aiohttp.ClientSession, base: str) -> JavaIndex | None:
        names = ("package-search-index.js", "type-search-index.js", "member-search-index.js")
        raw = await asyncio.gather(*(fetch(session, f"{base}/{name}") for name in names))
        if not all(raw):
            return None
        return await asyncio.to_thread(cls.build, session, base, *raw)  # type: ignore[arg-type]

    @classmethod
    def build(cls, session: aiohttp.ClientSession, base: str, packages_js: bytes, types_js: bytes, members_js: bytes) -> JavaIndex:
        entries: Entries = {}
        modules: dict[str, str | None] = {}
        packages: dict[str, tuple[str, Entry]] = {}
        for item in sorted(js_index(packages_js), key=lambda item: package_rank(item.get("l", ""))):
            name = item.get("l")
            if not name or "u" in item:  # "All Packages"
                continue
            modules[name] = item.get("m")
            url = page_url(base, item.get("m"), f"{name.replace('.', '/')}/package-summary.html")
            display = unique_name(entries, name, "package")
            entries[display] = Entry(url=url, role="package", detail="javadoc")
            packages[name.lower()] = (display, entries[display])

        types: dict[str, JavaType] = {}
        for item in sorted(js_index(types_js), key=lambda item: package_rank(item.get("p", ""))):
            package, name = item.get("p"), item.get("l")
            if not package or not name or "u" in item:  # "All Classes and Interfaces"
                continue
            url = page_url(base, item.get("m") or modules.get(package), f"{package.replace('.', '/')}/{name}.html")
            display = unique_name(entries, name, package)
            entries[display] = Entry(url=url, role=package, detail="javadoc")
            types[f"{package}.{name}"] = JavaType(package, name, url, display, entries[display])

        members: defaultdict[str, defaultdict[str, list[Member]]] = defaultdict(lambda: defaultdict(list))
        for item in sorted(js_index(members_js), key=lambda item: package_rank(item.get("p", ""))):
            package, owner, label = item.get("p"), item.get("c"), item.get("l")
            if not package or not owner or not label or (jtype := types.get(f"{package}.{owner}")) is None:
                continue
            anchor = unquote(item.get("u") or label)
            if "(" not in label:
                kind = "field"
            elif anchor.startswith("<init>"):
                kind = "constructor"
            else:
                kind = "method"
            prefix = owner.rpartition(".")[0] if kind == "constructor" else owner  # `ArrayList(int)`, not `ArrayList.ArrayList(int)`
            display = unique_name(entries, f"{prefix}.{label}" if prefix else label, package)
            entries[display] = Entry(url=f"{jtype.url}#{quote(anchor, safe='')}", role=f"{kind} in {package}", detail="javadoc")
            members[jtype.qualname][label.partition("(")[0].lower()].append(Member(display, entries[display], label, anchor))

        plain = {qualname: dict(named) for qualname, named in members.items()}
        return cls(session, SiteIndex.build("javadoc", entries), types, plain, packages)

    def describe(self) -> str:
        return self.fuzzy.describe()

    async def search_async(self, query: str, limit: int = MAX_RESULTS) -> list[tuple[str, Entry]]:
        exact = await self.resolve(query)
        fuzzy = await self.fuzzy.search_async(query, limit)
        seen = {name for name, _entry in exact}
        return (exact + [hit for hit in fuzzy if hit[0] not in seen])[:limit]

    async def resolve(self, query: str) -> list[tuple[str, Entry]]:
        """Exact hits for a dotted name: a package, a type, or a member reached through fields and return types."""
        parts = split_query(query)
        if not parts or len(parts) > MAX_HOPS + 2:
            return []
        if (package := self.packages.get(".".join(parts).lower())) is not None:
            return [package]
        for split in range(len(parts), 0, -1):
            head, rest = parts[:split], parts[split:]
            if any("(" in part for part in head[:-1]):  # a call is followed by members, never by more of a type name
                continue
            name = ".".join(head)
            if "(" in head[-1]:
                if rest:
                    continue
                name, rest = name.partition("(")[0], head[-1:]  # `ArrayList(int)` asks for a constructor
            for qualname in self.lookup(name):
                if hits := await self.walk(qualname, rest):
                    return hits
        return []

    def lookup(self, name: str) -> list[str]:
        lowered = name.lower()
        if (qualname := self.by_qualname.get(lowered)) is not None:
            return [qualname]
        return self.by_name.get(lowered, [])

    async def walk(self, qualname: str, rest: list[str]) -> list[tuple[str, Entry]]:
        if not rest:
            jtype = self.types[qualname]
            return [(jtype.display, jtype.entry)]
        current: str | None = qualname
        for segment in rest[:-1]:
            if (current := await self.member_type(current, segment)) is None:
                return []
        return [(member.name, member.entry) for member in await self.overloads(current, rest[-1])]

    async def overloads(self, qualname: str, segment: str) -> list[Member]:
        """Every overload of the member, the one whose arguments were spelled out first."""
        bare = segment.partition("(")[0].lower()
        declaring = await self.declaring_type(qualname, bare)
        found = self.members.get(declaring, {}).get(bare, []) if declaring else []
        wanted = squash(segment)
        return sorted(found, key=lambda member: squash(member.label) != wanted and squash(member.anchor) != wanted)

    async def declaring_type(self, qualname: str, bare: str) -> str | None:
        """The type whose page documents the member: this one, or the ancestor its inherited-member lists point at."""
        for _hop in range(MAX_HOPS):
            if bare in self.members.get(qualname, {}):
                return qualname
            page = await self.page(qualname)
            if page is None:
                return None
            link = next((a for a in page.select("div.inherited-list a[href]") if a.get_text(strip=True).lower() == bare), None)
            if link is None or (parent := self.type_for(qualname, attr(link, "href"))) in (None, qualname):
                return None
            qualname = parent
        return None

    async def member_type(self, qualname: str, segment: str) -> str | None:
        """The type a field holds or a method returns, read from the member's signature on its class page."""
        bare = segment.partition("(")[0].lower()
        declaring = await self.declaring_type(qualname, bare)
        page = await self.page(declaring) if declaring else None
        if declaring is None or page is None:
            return None
        wanted = squash(segment)
        sections = [s for s in page.select("section.detail") if s.h3 is not None and s.h3.get_text(strip=True).lower() == bare]
        sections.sort(key=lambda section: squash(attr(section, "id")) != wanted)
        for section in sections:
            link = section.select_one(".member-signature .return-type a[href]")
            if link is not None and not attr(link, "title").startswith("type parameter"):
                return self.type_for(declaring, attr(link, "href"))
        return None

    def type_for(self, qualname: str, href: str) -> str | None:
        return self.by_url.get(urljoin(self.types[qualname].url, href).partition("#")[0])

    async def page(self, qualname: str) -> BeautifulSoup | None:
        data = await fetch_shared(self.session, self.types[qualname].url)
        return await asyncio.to_thread(soup_of, data) if data else None


async def detail_javadoc(session: aiohttp.ClientSession, entry: Entry) -> DetailInfo | None:
    url, _, fragment = entry.url.partition("#")
    data = await fetch_shared(session, url)
    if not data:
        return None
    return await asyncio.to_thread(render, data, url, unquote(fragment), entry.role)


def render(data: bytes, url: str, anchor: str, role: str | None) -> DetailInfo | None:
    page = soup_of(data)
    heading = page.select_one("h1.title") or page.select_one("h1")
    title = heading.get_text(" ", strip=True) if heading else url
    if anchor:
        return member_detail(page, url, anchor, title, role)
    if url.endswith("package-summary.html"):
        return package_detail(page, url, title)
    return type_detail(page, url, title, role)


def type_detail(page: BeautifulSoup, url: str, title: str, package: str | None) -> DetailInfo:
    kind, _, name = title.rpartition(" ")  # "Enum Class Thread.State"
    description = page.select_one("section.class-description")
    signature = type_signature(description.select_one(".type-signature")) if description else None
    overview, extra = describe(description, url) if description else ("", {})

    sections: dict[str, str] = {"Overview": overview, **extra}
    for summary in page.select("section.summary section"):
        heading = summary.find("h2")
        rows = summary_rows(summary)
        if heading is not None and rows:
            sections[plural(heading.get_text(" ", strip=True).removesuffix(" Summary"))] = "\n".join(rows)
    role = kind.lower()
    return detail(name, role=f"{role} in {package}" if package else role, signature=signature, sections=sections, language="java")


def member_detail(page: BeautifulSoup, url: str, anchor: str, title: str, role: str | None) -> DetailInfo | None:
    section = page.find("section", class_="detail", id=anchor)
    if section is None:
        return None
    owner = GENERICS.sub("", title.rpartition(" ")[2])  # "Interface List<E>"
    name = section.h3.get_text(strip=True) if section.h3 else anchor.partition("(")[0]
    holder = section.find_parent("section", class_=list(KINDS))
    kind = next((KINDS[c] for c in (holder.get("class") or []) if c in KINDS), "member") if holder else "member"
    package = role.rpartition(" in ")[2] if role and " in " in role else ""
    overview, extra = describe(section, url)
    return detail(
        owner if kind == "constructor" else f"{owner}.{name}",
        role=f"{kind} in {package}" if package else kind,
        signature=member_signature(section.select_one(".member-signature")),
        sections={"Overview": overview, **extra},
        language="java",
    )


def package_detail(page: BeautifulSoup, url: str, title: str) -> DetailInfo:
    description = page.select_one("section.package-description")
    overview, extra = describe(description, url) if description else ("", {})
    return detail(title.rpartition(" ")[2], role="package", signature=None, sections={"Overview": overview, **extra}, language="java")


def describe(container: Tag, url: str) -> tuple[str, dict[str, str]]:
    """A class or member description: deprecation notice, text blocks and one-line notes, plus the notes that stand alone."""
    parts: list[str] = []
    deprecation = container.find("div", class_="deprecation-block")
    if deprecation is not None:
        label = deprecation.find("span", class_="deprecated-label")
        comment = deprecation.find("div", class_="deprecation-comment")
        text = f"**{label.get_text(' ', strip=True) if label else 'Deprecated.'}** {to_markdown(comment, url) if comment else ''}"
        parts.append("\n".join(f"> {line}" for line in text.strip().splitlines()))
    blocks = [
        block
        for block in container.find_all("div", class_="block")
        if block.find_parent(["dl", "div"], class_=["notes", "deprecation-block"]) is None
    ]
    parts.extend(filter(None, (to_markdown(block, url) for block in blocks)))

    inline: list[str] = []
    extra: dict[str, list[str]] = {}
    for notes in container.find_all("dl", class_="notes"):
        label = None
        for child in notes.find_all(["dt", "dd"], recursive=False):
            if child.name == "dt":
                label = child.get_text(" ", strip=True).rstrip(": ")  # "See <cite>JLS</cite>:" gets a space before the colon
                continue
            child.name = "div"  # the contents alone, without the dash a definition would get
            body = to_markdown(child, url) if label else ""
            if label is None or not body:
                continue
            if label in INLINE_NOTES:
                inline.append(f"-# {label}: {' '.join(body.split())}")
            elif label.startswith(("All ", "Direct ")):
                extra.setdefault("Hierarchy", []).append(f"**{label}**\n{body}")
            else:
                extra.setdefault(label, []).append(PARAM.sub(r"**\1** - ", body))
    if inline:
        parts.append("\n".join(inline))
    return "\n\n".join(parts), {label: "\n".join(bodies) for label, bodies in extra.items()}


def summary_rows(section: Tag) -> list[str]:
    """Summary tables as `signature` - description lines, then what the class inherits."""
    rows: list[str] = []
    cells: list[str] = []
    for cell in section.select("div.summary-table > div"):
        classes = cell.get("class") or []
        if "table-header" in classes:
            continue
        if "col-last" not in classes:
            cells.append(" ".join(cell.get_text().split()))
            continue
        head, text = " ".join(filter(None, cells)), " ".join(cell.get_text().split())
        cells = []
        if head:
            rows.append(f"`{head}` - {text}" if text else f"`{head}`")
    for inherited in section.select("div.inherited-list"):
        heading = inherited.find("h3")
        names = ", ".join(a.get_text(strip=True) for a in inherited.select("code a"))
        if heading is not None and names:
            rows.append(f"-# {' '.join(heading.get_text().split())}: {names}")
    return rows


def plural(title: str) -> str:
    return f"{title}es" if title.endswith("s") else f"{title}s"


def type_signature(tag: Tag | None) -> str | None:
    """Javadoc already breaks the line before `extends` and `implements`; keep that and tidy the spacing."""
    if tag is None:
        return None
    lines = [" ".join(line.split()) for line in tag.get_text().splitlines()]
    return "\n".join(line for line in lines if line) or None


def member_signature(tag: Tag | None) -> str | None:
    if tag is None:
        return None
    text = tag.get_text()
    one_line = " ".join(text.split())
    if len(one_line) <= ONE_LINE_SIGNATURE:
        return one_line
    lines: list[str] = []
    indent = False  # Javadoc puts one parameter per line; indent those after the opening parenthesis
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line:
            continue
        lines.append(f"    {line}" if indent and not line.startswith("throws") else line)
        indent = indent or "(" in line
    return "\n".join(lines)
