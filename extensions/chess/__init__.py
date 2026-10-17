from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

from core.utils.formats import safe_text
from core.utils.paginator import PaginationLayout
from core.utils.views import NoticeLayout
from extensions.supercell import render
from extensions.supercell.api import IMAGE_DIRECTORY, ImageStore
from extensions.supercell.base import NO_MENTIONS, Page, TabbedLayout

if TYPE_CHECKING:
    from core import Bot
    from extensions.supercell.base import Loader

_log = logging.getLogger(__name__)

HTTP_OK = 200

API_BASE = "https://api.chess.com/pub"
STALE_TTL = 86_400
TIMEOUT = aiohttp.ClientTimeout(total=15)

COLOUR = discord.Colour.from_rgb(129, 182, 76)
THEME = render.Theme((82, 118, 58), (30, 28, 26), (235, 236, 208, 255))

FOOTER = "Chess.com \N{BULLET} Published Data API"

USERNAME_RE = re.compile(r"[A-Za-z0-9_-]{3,25}")
HTML_RE = re.compile(r"<[^>]+>")

DRAWS = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}

RATINGS = (
    ("Rapid", "chess_rapid"),
    ("Blitz", "chess_blitz"),
    ("Bullet", "chess_bullet"),
    ("Daily", "chess_daily"),
    ("Daily 960", "chess960_daily"),
)
BOARDS = {
    "rapid": "live_rapid",
    "blitz": "live_blitz",
    "bullet": "live_bullet",
    "daily": "daily",
    "tactics": "tactics",
}


class ChessError(commands.CommandError):
    """A failure whose message is safe to show to the user."""


class ChessNotFound(ChessError):
    pass


class ChessUnavailable(ChessError):
    pass


class Username(commands.Converter[str]):
    """A chess.com username or profile URL. Raises ``BadArgument`` so optional parameters can fall through."""

    async def convert(self, ctx: commands.Context[Bot], argument: str) -> str:
        argument = argument.strip()
        if "chess.com" in argument:
            argument = argument.rstrip("/").rsplit("/", 1)[-1]
        if not USERNAME_RE.fullmatch(argument):
            message = f"`{argument}` is not a valid chess.com username."
            raise commands.BadArgument(message)
        return argument.lower()


def _slug(value: str) -> str:
    return value.strip().rstrip("/").rsplit("/", 1)[-1]


def _when(timestamp: int | None, style: Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"] = "R") -> str:
    if not timestamp:
        return "-"
    return discord.utils.format_dt(datetime.fromtimestamp(timestamp, UTC), style)


def _date(timestamp: int | None) -> str:
    if not timestamp:
        return "-"
    return datetime.fromtimestamp(timestamp, UTC).strftime("%d %b %Y")


class ChessClient:
    """Cached access to chess.com's PubAPI. Requests are serial, as the API asks."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._gate = asyncio.Semaphore(1)

    @property
    def _redis(self):
        return self.bot.database.redis_client

    async def get(self, path: str, *, ttl: int = 60, fresh: bool = False) -> Any:
        """GET ``path``; ``fresh`` skips the cache read. Serves a stale copy if chess.com is unreachable."""
        key = f"chesscom:{path}"
        if not fresh and (hit := await self._redis.get(key)) is not None:
            return json.loads(hit)

        try:
            data = await self._send(path)
        except ChessUnavailable:
            if (stale := await self._redis.get(f"{key}:stale")) is not None:
                return json.loads(stale)
            raise

        payload = json.dumps(data, separators=(",", ":"))
        async with self._redis.pipeline(transaction=False) as pipe:
            pipe.set(key, payload, ex=ttl)
            pipe.set(f"{key}:stale", payload, ex=STALE_TTL)
            await pipe.execute()
        return data

    async def _send(self, path: str) -> Any:
        headers = {"Accept": "application/json"}

        try:
            async with self._gate, self.bot.http_session.get(f"{API_BASE}{path}", headers=headers, timeout=TIMEOUT) as response:
                status = response.status
                payload = await response.json(content_type=None) if status == HTTP_OK else None
        except (TimeoutError, aiohttp.ClientError, ValueError) as error:
            message = "Chess.com did not respond. Try again shortly."
            raise ChessUnavailable(message) from error

        if status == HTTP_OK:
            return payload

        _log.warning("chess.com GET %s -> %s", path, status)
        match status:
            case 404 | 410:
                message = "Chess.com has no record of that."
                raise ChessNotFound(message)
            case 429:
                message = "Chess.com is rate limiting the bot right now. Try again in a moment."
                raise ChessUnavailable(message)
            case _:
                message = f"Chess.com returned an unexpected error ({status})."
                raise ChessUnavailable(message)


def _game_line(game: dict, username: str) -> tuple[str, str]:
    """Return ``(outcome, line)`` for a game from ``username``'s point of view."""
    white, black = game["white"], game["black"]
    is_white = white["username"].lower() == username
    me, opponent = (white, black) if is_white else (black, white)

    if me["result"] == "win":
        outcome, icon = "win", "\N{LARGE GREEN CIRCLE}"
    elif me["result"] in DRAWS:
        outcome, icon = "draw", "\N{MEDIUM WHITE CIRCLE}"
    else:
        outcome, icon = "loss", "\N{LARGE RED CIRCLE}"

    accuracy = (game.get("accuracies") or {}).get("white" if is_white else "black")
    colour = "\N{WHITE CHESS KING}" if is_white else "\N{BLACK CHESS KING}"
    line = (
        f"{icon} vs **{safe_text(opponent['username'], 20)}** ({opponent.get('rating', '?')}) \N{MIDDLE DOT} "
        f"{str(game.get('time_class', '')).title()} \N{MIDDLE DOT} {colour}"
        + (f" \N{MIDDLE DOT} {accuracy:.0f}%" if accuracy else "")
        + f" \N{MIDDLE DOT} [view]({game['url']}) \N{MIDDLE DOT} {_when(game.get('end_time'))}"
    )
    return outcome, line


class ChessCom(commands.Cog, command_attrs={"hidden": True}):
    """Chess.com profiles, linked accounts and game statistics."""

    help_category = "Chess.com"
    help_emoji = "\N{BLACK CHESS PAWN}\N{VARIATION SELECTOR-16}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.api = ChessClient(bot)
        self.images = ImageStore(bot, directory=IMAGE_DIRECTORY.parent / "chesscom")

    async def resolve_username(self, ctx: commands.Context[Bot], username: str | None, user: discord.User | None) -> str:
        if username:
            return username

        target = user or ctx.author
        account = await self.bot.database.get_chess_account(target.id)

        command_signature = self.bot.help_command.get_command_signature(self.link) if self.bot.help_command is not None else None

        if account is None:
            who = "You haven't" if target == ctx.author else f"{target.display_name} hasn't"
            message = f"{who} linked a chess.com account."
            if command_signature:
                message += f" Use `{command_signature}` to link one."

            raise ChessError(message)
        return account["username"]

    async def link_text(self, username: str) -> str | None:
        owners = await self.bot.database.get_chess_owners(username)
        if not owners:
            return None
        return "Linked to " + ", ".join(f"<@{user_id}>" + (" \N{WHITE HEAVY CHECK MARK}" if verified else "") for user_id, verified in owners)

    async def paginate(self, ctx: commands.Context[Bot], title: str, lines: list[str], *, per_page: int = 10) -> None:
        if not lines:
            message = "Nothing to show."
            raise ChessNotFound(message)

        pages: list[list[discord.ui.Item]] = [[discord.ui.TextDisplay("\n".join(chunk))] for chunk in discord.utils.as_chunks(lines, per_page)]
        layout = PaginationLayout(
            ctx.author,
            header=discord.ui.TextDisplay(f"### {title}"),
            footer=discord.ui.TextDisplay("-# Chess.com"),
            items=pages,
        )
        await layout.start(ctx, allowed_mentions=NO_MENTIONS)

    @commands.group(name="chess.com", aliases=["chesscom", "chessdotcom"], invoke_without_command=True)
    async def chess(
        self,
        ctx: commands.Context[Bot],
        username: Annotated[str | None, Username] = commands.parameter(description="chess.com username or profile link.", default=None),
        user: discord.User = commands.parameter(description="Use this member's linked account.", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Show a chess.com player profile."""
        async with ctx.typing():
            username = await self.resolve_username(ctx, username, user)
            profile = await self.api.get(f"/player/{quote(username)}", ttl=300)
            await TabbedLayout(ctx.author, tabs=self._tabs(profile), colour=COLOUR).start(ctx)

    @chess.command(name="link")
    async def link(
        self,
        ctx: commands.Context[Bot],
        *,
        username: Annotated[str, Username] = commands.parameter(description="chess.com username or profile link."),
    ) -> None:
        """Link your chess.com account."""
        async with ctx.typing():
            profile = await self.api.get(f"/player/{quote(username)}", ttl=300)
            canonical = profile["username"].lower()
            await self.bot.database.set_chess_account(ctx.author.id, username=canonical)

        command_signature = self.bot.help_command.get_command_signature(self.verify) if self.bot.help_command is not None else None

        body = f"Linked **{discord.utils.escape_markdown(profile['username'])}** to your Discord account."
        if command_signature:
            body += f"\nRun `{command_signature}` to prove it's yours."

        await ctx.reply(view=NoticeLayout.success(body, title="chess.com account linked"))

    @chess.command(name="unlink")
    async def unlink(self, ctx: commands.Context[Bot]) -> None:
        """Unlink your chess.com account."""
        removed = await self.bot.database.remove_chess_account(ctx.author.id)
        view = (
            NoticeLayout.success("Your chess.com account has been unlinked.")
            if removed
            else NoticeLayout.warning("You don't have a chess.com account linked.")
        )
        await ctx.reply(view=view)

    @chess.command(name="verify")
    async def verify(self, ctx: commands.Context[Bot]) -> None:
        """Prove you own your linked account by putting a one-time code in your chess.com location."""
        database = self.bot.database
        account = await database.get_chess_account(ctx.author.id)

        command_signature = self.bot.help_command.get_command_signature(self.link) if self.bot.help_command is not None else None

        if account is None:
            message = f"Link an account first with `{command_signature}`."
            raise ChessError(message)

        if account.get("verified"):
            await ctx.reply(view=NoticeLayout.info("This account is already verified.", title="Already verified"), ephemeral=True)
            return

        chessdotcom = self.chess.name

        code = account.get("code")
        if not code:
            code = f"verify-{secrets.token_hex(3)}"
            await database.set_chess_verification(ctx.author.id, verified=False, code=code)
            body = (
                f"Set the **Location** field on your chess.com profile to `{code}`, then run "
                f"`{ctx.clean_prefix}{chessdotcom} verify` again. You can change it back afterwards."
            )
            await ctx.reply(view=NoticeLayout.info(body, title="Verify your account"), ephemeral=True)
            return

        async with ctx.typing():
            profile = await self.api.get(f"/player/{quote(account['username'])}", ttl=60, fresh=True)

        if code not in (profile.get("location") or ""):
            message = f"Bot could not find `{code}` in your location yet. Chess.com can take a few minutes to update, so try again shortly."
            raise ChessError(message)

        await database.set_chess_verification(ctx.author.id, verified=True, code=None)
        await ctx.reply(view=NoticeLayout.success("Your chess.com account is verified.", title="Verified"), ephemeral=True)

    @chess.command(name="club")
    async def club(
        self,
        ctx: commands.Context[Bot],
        *,
        club: str = commands.parameter(description="Club name from its URL or the full link."),
    ) -> None:
        """Show a chess.com club."""
        async with ctx.typing():
            slug = _slug(club).lower().replace(" ", "-")
            data = await self.api.get(f"/club/{quote(slug)}", ttl=600)
            tabs: dict[str, Loader] = {
                "Overview": lambda: self._club_overview(data),
                "Members": lambda: self._club_members(data),
            }
            await TabbedLayout(ctx.author, tabs=tabs, colour=COLOUR).start(ctx)

    @chess.command(name="puzzle")
    async def puzzle(
        self,
        ctx: commands.Context[Bot],
        random: bool = commands.parameter(description="Show a random puzzle instead of the daily one.", default=False),
    ) -> None:
        """Show the daily puzzle, or a random one."""
        async with ctx.typing():
            data = await self.api.get("/puzzle/random" if random else "/puzzle", ttl=1 if random else 600)

        lines = [f"### {data.get('title', 'Puzzle')}", f"[Solve on chess.com]({data['url']})"]
        if published := data.get("publish_time"):
            lines.append(f"-# Published {_when(published, 'D')}")

        container = discord.ui.Container(accent_colour=COLOUR)
        container.add_item(discord.ui.TextDisplay("\n".join(lines)))
        if image := data.get("image"):
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(image)))

        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.reply(view=view)

    @chess.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(
        self,
        ctx: commands.Context[Bot],
        board: Literal["rapid", "blitz", "bullet", "daily", "tactics"] = commands.parameter(
            description="Which leaderboard to show.", default="rapid"
        ),
    ) -> None:
        """Show the top players on a leaderboard."""
        async with ctx.typing():
            data = await self.api.get("/leaderboards", ttl=900)

        lines = [
            f"`{entry.get('rank', index):>2}` {('**' + entry['title'] + '** ') if entry.get('title') else ''}"
            f"{discord.utils.escape_markdown(entry['username'])} \N{MIDDLE DOT} {entry.get('score', 0):,}"
            for index, entry in enumerate(data.get(BOARDS[board], []), 1)
        ]
        await self.paginate(ctx, f"Top players \N{MIDDLE DOT} {board.title()}", lines)

    @chess.command(name="streamers")
    async def streamers(self, ctx: commands.Context[Bot]) -> None:
        """Show chess.com streamers, live ones first."""
        async with ctx.typing():
            data = await self.api.get("/streamers", ttl=120)

        streamers = sorted(data.get("streamers", []), key=lambda s: not s.get("is_live"))
        lines = [
            f"{'\N{LARGE RED CIRCLE}' if s.get('is_live') else '\N{MEDIUM WHITE CIRCLE}'} [{discord.utils.escape_markdown(s['username'])}]({s.get('twitch_url') or s['url']})"
            for s in streamers
        ]
        await self.paginate(ctx, "Streamers", lines)

    @chess.command(name="tournament")
    async def tournament(
        self,
        ctx: commands.Context[Bot],
        *,
        tournament: str = commands.parameter(description="Tournament name from its URL or the full link."),
    ) -> None:
        """Show a tournament by its URL name or link."""
        async with ctx.typing():
            data = await self.api.get(f"/tournament/{quote(_slug(tournament))}", ttl=300)

        settings = data.get("settings") or {}
        lines = [
            f"### {data.get('name', 'Tournament')}",
            f"**Status** {str(data.get('status', '-')).title()}",
            f"**Format** {str(settings.get('type', '-')).title()} \N{MIDDLE DOT} {str(settings.get('time_class', '-')).title()} ({settings.get('time_control', '-')})",
            f"**Players** {len(data.get('players', []))} \N{MIDDLE DOT} **Rounds** {len(data.get('rounds', []))}",
        ]
        if finish := data.get("finish_time"):
            lines.append(f"**Finished** {_when(finish)}")
        lines.append(f"[Open on chess.com]({data['url']})")
        await ctx.reply(view=NoticeLayout("\n".join(lines), colour=COLOUR))

    def _tabs(self, profile: dict) -> dict[str, Loader]:
        username = profile["username"].lower()
        return {
            "Overview": lambda: self._overview(profile),
            "Ratings": lambda: self._ratings(profile),
            "Games": lambda: self._games(username),
            "Clubs": lambda: self._clubs(username),
        }

    async def _overview(self, profile: dict) -> Page:
        username = profile["username"].lower()
        stats = await self.api.get(f"/player/{quote(username)}/stats", ttl=300)
        portrait = await self.images.get(profile.get("avatar"))

        def last(key: str) -> str:
            return str(((stats.get(key) or {}).get("last") or {}).get("rating", "-"))

        puzzle_rush = ((stats.get("puzzle_rush") or {}).get("best") or {}).get("score", "-")
        tactics = ((stats.get("tactics") or {}).get("highest") or {}).get("rating", "-")
        country = _slug(profile["country"]) if profile.get("country") else "-"

        tiles = [
            ("Rapid", last("chess_rapid")),
            ("Blitz", last("chess_blitz")),
            ("Bullet", last("chess_bullet")),
            ("Daily", last("chess_daily")),
            ("Tactics", str(tactics)),
            ("Puzzle Rush", str(puzzle_rush)),
            ("FIDE", str(stats.get("fide") or "-")),
            ("Followers", f"{profile.get('followers', 0):,}"),
            ("Country", country),
            ("Joined", _date(profile.get("joined"))),
            ("Last online", _date(profile.get("last_online"))),
            ("Status", str(profile.get("status", "-")).title()),
        ]
        location = profile.get("location") or ""
        parts = [profile.get("name"), "" if location.startswith("verify-") else location]
        image = await asyncio.to_thread(
            render.profile_card,
            THEME,
            name=profile["username"],
            tag=profile.get("name") or f"#{profile.get('player_id', '')}",
            level=profile.get("title") or str(profile.get("status", "member")).title(),
            line=" \N{BULLET} ".join(p for p in parts if p) or "No details set",
            portrait=portrait,
            stats=tiles,
            footer=FOOTER,
        )
        text = f"-# [Open on chess.com]({profile['url']})"
        if linked := await self.link_text(username):
            text += f"\n-# {linked}"
        return Page(text=text, image=image)

    async def _ratings(self, profile: dict) -> Page:
        username = profile["username"].lower()
        stats = await self.api.get(f"/player/{quote(username)}/stats", ttl=300)

        bars: list[render.Bar] = []
        for label, key in RATINGS:
            entry = stats.get(key)
            if not entry:
                continue
            current = (entry.get("last") or {}).get("rating", 0)
            best = max((entry.get("best") or {}).get("rating", current), current)
            record = entry.get("record") or {}
            bars.append(
                render.Bar(
                    f"{label} \N{MIDDLE DOT} {record.get('win', 0)}W {record.get('loss', 0)}L {record.get('draw', 0)}D",
                    current,
                    best,
                )
            )
        if not bars:
            return Page(text="No rated games yet.")

        image = await asyncio.to_thread(
            render.bars_card,
            THEME,
            title=f"{profile['username']}'s ratings",
            subtitle="Current rating / personal best",
            bars=bars,
            footer=FOOTER,
        )
        return Page(image=image)

    async def _games(self, username: str) -> Page:
        data = await self.api.get(f"/player/{quote(username)}/games/archives", ttl=600)
        archives = data.get("archives", [])
        if not archives:
            return Page(text="No games played yet.")

        games: list[dict] = []
        for url in reversed(archives[-2:]):
            month = await self.api.get(url.removeprefix(API_BASE), ttl=120)
            games.extend(reversed(month.get("games", [])))
            if len(games) >= 10:
                break

        results = [_game_line(game, username) for game in games[:10]]
        wins = sum(1 for outcome, _ in results if outcome == "win")
        losses = sum(1 for outcome, _ in results if outcome == "loss")
        header = f"### Recent games\nLast {len(results)}: **{wins}W {losses}L {len(results) - wins - losses}D**"
        return Page(text="\n".join([header, "", *(line for _, line in results)]))

    async def _clubs(self, username: str) -> Page:
        data = await self.api.get(f"/player/{quote(username)}/clubs", ttl=900)
        clubs = sorted(data.get("clubs", []), key=lambda c: c.get("last_activity", 0), reverse=True)[:15]
        if not clubs:
            return Page(text="Not a member of any clubs.")

        lines = ["### Clubs"]
        lines += [f"[{safe_text(c['name'], 40)}]({c['url']}) \N{MIDDLE DOT} joined {_when(c.get('joined'), 'd')}" for c in clubs]
        return Page(text="\n".join(lines))

    async def _club_overview(self, club: dict) -> Page:
        portrait = await self.images.get(club.get("icon"))
        members = club.get("members_count", 0)
        tiles = [
            ("Members", f"{members:,}"),
            ("Avg daily", str(club.get("average_daily_rating", "-"))),
            ("Created", _date(club.get("created"))),
            ("Last active", _date(club.get("last_activity"))),
            ("Country", _slug(club["country"]) if club.get("country") else "-"),
            ("Visibility", str(club.get("visibility", "-")).title()),
            ("Admins", str(len(club.get("admins", [])))),
            ("Club ID", str(club.get("club_id", "-"))),
        ]
        description = HTML_RE.sub(" ", club.get("description") or "").replace("\n", " ").strip()
        image = await asyncio.to_thread(
            render.profile_card,
            THEME,
            name=club["name"],
            tag=f"#{club.get('club_id', '')}",
            level=f"{members:,} members",
            line=description or "No description",
            portrait=portrait,
            stats=tiles,
            footer=FOOTER,
        )
        return Page(text=f"-# [Open on chess.com]({club['url']})", image=image)

    async def _club_members(self, club: dict) -> Page:
        slug = _slug(club["url"])
        data = await self.api.get(f"/club/{quote(slug)}/members", ttl=900)
        admins = [_slug(url) for url in club.get("admins", [])][:20]
        lines = [
            "### Members",
            f"**This week** {len(data.get('weekly', []))} \N{MIDDLE DOT} **This month** {len(data.get('monthly', []))} \N{MIDDLE DOT} **All time** {len(data.get('all_time', []))}",
        ]
        if admins:
            lines += ["", "**Admins**", ", ".join(discord.utils.escape_markdown(a) for a in admins)]
        return Page(text="\n".join(lines))


async def setup(bot: Bot) -> None:
    await bot.add_cog(ChessCom(bot))
