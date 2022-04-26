from __future__ import annotations

import asyncio
import random
import re
from typing import Union
from cogs.meta.robopage import SimplePages

import discord
import pomice
from discord.ext import commands

from core import Parrot, Cog, Context
from utilities.formats import Player

HH_MM_SS_RE = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{1,2}):(?P<s>\d{1,2})")
MM_SS_RE = re.compile(r"(?P<m>\d{1,2}):(?P<s>\d{1,2})")
HUMAN_RE = re.compile(r"(?:(?P<m>\d+)\s*m\s*)?(?P<s>\d+)\s*[sm]")
OFFSET_RE = re.compile(r"(?P<s>(?:\-|\+)\d+)\s*s", re.IGNORECASE)
URL_REG = re.compile(r"https?://(?:www\.)?.+")


def format_time(milliseconds: Union[float, int]) -> str:
    hours, rem = divmod(int(milliseconds // 1000), 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours:2d}:{minutes:02d}:{seconds:2d}"
    if hours == 0:
        return f"{minutes:02d}:{seconds:02d}"


def duration(length) -> str:
    return "{}:{}:{}".format(
        (length / (1000 * 60 * 60)) % 24,
        (length / (1000 * 60)) % 60,
        (length / 1000) % 60,
    )


class ButtonLy(discord.ui.View):
    def __init__(self, ctx: Context, lyrics: str, title: str) -> None:
        super().__init__(timeout=300)
        self.context = ctx
        self.lyrics = lyrics
        self.title = title

    async def on_timeout(self):
        self.clear_items()
        self.stop()

    @discord.ui.button(label="Lyrics", style=discord.ButtonStyle.blurple)
    async def buttonlyrics(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = discord.Embed(
            title=self.title, description=self.lyrics, color=self.ctx.bot.color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Music(
    Cog,
):
    """Best Non-Stop Music Commands!"""

    def __init__(self, bot: Parrot):
        self.bot = bot

    def bot_voice(ctx: Context):
        if ctx.voice_client:
            return True
        raise commands.CheckFailure("I'm not in a voice channel")

    def user_voice(ctx: Context):
        if ctx.author.voice:
            return True
        raise commands.CheckFailure("You must be in voice channel")

    def full_voice(ctx: Context):
        if ctx.me.voice:
            if ctx.author.voice:
                if ctx.me.voice.channel == ctx.author.voice.channel:
                    return True
                raise commands.CheckFailure(
                    f"You must be in the same voice channel, {ctx.me.voice.channel.mention}"
                )
            raise commands.CheckFailure("You must be in voice channel")
        raise commands.CheckFailure("I'm not in a voice channel")

    async def cog_load(self,):
        await self.bot.loop.create_task(self.bot.start_nodes())

    @commands.command(aliases=["connect"])
    @commands.check(user_voice)
    async def join(self, ctx: Context, *, channel: discord.VoiceChannel = None):
        """Joins a Voice Channel."""
        vc = ctx.voice_client
        channel = getattr(ctx.author.voice, "channel", channel)
        if not channel:
            raise commands.CheckFailure()
        if vc:
            return await ctx.send(
                f"Music is already being used in {vc.channel.mention}."
            )

        if channel.permissions_for(ctx.me).connect:
            self.bot.pomice.get_best_node(algorithm=pomice.enums.NodeAlgorithm.by_ping)
            player = Player(self.bot, channel, ctx=ctx)
            vc = await channel.connect(cls=player)
            await ctx.guild.change_voice_state(
                channel=channel, self_mute=False, self_deaf=True
            )
            await ctx.send(f"Connected to {vc.channel.mention}.")
            return vc
        else:
            raise commands.CheckFailure()

    # Disconnect
    @commands.command(
        name="disconnect",
        aliases=["dc", "leave"],
    )
    @commands.check(full_voice)
    async def disconnect(self, ctx: Context):
        """Disconnects from the voice channel"""
        vc: Player = ctx.voice_client
        await vc.destroy()
        return await ctx.send("Disconnected from the voice channel")

    # Play
    @commands.command(
        name="play",
    )
    @commands.check(user_voice)
    async def play(self, ctx: Context, *, query: str):
        """What to search for on Youtube, Spotify or Soundcloud."""
        vc: Player = ctx.voice_client

        if not ctx.author.voice:
            return await ctx.send(
                "Can't join your voice channel. Make sure yor're in the voice channel where I can join."
            )

        if vc is None:
            vc = await ctx.invoke(self.join)

        if vc is not None and vc.channel != ctx.author.voice.channel:
            return await ctx.send(
                f"Sorry, Someone else is using me in {vc.channel.mention}"
            )

        if vc.channel == ctx.author.voice.channel:
            try:
                results = await vc.get_tracks(query=query, ctx=ctx)
            except pomice.TrackLoadError:
                return await ctx.send("An error occured while fetching tracks.")
            a = 0
            if not results:
                return await ctx.send("No results were found for that search term.")

            if isinstance(results, pomice.Playlist):
                for track in results.tracks:
                    new_track = pomice.Track(
                        track_id=track.track_id,
                        info=track.info,
                        ctx=ctx,
                        spotify=track.spotify,
                        search_type=track._search_type,
                        spotify_track=track.spotify_track,
                    )
                    await vc.queue.put(new_track)
                a = len(results.tracks)
            elif isinstance(results, pomice.Track):
                new_track = pomice.Track(
                    track_id=results.track_id,
                    info=results.info,
                    ctx=ctx,
                    spotify=results.spotify,
                    search_type=results._search_type,
                    spotify_track=results.spotify_track,
                )
                await vc.queue.put(new_track)
            else:
                result = results[0]
                new_track = pomice.Track(
                    track_id=result.track_id,
                    info=result.info,
                    ctx=ctx,
                    spotify=result.spotify,
                    search_type=result._search_type,
                    spotify_track=result.spotify_track,
                )
                await vc.queue.put(new_track)
            if not vc.is_playing:
                await vc.play(track=(await vc.queue.get()))

            if a > 0:
                count = f"with {a} songs"
            else:
                count = ""

            await ctx.send(
                f"Added {f'[{results}]({results.uri})' if isinstance(results, pomice.Playlist) else f'[{results[0]}]({results[0].uri})'} {count} to the queue."
            )

    # Stop
    @commands.command(
        name="stop",
        aliases=["stfu"],
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def stop(self, ctx: Context):
        """Stops playing music and clears queue"""
        vc: Player = ctx.voice_client

        if vc.is_playing or vc.is_paused:
            vc.loop = None
            vc.queue._queue.clear()
            await vc.stop()
            return await ctx.send("Stopped playing and cleared the queue.")
        return await ctx.send("Nothing is playing")

    # Skip
    @commands.command(
        name="skip",
        aliases=["sk"],
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def skip(self, ctx: Context):
        """Skips the current music track"""
        vc: Player = ctx.voice_client

        if vc.is_playing:
            if not vc.queue.empty():
                vc.loop = None
                return await vc.stop()

            return await ctx.send("There is nothing in the queue.")
        return await ctx.send("Nothing is playing")

    # Resume
    @commands.command(
        name="resume",
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def resume(self, ctx: Context):
        """Resumes the paused music"""
        vc: Player = ctx.voice_client

        if vc.is_paused:
            await vc.set_pause(pause=False)
            return await ctx.send("Music is now resumed.")
        return await ctx.send("The music is already playing")

    # Pause
    @commands.command(
        name="pause",
        aliases=["pu", "shhh"],
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pause(self, ctx: Context):
        """Pauses playing music"""
        vc: Player = ctx.voice_client

        if vc.is_playing:
            await vc.set_pause(pause=True)
            return await ctx.send("Music is now paused")

        return await ctx.send("Music is already paused.")

    # Loop
    @commands.command(
        name="loop",
        aliases=["lp"],
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def loop(self, ctx: Context):
        """Starts/Stops looping your currently playing track"""
        vc: Player = ctx.voice_client

        if vc.is_playing or vc.is_paused:
            if not vc.loop:
                vc.loop = vc.current
                return await ctx.send(
                    f"Loop has been turned on - [{vc.current.title}]({vc.current.uri}) - {vc.current.author}"
                )

            vc.loop = None
            return await ctx.send(
                f"Loop has been turned off - [{ctx.voice_client.current.title}]({ctx.voice_client.current.uri}) - {ctx.voice_client.current.author}"
            )

        return await ctx.send("Nothing is playing")

    # NowPlaying
    @commands.command(
        name="nowplaying",
        aliases=["np"],
    )
    @commands.check(bot_voice)
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def nowplaying(self, ctx: Context):
        """Shows information about currently playing song"""
        vc: Player = ctx.voice_client

        if vc.is_playing or vc.is_paused:
            await ctx.send(
                "Now playing {vc.current.title} - {vc.current.author}".format(vc=vc)
            )
            return
        await ctx.send("Nothing is playing right now.")

    # Queue
    @commands.command(name="queue", aliases=["q"], help="Shows the music queue")
    @commands.check(bot_voice)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def queue(self, ctx: Context):
        vc: Player = ctx.voice_client

        if len(vc.queue._queue) >= 1:
            paginator = commands.Paginator(prefix=None, suffix=None)

            es = [
                f"**{i.title}** ({format_time(i.length)}) | {i.ctx.author.mention}"
                for i in vc.queue._queue
            ]
            page = SimplePages(es, ctx=ctx)
            await page.start()
        else:
            await ctx.send("There are no songs in the queue.")

    # Queue-Clear
    @commands.command(
        name="clearqueue",
        aliases=["qremove", "qrm"],
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def queue_clear(self, ctx: Context):
        """Clears the music queue"""
        vc: Player = ctx.voice_client
        if not vc.queue.empty():

            value = await ctx.prompt("Do you want to clear the queue?")
            if value is True:
                vc.queue._queue.clear()
                return await ctx.send("Queue has been cleared.")
            if value is False:
                return await ctx.send("Queue has not been cleared.")
        return await ctx.send("Nothing is in the queue.")

    # Replay
    @commands.command(
        name="replay",
        aliases=["restart"],
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def replay(self, ctx: Context):
        """Replays the current song."""
        vc: Player = ctx.voice_client

        if vc.is_playing or vc.is_paused:
            await vc.seek(0)
            return await ctx.send("Started replaying the track")
        return await ctx.send("Nothing is playing")

    # Seek
    @commands.command(name="seek", aliases=["se"])
    @commands.check(full_voice)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def seek(self, ctx, *, time: str):
        """Seeks to a position in the track.
        Accepted formats are HH:MM:SS, MM:SS (or Mm Ss), +Xs and -Xs
        where X is the number of seconds.
        For example:
            - seek 01:23:30
            - seek 00:32
            - seek 2m 4s
            - seek 50s
            - seek +30s
            - seek -23s
        """
        player = ctx.voice_client
        milliseconds = 0

        if not player.is_playing:
            return await ctx.send(
                embed=discord.Embed(description="Nothing is playing!").set_footer(
                    text=""
                )
            )

        if match := HH_MM_SS_RE.fullmatch(time):
            milliseconds += int(match.group("h")) * 3600000
            milliseconds += int(match.group("m")) * 60000
            milliseconds += int(match.group("s")) * 1000
            new_position = milliseconds

        elif match := MM_SS_RE.fullmatch(time):
            milliseconds += int(match.group("m")) * 60000
            milliseconds += int(match.group("s")) * 1000
            new_position = milliseconds

        elif match := OFFSET_RE.fullmatch(time):
            milliseconds += int(match.group("s")) * 1000
            position = player.position
            new_position = position + milliseconds

        elif match := HUMAN_RE.fullmatch(time):
            if m := match.group("m"):
                if match.group("s") and time.lower().endswith("m"):
                    return await ctx.send("Invalid time format!")
                milliseconds += int(m) * 60000
            if s := match.group("s"):
                if time.lower().endswith("m"):
                    milliseconds += int(s) * 60000
                else:
                    milliseconds += int(s) * 1000
            new_position = milliseconds

        else:
            return await ctx.send("Invalid time format!")

        new_position = max(0, min(new_position, player.current.length))
        await player.seek(new_position)
        await ctx.send(f"Seeked to **{format_time(new_position)}**.")

    @commands.command(
        name="volume",
        aliases=["vol"],
    )
    @commands.check(full_voice)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def volume(self, ctx: Context, *, volume: int = None):
        """Sets or Tells the volume of the music"""

        vc: Player = ctx.voice_client
        if vc.is_playing or vc.is_paused:

            if volume == 0:
                await vc.set_volume(volume)
                return await ctx.send(f"Volume has been changed to **{volume}%**")

            if volume:

                if not volume < 0 or not volume > 200:
                    await vc.set_volume(volume)
                    return await ctx.send(f"Volume has been changed to **{volume}%**")

            return await ctx.send(f"The volume is currently at **{vc.volume}%**")

        return await ctx.send("Nothing is playing.")

    # Shuffle
    @commands.command(
        name="shuffle",
        aliases=["shufflequeue"],
    )
    @commands.check(full_voice)
    async def shuffle(self, ctx):
        """Shuffles the music queue."""
        vc: Player = ctx.voice_client
        if not vc.queue.empty():
            random.shuffle(vc.queue._queue)
            await ctx.send("Shuffled all the songs of queue")

    @commands.Cog.listener()
    async def on_pomice_track_start(self, player: pomice.Player, track: pomice.Track):
        ctx = track.ctx
        try:
            await track.old.delete()
        except Exception:
            pass

        track.old = await ctx.send(f"Now Playing: {track.title}", reply=False)

    @commands.Cog.listener()
    async def on_pomice_track_end(
        self, player: Player, track: pomice.Track, reason: str
    ):
        if not player.loop:
            if player.queue.empty():
                return await track.ctx.send(
                    f"**Title:** {track.title} - {track.author}\n**Requester:** {track.requester.mention}\n**Duration:** {format_time(track.length)}"
                )
            return await player.play(track=(await player.queue.get()))
        await player.play(track=player.loop)
