from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

import discord
from bson import ObjectId
from discord.ext import commands

from core.utils import FutureTime
from core.utils.database_manager.models import Giveaway

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.giveaway")
GIVEAWAY_EMOJI = "\N{PARTY POPPER}"


class GiveawayCog(commands.Cog):
    """Create persistent reaction-based giveaways."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", type(self).__name__)

    async def cog_load(self) -> None:
        """Restore persistent views and reconcile giveaways after a restart."""
        for giveaway in await self.bot.database_manager.get_giveaways():
            if giveaway.get("entry_mode", "reaction") == "button":
                self.bot.add_view(GiveawayView(self, giveaway), message_id=giveaway["message_id"])

            if giveaway["ended"]:
                continue
            if giveaway["ends_at"] <= discord.utils.utcnow():
                self.bot.loop.create_task(self._recover_giveaway(giveaway["_id"]))
                continue

            timers = await self.bot.timer_manager.search_timers(
                event_name="giveaway",
                metadata_filter={"giveaway_id": str(giveaway["_id"])},
            )
            if not timers:
                await self.bot.timer_manager.create_timer(
                    event_name="giveaway",
                    expires_at=giveaway["ends_at"],
                    metadata={"giveaway_id": str(giveaway["_id"])},
                )

    @staticmethod
    def _embed(giveaway: Giveaway, *, winners: list[int] | None = None) -> discord.Embed:
        embed = discord.Embed(title=f"{GIVEAWAY_EMOJI} Giveaway", colour=discord.Colour.blurple())
        entry_mode = giveaway.get("entry_mode", "reaction")
        entry_hint = "React with \N{PARTY POPPER} to enter!" if entry_mode == "reaction" else "Click **Enter giveaway** to enter!"
        embed.description = f"**Prize:** {giveaway['prize']}\n{entry_hint}"
        embed.add_field(name="Winners", value=str(giveaway["winners"]))
        embed.add_field(name="Ends", value=discord.utils.format_dt(giveaway["ends_at"], "R"))
        embed.set_footer(text=f"Giveaway ID: {giveaway['_id']}")
        if giveaway["ended"]:
            embed.description = f"**Prize:** {giveaway['prize']}\nThis giveaway has ended."
            embed.colour = discord.Colour.dark_grey()
            embed.set_field_at(1, name="Ended", value=discord.utils.format_dt(giveaway["ends_at"], "R"))
            if winners:
                embed.add_field(name="Winner(s)", value=", ".join(f"<@{user_id}>" for user_id in winners))
            else:
                embed.add_field(name="Winner(s)", value="No eligible entrants.")
        return embed

    @staticmethod
    def _object_id(value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except Exception:
            return None

    @commands.group(name="giveaway", invoke_without_command=True)
    @commands.guild_only()
    async def giveaway(self, ctx: commands.Context[Parrot]) -> None:
        """Manage giveaways in this server."""
        await ctx.send_help(ctx.command)

    @giveaway.command(name="start")
    @commands.has_guild_permissions(manage_guild=True)
    async def start_giveaway(
        self,
        ctx: commands.Context[Parrot],
        duration: FutureTime,
        winners: commands.Range[int, 1, 20],
        *,
        prize: str,
    ) -> None:
        """Start a giveaway: giveaway start <duration> <winners> <prize>."""
        if ctx.guild is None:
            return

        ends_at = duration.dt
        draft: Giveaway = {
            "_id": ObjectId(),
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "message_id": 0,
            "host_id": ctx.author.id,
            "prize": prize,
            "winners": winners,
            "ends_at": ends_at,
            "entry_mode": "button",
            "entrants": [],
            "ended": False,
            "created_at": discord.utils.utcnow(),
        }
        message = await ctx.reply(embed=self._embed(draft))

        result = await self.bot.database_manager.create_giveaway(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=message.id,
            host_id=ctx.author.id,
            prize=prize,
            winners=winners,
            ends_at=ends_at,
            entry_mode="button",
        )
        giveaway_id = result.inserted_id
        giveaway = await self.bot.database_manager.get_giveaway(giveaway_id)
        if giveaway is None:
            await ctx.reply("The giveaway could not be saved.")
            return

        view = GiveawayView(self, giveaway)
        await message.edit(embed=self._embed(giveaway), view=view)
        self.bot.add_view(view, message_id=message.id)

        await self.bot.timer_manager.create_timer(
            event_name="giveaway",
            expires_at=ends_at,
            metadata={"giveaway_id": str(giveaway_id)},
        )
        await ctx.reply(f"Giveaway started and ends {discord.utils.format_dt(ends_at, 'R')}.", delete_after=10)

    @giveaway.command(name="from-message", aliases=["message"])
    @commands.has_guild_permissions(manage_guild=True)
    async def giveaway_from_message(
        self,
        ctx: commands.Context[Parrot],
        message: discord.Message,
        duration: FutureTime,
        winners: commands.Range[int, 1, 20],
    ) -> None:
        """Turn the author's existing message into a reaction-only giveaway."""
        if ctx.guild is None or message.guild != ctx.guild or message.author.id != ctx.author.id:
            await ctx.reply("The message must be your own message in this server.")
            return
        if await self.bot.database_manager.get_giveaway_by_message(guild_id=ctx.guild.id, message_id=message.id):
            await ctx.reply("That message is already a giveaway.")
            return

        result = await self.bot.database_manager.create_giveaway(
            guild_id=ctx.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
            host_id=ctx.author.id,
            prize=message.content or "Giveaway",
            winners=winners,
            ends_at=duration.dt,
            entry_mode="reaction",
        )
        await message.add_reaction(GIVEAWAY_EMOJI)
        await self.bot.timer_manager.create_timer(
            event_name="giveaway",
            expires_at=duration.dt,
            metadata={"giveaway_id": str(result.inserted_id)},
        )
        await ctx.reply(f"Your message is now a giveaway and ends {discord.utils.format_dt(duration.dt, 'R')}.", delete_after=10)

    @giveaway.command(name="end")
    @commands.has_guild_permissions(manage_guild=True)
    async def end_giveaway(self, ctx: commands.Context[Parrot], giveaway_id: str) -> None:
        """End a giveaway immediately."""
        if ctx.guild is None:
            return
        object_id = self._object_id(giveaway_id)
        if object_id is None:
            await ctx.reply("That is not a valid giveaway ID.")
            return

        giveaway = await self.bot.database_manager.get_giveaway(object_id)
        if giveaway is None or giveaway["guild_id"] != ctx.guild.id or giveaway["ended"]:
            await ctx.reply("No active giveaway with that ID was found.")
            return

        giveaway = await self.bot.database_manager.end_giveaway(object_id)
        if giveaway is None:
            await ctx.reply("That giveaway has already ended.")
            return

        await self.bot.timer_manager.delete_timer(event_name="giveaway", metadata_filter={"giveaway_id": giveaway_id})
        await self._finish_giveaway(giveaway)
        await ctx.reply("Giveaway ended.", delete_after=10)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or (self.bot.user is not None and payload.user_id == self.bot.user.id) or str(payload.emoji) != GIVEAWAY_EMOJI:
            return

        giveaway = await self.bot.database_manager.get_giveaway_by_message(
            guild_id=payload.guild_id,
            message_id=payload.message_id,
        )
        if giveaway is not None and giveaway.get("entry_mode", "reaction") == "reaction" and not giveaway["ended"]:
            await self.bot.database_manager.add_giveaway_entrant(giveaway_id=giveaway["_id"], user_id=payload.user_id)

    @commands.Cog.listener()
    async def on_giveaway_timer_complete(self, metadata: dict[str, object]) -> None:
        object_id = self._object_id(str(metadata["giveaway_id"]))
        if object_id is None:
            return

        giveaway = await self.bot.database_manager.end_giveaway(object_id)
        if giveaway is not None:
            await self._finish_giveaway(giveaway)

    async def _recover_giveaway(self, giveaway_id: ObjectId) -> None:
        giveaway = await self.bot.database_manager.end_giveaway(giveaway_id)
        if giveaway is not None:
            await self._finish_giveaway(giveaway)

    async def _reroll_giveaway(self, giveaway: Giveaway) -> None:
        winners = random.sample(giveaway["entrants"], min(giveaway["winners"], len(giveaway["entrants"])))
        channel = self.bot.get_channel(giveaway["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return

        if giveaway.get("entry_mode", "reaction") == "button":
            try:
                message = await channel.fetch_message(giveaway["message_id"])
                await message.edit(embed=self._embed(giveaway, winners=winners), view=GiveawayView(self, giveaway))
            except discord.NotFound, discord.Forbidden:
                _log.warning("Could not update rerolled giveaway %s", giveaway["_id"])

        if winners:
            await channel.send(
                f"The giveaway was rerolled. Congratulations {', '.join(f'<@{user_id}>' for user_id in winners)}! You won **{giveaway['prize']}**!",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        else:
            await channel.send(f"The giveaway for **{giveaway['prize']}** still has no eligible entrants.")

    async def _finish_giveaway(self, giveaway: Giveaway) -> None:
        winners = random.sample(giveaway["entrants"], min(giveaway["winners"], len(giveaway["entrants"])))
        channel = self.bot.get_channel(giveaway["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(giveaway["message_id"])
            if giveaway.get("entry_mode", "reaction") == "button":
                await message.edit(embed=self._embed(giveaway, winners=winners), view=GiveawayView(self, giveaway))
            if winners:
                await channel.send(
                    f"Congratulations {', '.join(f'<@{user_id}>' for user_id in winners)}! You won **{giveaway['prize']}**!",
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            else:
                await channel.send(f"The giveaway for **{giveaway['prize']}** ended with no eligible entrants.")
        except discord.NotFound, discord.Forbidden:
            _log.warning("Could not finish giveaway %s in channel %s", giveaway["_id"], giveaway["channel_id"])


class GiveawayView(discord.ui.View):
    def __init__(self, cog: GiveawayCog, giveaway: Giveaway) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        giveaway_id = str(giveaway["_id"])
        enter = discord.ui.Button(
            label="Enter giveaway",
            emoji=GIVEAWAY_EMOJI,
            style=discord.ButtonStyle.success,
            custom_id=f"giveaway:enter:{giveaway_id}",
            disabled=giveaway["ended"],
        )

        enter.callback = self.enter_callback
        self.add_item(enter)


    async def enter_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        giveaway = await self.cog.bot.database_manager.get_giveaway(self._giveaway_id(interaction.data))
        if giveaway is None or giveaway["ended"]:
            await interaction.response.send_message("This giveaway has ended.", ephemeral=True)
            return

        added = await self.cog.bot.database_manager.add_giveaway_entrant(
            giveaway_id=giveaway["_id"],
            user_id=interaction.user.id,
        )
        await interaction.response.send_message("You are entered!" if added else "You are already entered.", ephemeral=True)

    async def reroll_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        giveaway = await self.cog.bot.database_manager.get_giveaway(self._giveaway_id(interaction.data))
        if giveaway is None or not giveaway["ended"]:
            await interaction.response.send_message("This giveaway has not ended yet.", ephemeral=True)
            return
        is_manager = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild
        if interaction.user.id != giveaway["host_id"] and not is_manager:
            await interaction.response.send_message("Only the giveaway host or a server manager can reroll it.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog._reroll_giveaway(giveaway)

    @staticmethod
    def _giveaway_id(data: object) -> ObjectId:
        if not isinstance(data, dict):
            raise ValueError("Missing giveaway interaction data")
        custom_id = data.get("custom_id")
        if not isinstance(custom_id, str):
            raise ValueError("Missing giveaway interaction ID")
        object_id = custom_id.rsplit(":", 1)[-1]
        parsed = GiveawayCog._object_id(object_id)
        if parsed is None:
            raise ValueError("Invalid giveaway interaction ID")
        return parsed


async def setup(bot: Parrot) -> None:
    await bot.add_cog(GiveawayCog(bot))
