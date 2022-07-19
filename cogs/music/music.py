from __future__ import annotations
from queue import Queue
from typing import Dict, Optional
import discord

import wavelink
from discord.ext import commands
from core import Context, Parrot, Cog


class Music(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        self._cache: Dict[int, Queue] = {}

    @commands.command()
    @commands.has_guild_permissions(connect=True)
    @commands.bot_has_guild_permissions(connect=True)
    async def join(self, ctx: Context, channel: Optional[discord.VoiceChannel] = None):
        """Joins a voice channel. If no channel is given then it will connects to your channel"""
        channel = getattr(ctx.author.voice, "channel", channel)

        if channel is None:
            raise commands.BadArgument(
                "You must be in a voice channel or must provide the channel argument"
            )

        await ctx.send(f"{ctx.author.mention} joined {channel.mention}")
        await channel.connect(cls=wavelink.Player)

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
    @commands.has_guild_permissions(connect=True)
    @commands.bot_has_guild_permissions(connect=True)
    async def play(self, ctx: Context, *, search: wavelink.YouTubeTrack):
        """Play a song with the given search query.
        If not connected, connect to our voice channel.
        """
        if ctx.voice_client is None:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(
                cls=wavelink.Player
            )
        else:
            vc: wavelink.Player = ctx.voice_client  # type: ignore

        await vc.play(search)
        await ctx.send(f"{ctx.author.mention} Now playing: {search.title}")

    @commands.command()
    @commands.has_guild_permissions(connect=True)
    @commands.has_permissions(connect=True)
    async def stop(self, ctx: Context):
        """Stop the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(
                f"{ctx.author.mention} bot is not connected to a voice channel."
            )

        channel: wavelink.Player = ctx.voice_client  # type: ignore
        await channel.stop()
        await ctx.send(f"{ctx.author.mention} stopped the music.")

    @commands.command()
    @commands.has_guild_permissions(connect=True)
    @commands.has_permissions(connect=True)
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
    @commands.has_guild_permissions(connect=True)
    @commands.has_permissions(connect=True)
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
    @commands.has_guild_permissions(connect=True)
    @commands.has_permissions(connect=True)
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

        await channel.set_volume(volume/10)
        await ctx.send(f"{ctx.author.mention} player volume set to {volume/10}%.")

    @commands.command()
    @commands.has_guild_permissions(connect=True)
    @commands.has_permissions(connect=True)
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
