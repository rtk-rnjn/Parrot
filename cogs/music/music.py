from __future__ import annotations

import asyncio
import itertools
import random
from asyncio import Queue, QueueEmpty
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union

import arrow
import discord
import wavelink
from core import Cog
from discord.ext import commands
from utilities.checks import in_voice, is_dj
from wavelink.ext import spotify

if TYPE_CHECKING:
    from collections import deque

    from core import Context, Parrot


class Music(Cog):
    """Music related commands."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self._cache: Dict[int, Queue[wavelink.Track]] = {}
        self._config: Dict[int, dict] = {}

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{MULTIPLE MUSICAL NOTES}")

    def make_embed(self, ctx: Context, track: wavelink.Track) -> discord.Embed:
        embed = discord.Embed(
            title=track.title,
            color=self.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        if track.uri is not None:
            embed.url = track.uri
        embed.add_field(name="Author", value=track.author, inline=True)
        duration = arrow.utcnow().shift(seconds=track.duration).humanize(only_distance=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.set_footer(
            text=f"Requested by {ctx.author.name}",
            icon_url=ctx.author.display_avatar.url,
        )
        if hasattr(track, "thumbnail") and track.thumbnail is not None:
            embed.set_thumbnail(url=track.thumbnail)
        return embed

    @commands.command()
    @commands.bot_has_guild_permissions(connect=True)
    async def join(self, ctx: Context, channel: Optional[discord.VoiceChannel] = None):
        """Joins a voice channel. If no channel is given then it will connects to your channel"""
        dj_role = await ctx.dj_role()
        if ctx.voice_client is None or dj_role in ctx.author.roles:
            channel = getattr(ctx.author.voice, "channel", channel)

            if channel is None:
                raise commands.BadArgument(
                    "You must be in a voice channel or must provide the channel argument"
                )

            await channel.connect(cls=wavelink.Player)
            await ctx.send(f"{ctx.author.mention} joined {channel.mention}")
            self._cache[ctx.guild.id] = Queue()
            return

        vc: wavelink.Player = ctx.voice_client
        if vc.is_playing():
            await ctx.send(
                f"{ctx.author.mention} bot is already already playing music in {vc.channel.mention}"
            )
            return

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    async def move(self, ctx: Context, *, channel: Optional[discord.VoiceChannel] = None):
        """Moves the bot to a different voice channel"""
        if ctx.voice_client is None:
            return self.join(ctx, channel)

        vc: wavelink.Player = ctx.voice_client

        await vc.move_to(channel)
        await ctx.send(f"{ctx.author.mention} moved to {vc.channel.mention}")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def loop(self, ctx: Context, info: Optional[Literal["all", "current"]] = "all"):
        """To loop the current song or the queue"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        try:
            self._config[ctx.guild.id]
        except KeyError:
            self._config[ctx.guild.id] = {}

        self._config[ctx.guild.id]["loop"] = not self._config[ctx.guild.id].get("loop", False)
        self._config[ctx.guild.id]["loop_type"] = info
        await ctx.send(
            f"{ctx.author.mention} looping is now **{'enabled' if self._config[ctx.guild.id]['loop'] else 'disabled'}**"
        )

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def shuffle(self, ctx: Context):
        """Shuffles the queue"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        try:
            self._cache[ctx.guild.id]
        except KeyError:
            self._cache[ctx.guild.id] = Queue()

        if queue := self._cache[ctx.guild.id]:
            if queue.empty():
                await ctx.send(f"{ctx.author.mention} queue is empty.")
                return

            random.shuffle(queue._queue)  # type: ignore

            await ctx.send(f"{ctx.author.mention} queue has been shuffled.")
            return

    @commands.command(name="filter")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    async def _filter(self, ctx: Context):
        """Set filter for the song"""

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    async def disconnect(self, ctx: Context):
        """Disconnects from the voice channel"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")
        await ctx.send(f"{ctx.author.mention} disconnected")

        await ctx.voice_client.disconnect()

    @commands.group(invoke_without_command=True)
    @commands.check_any(in_voice())
    @commands.bot_has_guild_permissions(connect=True)
    async def play(
        self,
        ctx: Context,
        *,
        search: Union[wavelink.YouTubeTrack, wavelink.SoundCloudTrack, str],
    ):
        """Play a song with the given search query. If not connected, connect to your voice channel."""
        if ctx.invoked_subcommand is None:
            if ctx.voice_client is None:
                vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            else:
                vc: wavelink.Player = ctx.voice_client  # type: ignore

            if isinstance(search, str):
                search = wavelink.PartialTrack(query=search)

            if vc.is_playing():
                try:
                    self._cache[ctx.guild.id]
                except KeyError:
                    self._cache[ctx.guild.id] = Queue()

                self._cache[ctx.guild.id].put_nowait(search)
                await ctx.send(f"{ctx.author.mention} added **{search.title}** to the queue")
                return

            await vc.play(search)
            await ctx.send(f"{ctx.author.mention} Now playing", embed=self.make_embed(ctx, search))

    @play.command(name="spotify")
    async def play_spotify(self, ctx: Context, *, link: str):
        """Play a song from spotify with the given link"""
        if ctx.voice_client is None:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client  # type: ignore

        with suppress(spotify.SpotifyRequestError):
            tracks = await spotify.SpotifyTrack.search(link)
            try:
                q = self._cache[ctx.guild.id]
            except KeyError:
                self._cache[ctx.guild.id] = Queue()
                q = self._cache[ctx.guild.id]

            for track in tracks:
                q.put_nowait(track)

            if not vc.is_playing():
                np_track = q.get_nowait()
                await vc.play(np_track)
                await ctx.send(
                    f"{ctx.author.mention} Now playing",
                    embed=self.make_embed(ctx, np_track),
                )
                return
            await ctx.send(f"{ctx.author.mention} added **{len(tracks)}** to the queue")
            return
        await ctx.send(f"{ctx.author.mention} Invalid link")

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx: Context):
        """Shows the currently playing song"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")
        await ctx.send(
            f"{ctx.author.mention} Now playing",
            embed=self.make_embed(ctx, channel.track),
        )

    @commands.command(aliases=["skip"])
    @in_voice()
    async def next(self, ctx: Context):
        """Skips the currently playing song"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")
        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")
        try:
            queue = self._cache[ctx.guild.id]
        except KeyError:
            self._cache[ctx.guild.id] = Queue()

        if queue.empty():
            return await ctx.send(f"{ctx.author.mention} There are no more songs in the queue.")

        channel: discord.VoiceChannel = vc.channel
        members = sum(1 for m in channel.members if not m.bot)

        async def __interal_skip(
            *, ctx: Context, vc: wavelink.Player, queue: Queue[wavelink.Track]
        ):
            with suppress(QueueEmpty):
                next_song = queue.get_nowait()
                await vc.play(next_song)
                await ctx.send(
                    f"{ctx.author.mention} Now playing",
                    embed=self.make_embed(ctx, next_song),
                )
                return
            await ctx.send(f"{ctx.author.mention} There are no more songs in the queue.")

        if members <= 2:
            return await __interal_skip(ctx=ctx, vc=vc, queue=queue)

        if members > 2:
            vote = 1
            required_vote = int(members / 2)
            msg: discord.Message = await ctx.send(  # type: ignore
                f"{ctx.author.mention} wants to skip the current song need {required_vote} votes to skip"
            )
            emoji = "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}"
            await msg.add_reaction(emoji)

            def check(reaction: discord.Reaction, user: discord.User) -> bool:
                return (
                    reaction.message.id == msg.id
                    and user.id != ctx.author.id
                    and str(reaction.emoji) == emoji
                    and user.bot is False
                    and user.id in [m.id for m in channel.members]
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check, timeout=abs(vc.track.duration - vc.last_position)
                )
            except asyncio.TimeoutError:
                await msg.delete()
                return
            else:
                vote += 1

            if vote >= required_vote:
                await msg.delete()
                return await __interal_skip(ctx=ctx, vc=vc, queue=queue)

        await __interal_skip(ctx=ctx, vc=vc, queue=queue)

    @commands.command(name="queue")
    async def _queue(self, ctx: Context):
        """Shows the current songs queue"""
        try:
            queue = self._cache[ctx.guild.id]
        except KeyError:
            self._cache[ctx.guild.id] = Queue()
            return await ctx.send(f"{ctx.author.mention} There are no songs in the queue.")

        if queue.empty():
            return await ctx.send(f"{ctx.author.mention} There are no songs in the queue.")

        entries = []
        for track in queue._queue:  # type: ignore
            if track.uri:
                entries.append(f"[{track.title} - {track.author}]({track.uri})")
            else:
                entries.append(f"{track.title} - {track.author}")

        await ctx.paginate(entries=entries, _type="SimplePages")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def stop(self, ctx: Context):
        """Stop the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client  # type: ignore
        await channel.stop()
        await ctx.send(f"{ctx.author.mention} stopped the music.")

        if queue := self._cache.get(ctx.guild.id):
            with suppress(QueueEmpty):
                track = queue.get_nowait()
                await channel.play(track)
                await ctx.send(
                    f"{ctx.author.mention} Now playing",
                    embed=self.make_embed(ctx, track),
                )
                return

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def clear(self, ctx: Context):
        """Clear the queue"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client
        await channel.stop()
        self._cache[ctx.guild.id] = Queue()
        await ctx.send(f"{ctx.author.mention} cleared the queue.")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def pause(self, ctx: Context):
        """Pause the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client
        if channel.is_paused():
            return await ctx.send(f"{ctx.author.mention} player is already paused.")

        if channel.is_playing():
            await channel.pause()
            await ctx.send(f"{ctx.author.mention} paused the music.")
            return

        await ctx.send(f"{ctx.author.mention} player is not playing.")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def resume(self, ctx: Context):
        """Resume the currently paused song."""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client
        if not channel.is_paused():
            return await ctx.send(f"{ctx.author.mention} player is not paused.")

        if channel.is_playing():
            await channel.resume()
            await ctx.send(f"{ctx.author.mention} resumed the music.")
            return

        await ctx.send(f"{ctx.author.mention} player is not playing.")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def volume(self, ctx: Context, volume: int):
        """Change the volume of the currently playing song."""
        if volume < 1 or volume > 100:
            return await ctx.send(
                f"{ctx.author.mention} volume must be between 1 and 100 inclusive."
            )

        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client
        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} player is not playing.")

        await channel.set_volume(volume / 100)
        await ctx.send(f"{ctx.author.mention} player volume set to {volume}%.")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def seek(self, ctx: Context, seconds: int):
        """Seek to a given position in the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client
        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} player is not playing.")

        await channel.seek(seconds)
        await ctx.send(f"{ctx.author.mention} player seeked to {seconds} seconds.")

    @Cog.listener()
    async def on_wavelink_track_end(
        self, player: wavelink.Player, original_track: wavelink.Track, reason: Any
    ):
        try:
            queue = self._cache[player.guild.id]
        except KeyError:
            self._cache[player.guild.id] = Queue()
            return

        with suppress(QueueEmpty):
            try:
                self._config[player.guild.id]
            except KeyError:
                self._config[player.guild.id] = {}

            q: deque = queue._queue  # type: ignore

            if self._config[player.guild.id].get("loop", False):
                if self._config[player.guild.id].get("loop_type", "all") == "all":
                    await player.play(itertools.cycle(q))
                else:
                    await player.play(original_track)
            else:
                track = queue.get_nowait()
                await player.play(track)
