from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.starboard")
DEFAULT_THRESHOLD = 3
DEFAULT_EMOJI = "\N{WHITE MEDIUM STAR}"


class Starboard(commands.Cog):
    """Collect starred messages in a dedicated channel."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.board_messages: dict[int, int] = {}
        _log.info("Cog loaded: %s", type(self).__name__)

    @commands.group(name="starboard", aliases=["startboard"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def starboard(self, ctx: commands.Context[Parrot]) -> None:
        """Configure this server's starboard."""
        if ctx.guild is None:
            return

        starboard_enabled = await self.bot.database.is_starboard_enabled(ctx.guild.id)
        if not starboard_enabled:
            await ctx.reply("Starboard is disabled.")
            return

        board_channel_id = await self.bot.database.get_starboard_board_channel_id(ctx.guild.id)
        if board_channel_id is None:
            await ctx.reply("Starboard is enabled, but no channel is set.")
            return

        channel = ctx.guild.get_channel(board_channel_id)
        if channel is None:
            await ctx.reply("Starboard is enabled, but the channel is invalid or deleted.")
            return

        threshold = await self.bot.database.get_starboard_threshold(ctx.guild.id)
        emoji = await self.bot.database.get_starboard_emoji(ctx.guild.id)

        channel_name = channel.mention
        await ctx.reply(f"The starboard is enabled in {channel_name} with a threshold of {threshold} {emoji}.")

    @starboard.command(name="set-channel", aliases=["channel"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_channel(self, ctx: commands.Context[Parrot], channel: discord.TextChannel) -> None:
        """Set the channel where starred messages are posted."""
        if ctx.guild is None:
            return

        await self.bot.database.set_starboard_board_channel(ctx.guild.id, channel.id)
        await ctx.reply(f"Starboard channel set to {channel.mention}.")

    @starboard.command(name="threshold", aliases=["limit"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_threshold(
        self,
        ctx: commands.Context[Parrot],
        threshold: commands.Range[int, 1, 20],
    ) -> None:
        """Set how many stars a message needs to reach the starboard."""
        if ctx.guild is None:
            return

        await self.bot.database.set_starboard_threshold(guild_id=ctx.guild.id, threshold=threshold)
        await ctx.reply(f"Starboard threshold set to {threshold}.")

    @starboard.command(name="emoji", aliases=["emote"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_emoji(self, ctx: commands.Context[Parrot], *, emoji: str) -> None:
        """Set the native or custom emoji used for starboard reactions."""
        if ctx.guild is None:
            return

        emote = discord.PartialEmoji.from_str(emoji)
        if emote.is_custom_emoji() and ctx.guild.get_emoji(emote.id) is None: # pyright: ignore[reportArgumentType]
            await ctx.reply("That custom emoji is not available in this server.")
            return

        await self.bot.database.set_starboard_emoji(guild_id=ctx.guild.id, emoji=emoji)
        await ctx.reply(f"Starboard emoji set to {emoji}.")

    @starboard.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    async def disable(self, ctx: commands.Context[Parrot]) -> None:
        """Disable the starboard for this server."""
        if ctx.guild is None:
            return

        await self.bot.database.disable_starboard(ctx.guild.id)
        await ctx.reply("Starboard disabled.")

    @starboard.command(name="enable")
    @commands.has_guild_permissions(manage_guild=True)
    async def enable(self, ctx: commands.Context[Parrot]) -> None:
        """Enable the starboard for this server."""
        if ctx.guild is None:
            return

        await self.bot.database.enable_starboard(ctx.guild.id)
        await ctx.reply("Starboard enabled.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self._update_board(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self._update_board(payload)

    async def _update_board(self, payload: discord.RawReactionActionEvent) -> None:  # noqa: PLR0911
        if payload.guild_id is None or (self.bot.user is not None and payload.user_id == self.bot.user.id):
            return

        is_starboard_enabled = await self.bot.database.is_starboard_enabled(payload.guild_id)
        if not is_starboard_enabled:
            return

        emoji = await self.bot.database.get_starboard_emoji(payload.guild_id)
        threshold = await self.bot.database.get_starboard_threshold(payload.guild_id)
        channel_id = await self.bot.database.get_starboard_board_channel_id(payload.guild_id)
        config = {
            "enabled": is_starboard_enabled,
            "emoji": emoji,
            "threshold": threshold,
            "channel_id": channel_id,
        }

        if config is None or not config["enabled"] or str(payload.emoji) != config["emoji"]:
            return
        if payload.channel_id == config["channel_id"]:
            return

        source_channel = self.bot.get_channel(payload.channel_id)
        board_channel = self.bot.get_channel(config["channel_id"])
        if not isinstance(source_channel, discord.TextChannel) or not isinstance(board_channel, discord.TextChannel):
            return

        source_message = await self._fetch_source_message(source_channel, payload.message_id)
        if source_message is None:
            return

        reaction = next((reaction for reaction in source_message.reactions if str(reaction.emoji) == config["emoji"]), None)
        count = reaction.count if reaction else 0
        board_message_id = await self.bot.database.get_starboard_board_message(payload.guild_id, source_message.id)

        if count < config["threshold"]:
            if board_message_id is not None:
                await self._delete_board_message(board_channel, payload.guild_id, source_message.id, board_message_id)
            return

        await self._upsert_board_message(
            board_channel,
            source_message,
            board_message_id,
            f"{config['emoji']} **{count}**",
        )

    @staticmethod
    async def _fetch_source_message(channel: discord.TextChannel, message_id: int) -> discord.Message | None:
        try:
            return await channel.fetch_message(message_id)
        except discord.Forbidden, discord.NotFound:
            return None

    async def _upsert_board_message(
        self,
        channel: discord.TextChannel,
        source_message: discord.Message,
        board_message_id: int | None,
        content: str,
    ) -> None:
        assert source_message.guild is not None
        embed = self._build_embed(source_message)
        if board_message_id is not None:
            try:
                board_message = await self.bot.get_or_fetch_message(channel, board_message_id)
                await board_message.edit(content=content, embed=embed)
                return
            except discord.Forbidden, discord.NotFound:
                await self.bot.database.delete_starboard_board_message(
                    guild_id=source_message.guild.id,
                    source_message_id=source_message.id,
                )

        try:
            board_message = await channel.send(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            _log.warning("Cannot post to starboard channel %s", channel.id)
            return

        await self.bot.database.set_starboard_board_message(
            guild_id=source_message.guild.id,
            source_message_id=source_message.id,
            board_message_id=board_message.id,
        )

    async def _delete_board_message(self, channel: discord.TextChannel, guild_id: int, source_id: int, board_id: int) -> None:
        try:
            board_message = await channel.fetch_message(board_id)
            await board_message.delete()
        except discord.Forbidden, discord.NotFound:
            pass
        finally:
            await self.bot.database.delete_starboard_board_message(
                guild_id=guild_id,
                source_message_id=source_id,
            )

    @staticmethod
    def _build_embed(message: discord.Message) -> discord.Embed:
        embed = discord.Embed(description=message.content[:4096], colour=discord.Colour.gold(), timestamp=message.created_at)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Source message: {message.id}")
        embed.add_field(name="Jump to message", value=f"[Open message]({message.jump_url})")
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
        return embed


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Starboard(bot))
