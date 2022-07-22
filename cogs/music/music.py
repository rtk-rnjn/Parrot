from __future__ import annotations

import asyncio
import random
from asyncio import Queue, QueueEmpty
from contextlib import suppress
from typing import TYPE_CHECKING, Deque, Dict, Literal, Optional, Union

import arrow
import discord
import wavelink
from core import Cog
from discord.ext import commands
from utilities.checks import in_voice, is_dj
from wavelink.ext import spotify

if TYPE_CHECKING:
    from core import Context, Parrot

from .__flags import (
    ChannelMixFlag,
    DistortionFlag,
    KaraokeFlag,
    LowPassFlag,
    RotationFlag,
    TimescaleFlag,
    TremoloFlag,
    VibratoFlag,
)
from .__view import MusicView


def get_emoji_from_like_rate(like_rate: float) -> str:
    if like_rate <= 0:
        return "\N{CONFUSED FACE}"
    if like_rate <= 10:
        return "\N{SLIGHTLY SMILING FACE}"
    if like_rate <= 20:
        return "\N{GRINNING FACE}"
    if like_rate <= 40:
        return "\N{SMILING FACE WITH OPEN MOUTH AND SMILING EYES}"
    if like_rate <= 60:
        return "\N{RELIEVED FACE}"
    if like_rate <= 80:
        return "\N{SMILING FACE WITH SMILING EYES}"
    if like_rate <= 100:
        return "\N{SMILING FACE WITH SMILING EYES AND THREE HEARTS}"
    return ""


class Music(Cog):
    """Music related commands."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

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

        if getattr(track, "uri", None) is not None:
            embed.url = track.uri
        embed.add_field(name="Author", value=track.author, inline=True)
        duration = arrow.utcnow().shift(seconds=track.duration).humanize(only_distance=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.set_footer(
            text="Like ratio is ONLY on bot personal usage. Owner of the bot is nothing to do with"
            + " it the actual song. We respect every Artist.\nThe ratio updation may be slow",
            icon_url=ctx.author.display_avatar.url,
        )
        if hasattr(track, "thumbnail") and track.thumbnail is not None:
            embed.set_thumbnail(url=track.thumbnail)

        return embed

    async def like_dislike(
        self,
        track: wavelink.Track,
    ) -> Dict[str, int]:
        data = await self.bot.mongo.extra.songs.find_one(
            {"_id": track.id},
        )
        if data is None:
            return {"likes": 0, "dislikes": 0}
        return {
            "likes": data.get("likes", 0),
            "dislikes": data.get("dislikes", 0),
        }

    async def make_final_embed(self, *, track: wavelink.Track, ctx: Context) -> discord.Embed:
        embed = self.make_embed(ctx, track)
        like_dislike = await self.like_dislike(track)
        try:
            ratio = (
                like_dislike["likes"] / (like_dislike["likes"] + like_dislike["dislikes"])
            ) * 100
        except ZeroDivisionError:
            ratio = 0.0
        embed.add_field(
            name="Like Rate",
            value=f"{round(ratio, 2)}% {get_emoji_from_like_rate(ratio)}",
            inline=False,
        )
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
            f"{ctx.author.mention} looping is now **{'enabled' if self._config[ctx.guild.id]['loop'] else 'disabled'}**. Type: `{info}`"
        )

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def shuffle(self, ctx: Context):
        """Shuffles the queue"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        if queue := vc.queue:
            if queue.is_empty:
                await ctx.send(f"{ctx.author.mention} queue is empty.")
                return

            random.shuffle(queue._queue)  # type: ignore

            await ctx.send(f"{ctx.author.mention} queue has been shuffled.")
            return

    @commands.group(name="filter", invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    async def _filter(self, ctx: Context):
        """Set filter for the song"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        if ctx.invoked_subcommand is None:
            return await self.bot.invoke_help_command(ctx)

    @_filter.command(name="equalizer", invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_equalizer(
        self,
        ctx: Context,
        *,
        equalizer: Literal["boost", "flat", "metal", "piano"],
    ):
        """Set the Equalizer filter. Available options: `boost`, `flat`, `metal`, `piano`"""
        if ctx.invoked_subcommand is None:
            _equalizer: wavelink.Equalizer = getattr(wavelink.Equalizer, equalizer)()
            if ctx.voice_client is None:
                return await ctx.send(
                    f"{ctx.author.mention} bot is not connected to a voice channel."
                )

            channel: wavelink.Player = ctx.voice_client
            await channel.set_filter(wavelink.Filter(equalizer=_equalizer))
            await ctx.send(f"{ctx.author.mention} set the equalizer to **{equalizer}**")
            return

        await self.bot.invoke_help_command(ctx)

    @_filter.command(name="karaoke")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_karaoke(self, ctx: Context, *, flag: KaraokeFlag):
        """To configure Karaoke filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        PAYLOAD = {}
        if flag.level:
            PAYLOAD["level"] = flag.level
        if flag.mono_level:
            PAYLOAD["mono_level"] = flag.mono_level
        if flag.filter_band:
            PAYLOAD["filter_band"] = flag.filter_band
        if flag.filter_width:
            PAYLOAD["filter_width"] = flag.filter_width

        _filter = wavelink.Karaoke(**PAYLOAD)
        await channel.set_filter(wavelink.Filter(karaoke=_filter))
        await ctx.send(
            f"{ctx.author.mention} set the karaoke filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
        )

    @_filter.command(name="timescale")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_timescale(self, ctx: Context, *, timescale: TimescaleFlag):
        """To configure the timescale filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        PAYLOAD = {}
        if timescale.rate:
            PAYLOAD["rate"] = timescale.rate
        if timescale.pitch:
            PAYLOAD["pitch"] = timescale.pitch
        if timescale.speed:
            PAYLOAD["speed"] = timescale.speed

        _filter = wavelink.Timescale(**PAYLOAD)
        await channel.set_filter(_filter)
        await ctx.send(
            f"{ctx.author.mention} set the timescale filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
        )

    @_filter.command(name="tremolo")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_tremolo(self, ctx: Context, *, tremolo: TremoloFlag):
        """To configure the tremolo filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        PAYLOAD = {}
        if tremolo.depth:
            PAYLOAD["depth"] = tremolo.depth
        if tremolo.frequency:
            PAYLOAD["frequency"] = tremolo.frequency

        _filter = wavelink.Tremolo(**PAYLOAD)
        await channel.set_filter(wavelink.Filter(tremolo=_filter))
        await ctx.send(
            f"{ctx.author.mention} set the tremolo filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
        )

    @_filter.command(name="vibrato")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_vibrato(self, ctx: Context, *, flag: VibratoFlag):
        """To configure the vibrato filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        PAYLOAD = {}
        if flag.depth:
            PAYLOAD["depth"] = flag.depth
        if flag.frequency:
            PAYLOAD["frequency"] = flag.frequency

        _filter = wavelink.Vibrato(**PAYLOAD)
        await channel.set_filter(wavelink.Filter(vibrato=_filter))
        await ctx.send(
            f"{ctx.author.mention} set the vibrato filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
        )

    @_filter.command(name="rotation")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_rotation(self, ctx: Context, *, flag: RotationFlag):
        """To configure the rotation filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        PAYLOAD = {}
        if flag.speed:
            PAYLOAD["speed"] = flag.speed

        _filter = wavelink.Rotation(**PAYLOAD)
        await channel.set_filter(wavelink.Filter(rotation=_filter))
        await ctx.send(
            f"{ctx.author.mention} set the rotation filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
        )

    @_filter.command(name="distortion")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_distortion(self, ctx: Context, *, flag: DistortionFlag):
        """To configure the distortion filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        PAYLOAD = {}
        if flag.sin_offset:
            PAYLOAD["sin_offset"] = flag.sin_offset
        if flag.cos_offset:
            PAYLOAD["cos_offset"] = flag.cos_offset
        if flag.tan_offset:
            PAYLOAD["tan_offset"] = flag.tan_offset
        if flag.sin_scale:
            PAYLOAD["sin_scale"] = flag.sin_scale
        if flag.cos_scale:
            PAYLOAD["cos_scale"] = flag.cos_scale
        if flag.tan_scale:
            PAYLOAD["tan_scale"] = flag.tan_scale
        if flag.offset:
            PAYLOAD["offset"] = flag.offset
        if flag.scale:
            PAYLOAD["scale"] = flag.scale

        _filter = wavelink.Distortion(**PAYLOAD)
        await channel.set_filter(wavelink.Filter(distortion=_filter))
        await ctx.send(
            f"{ctx.author.mention} set the distortion filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
        )

    @_filter.group(name="channelmix", invoke_without_command=True)
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_channelmix(
        self,
        ctx: Context,
        *,
        flag: ChannelMixFlag,
    ):
        """To configure the channelmix filter"""
        if ctx.invoked_subcommand is None:
            if ctx.voice_client is None:
                return await ctx.send(
                    f"{ctx.author.mention} bot is not connected to a voice channel."
                )

            channel: wavelink.Player = ctx.voice_client

            if not channel.is_playing():
                return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

            PAYLOAD = {}
            if flag.left_to_left:
                PAYLOAD["left_to_left"] = flag.left_to_left
            if flag.left_to_right:
                PAYLOAD["left_to_right"] = flag.left_to_right
            if flag.right_to_left:
                PAYLOAD["right_to_left"] = flag.right_to_left
            if flag.right_to_right:
                PAYLOAD["right_to_right"] = flag.right_to_right

            _filter = wavelink.ChannelMix(**PAYLOAD)
            await channel.set_filter(wavelink.Filter(channel_mix=_filter))
            await ctx.send(
                f"{ctx.author.mention} set the channelmix filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
            )

    @_filter_channelmix.command(name="builtin", aliases=["built-in"])
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_channelmix_builtin(
        self,
        ctx: Context,
        *,
        mix: Literal["full_left", "full_right", "mono", "only_left", "only_right", "switch"],
    ):
        """To configure the channelmix filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        _filter = getattr(wavelink.ChannelMix, mix)()

        await channel.set_filter(_filter)
        await ctx.send(f"{ctx.author.mention} set the channelmix filter to **{mix}**")

    @_filter.command(name="lowpass")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _filter_lowpass(self, ctx: Context, *, flag: LowPassFlag):
        """To configure the lowpass filter"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        channel: wavelink.Player = ctx.voice_client

        if not channel.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        PAYLOAD = {}
        if flag.smoothing:
            PAYLOAD["smoothing"] = flag.smoothing

        _filter = wavelink.LowPass(**PAYLOAD)
        await channel.set_filter(wavelink.Filter(low_pass=_filter))
        await ctx.send(
            f"{ctx.author.mention} set the lowpass filter to **{' '.join(k + '=' + str(v) for k, v in PAYLOAD.items())}**"
        )

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    async def disconnect(self, ctx: Context):
        """Disconnects from the voice channel"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")
        await ctx.send(f"{ctx.author.mention} disconnected")

        vc: wavelink.Player = ctx.voice_client
        await vc.disconnect()

    @commands.group(invoke_without_command=True)
    @commands.bot_has_guild_permissions(connect=True)
    @in_voice()
    async def play(
        self,
        ctx: Context,
        *,
        search: Union[wavelink.SoundCloudTrack, str],
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

                vc.queue.put(search)
                await ctx.send(f"{ctx.author.mention} added **{search.title}** to the queue")
                return

            await vc.play(search)
            await ctx.send(
                f"{ctx.author.mention} Now playing",
                embed=await self.make_final_embed(ctx=ctx, track=vc.track),
                view=MusicView(ctx.author.voice.channel, timeout=vc.track.duration, ctx=ctx),
            )

    @play.command(name="spotify")
    async def play_spotify(self, ctx: Context, *, link: str):
        """Play a song from spotify with the given link"""
        if ctx.voice_client is None:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client  # type: ignore

        with suppress(spotify.SpotifyRequestError):
            tracks = await spotify.SpotifyTrack.search(link)
            q = vc.queue
            q.extend(tracks)

            if not vc.is_playing():
                np_track = q.get()
                await vc.play(np_track)

                await ctx.send(
                    f"{ctx.author.mention} Now playing",
                    embed=await self.make_final_embed(ctx=ctx, track=vc.track),
                    view=MusicView(
                        ctx.author.voice.channel,
                        timeout=abs(vc.last_position - vc.track.duration),
                        ctx=ctx,
                    ),
                )
                return
            await ctx.send(f"{ctx.author.mention} added **{len(tracks)}** to the queue")
            return
        await ctx.send(f"{ctx.author.mention} Invalid link")

    @play.command(
        name="myplaylist", aliases=["playlist", "myplaylists", "playlists", "mysongs", "mysong"]
    )
    async def play_myplaylist(
        self,
        ctx: Context,
    ):
        """Play a playlist from spotify with the given link"""
        if ctx.voice_client is None:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client  # type: ignore

        data = await self.bot.mongo.extra.user_misc.find_one(
            {"_id": ctx.author.id, "playlist": {"$exists": True}}, {"playlist": 1, "_id": 0}
        )
        if data is None or len(data["playlist"]) == 0:
            return await ctx.send(
                f"{ctx.author.mention} You don't have a playlist. You haven't like any songs yet."
            )

        countr = 0

        for i, song in enumerate(data["playlist"], start=1):
            if i == 1 and not vc.is_playing():
                await self.play(ctx, search=song["song_name"])
            else:
                track = wavelink.PartialTrack(query=song["song_name"])
                vc.queue.put(track)
                countr += 1

        await ctx.send(f"{ctx.author.mention} added **{countr} songs** to the queue")

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx: Context):
        """Shows the currently playing song"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")
        await ctx.send(
            f"{ctx.author.mention} Now playing",
            embed=await self.make_final_embed(ctx=ctx, track=vc.track),
            view=MusicView(
                ctx.author.voice.channel,
                timeout=abs(vc.last_position - vc.track.duration),
                ctx=ctx,
            ),
        )

    @commands.command(name="myplaylist")
    async def myplaylist(self, ctx: Context):
        """Shows the songs you loved."""
        data = await self.bot.mongo.extra.user_misc.find_one(
            {"_id": ctx.author.id, "playlist": {"$exists": True}}, {"playlist": 1, "_id": 0}
        )
        if data is None or len(data["playlist"]) == 0:
            return await ctx.send(
                f"{ctx.author.mention} You don't have a playlist. You haven't like any songs yet."
            )

        entries = []
        for song in data["playlist"]:
            entries.append(
                f"**[{song['song_name'] or 'Fetching song name Failed'}]({song['url']})**"
            )
        await ctx.paginate(entries, per_page=5)

    @commands.command(name="next", aliases=["skip"])
    @in_voice()
    async def _next(self, ctx: Context, *, flag: Optional[Literal["--force"]] = None):
        """Skips the currently playing song

        To force the skip use `$skip --force`. This will skip the song without voting.
        Force skip can only be used by member with DJ role.
        """
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")
        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        if vc.queue.is_empty:
            return await ctx.send(f"{ctx.author.mention} There are no more songs in the queue.")

        channel: discord.VoiceChannel = vc.channel
        members = sum(1 for m in channel.members if not m.bot)

        async def __interal_skip(*, ctx: Context, vc: wavelink.Player):
            with suppress(QueueEmpty):
                next_song = vc.queue.get()
                await vc.play(next_song)
                await ctx.send(
                    f"{ctx.author.mention} Now playing",
                    embed=await self.make_final_embed(ctx=ctx, track=vc.track),
                    view=MusicView(
                        ctx.author.voice.channel,
                        timeout=abs(vc.last_position - vc.track.duration),
                        ctx=ctx,
                    ),
                )
                return
            await ctx.send(f"{ctx.author.mention} There are no more songs in the queue.")

        dj_role = await ctx.dj_role()
        if str(flag).lower() == "--force":
            if dj_role is not None and dj_role in ctx.author.roles:
                await __interal_skip(ctx=ctx, vc=vc)
                return
            else:
                await ctx.send(
                    f"{ctx.author.mention} You don't have the DJ role. You can't force skip."
                )
                return

        if members <= 2:
            return await __interal_skip(ctx=ctx, vc=vc)

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
                return await __interal_skip(
                    ctx=ctx,
                    vc=vc,
                )

        await __interal_skip(ctx=ctx, vc=vc)

    @commands.group(name="queue", invoke_without_command=True)
    async def _queue(self, ctx: Context):
        """Shows the current songs queue"""
        if ctx.invoked_subcommand is None:
            if ctx.voice_client is None:
                return await ctx.send(
                    f"{ctx.author.mention} bot is not connected to a voice channel."
                )
            vc: wavelink.Player = ctx.voice_client
            if vc.queue.is_empty:
                return await ctx.send(f"{ctx.author.mention} There are no songs in the queue.")

            entries = []
            for track in vc.queue._queue:  # type: ignore
                if hasattr(track, "uri"):
                    entries.append(f"[{track.title} - {track.author}]({track.uri})")
                else:
                    entries.append(f"{track.title} - {getattr(track, 'author', 'Unknown')}")

            await ctx.paginate(entries=entries, _type="SimplePages")

    @_queue.command(name="clear")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _queue_clear(self, ctx: Context):
        """Clears the current songs queue"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")
        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        if vc.queue.is_empty:
            return await ctx.send(f"{ctx.author.mention} There are no songs in the queue.")
        vc.queue.clear()
        await ctx.send(f"{ctx.author.mention} Cleared the queue.")

    @_queue.command(name="remove")
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def _queue_remove(self, ctx: Context, *, index: int):
        """Removes a song from the current songs queue"""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")
        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        if vc.queue.is_empty:
            return await ctx.send(f"{ctx.author.mention} There are no songs in the queue.")
        q: Deque[wavelink.Track] = vc.queue._queue  # type: ignore
        for i, track in enumerate(q, start=1):
            if i == index:
                q.remove(track)
                await ctx.send(f"{ctx.author.mention} Removed **{track.title}** from the queue.")
                return

        await ctx.send(f"{ctx.author.mention} no track at index {index}")

    @commands.command()
    @commands.check_any(commands.has_permissions(manage_channels=True), is_dj())
    @in_voice()
    async def stop(self, ctx: Context):
        """Stop the currently playing song."""
        if ctx.voice_client is None:
            return await ctx.send(f"{ctx.author.mention} bot is not connected to a voice channel.")

        vc: wavelink.Player = ctx.voice_client  # type: ignore
        if not vc.is_playing():
            return await ctx.send(f"{ctx.author.mention} bot is not playing anything.")

        await vc.stop()
        await ctx.send(f"{ctx.author.mention} stopped the music.")

        if not vc.queue.is_empty:
            track = vc.queue.get()
            await vc.play(track)
            await ctx.send(
                f"{ctx.author.mention} Now playing",
                embed=await self.make_final_embed(ctx=ctx, track=vc.track),
                view=MusicView(
                    ctx=ctx,
                    vc=vc,
                ),
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
        self, player: wavelink.Player, track: wavelink.Track, reason: str
    ):
        if reason == "STOPPED":
            return

        if reason == "FINISHED":
            try:
                self._config[player.guild.id]
            except KeyError:
                self._config[player.guild.id] = {}

            if self._config[player.guild.id].get("loop", False):
                q: Deque[wavelink.Track] = player.queue._queue  # type: ignore
                q.rotate(-1)

                if self._config[player.guild.id].get("loop_type") == "all" and len(q) != 0:
                    await player.play(q[0])
                elif self._config[player.guild.id].get("loop_type") == "current":
                    await player.play(track)
            else:
                try:
                    track = player.queue.get()
                    await player.play(track)
                except QueueEmpty:
                    pass
