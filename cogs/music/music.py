from __future__ import annotations

import discord
import pomice
import math
import random

from discord.ext import commands
from core import Context, Parrot
from utilities.formats import Player


class Music(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        # In order to initialize a node, or really do anything in this library,
        # you need to make a node pool

    async def cog_load(
        self,
    ):
        self.pomice = self.bot.pomice

    async def required(self, ctx: Context):
        """Method which returns required votes based on amount of members in a channel."""
        player: Player = ctx.voice_client
        channel = self.bot.get_channel(int(player.channel.id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    async def is_privileged(self, ctx: Context):
        """Check whether the user is an Admin or DJ."""
        player: Player = ctx.voice_client

        return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

    # The following are events from pomice.events
    # We are using these so that if the track either stops or errors,
    # we can just skip to the next track

    # Of course, you can modify this to do whatever you like

    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: Player, track, _):
        await player.do_next()

    @commands.Cog.listener()
    async def on_pomice_track_stuck(self, player: Player, track, _):
        await player.do_next()

    @commands.Cog.listener()
    async def on_pomice_track_exception(self, player: Player, track, _):
        await player.do_next()

    @commands.command(name="join", aliases=["j"])
    async def join(self, ctx: Context, *, channel: discord.VoiceChannel = None) -> None:
        if not channel:
            channel = getattr(ctx.author.voice, "channel", None)
            if not channel:
                await ctx.send(
                    "You must be in a voice channel in order to use this command!"
                )
                return

        # With the release of discord.py 1.7, you can now add a compatible
        # VoiceProtocol class as an argument in VoiceChannel.connect().
        # This library takes advantage of that and is how you initialize a player.
        await ctx.author.voice.channel.connect(cls=Player)
        player: Player = ctx.voice_client

        # Set the player context so we can use it so send messages
        await player.set_context(ctx=ctx)
        await ctx.send(f"Joined the voice channel `{channel.name}`")

    @commands.command(aliases=["disconnect", "dc", "disc", "lv", "fuckoff"])
    async def leave(self, ctx: Context):
        if not (player := ctx.voice_client):
            return await ctx.send(
                "You must have the bot in a channel in order to use this command",
                delete_after=7,
            )

        await player.destroy()
        await ctx.send("Player has left the channel.")

    @commands.command(aliases=["pla", "p"])
    async def play(self, ctx: Context, *, search: str) -> None:
        # Checks if the player is in the channel before we play anything
        if not (player := ctx.voice_client):
            await ctx.invoke(self.join)

        # If you search a keyword, Pomice will automagically search the result using YouTube
        # You can pass in "search_type=" as an argument to change the search type
        # i.e: player.get_tracks("query", search_type=SearchType.ytmsearch)
        # will search up any keyword results on YouTube Music

        # We will also set the context here to get special features, like a track.requester object
        results = await player.get_tracks(search, ctx=ctx)

        if not results:
            await ctx.send("No results were found for that search term", delete_after=7)
            return

        if isinstance(results, pomice.Playlist):
            for track in results.tracks:
                await player.queue.put(track)
        else:
            track = results[0]
            await player.queue.put(track)

        if not player.is_playing:
            await player.do_next()

    @commands.command(aliases=["pau", "pa"])
    async def pause(self, ctx: Context):
        """Pause the currently playing song."""
        if not (player := ctx.voice_client):
            return await ctx.send(
                "You must have the bot in a channel in order to use this command",
                delete_after=7,
            )

        if player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has paused the player.", delete_after=10)
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = await self.required(ctx)
        player.pause_votes.add(ctx.author)

        if len(player.pause_votes) >= required:
            await ctx.send("Vote to pause passed. Pausing player.", delete_after=10)
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to pause the player. Votes: {len(player.pause_votes)}/{required}",
                delete_after=15,
            )

    @commands.command(aliases=["res", "r"])
    async def resume(self, ctx: Context):
        """Resume a currently paused player."""
        if not (player := ctx.voice_client):
            return await ctx.send(
                "You must have the bot in a channel in order to use this command",
                delete_after=7,
            )

        if not player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has resumed the player.", delete_after=10)
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = await self.required(ctx)
        player.resume_votes.add(ctx.author)

        if len(player.resume_votes) >= required:
            await ctx.send("Vote to resume passed. Resuming player.", delete_after=10)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to resume the player. Votes: {len(player.resume_votes)}/{required}",
                delete_after=15,
            )

    @commands.command(aliases=["nex", "next", "sk"])
    async def skip(self, ctx: Context):
        """Skip the currently playing song."""
        if not (player := ctx.voice_client):
            return await ctx.send(
                "You must have the bot in a channel in order to use this command",
                delete_after=7,
            )

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has skipped the song.", delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        if ctx.author == player.current.requester:
            await ctx.send("The song requester has skipped the song.", delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        required = await self.required(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.send("Vote to skip passed. Skipping song.", delete_after=10)
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to skip the song. Votes: {len(player.skip_votes)}/{required} ",
                delete_after=15,
            )

    @commands.command()
    async def stop(self, ctx: Context):
        """Stop the player and clear all internal states."""
        if not (player := ctx.voice_client):
            return await ctx.send(
                "You must have the bot in a channel in order to use this command",
                delete_after=7,
            )

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has stopped the player.", delete_after=10)
            return await player.teardown()

        required = await self.required(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.send("Vote to stop passed. Stopping the player.", delete_after=10)
            await player.teardown()
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to stop the player. Votes: {len(player.stop_votes)}/{required}",
                delete_after=15,
            )

    @commands.command(aliases=["mix", "shuf"])
    async def shuffle(self, ctx: Context):
        """Shuffle the players queue."""
        if not (player := ctx.voice_client):
            return await ctx.send(
                "You must have the bot in a channel in order to use this command",
                delete_after=7,
            )

        if not player.is_connected:
            return

        if player.queue.qsize() < 3:
            return await ctx.send(
                "The queue is empty. Add some songs to shuffle the queue.",
                delete_after=15,
            )

        if self.is_privileged(ctx):
            await ctx.send("An admin or DJ has shuffled the queue.", delete_after=10)
            player.shuffle_votes.clear()
            return random.shuffle(player.queue._queue)

        required = await self.required(ctx)
        player.shuffle_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.send(
                "Vote to shuffle passed. Shuffling the queue.", delete_after=10
            )
            player.shuffle_votes.clear()
            random.shuffle(player.queue._queue)
        else:
            await ctx.send(
                f"{ctx.author.mention} has voted to shuffle the queue. Votes: {len(player.shuffle_votes)}/{required}",
                delete_after=15,
            )

    @commands.command(aliases=["v", "vol"])
    async def volume(self, ctx: Context, *, vol: int):
        """Change the players volume, between 1 and 100."""
        if not (player := ctx.voice_client):
            return await ctx.send(
                "You must have the bot in a channel in order to use this command",
                delete_after=7,
            )

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send("Only the DJ or admins may change the volume.")

        if not 0 < vol < 101:
            return await ctx.send("Please enter a value between 1 and 100.")

        await player.set_volume(vol)
        await ctx.send(f"Set the volume to **{vol}**%", delete_after=7)
