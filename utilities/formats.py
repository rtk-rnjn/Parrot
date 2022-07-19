from __future__ import annotations
from contextlib import suppress

import datetime
import re
from typing import TYPE_CHECKING, Any

import pomice
import discord
import asyncio
from discord.ext import commands


class plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        if abs(v) != 1:
            return f"{v} {plural}"
        return f"{v} {singular}"


def human_join(seq, delim=", ", final="or"):
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return delim.join(seq[:-1]) + f" {final} {seq[-1]}"


class TabularData:
    def __init__(self):
        self._widths = []
        self._columns = []
        self._rows = []

    def set_columns(self, columns):
        self._columns = columns
        self._widths = [len(c) + 2 for c in columns]

    def add_row(self, row):
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2
            if width > self._widths[index]:
                self._widths[index] = width

    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)

    def render(self):
        """Renders a table in rST format.
        Example:
        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice | 24  |
        |  Bob  | 19  |
        +-------+-----+
        """
        sep = "+".join("-" * w for w in self._widths)
        sep = f"+{sep}+"

        to_draw = [sep]

        def get_entry(d):
            elem = "|".join(f"{e:^{self._widths[i]}}" for i, e in enumerate(d))
            return f"|{elem}|"

        to_draw.append(get_entry(self._columns))
        to_draw.append(sep)

        for row in self._rows:
            to_draw.append(get_entry(row))

        to_draw.append(sep)
        return "\n".join(to_draw)


def format_dt(dt, style=None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f"<t:{int(dt.timestamp())}>"
    return f"<t:{int(dt.timestamp())}:{style}>"


def format_dt_with_int(dt: int, style=None) -> str:
    return f"<t:{dt}:{style if style else ''}>"


def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message


def get_flag(
    ls: list, ann: Any, *, deli: Any, pref: Any, alis: Any, default: bool
) -> list:
    for flag in ann.get_flags().values():
        if flag.required:
            ls.append(f"<{pref}{flag.name}{'|'.join(alis)}{deli}>")
        elif default:
            ls.append(f"[{pref}{flag.name}{'|'.join(list(alis))}{deli}={flag.default}]")
        else:
            ls.append(f"[{pref}{flag.name}{'|'.join(list(alis))}{deli}]")
    return ls


class Player(pomice.Player):
    """Custom pomice Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if TYPE_CHECKING:
            from core import Context

        self.queue = asyncio.Queue()
        self.controller: discord.Message = None
        # Set context here so we can send a now playing embed
        self.context: Context = None
        self.dj: discord.Member = None

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()

    async def do_next(self) -> None:
        # Clear the votes for a new song
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

        # Check if theres a controller still active and deletes it
        if self.controller is not None:
            with suppress(discord.HTTPException):
                await self.controller.delete()

        # Queue up the next track, else teardown the player
        try:
            track: pomice.Track = self.queue.get_nowait()
        except asyncio.queues.QueueEmpty:
            return await self.teardown()

        await self.play(track)

        # Call the controller (a.k.a: The "Now Playing" embed) and check if one exists

        if track.is_stream:
            embed = discord.Embed(
                title="Now playing",
                description=f":red_circle: **LIVE** [{track.title}]({track.uri}) [{track.requester.mention}]",
            )
            self.controller: discord.Message = await self.context.send(embed=embed)  # type: ignore
        else:
            embed = discord.Embed(
                title=f"Now playing",
                description=f"[{track.title}]({track.uri}) [{track.requester.mention}]",
            )
            self.controller: discord.Message = await self.context.send(embed=embed)  # type: ignore

    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        with suppress((discord.HTTPException), (KeyError)):
            await self.destroy()
            if self.controller:
                await self.controller.delete()

    async def set_context(self, ctx: commands.Context):
        """Set context for the player"""
        self.context = ctx
        self.dj = ctx.author
