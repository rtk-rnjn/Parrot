from __future__ import annotations

import json
import asyncio
import logging
import random
from collections.abc import Iterable
from typing import Optional

from discord import Embed, Member, Reaction
from discord.abc import User

import discord
from discord.ext.commands import Converter, BadArgument, Paginator
from rapidfuzz import fuzz

from core import Context
from ._utils import SNAKE_RESOURCES

FIRST_EMOJI = "\u23EE"  # [:track_previous:]
LEFT_EMOJI = "\u2B05"  # [:arrow_left:]
RIGHT_EMOJI = "\u27A1"  # [:arrow_right:]
LAST_EMOJI = "\u23ED"  # [:track_next:]
DELETE_EMOJI = "\N{WASTEBASKET}"  # [:trashcan:]

PAGINATION_EMOJI = (FIRST_EMOJI, LEFT_EMOJI, RIGHT_EMOJI, LAST_EMOJI, DELETE_EMOJI)


class EmptyPaginatorEmbedError(Exception):
    """Base Exception class for an empty paginator embed."""


class LinePaginator(Paginator):
    """A class that aids in paginating code blocks for Discord messages."""

    def __init__(
        self,
        prefix: str = "```",
        suffix: str = "```",
        max_size: int = 2000,
        max_lines: Optional[int] = None,
        linesep: str = "\n",
    ):
        """
        Overrides the Paginator.__init__ from inside discord.ext.commands.
        `prefix` and `suffix` will be prepended and appended respectively to every page.
        `max_size` and `max_lines` denote the maximum amount of codepoints and lines
        allowed per page.
        """
        super().__init__(prefix, suffix, max_size - len(suffix), linesep)

        self.max_lines = max_lines
        self._current_page = [prefix]
        self._linecount = 0
        self._count = len(prefix) + 1  # prefix + newline
        self._pages = []

    def add_line(self, line: str = "", *, empty: bool = False) -> None:
        """
        Adds a line to the current page.
        If the line exceeds the `max_size` then a RuntimeError is raised.
        Overrides the Paginator.add_line from inside discord.ext.commands in order to allow
        configuration of the maximum number of lines per page.
        If `empty` is True, an empty line will be placed after the a given `line`.
        """
        if len(line) > self.max_size - len(self.prefix) - 2:
            raise RuntimeError(
                "Line exceeds maximum page size %s"
                % (self.max_size - len(self.prefix) - 2)
            )

        if self.max_lines is not None:
            if self._linecount >= self.max_lines:
                self._linecount = 0
                self.close_page()

            self._linecount += 1
        if self._count + len(line) + 1 > self.max_size:
            self.close_page()

        self._count += len(line) + 1
        self._current_page.append(line)

        if empty:
            self._current_page.append("")
            self._count += 1

    @classmethod
    async def paginate(
        cls,
        lines: Iterable[str],
        ctx: Context,
        embed: Embed,
        prefix: str = "",
        suffix: str = "",
        max_lines: Optional[int] = None,
        max_size: int = 500,
        empty: bool = True,
        restrict_to_user: User = None,
        timeout: int = 300,
        footer_text: str = None,
        url: str = None,
        exception_on_empty_embed: bool = False,
    ) -> None:
        """
        Use a paginator and set of reactions to provide pagination over a set of lines.
        The reactions are used to switch page, or to finish with pagination.
        When used, this will send a message using `ctx.send()` and apply a set of reactions to it.
        These reactions may be used to change page, or to remove pagination from the message.
        Pagination will also be removed automatically if no reaction is added for `timeout` seconds,
        defaulting to five minutes (300 seconds).
        If `empty` is True, an empty line will be placed between each given line.
        >>> embed = Embed()
        >>> embed.set_author(name="Some Operation", url=url, icon_url=icon)
        >>> await LinePaginator.paginate(
        ...     (line for line in lines),
        ...     ctx, embed
        ... )
        """

        def event_check(reaction_: Reaction, user_: Member) -> bool:
            """Make sure that this reaction is what we want to operate on."""
            no_restrictions = (
                # Pagination is not restricted
                not restrict_to_user
                # The reaction was by a whitelisted user
                or user_.id == restrict_to_user.id
            )

            return (
                # Conditions for a successful pagination:
                all(
                    (
                        # Reaction is on this message
                        reaction_.message.id == message.id,
                        # Reaction is one of the pagination emotes
                        str(reaction_.emoji)
                        in PAGINATION_EMOJI,  # Note: DELETE_EMOJI is a string and not unicode
                        # Reaction was not made by the Bot
                        user_.id != ctx.bot.user.id,
                        # There were no restrictions
                        no_restrictions,
                    )
                )
            )

        paginator = cls(
            prefix=prefix, suffix=suffix, max_size=max_size, max_lines=max_lines
        )
        current_page = 0

        if not lines:
            if exception_on_empty_embed:
                log.exception("Pagination asked for empty lines iterable")
                raise EmptyPaginatorEmbedError("No lines to paginate")

            log.debug(
                "No lines to add to paginator, adding '(nothing to display)' message"
            )
            lines.append("(nothing to display)")

        for line in lines:
            try:
                paginator.add_line(line, empty=empty)
            except Exception:
                log.exception(f"Failed to add line to paginator: '{line}'")
                raise  # Should propagate
            else:
                log.trace(f"Added line to paginator: '{line}'")

        log.debug(f"Paginator created with {len(paginator.pages)} pages")

        embed.description = paginator.pages[current_page]

        if len(paginator.pages) <= 1:
            if footer_text:
                embed.set_footer(text=footer_text)
                log.trace(f"Setting embed footer to '{footer_text}'")

            if url:
                embed.url = url
                log.trace(f"Setting embed url to '{url}'")

            log.debug(
                "There's less than two pages, so we won't paginate - sending single page on its own"
            )
            await ctx.send(embed=embed)
            return
        if footer_text:
            embed.set_footer(
                text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
            )
        else:
            embed.set_footer(text=f"Page {current_page + 1}/{len(paginator.pages)}")
        log.trace(f"Setting embed footer to '{embed.footer.text}'")

        if url:
            embed.url = url
            log.trace(f"Setting embed url to '{url}'")

        log.debug("Sending first page to channel...")
        message = await ctx.send(embed=embed)

        log.debug("Adding emoji reactions to message...")

        for emoji in PAGINATION_EMOJI:
            # Add all the applicable emoji to the message
            log.trace(f"Adding reaction: {repr(emoji)}")
            await message.add_reaction(emoji)

        while True:
            try:
                reaction, user = await ctx.bot.wait_for(
                    "reaction_add", timeout=timeout, check=event_check
                )
                log.trace(f"Got reaction: {reaction}")
            except asyncio.TimeoutError:
                log.debug("Timed out waiting for a reaction")
                break  # We're done, no reactions for the last 5 minutes

            if (
                str(reaction.emoji) == DELETE_EMOJI
            ):  # Note: DELETE_EMOJI is a string and not unicode
                log.debug("Got delete reaction")
                return await message.delete()

            if reaction.emoji == FIRST_EMOJI:
                await message.remove_reaction(reaction.emoji, user)
                current_page = 0

                log.debug(
                    f"Got first page reaction - changing to page 1/{len(paginator.pages)}"
                )

                embed.description = paginator.pages[current_page]
                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )
                await message.edit(embed=embed)

            if reaction.emoji == LAST_EMOJI:
                await message.remove_reaction(reaction.emoji, user)
                current_page = len(paginator.pages) - 1

                log.debug(
                    f"Got last page reaction - changing to page {current_page + 1}/{len(paginator.pages)}"
                )

                embed.description = paginator.pages[current_page]
                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )
                await message.edit(embed=embed)

            if reaction.emoji == LEFT_EMOJI:
                await message.remove_reaction(reaction.emoji, user)

                if current_page <= 0:
                    log.debug(
                        "Got previous page reaction, but we're on the first page - ignoring"
                    )
                    continue

                current_page -= 1
                log.debug(
                    f"Got previous page reaction - changing to page {current_page + 1}/{len(paginator.pages)}"
                )

                embed.description = paginator.pages[current_page]

                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )

                await message.edit(embed=embed)

            if reaction.emoji == RIGHT_EMOJI:
                await message.remove_reaction(reaction.emoji, user)

                if current_page >= len(paginator.pages) - 1:
                    log.debug(
                        "Got next page reaction, but we're on the last page - ignoring"
                    )
                    continue

                current_page += 1
                log.debug(
                    f"Got next page reaction - changing to page {current_page + 1}/{len(paginator.pages)}"
                )

                embed.description = paginator.pages[current_page]

                if footer_text:
                    embed.set_footer(
                        text=f"{footer_text} (Page {current_page + 1}/{len(paginator.pages)})"
                    )
                else:
                    embed.set_footer(
                        text=f"Page {current_page + 1}/{len(paginator.pages)}"
                    )

                await message.edit(embed=embed)

        log.debug("Ending pagination and clearing reactions...")
        await message.clear_reactions()


async def disambiguate(
    ctx: Context,
    entries: list[str],
    *,
    timeout: float = 30,
    entries_per_page: int = 20,
    empty: bool = False,
    embed: Optional[discord.Embed] = None,
) -> str:
    """
    Has the user choose between multiple entries in case one could not be chosen automatically.
    Disambiguation will be canceled after `timeout` seconds.
    This will raise a BadArgument if entries is empty, if the disambiguation event times out,
    or if the user makes an invalid choice.
    """
    if len(entries) == 0:
        raise BadArgument("No matches found.")

    if len(entries) == 1:
        return entries[0]

    choices = (f"{index}: {entry}" for index, entry in enumerate(entries, start=1))

    def check(message: discord.Message) -> bool:
        return (
            message.content.isdecimal()
            and message.author == ctx.author
            and message.channel == ctx.channel
        )

    try:
        if embed is None:
            embed = discord.Embed()

        coro1 = ctx.bot.wait_for("message", check=check, timeout=timeout)
        coro2 = LinePaginator.paginate(
            choices,
            ctx,
            embed=embed,
            max_lines=entries_per_page,
            empty=empty,
            max_size=6000,
            timeout=9000,
        )

        # wait_for timeout will go to except instead of the wait_for thing as I expected
        futures = [asyncio.ensure_future(coro1), asyncio.ensure_future(coro2)]
        done, pending = await asyncio.wait(
            futures, return_when=asyncio.FIRST_COMPLETED, loop=ctx.bot.loop
        )

        # :yert:
        result = list(done)[0].result()

        # Pagination was canceled - result is None
        if result is None:
            for coro in pending:
                coro.cancel()
            raise BadArgument("Canceled.")

        # Pagination was not initiated, only one page
        if result.author == ctx.bot.user:
            # Continue the wait_for
            result = await list(pending)[0]

        # Love that duplicate code
        for coro in pending:
            coro.cancel()
    except asyncio.TimeoutError:
        raise BadArgument("Timed out.")

    # Guaranteed to not error because of isdecimal() in check
    index = int(result.content)

    try:
        return entries[index - 1]
    except IndexError:
        raise BadArgument("Invalid choice.")


log = logging.getLogger(__name__)


class Snake(Converter):
    """Snake converter for the Snakes Cog."""

    snakes = None
    special_cases = None

    async def convert(self, ctx: Context, name: str) -> str:
        """Convert the input snake name to the closest matching Snake object."""
        await self.build_list()
        name = name.lower()

        if name == "python":
            return "Python (programming language)"

        def get_potential(iterable: Iterable, *, threshold: int = 80) -> list[str]:
            nonlocal name
            potential = []

            for item in iterable:
                original, item = item, item.lower()

                if name == item:
                    return [original]

                a, b = fuzz.ratio(name, item), fuzz.partial_ratio(name, item)
                if a >= threshold or b >= threshold:
                    potential.append(original)

            return potential

        # Handle special cases
        if name.lower() in self.special_cases:
            return self.special_cases.get(name.lower(), name.lower())

        names = {snake["name"]: snake["scientific"] for snake in self.snakes}
        all_names = names.keys() | names.values()
        timeout = len(all_names) * (3 / 4)

        embed = discord.Embed(
            title="Found multiple choices. Please choose the correct one.",
            colour=0x59982F,
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        name = await disambiguate(
            ctx, get_potential(all_names), timeout=timeout, embed=embed
        )
        return names.get(name, name)

    @classmethod
    async def build_list(cls) -> None:
        """Build list of snakes from the static snake resources."""
        # Get all the snakes
        if cls.snakes is None:
            cls.snakes = json.loads(
                (SNAKE_RESOURCES / "snake_names.json").read_text("utf8")
            )
        # Get the special cases
        if cls.special_cases is None:
            special_cases = json.loads(
                (SNAKE_RESOURCES / "special_snakes.json").read_text("utf8")
            )
            cls.special_cases = {
                snake["name"].lower(): snake for snake in special_cases
            }

    @classmethod
    async def random(cls) -> str:
        """
        Get a random Snake from the loaded resources.
        This is stupid. We should find a way to somehow get the global session into a global context,
        so I can get it from here.
        """
        await cls.build_list()
        names = [snake["scientific"] for snake in cls.snakes]
        return random.choice(names)
