from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import math
import re
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=12)
USER_AGENT = "discord-coding-stats-bot"

LC_URL = "https://leetcode.com/graphql"
LC_COLOURS = {"Easy": 0x00B8A3, "Medium": 0xFFC01E, "Hard": 0xFF375F}
LC_ORANGE = 0xFFA116

CF_API = "https://codeforces.com/api"
CF_MIN_INTERVAL = 2.1  # Codeforces allows 1 request / 2 s


LC_DAILY_QUERY = """
query questionOfToday {
  activeDailyCodingChallengeQuestion {
    date
    link
    question {
      questionFrontendId
      title
      titleSlug
      difficulty
      acRate
      isPaidOnly
      topicTags { name }
    }
  }
}
"""

LC_USER_QUERY = """
query userStats($username: String!) {
  allQuestionsCount { difficulty count }
  matchedUser(username: $username) {
    username
    profile { realName userAvatar ranking }
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    userCalendar { streak totalActiveDays }
  }
  userContestRanking(username: $username) {
    rating
    attendedContestsCount
    globalRanking
    totalParticipants
    topPercentage
  }
}
"""

LC_USER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")
CF_HANDLE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,24}$")

# (low, high, RGB) -- the colour bands used on Codeforces rating graphs
CF_BANDS = [
    (0, 1200, (204, 204, 204)),
    (1200, 1400, (119, 255, 119)),
    (1400, 1600, (119, 221, 187)),
    (1600, 1900, (170, 170, 255)),
    (1900, 2100, (255, 136, 255)),
    (2100, 2400, (255, 204, 136)),
    (2400, 10_000, (255, 119, 119)),
]


class LookupFailed(Exception):
    """A user-facing failure (bad name, upstream down, not configured...)."""


@contextlib.asynccontextmanager
async def _reporting(ctx: commands.Context):
    """Turn ``LookupFailed`` into a plain chat message instead of an error traceback."""
    try:
        yield
    except LookupFailed as exc:
        await ctx.send(str(exc), allowed_mentions=discord.AllowedMentions.none())


class TTLCache:
    """Tiny in-memory cache with per-entry expiry and a size bound."""

    def __init__(self, ttl: float, maxsize: int = 256) -> None:
        self.ttl = ttl
        self.maxsize = maxsize
        self._data: dict[Any, tuple[float, Any]] = {}

    def get(self, key: Any) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        if item[0] < time.monotonic():
            del self._data[key]
            return None
        return item[1]

    def set(self, key: Any, value: Any, ttl: float | None = None) -> None:
        self._data.pop(key, None)
        self._data[key] = (time.monotonic() + (self.ttl if ttl is None else ttl), value)
        while len(self._data) > self.maxsize:
            del self._data[next(iter(self._data))]  # dicts keep insertion order -> oldest first


def _now() -> datetime:
    return datetime.now(UTC)


def _seconds_until_utc_midnight() -> float:
    now = _now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (tomorrow - now).total_seconds() + 5


def _bar(part: int, whole: int, width: int = 14) -> str:
    filled = round(width * part / whole) if whole else 0
    return "\N{FULL BLOCK}" * filled + "\N{LIGHT SHADE}" * (width - filled)


def lc_daily_embed(daily: dict[str, Any]) -> discord.Embed:
    q = daily["question"]
    link = daily["link"]
    url = f"https://leetcode.com{link}" if link.startswith("/") else link
    embed = discord.Embed(
        title=f"{q['questionFrontendId']}. {q['title']}",
        url=url,
        colour=LC_COLOURS.get(q["difficulty"], LC_ORANGE),
    )
    embed.add_field(name="Difficulty", value=q["difficulty"])
    embed.add_field(name="Acceptance", value=f"{q['acRate']:.1f}%")
    if q.get("isPaidOnly"):
        embed.add_field(name="Access", value="\N{LOCK} Premium")
    tags = ", ".join(t["name"] for t in q.get("topicTags", [])[:8])
    if tags:
        embed.add_field(name="Topics (spoiler)", value=f"||{tags}||", inline=False)
    embed.set_footer(text=f"LeetCode daily challenge \N{BULLET} {daily['date']}")
    return embed


def lc_user_embed(data: dict[str, Any]) -> discord.Embed:
    user = data["matchedUser"]
    profile = user.get("profile") or {}
    totals = {row["difficulty"]: row["count"] for row in data.get("allQuestionsCount", [])}
    solved = {row["difficulty"]: row["count"] for row in user["submitStatsGlobal"]["acSubmissionNum"]}

    name = user["username"]
    title = f"{name} ({profile['realName']})" if profile.get("realName") else name
    embed = discord.Embed(
        title=title[:256],
        url=f"https://leetcode.com/u/{name}/",
        description=(f"**{solved.get('All', 0):,}** / {totals.get('All', 0):,} solved\n`{_bar(solved.get('All', 0), totals.get('All', 0))}`"),
        colour=LC_ORANGE,
    )
    for level in ("Easy", "Medium", "Hard"):
        embed.add_field(name=level, value=f"{solved.get(level, 0):,} / {totals.get(level, 0):,}")

    ranking = profile.get("ranking")
    if ranking and ranking > 0:
        embed.add_field(name="Global ranking", value=f"#{ranking:,}")
    calendar = user.get("userCalendar")
    if calendar:
        embed.add_field(name="Streak", value=f"{calendar['streak']} days")
        embed.add_field(name="Active days", value=f"{calendar['totalActiveDays']:,}")
    contest = data.get("userContestRanking")
    if contest:
        embed.add_field(
            name="Contest rating",
            value=(
                f"**{round(float(contest['rating']))}** \N{BULLET} top {float(contest['topPercentage']):.2f}%\n"
                f"{contest['attendedContestsCount']} contests \N{BULLET} rank #{contest['globalRanking']:,}"
            ),
            inline=False,
        )
    avatar = profile.get("userAvatar")
    if avatar and avatar.startswith("http"):
        embed.set_thumbnail(url=avatar)
    return embed


def cf_colour(rating: int | None) -> int:
    if rating is None or rating < 1200:
        return 0x808080
    for limit, colour in ((1400, 0x008000), (1600, 0x03A89E), (1900, 0x0000FF), (2100, 0xAA00AA), (2400, 0xFF8C00)):
        if rating < limit:
            return colour
    return 0xFF0000


def cf_profile_embed(u: dict[str, Any]) -> discord.Embed:
    handle, rating, rank = u["handle"], u.get("rating"), u.get("rank")
    embed = discord.Embed(
        title=f"{rank.title()} {handle}" if rank else handle,
        url=f"https://codeforces.com/profile/{handle}",
        colour=cf_colour(rating),
    )
    real_name = " ".join(filter(None, (u.get("firstName"), u.get("lastName"))))
    if real_name:
        embed.description = discord.utils.escape_markdown(real_name)

    embed.add_field(name="Rating", value=f"**{rating}** ({rank.title()})" if rating is not None else "Unrated")
    peak = u.get("maxRating")
    if peak is not None:
        embed.add_field(name="Peak", value=f"**{peak}** ({u.get('maxRank', '').title()})")
    embed.add_field(name="Contribution", value=str(u.get("contribution", 0)))
    embed.add_field(name="Friend of", value=f"{u.get('friendOfCount', 0):,} users")
    place = ", ".join(filter(None, (u.get("city"), u.get("country"))))
    if place:
        embed.add_field(name="Location", value=discord.utils.escape_markdown(place))
    org = u.get("organization")
    if org:
        embed.add_field(name="Organization", value=discord.utils.escape_markdown(org))
    embed.add_field(name="Registered", value=f"<t:{u['registrationTimeSeconds']}:D>")
    embed.add_field(name="Last online", value=f"<t:{u['lastOnlineTimeSeconds']}:R>")

    photo = u.get("titlePhoto") or u.get("avatar")
    if photo:
        embed.set_thumbnail(url=f"https:{photo}" if photo.startswith("//") else photo)
    embed.set_footer(text="Use `cf rating` for rating history")
    return embed


def cf_rating_embed(history: list[dict[str, Any]]) -> discord.Embed:
    handle = history[0]["handle"]
    current = history[-1]["newRating"]
    deltas = [h["newRating"] - h["oldRating"] for h in history if h["oldRating"] > 0]  # first contest has oldRating 0

    embed = discord.Embed(
        title=f"{handle} \N{BULLET} rating history",
        url=f"https://codeforces.com/profile/{handle}",
        colour=cf_colour(current),
    )
    embed.add_field(name="Current", value=f"**{current}**")
    embed.add_field(name="Peak", value=f"**{max(h['newRating'] for h in history)}**")
    embed.add_field(name="Contests", value=str(len(history)))
    embed.add_field(name="Best rank", value=f"#{min(h['rank'] for h in history):,}")
    if deltas:
        embed.add_field(name="Biggest gain", value=f"{max(deltas):+d}")
        embed.add_field(name="Biggest drop", value=f"{min(deltas):+d}")

    lines = []
    for h in reversed(history[-5:]):
        delta = h["newRating"] - h["oldRating"] if h["oldRating"] > 0 else None
        arrow = (
            "\N{BULLET}" if delta in (None, 0) else ("\N{UP-POINTING SMALL RED TRIANGLE}" if delta > 0 else "\N{DOWN-POINTING SMALL RED TRIANGLE}")
        )
        change = f"**{delta:+d}** \N{RIGHTWARDS ARROW} {h['newRating']}" if delta is not None else f"debut \N{RIGHTWARDS ARROW} **{h['newRating']}**"
        name = re.sub(r"[\[\]]", "", discord.utils.escape_markdown(h["contestName"]))[:38]
        lines.append(f"{arrow} {change} \N{BULLET} #{h['rank']:,} \N{BULLET} [{name}](https://codeforces.com/contest/{h['contestId']})")
    embed.add_field(name="Recent contests", value="\n".join(lines), inline=False)
    return embed


def render_rating_graph(history: list[dict[str, Any]]) -> bytes:
    """Draw a Codeforces-style rating graph (coloured rank bands) and return PNG bytes."""
    width, height = 900, 420
    left, right, top, bottom = 64, 24, 20, 40
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()

    ratings = [h["newRating"] for h in history]
    times = [h["ratingUpdateTimeSeconds"] for h in history]
    lo = max(0, math.floor((min(ratings) - 100) / 100) * 100)
    hi = math.ceil((max(ratings) + 100) / 100) * 100
    t0, t1 = min(times), max(times)
    plot_w, plot_h = width - left - right, height - top - bottom
    inner = 14  # keep first/last point away from the frame

    def x_of(t: float) -> float:
        if t1 == t0:
            return left + plot_w / 2
        return left + inner + (t - t0) / (t1 - t0) * (plot_w - 2 * inner)

    def y_of(r: float) -> float:
        return top + (hi - r) / (hi - lo) * plot_h

    def text(xy: tuple[float, float], value: str, *, right_align: bool = False) -> None:
        x, y = xy
        if right_align:
            x -= draw.textlength(value, font=font)
        draw.text((x, y), value, font=font, fill=(55, 55, 55))

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    for band_lo, band_hi, colour in CF_BANDS:
        a, b = max(band_lo, lo), min(band_hi, hi)
        if a < b:
            draw.rectangle([left, y_of(b), left + plot_w, y_of(a)], fill=colour)
    for value in sorted({lo, hi, *(edge for lo_, hi_, _ in CF_BANDS for edge in (lo_, hi_) if lo < edge < hi)}):
        y = y_of(value)
        draw.line([(left, y), (left + plot_w, y)], fill="white", width=1)
        text((left - 8, y - 8), str(value), right_align=True)

    first, last = datetime.fromtimestamp(t0, UTC), datetime.fromtimestamp(t1, UTC)
    for year in range(first.year + 1, last.year + 1):
        x = x_of(datetime(year, 1, 1, tzinfo=UTC).timestamp())
        draw.line([(x, top), (x, top + plot_h)], fill="white", width=1)
        if left + 90 < x < left + plot_w - 90:  # keep clear of the first/last date labels
            text((x - 14, top + plot_h + 8), str(year))
    text((left, top + plot_h + 8), first.strftime("%b %Y"))
    if t1 != t0:
        text((left + plot_w, top + plot_h + 8), last.strftime("%b %Y"), right_align=True)

    points = [(x_of(t), y_of(r)) for t, r in zip(times, ratings, strict=True)]
    if len(points) > 1:
        draw.line(points, fill=(70, 70, 70), width=2)
    for x, y in points:
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill="white", outline=(70, 70, 70))
    px, py = points[ratings.index(max(ratings))]
    draw.ellipse([px - 6, py - 6, px + 6, py + 6], outline=(200, 0, 0), width=2)
    draw.rectangle([left, top, left + plot_w, top + plot_h], outline=(120, 120, 120))

    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


class CodingStats(commands.Cog):
    """LeetCode and Codeforces lookups."""

    help_emoji = "\N{TROPHY}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._lc_cache = TTLCache(600)
        self._cf_cache = TTLCache(300)
        self._cf_lock = asyncio.Lock()
        self._cf_last = 0.0

    async def _lc_query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Referer": "https://leetcode.com", "User-Agent": USER_AGENT}
        try:
            async with self.bot.http_session.post(
                LC_URL, json={"query": query, "variables": variables or {}}, headers=headers, timeout=HTTP_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    msg = f"LeetCode returned HTTP {resp.status}."
                    raise LookupFailed(msg)
                payload = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as exc:
            msg = "I couldn't reach LeetCode right now."
            raise LookupFailed(msg) from exc
        data = payload.get("data")
        if data is None:
            msg = "LeetCode returned an error."
            raise LookupFailed(msg)
        return data

    async def _lc_daily(self) -> dict[str, Any]:
        hit = self._lc_cache.get("daily")
        if hit is not None:
            return hit
        data = await self._lc_query(LC_DAILY_QUERY)
        daily = data.get("activeDailyCodingChallengeQuestion")
        if not daily:
            msg = "LeetCode didn't return today's challenge."
            raise LookupFailed(msg)
        self._lc_cache.set("daily", daily, ttl=min(900, _seconds_until_utc_midnight()))  # the daily rolls over at 00:00 UTC
        return daily

    async def _lc_user(self, username: str) -> dict[str, Any]:
        if not LC_USER_RE.match(username):
            msg = "That isn't a valid LeetCode username."
            raise LookupFailed(msg)
        key = ("user", username.lower())
        hit = self._lc_cache.get(key)
        if hit is not None:
            return hit
        data = await self._lc_query(LC_USER_QUERY, {"username": username})
        if not data.get("matchedUser"):
            msg = f"No LeetCode user named `{username}`."
            raise LookupFailed(msg)
        self._lc_cache.set(key, data)
        return data

    @commands.group(name="leetcode", aliases=["lc"], invoke_without_command=True)
    async def leetcode(self, ctx: commands.Context) -> None:
        """LeetCode daily challenge and user stats."""
        await ctx.send_help(ctx.command)

    @leetcode.command(name="daily", aliases=["today"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leetcode_daily(self, ctx: commands.Context) -> None:
        """Show today's LeetCode daily challenge."""
        async with _reporting(ctx), ctx.typing():
            daily = await self._lc_daily()
            await ctx.send(embed=lc_daily_embed(daily))

    @leetcode.command(name="user", aliases=["stats", "profile"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def leetcode_user(self, ctx: commands.Context, username: str = commands.parameter(description="LeetCode username")) -> None:
        """Show a LeetCode user's solved counts, streak and contest rating."""
        async with _reporting(ctx), ctx.typing():
            data = await self._lc_user(username)
            await ctx.send(embed=lc_user_embed(data), allowed_mentions=discord.AllowedMentions.none())

    async def _cf_call(self, method: str, params: dict[str, str], handle: str) -> Any:
        """One Codeforces API call, serialised so we never exceed 1 request / 2 seconds."""
        async with self._cf_lock:
            loop = asyncio.get_running_loop()
            wait = CF_MIN_INTERVAL - (loop.time() - self._cf_last)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                async with self.bot.http_session.get(
                    f"{CF_API}/{method}", params=params, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT
                ) as resp:
                    payload = await resp.json(content_type=None)  # error replies are JSON too (HTTP 400)
            except (TimeoutError, aiohttp.ClientError, ValueError) as exc:
                msg = "I couldn't reach Codeforces right now."
                raise LookupFailed(msg) from exc
            finally:
                self._cf_last = loop.time()

        if payload.get("status") != "OK":
            comment = str(payload.get("comment", ""))
            if "not found" in comment.lower():
                msg = f"No Codeforces user with the handle `{handle}`."
            elif "limit exceeded" in comment.lower():
                msg = "Codeforces is rate limiting me; try again in a few seconds."
            else:
                msg = "Codeforces returned an error."
            raise LookupFailed(msg)
        return payload["result"]

    @staticmethod
    def _cf_check_handle(handle: str) -> None:
        if not CF_HANDLE_RE.match(handle):
            msg = "That isn't a valid Codeforces handle."
            raise LookupFailed(msg)

    async def _cf_user(self, handle: str) -> dict[str, Any]:
        self._cf_check_handle(handle)
        key = ("info", handle.lower())
        hit = self._cf_cache.get(key)
        if hit is not None:
            return hit
        user = (await self._cf_call("user.info", {"handles": handle}, handle))[0]
        self._cf_cache.set(key, user)
        return user

    async def _cf_history(self, handle: str) -> list[dict[str, Any]]:
        self._cf_check_handle(handle)
        key = ("rating", handle.lower())
        hit = self._cf_cache.get(key)
        if hit is not None:
            return hit
        history = await self._cf_call("user.rating", {"handle": handle}, handle)
        if not history:
            msg = f"`{handle}` hasn't taken part in any rated contests yet."
            raise LookupFailed(msg)
        self._cf_cache.set(key, history)
        return history

    @commands.group(name="codeforces", aliases=["cf"], invoke_without_command=True)
    async def codeforces(self, ctx: commands.Context) -> None:
        """Codeforces profiles and rating history."""
        await ctx.send_help(ctx.command)

    @codeforces.command(name="user", aliases=["profile", "info"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def codeforces_user(self, ctx: commands.Context, handle: str = commands.parameter(description="Codeforces handle")) -> None:
        """Show a Codeforces profile: rating, rank, peak and activity."""
        async with _reporting(ctx), ctx.typing():
            user = await self._cf_user(handle)
            await ctx.send(embed=cf_profile_embed(user), allowed_mentions=discord.AllowedMentions.none())

    @codeforces.command(name="rating", aliases=["graph", "history"])
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def codeforces_rating(self, ctx: commands.Context, handle: str = commands.parameter(description="Codeforces handle")) -> None:
        """Show rating history with a graph."""
        async with _reporting(ctx), ctx.typing():
            history = await self._cf_history(handle)
            embed = cf_rating_embed(history)
            try:
                png = await asyncio.to_thread(render_rating_graph, history)
            except Exception:
                _log.exception("Rating graph failed for %s", handle)
                await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                return
            embed.set_image(url="attachment://rating.png")
            await ctx.send(embed=embed, file=discord.File(io.BytesIO(png), "rating.png"), allowed_mentions=discord.AllowedMentions.none())
