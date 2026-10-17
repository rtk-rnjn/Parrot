from __future__ import annotations

import asyncio
import difflib
from statistics import fmean
from typing import TYPE_CHECKING, Annotated, Literal

import discord
from discord.ext import commands

from core.utils.formats import human_join, safe_text

from . import render
from .api import CLASH_ROYALE, NotFound, Tag, enc, parse_time
from .base import Page
from .base import Supercell as SupercellCog

if TYPE_CHECKING:
    from core import Bot

    from .base import Loader

TOP_LEVEL = 16
FOOTER = "Clash Royale \N{BULLET} Supercell API"

ROLES = {"member": "Member", "elder": "Elder", "coLeader": "Co-leader", "leader": "Leader"}
CLAN_TYPES = {"open": "Open", "inviteOnly": "Invite only", "closed": "Closed"}
TOURNAMENT_STATUS = {"inPreparation": "Preparing", "inProgress": "Live", "ended": "Ended"}
COMMON_CHESTS = {"Silver Chest", "Golden Chest"}
RARITY_COLOURS = {
    "common": discord.Colour.light_grey(),
    "rare": discord.Colour.orange(),
    "epic": discord.Colour.purple(),
    "legendary": discord.Colour.teal(),
    "champion": discord.Colour.gold(),
}


def _num(data: dict, key: str) -> str:
    return f"{data.get(key) or 0:,}"


def _card_icon(card: dict, *, evolved: bool = False) -> str | None:
    icons = card.get("iconUrls") or {}
    if evolved and card.get("evolutionLevel"):
        return icons.get("evolutionMedium") or icons.get("medium")
    return icons.get("medium")


def _card_label(card: dict) -> str:
    """In-game level is the API's card-relative level plus the gap between the card's cap and the top level."""
    level = card.get("level", 1) + TOP_LEVEL - card.get("maxLevel", TOP_LEVEL)
    return f"Lv {level}" + ("\N{BLACK STAR}" if card.get("starLevel") else "")


class ClashRoyale(SupercellCog, command_attrs={"hidden": True}):
    game = CLASH_ROYALE
    group_name = "cr"

    @commands.group(name="cr", aliases=["clashroyale"], invoke_without_command=True)
    async def cr(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str | None, Tag] = commands.parameter(
            default=None, description="A player tag to look up. If omitted, your linked account will be used."
        ),
        user: discord.User = commands.parameter(default=lambda ctx: ctx.author, description="Show the linked account of this member."),  # noqa: B008
    ) -> None:
        """Show a Clash Royale player profile."""
        if ctx.invoked_subcommand is None:
            async with ctx.typing():
                tag = await self.resolve_tag(ctx, tag, user)
                player = await self.api.get(f"/players/{enc(tag)}", ttl=120)
                await self.show(ctx, self._profile_tabs(player))

    @cr.command(name="link")
    async def link(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str, Tag] = commands.parameter(description="A player tag to link."),
    ) -> None:
        """Link your Clash Royale account."""
        async with ctx.typing():
            await self.link_account(ctx, tag)

    @cr.command(name="unlink")
    async def unlink(self, ctx: commands.Context[Bot]) -> None:
        """Unlink your Clash Royale account."""
        await self.unlink_account(ctx)

    @cr.command(name="clan")
    async def clan(
        self,
        ctx: commands.Context[Bot],
        tag: Annotated[str | None, Tag] = commands.parameter(description="A clan tag to look up.", default=None),
        user: discord.User = commands.parameter(default=lambda ctx: ctx.author, description="Show the linked account of this member."),  # noqa: B008
    ) -> None:
        """Show a clan, by tag or via a player's linked account."""
        async with ctx.typing():
            clan_tag = await self.clan_tag_for(ctx, tag, user)
            await self.show(ctx, self._clan_tabs(clan_tag))

    @cr.command(name="clansearch", aliases=["searchclan"])
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

    @cr.command(name="card")
    async def card(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The name of the card to look up."),
    ) -> None:
        """Look up a card."""
        async with ctx.typing():
            cards = await self._cards()
            by_name = {c["name"].casefold(): c for c in cards}
            needle = name.casefold()
            match = by_name.get(needle) or next((c for key, c in by_name.items() if needle in key), None)
            if match is None and (close := difflib.get_close_matches(needle, by_name, n=1, cutoff=0.5)):
                match = by_name[close[0]]
            if match is None:
                message = f"No card called `{name}`."
                raise NotFound(message)

        lines = [
            f"**Elixir** {match.get('elixirCost', '-')}",
            f"**Rarity** {str(match.get('rarity', '-')).title()}",
            f"**Max level** {match.get('maxLevel', '-')}",
        ]
        if match.get("maxEvolutionLevel"):
            lines.append("**Evolution** available")

        embed = discord.Embed(title=match["name"], description="\n".join(lines), colour=RARITY_COLOURS.get(str(match.get("rarity", "")).lower()))
        embed.set_thumbnail(url=(match.get("iconUrls") or {}).get("medium"))
        await ctx.reply(embed=embed)

    @cr.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(
        self,
        ctx: commands.Context[Bot],
        kind: Literal["players", "clans"] = commands.parameter(description="The type of leaderboard to show.", default="players"),
        *,
        location: str = commands.parameter(description="A country name or Global.", default="global"),
    ) -> None:
        """Show Path of Legends or clan rankings."""
        async with ctx.typing():
            location_id, location_name = await self.resolve_location(location)
            path = "pathoflegend/players" if kind == "players" else "rankings/clans"
            data = await self.api.get(f"/locations/{location_id}/{path}", params={"limit": 100}, ttl=300)

        lines: list[str] = []
        for item in data.get("items", []):
            rank = item.get("rank", len(lines) + 1)
            name = safe_text(item.get("name", "?"))
            if kind == "players":
                score = item.get("eloRating", item.get("trophies", 0))
                clan = (item.get("clan") or {}).get("name")
                lines.append(f"{rank}. **{name}** \N{MIDDLE DOT} {score:,}" + (f" \N{MIDDLE DOT} {safe_text(clan)}" if clan else ""))
            else:
                lines.append(f"{rank}. **{name}** \N{MIDDLE DOT} {item.get('clanScore', 0):,} \N{MIDDLE DOT} {item.get('members', 0)}/50")

        await self.paginate(ctx, f"{location_name} \N{MIDDLE DOT} {'Path of Legends' if kind == 'players' else 'Clans'}", lines)

    @cr.command(name="tournaments", aliases=["tournament"])
    async def tournaments(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="Search for open tournaments by name."),
    ) -> None:
        """Search open tournaments by name."""
        async with ctx.typing():
            data = await self.api.get("/tournaments", params={"name": name, "limit": 50}, ttl=60)

        lines = [
            f"**{safe_text(t.get('name', '?'))}** `{t['tag']}` \N{MIDDLE DOT} {TOURNAMENT_STATUS.get(t.get('status'), '-')}"
            f" \N{MIDDLE DOT} {t.get('capacity', 0)}/{t.get('maxCapacity', 0)} \N{MIDDLE DOT} level cap {t.get('levelCap', '-')}"
            for t in data.get("items", [])
        ]
        if not lines:
            message = f"No tournaments matched `{name}`."
            raise NotFound(message)
        await self.paginate(ctx, "Tournaments", lines, per_page=8)

    async def _cards(self) -> list[dict]:
        data = await self.api.get("/cards", ttl=21_600)
        return data.get("items", [])

    def _profile_tabs(self, player: dict) -> dict[str, Loader]:
        tag = player["tag"]
        tabs: dict[str, Loader] = {
            "Overview": lambda: self._overview(player),
            "Deck": lambda: self._deck(player),
            "Chests": lambda: self._chests(tag),
            "Battles": lambda: self._battles(tag),
        }
        if clan := player.get("clan"):
            tabs["Clan"] = lambda: self._clan_overview(clan["tag"])
        return tabs

    def _clan_tabs(self, tag: str) -> dict[str, Loader]:
        return {
            "Overview": lambda: self._clan_overview(tag),
            "Members": lambda: self._members(tag),
            "River Race": lambda: self._race(tag),
            "War Log": lambda: self._race_log(tag),
        }

    async def _overview(self, player: dict) -> Page:
        clan = player.get("clan")
        deck = player.get("currentDeck", [])
        favourite = player.get("currentFavouriteCard") or {}
        portrait, *strip = await self.images.many([_card_icon(favourite), *(_card_icon(c) for c in deck)])

        battles = player.get("battleCount") or 0
        wins = player.get("wins") or 0
        legend = player.get("currentPathOfLegendSeasonResult") or {}
        stats = [
            ("Trophies", _num(player, "trophies")),
            ("Best", _num(player, "bestTrophies")),
            ("Wins", _num(player, "wins")),
            ("Win rate", f"{wins / battles:.0%}" if battles else "-"),
            ("3-crown wins", _num(player, "threeCrownWins")),
            ("Battles", _num(player, "battleCount")),
            ("Donated", _num(player, "totalDonations")),
            ("Star points", _num(player, "starPoints")),
            ("Cards", str(len(player.get("cards", [])))),
            ("Arena", (player.get("arena") or {}).get("name", "-")),
            ("Path of Legends", f"League {legend['leagueNumber']}" if legend.get("leagueNumber") else "-"),
            ("Max challenge", str(player.get("challengeMaxWins", 0))),
        ]
        if clan:
            line = clan["name"]
            if role := ROLES.get(player.get("role", "")):
                line += f" \N{BULLET} {role}"
        else:
            line = "No clan"

        image = await asyncio.to_thread(
            render.profile_card,
            render.CLASH_ROYALE,
            name=player["name"],
            tag=player["tag"],
            level=f"Lv {player.get('expLevel', 1)}",
            line=line,
            portrait=portrait,
            stats=stats,
            strip=strip,
            footer=FOOTER,
        )
        return Page(text=await self.link_text(player["tag"]), image=image)

    async def _deck(self, player: dict) -> Page:
        deck = player.get("currentDeck", [])
        if not deck:
            return Page(text="This player has no deck set.")

        images = await self.images.many([_card_icon(c, evolved=True) for c in deck])
        slots = [render.DeckSlot(image, _card_label(c), c.get("elixirCost")) for image, c in zip(images, deck, strict=True)]
        costs = [c["elixirCost"] for c in deck if c.get("elixirCost") is not None]
        average = fmean(costs) if costs else 0.0
        ids = ";".join(str(c["id"]) for c in deck)

        image = await asyncio.to_thread(
            render.deck_card,
            render.CLASH_ROYALE,
            title=f"{player['name']}'s deck",
            subtitle=f"Average elixir {average:.1f}",
            slots=slots,
            footer=FOOTER,
        )
        return Page(text=f"-# [Copy deck](https://link.clashroyale.com/deck/en?deck={ids})", image=image)

    async def _chests(self, tag: str) -> Page:
        data = await self.api.get(f"/players/{enc(tag)}/upcomingchests", ttl=120)
        items = sorted(data.get("items", []), key=lambda c: c["index"])
        if not items:
            return Page(text="No chest data available.")

        lines = ["### Upcoming chests"]
        for chest in items[:8]:
            lines.append(f"**Next** \N{MIDDLE DOT} {chest['name']}" if chest["index"] == 0 else f"`+{chest['index']}` {chest['name']}")  # noqa: PERF401

        if special := [c for c in items[8:] if c["name"] not in COMMON_CHESTS]:
            lines += ["", "**Further ahead**", *(f"`+{c['index']}` {c['name']}" for c in special)]
        return Page(text="\n".join(lines))

    async def _battles(self, tag: str) -> Page:
        battles = await self.api.get(f"/players/{enc(tag)}/battlelog", ttl=60)
        if not battles:
            return Page(text="No recent battles.")

        wins = losses = draws = 0
        lines: list[str] = []
        for index, battle in enumerate(battles[:25]):
            me = battle["team"][0]
            opponents = battle.get("opponent") or [{}]
            mine, theirs = me.get("crowns", 0), opponents[0].get("crowns", 0)
            if mine > theirs:
                wins, icon = wins + 1, "\N{LARGE GREEN CIRCLE}"
            elif mine < theirs:
                losses, icon = losses + 1, "\N{LARGE RED CIRCLE}"
            else:
                draws, icon = draws + 1, "\N{MEDIUM WHITE CIRCLE}"

            if index >= 10:
                continue

            names = human_join([safe_text(o.get("name", "?"), 20) for o in opponents], final="&")
            mode = (battle.get("gameMode") or {}).get("name") or battle.get("type", "")
            change = me.get("trophyChange")
            when = parse_time(battle.get("battleTime"))
            lines.append(
                f"{icon} **{mine}-{theirs}** vs {names} \N{MIDDLE DOT} {mode}"
                + (f" \N{MIDDLE DOT} {change:+d}" if change is not None else "")
                + (f" \N{MIDDLE DOT} {discord.utils.format_dt(when, 'R')}" if when else "")
            )

        header = f"### Recent battles\nLast {min(len(battles), 25)}: **{wins}W {losses}L {draws}D**"
        return Page(text="\n".join([header, "", *lines]))

    async def _clan_overview(self, tag: str) -> Page:
        clan = await self.api.get(f"/clans/{enc(tag)}", ttl=300)
        portrait = await self.images.get((clan.get("badgeUrls") or {}).get("large"))
        stats = [
            ("Clan score", _num(clan, "clanScore")),
            ("War trophies", _num(clan, "clanWarTrophies")),
            ("Donations/wk", _num(clan, "donationsPerWeek")),
            ("Required", _num(clan, "requiredTrophies")),
            ("Type", CLAN_TYPES.get(clan.get("type", ""), "-")),
            ("Location", (clan.get("location") or {}).get("name", "-")),
            ("Chest level", str(clan.get("clanChestLevel", "-"))),
            ("Members", f"{clan.get('members', 0)}/50"),
        ]
        image = await asyncio.to_thread(
            render.profile_card,
            render.CLASH_ROYALE,
            name=clan["name"],
            tag=clan["tag"],
            level=f"{clan.get('members', 0)}/50",
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

    async def _race(self, tag: str) -> Page:
        race = await self.api.get(f"/clans/{enc(tag)}/currentriverrace", ttl=120)
        period = {"training": "Training", "warDay": "War day", "colosseum": "Colosseum"}.get(race.get("periodType", ""), "River Race")
        standings = sorted(race.get("clans", []), key=lambda c: c.get("fame", 0), reverse=True)

        lines = [f"### River Race \N{MIDDLE DOT} Week {race.get('sectionIndex', 0) + 1}", period, "", "**Standings**"]
        for rank, clan in enumerate(standings, 1):
            marker = " \N{BLACK LEFT-POINTING TRIANGLE}" if clan["tag"] == tag else ""
            lines.append(f"`{rank}` **{safe_text(clan['name'])}** \N{MIDDLE DOT} {clan.get('fame', 0):,} fame{marker}")

        participants = sorted((race.get("clan") or {}).get("participants", []), key=lambda p: p.get("fame", 0), reverse=True)[:10]
        if participants:
            lines += ["", "**Top contributors**"]
            lines += [
                f"**{safe_text(p['name'], 22)}** \N{MIDDLE DOT} {p.get('fame', 0):,} fame \N{MIDDLE DOT} {p.get('decksUsed', 0)} decks"
                for p in participants
            ]
        return Page(text="\n".join(lines))

    async def _race_log(self, tag: str) -> Page:
        data = await self.api.get(f"/clans/{enc(tag)}/riverracelog", params={"limit": 10}, ttl=600)
        lines = ["### River Race log"]
        for race in data.get("items", []):
            standing = next((s for s in race.get("standings", []) if s["clan"]["tag"] == tag), None)
            if standing is None:
                continue
            when = parse_time(race.get("createdDate"))
            lines.append(
                f"**Season {race.get('seasonId', '?')} \N{MIDDLE DOT} Week {race.get('sectionIndex', 0) + 1}** - rank **{standing['rank']}**"
                f" \N{MIDDLE DOT} {standing['clan'].get('fame', 0):,} fame \N{MIDDLE DOT} {standing.get('trophyChange', 0):+d}"
                + (f" \N{MIDDLE DOT} {discord.utils.format_dt(when, 'R')}" if when else "")
            )
        return Page(text="\n".join(lines) if len(lines) > 1 else "No river race history available.")
