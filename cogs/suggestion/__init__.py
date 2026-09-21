from __future__ import annotations

import io
from random import random
from typing import Annotated

import discord
from discord.ext import commands

from core import Parrot
from core.utils import DisabledButtonView

REACTION_EMOJI = ["\N{UPWARDS BLACK ARROW}", "\N{DOWNWARDS BLACK ARROW}"]

# fmt: off
OTHER_REACTION = {
    "INVALID": {"emoji": "\N{WARNING SIGN}", "color": 0xFFFFE0},
    "NOTVALIDATED": {"emoji": "\N{WARNING SIGN}", "color": 0xFFFFE0},
    "NOTVALID": {"emoji": "\N{WARNING SIGN}", "color": 0xFFFFE0},
    "NOT VALID": {"emoji": "\N{WARNING SIGN}", "color": 0xFFFFE0},

    "ABUSE": {"emoji": "\N{DOUBLE EXCLAMATION MARK}", "color": 0xFFA500},
    "SPAM": {"emoji": "\N{DOUBLE EXCLAMATION MARK}", "color": 0xFFA500},

    "INCOMPLETE": {"emoji": "\N{WHITE QUESTION MARK ORNAMENT}", "color": 0xFFFFFF},
    "NEEDINFO": {"emoji": "\N{WHITE QUESTION MARK ORNAMENT}", "color": 0xFFFFFF},
    "MOREINFO": {"emoji": "\N{WHITE QUESTION MARK ORNAMENT}", "color": 0xFFFFFF},
    "WHAT?": {"emoji": "\N{WHITE QUESTION MARK ORNAMENT}", "color": 0xFFFFFF},
    "NEED INFO": {"emoji": "\N{WHITE QUESTION MARK ORNAMENT}", "color": 0xFFFFFF},
    "MORE INFO": {"emoji": "\N{WHITE QUESTION MARK ORNAMENT}", "color": 0xFFFFFF},

    "DECLINE": {"emoji": "\N{CROSS MARK}", "color": 0xFF0000},
    "DENY": {"emoji": "\N{CROSS MARK}", "color": 0xFF0000},
    "REJECT": {"emoji": "\N{CROSS MARK}", "color": 0xFF0000},

    "APPROVED": {"emoji": "\N{WHITE HEAVY CHECK MARK}", "color": 0x90EE90},
    "OK": {"emoji": "\N{WHITE HEAVY CHECK MARK}", "color": 0x90EE90},
    "ACCEPT": {"emoji": "\N{WHITE HEAVY CHECK MARK}", "color": 0x90EE90},
    "ALRIGHT": {"emoji": "\N{WHITE HEAVY CHECK MARK}", "color": 0x90EE90},

    "DUPLICATE": {"emoji": "\N{HEAVY EXCLAMATION MARK SYMBOL}", "color": 0xDDD6D5},
    "COPY": {"emoji": "\N{HEAVY EXCLAMATION MARK SYMBOL}", "color": 0xDDD6D5},
    "SAME": {"emoji": "\N{HEAVY EXCLAMATION MARK SYMBOL}", "color": 0xDDD6D5},
}
# fmt: on


class Suggestion(commands.Cog):
    """For making the suggestion, which then then voted on by the community."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    async def get_or_fetch_message(
        self,
        thread_id: int,
        *,
        guild: discord.Guild,
    ):
        thread = guild.get_channel(thread_id)
        if not isinstance(thread, discord.Thread):
            try:
                thread = await guild.fetch_channel(thread_id)
            except discord.NotFound:
                return None

        if not isinstance(thread, discord.Thread):
            return None

        return await self.bot.get_or_fetch_message(thread, thread_id)

    async def __suggest(
        self,
        content: str | None = None,
        *,
        embed: discord.Embed,
        ctx: commands.Context[Parrot],
        file: discord.File = discord.utils.MISSING,
    ) -> discord.Message | None:
        assert ctx.guild is not None

        channel_id = await self.bot.database.get_suggestion_channel_id(guild_id=ctx.guild.id)
        channel = ctx.guild.get_channel(channel_id) if channel_id is not None else None
        if channel is None or not isinstance(channel, discord.TextChannel):
            err = f"{ctx.author.mention} error fetching suggestion channel"
            raise commands.BadArgument(err)
        file = file or discord.utils.MISSING

        msg: discord.Message = await channel.send(content, embed=embed, file=file)

        for reaction in REACTION_EMOJI:
            await ctx.message.add_reaction(reaction)

        await msg.create_thread(name=f"Suggestion {ctx.author}")

    async def __notify_on_suggestion(self, ctx: commands.Context[Parrot], *, message: discord.Message | None) -> None:
        if message is None or ctx.guild is None:
            return

        jump_url: str = message.jump_url
        content = f"{ctx.author.mention} your suggestion being posted.\n> {jump_url}"
        try:
            await ctx.author.send(
                content,
                view=DisabledButtonView(author=ctx.author, display_text=ctx.guild.name),
            )
        except discord.Forbidden:
            pass

    async def __notify_user(
        self,
        ctx: commands.Context[Parrot],
        user: discord.Member | None = None,
        *,
        message: discord.Message,
        remark: str,
    ) -> None:
        if user is None or ctx.guild is None:
            return

        remark = remark or "No remark was given"

        content = (
            f"{user.mention} your suggestion of ID: {message.id} had being updated.\n"
            f"By: {ctx.author} (`{ctx.author.id}`)\n"
            f"Remark: {remark}\n"
            f"> {message.jump_url}"
        )
        try:
            await user.send(
                content,
                view=DisabledButtonView(author=user, display_text=ctx.guild.name),
            )
        except discord.Forbidden:
            pass

    @commands.group(aliases=["suggestion"], invoke_without_command=True)
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True, create_public_threads=True)
    async def suggest(self, ctx: commands.Context[Parrot], *, suggestion: Annotated[str, commands.clean_content]):
        """Suggest something. Abuse of the command may result in required mod actions."""
        assert ctx.guild is not None

        if not ctx.invoked_subcommand:
            embed = discord.Embed(description=suggestion, timestamp=ctx.message.created_at, color=0xADD8E6)
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            embed.set_footer(
                text=f"Author ID: {ctx.author.id}",
                icon_url=getattr(ctx.guild.icon, "url", ctx.author.display_avatar.url),
            )

            file: discord.File = discord.utils.MISSING

            if ctx.message.attachments and (ctx.message.attachments[0].url.lower().endswith(("png", "jpeg", "jpg", "gif", "webp"))):
                _bytes = await ctx.message.attachments[0].read(use_cached=True)
                file = discord.File(io.BytesIO(_bytes), "image.jpg")
                embed.set_image(url="attachment://image.jpg")

            msg = await self.__suggest(ctx=ctx, embed=embed, file=file)
            await self.__notify_on_suggestion(ctx, message=msg)
            await ctx.message.delete(delay=0)

    async def clear_suggestion_embed(self, ctx: commands.Context[Parrot], message_id: int):
        """To remove all kind of notes and extra reaction from suggestion embed."""
        assert ctx.guild is not None

        msg: discord.Message | None = await self.get_or_fetch_message(message_id, guild=ctx.guild)
        if not msg:
            return await ctx.send(
                f"{ctx.author.mention} Can not find message of ID `{message_id}`. Probably already deleted, or `{message_id}` is invalid",
            )

        embed: discord.Embed = msg.embeds[0]
        embed.clear_fields()
        embed.color = 0xADD8E6
        await msg.edit(embed=embed, content=None)

        for reaction in msg.reactions:
            if str(reaction.emoji) not in REACTION_EMOJI:
                await msg.clear_reaction(reaction.emoji)
        await ctx.send(f"{ctx.author.mention} Done", delete_after=5)

    async def suggest_flag(self, ctx: commands.Context[Parrot], message_id: int, flag: str, *, remark: str = ""):
        """To flag the suggestion.

        Avalibale Flags :-
        - INVALID / NOTVALIDATED / NOTVALID / NOT VALID
        - ABUSE / SPAM
        - INCOMPLETE / NEEDINFO / MOREINFO / WHAT? / NEED INFO / MORE INFO
        - DECLINE / DENY / REJECT
        - APPROVED / OK / ACCEPT / ALRIGHT
        - DUPLICATE / COPY / SAME
        """

        assert ctx.guild is not None

        message: discord.Message | None = await self.get_or_fetch_message(message_id, guild=ctx.guild)
        if not message:
            return await ctx.send(
                f"{ctx.author.mention} Can not find message of ID `{message_id}`. Probably already deleted, or `{message_id}` is invalid",
            )

        if message.author.id != self.bot.user.id:
            return await ctx.send(f"{ctx.author.mention} Invalid `{message_id}`")

        flag = flag.upper()
        try:
            payload = OTHER_REACTION[flag]
        except KeyError:
            return await ctx.send(f"{ctx.author.mention} Invalid Flag")

        embed: discord.Embed = message.embeds[0]
        embed.color = payload["color"]

        if embed.footer.text is None:
            return await ctx.send(f"{ctx.author.mention} Invalid Suggestion Embed")

        user_id = int(embed.footer.text.split(":")[1])
        if remark:
            embed.clear_fields()
            embed.add_field(name="Remark", value=remark[:250])

        user: discord.Member | None = await self.bot.get_or_fetch_member(ctx.guild, user_id)
        await self.__notify_user(ctx, user, message=message, remark=remark)

        content = f"Flagged: {flag} | {payload['emoji']}"
        await message.edit(content=content, embed=embed)

        await ctx.send(f"{ctx.author.mention} Done", delete_after=5)

        if random() < 0.05:
            await ctx.send(
                f"{ctx.author.mention} btw, you can also flag the suggestion by replying the message with the proper FLAG.\n"
                f"Like: `INVALID > This is a remark`, `SPAM`",
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if message.author.bot or message.guild is None:
            return

        suggestion_channel_id = await self.bot.database.get_suggestion_channel_id(guild_id=message.guild.id)

        if message.channel.id != suggestion_channel_id:
            return

        if await self.__parse_mod_action(message):
            return

        context = await self.bot.get_context(message)
        if context.valid:
            return

        await self.suggest(context, suggestion=message.content)

    async def __parse_mod_action(self, message: discord.Message) -> bool | None:
        assert isinstance(message.author, discord.Member)

        if not self.__is_mod(message.author):
            return

        if ">" not in message.content:
            return

        command, remark = message.content.split(">", 1)
        command = command.strip(" ").upper()
        remark = remark.strip(" ") or ""

        if command in OTHER_REACTION:
            context = await self.bot.get_context(message)

            msg = None

            if message.reference is not None:
                msg: discord.Message | discord.DeletedReferencedMessage | None = message.reference.resolved

            if not isinstance(msg, discord.Message):
                return

            if msg.author.id != self.bot.user.id:
                return

            if command in ["CLS", "CLEAR"]:
                await self.clear_suggestion_embed(context, msg.id)
                return True

            await self.suggest_flag(context, msg.id, command, remark=remark)
            return True

    def __is_mod(self, member: discord.Member) -> bool:
        return member.guild_permissions.manage_channels and member.guild_permissions.manage_threads and member.guild_permissions.manage_messages


async def setup(bot: Parrot):
    await bot.add_cog(Suggestion(bot))
