from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
import pomice
from discord.ext import commands

from core.utils import NoticeLayout, PaginationLayout, format_clock_duration, plural, truncate

from .player import Player, VoteResult

if TYPE_CHECKING:
    from discord.ext.commands import Context

    from core import Bot

_log = logging.getLogger(__name__)

QUEUE_PAGE_SIZE = 10
PROGRESS_BAR_WIDTH = 12
MAX_TITLE_LENGTH = 80
NO_NODES_MESSAGE = "No Lavalink nodes are connected, so music is unavailable right now."

SEARCH_ORDER = (pomice.SearchType.other, pomice.SearchType.scsearch, pomice.SearchType.ytsearch)
ADVANCE_ON_TRACK_END = frozenset({"finished", "loadfailed"})

type SearchResult = pomice.Playlist | list[pomice.Track]


def format_progress(position: float, length: float, *, is_stream: bool = False, width: int = PROGRESS_BAR_WIDTH) -> str:
    """A slider with timestamps, e.g. ``\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{FISHEYE}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL}\N{BOX DRAWINGS LIGHT HORIZONTAL} 1:02 / 3:45``. Streams and unknown lengths get no slider."""
    if is_stream:
        return f"\N{LARGE RED CIRCLE} LIVE \N{MIDDLE DOT} {format_clock_duration(position)}"
    if length <= 0:
        return format_clock_duration(position)

    ratio = min(max(position / length, 0.0), 1.0)
    filled = min(int(ratio * width), width - 1)
    bar = "\N{HORIZONTAL BAR}" * filled + "\N{RADIO BUTTON}" + "\N{HORIZONTAL BAR}" * (width - 1 - filled)
    return f"{bar} {format_clock_duration(position)} / {format_clock_duration(length)}"


def describe_track(track: pomice.Track) -> str:
    """A markdown one-liner: linked title plus author."""
    title = discord.utils.escape_markdown(truncate(track.title, MAX_TITLE_LENGTH))
    label = f"[{title}]({track.uri})" if track.uri else title
    return f"**{label}** by {discord.utils.escape_markdown(track.author)}"


def _has_tracks(result: SearchResult | None) -> bool:
    if result is None:
        return False
    if isinstance(result, pomice.Playlist):
        return bool(result.tracks)
    return bool(result)


class Music(commands.Cog):
    """Voice and music playback backed by Lavalink."""

    help_emoji = "\N{MUSICAL NOTE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    # Guards: each returns what a command needs, or None after telling the user why it cannot continue.

    @staticmethod
    def _get_player(ctx: Context[Bot]) -> Player | None:
        """The guild's live player, or ``None`` when the bot is not in a voice channel."""
        player = ctx.voice_client
        if isinstance(player, Player) and player.is_connected and not player.is_dead:
            return player
        return None

    async def _require_player(self, ctx: Context[Bot]) -> Player | None:
        player = self._get_player(ctx)
        if player is None:
            await ctx.reply(
                view=NoticeLayout.warning(
                    "Bot is not connected to a voice channel.",
                    footer=f"Join a voice channel and use `{ctx.clean_prefix}join`.",
                )
            )
        return player

    async def _require_author_voice_channel(self, ctx: Context[Bot]) -> discord.VoiceChannel | None:
        voice_state = ctx.author.voice if isinstance(ctx.author, discord.Member) else None
        channel = voice_state.channel if voice_state is not None else None
        if isinstance(channel, discord.VoiceChannel):
            return channel

        unsupported = isinstance(channel, discord.StageChannel)
        body = "Stage channels are not supported." if unsupported else "You need to be in a voice channel to do that."
        await ctx.reply(view=NoticeLayout.warning(body))
        return None

    async def _require_listener(self, ctx: Context[Bot], player: Player) -> discord.Member | None:
        """The author as a member of the player's voice channel; anyone else may not control playback."""
        author = ctx.author
        if isinstance(author, discord.Member) and author.voice is not None and author.voice.channel == player.channel:
            return author

        await ctx.reply(view=NoticeLayout.warning(f"You need to be in {player.channel.mention} to control playback."))
        return None

    async def _require_dj(self, ctx: Context[Bot], player: Player, member: discord.Member) -> bool:
        if player.is_dj(member):
            return True

        dj = player.dj
        who = dj.mention if dj is not None else "the DJ"
        await ctx.reply(view=NoticeLayout.error(f"Only {who} can do that."), allowed_mentions=discord.AllowedMentions.none())
        return False

    async def _connect(self, ctx: Context[Bot], channel: discord.VoiceChannel) -> Player | None:
        """Join ``channel`` with a fresh player, explaining any failure to the user."""
        if ctx.guild is not None and not channel.permissions_for(ctx.guild.me).connect:
            await ctx.reply(view=NoticeLayout.error(f"Bot lacks permission to connect to {channel.mention}."))
            return None

        # Drop a stale voice client (for example after Lavalink lost the player) before reconnecting.
        stale = ctx.voice_client
        if isinstance(stale, Player):
            await stale.teardown()
        elif stale is not None:
            await stale.disconnect(force=True)

        try:
            player = await channel.connect(cls=Player)
        except pomice.NoNodesAvailable:
            await ctx.reply(view=NoticeLayout.error(NO_NODES_MESSAGE))
            return None
        except (discord.ClientException, TimeoutError) as exc:
            _log.warning("Could not connect to voice channel %s (%s): %s", channel, channel.id, exc)
            await ctx.reply(view=NoticeLayout.error(f"Bot could not connect to {channel.mention}.", footer=str(exc)))
            return None

        player.ctx = ctx
        return player

    async def _search(self, ctx: Context[Bot], query: str) -> SearchResult | None:
        """Resolve ``query`` to tracks, trying each search backend in turn; failures are reported to the user."""
        try:
            node = self.bot.lavalink_node_pool.get_best_node(algorithm=pomice.NodeAlgorithm.by_players)
        except pomice.NoNodesAvailable:
            await ctx.reply(view=NoticeLayout.error(NO_NODES_MESSAGE))
            return None

        last_error: pomice.TrackLoadError | None = None
        for search_type in SEARCH_ORDER:
            try:
                result = await node.get_tracks(query, ctx=ctx, search_type=search_type)
            except pomice.TrackLoadError as exc:
                last_error = exc
                _log.debug("Search for %r via %s failed: %s", query, search_type, exc)
                continue

            if _has_tracks(result):
                return result

        if last_error is not None:
            await ctx.reply(view=NoticeLayout.error("Every source failed to load that query.", footer=str(last_error)))
        else:
            await ctx.reply(view=NoticeLayout.warning(f"Bot found nothing for **{discord.utils.escape_markdown(query)}**."))
        return None

    @staticmethod
    async def _report_vote(ctx: Context[Bot], result: VoteResult, *, passed: str, pending: str) -> None:
        if result.passed:
            await ctx.reply(view=NoticeLayout.success(passed))
        else:
            await ctx.reply(view=NoticeLayout.info(pending, footer=f"{result.votes}/{result.required} votes needed."))

    # Commands

    @commands.command(name="join", aliases=["connect"])
    async def join(self, ctx: Context[Bot]) -> None:
        """Connects the bot to your current voice channel."""
        channel = await self._require_author_voice_channel(ctx)
        if channel is None:
            return

        player = self._get_player(ctx)
        if player is not None:
            if player.channel == channel:
                await ctx.reply(view=NoticeLayout.info(f"Bot is already connected to {channel.mention}."))
            else:
                await ctx.reply(
                    view=NoticeLayout.warning(
                        f"Bot is already connected to {player.channel.mention}.",
                        footer=f"Use `{ctx.clean_prefix}forcejoin` to move me.",
                    )
                )
            return

        if await self._connect(ctx, channel) is not None:
            await ctx.reply(view=NoticeLayout.success(f"Joined {channel.mention}."))

    @commands.command(name="forcejoin", aliases=["fj"])
    @commands.has_permissions(manage_channels=True)
    async def force_join(self, ctx: Context[Bot]) -> None:
        """Moves the bot to your current voice channel, even if it is already connected elsewhere."""
        channel = await self._require_author_voice_channel(ctx)
        if channel is None:
            return

        player = self._get_player(ctx)
        if player is None:
            if await self._connect(ctx, channel) is not None:
                await ctx.reply(view=NoticeLayout.success(f"Joined {channel.mention}."))
            return

        if player.channel == channel:
            await ctx.reply(view=NoticeLayout.info(f"Bot is already in {channel.mention}."))
            return

        if ctx.guild is not None and not channel.permissions_for(ctx.guild.me).connect:
            await ctx.reply(view=NoticeLayout.error(f"Bot lacks permission to connect to {channel.mention}."))
            return

        await player.move_to(channel)
        await ctx.reply(view=NoticeLayout.success(f"Moved to {channel.mention}."))

    @commands.command(name="leave", aliases=["disconnect", "dc"])
    async def leave(self, ctx: Context[Bot]) -> None:
        """Disconnects the bot from the voice channel. Only the DJ can do this."""
        player = await self._require_player(ctx)
        if player is None:
            return

        member = await self._require_listener(ctx, player)
        if member is None or not await self._require_dj(ctx, player, member):
            return

        await player.teardown()
        await ctx.reply(view=NoticeLayout.success("Disconnected from the voice channel."))

    @commands.command(name="play", aliases=["p"])
    async def play(
        self,
        ctx: Context[Bot],
        *,
        query: str = commands.parameter(description="The URL or search term to play."),
    ) -> None:
        """Queues a track or playlist from a URL or search term."""
        player = await self._require_player(ctx)
        if player is None or await self._require_listener(ctx, player) is None:
            return

        async with ctx.typing():
            result = await self._search(ctx, query)
        if result is None:
            return

        if isinstance(result, pomice.Playlist):
            tracks = result.tracks
            body = f"Queued **{plural(len(tracks)):track}** from **{discord.utils.escape_markdown(result.name)}**."
        else:
            tracks = result[:1]
            body = f"Queued {describe_track(tracks[0])}."

        await player.enqueue(tracks)

        waiting = len(player.queue)
        footer = f"{plural(waiting):track} waiting in the queue." if waiting else "Playing now."
        await ctx.reply(view=NoticeLayout.success(body, footer=footer, thumbnail=tracks[0].thumbnail))

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx: Context[Bot]) -> None:
        """Skips the current track. The DJ skips at once; everyone else votes."""
        player = await self._require_player(ctx)
        if player is None:
            return

        member = await self._require_listener(ctx, player)
        if member is None:
            return

        if player.current is None:
            await ctx.reply(view=NoticeLayout.info("Nothing is playing right now."))
            return

        result = await player.vote_skip(member)
        await self._report_vote(ctx, result, passed="Skipped the current track.", pending="Your vote to skip has been counted.")

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx: Context[Bot]) -> None:
        """Displays the current queue."""
        player = await self._require_player(ctx)
        if player is None:
            return

        tracks = list(player.queue)
        if not tracks:
            await ctx.reply(
                view=NoticeLayout.info("The queue is empty.", footer=f"Add something with `{ctx.clean_prefix}play <url or search>`."),
            )
            return

        lines = [f"`{index}.` {describe_track(track)}" for index, track in enumerate(tracks, start=1)]
        pages: list[list[discord.ui.Item]] = [[discord.ui.TextDisplay("\n".join(chunk))] for chunk in discord.utils.as_chunks(lines, QUEUE_PAGE_SIZE)]

        duration = sum(track.length for track in tracks if not track.is_stream)
        header = discord.ui.TextDisplay(f"## Queue\n{plural(len(tracks)):track} \N{MIDDLE DOT} {format_clock_duration(duration)}")

        current = player.current
        footer = discord.ui.TextDisplay(f"-# Now playing: {describe_track(current)}" if current is not None else "-# Nothing is playing.")

        view = PaginationLayout(ctx.author, header=header, footer=footer, items=pages)
        await view.start(ctx)

    @commands.command(name="nowplaying", aliases=["np"])
    async def now_playing(self, ctx: Context[Bot]) -> None:
        """Shows the currently playing track."""
        player = await self._require_player(ctx)
        if player is None:
            return

        track = player.current
        if track is None:
            await ctx.reply(view=NoticeLayout.info("Nothing is playing right now."))
            return

        state = "\N{DOUBLE VERTICAL BAR} Paused\n" if player.is_paused else ""
        progress = format_progress(player.position, track.length, is_stream=track.is_stream)
        body = f"{describe_track(track)}\n{state}{progress}"

        requester = track.requester.mention if track.requester is not None else "unknown"
        dj = player.dj
        footer = f"Requested by {requester} \N{MIDDLE DOT} DJ: {dj.mention if dj is not None else 'nobody'} \N{MIDDLE DOT} {plural(len(player.queue)):track} queued"

        await ctx.reply(
            view=NoticeLayout.info(body, title="Now Playing", footer=footer, thumbnail=track.thumbnail),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.command(name="stop")
    async def stop(self, ctx: Context[Bot]) -> None:
        """Stops playback, clears the queue and disconnects. The DJ stops at once; everyone else votes."""
        player = await self._require_player(ctx)
        if player is None:
            return

        member = await self._require_listener(ctx, player)
        if member is None:
            return

        result = await player.vote_stop(member)
        await self._report_vote(
            ctx,
            result,
            passed="Playback stopped and the queue was cleared.",
            pending="Your vote to stop has been counted.",
        )

    # Lavalink events

    @commands.Cog.listener()
    async def on_pomice_track_start(self, player: pomice.Player, track: pomice.Track | None) -> None:
        if isinstance(player, Player):
            player.reset_votes()

    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: pomice.Player, track: pomice.Track | None, reason: str) -> None:
        _log.debug("Track ended: %s (reason: %s)", track.title if track else None, reason)
        if isinstance(player, Player) and reason.lower() in ADVANCE_ON_TRACK_END:
            await player.play_next()

    @commands.Cog.listener()
    async def on_pomice_track_exception(self, player: pomice.Player, track: pomice.Track | None, exception: object) -> None:
        # Lavalink follows a track exception with a track end event, which is what advances the queue.
        _log.warning("Track exception: %s (track: %s)", exception, track.title if track else None)

    @commands.Cog.listener()
    async def on_pomice_track_stuck(self, player: pomice.Player, track: pomice.Track | None, threshold_ms: float) -> None:
        _log.warning("Track stuck for %s ms, skipping: %s", threshold_ms, track.title if track else None)
        if isinstance(player, Player):
            await player.play_next()


async def setup(bot: Bot) -> None:
    await bot.add_cog(Music(bot))
