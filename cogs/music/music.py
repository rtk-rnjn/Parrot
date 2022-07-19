from __future__ import annotations

import wavelink
from discord.ext import commands
from core import Context, Parrot, Cog


class Music(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.command()
    async def play(self, ctx: Context, *, search: wavelink.YouTubeTrack):
        """Play a song with the given search query.
        If not connected, connect to our voice channel.
        """
        if ctx.voice_client is None:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client  # type: ignore

        await vc.play(search)
