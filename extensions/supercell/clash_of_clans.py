from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Annotated, Literal

import discord
from discord.ext import commands

from core.utils.formats import safe_text
from core.utils.views import NoticeLayout

from . import render
from .api import CLASH_OF_CLANS, Forbidden, NotFound, SupercellError, Tag, enc, parse_time
from .base import Page
from .base import Supercell as SupercellCog

if TYPE_CHECKING:
    from core import Bot

    from .base import Loader

FOOTER = "Clash of Clans \N{BULLET} Supercell API"

ROLES = {"member": "Member", "admin": "Elder", "coLeader": "Co-leader", "leader": "Leader"}
CLAN_TYPES = {"open": "Open", "inviteOnly": "Invite only", "closed": "Closed"}
WAR_RESULTS = {"win": "\N{LARGE GREEN CIRCLE} Win", "lose": "\N{LARGE RED CIRCLE} Loss", "tie": "\N{MEDIUM WHITE CIRCLE} Tie"}
BOARDS = {
    "players": ("players", "trophies"),
    "clans": ("clans", "clanPoints"),
    "builder-players": ("players-builder-base", "builderBaseTrophies"),
    "builder-clans": ("clans-builder-base", "clanBuilderBasePoints"),
}


def _num(data: dict, key: str) -> str:
    return f"{data.get(key) or 0:,}"


def _home(entries: list[dict]) -> list[render.Bar]:
    return [render.Bar(e["name"], e["level"], e["maxLevel"]) for e in entries if e.get("village") == "home"]


def _league(player: dict) -> dict:
    return player.get("leagueTier") or player.get("league") or {}


class ClashOfClans(SupercellCog, command_attrs={"hidden": True}):
    game = CLASH_OF_CLANS
    group_name = "coc"

    @commands.group(name="coc", aliases=["clashofclans"], invoke_without_command=True)
    async def coc(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str, Tag] | None = None,
        user: discord.User = commands.parameter(default=lambda ctx: ctx.author, description="Show the linked account of this member."),  # noqa: B008
    ) -> None:
        """Show a Clash of Clans player profile."""
        async with ctx.typing():
            tag = await self.resolve_tag(ctx, tag, user)
            player = await self.api.get(f"/players/{enc(tag)}", ttl=120)
            await self.show(ctx, self._profile_tabs(player))

    @coc.command(name="link")
    async def link(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str, Tag],
        token: str | None = commands.parameter(default=None, description="Add your in-game API token to verify ownership."),
    ) -> None:
        """Link your account. Add the in-game API token (Settings > More Settings) to verify ownership."""
        verified = False
        if token:
            if ctx.interaction is None:
                with contextlib.suppress(discord.HTTPException):
                    await ctx.message.delete()
            result = await self.api.post(f"/players/{enc(tag)}/verifytoken", {"token": token.strip()})
            if result.get("status") != "ok":
                message = "That API token doesn't belong to this account."
                raise SupercellError(message)
            verified = True

        async with ctx.typing():
            await self.link_account(ctx, tag, verified=verified, ephemeral=bool(token))

    @coc.command(name="unlink")
    async def unlink(self, ctx: commands.Context[Bot]) -> None:
        """Unlink your Clash of Clans account."""
        await self.unlink_account(ctx)

    @coc.command(name="clan")
    async def clan(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str, Tag] | None = None,
        user: discord.User = commands.parameter(default=lambda ctx: ctx.author, description="Show the linked account of this member."),  # noqa: B008
    ) -> None:
        """Show a clan, by tag or via a player's linked account."""
        async with ctx.typing():
            clan_tag = await self.clan_tag_for(ctx, tag, user)
            await self.show(ctx, self._clan_tabs(clan_tag))

    @coc.command(name="clansearch", aliases=["searchclan"])
    async def clansearch(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The name of the clan to search for."),
    ) -> None:
        """Search for a clan by name."""
        async with ctx.typing():
            clan_tag = await self.search_clans(ctx, name)
            await self.show(ctx, self._clan_tabs(clan_tag))

    @coc.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(
        self,
        ctx: commands.Context[Bot],
        kind: Literal["players", "clans", "builder-players", "builder-clans"] = commands.parameter(
            description="The type of leaderboard to show.", default="players"
        ),
        *,
        location: str = commands.parameter(description="The location to show rankings for.", default="global"),
    ) -> None:
        """Show location rankings."""
        async with ctx.typing():
            location_id, location_name = await self.resolve_location(location)
            path, key = BOARDS[kind]
            data = await self.api.get(f"/locations/{location_id}/rankings/{path}", params={"limit": 100}, ttl=300)

        lines: list[str] = []
        for item in data.get("items", []):
            clan = (item.get("clan") or {}).get("name")
            suffix = f" \N{MIDDLE DOT} {safe_text(clan)}" if clan else f" \N{MIDDLE DOT} {item.get('members', 0)}/50" if "members" in item else ""
            lines.append(f"{item.get('rank', len(lines) + 1)}. **{safe_text(item.get('name', '?'))}** \N{MIDDLE DOT} {item.get(key, 0):,}{suffix}")

        await self.paginate(ctx, f"{location_name} \N{MIDDLE DOT} {kind.replace('-', ' ').title()}", lines)

    @coc.command(name="goldpass")
    async def goldpass(self, ctx: commands.Context[Bot]) -> None:
        """Show the current Gold Pass season."""
        async with ctx.typing():
            season = await self.api.get("/goldpass/seasons/current", ttl=3600)

        start, end = parse_time(season.get("startTime")), parse_time(season.get("endTime"))
        if start is None or end is None:
            message = "Supercell didn't return Gold Pass dates."
            raise NotFound(message)
        body = f"Started {discord.utils.format_dt(start, 'R')}\nEnds {discord.utils.format_dt(end, 'F')} ({discord.utils.format_dt(end, 'R')})"
        await ctx.reply(view=NoticeLayout.info(body, title="Gold Pass season"))

    def _profile_tabs(self, player: dict) -> dict[str, Loader]:
        tabs: dict[str, Loader] = {
            "Overview": lambda: self._overview(player),
            "Heroes": lambda: self._heroes(player),
            "Army": lambda: self._army(player),
        }
        if clan := player.get("clan"):
            tabs["Clan"] = lambda: self._clan_overview(clan["tag"])
        return tabs

    def _clan_tabs(self, tag: str) -> dict[str, Loader]:
        return {
            "Overview": lambda: self._clan_overview(tag),
            "Members": lambda: self._members(tag),
            "War": lambda: self._war(tag),
            "War Log": lambda: self._war_log(tag),
        }

    async def _overview(self, player: dict) -> Page:
        clan = player.get("clan")
        labels = [(label.get("iconUrls") or {}).get("medium") for label in player.get("labels", [])][:6]
        portrait, *strip = await self.images.many([(_league(player).get("iconUrls") or {}).get("medium"), *labels])

        stats = [
            ("Trophies", _num(player, "trophies")),
            ("Best", _num(player, "bestTrophies")),
            ("War stars", _num(player, "warStars")),
            ("Attack wins", _num(player, "attackWins")),
            ("Defense wins", _num(player, "defenseWins")),
            ("Donated", _num(player, "donations")),
            ("Received", _num(player, "donationsReceived")),
            ("Capital gold", _num(player, "clanCapitalContributions")),
            ("XP level", str(player.get("expLevel", 1))),
            ("Builder hall", str(player.get("builderHallLevel", "-"))),
            ("Builder trophies", _num(player, "builderBaseTrophies")),
            ("League", _league(player).get("name", "Unranked")),
        ]
        if clan:
            line = clan["name"]
            if role := ROLES.get(player.get("role", "")):
                line += f" \N{BULLET} {role}"
        else:
            line = "No clan"

        image = await asyncio.to_thread(
            render.profile_card,
            render.CLASH_OF_CLANS,
            name=player["name"],
            tag=player["tag"],
            level=f"TH {player.get('townHallLevel', '?')}",
            line=line,
            portrait=portrait,
            stats=stats,
            strip=strip if any(strip) else (),
            strip_size=(72, 72),
            footer=FOOTER,
        )
        return Page(text=await self.link_text(player["tag"]), image=image)

    async def _heroes(self, player: dict) -> Page:
        bars = [*_home(player.get("heroes", [])), *_home(player.get("heroEquipment", []))]
        if not bars:
            return Page(text="No heroes unlocked yet.")

        image = await asyncio.to_thread(
            render.bars_card,
            render.CLASH_OF_CLANS,
            title=f"{player['name']}'s heroes",
            subtitle=f"Town Hall {player.get('townHallLevel', '?')} \N{BULLET} heroes and equipment",
            bars=bars,
            footer=FOOTER,
        )
        return Page(image=image)

    async def _army(self, player: dict) -> Page:
        bars = [*_home(player.get("troops", [])), *_home(player.get("spells", []))]
        if not bars:
            return Page(text="No troops or spells yet.")

        image = await asyncio.to_thread(
            render.bars_card,
            render.CLASH_OF_CLANS,
            title=f"{player['name']}'s army",
            subtitle=f"Town Hall {player.get('townHallLevel', '?')} \N{BULLET} troops, siege and spells",
            bars=bars,
            footer=FOOTER,
        )
        return Page(image=image)

    async def _clan_overview(self, tag: str) -> Page:
        clan = await self.api.get(f"/clans/{enc(tag)}", ttl=300)
        portrait = await self.images.get((clan.get("badgeUrls") or {}).get("large"))
        stats = [
            ("Members", f"{clan.get('members', 0)}/50"),
            ("Clan points", _num(clan, "clanPoints")),
            ("War wins", _num(clan, "warWins")),
            ("Win streak", _num(clan, "warWinStreak")),
            ("Capital points", _num(clan, "clanCapitalPoints")),
            ("Required TH", str(clan.get("requiredTownhallLevel", "-"))),
            ("Required", _num(clan, "requiredTrophies")),
            ("War frequency", str(clan.get("warFrequency", "-")).title()),
            ("Type", CLAN_TYPES.get(clan.get("type", ""), "-")),
            ("War league", (clan.get("warLeague") or {}).get("name", "-")),
            ("Capital league", (clan.get("capitalLeague") or {}).get("name", "-")),
            ("Location", (clan.get("location") or {}).get("name", "-")),
        ]
        image = await asyncio.to_thread(
            render.profile_card,
            render.CLASH_OF_CLANS,
            name=clan["name"],
            tag=clan["tag"],
            level=f"Lv {clan.get('clanLevel', 1)}",
            line=(clan.get("description") or "").replace("\n", " ") or "No description",
            portrait=portrait,
            stats=stats,
            footer=FOOTER,
        )
        return Page(image=image)

    async def _members(self, tag: str) -> Page:
        data = await self.api.get(f"/clans/{enc(tag)}/members", ttl=300)
        members = sorted(data.get("items", []), key=lambda m: m.get("clanRank", 99))
        lines = [
            f"`{m.get('clanRank', '?'):>2}` **{safe_text(m['name'], 22)}** \N{MIDDLE DOT} {ROLES.get(m.get('role', ''), '-')}"
            f" \N{MIDDLE DOT} \N{TROPHY} {m.get('trophies', 0):,} \N{MIDDLE DOT} \N{WRAPPED PRESENT} {m.get('donations', 0)}"
            for m in members
        ]
        return Page(text="\n".join(["### Members", *lines]) if lines else "No members found.")

    async def _war(self, tag: str) -> Page:
        try:
            war = await self.api.get(f"/clans/{enc(tag)}/currentwar", ttl=60)
        except Forbidden:
            return Page(text="This clan's war log is private, so the current war can't be shown.")

        if war.get("state") in {None, "notInWar"}:
            return await self._league_group(tag)

        clan, opponent = war["clan"], war["opponent"]
        attacks = war.get("teamSize", 0) * war.get("attacksPerMember", 2)
        state = war["state"]
        target = parse_time(war.get("startTime" if state == "preparation" else "endTime"))
        label = {"preparation": "Battle day starts", "inWar": "Ends", "warEnded": "Ended"}.get(state, state)

        lines = [
            f"### {safe_text(clan['name'])} vs {safe_text(opponent['name'])}",
            f"**{clan.get('stars', 0)}** \N{WHITE MEDIUM STAR} - \N{WHITE MEDIUM STAR} **{opponent.get('stars', 0)}**",
            f"Destruction: {clan.get('destructionPercentage', 0):.1f}% - {opponent.get('destructionPercentage', 0):.1f}%",
            f"Attacks: {clan.get('attacks', 0)}/{attacks} - {opponent.get('attacks', 0)}/{attacks}",
        ]
        if target:
            lines.append(f"{label} {discord.utils.format_dt(target, 'R')}")
        return Page(text="\n".join(lines))

    async def _league_group(self, tag: str) -> Page:
        try:
            group = await self.api.get(f"/clans/{enc(tag)}/currentwar/leaguegroup", ttl=300)
        except NotFound, Forbidden:
            return Page(text="This clan isn't in a war right now.")

        names = ", ".join(safe_text(c["name"], 20) for c in group.get("clans", []))
        return Page(text=f"### Clan War League\nSeason **{group.get('season', '?')}** \N{MIDDLE DOT} {group.get('state', '-')}\n{names}")

    async def _war_log(self, tag: str) -> Page:
        try:
            data = await self.api.get(f"/clans/{enc(tag)}/warlog", params={"limit": 10}, ttl=600)
        except Forbidden:
            return Page(text="This clan's war log is private.")

        lines = ["### War log"]
        for war in data.get("items", []):
            if not (result := war.get("result")):
                continue
            clan, opponent = war.get("clan") or {}, war.get("opponent") or {}
            ended = parse_time(war.get("endTime"))
            lines.append(
                f"{WAR_RESULTS.get(result, result)} \N{MIDDLE DOT} {clan.get('stars', 0)}\N{WHITE MEDIUM STAR}"
                f" - {opponent.get('stars', 0)}\N{WHITE MEDIUM STAR} vs {safe_text(opponent.get('name', '?'), 22)}"
                + (f" \N{MIDDLE DOT} {discord.utils.format_dt(ended, 'R')}" if ended else "")
            )
        return Page(text="\n".join(lines) if len(lines) > 1 else "No war history available.")
