from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

import discord
import pomice
from discord.ext.commands import Context

if TYPE_CHECKING:
    from core.bot import Parrot

MEMBER_ID = int
VoteSet = set[MEMBER_ID]
ACTION_TYPE = Callable[[], Awaitable[bool]]


class Player(pomice.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ctx: Context[Parrot] | None = None
        self.queue = pomice.Queue()
        self.message_controller: discord.Message | None = None

        self.pause_votes: VoteSet = set()
        self.resume_votes: VoteSet = set()
        self.skip_votes: VoteSet = set()
        self.shuffle_votes: VoteSet = set()
        self.stop_votes: VoteSet = set()

        self.get_formated_message: Callable[[pomice.Track], Awaitable[discord.Message]] | None = None

    @property
    def dj(self) -> discord.Member:
        if self.ctx is None:
            raise ValueError("Context is not set for this player.")

        voice_channel = self.channel
        if voice_channel is None:
            raise ValueError("Player is not connected to a voice channel.")

        members = [member for member in voice_channel.members if not member.bot]
        if not members:
            raise ValueError("No non-bot members in the voice channel.")

        possible_dj_members = self.__find_possible_djs(members)
        if not possible_dj_members:
            return cast(discord.Member, self.ctx.author)

        dj = min(possible_dj_members, key=lambda m: m.joined_at or discord.utils.snowflake_time(m.id))
        return dj

    def __find_possible_djs(self, members: list[discord.Member]) -> list[discord.Member]:
        possible_djs = []
        for member in members:
            if member.guild_permissions.manage_channels or member.guild_permissions.manage_guild:
                possible_djs.append(member)
        return possible_djs

    def _non_bot_members(self) -> int:
        return sum(1 for m in self.channel.members if not m.bot)

    def _reset_votes(self) -> None:
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

    async def _vote_action(self, *, member: discord.Member, votes: VoteSet, action: ACTION_TYPE, reset_votes: bool = True) -> bool:
        if member == self.dj:
            await action()
            if reset_votes:
                votes.clear()
            return True

        votes.add(member.id)
        if len(votes) / self._non_bot_members() >= 0.5:
            await action()
            votes.clear()
            return True

        return False

    def _shuffle_queue(self) -> bool:
        items = list(self.queue._queue)
        random.shuffle(items)
        self.queue._queue.clear()
        self.queue._queue.extend(items)

        return True

    async def play_next(self, *, ignore_if_playing: bool = False) -> bool:
        self._reset_votes()

        if self.message_controller:
            await self.message_controller.delete()
            self.message_controller = None

        try:
            track = self.queue.get()
        except pomice.QueueEmpty:
            await self.teardown()
            return False

        await self.play(track, ignore_if_playing=ignore_if_playing)
        if self.get_formated_message:
            self.message_controller = await self.get_formated_message(track)

        return True

    async def teardown(self) -> bool:
        await self.destroy()
        if self.message_controller:
            await self.message_controller.delete()
        self.message_controller = None

        return True

    async def vote_skip(self, member: discord.Member) -> bool:
        return await self._vote_action(member=member, votes=self.skip_votes, action=self.play_next)

    async def vote_pause(self, member: discord.Member) -> bool:
        return await self._vote_action(member=member, votes=self.pause_votes, action=lambda: self.set_pause(True))

    async def vote_resume(self, member: discord.Member) -> bool:
        return await self._vote_action(member=member, votes=self.resume_votes, action=lambda: self.set_pause(False))

    async def vote_stop(self, member: discord.Member) -> bool:
        return await self._vote_action(member=member, votes=self.stop_votes, action=self.teardown)

    async def vote_shuffle(self, member: discord.Member) -> bool:
        return await self._vote_action(member=member, votes=self.shuffle_votes, action=lambda: asyncio.to_thread(self._shuffle_queue))

    async def queue_track(self, track: pomice.Track, ctx: Context[Parrot]) -> None:
        self.queue.put(track)
        if not self.is_playing and not self.is_paused:
            await self.play_next()
