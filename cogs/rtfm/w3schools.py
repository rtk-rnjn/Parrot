from __future__ import annotations

import asyncio
import contextlib
import difflib
import importlib.util
import re
import textwrap
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import aiohttp
import discord
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot

SITE = "https://www.w3schools.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DiscordBot/1.0; +https://discord.com)",
    "Accept-Language": "en",
}
PARSER = "lxml" if importlib.util.find_spec("lxml") else "html.parser"

INDEX_TTL = 3600
PAGE_TTL = 1800
CACHE_MAX = 128
PAGE_CHARS = 1800
TOTAL_CAP = 4500
MAX_BLOCKS = 80
MAX_CODE_LINES = 25
MAX_CODE_CHARS = 1200
MIN_RANK_SCORE = 40
STRONG_RANK_SCORE = 85
RANK_SCORE_GAP = 6
HTTP_NOT_FOUND = 404
HTTP_OK = 200
MAX_TABLE_ITEMS = 12
MAX_RANKED_CHOICES = 3
MIN_WORD_LENGTH = 3
STRONG_RANK_SCORE = 85
MIN_STRONG_RANK_GAP = 6

W3_GREEN = discord.Colour(0x04AA6D)
RED = discord.Colour(0xED4245)


class W3Error(Exception):
    """User-facing error."""


@dataclass(frozen=True)
class Tutorial:
    key: str
    name: str
    base: str
    hl: str = ""
    prefixes: tuple[str, ...] = ()


TUTORIALS: dict[str, Tutorial] = {
    t.key: t
    for t in (
        Tutorial("python", "Python", "python", "py", ("python",)),
        Tutorial("js", "JavaScript", "js", "js", ("js", "javascript")),
        Tutorial("html", "HTML", "html", "html", ("html",)),
        Tutorial("css", "CSS", "css", "css", ("css",)),
        Tutorial("sql", "SQL", "sql", "sql", ("sql",)),
        Tutorial("java", "Java", "java", "java", ("java",)),
        Tutorial("cpp", "C++", "cpp", "cpp", ("c++", "cpp")),
        Tutorial("c", "C", "c", "c", ("c",)),
        Tutorial("csharp", "C#", "cs", "cs", ("c#", "cs")),
        Tutorial("php", "PHP", "php", "php", ("php",)),
        Tutorial("react", "React", "react", "jsx", ("react",)),
        Tutorial("nodejs", "Node.js", "nodejs", "js", ("node.js", "nodejs", "node")),
        Tutorial("typescript", "TypeScript", "typescript", "ts", ("typescript", "ts")),
        Tutorial("jquery", "jQuery", "jquery", "js", ("jquery",)),
        Tutorial("bootstrap", "Bootstrap 5", "bootstrap5", "html", ("bootstrap", "bs5")),
        Tutorial("git", "Git", "git", "sh", ("git",)),
        Tutorial("bash", "Bash", "bash", "sh", ("bash",)),
        Tutorial("numpy", "NumPy", "python/numpy", "py", ("numpy",)),
        Tutorial("pandas", "Pandas", "python/pandas", "py", ("pandas",)),
        Tutorial("django", "Django", "django", "py", ("django",)),
        Tutorial("mysql", "MySQL", "mysql", "sql", ("mysql",)),
        Tutorial("go", "Go", "go", "go", ("go",)),
        Tutorial("rust", "Rust", "rust", "rust", ("rust",)),
        Tutorial("kotlin", "Kotlin", "kotlin", "kt", ("kotlin",)),
        Tutorial("r", "R", "r", "r", ("r",)),
        Tutorial("ruby", "Ruby", "ruby", "rb", ("ruby",)),
        Tutorial("xml", "XML", "xml", "xml", ("xml",)),
        Tutorial("sass", "Sass", "sass", "scss", ("sass",)),
        Tutorial("dsa", "DSA", "dsa", "py", ("dsa",)),
    )
}

ALIASES = {
    "py": "python",
    "python3": "python",
    "javascript": "js",
    "node": "nodejs",
    "node.js": "nodejs",
    "c++": "cpp",
    "c#": "csharp",
    "cs": "csharp",
    "ts": "typescript",
    "golang": "go",
    "bs": "bootstrap",
    "bs5": "bootstrap",
    "sh": "bash",
    "rb": "ruby",
    "kt": "kotlin",
    "jq": "jquery",
    "np": "numpy",
    "pd": "pandas",
}

CODE_LANGS = {
    "python": "py",
    "js": "js",
    "html": "html",
    "css": "css",
    "sql": "sql",
    "java": "java",
    "cpp": "cpp",
    "csharp": "cs",
    "php": "php",
    "angular": "ts",
    "ts": "ts",
    "bash": "sh",
}

SKIP_TITLE = re.compile(
    r"exercise|quiz|certificate|bootcamp|training|challenges?$|syllabus|study plan|"
    r"interview q|compiler|practice problems|^\S+ examples$",
    re.I,
)
STOP_HEADING = re.compile(r"^(exercise|test yourself|w3schools certified|track your progress|report error)", re.I)
NOTE_CLASSES = {"w3-note", "w3-pale-yellow", "w3-pale-blue"}
NESTED_SKIP = {"w3-example", "w3-code", "w3-panel", "nextprev", "exercise", "w3-bar-block", "w3-sidebar"}
PYTHON_SUBSITES = ("/python/numpy/", "/python/pandas/", "/python/scipy/", "/python/matplotlib/", "/python/ml/")


def resolve_tutorial(token: str) -> Tutorial | None:
    low = token.lower()
    return TUTORIALS.get(ALIASES.get(low, low))


@dataclass
class Topic:
    title: str
    url: str


@dataclass
class PageData:
    title: str
    url: str
    pages: list[str]


@dataclass
class Block:
    kind: str  # h | p | list | note | code | table
    text: str = ""
    items: tuple[str, ...] = ()
    lang: str = ""
    tryit: str = ""


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def inside(el: Tag, names: set[str]) -> bool:
    return el.find_parent(lambda t: bool(set(t.get("class") or ()) & names)) is not None


def parse_menu(html: str, page_url: str, tut: Tutorial) -> list[Topic]:
    soup = BeautifulSoup(html, PARSER)
    root = soup.select_one("#leftmenuinner") or soup
    prefix = f"/{tut.base.lower()}/"
    seen: set[str] = set()
    out: list[Topic] = []
    for a in root.select("a[href]"):
        raw_href = a.get("href")
        if not isinstance(raw_href, str):
            continue
        href = raw_href.strip()
        if href.startswith(("#", "javascript:", "mailto:")):
            continue
        parsed = urlparse(urljoin(page_url, href))
        if parsed.netloc.lower() not in {"www.w3schools.com", "w3schools.com"}:
            continue
        path = parsed.path.lower()
        if not path.startswith(prefix):
            continue
        if tut.base == "python" and path.startswith(PYTHON_SUBSITES):
            continue
        title = clean(a.get_text(" "))
        if not title or SKIP_TITLE.search(title):
            continue
        key = path + (f"?{parsed.query}" if parsed.query else "")
        if key in seen:
            continue
        seen.add(key)
        out.append(Topic(title, f"{SITE}{parsed.path}" + (f"?{parsed.query}" if parsed.query else "")))
    return out


def extract_code(div: Tag) -> str:
    for br in div.find_all("br"):
        br.replace_with("\n")
    return textwrap.dedent(div.get_text().replace("\xa0", " ").strip("\n")).rstrip()


def code_lang(div: Tag, default: str) -> str:
    for cls in div.get("class") or ():
        m = re.fullmatch(r"(\w+?)High", cls)
        if m:
            return CODE_LANGS.get(m.group(1).lower(), default)
    return default


def _parse_code_block(el: Tag, url: str, tut: Tutorial, classes: set[str]) -> Block | None:
    if "w3-example" in classes:
        if inside(el, {"exercise"}) or "exercise" in classes:
            return None
        codes = el.select("div.w3-code")
        if not codes:
            return None
        button = el.select_one("a.w3-btn[href*=tryit]")
        tryit = button.get("href") if button else None
        return Block(
            "code",
            text="\n\n".join(extract_code(code) for code in codes),
            lang=code_lang(codes[0], tut.hl),
            tryit=urljoin(url, tryit) if isinstance(tryit, str) else "",
        )
    if "w3-code" in classes and not inside(el, {"w3-example"}):
        return Block("code", text=extract_code(el), lang=code_lang(el, tut.hl))
    return None


def _parse_text_block(el: Tag) -> tuple[Block | None, bool]:
    if el.name in {"h2", "h3"}:
        if inside(el, NESTED_SKIP):
            return None, False
        text = clean(el.get_text(" "))
        return (None, True) if STOP_HEADING.search(text) else (Block("h", text=text), False)
    if el.name == "p" and not inside(el, NESTED_SKIP):
        text = clean(el.get_text())
        if text and "Try it Yourself" not in text:
            return Block("p", text=text), False
    return None, False


def _parse_collection_block(el: Tag) -> Block | None:
    if el.name in {"ul", "ol"}:
        if inside(el, NESTED_SKIP) or el.find_parent(["ul", "ol", "table"]):
            return None
        items = tuple(clean(item.get_text()) for item in el.find_all("li", recursive=False))
        items = tuple(item for item in items if item)
        return Block("list", items=items) if items else None
    if el.name != "table" or inside(el, NESTED_SKIP) or el.find_parent("table"):
        return None
    rows = []
    for row in el.find_all("tr"):
        cells = [clean(cell.get_text()) for cell in row.find_all("td")]
        if cells and cells[0]:
            description = trim(cells[1], 90) if len(cells) > 1 and cells[1] else ""
            rows.append(f"`{cells[0]}` - {description}" if description else f"`{cells[0]}`")
    return Block("table", items=tuple(rows)) if rows else None


def _parse_element(el: Tag, url: str, tut: Tutorial) -> tuple[Block | None, bool]:
    classes = set(el.get("class") or ())
    if (el.name == "div" and "w3-example" in classes) or (el.name == "div" and "w3-code" in classes):
        return _parse_code_block(el, url, tut, classes), False
    if el.name == "div" and "w3-panel" in classes:
        if not inside(el, {"w3-example", "w3-panel"}) and classes & NOTE_CLASSES:
            text = clean(el.get_text(" "))
            return (Block("note", text=text) if text else None), False
        return None, False
    text_block, stop = _parse_text_block(el)
    return (text_block, stop) if text_block else (_parse_collection_block(el), stop)


def parse_page(html: str, url: str, tut: Tutorial) -> PageData:
    soup = BeautifulSoup(html, PARSER)
    for t in soup(["script", "style", "noscript", "iframe", "ins"]):
        t.decompose()
    main = soup.select_one("#main") or soup.body or soup
    for t in main.select(".nextprev, #mainLeaderboard, .adsbygoogle, [id^=snhb]"):
        t.decompose()

    h1 = main.find("h1")
    title = clean(h1.get_text(" ")) if h1 else tut.name

    # inline <code> -> `backticks` (outside of code blocks)
    for c in main.select("code.w3-codespan, p code, li code, td code"):
        if c.find_parent(class_="w3-code") or not c.get_text().strip():
            continue
        c.replace_with(NavigableString(f"`{c.get_text().strip()}`"))

    blocks: list[Block] = []
    for element in main.select("h2, h3, p, ul, ol, table, div.w3-example, div.w3-code, div.w3-panel"):
        if len(blocks) > MAX_BLOCKS:
            break
        block, stop = _parse_element(element, url, tut)
        if stop:
            break
        if block:
            blocks.append(block)

    pages = render_pages(blocks)
    return PageData(title=title, url=url, pages=pages or ["*(No previewable content found, open the lesson with the button below.)*"])


def render_piece(b: Block) -> str:
    if b.kind == "p":
        return trim(b.text, 900)
    if b.kind == "note":
        return "> " + trim(b.text, 500)
    if b.kind == "list":
        return "\n".join(f"• {trim(i, 150)}" for i in b.items[:10])
    if b.kind == "table":
        return "\n".join(b.items[:MAX_TABLE_ITEMS]) + ("\n*…more in the full lesson*" if len(b.items) > MAX_TABLE_ITEMS else "")
    if b.kind == "code":
        lines, size = [], 0
        for line in b.text.splitlines()[:MAX_CODE_LINES]:
            if size + len(line) > MAX_CODE_CHARS:
                lines.append("…")
                break
            lines.append(line)
            size += len(line) + 1
        body = "\n".join(lines).replace("```", "`\u200b``")
        piece = f"```{b.lang}\n{body}\n```"
        if b.tryit:
            piece += f"\n[▶ Try it yourself]({b.tryit})"
        return piece
    return ""


def render_pages(blocks: list[Block]) -> list[str]:
    pages: list[str] = []
    cur, total, heading, truncated = "", 0, "", False
    for b in blocks:
        if b.kind == "h":
            heading = f"**{trim(b.text, 120)}**"
            continue
        piece = render_piece(b)
        if not piece:
            continue
        if heading:
            piece, heading = f"{heading}\n{piece}", ""
        if total + len(piece) > TOTAL_CAP:
            truncated = True
            break
        total += len(piece)
        if cur and len(cur) + len(piece) + 2 > PAGE_CHARS:
            pages.append(cur)
            cur = piece
        else:
            cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        pages.append(cur)
    if truncated and pages:
        pages[-1] += "\n\n*…continues on W3Schools, use the button below.*"
    return pages


TOKEN_RE = re.compile(r"[a-z0-9_#+.]+")


def tokens(text: str) -> list[str]:
    # crude singularisation so "list" matches "lists"
    return [w[:-1] if len(w) > MIN_WORD_LENGTH and w.endswith("s") else w for w in TOKEN_RE.findall(text.lower())]


def score(query: list[str], title: str, prefixes: set[str]) -> float:
    t = tokens(title)
    variants = [t]
    if t and t[0] in prefixes:
        variants.append(t[1:])
    q = " ".join(query)
    best = 0.0
    for tt in variants:
        if not tt:
            continue
        s = " ".join(tt)
        extra = len(tt) - len(query)
        if s == q:
            sc = 100.0
        elif set(query) <= set(tt):
            sc = 90 - 3 * extra
        elif all(any(w.startswith(qt) for w in tt) for qt in query):
            sc = 75 - 2 * extra
        else:
            sc = difflib.SequenceMatcher(None, q, s).ratio() * 70
        best = max(best, sc)
    return best


def rank_topics(topics: list[Topic], query: str, tut: Tutorial) -> list[tuple[float, Topic]]:
    q = tokens(query)
    if not q:
        return []
    prefixes = {tokens(p)[0] if tokens(p) else p for p in tut.prefixes} | set(tut.prefixes)
    ranked = [(score(q, t.title, prefixes), t) for t in topics]
    ranked = [r for r in ranked if r[0] >= MIN_RANK_SCORE]
    ranked.sort(key=lambda r: -r[0])
    return ranked[:10]


def norm_url(url: str) -> str:
    p = urlparse(url)
    return (p.path + (f"?{p.query}" if p.query else "")).lower()


def error_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=RED)


class OwnedView(discord.ui.View):
    def __init__(self, author_id: int, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This one belongs to someone else, run the command yourself!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.url:
                continue
            child.disabled = True  # type: ignore[attr-defined]
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)


class PageView(OwnedView):
    def __init__(self, cog: W3Schools, author_id: int, tut: Tutorial, data: PageData, topics: list[Topic] | None) -> None:
        super().__init__(author_id)
        self.cog, self.tut, self.data, self.topics = cog, tut, data, topics
        self.index = 0
        self.link = discord.ui.Button(label="Open on W3Schools", emoji="🔗", url=data.url, row=1)
        self.add_item(self.link)
        self._sync()

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.data.title[:256],
            url=self.data.url,
            description=self.data.pages[self.index],
            colour=W3_GREEN,
        )
        embed.set_footer(text=f"{self.tut.name} · page {self.index + 1}/{len(self.data.pages)} · preview from W3Schools")
        return embed

    def _topic_pos(self) -> int | None:
        if not self.topics:
            return None
        here = norm_url(self.data.url)
        for i, t in enumerate(self.topics):
            if norm_url(t.url) == here:
                return i
        return None

    def _sync(self) -> None:
        last = len(self.data.pages) - 1
        self.prev_page.disabled = self.index == 0
        self.next_page.disabled = self.index == last
        self.counter.label = f"{self.index + 1}/{last + 1}"
        self.link.url = self.data.url

        pos = self._topic_pos()
        has_prev = pos is not None and pos > 0
        has_next = pos is not None and self.topics is not None and pos < len(self.topics) - 1
        self.prev_topic.disabled, self.next_topic.disabled = not has_prev, not has_next
        self.prev_topic.label = trim(self.topics[pos - 1].title, 28) if has_prev and self.topics and pos is not None else "Previous lesson"
        self.next_topic.label = trim(self.topics[pos + 1].title, 28) if has_next and self.topics and pos is not None else "Next lesson"

    async def _show(self, interaction: discord.Interaction) -> None:
        self._sync()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _goto(self, interaction: discord.Interaction, topic: Topic) -> None:
        await interaction.response.defer()
        try:
            data = await self.cog.load_page(self.tut, topic.url)
        except W3Error as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        self.data, self.index = data, 0
        self._sync()
        await interaction.edit_original_response(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.primary, row=0)
    async def prev_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = max(0, self.index - 1)
        await self._show(interaction)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True, row=0)
    async def counter(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.primary, row=0)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = min(len(self.data.pages) - 1, self.index + 1)
        await self._show(interaction)

    @discord.ui.button(label="Previous lesson", emoji="⏪", style=discord.ButtonStyle.secondary, row=1)
    async def prev_topic(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        pos = self._topic_pos()
        if pos is not None and self.topics and pos > 0:
            await self._goto(interaction, self.topics[pos - 1])

    @discord.ui.button(label="Next lesson", emoji="⏩", style=discord.ButtonStyle.success, row=1)
    async def next_topic(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        pos = self._topic_pos()
        if pos is not None and self.topics and pos < len(self.topics) - 1:
            await self._goto(interaction, self.topics[pos + 1])

    @discord.ui.button(emoji="🗑", style=discord.ButtonStyle.danger, row=1)
    async def delete(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.delete()
        self.stop()


class ChoiceView(OwnedView):
    """Dropdown shown when the query matches several lessons."""

    def __init__(self, cog: W3Schools, author_id: int, tut: Tutorial, topics: list[Topic], choices: list[Topic]) -> None:
        super().__init__(author_id, timeout=120)
        self.cog, self.tut, self.topics, self.choices = cog, tut, topics, choices
        self.select = discord.ui.Select(
            placeholder="Pick a lesson…",
            options=[discord.SelectOption(label=t.title[:100], value=str(i), description=urlparse(t.url).path[-100:]) for i, t in enumerate(choices)],
        )
        self.select.callback = self.on_select
        self.add_item(self.select)

    async def on_select(self, interaction: discord.Interaction) -> None:
        topic = self.choices[int(self.select.values[0])]
        await interaction.response.defer()
        try:
            data = await self.cog.load_page(self.tut, topic.url)
        except W3Error as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        view = PageView(self.cog, self.author_id, self.tut, data, self.topics)
        view.message = self.message
        self.stop()
        await interaction.edit_original_response(embed=view.build_embed(), view=view)


class W3Schools(commands.Cog, name="W3Schools", command_attrs={"hidden": True}):
    """Look up W3Schools lessons."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._topics: dict[str, tuple[float, str, list[Topic]]] = {}
        self._pages: dict[str, tuple[float, PageData]] = {}

    # -- network --
    async def fetch(self, url: str) -> str:
        if urlparse(url).netloc.lower() not in {"www.w3schools.com", "w3schools.com"}:
            msg = "Refusing to fetch a non-W3Schools URL."
            raise W3Error(msg)
        try:
            async with self.bot.http_session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == HTTP_NOT_FOUND:
                    msg = "That page doesn't exist (404)."
                    raise W3Error(msg)
                if resp.status != HTTP_OK:
                    msg = f"W3Schools returned HTTP {resp.status}."
                    raise W3Error(msg)
                return await resp.text(errors="replace")
        except TimeoutError:
            msg = "W3Schools took too long to respond."
            raise W3Error(msg) from None
        except aiohttp.ClientError as exc:
            msg = f"Couldn't reach W3Schools ({type(exc).__name__})."
            raise W3Error(msg) from None

    @staticmethod
    def _evict(cache: dict) -> None:
        if len(cache) >= CACHE_MAX:
            cache.pop(min(cache, key=lambda k: cache[k][0]))

    async def get_topics(self, tut: Tutorial) -> tuple[str, list[Topic]]:
        hit = self._topics.get(tut.base)
        if hit and time.monotonic() - hit[0] < INDEX_TTL:
            return hit[1], hit[2]
        last: W3Error | None = None
        for candidate in ("default.asp", "index.php"):
            url = f"{SITE}/{tut.base}/{candidate}"
            try:
                html = await self.fetch(url)
            except W3Error as exc:
                last = exc
                continue
            topics = await asyncio.to_thread(parse_menu, html, url, tut)
            if topics:
                self._evict(self._topics)
                self._topics[tut.base] = (time.monotonic(), url, topics)
                return url, topics
        raise last or W3Error("Couldn't read the lesson list for this tutorial.")

    async def load_page(self, tut: Tutorial, url: str) -> PageData:
        hit = self._pages.get(url)
        if hit and time.monotonic() - hit[0] < PAGE_TTL:
            return hit[1]
        html = await self.fetch(url)
        data = await asyncio.to_thread(parse_page, html, url, tut)
        self._evict(self._pages)
        self._pages[url] = (time.monotonic(), data)
        return data

    # -- commands --
    @commands.group(
        name="w3schools",
        aliases=["w3", "w3s", "w3school"],
        invoke_without_command=True,
        case_insensitive=True,
    )
    async def w3schools(self, ctx: commands.Context, tutorial: str | None = None, *, topic: str | None = None) -> None:
        """Show a W3Schools lesson preview.

        `w3 python lists` · `w3 js array map` · `w3 css flexbox` · `w3 sql join`
        Omit the topic to get the tutorial's intro page.
        """
        if not tutorial:
            p = ctx.clean_prefix
            embed = discord.Embed(
                title="W3Schools",
                description="Search lessons from the W3Schools tutorials.",
                colour=W3_GREEN,
            )
            embed.add_field(
                name="Examples",
                value=f"`{p}w3 python lists`\n`{p}w3 js array map`\n`{p}w3 css flexbox`\n`{p}w3 sql join`",
                inline=False,
            )
            embed.add_field(name="Other commands", value=f"`{p}w3 tutorials` · `{p}w3 topics <tutorial>`", inline=False)
            await ctx.reply(embed=embed, mention_author=False)
            return

        tut = resolve_tutorial(tutorial)
        if not tut:
            close = difflib.get_close_matches(tutorial.lower(), [*TUTORIALS, *ALIASES], n=MAX_RANKED_CHOICES)
            hint = f" Did you mean {', '.join(f'`{c}`' for c in close)}?" if close else ""
            await ctx.reply(
                embed=error_embed("Unknown tutorial", f"`{tutorial}` isn't supported.{hint}\nSee `{ctx.clean_prefix}w3 tutorials`."),
                mention_author=False,
            )
            return

        try:
            async with ctx.typing():
                index_url, topics = await self.get_topics(tut)
                choices: list[Topic] = []
                if topic:
                    ranked = rank_topics(topics, topic, tut)
                    if not ranked:
                        msg = f"No **{tut.name}** lesson matches `{topic[:60]}`.\nBrowse them with `{ctx.clean_prefix}w3 topics {tut.key}`."
                        raise W3Error(msg)
                    best = ranked[0][0]
                    if best >= STRONG_RANK_SCORE and (len(ranked) == 1 or best - ranked[1][0] >= MIN_STRONG_RANK_GAP):
                        target = ranked[0][1]
                    else:
                        target, choices = None, [t for _, t in ranked]
                else:
                    target = Topic(f"{tut.name} Tutorial", index_url)
                data = await self.load_page(tut, target.url) if target else None
        except W3Error as exc:
            await ctx.reply(embed=error_embed("Couldn't load that", str(exc)), mention_author=False)
            return

        if data:
            view = PageView(self, ctx.author.id, tut, data, topics)
            view.message = await ctx.reply(embed=view.build_embed(), view=view, mention_author=False)
        else:
            embed = discord.Embed(
                title=f"Several {tut.name} lessons match",
                description=f"Results for `{topic[:60]}`: pick one below.",  # type: ignore[index]
                colour=W3_GREEN,
            )
            cview = ChoiceView(self, ctx.author.id, tut, topics, choices)
            cview.message = await ctx.reply(embed=embed, view=cview, mention_author=False)

    @w3schools.command(name="topics", aliases=["list", "ls", "lessons"])
    async def w3_topics(self, ctx: commands.Context, tutorial: str) -> None:
        """List every lesson in a tutorial: `w3 topics python`."""
        tut = resolve_tutorial(tutorial)
        if not tut:
            await ctx.reply(embed=error_embed("Unknown tutorial", f"See `{ctx.clean_prefix}w3 tutorials`."), mention_author=False)
            return
        try:
            async with ctx.typing():
                index_url, topics = await self.get_topics(tut)
        except W3Error as exc:
            await ctx.reply(embed=error_embed("Couldn't load that", str(exc)), mention_author=False)
            return

        lines = [f"• {t.title}" for t in topics]
        pages = ["\n".join(lines[i : i + 30]) for i in range(0, len(lines), 30)]
        data = PageData(title=f"{tut.name} · {len(topics)} lessons", url=index_url, pages=pages)
        view = PageView(self, ctx.author.id, tut, data, None)
        view.message = await ctx.reply(embed=view.build_embed(), view=view, mention_author=False)

    @w3schools.command(name="tutorials", aliases=["tuts", "languages"])
    async def w3_tutorials(self, ctx: commands.Context) -> None:
        """Show supported tutorials and their aliases."""
        by_target: dict[str, list[str]] = {}
        for alias, key in ALIASES.items():
            by_target.setdefault(key, []).append(alias)
        lines = []
        for key, tut in TUTORIALS.items():
            al = by_target.get(key)
            lines.append(f"`{key}`" + (f" ({', '.join(al)})" if al else "") + f" - {tut.name}")
        embed = discord.Embed(title="W3Schools tutorials", description="\n".join(lines), colour=W3_GREEN)
        embed.set_footer(text="Usage: w3 <tutorial> <topic>")
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(W3Schools(bot))
