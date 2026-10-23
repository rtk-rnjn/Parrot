from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, unquote, urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, FeatureNotFound, Tag
from bs4.element import Comment, NavigableString

if TYPE_CHECKING:
    from core import Bot

log = logging.getLogger(__name__)

BASE_URL = "https://minecraft.wiki"

# Language editions that exist as <lang>.minecraft.wiki (extend freely).
WIKI_LANGS: dict[str, str] = {
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
    "ja": "日本語",
    "ko": "한국어",
    "nl": "Nederlands",
    "pl": "Polski",
    "pt": "Português",
    "ru": "Русский",
    "th": "ไทย",
    "uk": "Українська",
    "zh": "中文",
}

SKIP_HEADINGS = {
    "contents",
    "navigation",
    "references",
    "external links",
    "notes",
    "footnotes",
    "อ้างอิง",
    "einzelnachweise",
    "weblinks",
    "références",
    "liens externes",
    "referencias",
    "enlaces externos",
    "脚注",
    "外部リンク",
    "참고",
    "각주",
}

# Elements that are never prose.
NOISE_TAGS = {"script", "style", "noscript", "table", "figure", "svg", "audio", "video", "sup", "form"}
NOISE_CLASSES = (
    "navbox",
    "notaninfobox",
    "infobox",
    "hatnote",
    "msgbox",
    "ambox",
    "toc",
    "mw-editsection",
    "reflist",
    "references",
    "mw-references-wrap",
    "catlinks",
    "printfooter",
    "noprint",
    "mw-empty-elt",
    "thumb",
    "gallery",
    "mw-cite-backlink",
    "navigation-not-searchable",
)
INFOBOX_SELECTOR = "div.notaninfobox, table.infobox-rows, table.infobox, div.infobox, aside.portable-infobox"
TABLE_SELECTOR = "table.wikitable, table.stikitable, table.data-table"

_MD_ESCAPE = re.compile(r"([\\*_~`|])")


def escape_md(text: str) -> str:
    """Escape Discord markdown and neutralise @mentions."""
    return _MD_ESCAPE.sub(r"\\\1", text).replace("@", "@\u200b")


def paginate(text: str, limit: int = 1700) -> list[str]:
    """Split text into chunks <= limit, preferring paragraph, then sentence, then word boundaries."""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    cur = ""
    for paragraph in text.split("\n"):
        para = paragraph
        while len(para) > limit:  # hard-split an enormous paragraph
            cut = max(para.rfind(". ", 0, limit), para.rfind(" ", 0, limit))
            cut = cut + 1 if cut > limit // 3 else limit
            piece, para = para[:cut].rstrip(), para[cut:].lstrip()
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(piece)
        if len(cur) + len(para) + 1 > limit and cur:
            chunks.append(cur)
            cur = para
        else:
            cur = f"{cur}\n{para}" if cur else para
    if cur.strip():
        chunks.append(cur)
    return chunks


@dataclass(slots=True)
class WikiTable:
    caption: str
    headers: list[str]
    rows: list[list[str]]

    def to_text(self, max_rows: int = 15, max_width: int = 66, max_cell: int = 20) -> str:
        """Render as an aligned monospace table, or `Header: value` records if too wide."""
        rows = [[c.replace("`", "'") for c in r] for r in self.rows[:max_rows]]
        headers = [h.replace("`", "'") for h in self.headers]
        ncols = max([len(headers)] + [len(r) for r in rows] or [0])
        if not ncols:
            return ""
        trim = lambda s: s if len(s) <= max_cell else s[: max_cell - 1] + "…"  # noqa: E731
        grid = ([[trim(h) for h in headers]] if headers else []) + [[trim(c) for c in r] for r in rows]
        widths = [max((len(r[i]) for r in grid if i < len(r)), default=0) for i in range(ncols)]
        if sum(widths) + 2 * (ncols - 1) <= max_width:
            lines = []
            for n, r in enumerate(grid):
                lines.append("  ".join((r[i] if i < len(r) else "").ljust(widths[i]) for i in range(ncols)).rstrip())
                if headers and n == 0:
                    lines.append("  ".join("─" * w for w in widths))
            body = "\n".join(lines)
        else:  # too wide -> record style
            recs = []
            for r in rows:
                head = r[0] if r else ""
                pairs = [f"{headers[i] if i < len(headers) and headers[i] else i + 1}: {r[i]}" for i in range(1, len(r)) if r[i]]
                recs.append(f"■ {head}\n   " + "\n   ".join(pairs) if pairs else f"■ {head}")
            body = "\n".join(recs)
        extra = len(self.rows) - max_rows
        if extra > 0:
            body += f"\n… +{extra} more rows"
        return f"```\n{body}\n```"


@dataclass(slots=True)
class WikiSection:
    heading: str
    level: int
    text: str = ""
    subsections: list[WikiSection] = field(default_factory=list)

    def iter_flat(self) -> Iterator[WikiSection]:
        yield self
        for s in self.subsections:
            yield from s.iter_flat()


@dataclass(slots=True)
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    matched_terms: list[str] = field(default_factory=list)
    pageid: int | None = None
    wordcount: int | None = None
    size_bytes: int | None = None
    timestamp: str | None = None
    redirect_from: str | None = None


@dataclass(slots=True)
class SearchPage:
    query: str
    hits: list[SearchHit]
    total: int
    suggestion: str | None = None
    next_offset: int | None = None


@dataclass(slots=True)
class WikiArticle:
    title: str
    url: str
    lang: str
    base_url: str
    summary: str = ""
    infoboxes: list[dict[str, Any]] = field(default_factory=list)
    sections: list[WikiSection] = field(default_factory=list)
    tables: list[WikiTable] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    thumbnail: str | None = None
    pageid: int | None = None
    revid: int | None = None
    last_modified: str | None = None
    last_editor: str | None = None
    raw_wikitext: str | None = None

    @property
    def infobox(self) -> dict[str, Any]:
        return self.infoboxes[0] if self.infoboxes else {}

    def flat_sections(self) -> list[WikiSection]:
        return [s for top in self.sections for s in top.iter_flat()]

    @property
    def history_url(self) -> str:
        return f"{self.base_url}/w/Special:History/{quote(self.title.replace(' ', '_'), safe=':/_(),-.')}"


class WikiParser:
    """HTML -> structured data. Pure CPU, no I/O, safe to run in a thread."""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        try:
            return BeautifulSoup(html, "lxml")
        except FeatureNotFound:
            return BeautifulSoup(html, "html.parser")

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"\[(?:edit|citation needed|\d+|[a-z]|แก้ไข|แก้)\]", "", text, flags=re.I)
        text = re.sub(r"[ \t\xa0\u200b]+", " ", text)
        text = re.sub(r" ?\n ?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def title_to_url(self, title: str) -> str:
        return f"{self.base_url}/w/{quote(title.strip().replace(' ', '_'), safe=':/_(),-.')}"

    def title_from_href(self, href: str) -> str | None:
        """'/w/Diamond_Sword#Usage' -> 'Diamond Sword'; None for external/namespaced/special links."""
        if not href or href.startswith("#"):
            return None
        host = urlparse(urljoin(self.base_url + "/", href)).netloc
        if host != urlparse(self.base_url).netloc:
            return None
        path = urlparse(urljoin(self.base_url + "/", href)).path
        if not path.startswith("/w/"):
            return None
        title = unquote(path[3:]).replace("_", " ")
        if not title or ":" in title.split(" ", 1)[0] or "redlink" in href:
            return None
        return title

    def parse_snippet(self, snippet_html: str) -> tuple[str, list[str]]:
        if not snippet_html:
            return "", []
        soup = self._soup(snippet_html)
        terms: list[str] = []
        for span in soup.select("span.searchmatch"):
            t = self.clean_text(span.get_text(" ", strip=True))
            if t and t.lower() not in (x.lower() for x in terms):
                terms.append(t)
        return self.clean_text(soup.get_text(" ", strip=True)), terms

    @staticmethod
    def _is_noise(tag: Tag) -> bool:
        if tag.name in NOISE_TAGS:
            return True
        classes = " ".join(tag.get("class") or [])
        return any(c in classes for c in NOISE_CLASSES) or tag.get("id") == "toc"

    @staticmethod
    def _wrap(marker: str, inner: str) -> str:
        core = inner.strip()
        if not core:
            return inner
        lead, trail = inner[: len(inner) - len(inner.lstrip())], inner[len(inner.rstrip()) :]
        return f"{lead}{marker}{core}{marker}{trail}"

    def inline_md(self, node: Tag, skip_lists: bool = True) -> str:
        out: list[str] = []
        for ch in node.children:
            if isinstance(ch, Comment):
                continue
            if isinstance(ch, NavigableString):
                out.append(escape_md(re.sub(r"\s+", " ", str(ch))))
                continue
            if not isinstance(ch, Tag) or self._is_noise(ch):
                continue
            n = ch.name
            if n in ("ul", "ol", "dl") and skip_lists:
                continue
            if n == "br":
                out.append("\n")
            elif n == "code":
                out.append(f"`{ch.get_text().replace('`', chr(39))}`")
            elif n in ("b", "strong"):
                out.append(self._wrap("**", self.inline_md(ch)))
            elif n in ("i", "em"):
                out.append(self._wrap("*", self.inline_md(ch)))
            else:
                out.append(self.inline_md(ch, skip_lists))
        return "".join(out)

    def _list_md(self, tag: Tag, depth: int = 0) -> list[str]:
        lines: list[str] = []
        for n, li in enumerate(tag.find_all("li", recursive=False), 1):
            text = self.clean_text(self.inline_md(li))
            bullet = f"{n}." if tag.name == "ol" else "•"
            if text:
                lines.append(f"{'  ' * depth}{bullet} {text}")
            for sub in li.find_all(["ul", "ol"], recursive=False):
                lines.extend(self._list_md(sub, depth + 1))
        return lines

    def block_md(self, tag: Tag) -> str:
        if tag.name in ("ul", "ol"):
            return "\n".join(self._list_md(tag))
        if tag.name == "dl":
            lines = []
            for el in tag.find_all(["dt", "dd"], recursive=False):
                t = self.clean_text(self.inline_md(el))
                if t:
                    lines.append(f"**{t}**" if el.name == "dt" else f"  {t}")
            return "\n".join(lines)
        if tag.name == "blockquote":
            return "\n".join(f"> {line}" for line in self.clean_text(self.inline_md(tag)).split("\n") if line)
        if tag.name == "pre":
            return f"```\n{tag.get_text().strip()[:1500]}\n```"
        return self.clean_text(self.inline_md(tag))

    def _heading(self, tag: Tag) -> tuple[int, str] | None:
        h = tag
        if tag.name == "div" and "mw-heading" in (tag.get("class") or []):
            h = tag.find(["h2", "h3", "h4", "h5", "h6"])
        if h is None or h.name not in ("h2", "h3", "h4", "h5", "h6"):
            return None
        head = h.select_one(".mw-headline") or h
        return int(h.name[1]), self.clean_text(head.get_text(" ", strip=True))

    def _walk(self, container: Tag) -> Iterator[tuple[str, Any, Tag | None]]:
        """Yield ('heading', (level, text), tag) / ('block', text, tag); descends into generic wrappers."""
        for ch in container.children:
            if not isinstance(ch, Tag) or isinstance(ch, Comment):
                continue
            h = self._heading(ch)
            if h is not None:
                yield "heading", h, ch
                continue
            if self._is_noise(ch):
                continue
            if ch.name in ("p", "ul", "ol", "dl", "blockquote", "pre"):
                text = self.block_md(ch)
                if text:
                    yield "block", text, ch
            elif ch.name in ("div", "section", "center", "span"):
                yield from self._walk(ch)

    def _sections(self, root: Tag, title: str) -> tuple[str, list[WikiSection], list[str]]:
        lead: list[str] = []
        related: list[str] = []
        sections: list[WikiSection] = []
        cur_top: WikiSection | None = None
        cur: WikiSection | None = None
        skipping = False
        seen_heading = False

        for kind, payload, tag in self._walk(root):
            if kind == "heading":
                seen_heading = True
                level, text = payload
                if not text or text.lower() in SKIP_HEADINGS:
                    skipping = True
                    continue
                skipping = False
                sec = WikiSection(heading=text, level=level)
                if level <= 2 or cur_top is None:
                    sec.level = 2 if level <= 2 else level
                    sections.append(sec)
                    cur_top = cur = sec
                else:
                    cur_top.subsections.append(sec)
                    cur = sec
                continue
            if skipping:
                continue
            if not seen_heading:
                lead.append(payload)
                if tag is not None and len(related) < 12:
                    for a in tag.select("a[href]"):
                        t = self.title_from_href(a["href"])
                        if t and t.lower() != title.lower() and t not in related:
                            related.append(t)
            elif cur is not None:
                cur.text = f"{cur.text}\n{payload}".strip()

        keep = lambda s: bool(s.text or any(x.text for x in s.subsections))  # noqa: E731
        return "\n\n".join(lead), [s for s in sections if keep(s)], related

    def _infoboxes(self, root: Tag) -> list[dict[str, Any]]:
        boxes: list[dict[str, Any]] = []
        for box in root.select(INFOBOX_SELECTOR):
            if box.find_parent(class_=re.compile("infobox")) is not None:
                continue  # nested part of an already handled infobox
            data: dict[str, Any] = {}
            head = box.select_one(".infobox-title, caption, th.infobox-header")
            if head:
                data["_title"] = self.clean_text(head.get_text(" ", strip=True))
            for br in box.find_all("br"):
                br.replace_with(" · ")
            for tr in box.select("tr"):
                th, td = tr.find("th"), tr.find("td")
                if not (th and td):
                    continue
                key = self.clean_text(th.get_text(" ", strip=True))
                items = [self.clean_text(li.get_text(" ", strip=True)) for li in td.find_all("li")]
                val: Any = [i for i in items if i] or self.clean_text(td.get_text(" ", strip=True))
                if key and val:
                    data[key] = val
            if len(data) > (1 if "_title" in data else 0):
                boxes.append(data)
        return boxes

    @staticmethod
    def _cell_text(cell: Tag) -> str:
        text = WikiParser.clean_text(cell.get_text(" ", strip=True))
        if text:
            return text
        a = cell.find("a", title=True)
        if a:
            return a["title"]
        img = cell.find("img", alt=True)
        return re.sub(r"\.\w{3,4}$", "", img["alt"]).replace("_", " ")[:30] if img else ""

    def _tables(self, root: Tag) -> list[WikiTable]:
        out: list[WikiTable] = []
        for n, table in enumerate(root.select(TABLE_SELECTOR), 1):
            if table.find_parent(class_=re.compile("navbox|infobox")):
                continue
            cap = table.find("caption")
            caption = self.clean_text(cap.get_text(" ", strip=True)) if cap else ""
            if not caption:
                h = table.find_previous(["h2", "h3", "h4"])
                caption = self.clean_text(h.get_text(" ", strip=True)) if h else f"Table {n}"
            headers, rows = self._grid(table)
            if rows:
                out.append(WikiTable(caption=caption[:80], headers=headers, rows=rows[:200]))
        return out

    def _grid(self, table: Tag) -> tuple[list[str], list[list[str]]]:
        """Table -> headers + rows with rowspan/colspan expanded. Includes <thead> rows."""
        trs = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
        grid: dict[tuple[int, int], str] = {}
        header_rows: list[int] = []
        max_c = 0
        for r, tr in enumerate(trs):
            cells = tr.find_all(["th", "td"], recursive=False)
            if not cells:
                continue
            if all(c.name == "th" for c in cells) and r < 3 and len(header_rows) == r:
                header_rows.append(r)
            c = 0
            for cell in cells:
                while (r, c) in grid:
                    c += 1
                rs = max(1, int(re.sub(r"\D", "", str(cell.get("rowspan", 1))) or 1))
                cs = max(1, int(re.sub(r"\D", "", str(cell.get("colspan", 1))) or 1))
                txt = self._cell_text(cell)
                for dr in range(min(rs, 50)):
                    for dc in range(min(cs, 30)):
                        grid[(r + dr, c + dc)] = txt
                        max_c = max(max_c, c + dc + 1)
                c += cs
        n_rows = len(trs)
        headers: list[str] = []
        for c in range(max_c):
            parts: list[str] = []
            for r in header_rows:
                v = grid.get((r, c), "")
                if v and (not parts or parts[-1] != v):
                    parts.append(v)
            headers.append(" / ".join(parts))
        start = (header_rows[-1] + 1) if header_rows else 0
        rows = [[grid.get((r, c), "") for c in range(max_c)] for r in range(start, n_rows)]
        return (headers if header_rows else []), [r for r in rows if any(r)]

    def _images(self, root: Tag) -> list[dict[str, str]]:
        imgs, seen = [], set()
        for img in root.select("img"):
            src = img.get("src") or img.get("data-src")
            if not src or src.startswith("data:"):
                continue
            full = urljoin(self.base_url + "/", src)
            if full in seen:
                continue
            seen.add(full)
            imgs.append(
                {"src": full, "alt": (img.get("alt") or "").strip(), "width": str(img.get("width") or ""), "height": str(img.get("height") or "")}
            )
        return imgs

    def parse_article(self, html: str, *, title: str, lang: str = "en", **meta: Any) -> WikiArticle:
        soup = self._soup(html)
        root = soup.select_one(".mw-parser-output") or soup.body or soup
        infoboxes = self._infoboxes(root)  # must run before anything mutates/removes nodes
        tables = self._tables(root)
        images = self._images(root)
        summary, sections, related = self._sections(root, title)
        thumb = None
        for im in images:  # first reasonably large image as fallback lead image
            if im["width"].isdigit() and int(im["width"]) >= 100:
                thumb = im["src"]
                break
        return WikiArticle(
            title=title,
            url=self.title_to_url(title),
            lang=lang,
            base_url=self.base_url,
            summary=summary,
            infoboxes=infoboxes,
            sections=sections,
            tables=tables,
            images=images,
            related=related,
            thumbnail=thumb,
            **meta,
        )


class WikiError(Exception):
    """Network / API failure."""


class WikiNotFound(WikiError):
    """Page does not exist."""


class WikiClient:
    """Async client for one wiki edition. Share one aiohttp session across editions."""

    def __init__(
        self,
        bot: Bot,
        *,
        lang: str = "en",
        min_interval: float = 0.25,
        cache_ttl: float = 600.0,
        maxlag: int = 5,
        timeout: float = 15.0,
    ) -> None:
        self.lang = lang if lang in WIKI_LANGS else "en"
        self.base_url = BASE_URL if self.lang == "en" else f"https://{self.lang}.minecraft.wiki"
        self.api_url = f"{self.base_url}/api.php"
        self.parser = WikiParser(self.base_url)

        self._session = bot.http_session
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._min_interval = min_interval
        self._ttl = cache_ttl
        self._maxlag = maxlag
        self._cache: dict[tuple, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._last = 0.0

    def _sess(self) -> aiohttp.ClientSession:
        return self._session

    async def _throttle(self) -> None:
        async with self._lock:
            wait = self._last + self._min_interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()

    async def _api(self, params: dict[str, Any], *, ttl: float | None = None) -> Any:
        params = {"format": "json", "formatversion": 2, "utf8": 1, "maxlag": self._maxlag, **params}
        key = tuple(sorted((k, str(v)) for k, v in params.items()))
        hit = self._cache.get(key)
        ttl = self._ttl if ttl is None else ttl
        if hit and hit[0] > time.monotonic():
            return hit[1]
        last_exc: Exception | None = None
        for attempt in range(3):
            await self._throttle()
            try:
                async with self._sess().get(self.api_url, params=params, timeout=self._timeout) as r:
                    if r.status in (429, 502, 503, 504):
                        delay = float(r.headers.get("Retry-After", 1.5 ** (attempt + 1)))
                        await asyncio.sleep(min(delay, 8))
                        last_exc = WikiError(f"wiki returned HTTP {r.status}")
                        continue
                    r.raise_for_status()
                    data = await r.json(content_type=None)
            except (TimeoutError, aiohttp.ClientError) as exc:
                last_exc = exc
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            if isinstance(data, dict) and data.get("error", {}).get("code") == "maxlag":
                await asyncio.sleep(2.0)
                last_exc = WikiError("wiki is lagging, try again shortly")
                continue
            if len(self._cache) > 400:
                now = time.monotonic()
                self._cache = {k: v for k, v in self._cache.items() if v[0] > now}
            self._cache[key] = (time.monotonic() + ttl, data)
            return data
        msg = f"Could not reach {self.base_url}: {last_exc}"
        raise WikiError(msg)

    # -- search
    async def opensearch(self, query: str, limit: int = 15) -> list[str]:
        """Prefix autocomplete (titles). Cached briefly; cheap enough for Discord autocomplete."""
        if not query.strip():
            return []
        data = await self._api({"action": "opensearch", "search": query, "limit": min(limit, 25), "namespace": 0}, ttl=120)
        return [str(t) for t in data[1]] if isinstance(data, list) and len(data) > 1 else []

    async def search(self, query: str, *, limit: int = 10, offset: int = 0, namespace: str = "0") -> SearchPage:
        data = await self._api(
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": min(limit, 50),
                "sroffset": offset,
                "srnamespace": namespace,
                "srinfo": "totalhits|suggestion",
                "srprop": "snippet|size|wordcount|timestamp|redirecttitle",
                "srenablerewrites": 1,
            },
            ttl=180,
        )
        q = data.get("query", {})
        hits: list[SearchHit] = []
        for it in q.get("search", []):
            snippet, terms = self.parser.parse_snippet(it.get("snippet", ""))
            hits.append(
                SearchHit(
                    title=it["title"],
                    url=self.parser.title_to_url(it["title"]),
                    snippet=snippet,
                    matched_terms=terms,
                    pageid=it.get("pageid"),
                    wordcount=it.get("wordcount"),
                    size_bytes=it.get("size"),
                    timestamp=it.get("timestamp"),
                    redirect_from=it.get("redirecttitle"),
                )
            )
        info = q.get("searchinfo", {})
        nxt = data.get("continue", {}).get("sroffset")
        return SearchPage(
            query=query,
            hits=hits,
            total=int(info.get("totalhits", len(hits))),
            suggestion=info.get("suggestion"),
            next_offset=int(nxt) if nxt is not None else None,
        )

    async def random_title(self) -> str:
        data = await self._api({"action": "query", "list": "random", "rnnamespace": 0, "rnlimit": 1}, ttl=0)
        try:
            return data["query"]["random"][0]["title"]
        except (KeyError, IndexError) as exc:
            msg = "Couldn't pick a random page."
            raise WikiError(msg) from exc

    # -- article
    async def get_article(self, title: str, *, raw_wikitext: bool = False) -> WikiArticle:
        title = unquote(title).replace("_", " ").strip()
        props = "text|categories|revid|displaytitle" + ("|wikitext" if raw_wikitext else "")
        parse_coro = self._api(
            {
                "action": "parse",
                "page": title,
                "prop": props,
                "redirects": 1,
                "disableeditsection": 1,
                "disabletoc": 1,
                "disablelimitreport": 1,
                "wrapoutputclass": "mw-parser-output",
            },
            ttl=900,
        )
        meta_coro = self._api(
            {
                "action": "query",
                "titles": title,
                "redirects": 1,
                "prop": "pageimages|revisions",
                "piprop": "thumbnail",
                "pithumbsize": 400,
                "rvprop": "timestamp|user",
            },
            ttl=900,
        )
        parsed, meta = await asyncio.gather(parse_coro, meta_coro, return_exceptions=True)
        if isinstance(parsed, BaseException):
            raise parsed if isinstance(parsed, WikiError) else WikiError(str(parsed))
        if "error" in parsed:
            if parsed["error"].get("code") in ("missingtitle", "invalidtitle"):
                msg = f"No wiki page named “{title}”."
                raise WikiNotFound(msg)
            raise WikiError(parsed["error"].get("info", "wiki API error"))
        p = parsed["parse"]
        canonical = p.get("title", title)
        cats = [c["category"].replace("_", " ") for c in p.get("categories", []) if not c.get("hidden")]
        article = await asyncio.to_thread(
            self.parser.parse_article,
            p.get("text", ""),
            title=canonical,
            lang=self.lang,
            pageid=p.get("pageid"),
            revid=p.get("revid"),
            categories=cats,
            raw_wikitext=p.get("wikitext") if raw_wikitext else None,
        )
        if isinstance(meta, dict):
            pages = meta.get("query", {}).get("pages", [])
            if pages:
                pg = pages[0]
                if pg.get("thumbnail", {}).get("source"):
                    article.thumbnail = pg["thumbnail"]["source"]
                revs = pg.get("revisions") or []
                if revs:
                    article.last_modified = revs[0].get("timestamp")
                    article.last_editor = revs[0].get("user")
        return article

    def search_url(self, query: str) -> str:
        return f"{self.base_url}/w/Special:Search?search={quote(query)}"
