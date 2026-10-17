from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, Any, ClassVar

import discord
from discord import app_commands
from discord.ext import commands

from core.utils.formats import truncate
from core.utils.paginator import PaginationLayout
from core.utils.views import MAX_TEXT_LENGTH, BaseLayoutView, NoticeLayout

from .api import Game, ImageStore, NotFound, SupercellClient, SupercellError, enc

if TYPE_CHECKING:
    from core import Bot

__all__ = ("Loader", "Page", "Supercell", "TabbedLayout")

NO_MENTIONS = discord.AllowedMentions.none()


@dataclass(slots=True)
class Page:
    text: str | None = None
    image: bytes | None = None


type Loader = Callable[[], Awaitable[Page]]


class TabbedLayout(BaseLayoutView):
    """A components v2 message whose buttons switch between lazily loaded pages."""

    def __init__(
        self,
        author: discord.User | discord.Member,
        *,
        tabs: dict[str, Loader],
        colour: discord.Colour,
        timeout: float = 300.0,
    ) -> None:
        super().__init__(author, timeout=timeout)
        self.tabs = tabs
        self.colour = colour
        self.current = next(iter(tabs))
        self._cache: dict[str, Page] = {}

    async def _load(self, name: str) -> Page:
        if (page := self._cache.get(name)) is None:
            page = self._cache[name] = await self.tabs[name]()
        return page

    def _build(self, page: Page) -> list[discord.File]:
        self.clear_items()
        container = discord.ui.Container(accent_colour=self.colour)
        files: list[discord.File] = []

        if page.image:
            filename = f"page-{list(self.tabs).index(self.current)}.png"
            files.append(discord.File(BytesIO(page.image), filename=filename))
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{filename}")))

        if page.text:
            container.add_item(discord.ui.TextDisplay(truncate(page.text, MAX_TEXT_LENGTH)))

        container.add_item(discord.ui.Separator())
        row = discord.ui.ActionRow()
        for name in self.tabs:
            style = discord.ButtonStyle.primary if name == self.current else discord.ButtonStyle.secondary
            button = discord.ui.Button(label=name, style=style)
            button.callback = self._switcher(name)
            row.add_item(button)
        container.add_item(row)

        self.add_item(container)
        return files

    def _switcher(self, name: str):
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            if name == self.current:
                return

            try:
                page = await self._load(name)
            except SupercellError as error:
                await interaction.followup.send(str(error), ephemeral=True)
                return

            self.current = name
            files = self._build(page)
            await interaction.edit_original_response(view=self, attachments=files)

        return callback

    async def start(self, ctx: commands.Context[Bot]) -> discord.Message:
        page = await self._load(self.current)
        files = self._build(page)
        self.message = await ctx.reply(view=self, files=files, allowed_mentions=NO_MENTIONS)
        return self.message


class Supercell(commands.Cog):
    """Behaviour shared by the Clash Royale and Clash of Clans cogs."""

    help_category = "Supercell"
    help_emoji = "\N{CROSSED SWORDS}\N{VARIATION SELECTOR-16}"
    help_description = "Clash Royale, Clash of Clans and Brawl Stars profiles, clans and leaderboards."

    game: ClassVar[Game]
    group_name: ClassVar[str]

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.api = SupercellClient(bot, self.game)
        self.images = ImageStore(bot)

    async def resolve_tag(self, ctx: commands.Context[Bot], tag: str | None, user: discord.User | discord.Member | None) -> str:
        if tag is not None:
            return tag

        target = user or ctx.author
        account = await self.bot.database.get_supercell_account(target.id, self.game.key)
        if account is None:
            who = "You haven't" if target == ctx.author else f"{target.display_name} hasn't"
            message = f"{who} linked a {self.game.name} account. Use `{ctx.clean_prefix}{self.group_name} link #TAG` or pass a tag."
            raise SupercellError(message)
        return account["tag"]

    async def link_text(self, tag: str) -> str | None:
        owners = await self.bot.database.get_supercell_owners(self.game.key, tag)
        if not owners:
            return None
        return "-# Linked to " + ", ".join(f"<@{user_id}>" + (" \N{WHITE HEAVY CHECK MARK}" if verified else "") for user_id, verified in owners)

    async def link_account(self, ctx: commands.Context[Bot], tag: str, *, verified: bool = False, ephemeral: bool = False) -> None:
        player = await self.api.get(f"/players/{enc(tag)}", ttl=300)
        database = self.bot.database
        await database.register_user(ctx.author.id)
        await database.set_supercell_account(ctx.author.id, self.game.key, tag=tag, verified=verified)

        body = f"Linked **{discord.utils.escape_markdown(player['name'])}** (`{tag}`) to your Discord account."
        if verified:
            body += "\nOwnership verified."
        await ctx.reply(view=NoticeLayout.success(body, title=f"{self.game.name} account linked"), ephemeral=ephemeral)

    async def unlink_account(self, ctx: commands.Context[Bot]) -> None:
        removed = await self.bot.database.remove_supercell_account(ctx.author.id, self.game.key)
        if removed:
            view = NoticeLayout.success(f"Your {self.game.name} account has been unlinked.")
        else:
            view = NoticeLayout.warning(f"You don't have a {self.game.name} account linked.")
        await ctx.reply(view=view)

    async def show(self, ctx: commands.Context[Bot], tabs: dict[str, Loader]) -> None:
        await TabbedLayout(ctx.author, tabs=tabs, colour=self.game.colour).start(ctx)

    async def paginate(self, ctx: commands.Context[Bot], title: str, lines: list[str], *, per_page: int = 10) -> None:
        if not lines:
            message = "Nothing to show."
            raise NotFound(message)

        pages: list[list[discord.ui.Item]] = [[discord.ui.TextDisplay("\n".join(chunk))] for chunk in discord.utils.as_chunks(lines, per_page)]
        layout = PaginationLayout(
            ctx.author,
            header=discord.ui.TextDisplay(f"### {title}"),
            footer=discord.ui.TextDisplay(f"-# {self.game.name}"),
            items=pages,
        )
        await layout.start(ctx, allowed_mentions=NO_MENTIONS)

    async def clan_tag_for(self, ctx: commands.Context[Bot], tag: str | None, user: discord.User | discord.Member | None) -> str:
        if tag:
            return tag

        player_tag = await self.resolve_tag(ctx, None, user)
        player = await self.api.get(f"/players/{enc(player_tag)}", ttl=120)
        if not (clan := player.get("clan")):
            message = f"**{discord.utils.escape_markdown(player['name'])}** isn't in a clan."
            raise NotFound(message)
        return clan["tag"]

    async def search_clans(self, ctx: commands.Context[Bot], name: str, **params: Any) -> str:
        if len(name.strip()) < 3:
            message = "Clan searches need at least three characters."
            raise SupercellError(message)

        data = await self.api.get("/clans", params={"name": name.strip(), "limit": 25, **params}, ttl=300)
        if not (items := data.get("items")):
            message = f"No clans matched `{name}`."
            raise NotFound(message)

        try:
            clan = await self.bot.disambiguate(
                ctx,
                matches=items,
                entry=lambda c: truncate(f"{c['name']} {c['tag']} \N{MIDDLE DOT} {c.get('members', 0)} members", 95),
            )
        except ValueError as error:
            raise SupercellError(str(error)) from None

        if clan is None:
            message = "Selection timed out."
            raise SupercellError(message)
        return clan["tag"]

    async def locations(self) -> list[dict[str, Any]]:
        data = await self.api.get("/locations", params={"limit": 1000}, ttl=86_400)
        return data.get("items", [])

    async def resolve_location(self, query: str) -> tuple[str, str]:
        needle = query.strip().casefold()
        if needle in {"", "global", "world"}:
            return "global", "Global"

        locations = await self.locations()
        for item in locations:
            if needle in {item["name"].casefold(), str(item.get("countryCode", "")).casefold(), str(item["id"])}:
                return str(item["id"]), item["name"]
        for item in locations:
            if item["name"].casefold().startswith(needle):
                return str(item["id"]), item["name"]

        message = f"Bot could not find a location called `{query}`."
        raise SupercellError(message)

    async def location_choices(self, current: str) -> list[app_commands.Choice[str]]:
        try:
            names = ["Global", *(item["name"] for item in await self.locations())]
        except SupercellError:
            return []
        needle = current.casefold()
        return [app_commands.Choice(name=name, value=name) for name in names if needle in name.casefold()][:25]
