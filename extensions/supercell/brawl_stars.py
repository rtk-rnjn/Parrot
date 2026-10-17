from __future__ import annotations

import asyncio
import difflib
import re
from typing import TYPE_CHECKING, Annotated, Literal

import discord
from discord.ext import commands

from core.utils.formats import safe_text
from core.utils.views import NoticeLayout

from . import render
from .api import BRAWL_STARS, NotFound, SupercellError, Tag, enc, parse_time
from .base import Page
from .base import Supercell as SupercellCog

if TYPE_CHECKING:
    from core import Bot

    from .base import Loader

FOOTER = "Brawl Stars \N{BULLET} Supercell API"
MAX_POWER = 11
CDN = "https://cdn.brawlify.com"

ROLES = {"member": "Member", "senior": "Senior", "vicePresident": "Vice president", "president": "President"}
CLUB_TYPES = {"open": "Open", "inviteOnly": "Invite only", "closed": "Closed"}
RESULTS = {
    "victory": "\N{LARGE GREEN CIRCLE}",
    "defeat": "\N{LARGE RED CIRCLE}",
    "draw": "\N{MEDIUM WHITE CIRCLE}",
}
COUNTRY_RE = re.compile(r"global|[a-z]{2}")


def _num(data: dict, key: str) -> str:
    return f"{data.get(key) or 0:,}"


def _title(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", value).title()


def _brawler_icon(brawler_id: int) -> str:
    return f"{CDN}/brawlers/borderless/{brawler_id}.png"


class BrawlStars(SupercellCog, command_attrs={"hidden": True}):
    game = BRAWL_STARS
    group_name = "bs"

    @commands.group(name="bs", aliases=["brawlstars", "brawl"], invoke_without_command=True)
    async def bs(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str, Tag] = commands.parameter(description="Player tag, e.g. #2PP.", default=None),
        *,
        user: discord.User = commands.parameter(description="Use this member's linked account.", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Show a Brawl Stars player profile."""
        async with ctx.typing():
            tag = await self.resolve_tag(ctx, tag, user)
            player = await self.api.get(f"/players/{enc(tag)}", ttl=120)
            await self.show(ctx, self._profile_tabs(player))

    @bs.command(name="link")
    async def link(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str, Tag] = commands.parameter(description="Player tag, e.g. #2PP.", default=None),
    ) -> None:
        """Link your Brawl Stars account."""
        async with ctx.typing():
            await self.link_account(ctx, tag)

    @bs.command(name="unlink")
    async def unlink(self, ctx: commands.Context[Bot]) -> None:
        """Unlink your Brawl Stars account."""
        await self.unlink_account(ctx)

    @bs.command(name="club")
    async def club(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str, Tag] = commands.parameter(description="Club tag, e.g. #2PP.", default=None),
        user: discord.User = commands.parameter(description="Show the club of this member's linked account.", default=lambda ctx: ctx.author),  # noqa: B008
    ) -> None:
        """Show a club, by tag or via a player's linked account."""
        async with ctx.typing():
            club_tag = tag or await self._club_tag_for(ctx, user)
            await self.show(ctx, self._club_tabs(club_tag))

    @bs.command(name="brawler")
    async def brawler(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="Brawler name, e.g. Shelly."),
    ) -> None:
        """Look up a brawler's gadgets and star powers."""
        async with ctx.typing():
            brawlers = await self._brawlers()
            by_name = {b["name"].casefold(): b for b in brawlers}
            needle = name.casefold()
            match = by_name.get(needle) or next((b for key, b in by_name.items() if needle in key), None)
            if match is None and (close := difflib.get_close_matches(needle, by_name, n=1, cutoff=0.5)):
                match = by_name[close[0]]
            if match is None:
                message = f"No brawler called `{name}`."
                raise NotFound(message)

        def names(entries: list[dict]) -> str:
            return ", ".join(e["name"].title() for e in entries) or "-"

        body = "\n".join(
            [
                f"**Gadgets** {names(match.get('gadgets', []))}",
                f"**Star powers** {names(match.get('starPowers', []))}",
            ]
        )
        view = NoticeLayout(body, title=match["name"].title(), colour=self.game.colour, thumbnail=_brawler_icon(match["id"]))
        await ctx.reply(view=view)

    @bs.command(name="events", aliases=["rotation"])
    async def events(self, ctx: commands.Context[Bot]) -> None:
        """Show the current event rotation."""
        async with ctx.typing():
            rotation = await self.api.get("/events/rotation", ttl=300)

        lines = ["### Event rotation"]
        for slot in rotation:
            event = slot.get("event") or {}
            ends = parse_time(slot.get("endTime"))
            lines.append(
                f"**{_title(event.get('mode', '?'))}** \N{MIDDLE DOT} {event.get('map', '?')}"
                + (f" \N{MIDDLE DOT} ends {discord.utils.format_dt(ends, 'R')}" if ends else "")
            )
        if len(lines) == 1:
            message = "No events are rotating right now."
            raise NotFound(message)
        await ctx.reply(view=NoticeLayout.info("\n".join(lines[1:]), title="Event rotation"))

    @bs.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(
        self,
        ctx: commands.Context[Bot],
        kind: Literal["players", "clubs"] = commands.parameter(description="Show top players or clubs.", default="players"),
        country: str = commands.parameter(description="Two-letter country code, e.g. IN, or global.", default="global"),
    ) -> None:
        """Show trophy rankings."""
        code = country.strip().lower()
        if not COUNTRY_RE.fullmatch(code):
            message = "Use `global` or a two-letter country code such as `IN` or `US`."
            raise SupercellError(message)

        async with ctx.typing():
            data = await self.api.get(f"/rankings/{code}/{kind}", params={"limit": 100}, ttl=300)

        lines: list[str] = []
        for item in data.get("items", []):
            rank = item.get("rank", len(lines) + 1)
            extra = (
                f" \N{MIDDLE DOT} {safe_text((item.get('club') or {}).get('name', ''))}".rstrip(" \N{MIDDLE DOT}")
                if kind == "players"
                else f" \N{MIDDLE DOT} {item.get('memberCount', 0)}/30"
            )
            lines.append(f"`{rank:>3}` **{safe_text(item.get('name', '?'))}** \N{MIDDLE DOT} {item.get('trophies', 0):,}{extra}")

        await self.paginate(ctx, f"{code.upper()} \N{MIDDLE DOT} {kind.title()}", lines)

    async def _brawlers(self) -> list[dict]:
        data = await self.api.get("/brawlers", ttl=21_600)
        return data.get("items", [])

    async def _club_tag_for(self, ctx: commands.Context[Bot], user: discord.User | None) -> str:
        player_tag = await self.resolve_tag(ctx, None, user)
        player = await self.api.get(f"/players/{enc(player_tag)}", ttl=120)
        if not (club := player.get("club")) or not club.get("tag"):
            message = f"**{discord.utils.escape_markdown(player['name'])}** isn't in a club."
            raise NotFound(message)
        return club["tag"]

    def _profile_tabs(self, player: dict) -> dict[str, Loader]:
        tag = player["tag"]
        tabs: dict[str, Loader] = {
            "Overview": lambda: self._overview(player),
            "Brawlers": lambda: self._brawlers_page(player),
            "Battles": lambda: self._battles(tag),
        }
        if (club := player.get("club")) and club.get("tag"):
            tabs["Club"] = lambda: self._club_overview(club["tag"])
        return tabs

    def _club_tabs(self, tag: str) -> dict[str, Loader]:
        return {
            "Overview": lambda: self._club_overview(tag),
            "Members": lambda: self._members(tag),
        }

    async def _overview(self, player: dict) -> Page:
        brawlers = sorted(player.get("brawlers", []), key=lambda b: b.get("trophies", 0), reverse=True)
        icon_id = (player.get("icon") or {}).get("id")
        portrait_url = f"{CDN}/profile-icons/regular/{icon_id}.png" if icon_id else None
        portrait, *strip = await self.images.many([portrait_url, *(_brawler_icon(b["id"]) for b in brawlers[:8])])

        count = len(brawlers)
        total = sum(b.get("trophies", 0) for b in brawlers)
        stats = [
            ("Trophies", _num(player, "trophies")),
            ("Highest", _num(player, "highestTrophies")),
            ("3v3 wins", _num(player, "3vs3Victories")),
            ("Solo wins", _num(player, "soloVictories")),
            ("Duo wins", _num(player, "duoVictories")),
            ("Brawlers", str(count)),
            ("Max power", str(sum(1 for b in brawlers if b.get("power", 0) >= MAX_POWER))),
            ("Rank 30+", str(sum(1 for b in brawlers if b.get("rank", 0) >= 30))),
            ("Top brawler", brawlers[0]["name"].title() if brawlers else "-"),
            ("Avg / brawler", f"{total // count:,}" if count else "-"),
            ("XP points", _num(player, "expPoints")),
            ("Club", (player.get("club") or {}).get("name") or "None"),
        ]
        club = player.get("club") or {}
        line = club["name"] if club.get("name") else "No club"

        image = await asyncio.to_thread(
            render.profile_card,
            render.BRAWL_STARS,
            name=player["name"],
            tag=player["tag"],
            level=f"Lv {player.get('expLevel', 1)}",
            line=line,
            portrait=portrait,
            stats=stats,
            strip=strip if any(strip) else (),
            strip_size=(84, 84),
            footer=FOOTER,
        )
        return Page(text=await self.link_text(player["tag"]), image=image)

    async def _brawlers_page(self, player: dict) -> Page:
        brawlers = sorted(player.get("brawlers", []), key=lambda b: b.get("trophies", 0), reverse=True)[:30]
        if not brawlers:
            return Page(text="No brawlers unlocked yet.")

        bars = [
            render.Bar(
                f"{b['name'].title()} \N{MIDDLE DOT} R{b.get('rank', 1)} \N{MIDDLE DOT} {b.get('trophies', 0):,}", b.get("power", 1), MAX_POWER
            )
            for b in brawlers
        ]
        image = await asyncio.to_thread(
            render.bars_card,
            render.BRAWL_STARS,
            title=f"{player['name']}'s brawlers",
            subtitle=f"Top {len(bars)} by trophies \N{BULLET} bar shows power level",
            bars=bars,
            footer=FOOTER,
        )
        return Page(image=image)

    async def _battles(self, tag: str) -> Page:
        data = await self.api.get(f"/players/{enc(tag)}/battlelog", ttl=60)
        entries = data.get("items", [])
        if not entries:
            return Page(text="No recent battles.")

        wins = losses = draws = 0
        lines: list[str] = []
        for index, entry in enumerate(entries[:25]):
            battle = entry.get("battle") or {}
            result = battle.get("result")
            if result == "victory":
                wins += 1
            elif result == "defeat":
                losses += 1
            elif result == "draw":
                draws += 1

            if index >= 10:
                continue

            participants = [p for team in battle.get("teams", []) for p in team] or battle.get("players", [])
            mine = next((p for p in participants if p.get("tag") == tag), None)
            brawler = ((mine or {}).get("brawler") or {}).get("name", "?").title()
            event = entry.get("event") or {}
            mode = _title(battle.get("mode") or event.get("mode", "?"))

            if result:
                outcome = f"{RESULTS.get(result, '\N{MEDIUM WHITE CIRCLE}')} **{result.title()}**"
            elif "rank" in battle:
                outcome = f"\N{TROPHY} **Rank {battle['rank']}**"
            else:
                outcome = "\N{MEDIUM WHITE CIRCLE}"

            change = battle.get("trophyChange")
            when = parse_time(entry.get("battleTime"))
            lines.append(
                f"{outcome} \N{MIDDLE DOT} {mode} \N{MIDDLE DOT} {event.get('map') or '-'} \N{MIDDLE DOT} {brawler}"
                + (f" \N{MIDDLE DOT} {change:+d}" if change is not None else "")
                + (f" \N{MIDDLE DOT} {discord.utils.format_dt(when, 'R')}" if when else "")
            )

        header = f"### Recent battles\nLast {min(len(entries), 25)}: **{wins}W {losses}L {draws}D**"
        return Page(text="\n".join([header, "", *lines]))

    async def _club_overview(self, tag: str) -> Page:
        club = await self.api.get(f"/clubs/{enc(tag)}", ttl=300)
        members = club.get("members", [])
        president = next((m["name"] for m in members if m.get("role") == "president"), "-")
        trophies = club.get("trophies", 0)
        portrait = await self.images.get(f"{CDN}/club-badges/regular/{club['badgeId']}.png" if club.get("badgeId") else None)

        stats = [
            ("Trophies", f"{trophies:,}"),
            ("Required", _num(club, "requiredTrophies")),
            ("Members", f"{len(members)}/30"),
            ("Type", CLUB_TYPES.get(club.get("type", ""), "-")),
            ("President", president),
            ("Avg / member", f"{trophies // len(members):,}" if members else "-"),
            ("Top member", f"{max(m.get('trophies', 0) for m in members):,}" if members else "-"),
            ("Badge", str(club.get("badgeId", "-"))),
        ]
        image = await asyncio.to_thread(
            render.profile_card,
            render.BRAWL_STARS,
            name=club["name"],
            tag=club["tag"],
            level=f"{len(members)}/30",
            line=(club.get("description") or "").replace("\n", " ") or "No description",
            portrait=portrait,
            stats=stats,
            footer=FOOTER,
        )
        return Page(image=image)

    async def _members(self, tag: str) -> Page:
        data = await self.api.get(f"/clubs/{enc(tag)}/members", ttl=300)
        members = data.get("items", [])
        lines = [
            f"`{rank:>2}` **{safe_text(m['name'], 22)}** \N{MIDDLE DOT} {ROLES.get(m.get('role', ''), '-')} \N{MIDDLE DOT} \N{TROPHY} {m.get('trophies', 0):,}"
            for rank, m in enumerate(members, 1)
        ]
        return Page(text="\n".join(["### Members", *lines]) if lines else "No members found.")
