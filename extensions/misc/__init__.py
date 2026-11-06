from __future__ import annotations

import asyncio
import contextlib
import datetime
import http as std_http
import io
import ipaddress
import itertools
import logging
import math
import os
import random
import re
import socket
import ssl
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Annotated
from urllib.parse import quote, urlparse

import aiohttp
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
from .chemistry import Chemistry
from .constants import HTTP_STATUS_CODES, LANGUAGE_CODES, TRANSLATE_API, TRANSLATE_HEADERS, TRANSLATION_FLAG_MAP
from .dictionary_parser import build_definition_embed
from .events import PingMessageListner, SnipeMessageListener
from .graphing import boxplot, plotfn
from .logo import LogoError, LogoInterpreter, LogoParser, build_logo_guide
from .news import NEWS_API_KEY, NEWS_CATEGORIES, NewsError, NewsView, fetch_news
from .ttg import Truths, TTFlag
from .weather import Weather

if TYPE_CHECKING:
    from core import Bot

BOOKMARK_EMOJI = "\N{PUSHPIN}"
DEFAULT_AFK_REASON = "AFK"

BIRTHDAY_DATE_FORMAT = "MM-DD"

_log = logging.getLogger(__name__)
EMBED_FIELD_LIMIT = 1024
DISCORD_MESSAGE_LIMIT = 1900
WORKER = Path(__file__).with_name("latex_worker.py")
MAX_INPUT_LEN = 500
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
RENDER_TIMEOUT = 10  # seconds
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")
USER_AGENT = "DiscordBot/1.0 (+https://discord.com)"

with (Path("assets") / "dictionary.json").open(encoding="utf-8") as file:
    DICTIONARY: dict[str, str] = discord.utils._from_json(file.read())

ANAGRAM_INDEX: dict[str, list[str]] = {}
for _word in DICTIONARY:
    _clean = _word.strip().lower()
    if _clean.isalpha():
        ANAGRAM_INDEX.setdefault("".join(sorted(_clean)), []).append(_word)

TAROT_DECK: list[tuple[str, str, str]] = [
    ("0 - The Fool", "New beginnings, innocence, spontaneity, a free spirit", "Holding back, recklessness, risk-taking"),
    ("I - The Magician", "Manifestation, resourcefulness, power, inspired action", "Manipulation, poor planning, untapped talents"),
    (
        "II - The High Priestess",
        "Intuition, sacred knowledge, divine feminine, the subconscious mind",
        "Secrets, disconnected from intuition, withdrawal",
    ),
    ("III - The Empress", "Femininity, beauty, nature, nurturing, abundance", "Creative block, dependence on others"),
    ("IV - The Emperor", "Authority, establishment, structure, a father figure", "Domination, excessive control, lack of discipline"),
    ("V - The Hierophant", "Spiritual wisdom, religious beliefs, conformity, tradition", "Personal beliefs, freedom, challenging the status quo"),
    ("VI - The Lovers", "Love, harmony, relationships, values alignment, choices", "Self-love, disharmony, imbalance, misalignment of values"),
    ("VII - The Chariot", "Control, willpower, success, action, determination", "Self-discipline, opposition, lack of direction"),
    ("VIII - Strength", "Strength, courage, persuasion, influence, compassion", "Inner strength, self-doubt, low energy, raw emotion"),
    ("IX - The Hermit", "Soul-searching, introspection, being alone, inner guidance", "Isolation, loneliness, withdrawal"),
    ("X - Wheel of Fortune", "Good luck, karma, life cycles, destiny, a turning point", "Bad luck, resistance to change, breaking cycles"),
    ("XI - Justice", "Justice, fairness, truth, cause and effect, law", "Unfairness, lack of accountability, dishonesty"),
    ("XII - The Hanged Man", "Pause, surrender, letting go, new perspectives", "Delays, resistance, stalling, indecision"),
    ("XIII - Death", "Endings, change, transformation, transition", "Resistance to change, personal transformation, inner purging"),
    ("XIV - Temperance", "Balance, moderation, patience, purpose", "Imbalance, excess, self-healing, Re-alignment"),
    (
        "XV - The Devil",
        "Shadow self, attachment, addiction, restriction, sexuality",
        "Releasing limiting beliefs, exploring dark thoughts, detachment",
    ),
    ("XVI - The Tower", "Sudden change, upheaval, chaos, revelation, awakening", "Personal transformation, fear of change, averting disaster"),
    ("XVII - The Star", "Hope, faith, purpose, renewal, spirituality", "Lack of faith, despair, self-trust, disconnection"),
    ("XVIII - The Moon", "Illusion, fear, anxiety, subconscious, intuition", "Release of fear, repressed emotion, inner confusion"),
    ("XIX - The Sun", "Positivity, fun, warmth, success, vitality", "Inner child, feeling down, overly optimistic"),
    ("XX - Judgement", "Judgement, rebirth, inner calling, absolution", "Self-doubt, inner critic, ignoring the call"),
    ("XXI - The World", "Completion, integration, accomplishment, travel", "Seeking personal closure, short-cuts, delays"),
]

ROMAN_NUMERAL_MAP: list[tuple[str, int]] = [
    ("M", 1000),
    ("CM", 900),
    ("D", 500),
    ("CD", 400),
    ("C", 100),
    ("XC", 90),
    ("L", 50),
    ("XL", 40),
    ("X", 10),
    ("IX", 9),
    ("V", 5),
    ("IV", 4),
    ("I", 1),
]
ROMAN_REGEX = re.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$", re.IGNORECASE)

ANILIST_QUERY = """
query ($search: String, $type: MediaType) {
  Media (search: $search, type: $type) {
    id
    title {
      romaji
      english
      native
    }
    format
    status
    description(asHtml: false)
    episodes
    chapters
    volumes
    averageScore
    genres
    siteUrl
    coverImage {
      large
      color
    }
    startDate {
      year
      month
      day
    }
  }
}
"""


def int_to_roman(n: int) -> str:
    if not 1 <= n <= 3999:
        msg = "Number must be between 1 and 3999."
        raise ValueError(msg)
    result = []
    for numeral, value in ROMAN_NUMERAL_MAP:
        count, n = divmod(n, value)
        result.append(numeral * count)
    return "".join(result)


def roman_to_int(s: str) -> int:
    s = s.strip().upper()
    if not s or not ROMAN_REGEX.match(s):
        msg = "Invalid Roman numeral."
        raise ValueError(msg)
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(s):
        curr = values[char]
        if curr < prev:
            total -= curr
        else:
            total += curr
        prev = curr
    return total


def calculate_moon_phase(dt: datetime.datetime) -> tuple[str, str, float, float]:
    """Return (phase_name, emoji, illumination_pct, age_days)."""
    ref = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.UTC)
    synodic_month = 29.53058867
    days = (dt - ref).total_seconds() / 86400.0
    age = days % synodic_month
    frac = age / synodic_month
    illumination = (1 - math.cos(2 * math.pi * frac)) / 2 * 100

    phases = [
        (1.84566, "New Moon", "\N{NEW MOON SYMBOL}"),
        (5.53699, "Waxing Crescent", "\N{WAXING CRESCENT MOON SYMBOL}"),
        (9.22831, "First Quarter", "\N{FIRST QUARTER MOON SYMBOL}"),
        (12.91963, "Waxing Gibbous", "\N{WAXING GIBBOUS MOON SYMBOL}"),
        (16.61096, "Full Moon", "\N{FULL MOON SYMBOL}"),
        (20.30228, "Waning Gibbous", "\N{WANING GIBBOUS MOON SYMBOL}"),
        (23.99361, "Last Quarter", "\N{LAST QUARTER MOON SYMBOL}"),
        (27.68493, "Waning Crescent", "\N{WANING CRESCENT MOON SYMBOL}"),
        (synodic_month, "New Moon", "\N{NEW MOON SYMBOL}"),
    ]
    for limit, name, emoji in phases:
        if age < limit:
            return name, emoji, illumination, age
    return "New Moon", "\N{NEW MOON SYMBOL}", illumination, age


def is_public_host(hostname: str) -> bool:
    """Validate that a hostname does not resolve to private or loopback IP space."""
    if not hostname or hostname.lower() == "localhost":
        return False
    try:
        ip = ipaddress.ip_address(hostname)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved)
    except ValueError:
        return True


def fetch_ssl_cert(hostname: str, port: int = 443) -> dict:
    ctx = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=8) as sock, ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
        cert = ssock.getpeercert()
        cipher = ssock.cipher()
        version = ssock.version()
        return {"cert": cert or {}, "cipher": cipher, "version": version}


async def query_whois_server(server: str, query: str) -> str:
    reader, writer = await asyncio.wait_for(asyncio.open_connection(server, 43), timeout=8)
    try:
        writer.write(f"{query}\r\n".encode())
        await writer.drain()
        data = await asyncio.wait_for(reader.read(65536), timeout=8)
        return data.decode("utf-8", errors="replace")
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


def parse_birthday(value: str) -> str:
    return arrow.get(value).format(BIRTHDAY_DATE_FORMAT)


class LatexError(Exception):
    """Error whose message is safe to show to users."""


def validate_latex(latex: str) -> str:
    latex = latex.strip()
    if not latex:
        msg = "LaTeX input cannot be empty."
        raise LatexError(msg)
    if len(latex) > MAX_INPUT_LEN:
        msg = f"Input too long (max {MAX_INPUT_LEN} characters)."
        raise LatexError(msg)
    if _CONTROL.search(latex):
        msg = "Input contains invalid characters."
        raise LatexError(msg)
    if "$" in latex:
        msg = "Don't include `$`; the equation is already in math mode."
        raise LatexError(msg)
    return " ".join(latex.split())  # collapse newlines/whitespace


class WrappedMessageConverter(commands.MessageConverter):  # pylint: disable=too-few-public-methods
    async def convert(self, ctx: commands.Context[Bot], argument: str) -> discord.Message:
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

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
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
        interaction: discord.Interaction[Bot],
        target_message: discord.Message,
        title: str | None,
    ) -> None:
        embed = Misc.build_bookmark_dm(target_message, title=title)
        message_url_view = discord.ui.View().add_item(discord.ui.Button(label="View Message", url=target_message.jump_url))
        await interaction.user.send(embed=embed, view=message_url_view)


class Misc(commands.Cog, name="Miscellaneous"):
    """Utility commands that do not belong to a bigger feature."""

    help_emoji = "\N{TOOLBOX}"

    def __init__(self, bot: Bot):
        self.bot = bot

        self._announced: set[tuple[int, str, int]] = set()

        self.__bookmark_context_menu = discord.app_commands.ContextMenu(name="Bookmark", callback=self._bookmark_context_menu_callback)
        self.__interpret_as_command = discord.app_commands.ContextMenu(name="Interpret as command", callback=self._interpret_as_command)

        self.bot.tree.add_command(self.__bookmark_context_menu)
        self.bot.tree.add_command(self.__interpret_as_command)

        self.translate_user_limit = commands.CooldownMapping(commands.Cooldown(3, 15), lambda user_id: user_id)
        self.translate_message_limit = commands.CooldownMapping(commands.Cooldown(1, 60), lambda key: key)

        _log.debug("Cog loaded: %s", self.__class__.__name__)

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

    @commands.command(name="bookmark", aliases=["bm", "pin"])
    async def bookmark(
        self,
        ctx: commands.Context[Bot],
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

    async def _bookmark_context_menu_callback(self, interaction: discord.Interaction[Bot], message: discord.Message, /) -> None:
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
        if len(st) > EMBED_FIELD_LIMIT:
            st = f"{st[:980]}..."
        return INVITE_RE.sub("[INVITE REDACTED]", st)

    @commands.command(name="snipe")
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def snipe_message(
        self,
        ctx: commands.Context[Bot],
        *,
        index: int = commands.parameter(description="Index of the message to snipe, with 1 being the most recent.", default=1),
    ) -> discord.Message:
        """Snipes someone's message that's deleted.

        This command is used to retrieve the most recently deleted message in a channel.
        You can specify the index of the message to snipe, with 1 being the most recent, 2 being the second most recent, and so on.
        """
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
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def edit_snipe_message(
        self,
        ctx: commands.Context[Bot],
        *,
        index: int = commands.parameter(description="Index of the message to snipe, with 1 being the most recent.", default=1),
    ) -> discord.Message:
        """Snipes someone's message that's deleted.

        This command is used to retrieve the most recently edited message in a channel.
        You can specify the index of the message to snipe, with 1 being the most recent, 2 being the second most recent, and so on.
        """
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
        ctx: commands.Context[Bot],
        *,
        term: str = commands.parameter(description="The term to define."),
    ) -> discord.Message:
        """Fetch a definition from Oxford Dictionary."""
        await ctx.typing()

        show_definition_button = discord.ui.Button(label="Show raw definition", style=discord.ButtonStyle.secondary)

        try:
            definition = DICTIONARY[term.capitalize()]

            async def callback(interaction: discord.Interaction[Bot]) -> None:
                await interaction.response.send_message(definition, ephemeral=True)

            show_definition_button.callback = callback

            view = discord.ui.View()
            view.add_item(show_definition_button)

            return await ctx.reply(embed=build_definition_embed(term.capitalize(), definition), view=view)
        except KeyError:
            pass

        matches = process.extract(term.capitalize(), DICTIONARY.keys(), scorer=fuzz.ratio)
        if not matches:
            return await ctx.reply(f"No definition found for '{term}'.")

        embeds: list[discord.Embed] = []

        for match in matches:
            embed = build_definition_embed(match[0], DICTIONARY[match[0]])
            embeds.append(embed)

        pagination_view = PaginationView(author=ctx.author, items=embeds)
        pagination_view.add_item(show_definition_button)

        async def callback(interaction: discord.Interaction[Bot]) -> None:
            await interaction.response.send_message(DICTIONARY[matches[pagination_view.current_index][0]], ephemeral=True)

        show_definition_button.callback = callback

        return await pagination_view.start(ctx)

    @commands.command(name="ghostping", aliases=["gp", "ghost-ping"])
    async def ghost_ping(self, ctx: commands.Context[Bot]) -> discord.Message | None:
        """Check if someone ghost pinged you."""
        cog: PingMessageListner = self.bot.get_cog("PingMessageListner")  # pyright: ignore[reportAssignmentType]
        pages = []
        for message in cog.get_ghost_pings(ctx.author.id):
            relative_dt = discord.utils.format_dt(message.created_at, style="R")
            pages.append(f"[{relative_dt}] {message.author}: {self.sanitise(message.content)}")

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

    @commands.command(name="boxplot", aliases=["box", "boxwhisker", "numsetdata"])
    async def _boxplot(self, ctx: commands.Context[Bot], *numbers: float) -> None:
        """Plots the providednumber data set in a box & whisker plot

        showing Min, Max, Mean, Q1, Median and Q3.
        Numbers should be seperated by spaces per data point.
        """
        file = await boxplot(numbers)
        await ctx.reply(file=file)

    @commands.command(name="plot", aliases=["line-graph", "graph"])
    async def _plot(
        self,
        ctx: commands.Context[Bot],
        *,
        equation: str = commands.parameter(description="The equation to plot. Use `x` as the variable."),
    ) -> None:
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

    @commands.group(name="logo", aliases=["turtle", "turtle-graphics"], invoke_without_command=True)
    async def turtle(self, ctx: commands.Context[Bot]) -> None:
        """Interprets the provided code as Logo programming language code and returns the resulting image."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @turtle.command(name="run", aliases=["execute", "eval", "evaluate", "draw"])
    async def turtle_run(
        self,
        ctx: commands.Context[Bot],
        *,
        code: Annotated[Codeblock, codeblock_converter] = commands.parameter(description="The code to interpret as Logo programming language code."),  # noqa: B008
    ) -> None:
        """Interprets the provided code as Logo programming language code and returns the resulting image."""
        clean_code = code.content.strip()

        try:
            ast = LogoParser().parse(clean_code)

            interpreter = LogoInterpreter()
            interpreter.execute(ast)
        except LogoError as e:
            await ctx.reply(f"Error: {e}")
            return

        image_buffer = await asyncio.to_thread(interpreter.turtle.render)
        file = discord.File(image_buffer, filename="turtle.png")
        output = ""
        omitted = False

        for i, op in enumerate(interpreter.output):
            line = f"{op}\n"
            notice = "[Output omitted]"

            if i >= 20:
                omitted = True
                break

            if len(output) + len(line) + len(notice) > DISCORD_MESSAGE_LIMIT:
                omitted = True
                break

            output += line

        if omitted:
            output += "[Output omitted]"

        if not output:
            output = "No output generated."

        embed = discord.Embed(title="Turtle Output")
        embed.set_image(url="attachment://turtle.png")
        await ctx.reply(file=file, content=output, embed=embed)

    @turtle.command(name="animate", aliases=["gif", "draw-gif"])
    async def turtle_animate(
        self,
        ctx: commands.Context[Bot],
        *,
        code: Annotated[Codeblock, codeblock_converter] = commands.parameter(description="The code to interpret as Logo programming language code."),  # noqa: B008
    ) -> None:
        """Interprets the provided code as Logo programming language code and returns the resulting animated GIF."""
        clean_code = code.content.strip()

        try:
            ast = LogoParser().parse(clean_code)

            interpreter = LogoInterpreter()
            interpreter.execute(ast)
        except LogoError as e:
            await ctx.reply(f"Error: {e}")
            return

        image_buffer = await asyncio.to_thread(interpreter.turtle.render_gif)
        file = discord.File(image_buffer, filename="turtle.gif")
        output = ""
        omitted = False

        for i, op in enumerate(interpreter.output):
            line = f"{op}\n"
            notice = "[Output omitted]"

            if i >= 20:
                omitted = True
                break

            if len(output) + len(line) + len(notice) > DISCORD_MESSAGE_LIMIT:
                omitted = True
                break

            output += line

        if omitted:
            output += "[Output omitted]"

        if not output:
            output = "No output generated."

        embed = discord.Embed(title="Turtle Output")
        embed.set_image(url="attachment://turtle.gif")
        await ctx.reply(file=file, content=output, embed=embed)

    @turtle.command(name="guide", aliases=["help", "tutorial"])
    async def turtle_guide(self, ctx: commands.Context[Bot]) -> None:
        """Sends a guide on how to use the Logo programming language."""
        embeds = build_logo_guide()
        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)

    @commands.command(aliases=["trutht", "tt", "ttable"])
    async def truthtable(
        self,
        ctx: commands.Context[Bot],
        *,
        flags: TTFlag = commands.parameter(description="The expression and variables to evaluate"),  # noqa: B008
    ):
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
        if len(main) > DISCORD_MESSAGE_LIMIT:
            await ctx.reply("The generated table is too long to display. Please try again with a smaller input.")
            return

        await ctx.reply(f"```{flags.table_format}\n{main}\n```")

    async def render_latex(self, latex: str) -> bytes:
        latex = validate_latex(latex)

        with tempfile.TemporaryDirectory(prefix=f"{self.bot.user.name}-mplconfig-") as mpl_config_dir:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-I",
                str(WORKER),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={"MPLCONFIGDIR": mpl_config_dir, "PATH": "/usr/bin:/bin"},
            )
            try:
                out, _ = await asyncio.wait_for(proc.communicate(latex.encode()), timeout=RENDER_TIMEOUT)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                msg = "Rendering took too long."
                raise LatexError(msg) from None

        if proc.returncode == 3:
            msg = "That equation is too large to render."
            raise LatexError(msg)
        if proc.returncode != 0 or not out.startswith(b"\x89PNG"):
            msg = "Couldn't render that LaTeX. Check your syntax."
            raise LatexError(msg)
        if len(out) > MAX_OUTPUT_BYTES:
            msg = "The rendered image is too large."
            raise LatexError(msg)
        return out

    @commands.command(name="latex", aliases=["tex"], extras={"examples": [r"latex \frac{-b \pm \sqrt{b^2-4ac}}{2a}"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(2, commands.BucketType.guild, wait=False)
    async def latex(
        self,
        ctx: commands.Context[Bot],
        *,
        code: Annotated[Codeblock, codeblock_converter] = commands.parameter(  # noqa: B008
            description="The LaTeX source, optionally inside a code block"
        ),
    ) -> None:
        """Renders the text in latex and sends the image."""
        async with ctx.typing():
            try:
                png = await self.render_latex(code.content)
            except LatexError as exc:
                await ctx.reply(
                    str(exc),
                    mention_author=False,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return

        await ctx.reply(
            file=discord.File(io.BytesIO(png), filename="equation.png"),
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.command(name="afk")
    async def afk(
        self,
        ctx: commands.Context[Bot],
        *,
        reason: Annotated[str, commands.clean_content] = commands.parameter(description="Reason for going AFK", default=DEFAULT_AFK_REASON),
    ) -> None:
        """Set your AFK status.

        AFK status will be automatically removed when you send a message in the server.
        """

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
    async def birthday(self, ctx: commands.Context[Bot]) -> None:
        """View birthday status or manage your birthday."""
        if ctx.guild is None:
            return

        birthday = await self.bot.database.get_user_birthday(ctx.author.id)
        if birthday is None:
            await ctx.send_help(ctx.command)
            return

        await ctx.reply(f"Your birthday is set to **{birthday}**.")

    @birthday.command(name="set")
    async def set_birthday(self, ctx: commands.Context[Bot], *, date: str = commands.parameter(description="Your birthday, e.g. 14 October")) -> None:
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
    async def clear_birthday(self, ctx: commands.Context[Bot]) -> None:
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

    @commands.command(name="news", aliases=["headlines"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def news(
        self,
        ctx: commands.Context,
        *,
        topic: str = commands.parameter(description="The topic to search for.", default="general"),
    ) -> None:
        """Fetches the latest news articles from the News API.

        If a topic is provided, it will fetch news related to that topic.

        Available topics include: business, entertainment, general, health, science, sports, technology.
        """
        if not NEWS_API_KEY:
            await ctx.reply("The news command isn't set up right now.")
            return

        topic = topic.strip()
        if topic and topic.casefold() in NEWS_CATEGORIES:
            topic = topic.casefold()
        else:
            embed = discord.Embed(
                title="Invalid News Category",
                description=f"The topic '{topic}' is not a valid news category. Please select a valid category from the list below.",  # noqa: S608
                color=discord.Color.red(),
            )
            topic = await self.bot.disambiguate(
                ctx,
                matches=NEWS_CATEGORIES,
                entry=lambda e: e.capitalize(),
                embed=embed,
            )

        try:
            async with ctx.typing():
                articles = await fetch_news(topic=topic, session=self.bot.http_session)
        except NewsError as exc:
            ctx.command.reset_cooldown(ctx) if ctx.command else None
            await ctx.reply(str(exc))
            return

        if not articles:
            await ctx.reply("Couldn't find any news for that. No articles were returned from the News API.")
            return

        view = NewsView(ctx, topic, articles)
        view.message = await ctx.reply(view=view)

    async def google_translate(self, text: str, to: str) -> tuple[str, str] | None:
        translated = ""
        source = "auto"
        try:
            async with self.bot.http_session.get(
                TRANSLATE_API,
                params=[
                    ("dj", "1"),
                    ("dt", "sp"),
                    ("dt", "t"),
                    ("dt", "ld"),
                    ("dt", "bd"),
                    ("client", "dict-chrome-ex"),
                    ("sl", "auto"),
                    ("tl", to),
                    ("q", text[:1000]),
                ],
                headers=TRANSLATE_HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    source = str(data.get("src") or "auto")
                    translated = "".join(sentence.get("trans", "") for sentence in data.get("sentences") or [])
        except aiohttp.ClientError, TimeoutError, ValueError, AttributeError, TypeError:
            return None
        return (source, translated) if translated.strip() else None

    @commands.command(name="translate", aliases=["tr"])
    async def translate(
        self,
        ctx: commands.Context[Bot],
        to: str = commands.parameter(description="The language code to translate to, e.g. 'en' for English.", default="en"),
        *,
        text: str | None = commands.parameter(
            description="The text to translate. If not provided, the command will attempt to translate the message being replied to.",
            default=None,
        ),
    ) -> None:
        """Translate text into another language, English by default.

        Reply to a message to translate it, or type the text yourself.
        Put a language code first to pick the target, e.g. translate hi Hello.
        """

        languages = LANGUAGE_CODES

        if to.lower() not in languages:
            text = f"{to} {text}" if text else to
            to = "en"
        to = to.lower()

        if not text:
            reference = ctx.message.reference
            if reference is not None:
                message = reference.resolved
                if not isinstance(message, discord.Message) and reference.message_id is not None:
                    try:
                        message = await ctx.fetch_message(reference.message_id)
                    except discord.HTTPException:
                        message = None
                if isinstance(message, discord.Message):
                    text = message.content

        if not text or not text.strip():
            await ctx.reply("There is nothing to translate. Give me some text or reply to a message.", mention_author=False)
            return

        bucket = self.translate_message_limit.get_bucket(ctx.author.id)
        if bucket is None:
            await ctx.reply("Translation is not available right now. Please try again later.", mention_author=False)
            return

        retry = bucket.update_rate_limit()
        if retry:
            raise commands.CommandOnCooldown(self.translate_user_limit._cooldown, retry, commands.BucketType.user)  # pyright: ignore[reportArgumentType]

        async with ctx.typing():
            result = await self.google_translate(text, to)

        if result is None:
            await ctx.reply("I couldn't translate that right now. Try again later.", mention_author=False)
            return

        source, translated = result
        await ctx.reply(
            f"-# {source} \N{RIGHTWARDS ARROW} {to}\n{translated}"[:2000],
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        target = TRANSLATION_FLAG_MAP.get(str(payload.emoji))
        if (
            target is None
            or (payload.member is not None and payload.member.bot)
            or (self.bot.user is not None and payload.user_id == self.bot.user.id)
        ):
            return

        translation_user_bucket = self.translate_user_limit.get_bucket(payload.user_id)
        translation_message_bucket = self.translate_message_limit.get_bucket((payload.message_id, target))
        if (
            translation_user_bucket is None
            or translation_message_bucket is None
            or translation_user_bucket.update_rate_limit()
            or translation_message_bucket.update_rate_limit()
        ):
            return

        try:
            channel = self.bot.get_partial_messageable(payload.channel_id, guild_id=payload.guild_id)
            message = await self.bot.get_or_fetch_message(channel, payload.message_id)
        except discord.HTTPException:
            return

        if not message.content.strip():
            return

        result = await self.google_translate(message.content, target)
        if result is None or result[0] == target:
            return

        source, translated = result
        try:
            await message.reply(
                f"-# {source} \N{RIGHTWARDS ARROW} {target}\n{translated}"[:2000],
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            return

    @commands.command(name="rhyme", aliases=["rhymes"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def rhyme(
        self,
        ctx: commands.Context[Bot],
        *,
        word: str = commands.parameter(description="The word to find rhymes for."),
    ) -> None:
        """Find words that rhyme with the given word using Datamuse."""
        word = word.strip()
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    "https://api.datamuse.com/words",
                    params={"rel_rhy": word, "max": 60},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Failed to fetch rhymes right now.")
                        return
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to connect to the rhyme service.")
                return

        if not data:
            await ctx.reply(f"No rhymes found for **{discord.utils.escape_markdown(word)}**.")
            return

        words = [item["word"] for item in data if "word" in item]
        embed = discord.Embed(
            title=f"Words that rhyme with '{word}'",
            description=", ".join(words)[:4000],
            color=discord.Color.blurple(),
        )
        await ctx.reply(embed=embed)

    @commands.command(name="synonyms", aliases=["synonym", "syn", "thesaurus"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def synonyms(
        self,
        ctx: commands.Context[Bot],
        *,
        word: str = commands.parameter(description="The word to find synonyms and antonyms for."),
    ) -> None:
        """Find synonyms and antonyms for a given word."""
        word = word.strip()
        async with ctx.typing():
            try:
                async with (
                    self.bot.http_session.get(
                        "https://api.datamuse.com/words",
                        params={"rel_syn": word, "max": 35},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as syn_resp,
                    self.bot.http_session.get(
                        "https://api.datamuse.com/words",
                        params={"rel_ant": word, "max": 20},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as ant_resp,
                ):
                    syns = await syn_resp.json() if syn_resp.status == 200 else []
                    ants = await ant_resp.json() if ant_resp.status == 200 else []
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to connect to the thesaurus service.")
                return

        if not syns and not ants:
            await ctx.reply(f"No synonyms or antonyms found for **{discord.utils.escape_markdown(word)}**.")
            return

        embed = discord.Embed(title=f"Thesaurus: {word.capitalize()}", color=discord.Color.blurple())
        if syns:
            embed.add_field(
                name="Synonyms",
                value=", ".join(item["word"] for item in syns)[:1024],
                inline=False,
            )
        if ants:
            embed.add_field(
                name="Antonyms",
                value=", ".join(item["word"] for item in ants)[:1024],
                inline=False,
            )
        await ctx.reply(embed=embed)

    @commands.command(name="anagram", aliases=["anagrams", "unscramble"])
    async def anagram(
        self,
        ctx: commands.Context[Bot],
        *,
        letters: str = commands.parameter(description="The letters or word to solve anagrams for."),
    ) -> None:
        """Find valid dictionary anagrams and sub-anagrams from given letters."""
        cleaned = "".join(c.lower() for c in letters if c.isalpha())
        if not cleaned or len(cleaned) > 15:
            await ctx.reply("Please provide between 1 and 15 alphabetical characters.")
            return

        key = "".join(sorted(cleaned))
        exact_matches = sorted(set(ANAGRAM_INDEX.get(key, [])))

        sub_matches: set[str] = set()
        if len(cleaned) <= 9:
            for length in range(len(cleaned) - 1, max(2, len(cleaned) - 3), -1):
                for comb in set(itertools.combinations(key, length)):
                    sub_key = "".join(comb)
                    if sub_key in ANAGRAM_INDEX:
                        sub_matches.update(ANAGRAM_INDEX[sub_key])

        sub_list = sorted(sub_matches - set(exact_matches), key=lambda w: (-len(w), w))

        if not exact_matches and not sub_list:
            await ctx.reply(f"No anagrams found for `{cleaned}`.")
            return

        embed = discord.Embed(title=f"Anagrams for '{letters}'", color=discord.Color.green())
        if exact_matches:
            embed.add_field(
                name=f"Exact Matches ({len(exact_matches)})",
                value=", ".join(exact_matches)[:1024],
                inline=False,
            )
        if sub_list:
            embed.add_field(
                name=f"Sub-anagrams ({len(sub_list)})",
                value=", ".join(sub_list[:50])[:1024],
                inline=False,
            )
        await ctx.reply(embed=embed)

    @commands.command(name="grammar", aliases=["grammarcheck", "proofread"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def grammar(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str | None = commands.parameter(
            description="The text to check for grammar and spelling.",
            default=None,
        ),
    ) -> None:
        """Check grammar and spelling using LanguageTool. Reply to a message or provide text."""
        if not text and ctx.message.reference:
            ref = ctx.message.reference.resolved
            if isinstance(ref, discord.Message):
                text = ref.content

        if not text or not text.strip():
            await ctx.reply("Please provide text to check or reply to a message.")
            return

        text = text.strip()[:1500]
        async with ctx.typing():
            try:
                async with self.bot.http_session.post(
                    "https://api.languagetool.org/v2/check",
                    data={"text": text, "language": "auto"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Grammar check service is currently unavailable.")
                        return
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to reach the grammar checking service.")
                return

        matches = data.get("matches", [])
        if not matches:
            embed = discord.Embed(
                title="Grammar Check",
                description="\N{WHITE HEAVY CHECK MARK} No grammar or spelling issues found!",
                color=discord.Color.green(),
            )
            await ctx.reply(embed=embed)
            return

        corrected = list(text)
        lines: list[str] = []
        for match in reversed(matches):
            offset = match.get("offset", 0)
            length = match.get("length", 0)
            replacements = match.get("replacements", [])
            if replacements:
                best = replacements[0]["value"]
                corrected[offset : offset + length] = list(best)

        for match in matches[:10]:
            msg = match.get("message", "Issue detected")
            offset = match.get("offset", 0)
            length = match.get("length", 0)
            snippet = text[offset : offset + length]
            reps = [r["value"] for r in match.get("replacements", [])[:3]]
            rep_str = f" \N{RIGHTWARDS ARROW} `{', '.join(reps)}`" if reps else ""
            lines.append(f"• `{snippet}`: {msg}{rep_str}")

        embed = discord.Embed(
            title=f"Grammar Check ({len(matches)} issue{'s' if len(matches) != 1 else ''})",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Suggested Text", value="".join(corrected)[:1024], inline=False)
        embed.add_field(name="Details", value="\n".join(lines)[:1024], inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="wotd", aliases=["wordoftheday"])
    async def word_of_the_day(self, ctx: commands.Context[Bot]) -> None:
        """Display the Word of the Day from the dictionary."""
        today_str = arrow.utcnow().format("YYYY-MM-DD")
        rng = random.Random(today_str)
        keys = list(DICTIONARY.keys())
        word = rng.choice(keys)
        definition = DICTIONARY[word]
        embed = build_definition_embed(word, definition)
        embed.title = f"\N{OPEN BOOK} Word of the Day ({today_str}): {word}"
        await ctx.reply(embed=embed)

    @commands.command(name="ip", aliases=["iplookup", "geoip"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ip_lookup(
        self,
        ctx: commands.Context[Bot],
        target: str = commands.parameter(description="The IP address or domain to look up."),
    ) -> None:
        """Look up geolocation and network info for an IP address or domain."""
        target = target.strip()
        if not is_public_host(target):
            await ctx.reply("Please provide a valid public IP address or domain.")
            return

        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    f"http://ip-api.com/json/{quote(target)}",
                    params={"fields": "status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to query IP information service.")
                return

        if data.get("status") != "success":
            await ctx.reply(f"Lookup failed: {data.get('message', 'Unknown error')}.")
            return

        location = ", ".join(filter(None, [data.get("city"), data.get("regionName"), data.get("country")]))

        embed = (
            discord.Embed(
                title=f"IP Lookup: {data.get('query', target)}",
                color=discord.Color.blue(),
            )
            .add_field(name="Location", value=location or "Unknown", inline=True)
            .add_field(name="Coordinates", value=f"{data.get('lat')}, {data.get('lon')}", inline=True)
            .add_field(name="Timezone", value=data.get("timezone") or "Unknown", inline=True)
            .add_field(name="ISP", value=data.get("isp") or "Unknown", inline=True)
            .add_field(name="Organization", value=data.get("org") or "Unknown", inline=True)
            .add_field(name="ASN", value=data.get("as") or "Unknown", inline=False)
        )
        await ctx.reply(embed=embed)

    @commands.command(name="dns", aliases=["dig", "nslookup"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def dns_lookup(
        self,
        ctx: commands.Context[Bot],
        domain: str = commands.parameter(description="The domain name to query."),
        record_type: str = commands.parameter(description="Record type (A, AAAA, MX, TXT, NS, CNAME) or 'ALL'.", default="ALL"),
    ) -> None:
        """Perform a DNS lookup for a domain using Cloudflare DNS-over-HTTPS."""
        domain = domain.strip().lower()
        record_type = record_type.strip().upper()
        valid_types = ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA"]
        types_to_query = valid_types if record_type == "ALL" else [record_type]

        if any(t not in valid_types for t in types_to_query):
            await ctx.reply(f"Unsupported record type. Choose from: `{', '.join(valid_types)}` or `ALL`.")
            return

        embed = discord.Embed(title=f"DNS Records for {domain}", color=discord.Color.teal())
        async with ctx.typing():
            for rtype in types_to_query:
                try:
                    async with self.bot.http_session.get(
                        "https://cloudflare-dns.com/dns-query",
                        params={"name": domain, "type": rtype},
                        headers={"Accept": "application/dns-json"},
                        timeout=aiohttp.ClientTimeout(total=8),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json(content_type=None)
                        answers = data.get("Answer", [])
                        if answers:
                            values = [f"`{ans.get('data')}` (TTL {ans.get('TTL')}s)" for ans in answers[:10]]
                            embed.add_field(name=rtype, value="\n".join(values)[:1024], inline=False)
                except aiohttp.ClientError, TimeoutError:
                    continue

        if not embed.fields:
            await ctx.reply(f"No DNS records found for **{discord.utils.escape_markdown(domain)}**.")
            return

        await ctx.reply(embed=embed)

    @commands.command(name="whois")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def whois_lookup(
        self,
        ctx: commands.Context[Bot],
        domain: str = commands.parameter(description="The domain or IP to query via WHOIS."),
    ) -> None:
        """Perform a WHOIS lookup for a domain or IP address."""
        domain = urlparse(domain).netloc or domain.strip().lower().split("/")[0]
        if not domain or not is_public_host(domain):
            await ctx.reply("Please provide a valid public domain or IP.")
            return

        async with ctx.typing():
            try:
                iana_resp = await query_whois_server("whois.iana.org", domain)
                refer_match = re.search(r"refer:\s*(\S+)", iana_resp, re.IGNORECASE)
                whois_server = refer_match.group(1) if refer_match else "whois.verisign-grs.com"
                raw_whois = await query_whois_server(whois_server, domain)
            except Exception as exc:
                await ctx.reply(f"WHOIS lookup failed: {exc}")
                return

        important_keys = (
            "Domain Name",
            "Registrar",
            "Creation Date",
            "Updated Date",
            "Registry Expiry Date",
            "Registrar Registration Expiration Date",
            "Name Server",
            "Domain Status",
            "Registrant Organization",
            "OrgName",
            "NetRange",
            "CIDR",
        )
        extracted: list[str] = []
        seen: set[str] = set()
        for line in raw_whois.splitlines():
            line_s = line.strip()
            if any(line_s.lower().startswith(k.lower() + ":") for k in important_keys) and line_s not in seen:
                seen.add(line_s)
                extracted.append(line_s)

        summary = "\n".join(extracted[:25]) if extracted else raw_whois[:1800]
        embed = discord.Embed(
            title=f"WHOIS: {domain}",
            description=f"```yaml\n{summary[:1900]}\n```",
            color=discord.Color.dark_blue(),
        )
        embed.set_footer(text=f"Server: {whois_server}")
        await ctx.reply(embed=embed)

    @commands.command(name="ssl", aliases=["cert", "sslcheck"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ssl_lookup(
        self,
        ctx: commands.Context[Bot],
        hostname: str = commands.parameter(description="The hostname to inspect SSL certificate for."),
    ) -> None:
        """Inspect the SSL/TLS certificate of a domain."""
        hostname = urlparse(hostname).netloc or hostname.strip().split("/")[0]
        hostname = hostname.split(":")[0]
        if not hostname or not is_public_host(hostname):
            await ctx.reply("Please provide a valid public hostname.")
            return

        async with ctx.typing():
            try:
                info = await asyncio.to_thread(fetch_ssl_cert, hostname)
            except Exception as exc:
                await ctx.reply(f"Could not retrieve SSL certificate for `{hostname}`: {exc}")
                return

        cert = info["cert"]
        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))
        not_before = cert.get("notBefore", "Unknown")
        not_after = cert.get("notAfter", "Unknown")
        sans = [val for _, val in cert.get("subjectAltName", [])]

        embed = (
            discord.Embed(title=f"SSL Certificate: {hostname}", color=discord.Color.green())
            .add_field(name="Common Name (CN)", value=subject.get("commonName", hostname), inline=True)
            .add_field(name="Issuer", value=issuer.get("organizationName") or issuer.get("commonName") or "Unknown", inline=True)
            .add_field(name="Protocol / Cipher", value=f"{info['version']} ({info['cipher'][0] if info['cipher'] else 'Unknown'})", inline=True)
            .add_field(name="Valid From", value=not_before, inline=True)
            .add_field(name="Valid Until", value=not_after, inline=True)
        )
        if sans:
            embed.add_field(name=f"Subject Alt Names ({len(sans)})", value=", ".join(sans[:15])[:1024], inline=False)

        await ctx.reply(embed=embed)

    @commands.command(name="isup", aliases=["updown", "pingweb", "statuscheck"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def website_up_check(
        self,
        ctx: commands.Context[Bot],
        url: str = commands.parameter(description="The URL or domain to check."),
    ) -> None:
        """Check whether a website is up or down and measure response latency."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        if not parsed.hostname or not is_public_host(parsed.hostname):
            await ctx.reply("Please provide a valid public URL.")
            return

        async with ctx.typing():
            start = time.perf_counter()
            try:
                async with self.bot.http_session.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True,
                ) as resp:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    status = resp.status
                    final_url = str(resp.url)
            except Exception as exc:
                embed = discord.Embed(
                    title=f"\N{LARGE RED CIRCLE} {parsed.hostname} appears to be DOWN",
                    description=f"Error: `{exc}`",
                    color=discord.Color.red(),
                )
                await ctx.reply(embed=embed)
                return

        is_ok = 200 <= status < 400
        color = discord.Color.green() if is_ok else discord.Color.orange()
        icon = "\N{LARGE GREEN CIRCLE}" if is_ok else "\N{LARGE YELLOW CIRCLE}"
        embed = (
            discord.Embed(
                title=f"{icon} {parsed.hostname} is UP",
                color=color,
            )
            .add_field(name="HTTP Status", value=f"`{status}`", inline=True)
            .add_field(name="Response Time", value=f"`{elapsed_ms:.0f} ms`", inline=True)
            .add_field(name="Final URL", value=final_url, inline=False)
        )
        await ctx.reply(embed=embed)

    @commands.command(name="screenshot", aliases=["ss", "webshot"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def screenshot_url(
        self,
        ctx: commands.Context[Bot],
        url: str = commands.parameter(description="The website URL to screenshot."),
    ) -> None:
        """Capture a screenshot of a public website URL."""
        url = url.strip("<> ")
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        if not parsed.hostname or not is_public_host(parsed.hostname):
            await ctx.reply("Please provide a valid public website URL.")
            return

        screenshot_endpoint = f"https://image.thum.io/get/width/1280/crop/800/noanimate/{url}"
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    screenshot_endpoint,
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply(f"Failed to capture screenshot (HTTP {resp.status}).")
                        return
                    img_bytes = await resp.read()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Timed out while capturing the website screenshot.")
                return

        file = discord.File(io.BytesIO(img_bytes), filename="screenshot.png")
        embed = discord.Embed(title=f"Screenshot: {parsed.hostname}", url=url, color=discord.Color.blurple())
        embed.set_image(url="attachment://screenshot.png")
        await ctx.reply(embed=embed, file=file)

    @commands.command(name="moon", aliases=["moonphase"])
    async def moon_phase(
        self,
        ctx: commands.Context[Bot],
        *,
        date: str | None = commands.parameter(description="Optional date (YYYY-MM-DD) to check moon phase for.", default=None),
    ) -> None:
        """Calculate the current moon phase, illumination, and lunar age."""
        try:
            target_dt = arrow.get(date).datetime if date else datetime.datetime.now(datetime.UTC)
        except Exception:
            await ctx.reply("Invalid date format. Try `YYYY-MM-DD`.")
            return

        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=datetime.UTC)

        phase_name, emoji, illumination, age = calculate_moon_phase(target_dt)
        embed = (
            discord.Embed(
                title=f"{emoji} Moon Phase: {phase_name}",
                color=discord.Color.dark_gold(),
                timestamp=target_dt,
            )
            .add_field(name="Illumination", value=f"`{illumination:.1f}%`", inline=True)
            .add_field(name="Lunar Age", value=f"`{age:.1f} days`", inline=True)
            .add_field(name="Next Full Moon", value=f"In `{(14.765 - age) % 29.53:.1f} days`", inline=True)
        )
        await ctx.reply(embed=embed)

    @commands.command(name="sun", aliases=["sunrise", "sunset", "daylight"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def sunrise_sunset(
        self,
        ctx: commands.Context[Bot],
        *,
        location: str = commands.parameter(description="City, address, or 'lat, lon' coordinates."),
    ) -> None:
        """Fetch sunrise, sunset, solar noon, and day length for a location."""
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": location, "format": "json", "limit": 1},
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as geo_resp:
                    geo_data = await geo_resp.json()
                    if not geo_data:
                        await ctx.reply(f"Could not find coordinates for **{discord.utils.escape_markdown(location)}**.")
                        return
                    lat = geo_data[0]["lat"]
                    lon = geo_data[0]["lon"]
                    display_name = geo_data[0]["display_name"]

                async with self.bot.http_session.get(
                    "https://api.sunrise-sunset.org/json",
                    params={"lat": lat, "lng": lon, "formatted": 0},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as sun_resp:
                    sun_data = await sun_resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to retrieve solar data right now.")
                return

        if sun_data.get("status") != "OK":
            await ctx.reply("Could not calculate sunrise/sunset times for that location.")
            return

        res = sun_data["results"]
        sunrise_dt = arrow.get(res["sunrise"]).datetime
        sunset_dt = arrow.get(res["sunset"]).datetime
        noon_dt = arrow.get(res["solar_noon"]).datetime
        day_len = int(res["day_length"])
        hours, remainder = divmod(day_len, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = (
            discord.Embed(
                title=f"\N{SUNRISE OVER MOUNTAINS} Solar Times: {display_name[:180]}",
                color=discord.Color.gold(),
            )
            .add_field(name="Sunrise", value=discord.utils.format_dt(sunrise_dt, style="t"), inline=True)
            .add_field(name="Sunset", value=discord.utils.format_dt(sunset_dt, style="t"), inline=True)
            .add_field(name="Solar Noon", value=discord.utils.format_dt(noon_dt, style="t"), inline=True)
            .add_field(name="Day Length", value=f"`{hours}h {minutes}m {seconds}s`", inline=True)
            .add_field(name="Coordinates", value=f"`{float(lat):.4f}, {float(lon):.4f}`", inline=True)
        )
        await ctx.reply(embed=embed)

    @commands.command(name="iss", aliases=["issloc", "spacestation"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def iss_location(self, ctx: commands.Context[Bot]) -> None:
        """Track the current real-time position and velocity of the International Space Station."""
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    "https://api.wheretheiss.at/v1/satellites/25544",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Could not fetch ISS telemetry at the moment.")
                        return
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to reach the ISS tracking service.")
                return

        lat = data.get("latitude", 0.0)
        lon = data.get("longitude", 0.0)
        alt = data.get("altitude", 0.0)
        vel = data.get("velocity", 0.0)
        vis = str(data.get("visibility", "unknown")).capitalize()
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        embed = (
            discord.Embed(
                title="\N{SATELLITE} International Space Station (ISS) Live Tracker",
                description=f"[View current ground point on Google Maps]({maps_url})",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.fromtimestamp(data.get("timestamp", time.time()), tz=datetime.UTC),
            )
            .add_field(name="Latitude", value=f"`{lat:.4f}°`", inline=True)
            .add_field(name="Longitude", value=f"`{lon:.4f}°`", inline=True)
            .add_field(name="Altitude", value=f"`{alt:.2f} km`", inline=True)
            .add_field(name="Velocity", value=f"`{vel:,.2f} km/h`", inline=True)
            .add_field(name="Visibility", value=f"`{vis}`", inline=True)
        )
        await ctx.reply(embed=embed)

    @commands.command(name="launches", aliases=["rocket", "rockets", "spacelaunch"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def rocket_launches(self, ctx: commands.Context[Bot]) -> None:
        """View upcoming orbital rocket launches around the world."""
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    "https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
                    params={"limit": 5},
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Rocket launch schedule service is currently busy or unavailable.")
                        return
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to fetch upcoming rocket launches.")
                return

        results = data.get("results", [])
        if not results:
            await ctx.reply("No upcoming rocket launches found.")
            return

        embeds: list[discord.Embed] = []
        for item in results:
            name = item.get("name", "Upcoming Launch")
            provider = (item.get("launch_service_provider") or {}).get("name", "Unknown Provider")
            pad = (item.get("pad") or {}).get("name", "Unknown Pad")
            loc = ((item.get("pad") or {}).get("location") or {}).get("name", "Unknown Location")
            net_str = item.get("net")
            status_name = (item.get("status") or {}).get("name", "Scheduled")
            mission_desc = (item.get("mission") or {}).get("description") or "No mission description available."

            emb = discord.Embed(title=f"\N{ROCKET} {name}", description=mission_desc[:1000], color=discord.Color.orange())
            emb.add_field(name="Provider", value=provider, inline=True)
            emb.add_field(name="Status", value=status_name, inline=True)
            if net_str:
                try:
                    net_dt = arrow.get(net_str).datetime
                    emb.add_field(
                        name="Window (NET)",
                        value=f"{discord.utils.format_dt(net_dt, 'F')} ({discord.utils.format_dt(net_dt, 'R')})",
                        inline=False,
                    )
                except Exception:
                    emb.add_field(name="Window (NET)", value=net_str, inline=False)
            emb.add_field(name="Launch Pad", value=f"{pad} — {loc}", inline=False)
            if item.get("image"):
                emb.set_thumbnail(url=item["image"])
            embeds.append(emb)

        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)

    @commands.command(name="prime", aliases=["factor", "factors", "isprime"])
    async def prime_factor_check(
        self,
        ctx: commands.Context[Bot],
        number: Annotated[int, commands.Range[int, 1, 10**18]] = commands.parameter(description="The integer to test for primality and factorize."),
    ) -> None:
        """Check if a number is prime and compute its prime factorization."""
        if number < 2:
            await ctx.reply(f"**{number}** is neither prime nor composite.")
            return

        is_p = bool(sympy.isprime(number))
        factors_dict: dict[int, int] = await asyncio.to_thread(sympy.factorint, number)
        factor_parts = [f"{p}^{e}" if e > 1 else str(p) for p, e in sorted(factors_dict.items())]
        divisor_count = math.prod(e + 1 for e in factors_dict.values())

        embed = discord.Embed(
            title=f"Number Analysis: {number:,}",
            color=discord.Color.green() if is_p else discord.Color.blurple(),
        )
        embed.add_field(name="Is Prime?", value="\N{WHITE HEAVY CHECK MARK} Yes" if is_p else "\N{CROSS MARK} No", inline=True)
        embed.add_field(name="Total Divisors", value=f"`{divisor_count:,}`", inline=True)
        embed.add_field(name="Prime Factorization", value=f"`{' \N{MULTIPLICATION SIGN} '.join(factor_parts)}`", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="roman", aliases=["numeral", "romannumeral"])
    async def roman_numeral(
        self,
        ctx: commands.Context[Bot],
        value: str = commands.parameter(description="An integer (1-3999) or a Roman numeral (e.g. MMXXVI)."),
    ) -> None:
        """Convert between integers (1-3999) and Roman numerals."""
        value = value.strip()
        try:
            if value.isdigit():
                num = int(value)
                roman = int_to_roman(num)
                await ctx.reply(f"**{num:,}** in Roman numerals is **`{roman}`**.")
            else:
                num = roman_to_int(value)
                await ctx.reply(f"**`{value.upper()}`** in standard integer form is **{num:,}**.")
        except ValueError as exc:
            await ctx.reply(str(exc))

    @commands.command(name="tarot")
    async def tarot_reading(
        self,
        ctx: commands.Context[Bot],
        spread: int = commands.parameter(description="Number of cards to draw (1 or 3).", default=1),
    ) -> None:
        """Draw a single Tarot card or a 3-card Past/Present/Future spread."""
        if spread not in (1, 3):
            await ctx.reply("Please choose either a `1`-card draw or a `3`-card (Past / Present / Future) spread.")
            return

        drawn = random.sample(TAROT_DECK, k=spread)
        positions = ["Single Draw"] if spread == 1 else ["Past", "Present", "Future"]

        embed = discord.Embed(
            title="\N{CRYSTAL BALL} Tarot Card Reading",
            color=discord.Color.purple(),
        )
        for pos, (name, upright, reversed_meaning) in zip(positions, drawn, strict=False):
            is_reversed = random.choice([False, True])
            orientation = "Reversed \N{DOWNWARDS BLACK ARROW}" if is_reversed else "Upright \N{UPWARDS BLACK ARROW}"
            meaning = reversed_meaning if is_reversed else upright
            embed.add_field(
                name=f"{pos}: {name} ({orientation})",
                value=meaning,
                inline=False,
            )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.reply(embed=embed)

    @commands.command(name="onthisday", aliases=["otd", "historytoday"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def on_this_day(
        self,
        ctx: commands.Context[Bot],
        month: int | None = commands.parameter(description="Month number (1-12).", default=None),
        day: int | None = commands.parameter(description="Day of month (1-31).", default=None),
    ) -> None:
        """Discover historical events that occurred on this day in history."""
        now = arrow.utcnow()
        m = month if month is not None else now.month
        d = day if day is not None else now.day
        if not (1 <= m <= 12 and 1 <= d <= 31):
            await ctx.reply("Please provide a valid month (1-12) and day (1-31).")
            return

        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{m:02d}/{d:02d}",
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Failed to fetch historical events for that date.")
                        return
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to connect to the Wikipedia history feed.")
                return

        events = data.get("events", [])
        if not events:
            await ctx.reply("No historical events found for that date.")
            return

        sampled = random.sample(events, k=min(6, len(events)))
        sampled.sort(key=lambda e: e.get("year", 0))

        lines = []
        for ev in sampled:
            year = ev.get("year", "?")
            text = ev.get("text", "")
            pages = ev.get("pages") or []
            url = ((pages[0].get("content_urls") or {}).get("desktop") or {}).get("page") if pages else None
            year_label = f"[**{year}**]({url})" if url else f"**{year}**"
            lines.append(f"• {year_label}: {text}")

        embed = discord.Embed(
            title=f"\N{SCROLL} On This Day in History ({m:02d}/{d:02d})",
            description="\n\n".join(lines)[:4000],
            color=discord.Color.blurple(),
        )
        await ctx.reply(embed=embed)

    @commands.command(name="funfact", aliases=["fact", "randomfact"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fun_fact(self, ctx: commands.Context[Bot]) -> None:
        """Fetch a random verified fun fact."""
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    "https://uselessfacts.jsph.pl/api/v2/facts/random",
                    params={"language": "en"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Could not fetch a fun fact right now.")
                        return
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to connect to the fun facts service.")
                return

        embed = discord.Embed(
            title="\N{ELECTRIC LIGHT BULB} Did You Know?",
            description=data.get("text", "No fact returned."),
            color=discord.Color.teal(),
        )
        if data.get("source_url"):
            embed.url = data["source_url"]
        await ctx.reply(embed=embed)

    @commands.command(name="animal", aliases=["pet", "cat", "dog", "fox", "duck"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def random_animal(
        self,
        ctx: commands.Context[Bot],
        species: str | None = commands.parameter(description="Animal species: cat, dog, fox, duck, or shiba.", default=None),
    ) -> None:
        """Fetch a random cute animal picture (cat, dog, fox, duck, or shiba)."""
        invoked = ctx.invoked_with.lower() if ctx.invoked_with else ""
        choice = (species or (invoked if invoked in ("cat", "dog", "fox", "duck") else random.choice(["cat", "dog", "fox", "duck"]))).lower()

        endpoints = {
            "cat": ("https://api.thecatapi.com/v1/images/search", lambda d: d[0]["url"]),
            "dog": ("https://dog.ceo/api/breeds/image/random", lambda d: d["message"]),
            "fox": ("https://randomfox.ca/floof/", lambda d: d["image"]),
            "duck": ("https://random-d.uk/api/v2/random", lambda d: d["url"]),
            "shiba": ("https://shibe.online/api/shibes?count=1", lambda d: d[0]),
        }
        if choice not in endpoints:
            await ctx.reply(f"Unsupported animal `{choice}`. Choose from: `cat`, `dog`, `fox`, `duck`, `shiba`.")
            return

        url, extractor = endpoints[choice]
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        await ctx.reply("Could not fetch an animal image right now.")
                        return
                    data = await resp.json()
                    img_url = extractor(data)
            except Exception:
                await ctx.reply("Failed to fetch animal image.")
                return

        embed = discord.Embed(title=f"Random {choice.capitalize()}", color=discord.Color.random())
        embed.set_image(url=img_url)
        await ctx.reply(embed=embed)

    @commands.command(name="tmdb", aliases=["movie", "tv", "show", "series"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def media_lookup(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The movie or TV series title to search for."),
    ) -> None:
        """Look up movie or TV show details via TMDB (or TVMaze fallback if TMDB_API_KEY is unset)."""
        query = query.strip()
        async with ctx.typing():
            if TMDB_API_KEY:
                try:
                    async with self.bot.http_session.get(
                        "https://api.themoviedb.org/3/search/multi",
                        params={"api_key": TMDB_API_KEY, "query": query, "include_adult": "false"},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        data = await resp.json() if resp.status == 200 else {}
                except aiohttp.ClientError, TimeoutError:
                    await ctx.reply("Failed to reach TMDB.")
                    return

                results = [r for r in data.get("results", []) if r.get("media_type") in ("movie", "tv")]
                if not results:
                    await ctx.reply(f"No movies or TV shows found on TMDB for **{discord.utils.escape_markdown(query)}**.")
                    return

                item = results[0]
                mtype = item.get("media_type", "movie")
                title = item.get("title") or item.get("name") or "Unknown"
                date_str = item.get("release_date") or item.get("first_air_date") or "Unknown"
                rating = item.get("vote_average", 0.0)
                votes = item.get("vote_count", 0)
                overview = item.get("overview") or "No synopsis available."
                poster = item.get("poster_path")
                tmdb_url = f"https://www.themoviedb.org/{mtype}/{item.get('id')}"

                embed = discord.Embed(
                    title=f"\N{CLAPPER BOARD} {title} ({mtype.upper()})",
                    url=tmdb_url,
                    description=overview[:2000],
                    color=discord.Color.blue(),
                )
                embed.add_field(name="Release Date", value=date_str, inline=True)
                embed.add_field(name="Rating", value=f"\N{WHITE MEDIUM STAR} `{rating:.1f}/10` ({votes:,} votes)", inline=True)
                if poster:
                    embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{poster}")
                await ctx.reply(embed=embed)
                return

            # Keyless fallback via TVMaze API for TV/Media lookup when TMDB_API_KEY is not configured
            try:
                async with self.bot.http_session.get(
                    "https://api.tvmaze.com/singlesearch/shows",
                    params={"q": query},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply(
                            f"No results found for **{discord.utils.escape_markdown(query)}** "
                            "(Set `TMDB_API_KEY` in environment for full movie & TV TMDB catalog)."
                        )
                        return
                    show = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to reach the media lookup service.")
                return

        summary = re.sub(r"<[^>]+>", "", show.get("summary") or "No synopsis available.")
        rating = (show.get("rating") or {}).get("average") or "N/A"
        genres = ", ".join(show.get("genres") or []) or "Unknown"
        embed = discord.Embed(
            title=f"\N{TELEVISION} {show.get('name', query)}",
            url=show.get("officialSite") or show.get("url"),
            description=summary[:2000],
            color=discord.Color.blue(),
        )
        embed.add_field(name="Premiered", value=show.get("premiered") or "Unknown", inline=True)
        embed.add_field(name="Status", value=show.get("status") or "Unknown", inline=True)
        embed.add_field(name="Rating", value=f"\N{WHITE MEDIUM STAR} `{rating}`", inline=True)
        embed.add_field(name="Genres", value=genres, inline=False)
        image_url = (show.get("image") or {}).get("original") or (show.get("image") or {}).get("medium")
        if image_url:
            embed.set_thumbnail(url=image_url)
        await ctx.reply(embed=embed)

    async def _query_anilist(self, ctx: commands.Context[Bot], query: str, media_type: str) -> None:
        async with ctx.typing():
            try:
                async with self.bot.http_session.post(
                    "https://graphql.anilist.co",
                    json={"query": ANILIST_QUERY, "variables": {"search": query.strip(), "type": media_type}},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply(f"No {media_type.lower()} found on AniList for **{discord.utils.escape_markdown(query)}**.")
                        return
                    payload = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to connect to AniList.")
                return

        media = (payload.get("data") or {}).get("Media")
        if not media:
            await ctx.reply(f"No {media_type.lower()} found for **{discord.utils.escape_markdown(query)}**.")
            return

        titles = media.get("title") or {}
        display_title = titles.get("english") or titles.get("romaji") or titles.get("native") or query
        desc = re.sub(r"<[^>]+>", "", media.get("description") or "No synopsis available.")
        score = media.get("averageScore")
        genres = ", ".join(media.get("genres") or []) or "Unknown"
        status = (media.get("status") or "Unknown").replace("_", " ").title()

        embed = discord.Embed(
            title=f"{display_title} ({media.get('format', media_type)})",
            url=media.get("siteUrl"),
            description=desc[:1800],
            color=discord.Color.blue(),
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Score", value=f"`{score}%`" if score else "N/A", inline=True)
        if media_type == "ANIME":
            embed.add_field(name="Episodes", value=str(media.get("episodes") or "?"), inline=True)
        else:
            embed.add_field(
                name="Chapters / Volumes",
                value=f"{media.get('chapters') or '?'} ch / {media.get('volumes') or '?'} vol",
                inline=True,
            )
        embed.add_field(name="Genres", value=genres, inline=False)
        cover = (media.get("coverImage") or {}).get("large")
        if cover:
            embed.set_thumbnail(url=cover)
        await ctx.reply(embed=embed)

    @commands.command(name="anime", aliases=["ani"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def anime_lookup(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The anime title to search on AniList."),
    ) -> None:
        """Search for an anime on AniList."""
        await self._query_anilist(ctx, query, "ANIME")

    @commands.command(name="manga")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def manga_lookup(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The manga title to search on AniList."),
    ) -> None:
        """Search for a manga on AniList."""
        await self._query_anilist(ctx, query, "MANGA")

    @commands.command(name="book", aliases=["books", "openlibrary"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def book_lookup(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The book title or author to search on Open Library."),
    ) -> None:
        """Search for book metadata and editions via Open Library."""
        async with ctx.typing():
            try:
                async with self.bot.http_session.get(
                    "https://openlibrary.org/search.json",
                    params={"q": query.strip(), "limit": 5},
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Failed to query Open Library.")
                        return
                    data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to connect to Open Library.")
                return

        docs = data.get("docs", [])
        if not docs:
            await ctx.reply(f"No books found for **{discord.utils.escape_markdown(query)}**.")
            return

        book = docs[0]
        title = book.get("title", "Unknown Title")
        authors = ", ".join(book.get("author_name", ["Unknown Author"]))
        first_year = book.get("first_publish_year", "Unknown")
        editions = book.get("edition_count", 1)
        pages = book.get("number_of_pages_median", "Unknown")
        subjects = ", ".join((book.get("subject") or [])[:6]) or "Unlisted"
        key = book.get("key", "")
        book_url = f"https://openlibrary.org{key}" if key else "https://openlibrary.org"

        embed = discord.Embed(
            title=f"\N{BOOKS} {title}",
            url=book_url,
            color=discord.Color.dark_teal(),
        )
        embed.add_field(name="Author(s)", value=authors[:1024], inline=True)
        embed.add_field(name="First Published", value=str(first_year), inline=True)
        embed.add_field(name="Median Pages / Editions", value=f"{pages} pages ({editions} editions)", inline=True)
        embed.add_field(name="Subjects", value=subjects[:1024], inline=False)
        if book.get("cover_i"):
            embed.set_thumbnail(url=f"https://covers.openlibrary.org/b/id/{book['cover_i']}-L.jpg")
        await ctx.reply(embed=embed)

    @commands.command(name="music", aliases=["song", "track", "musicbrainz", "lastfm"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def music_lookup(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The song or artist to search on Last.fm / MusicBrainz."),
    ) -> None:
        """Look up track, artist, and release metadata via Last.fm or MusicBrainz."""
        query = query.strip()
        async with ctx.typing():
            if LASTFM_API_KEY:
                try:
                    async with self.bot.http_session.get(
                        "https://ws.audioscrobbler.com/2.0/",
                        params={
                            "method": "track.search",
                            "track": query,
                            "api_key": LASTFM_API_KEY,
                            "format": "json",
                            "limit": 1,
                        },
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            lfm_data = await resp.json()
                            tracks = (((lfm_data.get("results") or {}).get("trackmatches") or {}).get("track")) or []
                            if tracks:
                                tr = tracks[0]
                                embed = discord.Embed(
                                    title=f"\N{MUSICAL NOTE} {tr.get('name')} — {tr.get('artist')}",
                                    url=tr.get("url"),
                                    color=discord.Color.red(),
                                )
                                embed.add_field(name="Artist", value=tr.get("artist", "Unknown"), inline=True)
                                embed.add_field(name="Listeners", value=f"{int(tr.get('listeners', 0)):,}", inline=True)
                                await ctx.reply(embed=embed)
                                return
                except aiohttp.ClientError, TimeoutError, ValueError:
                    pass

            try:
                async with self.bot.http_session.get(
                    "https://musicbrainz.org/ws/2/recording",
                    params={"query": query, "fmt": "json", "limit": 5},
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        await ctx.reply("Failed to query MusicBrainz.")
                        return
                    mb_data = await resp.json()
            except aiohttp.ClientError, TimeoutError:
                await ctx.reply("Failed to connect to MusicBrainz.")
                return

        recordings = mb_data.get("recordings", [])
        if not recordings:
            await ctx.reply(f"No music recordings found for **{discord.utils.escape_markdown(query)}**.")
            return

        rec = recordings[0]
        title = rec.get("title", "Unknown Track")
        artist_credits_list = rec.get("artist-credit") or []
        artist_name = "".join(c.get("name", "") + c.get("joinphrase", "") for c in artist_credits_list) or "Unknown Artist"
        releases = rec.get("releases") or []
        album_title = releases[0].get("title", "Unknown Release") if releases else "Single / Unlisted"
        release_date = rec.get("first-release-date", "Unknown")
        length_ms = rec.get("length")
        duration = f"{length_ms // 60000}:{(length_ms // 1000) % 60:02d}" if length_ms else "Unknown"
        mbid = rec.get("id", "")
        tags = ", ".join(t["name"] for t in (rec.get("tags") or [])[:6]) or "None listed"

        embed = (
            discord.Embed(
                title=f"\N{MUSICAL NOTE} {title}",
                url=f"https://musicbrainz.org/recording/{mbid}" if mbid else None,
                color=discord.Color.purple(),
            )
            .add_field(name="Artist", value=artist_name, inline=True)
            .add_field(name="Release / Album", value=album_title, inline=True)
            .add_field(name="First Released", value=release_date, inline=True)
            .add_field(name="Duration", value=f"`{duration}`", inline=True)
            .add_field(name="Tags", value=tags, inline=False)
        )
        await ctx.reply(embed=embed)

    def _build_http_embed(self, code: int, animal: str = "cat") -> discord.Embed:
        if code in HTTP_STATUS_CODES:
            phrase, description = HTTP_STATUS_CODES[code]
        else:
            try:
                status = std_http.HTTPStatus(code)
                phrase = status.phrase
                description = status.description or "Standard HTTP status code."
            except ValueError:
                if 100 <= code <= 599:
                    phrase = "Unassigned / Custom Status Code"
                    description = "This HTTP status code is non-standard or unassigned by IANA."
                else:
                    msg = f"`{code}` is not a valid HTTP status code (must be between 100 and 599)."
                    raise commands.BadArgument(msg) from None

        categories = {
            1: ("1xx Informational", discord.Color.blue()),
            2: ("2xx Success", discord.Color.green()),
            3: ("3xx Redirection", discord.Color.gold()),
            4: ("4xx Client Error", discord.Color.orange()),
            5: ("5xx Server Error", discord.Color.red()),
        }
        cat_label, color = categories.get(code // 100, ("HTTP Status", discord.Color.blurple()))
        mdn_url = f"https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/{code}"
        img_url = f"https://http.dog/{code}.jpg" if animal == "dog" else f"https://http.cat/{code}.jpg"

        embed = discord.Embed(
            title=f"HTTP {code} — {phrase}",
            url=mdn_url,
            description=description,
            color=color,
        )
        embed.add_field(name="Category", value=f"`{cat_label}`", inline=True)
        embed.add_field(name="Reference", value=f"[MDN Web Docs]({mdn_url})", inline=True)
        embed.set_image(url=img_url)
        return embed

    @commands.group(name="http", aliases=["httpstatus", "httpcode"], invoke_without_command=True)
    async def http(
        self,
        ctx: commands.Context[Bot],
        code: int = commands.parameter(description="The HTTP status code to look up.", default=404),
    ) -> None:
        """Display information about HTTP status codes."""
        await ctx.reply(embed=self._build_http_embed(code, animal="cat"))

    @http.command(name="cat", aliases=["cats"])
    async def http_cat(
        self,
        ctx: commands.Context[Bot],
        code: int = commands.parameter(description="The HTTP status code to look up.", default=404),
    ) -> None:
        """Display an HTTP status code with an HTTP cat image (http.cat)."""
        await ctx.reply(embed=self._build_http_embed(code, animal="cat"))

    @http.command(name="dog", aliases=["dogs"])
    async def http_dog(
        self,
        ctx: commands.Context[Bot],
        code: int = commands.parameter(description="The HTTP status code to look up.", default=404),
    ) -> None:
        """Display an HTTP status code with an HTTP dog image (http.dog)."""
        await ctx.reply(embed=self._build_http_embed(code, animal="dog"))

    @commands.command(name="httpdog", aliases=["doghttp"])
    async def httpdog_shortcut(
        self,
        ctx: commands.Context[Bot],
        code: int = commands.parameter(description="The HTTP status code to look up.", default=404),
    ) -> None:
        """Display an HTTP status code with an HTTP dog image (http.dog)."""
        await ctx.reply(embed=self._build_http_embed(code, animal="dog"))


async def setup(bot: Bot) -> None:
    await bot.add_cog(Misc(bot))
    await bot.add_cog(SnipeMessageListener(bot))
    await bot.add_cog(PingMessageListner(bot))
    await bot.add_cog(Weather(bot))
    await bot.add_cog(Chemistry(bot))
