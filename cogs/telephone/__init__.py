from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from rapidfuzz import fuzz, process

if TYPE_CHECKING:
    from core import Parrot


class Telephone(commands.Cog):
    """Ever thought to talk to your friends in a different server? Well, now you can!"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    async def _find_line_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel_id = await self.bot.database.get_telephone_channel_id(guild_id=guild.id)
        if channel_id is None:
            return None
        return discord.utils.get(guild.text_channels, id=channel_id)

    @staticmethod
    def _call_check(channels: tuple[discord.abc.MessageableChannel, ...]):
        def check(message: discord.Message) -> bool:
            return not message.author.bot and message.channel in channels and message.content.casefold() in {"pickup", "hangup"}

        return check

    async def _clear_busy_lines(self, guild_ids: tuple[int, int]) -> None:
        await asyncio.gather(
            *(self.bot.database.clear_telephone_line_busy(guild_id=guild_id) for guild_id in guild_ids),
        )

    async def _relay_call(
        self,
        ctx: commands.Context[Parrot],
        target_channel: discord.TextChannel,
        target_guild: discord.Guild,
    ) -> None:
        await ctx.send(
            f"\N{TELEPHONE RECEIVER} **Connected. Say {random.choice(('hi', 'hello', 'heya'))}!**",
        )
        await target_channel.send(
            f"\N{TELEPHONE RECEIVER} **Connected. Say {random.choice(('hi', 'hello', 'heya'))}!**",
        )

        channels = (ctx.channel, target_channel)

        def check(message: discord.Message) -> bool:
            return not message.author.bot and message.channel in channels

        try:
            while True:
                message = await self.bot.wait_for("message", check=check, timeout=120)

                if message.content.casefold() == "hangup":
                    await ctx.send("\N{TELEPHONE RECEIVER} **Disconnected.**")
                    await target_channel.send("\N{TELEPHONE RECEIVER} **Disconnected.**")
                    return

                content = discord.utils.escape_mentions(message.content[:1000])
                destination = target_channel if message.channel == ctx.channel else ctx.channel
                await destination.send(f"**{message.author}** {content}")

        except TimeoutError:
            assert ctx.guild is not None
            await ctx.send(
                f"\N{SLEEPING SYMBOL} Disconnected from **{target_guild.name}**. Reason: Line inactive for more than 120 seconds.",
            )
            await target_channel.send(
                f"\N{SLEEPING SYMBOL} Disconnected from **{ctx.guild.name}**. Reason: Line inactive for more than 120 seconds.",
            )

    async def _dial(self, ctx: commands.Context[Parrot], target_guild: discord.Guild) -> None:
        assert ctx.guild is not None

        if target_guild.id == ctx.guild.id:
            await ctx.send("\N{CROSS MARK} **Can't make a self call.**")
            return

        caller_id = ctx.guild.id
        target_id = target_guild.id

        if not await self.bot.database.is_telephone_enabled(guild_id=caller_id) or not await self.bot.database.is_telephone_enabled(
            guild_id=target_id,
        ):
            await ctx.send(
                "\N{CROSS MARK} **Calling failed!** Telephone is disabled in one of these servers.",
            )
            return

        caller_blocked = await self.bot.database.telephone_config_get_blocked_servers(
            guild_id=caller_id,
        )
        target_blocked = await self.bot.database.telephone_config_get_blocked_servers(
            guild_id=target_id,
        )

        if target_id in caller_blocked or caller_id in target_blocked:
            await ctx.send(
                "\N{NO ENTRY SIGN} **Calling failed!** One of these servers has blocked the other.",
            )
            return

        if await self.bot.database.is_telephone_line_busy(guild_id=caller_id) or await self.bot.database.is_telephone_line_busy(guild_id=target_id):
            await ctx.send(
                f"\N{TELEPHONE RECEIVER} Cannot connect to **{target_guild.name}**. **Line busy!**",
            )
            return

        target_channel = await self._find_line_channel(target_guild)

        if target_channel is None:
            await ctx.send(
                "\N{CROSS MARK} **Calling failed!** The target server has no writable text channel.",
            )
            return

        await asyncio.gather(
            self.bot.database.set_telephone_line_busy(guild_id=caller_id, busy=True),
            self.bot.database.set_telephone_line_busy(guild_id=target_id, busy=True),
        )

        try:
            await ctx.send(
                f"\N{TELEPHONE RECEIVER} Calling **{target_guild.name}** ... Waiting for the response ...",
            )

            await target_channel.send(
                f"\N{TELEPHONE RECEIVER} **Incoming call from {ctx.guild.name} ({ctx.guild.id})**\n`pickup` to pickup | `hangup` to reject",
            )

            response: discord.Message | None = None

            try:
                response = await self.bot.wait_for(
                    "message",
                    check=self._call_check((ctx.channel, target_channel)),
                    timeout=60,
                )
            except TimeoutError:
                await ctx.send(
                    f"\N{SLEEPING SYMBOL} Line disconnected from **{target_guild.name}**. Reason: Line inactive for more than 60 seconds.",
                )
                await target_channel.send(
                    f"\N{SLEEPING SYMBOL} Line disconnected from **{ctx.guild.name}**. Reason: Line inactive for more than 60 seconds.",
                )

            if response is not None:
                if response.content.casefold() == "hangup":
                    await ctx.send(
                        f"\N{TELEPHONE RECEIVER} Disconnected. From **{response.author}**.",
                    )
                    await target_channel.send(
                        f"\N{TELEPHONE RECEIVER} Disconnected. From **{response.author}**.",
                    )
                else:
                    await self._relay_call(ctx, target_channel, target_guild)

        finally:
            await self._clear_busy_lines((caller_id, target_id))

    def _search_guild(self, server: str) -> discord.Guild | None:
        """Searches for a guild by name using fuzzy matching."""
        if server.isdigit():
            guild = self.bot.get_guild(int(server))
            if guild:
                return guild

        guilds = {guild.name: guild for guild in self.bot.guilds}
        match, score, _ = process.extractOne(server, guilds.keys(), scorer=fuzz.ratio)

        if score >= 80:
            return guilds[match]

        return None

    @commands.group(name="telephone", aliases=["phone", "tel", "call"])
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    async def telephone(self, ctx: commands.Context[Parrot], *, server: str) -> None:
        """Starts a game of telephone in the specified server."""
        assert ctx.guild is not None

        target_guild = self._search_guild(server)

        if target_guild is None:
            await ctx.send(
                f":mag: Bot couldn't find a server matching **{server}**.",
            )
            return

        await self._dial(ctx, target_guild)

    @telephone.command(name="enable", aliases=["on"])
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx: commands.Context[Parrot]) -> None:
        """Enables the telephone game in the server."""
        assert ctx.guild is not None

        await self.bot.database.enable_telephone(guild_id=ctx.guild.id)
        await ctx.send(":white_check_mark: **The telephone game has been enabled!**")

    @telephone.command(name="disable", aliases=["off"])
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx: commands.Context[Parrot]) -> None:
        """Disables the telephone game in the server."""
        assert ctx.guild is not None

        await self.bot.database.disable_telephone(guild_id=ctx.guild.id)
        await ctx.send(":white_check_mark: **The telephone game has been disabled!**")

    @telephone.command(name="setchannel", aliases=["setchan", "channel"])
    @commands.has_permissions(administrator=True)
    async def set_channel(
        self,
        ctx: commands.Context[Parrot],
        *,
        channel: discord.TextChannel = commands.parameter(  # noqa: B008
            description="The text channel to set for the telephone game.",
            default=lambda ctx: ctx.channel if isinstance(ctx.channel, discord.TextChannel) else None,
        ),
    ) -> None:
        """Sets the channel for the telephone game in the server."""
        assert ctx.guild is not None

        await self.bot.database.set_telephone_channel_id(
            guild_id=ctx.guild.id,
            channel_id=channel.id,
        )
        await ctx.send(
            f":white_check_mark: The telephone game channel has been set to {channel.mention}!",
        )

    @telephone.command(name="block", aliases=["ban"])
    @commands.has_permissions(administrator=True)
    async def block(self, ctx: commands.Context[Parrot], *, server: str) -> None:
        """Blocks a server from calling the telephone game."""
        assert ctx.guild is not None

        target_guild = self._search_guild(server)

        if target_guild is None or target_guild.id == ctx.guild.id:
            await ctx.send(
                f"\N{CROSS MARK} I couldn't find another server matching **{server}**.",
            )
            return

        await self.bot.database.telephone_config_add_blocked_server(
            guild_id=ctx.guild.id,
            server_id=target_guild.id,
        )

        await ctx.send(
            f"\N{NO ENTRY SIGN} The server **{target_guild.name}** has been blocked from calling the telephone game!",
        )

    @telephone.command(name="unblock", aliases=["unban"])
    @commands.has_permissions(administrator=True)
    async def unblock(self, ctx: commands.Context[Parrot], *, server: str) -> None:
        """Unblocks a server from calling the telephone game."""
        assert ctx.guild is not None

        target_guild = self._search_guild(server)

        if target_guild is None or target_guild.id == ctx.guild.id:
            await ctx.send(
                f"\N{CROSS MARK} I couldn't find another server matching **{server}**.",
            )
            return

        await self.bot.database.telephone_config_remove_blocked_server(
            guild_id=ctx.guild.id,
            server_id=target_guild.id,
        )

        await ctx.send(
            f":white_check_mark: The server **{target_guild.name}** has been unblocked!",
        )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Telephone(bot))
