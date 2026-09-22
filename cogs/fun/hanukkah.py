from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import arrow
import discord
from discord import Embed
from discord.ext import commands

from core import in_month
from core.constants import Month

if TYPE_CHECKING:
    from discord.ext.commands import Context

    from core import Parrot

_log = logging.getLogger("bot.cogs.fun.hanukkah")

HEBCAL_URL = (
    "https://www.hebcal.com/hebcal/?v=1&cfg=json&maj=on&min=on&mod=on&nx=on&year=now&month=x&ss=on&mf=on&c=on&geo=geoname&geonameid=3448439&m=50&s=on"
)


class Hanukkah(commands.Cog, command_attrs={"hidden": True}):
    """A cog that returns information about Hanukkah festival."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.hanukkah_dates: list[arrow.Arrow] = []

        _log.info("Cog loaded: %s", self.__class__.__name__)

    def _parse_time_to_arrow(self, date: str) -> arrow.Arrow:
        """Format the times provided by the API to Arrow objects."""
        return arrow.get(date)

    async def fetch_hanukkah_dates(self) -> list[arrow.Arrow]:
        """Gets the dates for Hanukkah festival."""
        self.hanukkah_dates = []

        async with self.bot.http_session.get(HEBCAL_URL) as response:
            json_data = await response.json()

        festivals = json_data["items"]

        for festival in festivals:
            if festival["title"].startswith("Chanukah"):
                date = festival["date"]
                self.hanukkah_dates.append(self._parse_time_to_arrow(date))

        return self.hanukkah_dates

    @in_month(Month.NOVEMBER, Month.DECEMBER)
    @commands.command(name="hanukkah", aliases=("chanukah",))
    async def hanukkah_festival(self, ctx: Context) -> None:
        """Tells you about the Hanukkah festival."""

        hanukkah_dates = await self.fetch_hanukkah_dates()
        start_day = hanukkah_dates[0]
        end_day = hanukkah_dates[-1]
        today = arrow.now().floor("day")

        embed = Embed(title="Hanukkah", colour=discord.Color.blue())

        if start_day <= today <= end_day:
            if start_day == today:
                now = arrow.utcnow()
                hours = now.hour + 4
                hanukkah_start_hour = 18

                if hours < hanukkah_start_hour:
                    embed.description = f"Hanukkah hasnt started yet, it will start in about {hanukkah_start_hour - hours} hour/s."
                    await ctx.reply(embed=embed)
                    return

                if hours > hanukkah_start_hour:
                    embed.description = f"It is the starting day of Hanukkah! Its been {hours - hanukkah_start_hour} hours hanukkah started!"
                    await ctx.reply(embed=embed)
                    return

            festival_day = hanukkah_dates.index(today)
            number_suffixes = ["st", "nd", "rd", "th"]
            suffix = number_suffixes[festival_day - 1 if festival_day <= 3 else 3]
            message = ":menorah:" * festival_day

            embed.description = f"It is the {festival_day}{suffix} day of Hanukkah!\n{message}"

        elif today < start_day:
            format_start = start_day.format("DD [of] MMMM")
            embed.description = f"Hanukkah has not started yet. Hanukkah will start at sundown on {format_start}."

        else:
            format_end = end_day.format("DD [of] MMMM")
            embed.description = f"Looks like you missed Hanukkah! Hanukkah ended on {format_end}."

        await ctx.reply(embed=embed)


async def setup(bot: Parrot) -> None:
    """Load the cog."""
    await bot.add_cog(Hanukkah(bot))
