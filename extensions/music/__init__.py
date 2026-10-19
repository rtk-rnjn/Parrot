from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING, Annotated

import discord
import pomice
from discord.ext import commands

from core.utils import NoticeLayout as Notice
from core.utils import plural

from .models import PRESETS, LoopMode
from .panel import MusicPanel, SearchView, Tab
from .player import LavalinkPlayer, LocalPlayer, MusicPlayer, SessionMixin, VoteResult
from .sources import Resolved, ResolveError, local_available, resolve
from .ui import describe_song

if TYPE_CHECKING:
    from discord.ext.commands import Context

    from core import Bot

_log = logging.getLogger(__name__)

NO_BACKEND_MESSAGE = "No Lavalink node is connected and the local fallback (yt-dlp + FFmpeg) is not available."
ADVANCE_ON_TRACK_END = frozenset({"finished", "loadfailed"})


def parse_clock(text: str) -> int | None:
    """``90``, ``1:30`` or ``1:02:03`` to milliseconds, or ``None`` when it is not a time."""
    try:
        parts = [float(part) for part in text.strip().split(":")]
    except ValueError:
        return None
    if not 1 <= len(parts) <= 3 or any(part < 0 for part in parts):
        return None

    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return int(seconds * 1000)


class Music(commands.Cog):
    """Music with a live control panel. Lavalink first, yt-dlp + FFmpeg when Lavalink is unavailable."""

    help_emoji = "\N{MUSICAL NOTE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        # guild id -> player. Weak, so a player that Discord has dropped disappears from here by itself.
        self.players: weakref.WeakValueDictionary[int, MusicPlayer] = weakref.WeakValueDictionary()
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def cog_unload(self) -> None:
        for player in list(self.players.values()):
            await player.teardown("Music is restarting.")

    @staticmethod
    def _get_player(ctx: Context[Bot]) -> MusicPlayer | None:
        player = ctx.voice_client
        if isinstance(player, SessionMixin) and player.usable:
            return player  # type: ignore[return-value]
        return None

    async def _require_player(self, ctx: Context[Bot]) -> MusicPlayer | None:
        player = self._get_player(ctx)
        if player is None:
            await ctx.reply(
                view=Notice.warning(
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
        await ctx.reply(view=Notice.warning("Stage channels are not supported." if unsupported else "You need to be in a voice channel to do that."))
        return None

    async def _controls(self, ctx: Context[Bot], *, dj: bool = False) -> tuple[MusicPlayer, discord.Member] | None:
        """Player plus the author, provided the author is listening (and is the DJ, when ``dj`` is set)."""
        player = await self._require_player(ctx)
        if player is None:
            return None

        author = ctx.author
        if not (isinstance(author, discord.Member) and author.voice is not None and author.voice.channel == player.channel):
            await ctx.reply(view=Notice.warning(f"You need to be in {player.channel.mention} to control playback."))
            return None

        if dj and not player.is_dj(author):
            who = player.dj.display_name if player.dj is not None else "the DJ"
            await ctx.reply(view=Notice.error(f"Only {who} can do that."))
            return None

        player.text_channel = ctx.channel
        return player, author

    async def _ensure_player(self, ctx: Context[Bot]) -> MusicPlayer | None:
        """The guild's player, joining the author's channel first when the bot is not connected."""
        channel = await self._require_author_voice_channel(ctx)
        if channel is None:
            return None

        player = self._get_player(ctx)
        if player is None:
            player = await self._connect(ctx, channel)
        elif player.channel != channel:
            await ctx.reply(view=Notice.warning(f"You need to be in {player.channel.mention} to queue music."))
            return None

        if player is not None:
            player.text_channel = ctx.channel
        return player

    def _lavalink_ready(self) -> bool:
        try:
            node = self.bot.lavalink_node_pool.get_best_node(algorithm=pomice.NodeAlgorithm.by_players)
        except pomice.NoNodesAvailable:
            return False
        return bool(getattr(node, "is_connected", True))

    async def _connect(self, ctx: Context[Bot], channel: discord.VoiceChannel) -> MusicPlayer | None:
        """Join ``channel`` with Lavalink if it is healthy, otherwise with the local backend."""
        if ctx.guild is not None and not channel.permissions_for(ctx.guild.me).connect:
            await ctx.reply(view=Notice.error(f"Bot lacks permission to connect to {channel.mention}."))
            return None

        backends: list[type[MusicPlayer]] = []
        if self._lavalink_ready():
            backends.append(LavalinkPlayer)
        if local_available():
            backends.append(LocalPlayer)
        if not backends:
            await ctx.reply(view=Notice.error(NO_BACKEND_MESSAGE))
            return None

        # Drop a stale voice client (for example after Lavalink lost the player) before reconnecting.
        stale = ctx.voice_client
        if isinstance(stale, SessionMixin):
            await stale.teardown("Reconnecting.")
        elif stale is not None:
            await stale.disconnect(force=True)

        for backend in backends:
            try:
                player = await channel.connect(cls=backend)
            except pomice.NoNodesAvailable:
                continue  # Lavalink went away between the check and the connect: try the next backend
            except (discord.ClientException, TimeoutError) as exc:
                _log.warning("Could not connect to voice channel %s (%s): %s", channel, channel.id, exc)
                await ctx.reply(view=Notice.error(f"Bot could not connect to {channel.mention}.", footer=str(exc)))
                return None

            player.ctx = ctx
            player.text_channel = ctx.channel
            player.panel = MusicPanel(player)
            if isinstance(player, LavalinkPlayer) and local_available():
                player.failover = self._failover
            self.players[channel.guild.id] = player
            return player

        await ctx.reply(view=Notice.error(NO_BACKEND_MESSAGE))
        return None

    async def _failover(self, player: MusicPlayer, reason: str) -> None:
        """Lavalink kept failing: move the whole session (queue, position, loop, filter, panel) to local playback."""
        async with player.lock:
            if not player.usable or not isinstance(player, LavalinkPlayer):
                return

            channel = player.channel
            state = player.snapshot()
            _log.warning("Guild %s: Lavalink is failing (%s), switching to local playback.", channel.guild.id, reason)
            await player.detach()

            try:
                local = await channel.connect(cls=LocalPlayer)
            except discord.ClientException, TimeoutError:
                _log.exception("Could not start the local fallback in guild %s.", channel.guild.id)
                if state["panel"] is not None:
                    await state["panel"].close("Lavalink failed and the local fallback could not start.")
                return

            self.players[channel.guild.id] = local
            await local.restore(state)
            await local._notify(  # pylint: disable=protected-access
                Notice.warning("Lavalink is having trouble, so playback moved to the local fallback.", footer="Filters and the queue were kept.")
            )

    async def _resolve(self, ctx: Context[Bot], query: str, *, limit: int = 1) -> Resolved | None:
        try:
            async with ctx.typing():
                return await resolve(self.bot, ctx, query, limit=limit)
        except ResolveError as exc:
            if exc.errors:
                await ctx.reply(view=Notice.error("Every source failed to load that query.", footer=exc.errors[-1][:200]))
            else:
                await ctx.reply(view=Notice.warning(f"Bot found nothing for **{discord.utils.escape_markdown(query)}**."))
            return None

    @staticmethod
    async def _report_vote(ctx: Context[Bot], result: VoteResult, *, passed: str, pending: str) -> None:
        if result.passed:
            await ctx.reply(view=Notice.success(passed))
        else:
            await ctx.reply(view=Notice.info(pending, footer=f"{result.votes}/{result.required} votes needed."))

    @commands.command(name="join", aliases=["connect"])
    async def join(self, ctx: Context[Bot]) -> None:
        """Connects the bot to your current voice channel."""
        channel = await self._require_author_voice_channel(ctx)
        if channel is None:
            return

        player = self._get_player(ctx)
        if player is not None:
            if player.channel == channel:
                await ctx.reply(view=Notice.info(f"Bot is already connected to {channel.mention}."))
            else:
                await ctx.reply(
                    view=Notice.warning(
                        f"Bot is already connected to {player.channel.mention}.",
                        footer=f"Use `{ctx.clean_prefix}forcejoin` to move me.",
                    )
                )
            return

        player = await self._connect(ctx, channel)
        if player is not None:
            player.sync_idle()
            await ctx.reply(view=Notice.success(f"Joined {channel.mention}.", footer=f"Backend: {player.backend_name}"))

    @commands.command(name="forcejoin", aliases=["fj"])
    @commands.has_permissions(manage_channels=True)
    async def force_join(self, ctx: Context[Bot]) -> None:
        """Moves the bot to your current voice channel, even if it is already connected elsewhere."""
        channel = await self._require_author_voice_channel(ctx)
        if channel is None:
            return

        player = self._get_player(ctx)
        if player is None:
            player = await self._connect(ctx, channel)
            if player is not None:
                await ctx.reply(view=Notice.success(f"Joined {channel.mention}."))
            return

        if player.channel == channel:
            await ctx.reply(view=Notice.info(f"Bot is already in {channel.mention}."))
            return

        if ctx.guild is not None and not channel.permissions_for(ctx.guild.me).connect:
            await ctx.reply(view=Notice.error(f"Bot lacks permission to connect to {channel.mention}."))
            return

        await player.move_to(channel)
        player.sync_idle()
        await ctx.reply(view=Notice.success(f"Moved to {channel.mention}."))

    @commands.command(name="leave", aliases=["disconnect", "dc"])
    async def leave(self, ctx: Context[Bot]) -> None:
        """Disconnects the bot from the voice channel. Only the DJ can do this."""
        got = await self._controls(ctx, dj=True)
        if got is None:
            return
        player, _ = got

        async with player.lock:
            await player.teardown(f"Disconnected by {ctx.author.display_name}.")
        await ctx.reply(view=Notice.success("Disconnected from the voice channel."))

    @commands.command(name="play", aliases=["p"])
    async def play(
        self,
        ctx: Context[Bot],
        *,
        query: str = commands.parameter(description="The URL or search term to play."),
    ) -> None:
        """Queues a track or playlist from a URL or search term. Joins your channel if needed."""
        player = await self._ensure_player(ctx)
        if player is None:
            return
        resolved = await self._resolve(ctx, query)
        if resolved is None:
            return

        started_idle = player.song is None
        async with player.lock:
            if not player.usable:
                await ctx.reply(view=Notice.warning("The player disconnected while searching. Try again."))
                return
            await player.enqueue(resolved.songs)

        # A single track that starts immediately is already announced by the panel; say something otherwise.
        if resolved.name is not None:
            body = f"Queued **{plural(len(resolved.songs)):track}** from **{discord.utils.escape_markdown(resolved.name)}**."
        elif started_idle:
            return
        else:
            body = f"Queued {describe_song(resolved.songs[0])}."

        footer = f"{plural(len(player.queue)):track} waiting in the queue \N{MIDDLE DOT} via {resolved.via}"
        await ctx.reply(view=Notice.success(body, footer=footer, thumbnail=resolved.songs[0].thumbnail))

    @commands.command(name="search")
    async def search(
        self,
        ctx: Context[Bot],
        *,
        query: str = commands.parameter(description="What to search for."),
    ) -> None:
        """Shows search results and lets you pick what to queue."""
        player = await self._ensure_player(ctx)
        if player is None:
            return
        resolved = await self._resolve(ctx, query, limit=10)
        if resolved is None:
            return

        view = SearchView(ctx, player, resolved.songs[:10])
        view.message = await ctx.reply(view=view)

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx: Context[Bot]) -> None:
        """Skips the current track. The DJ skips at once; everyone else votes."""
        got = await self._controls(ctx)
        if got is None:
            return
        player, member = got

        if player.song is None:
            await ctx.reply(view=Notice.info("Nothing is playing right now."))
            return

        async with player.lock:
            result = await player.vote_skip(member)
        await self._report_vote(ctx, result, passed="Skipped the current track.", pending="Your vote to skip has been counted.")
        await player.refresh_panel()

    @commands.command(name="stop")
    async def stop(self, ctx: Context[Bot]) -> None:
        """Stops playback, clears the queue and disconnects. The DJ stops at once; everyone else votes."""
        got = await self._controls(ctx)
        if got is None:
            return
        player, member = got

        async with player.lock:
            result = await player.vote_stop(member)
        await self._report_vote(ctx, result, passed="Playback stopped and the queue was cleared.", pending="Your vote to stop has been counted.")
        await player.refresh_panel()

    @commands.command(name="pause")
    async def pause(self, ctx: Context[Bot]) -> None:
        """Pauses playback. The DJ pauses at once; everyone else votes."""
        got = await self._controls(ctx)
        if got is None:
            return
        player, member = got

        if player.song is None or player.paused:
            await ctx.reply(view=Notice.info("Nothing is playing, or it is already paused."))
            return

        async with player.lock:
            result = await player.vote_pause(member)
        await self._report_vote(ctx, result, passed="Paused.", pending="Your vote to pause has been counted.")
        await player.refresh_panel()

    @commands.command(name="resume", aliases=["unpause"])
    async def resume(self, ctx: Context[Bot]) -> None:
        """Resumes playback. The DJ resumes at once; everyone else votes."""
        got = await self._controls(ctx)
        if got is None:
            return
        player, member = got

        if not player.paused:
            await ctx.reply(view=Notice.info("Playback is not paused."))
            return

        async with player.lock:
            result = await player.vote_resume(member)
        await self._report_vote(ctx, result, passed="Resumed.", pending="Your vote to resume has been counted.")
        await player.refresh_panel()

    @commands.command(name="shuffle")
    async def shuffle(self, ctx: Context[Bot]) -> None:
        """Shuffles the queue. The DJ shuffles at once; everyone else votes."""
        got = await self._controls(ctx)
        if got is None:
            return
        player, member = got

        if len(player.queue) < 2:
            await ctx.reply(view=Notice.info("There is nothing to shuffle."))
            return

        async with player.lock:
            result = await player.vote_shuffle(member)
        await self._report_vote(ctx, result, passed="Shuffled the queue.", pending="Your vote to shuffle has been counted.")
        await player.refresh_panel()

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx: Context[Bot]) -> None:
        """Opens the panel on the queue tab."""
        if (player := await self._require_player(ctx)) is None or player.panel is None:
            return
        player.text_channel = ctx.channel
        await player.panel.open(Tab.queue)

    @commands.command(name="nowplaying", aliases=["np"])
    async def now_playing(self, ctx: Context[Bot]) -> None:
        """Brings the music panel down to the bottom of this channel."""
        if (player := await self._require_player(ctx)) is None or player.panel is None:
            return
        player.text_channel = ctx.channel
        await player.panel.open(Tab.player)

    @commands.command(name="volume", aliases=["vol"])
    async def volume(
        self,
        ctx: Context[Bot],
        level: Annotated[int, commands.Range[int, 0, 150]] | None = commands.parameter(default=None, description="Volume from 0 to 150."),
    ) -> None:
        """Shows or sets the volume. Only the DJ can change it."""
        got = await self._controls(ctx, dj=level is not None)
        if got is None:
            return
        player, _ = got

        if level is None:
            await ctx.reply(view=Notice.info(f"Volume is at **{player.volume_level}%**."))
            return

        async with player.lock:
            await player.set_volume_level(level)
        await ctx.reply(view=Notice.success(f"Volume set to **{player.volume_level}%**."))
        await player.refresh_panel()

    @commands.command(name="loop", aliases=["repeat"])
    async def loop(
        self,
        ctx: Context[Bot],
        mode: str | None = commands.parameter(default=None, description="off, track or queue. Leave empty to cycle."),
    ) -> None:
        """Sets the loop mode. Only the DJ can change it."""
        got = await self._controls(ctx, dj=True)
        if got is None:
            return

        player, _ = got

        if mode is None:
            player.loop_mode = player.loop_mode.next
        else:
            try:
                player.loop_mode = LoopMode[mode.lower()]
            except KeyError:
                await ctx.reply(view=Notice.warning("Pick one of `off`, `track` or `queue`."))
                return

        await ctx.reply(view=Notice.success(f"Loop mode: **{player.loop_mode.value}**."))
        await player.refresh_panel()

    @commands.command(name="seek")
    async def seek(
        self,
        ctx: Context[Bot],
        position: str = commands.parameter(description="A time such as 90, 1:30 or 1:02:03."),
    ) -> None:
        """Jumps to a position in the current track. Only the DJ can do this."""
        got = await self._controls(ctx, dj=True)
        if got is None:
            return
        player, _ = got

        song = player.song
        target = parse_clock(position)
        if song is None or song.is_stream:
            await ctx.reply(view=Notice.info("There is nothing seekable playing right now."))
            return
        if target is None or (song.length > 0 and target >= song.length):
            await ctx.reply(view=Notice.warning("Give a time inside the track, like `1:30`."))
            return

        async with player.lock:
            await player.seek_to(target)
        await ctx.reply(view=Notice.success(f"Jumped to **{position}**."))
        await player.refresh_panel()

    @commands.command(name="filter", aliases=["fx"])
    async def filter(
        self,
        ctx: Context[Bot],
        name: str | None = commands.parameter(default=None, description="A filter name, or `off`. Leave empty to list them."),
    ) -> None:
        """Applies an audio filter such as nightcore or bassboost. Only the DJ can change it."""
        if name is None:
            listing = "\n".join(f"{preset.emoji} `{preset.key}`: {preset.description}" for preset in PRESETS.values())
            await ctx.reply(
                view=Notice.info(
                    listing, title="Filters", footer=f"Use `{ctx.clean_prefix}filter <name>` or `off`, or open the Filters tab on the panel."
                )
            )
            return

        got = await self._controls(ctx, dj=True)
        if got is None:
            return
        player, _ = got

        key = name.lower()
        if key not in PRESETS and key != "off":
            await ctx.reply(view=Notice.warning(f"Unknown filter. Try `{ctx.clean_prefix}filter` to list them."))
            return

        try:
            async with player.lock:
                await player.set_preset(None if key == "off" else key)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _log.warning("Could not apply filter %r: %s", key, exc)
            await ctx.reply(view=Notice.error("That filter could not be applied.", footer=str(exc)[:200]))
            return

        await ctx.reply(view=Notice.success("Filter removed." if key == "off" else f"Applied **{PRESETS[key].label}**."))
        await player.refresh_panel()

    # @commands.command(name="remove")
    # async def remove(
    #     self,
    #     ctx: Context[Bot],
    #     position: Annotated[int, commands.Range[int, 1]] = commands.parameter(description="The queue position to remove."),
    # ) -> None:
    #     """Removes a track from the queue. The DJ or the person who requested it can do this."""
    #     if (got := await self._controls(ctx)) is None:
    #         return
    #     player, member = got

    #     async with player.lock:
    #         if position > len(player.queue):
    #             await ctx.reply(view=Notice.warning(f"The queue only has {plural(len(player.queue)):track}."))
    #             return

    #         song = player.queue[position - 1]
    #         if not (player.is_dj(member) or (song.requester is not None and song.requester.id == member.id)):
    #             await ctx.reply(view=Notice.error("Only the DJ or the person who requested it can remove that."))
    #             return
    #         player.queue.remove(position - 1)

    #     await ctx.reply(view=Notice.success(f"Removed {describe_song(song)}."))
    #     await player.refresh_panel()

    @commands.command(name="clear")
    async def clear(self, ctx: Context[Bot]) -> None:
        """Clears the queue but keeps the current track playing. Only the DJ can do this."""
        got = await self._controls(ctx, dj=True)
        if got is None:
            return
        player, _ = got

        async with player.lock:
            player.queue.clear()
        await ctx.reply(view=Notice.success("Cleared the queue."))
        await player.refresh_panel()

    @commands.Cog.listener()
    async def on_pomice_track_start(self, player: pomice.Player, track: pomice.Track | None) -> None:
        if isinstance(player, LavalinkPlayer):
            player.failures = 0

    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: pomice.Player, track: pomice.Track | None, reason: str) -> None:
        _log.debug("Track ended: %s (reason: %s)", track.title if track else None, reason)
        if not isinstance(player, LavalinkPlayer) or reason.lower() not in ADVANCE_ON_TRACK_END:
            return

        # The track may already have been replaced by a skip, so check before and after taking the lock.
        if player.song is None or not player.song.is_track(track):
            return
        async with player.lock:
            if player.song is not None and player.song.is_track(track):
                await player.advance()

    @commands.Cog.listener()
    async def on_pomice_track_exception(self, player: pomice.Player, track: pomice.Track | None, exception: object) -> None:
        # Lavalink follows a track exception with a track end event, which is what advances the queue.
        _log.warning("Track exception: %s (track: %s)", exception, track.title if track else None)
        if isinstance(player, LavalinkPlayer):
            player.note_failure(str(exception))

    @commands.Cog.listener()
    async def on_pomice_track_stuck(self, player: pomice.Player, track: pomice.Track | None, threshold_ms: float) -> None:
        _log.warning("Track stuck for %s ms, skipping: %s", threshold_ms, track.title if track else None)
        if not isinstance(player, LavalinkPlayer) or player.song is None or not player.song.is_track(track):
            return

        player.note_failure("track stuck")
        async with player.lock:
            if player.song is not None and player.song.is_track(track):
                await player.advance(skipped=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        player = self.players.get(member.guild.id)
        if player is None or player.torn_down:
            return

        if self.bot.user is not None and member.id == self.bot.user.id:
            if after.channel is None:
                await player.teardown("I was disconnected from the voice channel.")
            return

        channel = player.channel
        if channel is None or channel not in (before.channel, after.channel):
            return

        player.sync_idle()
        await player.refresh_panel()  # the DJ and listener count may have changed


async def setup(bot: Bot) -> None:
    await bot.add_cog(Music(bot))
