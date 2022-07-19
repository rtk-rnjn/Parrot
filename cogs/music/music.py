from __future__ import annotations
from asyncio import QueueEmpty
from contextlib import suppress
from queue import Queue
from typing import Any, Dict, Optional, Union
import discord

import wavelink
from discord.ext import commands
from core import Context, Parrot, Cog
import arrow


class Music(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self._cache: Dict[int, Queue[wavelink.Track]] = {}

    def make_embed(self, ctx: Context, track: wavelink.Track) -> discord.Embed:
        embed = discord.Embed(
            title=track.title,
            color=self.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        if track.uri is not None:
            embed.url = track.uri
        embed.add_field(name="Author", value=track.author, inline=True)
        duration = (
            arrow.utcnow().shift(seconds=track.duration).humanize(only_distance=True)
        )
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
        channel = getattr(ctx.author.voice, "channel", channel)

        if channel is None:
            raise commands.BadArgument(
                "You must be in a voice channel or must provide the channel argument"
            )

        await channel.connect(cls=wavelink.Player)
        await ctx.send(f"{ctx.author.mention} joined {channel.mention}")
        self._cache[ctx.guild.id] = Queue()

    @commands.command()
    async def disconnect(self, ctx: Context):
        """Disconnects from the voice channel"""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )
        await ctx.send(f"{ctx.author.mention} disconnected")

        await ctx.voice_client.disconnect()

    @commands.command()
    @commands.bot_has_guild_permissions(connect=True)
    async def play(
        self,
        ctx: Context,
        *,
        search: Union[wavelink.YouTubeTrack, wavelink.SoundCloudTrack, str],
    ):
        """Play a song with the given search query.
        If not connected, connect to our voice channel.
        """
        if ctx.voice_client is None:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(
                cls=wavelink.Player
            )
        else:
            vc: wavelink.Player = ctx.voice_client  # type: ignore

        if isinstance(search, str):
            search = wavelink.PartialTrack(query=search)

        if vc.is_playing():
            try:
                self._cache[ctx.guild.id]
            except KeyError:
                self._cache[ctx.guild.id] = Queue()

            self._cache[ctx.guild.id].put(search)
            await ctx.send(
                f"{ctx.author.mention} added {search.title} to the queue"
            )
            return

        await vc.play(search)
        await ctx.send(
            f"{ctx.author.mention} Now playing", embed=self.make_embed(ctx, search)
        )

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx: Context):
        """Shows the currently playing song"""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )
        
        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(
                f"{ctx.author.mention} bot is not playing anything."
            )
        await ctx.send(
            f"{ctx.author.mention} Now playing",
            embed=self.make_embed(ctx, channel.track),
        )

    @commands.command()
    async def next(self, ctx: Context):
        """Skips the currently playing song"""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )
        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(
                f"{ctx.author.mention} bot is not playing anything."
            )
        try:
            queue = self._cache[ctx.guild.id]
        except KeyError:
            self._cache[ctx.guild.id] = Queue()

        if queue.empty():
            return await ctx.send(
                f"{ctx.author.mention} There are no more songs in the queue."
            )
        with suppress(QueueEmpty):
            next_song = queue.get_nowait()
            await channel.play(next_song)
            await ctx.send(
                f"{ctx.author.mention} Now playing",
                embed=self.make_embed(ctx, next_song),
            )
            return
        await channel.stop()
        await ctx.send(f"{ctx.author.mention} Skipped {channel.track}")

    @commands.command()
    async def queue(self, ctx: Context):
        """Shows the current songs queue"""
        try:
            queue = self._cache[ctx.guild.id]
        except KeyError:
            self._cache[ctx.guild.id] = Queue()
            return await ctx.send(
                f"{ctx.author.mention} There are no songs in the queue."
            )

        if queue.empty():
            return await ctx.send(
                f"{ctx.author.mention} There are no songs in the queue."
            )

        entries = []
        while not queue.empty():
            track = queue.get_nowait()
            if track.uri:
                entries.append(f"[{track.title} - {track.author}]({track.uri})")
            else:
                entries.append(f"{track.title} - {track.author}")

        await ctx.paginate(entries=entries, _type="SimplePages")

    @commands.command()
    async def stop(self, ctx: Context):
        """Stop the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )

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
    async def clear(self, ctx: Context):
        """Clear the queue"""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )

        channel: wavelink.Player = ctx.voice_client
        await channel.stop()
        self._cache[ctx.guild.id] = Queue()
        await ctx.send(f"{ctx.author.mention} cleared the queue.")

    @commands.command()
    async def pause(self, ctx: Context):
        """Pause the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )

        channel: wavelink.Player = ctx.voice_client
        if channel.is_paused():
            return await ctx.send(f"{ctx.author.mention} player is already paused.")

        if channel.is_playing():
            await channel.pause()
            await ctx.send(f"{ctx.author.mention} paused the music.")
            return

        await ctx.send(f"{ctx.author.mention} player is not playing.")

    @commands.command()
    async def resume(self, ctx: Context):
        """Resume the currently paused song."""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )

        channel: wavelink.Player = ctx.voice_client
        if not channel.is_paused():
            return await ctx.send(f"{ctx.author.mention} player is not paused.")

        if channel.is_playing():
            await channel.resume()
            await ctx.send(f"{ctx.author.mention} resumed the music.")
            return

        await ctx.send(f"{ctx.author.mention} player is not playing.")

    @commands.command()
    async def volume(self, ctx: Context, volume: int):
        """Change the volume of the currently playing song."""
        if volume < 1 or volume > 100:
            return await ctx.send(
                f"{ctx.author.mention} volume must be between 1 and 100 inclusive."
            )

        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )

        channel: wavelink.Player = ctx.voice_client
        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} player is not playing.")

        await channel.set_volume(volume / 10)
        await ctx.send(f"{ctx.author.mention} player volume set to {volume/10}%.")

    @commands.command()
    async def seek(self, ctx: Context, seconds: int):
        """Seek to a given position in the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )

        channel: wavelink.Player = ctx.voice_client
        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} player is not playing.")

        await channel.seek(seconds)
        await ctx.send(f"{ctx.author.mention} player seeked to {seconds} seconds.")

    @Cog.listener()
    async def on_wavelink_track_end(
        self, player: wavelink.Player, track: wavelink.Track, reason: Any
    ):
        try:
            queue = self._cache[player.guild.id]
        except KeyError:
            return

        with suppress(QueueEmpty):
            await player.play(queue.get_nowait())
