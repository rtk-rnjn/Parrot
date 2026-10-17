from __future__ import annotations

import datetime
import logging
import math
from collections.abc import Awaitable, Callable, Iterable
from typing import TYPE_CHECKING, NamedTuple

import discord
import pomice

if TYPE_CHECKING:
    from discord.ext.commands import Context

    from core import Bot

__all__ = ("Player", "VoteResult")

_log = logging.getLogger(__name__)

# Share of non-bot listeners that must agree before a vote-gated action runs.
VOTE_THRESHOLD = 0.5

type VoteSet = set[int]
type Action = Callable[[], Awaitable[object]]


class VoteResult(NamedTuple):
    """Outcome of a vote-gated action. ``votes`` and ``required`` describe the tally after this vote."""

    passed: bool
    votes: int
    required: int


def _joined_at(member: discord.Member) -> datetime.datetime:
    return member.joined_at or discord.utils.snowflake_time(member.id)


class Player(pomice.Player):
    """A guild player with a queue, a DJ and vote-gated controls.

    ``ctx`` is the context that connected the player and is used to pick a fallback DJ.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.ctx: Context[Bot] | None = None
        self.queue = pomice.Queue()

        self.pause_votes: VoteSet = set()
        self.resume_votes: VoteSet = set()
        self.skip_votes: VoteSet = set()
        self.shuffle_votes: VoteSet = set()
        self.stop_votes: VoteSet = set()

    # Membership

    @property
    def listeners(self) -> list[discord.Member]:
        """Non-bot members in the player's voice channel. Empty once the player has disconnected."""
        channel = self.channel
        if channel is None:
            return []
        return [member for member in channel.members if not member.bot]

    def _can_manage(self, member: discord.Member) -> bool:
        permissions = member.guild_permissions
        return permissions.manage_guild or permissions.manage_channels or self.channel.permissions_for(member).manage_channels

    @property
    def dj(self) -> discord.Member | None:
        """Who controls the player without a vote.

        Preference order: the longest-standing listener who can manage channels, then the member who
        connected the player if they are still listening, then the longest-standing listener.
        """
        listeners = self.listeners
        if not listeners:
            return None

        privileged = [member for member in listeners if self._can_manage(member)]
        if privileged:
            return min(privileged, key=_joined_at)

        if self.ctx is not None and isinstance(self.ctx.author, discord.Member) and self.ctx.author in listeners:
            return self.ctx.author

        return min(listeners, key=_joined_at)

    def is_dj(self, member: discord.Member) -> bool:
        dj = self.dj
        return dj is not None and dj.id == member.id

    # Votes

    def reset_votes(self) -> None:
        for votes in (self.pause_votes, self.resume_votes, self.skip_votes, self.shuffle_votes, self.stop_votes):
            votes.clear()

    @property
    def required_votes(self) -> int:
        return max(1, math.ceil(len(self.listeners) * VOTE_THRESHOLD))

    async def _vote(self, member: discord.Member, votes: VoteSet, action: Action) -> VoteResult:
        """Run ``action`` at once for the DJ, otherwise once enough listeners have voted for it."""
        required = self.required_votes
        if self.is_dj(member):
            votes.clear()
            await action()
            return VoteResult(passed=True, votes=required, required=required)

        votes.add(member.id)
        if len(votes) < required:
            return VoteResult(passed=False, votes=len(votes), required=required)

        votes.clear()
        await action()
        return VoteResult(passed=True, votes=required, required=required)

    async def vote_skip(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, self.skip_votes, self.play_next)

    async def vote_stop(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, self.stop_votes, self.teardown)

    async def vote_pause(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, self.pause_votes, lambda: self.set_pause(True))

    async def vote_resume(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, self.resume_votes, lambda: self.set_pause(False))

    async def vote_shuffle(self, member: discord.Member) -> VoteResult:
        async def shuffle() -> None:
            self.queue.shuffle()

        return await self._vote(member, self.shuffle_votes, shuffle)

    # Playback

    async def enqueue(self, tracks: Iterable[pomice.Track]) -> None:
        """Add ``tracks`` to the queue and start playing unless something is already playing or paused."""
        for track in tracks:
            self.queue.put(track)

        if not self.is_playing and not self.is_paused:
            await self.play_next()

    async def play_next(self) -> pomice.Track | None:
        """Play the next queued track. When the queue is exhausted the player tears down and ``None`` is returned."""
        if self.is_dead:
            return None

        self.reset_votes()
        try:
            track = self.queue.get()
        except pomice.QueueEmpty:
            await self.teardown()
            return None

        await self.play(track)
        return track

    async def teardown(self) -> None:
        """Clear the queue, leave the voice channel and release the Lavalink player. Safe to call more than once."""
        self.reset_votes()
        self.queue.clear()

        if self.is_dead:
            return

        try:
            await self.destroy()
        except Exception:  # pylint: disable=broad-exception-caught
            _log.exception("Could not destroy the player for guild %s cleanly.", self.guild.id)
