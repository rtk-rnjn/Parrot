from __future__ import annotations

import contextlib
import re
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot

CHEAT_SH_URL = "https://cheat.sh/{path}"
HEADERS = {"User-Agent": "curl/8.5.0"}
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

CACHE_TTL = 300  # seconds
CACHE_MAX = 128
PAGE_CHARS = 1800
PAGE_LINES = 32
DEFAULT_LANGUAGE = "python"

HTTP_OK = 200
HTTP_NOT_FOUND = 404

LANGUAGES = frozenset(
    [
        "arduino",
        "assembly",
        "awk",
        "bash",
        "basic",
        "bf",
        "c",
        "chapel",
        "clean",
        "clojure",
        "coffee",
        "cpp",
        "csharp",
        "d",
        "dart",
        "delphi",
        "dylan",
        "eiffel",
        "elixir",
        "elisp",
        "elm",
        "erlang",
        "factor",
        "fortran",
        "forth",
        "fsharp",
        "go",
        "groovy",
        "haskell",
        "java",
        "js",
        "julia",
        "kotlin",
        "latex",
        "lisp",
        "lua",
        "matlab",
        "nim",
        "ocaml",
        "octave",
        "perl",
        "perl6",
        "php",
        "pike",
        "python",
        "python3",
        "r",
        "racket",
        "ruby",
        "rust",
        "scala",
        "scheme",
        "solidity",
        "swift",
        "tcsh",
        "tcl",
        "objective-c",
        "vb",
        "vbnet",
        "cmake",
        "django",
        "flask",
        "git",
    ]
)

ALIASES = {
    "py": "python",
    "py3": "python3",
    "python2": "python",
    "javascript": "js",
    "node": "js",
    "nodejs": "js",
    "golang": "go",
    "c++": "cpp",
    "c#": "csharp",
    "cs": "csharp",
    "f#": "fsharp",
    "rb": "ruby",
    "rs": "rust",
    "kt": "kotlin",
    "sh": "bash",
    "shell": "bash",
    "objc": "objective-c",
    "vb.net": "vbnet",
    "perl5": "perl",
    "pl": "perl",
    "hs": "haskell",
    "ex": "elixir",
    "tex": "latex",
    "coffeescript": "coffee",
    "emacs-lisp": "elisp",
    "raku": "perl6",
}

HIGHLIGHT = {
    "js": "javascript",
    "csharp": "cs",
    "python3": "python",
    "fsharp": "fs",
    "objective-c": "objectivec",
    "vbnet": "vbnet",
    "elisp": "lisp",
    "perl6": "perl",
    "coffee": "coffeescript",
    "bf": "",
    "assembly": "x86asm",
    "cmake": "cmake",
    "git": "sh",
    "django": "python",
    "flask": "python",
    "tcsh": "sh",
    "arduino": "cpp",
}

BLURPLE = discord.Colour(0x5865F2)
RED = discord.Colour(0xED4245)


class QueryError(Exception):
    """User-facing problem with the query itself."""


@dataclass
class Request:
    base_path: str  # e.g. "python/reverse+a+list"
    title: str  # e.g. "python · reverse a list"
    highlight: str = ""  # code-block language
    quiet: bool = False  # cheat.sh option Q (no comments)
    alt: int = 0  # alternative answer index (/1, /2, ...)
    defaulted: bool = False  # language was guessed
    allow_alt: bool = True

    @property
    def path(self) -> str:
        return f"{self.base_path}/{self.alt}" if self.alt else self.base_path

    @property
    def url(self) -> str:
        return CHEAT_SH_URL.format(path=self.path)


def make_path(scope: str | None, words: list[str]) -> str:
    parts = []
    if scope:
        parts.append(quote(scope, safe=""))
    if words:
        parts.append("+".join(quote(w, safe="-:~") for w in words))
    return "/".join(parts)


def resolve_language(token: str) -> str | None:
    low = token.lower()
    low = ALIASES.get(low, low)
    return low if low in LANGUAGES else None


def parse_flags(terms: tuple[str, ...]) -> tuple[list[str], bool, int]:
    """Pull `-q/--quiet` and `-n/--alt N` out of the raw words."""
    words: list[str] = []
    quiet, alt = False, 0
    it = iter(terms)
    for tok in it:
        low = tok.lower()
        if low in {"-q", "--quiet", "--no-comments"}:
            quiet = True
        elif low in {"-n", "--alt", "--answer"}:
            nxt = next(it, None)
            if nxt is None or not nxt.isdigit():
                msg = "`-n` needs a number, e.g. `cheat python random string -n 2`."
                raise QueryError(msg)
            alt = int(nxt)
        else:
            words.append(tok)
    return words, quiet, alt


def parse_query(terms: tuple[str, ...]) -> Request:
    words, quiet, alt = parse_flags(terms)
    if not words:
        msg = "Give me something to look up, e.g. `cheat python reverse a list`."
        raise QueryError(msg)

    if "/" in words[0]:
        head, _, tail = words[0].partition("/")
        words = [head, *([tail] if tail else []), *words[1:]]

    scope = resolve_language(words[0])
    defaulted = False
    if scope:
        rest = words[1:]
    elif len(words) == 1:
        rest, scope = words, None
    else:
        scope, rest, defaulted = DEFAULT_LANGUAGE, words, True

    rest = [w.strip("/") for w in rest if w.strip("/")]
    if scope:
        title = f"{scope} · {' '.join(rest)}" if rest else scope
        hl = HIGHLIGHT.get(scope, scope)
    else:
        title, hl = " ".join(rest), "sh"

    return Request(
        base_path=make_path(scope, rest),
        title=title,
        highlight=hl,
        quiet=quiet,
        alt=alt,
        defaulted=defaulted,
    )


def special_request(scope: str | None, page: str, *, title: str, allow_alt: bool = False) -> Request:
    base = make_path(scope, [page])
    return Request(base_path=base, title=title, highlight="", allow_alt=allow_alt)


def clean_text(text: str) -> str:
    text = ANSI_RE.sub("", text).expandtabs(4).replace("```", "`\u200b``")
    return text.strip("\n").rstrip()


def paginate(text: str) -> list[str]:
    pages: list[str] = []
    cur: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal cur, size
        if cur:
            pages.append("\n".join(cur))
        cur, size = [], 0

    for raw in text.splitlines():
        line = raw.rstrip()
        chunks = [line[i : i + PAGE_CHARS] for i in range(0, len(line), PAGE_CHARS)] or [""]
        for chunk in chunks:
            if cur and (size + len(chunk) + 1 > PAGE_CHARS or len(cur) >= PAGE_LINES):
                flush()
            cur.append(chunk)
            size += len(chunk) + 1
    flush()
    return pages or ["(empty)"]


def error_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=RED)


@dataclass
class Result:
    status: int
    text: str

    @property
    def ok(self) -> bool:
        return self.status == HTTP_OK and bool(self.text.strip())


class CheatView(discord.ui.View):
    def __init__(self, cog: CheatSheet, author_id: int, req: Request, text: str) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.author_id = author_id
        self.req = req
        self.pages = paginate(text)
        self.index = 0
        self.message: discord.Message | None = None
        self._sync()

    # -- rendering --
    def build_embed(self) -> discord.Embed:
        req = self.req
        body = self.pages[self.index]
        embed = discord.Embed(
            title=f"\N{OPEN BOOK} {req.title}"[:256],
            url=req.url,
            description=f"```{req.highlight}\n{body}\n```",
            colour=BLURPLE,
        )
        bits = [f"Page {self.index + 1}/{len(self.pages)}"]
        if req.allow_alt:
            bits.append(f"Answer #{req.alt}")
        if req.quiet:
            bits.append("comments hidden")
        if req.defaulted:
            bits.append(f"language defaulted to {DEFAULT_LANGUAGE}")
        embed.set_footer(text=" • ".join(bits) + " • cheat.sh")
        return embed

    def _sync(self) -> None:
        last = len(self.pages) - 1
        self.first.disabled = self.prev.disabled = self.index == 0
        self.next.disabled = self.last.disabled = self.index == last
        self.counter.label = f"{self.index + 1}/{len(self.pages)}"
        self.another.disabled = not self.req.allow_alt
        self.comments.disabled = not self.req.allow_alt
        self.comments.label = "Show comments" if self.req.quiet else "Hide comments"

    async def _show(self, interaction: discord.Interaction) -> None:
        self._sync()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _reload(self, interaction: discord.Interaction, candidates: list[Request]) -> None:
        await interaction.response.defer()
        for new in candidates:
            result = await self.cog.fetch(new)
            if result.ok:
                self.req, self.pages, self.index = new, paginate(result.text), 0
                self._sync()
                await interaction.edit_original_response(embed=self.build_embed(), view=self)
                return
        await interaction.followup.send("No other version of this answer available.", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This cheat sheet belongs to someone else, run the command yourself!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)

    @discord.ui.button(emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", style=discord.ButtonStyle.secondary, row=0)
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = 0
        await self._show(interaction)

    @discord.ui.button(emoji="\N{BLACK LEFT-POINTING TRIANGLE}", style=discord.ButtonStyle.primary, row=0)
    async def prev(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = max(0, self.index - 1)
        await self._show(interaction)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True, row=0)
    async def counter(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", style=discord.ButtonStyle.primary, row=0)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = min(len(self.pages) - 1, self.index + 1)
        await self._show(interaction)

    @discord.ui.button(emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", style=discord.ButtonStyle.secondary, row=0)
    async def last(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = len(self.pages) - 1
        await self._show(interaction)

    @discord.ui.button(label="Another answer", emoji="\N{TWISTED RIGHTWARDS ARROWS}", style=discord.ButtonStyle.success, row=1)
    async def another(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        # Try the next alternative; if it doesn't exist, wrap around to the first.
        await self._reload(
            interaction,
            [replace(self.req, alt=self.req.alt + 1), replace(self.req, alt=0)],
        )

    @discord.ui.button(label="Hide comments", emoji="\N{SPEECH BALLOON}", style=discord.ButtonStyle.secondary, row=1)
    async def comments(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._reload(interaction, [replace(self.req, quiet=not self.req.quiet)])

    @discord.ui.button(emoji="\N{WASTEBASKET}", style=discord.ButtonStyle.danger, row=1)
    async def delete(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer()
        if interaction.message:
            await interaction.message.delete()
        self.stop()


class CheatSheet:
    bot: Parrot

    def __init__(self) -> None:
        self._cheat_sh_response_cache: dict[str, tuple[float, Result]] = {}

    async def fetch(self, req: Request) -> Result:
        url = CHEAT_SH_URL.format(path=req.path) + ("?TQ" if req.quiet else "?T")
        now = time.monotonic()
        cached = self._cheat_sh_response_cache.get(url)
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

        try:
            async with self.bot.http_session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status, raw = resp.status, await resp.text(errors="replace")
        except TimeoutError:
            return Result(0, "cheat.sh took too long to respond.")
        except aiohttp.ClientError as exc:
            return Result(0, f"Couldn't reach cheat.sh ({type(exc).__name__}).")

        result = Result(status, clean_text(raw))
        if result.ok:
            if len(self._cheat_sh_response_cache) >= CACHE_MAX:
                self._cheat_sh_response_cache.pop(min(self._cheat_sh_response_cache, key=lambda k: self._cheat_sh_response_cache[k][0]))
            self._cheat_sh_response_cache[url] = (now, result)
        return result

    async def _run(self, ctx: commands.Context, req: Request) -> discord.Message:
        async with ctx.typing():
            result = await self.fetch(req)

        if not result.ok:
            if result.status == HTTP_NOT_FOUND or (result.status == HTTP_OK and not result.text.strip()):
                hint = result.text[:900]
                desc = f"Nothing found for **{discord.utils.escape_markdown(req.title)}**."
                if hint:
                    desc += f"\n```\n{hint}\n```"
                desc += "\nTry `cheat search <keyword>` or `cheat languages`."
                return await ctx.reply(embed=error_embed("No cheat sheet found", desc), mention_author=False)
            title = "Network problem" if result.status == 0 else f"cheat.sh returned HTTP {result.status}"
            return await ctx.reply(embed=error_embed(title, result.text[:900] or "Try again later."), mention_author=False)

        view = CheatView(self, ctx.author.id, req, result.text)
        view.message = await ctx.reply(embed=view.build_embed(), view=view, mention_author=False)
        return view.message

    async def _safe(self, ctx: commands.Context, builder):
        try:
            req = builder()
        except QueryError as exc:
            return await ctx.reply(embed=error_embed("Invalid query", str(exc)), mention_author=False)

        return await self._run(ctx, req)

    async def cheat_sheet(self, ctx: commands.Context, *terms: str):
        if terms:
            return await self._safe(ctx, lambda: parse_query(terms))

        p = ctx.clean_prefix
        embed = (
            discord.Embed(
                title="cheat.sh",
                description="Community cheat sheets for 50+ languages and 1000+ commands.",
                colour=BLURPLE,
            )
            .add_field(
                name="Look something up",
                value=(
                    f"`{p}cheat tar`\n"
                    f"`{p}cheat python reverse a list`\n"
                    f"`{p}cheat go/pointers`\n"
                    f"`{p}cheat js parse json -q` *(no comments)*\n"
                    f"`{p}cheat python random string -n 2` *(2nd answer)*"
                ),
                inline=False,
            )
            .add_field(
                name="Subcommands",
                value=(f"`search` `list` `learn` `hello` `oneliners` `languages` `random`\nUse `{p}help cheat <subcommand>` for details."),
                inline=False,
            )
        )
        return await ctx.reply(embed=embed, mention_author=False)

    async def search(self, ctx: commands.Context, *terms: str) -> None:
        def build() -> Request:
            words, _, _ = parse_flags(terms)
            if not words:
                msg = "What should I search for? e.g. `cheat search snapshot`."
                raise QueryError(msg)
            scope = resolve_language(words[0]) if len(words) > 1 else None
            kw = words[1:] if scope else words
            return Request(
                base_path=make_path(scope, ["~" + "+".join(quote(w, safe="-") for w in kw)]).replace("%2B", "+"),
                title=f"search · {' '.join(kw)}" + (f" in {scope}" if scope else ""),
                allow_alt=False,
            )

        await self._safe(ctx, build)

    async def list(self, ctx: commands.Context, language: str | None = None) -> None:
        """List all topics (`cheat list`) or the topics of one language (`cheat list go`)."""

        def build() -> Request:
            scope = resolve_language(language) if language else None
            if language and not scope:
                msg = f"`{language}` isn't a supported language. See `cheat languages`."
                raise QueryError(msg)
            return special_request(scope, ":list", title=f"{scope or 'all'} · topics")

        await self._safe(ctx, build)

    def _lang_page(self, page: str, label: str):
        async def callback(ctx: commands.Context, language: str) -> None:
            def build() -> Request:
                scope = resolve_language(language)
                if not scope:
                    msg = f"`{language}` isn't a supported language. See `cheat languages`."
                    raise QueryError(msg)
                req = special_request(scope, page, title=f"{scope} · {label}")
                req.highlight = HIGHLIGHT.get(scope, scope)
                return req

            await self._safe(ctx, build)

        return callback

    async def random(self, ctx: commands.Context, language: str | None = None) -> None:
        """A random cheat sheet, optionally within a language."""

        def build() -> Request:
            scope = resolve_language(language) if language else None
            if language and not scope:
                msg = f"`{language}` isn't a supported language. See `cheat languages`."
                raise QueryError(msg)
            req = special_request(scope, ":random", title=f"{scope or 'any'} · random")
            req.highlight = HIGHLIGHT.get(scope, scope) if scope else "sh"
            return req

        await self._safe(ctx, build)

    async def languages(self, ctx: commands.Context) -> None:
        """Show supported languages/topics and their aliases."""
        names = sorted(LANGUAGES)
        cols = 4
        rows = -(-len(names) // cols)
        grid = [names[i::rows] for i in range(rows)]
        table = "\n".join("".join(n.ljust(14) for n in row) for row in grid)
        alias_text = ", ".join(f"`{a}`→`{b}`" for a, b in list(ALIASES.items())[:14])
        embed = discord.Embed(
            title="Supported languages & topics",
            description=f"```\n{table}\n```",
            colour=BLURPLE,
        )
        embed.add_field(name="Common aliases", value=alias_text + ", …", inline=False)
        embed.set_footer(text="Anything else is treated as a UNIX/Linux command (e.g. `cheat tar`).")
        await ctx.reply(embed=embed, mention_author=False)
