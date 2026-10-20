from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import re
from typing import TYPE_CHECKING, Any, Literal

import discord
from bson import ObjectId
from bson.errors import InvalidId
from discord.ext import commands

from core import FutureTime
from core.utils.database.models import GiveawayEntry as GiveawayModel

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

GIVEAWAY_EMOJI = "\N{PARTY POPPER}"
OBJECT_ID_RE = re.compile(r"\b[0-9a-f]{24}\b")
SNOWFLAKE_RE = re.compile(r"\d{15,21}")
LIST_LIMIT = 10
NOT_FOUND = "No giveaway matches that ID, message ID or message link."
NO_MENTIONS = discord.AllowedMentions.none()
DOT = " \N{MIDDLE DOT} "


def parse_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except InvalidId, TypeError:
        return None


def shorten(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"


def message_url(giveaway: GiveawayModel) -> str:
    return f"https://discord.com/channels/{giveaway['guild_id']}/{giveaway['channel_id']}/{giveaway['message_id']}"


class EnterButton(discord.ui.DynamicItem[discord.ui.Button], template=r"giveaway:enter:(?P<id>[0-9a-f]{24})"):
    """One registered item answers the button of every giveaway, past and future.

    The custom id format is unchanged, so giveaways that are already running keep working.
    """

    def __init__(self, giveaway_id: ObjectId | str, *, disabled: bool = False) -> None:
        self.giveaway_id = str(giveaway_id)
        super().__init__(
            discord.ui.Button(
                label="Enter giveaway",
                emoji=GIVEAWAY_EMOJI,
                style=discord.ButtonStyle.success,
                custom_id=f"giveaway:enter:{self.giveaway_id}",
                disabled=disabled,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /) -> EnterButton:
        return cls(match["id"])

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        database = interaction.client.database
        giveaway = await database.get_giveaway(ObjectId(self.giveaway_id))
        if giveaway is None or giveaway["ended"] or giveaway["ends_at"] <= discord.utils.utcnow():
            await interaction.response.send_message("This giveaway has ended.", ephemeral=True)
            return

        role_id = await database.get_giveaway_role_id(giveaway["guild_id"])
        if role_id is not None and not (isinstance(interaction.user, discord.Member) and interaction.user.get_role(role_id)):
            await interaction.response.send_message(f"You need the <@&{role_id}> role to enter.", ephemeral=True)
            return

        added = await database.add_giveaway_entrant(giveaway_id=giveaway["_id"], user_id=interaction.user.id)
        await interaction.response.send_message("You are entered!" if added else "You are already entered.", ephemeral=True)


def entry_view(giveaway_id: ObjectId | str, *, disabled: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(EnterButton(giveaway_id, disabled=disabled))
    return view


class Giveaway(commands.Cog):
    """Create persistent giveaways with a button or a reaction."""

    help_emoji = GIVEAWAY_EMOJI

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._tasks: set[asyncio.Task[None]] = set()
        _log.debug("Cog loaded: %s", type(self).__name__)

    async def cog_load(self) -> None:
        """Register the button handler and reconcile running giveaways after a restart."""
        self.bot.add_dynamic_items(EnterButton)

        collection = self.bot.database.giveaways_collection
        await collection.create_index([("guild_id", 1), ("message_id", 1)])
        await collection.create_index([("ended", 1), ("guild_id", 1)])

        now = discord.utils.utcnow()
        for giveaway in await self.bot.database.get_giveaways(ended=False):
            if giveaway["ends_at"] <= now:
                task = asyncio.create_task(self._recover_giveaway(giveaway["_id"]))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
                continue

            timers = await self.bot.event_scheduler.search(event_name="giveaway", metadata_filter={"giveaway_id": str(giveaway["_id"])})
            if not timers:
                await self.bot.event_scheduler.create_timer(
                    event_name="giveaway", expires_at=giveaway["ends_at"], metadata={"giveaway_id": str(giveaway["_id"])}
                )

    async def cog_unload(self) -> None:
        self.bot.remove_dynamic_items(EnterButton)

    @staticmethod
    def _embed(giveaway: GiveawayModel, *, role_id: int | None = None) -> discord.Embed:
        ended = giveaway["ended"]
        cancelled = giveaway.get("cancelled", False)
        winners = giveaway.get("winner_ids") or []

        lines = [f"**Prize:** {giveaway['prize']}"]
        if cancelled:
            lines.append("This giveaway was cancelled.")
        elif ended:
            lines.append("This giveaway has ended.")
        elif giveaway.get("entry_mode", "reaction") == "reaction":
            lines.append(f"React with {GIVEAWAY_EMOJI} to enter!")
        else:
            lines.append("Click **Enter giveaway** to enter!")

        colour = discord.Colour.red() if cancelled else discord.Colour.dark_grey() if ended else discord.Colour.blurple()
        embed = discord.Embed(title=f"{GIVEAWAY_EMOJI} Giveaway", colour=colour, description="\n".join(lines))
        embed.add_field(name="Winners", value=str(giveaway["winners"]))
        when = (giveaway.get("ended_at") or giveaway["ends_at"]) if ended else giveaway["ends_at"]
        embed.add_field(name="Ended" if ended else "Ends", value=discord.utils.format_dt(when, "R"))
        embed.add_field(name="Hosted by", value=f"<@{giveaway['host_id']}>")
        if role_id is not None and not ended:
            embed.add_field(name="Requires", value=f"<@&{role_id}>")
        if ended and not cancelled:
            embed.add_field(name="Winner(s)", value=", ".join(f"<@{user_id}>" for user_id in winners) or "No eligible entrants.", inline=False)
        return embed.set_footer(text=f"Giveaway ID: {giveaway['_id']}")

    async def _refresh_message(self, giveaway: GiveawayModel, message: discord.Message | None) -> None:
        """Button giveaways own their message, so keep its embed and button in sync. Reaction ones are the host's message."""
        if message is None or giveaway.get("entry_mode", "reaction") != "button":
            return
        role_id = await self.bot.database.get_giveaway_role_id(giveaway["guild_id"])
        try:
            await message.edit(embed=self._embed(giveaway, role_id=role_id), view=entry_view(giveaway["_id"], disabled=giveaway["ended"]))
        except discord.HTTPException:
            _log.warning("Could not update giveaway message %s", giveaway["message_id"])

    async def _is_eligible(self, guild: discord.Guild, user_id: int, role_id: int | None) -> bool:
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:  # includes NotFound: they left the server
                return False
        if member.bot:
            return False
        return role_id is None or member.get_role(role_id) is not None

    async def _draw(self, guild: discord.Guild, giveaway: GiveawayModel, count: int, *, exclude: set[int] | None = None) -> list[int]:
        """Shuffle the entrants and take the first ``count`` who are still eligible (checked lazily, so few API calls)."""
        role_id = await self.bot.database.get_giveaway_role_id(guild.id)
        pool = [user_id for user_id in giveaway["entrants"] if user_id not in (exclude or set())]
        random.shuffle(pool)

        winners: list[int] = []
        for user_id in pool:
            if len(winners) >= count:
                break
            if await self._is_eligible(guild, user_id, role_id):
                winners.append(user_id)
        return winners

    @staticmethod
    async def _fetch_message(channel: Any, message_id: int) -> discord.Message | None:
        try:
            return await channel.fetch_message(message_id)
        except discord.NotFound, discord.Forbidden:
            return None

    async def _sync_reaction_entrants(self, giveaway: GiveawayModel, message: discord.Message) -> None:
        """Reaction giveaways are recounted from the live reactions, which also catches anything missed while offline."""
        reaction = next((reaction for reaction in message.reactions if str(reaction.emoji) == GIVEAWAY_EMOJI), None)
        entrants = [user.id async for user in reaction.users() if not user.bot] if reaction else []
        await self.bot.database.set_giveaway_entrants(giveaway["_id"], entrants)
        giveaway["entrants"] = entrants

    @staticmethod
    async def _announce(channel: Any, message: discord.Message | None, giveaway: GiveawayModel, winners: list[int], *, reroll: bool = False) -> None:
        prize = giveaway["prize"]
        if winners:
            mentions = ", ".join(f"<@{user_id}>" for user_id in winners)
            text = f"{'The giveaway was rerolled. ' if reroll else ''}Congratulations {mentions}! You won **{prize}**!"
        else:
            text = f"The giveaway for **{prize}** ended with no eligible entrants."

        allowed = discord.AllowedMentions(users=True)
        try:
            if message is not None:
                await message.reply(text, allowed_mentions=allowed)
                return
        except discord.HTTPException:
            pass  # the message vanished meanwhile, fall back to a plain post
        try:
            await channel.send(text, allowed_mentions=allowed)
        except discord.HTTPException:
            _log.warning("Could not announce winners of giveaway %s", giveaway["_id"])

    async def _finish_giveaway(self, giveaway: GiveawayModel) -> None:
        guild = self.bot.get_guild(giveaway["guild_id"])
        channel = guild.get_channel_or_thread(giveaway["channel_id"]) if guild else None
        if guild is None or not isinstance(channel, discord.abc.Messageable):
            _log.warning("Giveaway %s ended but its channel is gone", giveaway["_id"])
            return

        message = await self._fetch_message(channel, giveaway["message_id"])
        if giveaway.get("entry_mode", "reaction") == "reaction" and message is not None:
            await self._sync_reaction_entrants(giveaway, message)

        winners = await self._draw(guild, giveaway, giveaway["winners"])
        await self.bot.database.set_giveaway_winners(giveaway["_id"], winners)
        giveaway["winner_ids"] = winners

        await self._refresh_message(giveaway, message)
        await self._announce(channel, message, giveaway, winners)

    async def _recover_giveaway(self, giveaway_id: ObjectId) -> None:
        giveaway = await self.bot.database.end_giveaway(giveaway_id)
        if giveaway is not None:
            await self._finish_giveaway(giveaway)

    async def _find(self, ctx: commands.Context[Bot], text: str) -> GiveawayModel | None:
        """Accepts a giveaway ID, a message ID or a message link."""
        assert ctx.guild is not None
        database = self.bot.database
        giveaway = None
        if (match := OBJECT_ID_RE.search(text)) and (object_id := parse_object_id(match.group())):
            giveaway = await database.get_giveaway(object_id)
        if giveaway is None and (numbers := SNOWFLAKE_RE.findall(text)):
            giveaway = await database.get_giveaway_by_message(guild_id=ctx.guild.id, message_id=int(numbers[-1]))
        return giveaway if giveaway is not None and giveaway["guild_id"] == ctx.guild.id else None

    @commands.Cog.listener("on_raw_reaction_add")
    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_giveaway_reaction(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or str(payload.emoji) != GIVEAWAY_EMOJI:
            return
        if (self.bot.user is not None and payload.user_id == self.bot.user.id) or (payload.member is not None and payload.member.bot):
            return

        database = self.bot.database
        giveaway = await database.get_giveaway_by_message(guild_id=payload.guild_id, message_id=payload.message_id)
        if giveaway is None or giveaway.get("entry_mode", "reaction") != "reaction" or giveaway["ended"]:
            return

        if payload.event_type == "REACTION_ADD":
            await database.add_giveaway_entrant(giveaway_id=giveaway["_id"], user_id=payload.user_id)
        else:
            await database.remove_giveaway_entrant(giveaway_id=giveaway["_id"], user_id=payload.user_id)

    @commands.Cog.listener()
    async def on_giveaway_timer_complete(self, metadata: dict[str, object]) -> None:
        object_id = parse_object_id(str(metadata["giveaway_id"]))
        if object_id is not None:
            await self._recover_giveaway(object_id)

    @commands.group(name="giveaway", invoke_without_command=True, aliases=["gaw", "gw"])
    @commands.guild_only()
    async def giveaway(self, ctx: commands.Context[Bot]) -> None:
        """Manage giveaways in this server."""
        await ctx.send_help(ctx.command)

    @giveaway.command(name="start")
    @commands.has_guild_permissions(manage_guild=True)
    async def start_giveaway(
        self,
        ctx: commands.Context[Bot],
        duration: FutureTime = commands.parameter(description="How long the giveaway runs, e.g. 1h or 2d"),  # noqa: B008
        winners: commands.Range[int, 1, 20] = commands.parameter(description="How many winners to draw (1-20)"),  # noqa: B008
        *,
        prize: str = commands.parameter(description="What is being given away"),
    ) -> None:
        """Start a giveaway: giveaway start <duration> <winners> <prize>."""
        guild = ctx.guild
        if guild is None:
            return
        database = self.bot.database

        channel_id = await database.get_giveaway_channel_id(guild.id)
        configured = guild.get_channel(channel_id) if channel_id else None
        channel = configured if isinstance(configured, discord.TextChannel) else ctx.channel
        role_id = await database.get_giveaway_role_id(guild.id)

        try:
            message = await channel.send("\N{HOURGLASS WITH FLOWING SAND} Creating giveaway\N{HORIZONTAL ELLIPSIS}")
        except discord.Forbidden:
            await ctx.reply(f"I cannot send messages in {channel.mention}.")  # type: ignore[union-attr]
            return

        giveaway_id: ObjectId | None = None
        try:
            result = await database.create_giveaway(
                guild_id=guild.id,
                channel_id=channel.id,
                message_id=message.id,
                host_id=ctx.author.id,
                prize=prize,
                winners=winners,
                ends_at=duration.dt,
                entry_mode="button",
            )
            giveaway_id = result.inserted_id
            giveaway = await database.get_giveaway(result.inserted_id)
            if giveaway is None:
                msg = "giveaway was not saved"
                raise RuntimeError(msg)

            await message.edit(content=None, embed=self._embed(giveaway, role_id=role_id), view=entry_view(result.inserted_id))
            await self.bot.event_scheduler.create_timer(
                event_name="giveaway", expires_at=duration.dt, metadata={"giveaway_id": str(result.inserted_id)}
            )
        except Exception:
            # Do not leave a half-created giveaway behind.
            if giveaway_id is not None:
                await database.end_giveaway(giveaway_id, cancelled=True)
            with contextlib.suppress(discord.HTTPException):
                await message.delete(delay=0)
            raise

        where = "" if channel.id == ctx.channel.id else f" in {message.jump_url}"
        await ctx.reply(f"Giveaway started{where} and ends {discord.utils.format_dt(duration.dt, 'R')}.", delete_after=15)

    @giveaway.command(name="from-message", aliases=["message"])
    @commands.has_guild_permissions(manage_guild=True)
    async def giveaway_from_message(
        self,
        ctx: commands.Context[Bot],
        message: discord.Message = commands.parameter(description="The message (link or ID) to turn into a giveaway"),  # noqa: B008
        duration: FutureTime = commands.parameter(description="How long the giveaway runs, e.g. 1h or 2d"),  # noqa: B008
        winners: commands.Range[int, 1, 20] = commands.parameter(description="How many winners to draw (1-20)"),  # noqa: B008
    ) -> None:
        """Turn your own message into a reaction giveaway."""
        if ctx.guild is None or message.guild != ctx.guild or message.author.id != ctx.author.id:
            await ctx.reply("The message must be your own message in this server.")
            return
        if await self.bot.database.get_giveaway_by_message(guild_id=ctx.guild.id, message_id=message.id):
            await ctx.reply("That message is already a giveaway.")
            return

        try:
            await message.add_reaction(GIVEAWAY_EMOJI)  # first, so a missing permission does not leave a record behind
        except discord.HTTPException:
            await ctx.reply("I could not add the reaction to that message. I need **Add Reactions** and **Read Message History** there.")
            return

        result = await self.bot.database.create_giveaway(
            guild_id=ctx.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
            host_id=ctx.author.id,
            prize=message.content or "Giveaway",
            winners=winners,
            ends_at=duration.dt,
            entry_mode="reaction",
        )
        await self.bot.event_scheduler.create_timer(event_name="giveaway", expires_at=duration.dt, metadata={"giveaway_id": str(result.inserted_id)})
        await ctx.reply(f"Your message is now a giveaway and ends {discord.utils.format_dt(duration.dt, 'R')}.", delete_after=15)

    @giveaway.command(name="end")
    @commands.has_guild_permissions(manage_guild=True)
    async def end_giveaway(
        self, ctx: commands.Context[Bot], giveaway_id: str = commands.parameter(description="Giveaway ID, message ID or message link")
    ) -> None:
        """End a giveaway now and draw the winners."""
        giveaway = await self._find(ctx, giveaway_id)
        if giveaway is None or giveaway["ended"]:
            await ctx.reply(NOT_FOUND if giveaway is None else "That giveaway has already ended.")
            return

        ended = await self.bot.database.end_giveaway(giveaway["_id"])
        if ended is None:  # the timer won the race
            await ctx.reply("That giveaway has already ended.")
            return

        await self.bot.event_scheduler.delete(event_name="giveaway", metadata_filter={"giveaway_id": str(giveaway["_id"])})
        await self._finish_giveaway(ended)
        await ctx.reply("Giveaway ended.", delete_after=10)

    @giveaway.command(name="cancel")
    @commands.has_guild_permissions(manage_guild=True)
    async def cancel_giveaway(
        self, ctx: commands.Context[Bot], giveaway_id: str = commands.parameter(description="Giveaway ID, message ID or message link")
    ) -> None:
        """Cancel a giveaway without drawing winners."""
        giveaway = await self._find(ctx, giveaway_id)
        if giveaway is None or giveaway["ended"]:
            await ctx.reply(NOT_FOUND if giveaway is None else "That giveaway has already ended.")
            return

        cancelled = await self.bot.database.end_giveaway(giveaway["_id"], cancelled=True)
        if cancelled is None:
            await ctx.reply("That giveaway has already ended.")
            return

        await self.bot.event_scheduler.delete(event_name="giveaway", metadata_filter={"giveaway_id": str(giveaway["_id"])})
        channel = ctx.guild.get_channel_or_thread(cancelled["channel_id"]) if ctx.guild else None
        if isinstance(channel, discord.abc.Messageable):
            await self._refresh_message(cancelled, await self._fetch_message(channel, cancelled["message_id"]))
        await ctx.reply("Giveaway cancelled. No winners were drawn.", delete_after=10)

    @giveaway.command(name="reroll")
    @commands.has_guild_permissions(manage_guild=True)
    async def reroll_giveaway(
        self,
        ctx: commands.Context[Bot],
        giveaway_id: str = commands.parameter(description="Giveaway ID, message ID or message link"),
        count: commands.Range[int, 1, 20] = commands.parameter(default=1, description="How many new winners to pick"),  # noqa: B008
    ) -> None:
        """Pick new winners from the remaining entrants (earlier winners are excluded)."""
        giveaway = await self._find(ctx, giveaway_id)
        if giveaway is None or not giveaway["ended"] or giveaway.get("cancelled"):
            await ctx.reply(NOT_FOUND if giveaway is None else "Only finished giveaways can be rerolled.")
            return

        assert ctx.guild is not None
        channel = ctx.guild.get_channel_or_thread(giveaway["channel_id"])
        if not isinstance(channel, discord.abc.Messageable):
            await ctx.reply("I cannot find the giveaway's channel anymore.")
            return

        previous = giveaway.get("winner_ids") or []
        new = await self._draw(ctx.guild, giveaway, count, exclude=set(previous))
        if not new:
            await ctx.reply("There is nobody left to pick.")
            return

        giveaway["winner_ids"] = [*previous, *new]
        await self.bot.database.set_giveaway_winners(giveaway["_id"], giveaway["winner_ids"])

        message = await self._fetch_message(channel, giveaway["message_id"])
        await self._refresh_message(giveaway, message)
        await self._announce(channel, message, giveaway, new, reroll=True)

    @giveaway.command(name="list")
    async def list_giveaways(self, ctx: commands.Context[Bot]) -> None:
        """List the running giveaways of this server."""
        assert ctx.guild is not None
        giveaways = sorted(await self.bot.database.get_giveaways(guild_id=ctx.guild.id, ended=False), key=lambda item: item["ends_at"])
        if not giveaways:
            await ctx.reply("There are no running giveaways.")
            return

        lines = [
            f"[{discord.utils.escape_markdown(shorten(item['prize'], 40))}]({message_url(item)})\n"
            f"-# {item['winners']} winner(s){DOT}ends {discord.utils.format_dt(item['ends_at'], 'R')}{DOT}`{item['_id']}`"
            for item in giveaways[:LIST_LIMIT]
        ]
        embed = discord.Embed(title=f"{GIVEAWAY_EMOJI} Running giveaways", description="\n".join(lines), colour=discord.Colour.blurple())
        if len(giveaways) > LIST_LIMIT:
            embed.set_footer(text=f"Showing {LIST_LIMIT} of {len(giveaways)}")
        await ctx.reply(embed=embed)

    @giveaway.command(name="info")
    async def giveaway_info(
        self,
        ctx: commands.Context[Bot],
        giveaway_id: str = commands.parameter(description="Giveaway ID, message ID or message link"),
    ) -> None:
        """Show the details and status of a giveaway."""
        giveaway = await self._find(ctx, giveaway_id)
        if giveaway is None:
            await ctx.reply(NOT_FOUND)
            return

        status = "Cancelled" if giveaway.get("cancelled") else "Ended" if giveaway["ended"] else "Running"
        when = (giveaway.get("ended_at") or giveaway["ends_at"]) if giveaway["ended"] else giveaway["ends_at"]
        mode = giveaway.get("entry_mode", "reaction")

        embed = discord.Embed(title=shorten(giveaway["prize"], 200), colour=discord.Colour.blurple(), url=message_url(giveaway))
        embed.add_field(name="Status", value=status)
        embed.add_field(name="Hosted by", value=f"<@{giveaway['host_id']}>")
        embed.add_field(name="Winners", value=str(giveaway["winners"]))
        embed.add_field(name="Ended" if giveaway["ended"] else "Ends", value=discord.utils.format_dt(when, "R"))
        embed.add_field(name="Entries", value=str(len(giveaway["entrants"])))
        embed.add_field(name="Entry", value="Button" if mode == "button" else f"Reaction {GIVEAWAY_EMOJI}")
        if giveaway.get("winner_ids"):
            embed.add_field(name="Winner(s)", value=", ".join(f"<@{user_id}>" for user_id in giveaway["winner_ids"]), inline=False)
        if mode == "reaction" and not giveaway["ended"]:
            embed.set_footer(text=f"Entries are recounted from the reactions when it ends. ID: {giveaway['_id']}")
        else:
            embed.set_footer(text=f"ID: {giveaway['_id']}")
        await ctx.reply(embed=embed, allowed_mentions=NO_MENTIONS)

    @giveaway.command(name="role")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_role(
        self,
        ctx: commands.Context[Bot],
        role: discord.Role | Literal["none"] | None = commands.parameter(default=None, description="Required role, or 'none' to clear"),  # noqa: B008
    ) -> None:
        """Show or set the role members need to enter giveaways."""
        assert ctx.guild is not None
        database = self.bot.database

        if role is None:
            current = await database.get_giveaway_role_id(ctx.guild.id)
            await ctx.reply(f"Entering requires <@&{current}>." if current else "Anyone can enter.", allowed_mentions=NO_MENTIONS)
            return

        role_id = None if isinstance(role, str) else role.id
        saved = await database.edit_giveaway_config(guild_id=ctx.guild.id, giveaway_role_id=role_id)
        if not saved:
            await ctx.reply("Could not save the setting.")
        elif role_id is None:
            await ctx.reply("Requirement removed. Anyone can enter.")
        else:
            await ctx.reply(f"Entering now requires <@&{role_id}>. It applies to every running giveaway.", allowed_mentions=NO_MENTIONS)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Giveaway(bot))
