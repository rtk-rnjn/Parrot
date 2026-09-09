from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Annotated

import discord
import sympy
from discord.ext import commands
from rapidfuzz import fuzz, process

from core.constants import INVITE_RE, LINKS_RE

from .events import PingMessageListner, SnipeMessageListener
from .graphing import boxplot, plotfn

if TYPE_CHECKING:
    from core.bot import Parrot

BOOKMARK_EMOJI = "\N{PUSHPIN}"

_log = logging.getLogger("bot.cogs.misc")

with open("assets/dictionary.json", encoding="utf-8") as f:
    DICTIONARY: dict[str, str] = discord.utils._from_json(f.read())


class WrappedMessageConverter(commands.MessageConverter):  # pylint: disable=too-few-public-methods
    async def convert(self, ctx: commands.Context[Parrot], argument: str) -> discord.Message:
        if argument.startswith("[") and argument.endswith("]"):
            argument = argument[1:-1]
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]

        return await super().convert(ctx, argument)


class BookmarkForm(discord.ui.Modal):
    bookmark_title = discord.ui.TextInput(
        label="Choose a title for your bookmark (optional)",
        placeholder="Type your bookmark title here",
        default="Bookmark",
        max_length=50,
        min_length=0,
        required=False,
    )

    def __init__(self, message: discord.Message) -> None:
        super().__init__(timeout=1000, title="Name your bookmark")
        self.message = message

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        title = self.bookmark_title.value or self.bookmark_title.default
        try:
            await self.dm_bookmark(interaction, self.message, title)
        except discord.Forbidden:
            await interaction.response.send_message(embed=Misc.build_error_embed("Enable your DMs to receive the bookmark."), ephemeral=True)
            return

        await interaction.response.send_message(embed=Misc.build_success_reply_embed(self.message), ephemeral=True)

    async def dm_bookmark(self, interaction: discord.Interaction[Parrot], target_message: discord.Message, title: str | None) -> None:
        embed = Misc.build_bookmark_dm(target_message, title=title)
        message_url_view = discord.ui.View().add_item(discord.ui.Button(label="View Message", url=target_message.jump_url))
        await interaction.user.send(embed=embed, view=message_url_view)


class Misc(commands.Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

        self.__bookmark_context_menu = discord.app_commands.ContextMenu(name="Bookmark", callback=self._bookmark_context_menu_callback)
        self.__interpret_as_command = discord.app_commands.ContextMenu(name="Interpret as command", callback=self._interpret_as_command)

        self.bot.tree.add_command(self.__bookmark_context_menu)
        self.bot.tree.add_command(self.__interpret_as_command)

        _log.info("Cog loaded: %s", self.__class__.__name__)

    async def _interpret_as_command(self, interaction: discord.Interaction, message: discord.Message) -> None:
        # await interaction.response.defer(thinking=False)
        if message.guild is None:
            await interaction.response.send_message(
                f"{interaction.user.mention} interpreting as command is only available in guilds.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(f"{interaction.user.mention} processing...", ephemeral=True)
        prefixes = await self.bot.get_prefix(message)
        if message.content.startswith(tuple(prefixes)):
            await interaction.edit_original_response(
                content=f"{interaction.user.mention} the command is already interpreted as command. Do you think it's an error? Please report it.",
            )
            return

        if message.author.bot:
            await interaction.edit_original_response(
                content=f"{interaction.user.mention} the message is from a bot. Can't interpret it as command.",
            )
            return
        ini = time.perf_counter()

        prefix = await self.bot.database.get_command_prefix(guild_id=message.guild.id)
        message.content = f"{prefix} {message.content.strip()}"
        message.author = interaction.user
        await self.bot.process_commands(message)

        end = time.perf_counter()
        await interaction.edit_original_response(
            content=f"{interaction.user.mention} completed command interpretation. It took {end - ini:.2f} seconds.",
        )

    @commands.command(name="bookmark", aliases=("bm", "pin"))
    async def bookmark(
        self,
        ctx: commands.Context[Parrot],
        target_message: Annotated[discord.Message | None, WrappedMessageConverter] = commands.parameter(  # noqa: B008
            description="The message to bookmark.",
            default=None,
        ),
        *,
        title: str = commands.parameter(description="The title of the bookmark.", default="Bookmark"),
    ) -> discord.Message:
        """Send the author a link to `target_message` via DMs."""
        if not target_message:
            if not ctx.message.reference:
                msg = "You must either provide a valid message to bookmark, or reply to one.\n\nThe lookup strategy for a message is as follows (in order):\n1. Lookup by '{channel ID}-{message ID}' (retrieved by shift-clicking on 'Copy ID')\n2. Lookup by message ID (the message **must** be in the context channel)\n3. Lookup by message URL"
                raise commands.BadArgument(msg)
            maybe_message = ctx.message.reference.resolved
            if isinstance(maybe_message, discord.Message):
                target_message = maybe_message

        if not target_message:
            msg = "Couldn't find that message."
            raise commands.BadArgument(msg)

        assert isinstance(target_message, discord.Message) and isinstance(ctx.author, discord.Member)

        # Prevent users from bookmarking a message in a channel they don't have access to
        permissions = target_message.channel.permissions_for(ctx.author)
        if not permissions.read_messages:
            embed = discord.Embed(title="Permission", color=ctx.author.color, description="You don't have permission to view this channel.")
            return await ctx.reply(embed=embed)

        bookmarked_users = [ctx.author.id]

        def event_check(reaction: discord.Reaction, user: discord.Member) -> bool:
            """Make sure that this reaction is what we want to operate on."""
            assert self.bot.user is not None

            return (
                # Conditions for a successful pagination:
                all(
                    (
                        # Reaction is on this message
                        reaction.message.id == reaction_message.id,
                        # User has not already bookmarked this message
                        user.id not in bookmarked_users,
                        # Reaction is the `BOOKMARK_EMOJI` emoji
                        str(reaction.emoji) == BOOKMARK_EMOJI,
                        # Reaction was not made by the Bot
                        user.id != self.bot.user.id,
                    ),
                )
            )

        assert isinstance(target_message, discord.Message)

        message = await self.action_bookmark(channel=ctx.channel, user=ctx.author, target_message=target_message, title=title)

        # Keep track of who has already bookmarked, so users can't spam reactions and cause loads of DMs
        reaction_message = await self.send_reaction_embed(ctx.channel, target_message)

        try:
            _, user = await self.bot.wait_for("reaction_add", timeout=120, check=event_check)
        except TimeoutError as e:
            await reaction_message.delete(delay=0)
            raise e

        message = await self.action_bookmark(channel=ctx.channel, user=user, target_message=target_message, title=title)
        bookmarked_users.append(user.id)

        return message

    @staticmethod
    def build_bookmark_dm(target_message: discord.Message, /, *, title: str | None = "Bookmark") -> discord.Embed:
        """Build the embed to DM the bookmark requester."""
        embed = discord.Embed(title=title, description=target_message.content)
        if target_message.attachments and target_message.attachments[0].url.endswith(("png", "jpeg", "jpg", "gif", "webp")):
            embed.set_image(url=target_message.attachments[0].url)

        embed.add_field(name="Wanna give it a visit?", value=f"[Visit original message]({target_message.jump_url})")
        embed.set_author(name=target_message.author, icon_url=target_message.author.display_avatar.url)

        return embed

    @staticmethod
    def build_success_reply_embed(target_message: discord.Message, /) -> discord.Embed:
        """Build the ephemeral reply embed to the bookmark requester."""
        return discord.Embed(
            description=(f"A bookmark for [this message]({target_message.jump_url}) has been successfully sent your way."),
            color=discord.Color.green(),
        )

    async def _bookmark_context_menu_callback(self, interaction: discord.Interaction[Parrot], message: discord.Message, /) -> None:
        """The callback that will be invoked upon using the bookmark's context menu command."""
        assert isinstance(interaction.user, discord.Member) and isinstance(interaction.channel, discord.abc.GuildChannel)
        permissions = interaction.channel.permissions_for(interaction.user)
        if not permissions.read_messages:
            embed = self.build_error_embed("You don't have permission to view this channel.")
            await interaction.response.send_message(embed=embed)
            return

        bookmark_title_form = BookmarkForm(message=message)
        await interaction.response.send_modal(bookmark_title_form)

    @staticmethod
    def build_error_embed(user: discord.Member | discord.User | str) -> discord.Embed:
        """Builds an error embed for when a bookmark requester has DMs disabled."""
        if isinstance(user, str):
            return discord.Embed(title="You DM(s) are closed!", description=user)

        return discord.Embed(title="You DM(s) are closed!", description=f"{user.mention}, please enable your DMs to receive the bookmark.")

    async def action_bookmark(
        self,
        *,
        channel: discord.abc.MessageableChannel,
        user: discord.Member | discord.User,
        target_message: discord.Message,
        title: str,
    ) -> discord.Message:
        """Sends the bookmark DM, or sends an error embed when a user bookmarks a message."""
        try:
            embed = self.build_bookmark_dm(target_message, title=title)
            return await user.send(embed=embed)
        except discord.Forbidden:
            error_embed = self.build_error_embed(user)
            return await channel.send(embed=error_embed)

    @staticmethod
    async def send_reaction_embed(channel: discord.abc.MessageableChannel, target_message: discord.Message) -> discord.Message:
        """Sends an embed, with a reaction, so users can react to bookmark the message too."""
        message = await channel.send(
            embed=discord.Embed(
                description=(f"React with {BOOKMARK_EMOJI} to be sent your very own bookmark to [this message]({target_message.jump_url})."),
            ),
        )

        await message.add_reaction(BOOKMARK_EMOJI)
        return message

    def sanitise(self, st: str) -> str:
        if len(st) > 1024:
            st = f"{st[:980]}..."
        return INVITE_RE.sub("[INVITE REDACTED]", st)

    @commands.command(name="snipe")
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def snipe_message(self, ctx: commands.Context[Parrot], index: int = 1) -> discord.Message:
        """Snipes someone's message that's deleted."""
        snipes: SnipeMessageListener = self.bot.get_cog("SnipeMessageListener")  # type: ignore

        snipe: discord.Message = snipes.get_snipe(ctx.channel, index=index)

        channel = ctx.channel

        emb = (
            discord.Embed(color=snipe.author.color, timestamp=snipe.created_at)
            .set_author(name=snipe.author, icon_url=snipe.author.display_avatar.url)
            .set_footer(
                text=f"Message sniped by {str(ctx.author)}",
                icon_url=ctx.author.display_avatar.url,
            )
        )
        if snipe.attachments:
            url = snipe.attachments[0].proxy_url
            if url.endswith(("png", "jpeg", "jpg", "gif", "webp")):
                emb.set_image(url=url)

        ref = snipe.reference.resolved if snipe.reference else None
        if LINKS_RE.fullmatch(snipe.content) and snipe.content.endswith(("png", "jpeg", "jpg", "gif", "webp")):
            if isinstance(ref, discord.Message):
                emb.description = f"Replied to: **[{ref.author}]({ref.jump_url})**"
            emb.set_image(url=snipe.content)
        elif isinstance(ref, discord.Message):
            emb.description = f"- **Replied to: [`{ref.author}`]({ref.jump_url})**\n\n{self.sanitise(snipe.content)}"

        else:
            emb.description = self.sanitise(snipe.content)

        message = await ctx.reply(embed=emb)
        snipes.delete_snipe(channel, index=index)
        return message

    @commands.command(name="editsnipe", aliases=["esnipe"])
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def edit_snipe_message(self, ctx: commands.Context[Parrot], index: int = 1) -> discord.Message:
        """Snipes someone's message that's deleted."""
        channel = ctx.channel

        snipes: SnipeMessageListener = self.bot.get_cog("SnipeMessageListener")  # type: ignore

        snipe: tuple[discord.Message, discord.Message] = snipes.get_edit_snipe(channel, index=index)

        emb = (
            discord.Embed(color=snipe[0].author.color, timestamp=snipe[0].created_at)
            .set_author(name=snipe[0].author, icon_url=snipe[0].author.display_avatar.url)
            .set_footer(
                text=f"Message sniped by {str(ctx.author)}",
                icon_url=ctx.author.display_avatar.url,
            )
        )
        if snipe[0].content and snipe[1].content:
            emb.description = f"**Before:**\n{self.sanitise(snipe[0].content)}\n\n**After:**\n{self.sanitise(snipe[1].content)}"

        message = await ctx.reply(embed=emb)
        snipes.delete_edit_snipe(channel, index=index)
        return message

    @commands.command(name="define", aliases=["dictionary", "dict"])
    async def define(self, ctx: commands.Context[Parrot], *, term: str = commands.parameter(description="The term to define.")) -> discord.Message:
        """Fetch a definition from Urban Dictionary API."""
        closest_match = process.extractOne(term.capitalize(), DICTIONARY.keys(), scorer=fuzz.ratio)
        if closest_match is None:
            return await ctx.reply(f"No definition found for '{term}'.")
        return await ctx.reply(f"**{closest_match[0]}**: {DICTIONARY[closest_match[0]]}")

    @commands.command(name="ghostping", aliases=["gp", "ghost-ping"])
    async def ghost_ping(
        self,
        ctx: commands.Context[Parrot],
    ) -> discord.Message | None:
        """Check if someone ghost pinged you."""
        cog: PingMessageListner = self.bot.get_cog("PingMessageListner")  # type: ignore
        pages = []
        for message in cog.get_ghost_pings(ctx.author.id):
            relative_dt = discord.utils.format_dt(message.created_at, style="R")
            pages.append(
                f"[{relative_dt}] {message.author} {self.sanitise(message.content)}",
            )

        if not pages:
            return await ctx.reply("You haven't been ghost pinged.")

        interface = await self.bot.paginate(ctx, embed=True, pages=pages)
        return interface.message

    @commands.command(name="boxplot", aliases=("box", "boxwhisker", "numsetdata"))
    async def _boxplot(self, ctx: commands.Context[Parrot], *numbers: float) -> None:
        """Plots the providednumber data set in a box & whisker plot

        showing Min, Max, Mean, Q1, Median and Q3.
        Numbers should be seperated by spaces per data point.
        """
        file = await boxplot(numbers)
        await ctx.reply(file=file)

    @commands.command(name="plot", aliases=("line-graph", "graph"))
    async def _plot(self, ctx: commands.Context[Parrot], *, equation: str) -> None:
        """Plots the provided equation out.
        Ex: `$plot 2x+1`.
        """
        try:
            file = await plotfn(equation)
            await ctx.reply(file=file)
        except TypeError:
            await ctx.reply("Provided equation was invalid; the only variable present must be `x`")
        except (NameError, ValueError) as e:
            await ctx.reply(f"{ctx.author.mention} Provided equation was invalid; {e}")
        except (SyntaxError, sympy.SympifyError, ZeroDivisionError) as e:
            await ctx.reply(f"{ctx.author.mention} Provided equation was invalid; check your syntax.\nError: {e}")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Misc(bot))
    await bot.add_cog(SnipeMessageListener(bot))
    await bot.add_cog(PingMessageListner(bot))
