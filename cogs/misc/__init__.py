from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import string
import time
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, BinaryIO

import arrow
import discord
import sympy
from discord.ext import commands, tasks
from jishaku.codeblocks import Codeblock, codeblock_converter
from PIL import Image
from rapidfuzz import fuzz, process

from core.constants import INVITE_RE, LINKS_RE
from core.utils import HumanDate, PaginationView

from .birthday_card import birthday_card_file
from .events import PingMessageListner, SnipeMessageListener
from .graphing import boxplot, plotfn
from .logo import LogoInterpreter, LogoParser, build_logo_guide
from .ttg import Truths, TTFlag

if TYPE_CHECKING:
    from core import Parrot

BOOKMARK_EMOJI = "\N{PUSHPIN}"
DEFAULT_AFK_REASON = "AFK"

BIRTHDAY_DATE_FORMAT = "MM-DD"

LATEX_API_URL = "https://rtex.probablyaweb.site/api/v2"

THIS_DIR = Path(__file__).parent
LATEX_CACHE_DIRECTORY = THIS_DIR / "_latex_cache"
LATEX_CACHE_DIRECTORY.mkdir(exist_ok=True)
LATEX_DOCUMENT_TEMPLATE = string.Template(r"""
\documentclass{article}
\begin{document}
    \pagenumbering{gobble}
    $text
\end{document}
""")


_log = logging.getLogger("bot.cogs.misc")


with Path("assets/dictionary.json").open(encoding="utf-8") as file:
    DICTIONARY: dict[str, str] = discord.utils._from_json(file.read())


def parse_birthday(value: str) -> str:
    return arrow.get(value).format(BIRTHDAY_DATE_FORMAT)


class InvalidLatexError(Exception):
    """Represents an error caused by invalid latex."""

    def __init__(self, logs: str | None) -> None:
        super().__init__(logs)
        self.logs = logs


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
            await interaction.response.send_message(
                embed=Misc.build_error_embed("Enable your DMs to receive the bookmark."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(embed=Misc.build_success_reply_embed(self.message), ephemeral=True)

    async def dm_bookmark(
        self,
        interaction: discord.Interaction[Parrot],
        target_message: discord.Message,
        title: str | None,
    ) -> None:
        embed = Misc.build_bookmark_dm(target_message, title=title)
        message_url_view = discord.ui.View().add_item(discord.ui.Button(label="View Message", url=target_message.jump_url))
        await interaction.user.send(embed=embed, view=message_url_view)


def _process_image(data: bytes, out_file: BinaryIO) -> None:
    PAD = 10

    image = Image.open(io.BytesIO(data)).convert("RGBA")
    width, height = image.size
    background = Image.new("RGBA", (width + 2 * PAD, height + 2 * PAD), "WHITE")
    background.paste(image, (PAD, PAD), image)
    background.save(out_file)


class Misc(commands.Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

        self._announced: set[tuple[int, str, int]] = set()

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
                content=f"{interaction.user.mention} the command is already interpreted as command. Do you think it's an error? Please report it."
            )
            return

        if message.author.bot:
            await interaction.edit_original_response(content=f"{interaction.user.mention} the message is from a bot. Can't interpret it as command.")
            return
        ini = time.perf_counter()

        prefix = await self.bot.database.get_command_prefix(guild_id=message.guild.id)
        message.content = f"{prefix} {message.content.strip()}"
        message.author = interaction.user
        await self.bot.process_commands(message)

        end = time.perf_counter()
        await interaction.edit_original_response(
            content=f"{interaction.user.mention} completed command interpretation. It took {end - ini:.2f} seconds."
        )

    @commands.command(name="bookmark", aliases=("bm", "pin"))
    async def bookmark(
        self,
        ctx: commands.Context[Parrot],
        target_message: Annotated[discord.Message | None, WrappedMessageConverter] = commands.parameter(  # noqa: B008
            description="The message to bookmark.", default=None
        ),
        *,
        title: str = commands.parameter(description="The title of the bookmark.", default="Bookmark"),
    ) -> discord.Message:
        """Send the author a link to `target_message` via DMs."""
        if not target_message:
            if not ctx.message.reference:
                msg = (
                    "You must either provide a valid message to bookmark, or reply to one.\n\n"
                    "The lookup strategy for a message is as follows (in order):\n"
                    "1. Lookup by '{channel ID}-{message ID}' (retrieved by shift-clicking on 'Copy ID')\n"
                    "2. Lookup by message ID (the message **must** be in the context channel)\n3. Lookup by message URL"
                )
                raise commands.BadArgument(msg)
            maybe_message = ctx.message.reference.resolved
            if isinstance(maybe_message, discord.Message):
                target_message = maybe_message

        if not target_message:
            msg = "Couldn't find that message."
            raise commands.BadArgument(msg)

        assert isinstance(target_message, discord.Message)
        assert isinstance(ctx.author, discord.Member)

        # Prevent users from bookmarking a message in a channel they don't have access to
        permissions = target_message.channel.permissions_for(ctx.author)
        if not permissions.read_messages:
            embed = discord.Embed(
                title="Permission",
                color=ctx.author.color,
                description="You don't have permission to view this channel.",
            )
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
                    )
                )
            )

        assert isinstance(target_message, discord.Message)

        message = await self.action_bookmark(
            channel=ctx.channel,
            user=ctx.author,
            target_message=target_message,
            title=title,
        )

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

        embed.add_field(
            name="Wanna give it a visit?",
            value=f"[Visit original message]({target_message.jump_url})",
        )
        embed.set_author(
            name=target_message.author,
            icon_url=target_message.author.display_avatar.url,
        )

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
        assert isinstance(interaction.user, discord.Member)
        assert isinstance(interaction.channel, discord.abc.GuildChannel)
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

        return discord.Embed(
            title="You DM(s) are closed!",
            description=f"{user.mention}, please enable your DMs to receive the bookmark.",
        )

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
                description=(f"React with {BOOKMARK_EMOJI} to be sent your very own bookmark to [this message]({target_message.jump_url}).")
            )
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
        snipes: SnipeMessageListener = self.bot.get_cog("SnipeMessageListener")  # pyright: ignore[reportAssignmentType]

        snipe: discord.Message = snipes.get_snipe(ctx.channel, index=index)

        channel = ctx.channel

        emb = (
            discord.Embed(color=snipe.author.color, timestamp=snipe.created_at)
            .set_author(name=snipe.author, icon_url=snipe.author.display_avatar.url)
            .set_footer(
                text=f"Message sniped by {ctx.author!s}",
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

        snipes: SnipeMessageListener = self.bot.get_cog("SnipeMessageListener")  # pyright: ignore[reportAssignmentType]

        snipe: tuple[discord.Message, discord.Message] = snipes.get_edit_snipe(channel, index=index)

        emb = (
            discord.Embed(color=snipe[0].author.color, timestamp=snipe[0].created_at)
            .set_author(name=snipe[0].author, icon_url=snipe[0].author.display_avatar.url)
            .set_footer(
                text=f"Message sniped by {ctx.author!s}",
                icon_url=ctx.author.display_avatar.url,
            )
        )
        if snipe[0].content and snipe[1].content:
            emb.description = f"**Before:**\n{self.sanitise(snipe[0].content)}\n\n**After:**\n{self.sanitise(snipe[1].content)}"

        message = await ctx.reply(embed=emb)
        snipes.delete_edit_snipe(channel, index=index)
        return message

    @commands.command(name="define", aliases=["dictionary", "dict"])
    async def define(
        self,
        ctx: commands.Context[Parrot],
        *,
        term: str = commands.parameter(description="The term to define."),
    ) -> discord.Message:
        """Fetch a definition from Urban Dictionary API."""
        closest_match = process.extractOne(term.capitalize(), DICTIONARY.keys(), scorer=fuzz.ratio)
        if closest_match is None:
            return await ctx.reply(f"No definition found for '{term}'.")
        return await ctx.reply(f"**{closest_match[0]}**: {DICTIONARY[closest_match[0]]}")

    @commands.command(name="ghostping", aliases=["gp", "ghost-ping"])
    async def ghost_ping(self, ctx: commands.Context[Parrot]) -> discord.Message | None:
        """Check if someone ghost pinged you."""
        cog: PingMessageListner = self.bot.get_cog("PingMessageListner")  # pyright: ignore[reportAssignmentType]
        pages = []
        for message in cog.get_ghost_pings(ctx.author.id):
            relative_dt = discord.utils.format_dt(message.created_at, style="R")
            pages.append(f"[{relative_dt}] {message.author} - {self.sanitise(message.content)}")

        if not pages:
            return await ctx.reply("You haven't been ghost pinged.")

        embeds: list[discord.Embed] = []
        chunks = discord.utils.as_chunks(pages, 10)
        for chunk in chunks:
            embed = discord.Embed(title="Ghost Pings", description="\n".join(chunk))
            embeds.append(embed)

        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)
        return None

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

    @commands.group(name="logo", aliases=("turtle", "turtle-graphics"), invoke_without_command=True)
    async def _logo(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: Annotated[Codeblock, codeblock_converter],
    ) -> None:
        """Interprets the provided code as Logo programming language code and returns the resulting image."""
        parser = LogoParser()
        program = parser.parse(code.content)

        interpreter = LogoInterpreter()
        await asyncio.to_thread(interpreter.execute, program)

        image_buffer = await asyncio.to_thread(interpreter.turtle.render)
        await ctx.reply(file=discord.File(image_buffer, filename="logo.png"))

    @_logo.command(name="guide", aliases=("help", "tutorial"))
    async def _logo_guide(self, ctx: commands.Context[Parrot]) -> None:
        """Sends a guide on how to use the Logo programming language."""
        embeds = build_logo_guide()
        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)

    @commands.command(aliases=["trutht", "tt", "ttable"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def truthtable(self, ctx: commands.Context[Parrot], *, flags: TTFlag):
        """A simple command to generate Truth Table of given data. Make sure you use proper syntax.

        ```
        Negation             : not, -, ~
        Logical disjunction  : or
        Logical nor          : nor
        Exclusive disjunction: xor, !=
        Logical conjunction  : and
        Logical NAND         : nand
        Material implication : =>, implies
        Logical biconditional: =
        ```
        """
        table = Truths(
            [j.strip(" ") for j in flags.var.replace(" ", "").split(",")],
            [i.strip(" ") for i in flags.con.split(",")],
            ascending=flags.ascending,
        )
        main = table.as_tabulate(index=False, table_format=flags.table_format, align=flags.align)
        if len(main) > 1900:
            await ctx.reply("The generated table is too long to display. Please try again with a smaller input.")
            return

        await ctx.reply(f"```{flags.table_format}\n{main}\n```")

    async def _generate_image(self, query: str, out_file: BinaryIO) -> None:
        """Make an API request and save the generated image to cache."""
        payload = {"code": query, "format": "png"}
        async with self.bot.http_session.post(LATEX_API_URL, data=payload, raise_for_status=True) as response:
            response_json = await response.json()
        if response_json["status"] != "success":
            raise InvalidLatexError(logs=response_json.get("log"))

        async with self.bot.http_session.get(f"{LATEX_API_URL}/{response_json['filename']}", raise_for_status=True) as response:
            await asyncio.to_thread(_process_image, await response.read(), out_file)

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
    async def latex(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: Annotated[Codeblock, codeblock_converter],
    ) -> None:
        """Renders the text in latex and sends the image."""
        query = code.content
        query_hash = hashlib.md5(query.encode()).hexdigest()  # nosec
        image_path = LATEX_CACHE_DIRECTORY / f"{query_hash}.png"
        if not image_path.exists():
            try:
                with image_path.open("wb") as out_file:
                    await self._generate_image(LATEX_DOCUMENT_TEMPLATE.substitute(text=query), out_file)
            except InvalidLatexError as err:
                embed = discord.Embed(title="Failed to render input.")
                if err.logs is None:
                    embed.description = "No logs available"

                await ctx.send(embed=embed)
                image_path.unlink()
                return
        await ctx.send(file=discord.File(image_path, "latex.png"))

    @commands.command(name="afk")
    async def afk(
        self,
        ctx: commands.Context[Parrot],
        *,
        reason: Annotated[str, commands.clean_content] = commands.parameter(description="Reason for going AFK", default=DEFAULT_AFK_REASON),
    ) -> None:
        """Set your AFK status."""

        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return

        reason = reason.strip() or DEFAULT_AFK_REASON

        await self.bot.database.set_user_as_afk(guild_id=ctx.guild.id, user_id=ctx.author.id, reason=reason)

        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        me = ctx.guild.me

        if me is not None and me.guild_permissions.manage_nicknames and me.top_role > ctx.author.top_role:
            nickname = f"[AFK] {ctx.author.display_name}"[:32]

            try:
                await ctx.author.edit(nick=nickname, reason="User marked themselves as AFK")
            except discord.HTTPException:
                _log.warning(
                    "Failed to update AFK nickname for %s (%s)",
                    ctx.author,
                    ctx.author.id,
                    exc_info=True,
                )

    @commands.Cog.listener("on_message")
    async def on_afk_message(self, message: discord.Message) -> None:
        """Handle AFK notifications and automatically remove AFK status."""

        if message.guild is None or message.author.bot:
            return

        afk_reason = await self.bot.database.get_afk_reason(guild_id=message.guild.id, user_id=message.author.id)

        mentioned_ids = {member.id for member in message.mentions if not member.bot}

        if mentioned_ids:
            afk_users = await self.bot.database.get_afk_users(guild_id=message.guild.id)

            for user_id, afk_reason in afk_users.items():
                member = message.guild.get_member(user_id)

                if member is None:
                    continue

                await message.reply(
                    f"{member.mention} is currently AFK: {afk_reason}",
                    allowed_mentions=discord.AllowedMentions.none(),
                )

        if afk_reason is None:
            return

        await self.bot.database.remove_user_from_afk(guild_id=message.guild.id, user_id=message.author.id)
        await message.reply(
            f"Welcome back, {message.author.mention}.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.group(name="birthday", invoke_without_command=True, aliases=["bday", "dob"])
    async def birthday(self, ctx: commands.Context[Parrot]) -> None:
        """View birthday status or manage your birthday."""
        if ctx.guild is None:
            return

        birthday = await self.bot.database.get_user_birthday(ctx.author.id)
        if birthday is None:
            await ctx.send_help(ctx.command)
            return

        await ctx.reply(f"Your birthday is set to **{birthday}**.")

    @birthday.command(name="set")
    async def set_birthday(self, ctx: commands.Context[Parrot], *, date: str) -> None:
        """Set your birthday."""
        try:
            birthday = parse_birthday(date)
        except ValueError:
            human_readable_date = HumanDate(date)
            datetime = human_readable_date.datetime
            birthday = parse_birthday(datetime.isoformat())

        await self.bot.database.set_user_birthday(user_id=ctx.author.id, birthday=birthday)
        await ctx.reply(f"Your birthday is set to **{birthday}**.")

    @birthday.command(name="clear")
    async def clear_birthday(self, ctx: commands.Context[Parrot]) -> None:
        """Remove your saved birthday."""
        await self.bot.database.clear_user_birthday(ctx.author.id)
        await ctx.reply("Your birthday has been cleared.")

    @tasks.loop(minutes=30)
    async def check_birthdays(self) -> None:
        today = arrow.utcnow().format(BIRTHDAY_DATE_FORMAT)
        users = await self.bot.database.get_users_with_birthdays()
        birthday_users = {user["_id"]: user for user in users if user.get("birthday") == today}

        for guild in self.bot.guilds:
            enabled = await self.bot.database.is_birthday_config_enabled(guild.id)
            if not enabled:
                continue

            channel_id = await self.bot.database.get_birthday_config_channel_id(guild.id)
            config = {"enabled": enabled, "channel_id": channel_id}

            if not config or not config["enabled"] or config["channel_id"] is None:
                continue

            channel = guild.get_channel(config["channel_id"])
            if not isinstance(channel, discord.TextChannel):
                continue

            for member in guild.members:
                announcement_key = (guild.id, today, member.id)
                if member.bot or member.id not in birthday_users or announcement_key in self._announced:
                    continue
                await self._send_wish(channel, member, today)
                self._announced.add(announcement_key)

    @check_birthdays.before_loop
    async def before_check_birthdays(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_wish(self, channel: discord.TextChannel, member: discord.Member, birthday: str) -> None:
        avatar = None
        try:
            avatar = Image.open(io.BytesIO(await member.display_avatar.read()))
        except discord.HTTPException, OSError:
            _log.debug("Could not download avatar for %s", member.id, exc_info=True)

        try:
            await channel.send(
                content=f"Happy birthday, {member.mention}!",
                file=await birthday_card_file(member.display_name, birthday, avatar),
            )
        except discord.HTTPException:
            _log.exception(
                "Could not send birthday wish for %s in guild %s",
                member.id,
                channel.guild.id,
            )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Misc(bot))
    await bot.add_cog(SnipeMessageListener(bot))
    await bot.add_cog(PingMessageListner(bot))
