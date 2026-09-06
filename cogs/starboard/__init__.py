from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.starboard")
DEFAULT_THRESHOLD = 3
DEFAULT_EMOJI = "⭐"


class Starboard(commands.Cog):
    """Collect starred messages in a dedicated channel."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.board_messages: dict[int, int] = {}
        _log.info("Cog loaded: %s", type(self).__name__)

    @commands.group(name="starboard", aliases=["startboard"], invoke_without_command=True)
    @commands.guild_only()
    async def starboard(self, ctx: commands.Context[Parrot]) -> None:
        """Configure this server's starboard."""
        if ctx.guild is None:
            return

        config = await self.bot.database_manager.get_starboard_config(ctx.guild.id)
        if config is None or not config["enabled"]:
            await ctx.reply("The starboard is disabled.")
            return

        channel = ctx.guild.get_channel(config["channel_id"])
        channel_name = channel.mention if isinstance(channel, discord.TextChannel) else f"<#{config['channel_id']}>"
        await ctx.reply(f"The starboard is enabled in {channel_name} with a threshold of {config['threshold']} {config['emoji']}.")

    @starboard.command(name="set-channel", aliases=["channel"])
    @commands.has_guild_permissions(manage_guild=True)
    async def set_channel(self, ctx: commands.Context[Parrot], channel: discord.TextChannel) -> None:
        """Set the channel where starred messages are posted."""
        if ctx.guild is None:
            return

        current = await self.bot.database_manager.get_starboard_config(ctx.guild.id)
        await self.bot.database_manager.edit_starboard_config(
            guild_id=ctx.guild.id,
            enabled=True,
            channel_id=channel.id,
            threshold=current["threshold"] if current else DEFAULT_THRESHOLD,
            emoji=current["emoji"] if current else DEFAULT_EMOJI,
        )
        await ctx.reply(f"Starboard channel set to {channel.mention}.")

    @starboard.command(name="threshold")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_threshold(
        self,
        ctx: commands.Context[Parrot],
        threshold: commands.Range[int, 1, 20],
    ) -> None:
        """Set how many stars a message needs to reach the starboard."""
        if ctx.guild is None:
            return

        config = await self.bot.database_manager.get_starboard_config(ctx.guild.id)
        if config is None or not config["enabled"]:
            await ctx.reply("Set a starboard channel first.")
            return

        await self.bot.database_manager.edit_starboard_config(guild_id=ctx.guild.id, threshold=threshold)
        await ctx.reply(f"Starboard threshold set to {threshold} stars.")

    @starboard.command(name="emoji")
    @commands.has_guild_permissions(manage_guild=True)
    async def set_emoji(self, ctx: commands.Context[Parrot], *, emoji: str) -> None:
        """Set the native or custom emoji used for starboard reactions."""
        if ctx.guild is None:
            return

        config = await self.bot.database_manager.get_starboard_config(ctx.guild.id)
        if config is None or not config["enabled"]:
            await ctx.reply("Set a starboard channel first.")
            return

        emoji = emoji.strip()
        if not emoji:
            await ctx.reply("Provide a native or custom emoji.")
            return

        parsed_emoji = discord.PartialEmoji.from_str(emoji)
        stored_emoji = str(parsed_emoji) if parsed_emoji is not None else emoji
        await self.bot.database_manager.edit_starboard_config(guild_id=ctx.guild.id, emoji=stored_emoji)
        await ctx.reply(f"Starboard emoji set to {stored_emoji}.")

    @starboard.command(name="disable")
    @commands.has_guild_permissions(manage_guild=True)
    async def disable(self, ctx: commands.Context[Parrot]) -> None:
        """Disable the starboard for this server."""
        if ctx.guild is None:
            return

        await self.bot.database_manager.edit_starboard_config(guild_id=ctx.guild.id, enabled=False)
        await ctx.reply("Starboard disabled.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self._update_board(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self._update_board(payload)

    async def _update_board(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or (self.bot.user is not None and payload.user_id == self.bot.user.id):
            return

        config = await self.bot.database_manager.get_starboard_config(payload.guild_id)
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
        board_message_id = await self.bot.database_manager.get_starboard_board_message(payload.guild_id, source_message.id)

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
                board_message = await channel.fetch_message(board_message_id)
                await board_message.edit(content=content, embed=embed)
                return
            except discord.Forbidden, discord.NotFound:
                await self.bot.database_manager.delete_starboard_board_message(
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

        await self.bot.database_manager.set_starboard_board_message(
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
            await self.bot.database_manager.delete_starboard_board_message(
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
