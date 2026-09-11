from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
import pomice
from discord.ext import commands
from discord.ext.commands import Context

from .player import Player

if TYPE_CHECKING:
    from core import Parrot


_log = logging.getLogger("bot.cogs.music")


class Music(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    async def cog_check(self, ctx: commands.Context[Parrot]) -> bool:
        if self.bot.lavalink_node_pool.node_count == 0:
            raise commands.CommandError("No Lavalink nodes are connected. This feature is not available at the moment.")

        return True

    async def connect_channel(self, ctx: Context[Parrot]) -> Player:
        assert isinstance(ctx.author, discord.Member)

        if ctx.author.voice is None or ctx.author.voice.channel is None:
            raise commands.CommandError("You are not connected to a voice channel.")

        voice_client = await ctx.author.voice.channel.connect(cls=Player)
        if hasattr(voice_client, "ctx"):
            voice_client.ctx = ctx

        return voice_client

    @commands.command(name="join", aliases=["connect"])
    async def join(self, ctx: Context[Parrot]) -> None:
        """Connects the bot to your current voice channel.

        On success, the bot will react to the message with: \N{WHITE HEAVY CHECK MARK}
        Otherwise, it will react with: \N{WARNING SIGN}
        """

        if isinstance(ctx.voice_client, Player) and ctx.voice_client.is_connected:
            await ctx.message.add_reaction("\N{INFORMATION SOURCE}")
            await ctx.reply("I am already connected to a voice channel.")
            return

        if ctx.voice_client is None:
            await self.connect_channel(ctx)
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            await ctx.reply(f"Joined **{ctx.author.voice.channel}**.")  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
            return

        await ctx.message.add_reaction("\N{WARNING SIGN}")
        await ctx.reply("I could not connect to your voice channel.")

    @commands.command(name="forcejoin", aliases=["fj"])
    @commands.has_permissions(manage_channels=True)
    async def force_join(self, ctx: Context[Parrot]) -> None:
        """Forces the bot to join your current voice channel, disconnecting from any existing one."""

        assert isinstance(ctx.author, discord.Member)

        if ctx.voice_client is None or (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.invoke(self.join)
            return

        if ctx.author.voice and (ctx.voice_client.channel == ctx.author.voice.channel):
            await ctx.message.add_reaction("\N{INFORMATION SOURCE}")
            await ctx.reply("I am already in your voice channel.")
            return

        if ctx.voice_client and (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.voice_client.teardown()

        if ctx.author.voice is None:
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("You are not connected to a voice channel.")
            return

        voice_channel = ctx.author.voice.channel
        if not isinstance(voice_channel, discord.VoiceChannel):
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("I can only join a voice channel.")
            return

        if isinstance(ctx.voice_client, Player):
            await ctx.voice_client.move_to(voice_channel)
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            await ctx.reply(f"Moved to **{voice_channel}**.")

    @commands.command(name="leave", aliases=["disconnect", "dc"])
    async def leave(self, ctx: Context[Parrot]) -> None:
        """Disconnects the bot from the voice channel."""

        if not ctx.voice_client or (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("I am not connected to any voice channel.")
            return

        assert isinstance(ctx.voice_client, Player)

        if ctx.author == ctx.voice_client.dj:
            await ctx.voice_client.teardown()
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            await ctx.reply("Disconnected from the voice channel.")
        else:
            await ctx.message.add_reaction("\N{CROSS MARK}")
            await ctx.reply("Only the DJ can disconnect me.")

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx: Context[Parrot], *, query: str = commands.parameter(description="The URL or search term to play.")) -> None:
        """Play a song from a URL or search term."""

        if not ctx.voice_client or (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("Join a voice channel first with `join`.")
            return

        node = self.bot.lavalink_node_pool.get_best_node(algorithm=pomice.NodeAlgorithm.by_players)
        result = None

        for search_type in [pomice.SearchType.other, pomice.SearchType.scsearch, pomice.SearchType.ytsearch]:
            result = await node.get_tracks(query, search_type=search_type, ctx=ctx)
            if result is not None:
                break

        if result is None or not result or (isinstance(result, pomice.Playlist) and not result.tracks):
            await ctx.message.add_reaction("\N{OPEN MAILBOX WITH LOWERED FLAG}")
            await ctx.reply("Bot could not find anything to play for that query.")
            return

        assert isinstance(ctx.voice_client, Player)

        if isinstance(result, pomice.Playlist):
            for track in result.tracks:
                await ctx.voice_client.queue_track(track, ctx=ctx)
            feedback = f"Queued **{len(result.tracks)}** tracks from the playlist."
        else:
            await ctx.voice_client.queue_track(result[0], ctx=ctx)
            feedback = f"Queued **[{result[0].title} - {result[0].author}](<{result[0].uri}>)**."

        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await ctx.reply(feedback)

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx: Context[Parrot]) -> None:
        """Skips the current track."""

        if not ctx.voice_client or (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("I am not connected to a voice channel.")
            return

        assert isinstance(ctx.voice_client, Player)

        if not ctx.voice_client.current:
            await ctx.message.add_reaction("\N{CROSS MARK}")
            await ctx.reply("There is no track currently playing.")
            return

        await ctx.voice_client.play_next()
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await ctx.reply("Skipped the current track.")

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx: Context[Parrot]) -> None:
        """Displays the current queue."""

        if not ctx.voice_client or (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("I am not connected to a voice channel.")
            return

        assert isinstance(ctx.voice_client, Player)

        if not ctx.voice_client.queue:
            await ctx.message.add_reaction("\N{OPEN MAILBOX WITH LOWERED FLAG}")
            await ctx.reply("The queue is currently empty.")
            return

        pages = []
        for index, track in enumerate(ctx.voice_client.queue, start=1):
            pages.append(f"{index}. [{track.title}](<{track.uri}>) by {track.author}")

        await self.bot.paginate(ctx, embed=True, pages=pages)

    @commands.command(name="nowplaying", aliases=["np"])
    async def now_playing(self, ctx: Context[Parrot]) -> None:
        """Shows the currently playing track."""

        if not ctx.voice_client or (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("I am not connected to a voice channel.")
            return

        player = ctx.voice_client
        if not player.current:  # pyright: ignore[reportAttributeAccessIssue]
            await ctx.message.add_reaction("\N{OPEN MAILBOX WITH LOWERED FLAG}")
            await ctx.reply("Nothing is currently playing.")
            return

        track = player.current  # pyright: ignore[reportAttributeAccessIssue]
        title = track.title
        url = track.uri
        author = track.author
        duration = track.length
        current_length = player.position  # pyright: ignore[reportAttributeAccessIssue]

        await ctx.reply(
            f"**Now Playing:** [{title}](<{url}>) by {author}\n{self.__create_duration_string(total_duration=duration, current_duration=current_length)}",
            suppress_embeds=True,
        )

    def __create_duration_string(self, *, total_duration: float, current_duration: float) -> str:
        dash = "\N{HORIZONTAL BAR}"
        slider = "\N{RADIO BUTTON}"

        total_bars = 12
        filled_bars = int((current_duration / total_duration) * total_bars)
        empty_bars = total_bars - filled_bars
        bar_string = dash * filled_bars + slider + dash * (empty_bars - 1)
        return f"{bar_string} {current_duration // 60000}:{(current_duration % 60000) // 1000:02} / {total_duration // 60000}:{(total_duration % 60000) // 1000:02}"

    @commands.command(name="stop")
    async def stop(self, ctx: Context[Parrot]) -> None:
        """Stops playback and clears the queue."""

        if not ctx.voice_client or (isinstance(ctx.voice_client, Player) and not ctx.voice_client.is_connected):
            await ctx.message.add_reaction("\N{WARNING SIGN}")
            await ctx.reply("I am not connected to a voice channel.")
            return

        assert isinstance(ctx.voice_client, Player)

        if ctx.author == ctx.voice_client.dj:
            await ctx.voice_client.teardown()
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            await ctx.reply("Playback stopped and the queue was cleared.")
        else:
            await ctx.voice_client.vote_stop(ctx.author)  # pyright: ignore[reportArgumentType]
            await ctx.message.add_reaction("\N{HOURGLASS WITH FLOWING SAND}")
            await ctx.reply("Your vote to stop playback has been counted.")

    @commands.Cog.listener()
    async def on_pomice_track_start(self, player: Player, track: pomice.Track) -> None:
        player._reset_votes()

    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: Player, track: pomice.Track, reason: str) -> None:
        _log.info("Track ended: %s (Reason: %s)", track.title, reason)
        await player.play_next()

    @commands.Cog.listener()
    async def on_pomice_track_exception(self, player: Player, track: pomice.Track, exception: Exception) -> None:
        _log.error("Track exception: %s (Track: %s)", exception, track.title)
        await player.play_next()

    @commands.Cog.listener()
    async def on_pomice_track_stuck(self, player: Player, track: pomice.Track, threshold_ms: int) -> None:
        _log.warning("Track stuck: %s (Threshold: %d ms)", track.title, threshold_ms)
        await player.play_next()

    async def _make_request(self) -> list[dict]:
        uri = "https://lavalink-list.ajieblogs.eu.org/NonSSL"
        async with self.bot.http_session.get(uri) as response:
            return await response.json()

    async def fetch_lavasrc_providers(self) -> list[tuple[str, str, str, str]]:
        data: list[dict[str, str]] = await self._make_request()
        providers = []

        for provider in data:
            if provider.get("version") != "v4":
                continue

            identifier = provider["identifier"]
            host = provider["host"]
            port = provider["port"]
            password = provider["password"]
            if host and port and password and identifier:
                providers.append((host, port, password, identifier))

        return providers

    @commands.command(name="loadlavasrc")
    @commands.is_owner()
    async def load_lavasrc(self, ctx: Context[Parrot]) -> None:
        """Loads Lavalink nodes from the lavasrc list."""

        errors = []
        providers = await self.fetch_lavasrc_providers()

        await ctx.message.add_reaction("\N{HOURGLASS WITH FLOWING SAND}")
        await ctx.reply(f"Loading **{len(providers)}** Lavalink nodes...")
        for host, port, password, identifier in providers:
            try:
                await self.bot.lavalink_node_pool.create_node(bot=self.bot, host=host, port=int(port), password=password, identifier=identifier)
            except Exception as e:
                errors.append((identifier, str(e)))
                continue
        if errors:
            description = "\n".join(f"**{identifier}**: {error}" for identifier, error in errors)
            embed = discord.Embed(title="Lavalink Node Load Errors", description=description, color=discord.Color.red())
            await ctx.reply(embed=embed)

        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await ctx.reply(f"Finished loading Lavalink nodes. **{len(providers) - len(errors)}** connected successfully.")

    @commands.command(name="listnodes")
    @commands.is_owner()
    async def list_nodes(self, ctx: Context[Parrot]) -> None:
        """Lists all connected Lavalink nodes."""

        nodes = self.bot.lavalink_node_pool.nodes
        if not nodes:
            await ctx.reply("No Lavalink nodes are connected.", delete_after=5)
            return

        description = ""
        for _, node in nodes.items():
            description += f"**Host:** {node._host}:{node._port}\n**Players:** {len(node.players)}\n\n"

        embed = discord.Embed(title="Connected Lavalink Nodes", description=description, color=discord.Color.blurple())
        await ctx.reply(embed=embed)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Music(bot))
