import json
import random
import discord

from discord.ext import commands

from pathlib import Path
from datetime import datetime
from rapidfuzz import fuzz
import dateutil.parser
from typing import Optional, Union

from utilities.deco import seasonal_task
from utilities.constants import Month, Colours

from core import Cog, Context, Parrot

NAMES = json.loads(Path(r"extra/pride/drag_queen_names.json").read_text("utf8"))
VIDEOS = json.loads(Path(r"extra/pride/anthems.json").read_text("utf8"))
FACTS = json.loads(Path(r"extra/pride/facts.json").read_text("utf8"))

PRIDE_RESOURCE = json.loads(Path(r"extra/pride/prideleader.json").read_text("utf8"))
MINIMUM_FUZZ_RATIO = 40


class Pride(Cog):
    """PRIDE PRIDE PRIDE!"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.daily_fact_task = self.bot.loop.create_task(self.send_pride_fact_daily())

    @seasonal_task(Month.JUNE)
    async def send_pride_fact_daily(self) -> None:
        """Background task to post the daily pride fact every day."""
        await self.bot.wait_until_guild_available()

        channel = self.bot.get_channel(Channels.community_bot_commands)
        await self.send_select_fact(channel, datetime.utcnow())

    async def send_random_fact(self, ctx: Context) -> None:
        """Provides a fact from any previous day, or today."""
        now = datetime.utcnow()
        previous_years_facts = (y for x, y in FACTS.items() if int(x) < now.year)
        current_year_facts = FACTS.get(str(now.year), [])[: now.day]
        previous_facts = current_year_facts + [
            x for y in previous_years_facts for x in y
        ]
        try:
            await ctx.send(embed=self.make_embed(random.choice(previous_facts)))
        except IndexError:
            await ctx.send("No facts available")

    async def send_select_fact(
        self, target: discord.abc.Messageable, _date: Union[str, datetime]
    ) -> None:
        """Provides the fact for the specified day, if the day is today, or is in the past."""
        now = datetime.utcnow()
        if isinstance(_date, str):
            try:
                date = dateutil.parser.parse(
                    _date, dayfirst=False, yearfirst=False, fuzzy=True
                )
            except (ValueError, OverflowError) as err:
                await target.send(f"Error parsing date: {err}")
                return
        else:
            date = _date
        if date.year < now.year or (date.year == now.year and date.day <= now.day):
            try:
                await target.send(
                    embed=self.make_embed(FACTS[str(date.year)][date.day - 1])
                )
            except KeyError:
                await target.send(f"The year {date.year} is not yet supported")
                return
            except IndexError:
                await target.send(f"Day {date.day} of {date.year} is not yet support")
                return
        else:
            await target.send("The fact for the selected day is not yet available.")

    @commands.command(name="pridefact", aliases=("pridefacts",))
    async def pridefact(self, ctx: Context, option: str = None) -> None:
        """
        Sends a message with a pride fact of the day.
        If "random" is given as an argument, a random previous fact will be provided.
        If a date is given as an argument, and the date is in the past, the fact from that day
        will be provided.
        """
        if not option:
            await self.send_select_fact(ctx, datetime.utcnow())
        elif option.lower().startswith("rand"):
            await self.send_random_fact(ctx)
        else:
            await self.send_select_fact(ctx, option)

    @staticmethod
    def make_embed(fact: str) -> discord.Embed:
        """Makes a nice embed for the fact to be sent."""
        return discord.Embed(colour=Colours.pink, title="Pride Fact!", description=fact)

    @commands.command(name="dragname", aliases=("dragqueenname", "queenme"))
    async def dragname(self, ctx: Context) -> None:
        """Sends a message with a drag queen name."""
        await ctx.send(random.choice(NAMES))

    def get_video(self, genre: Optional[str] = None) -> dict:
        """
        Picks a random anthem from the list.
        If `genre` is supplied, it will pick from videos attributed with that genre.
        If none can be found, it will log this as well as provide that information to the user.
        """
        if not genre:
            return random.choice(VIDEOS)
        songs = [song for song in VIDEOS if genre.casefold() in song["genre"]]
        try:
            return random.choice(songs)
        except IndexError:
            pass

    @commands.command(name="prideanthem", aliases=("anthem", "pridesong"))
    async def prideanthem(self, ctx: Context, genre: str = None) -> None:
        """
        Sends a message with a video of a random pride anthem.
        If `genre` is supplied, it will select from that genre only.
        """
        anthem = self.get_video(genre)
        if anthem:
            await ctx.send(anthem["url"])
        else:
            await ctx.send("I couldn't find a video, sorry!")

    def invalid_embed_generate(self, pride_leader: str) -> discord.Embed:
        """
        Generates Invalid Embed.
        The invalid embed contains a list of closely matched names of the invalid pride
        leader the user gave. If no closely matched names are found it would list all
        the available pride leader names.
        Wikipedia is a useful place to learn about pride leaders and we don't have all
        the pride leaders, so the bot would add a field containing the wikipedia
        command to execute.
        """
        embed = discord.Embed(color=Colours.soft_red)
        valid_names = []
        pride_leader = pride_leader.title()
        for name in PRIDE_RESOURCE:
            if fuzz.ratio(pride_leader, name) >= MINIMUM_FUZZ_RATIO:
                valid_names.append(name)

        if not valid_names:
            valid_names = ", ".join(PRIDE_RESOURCE)
            error_msg = "Sorry your input didn't match any stored names, here is a list of available names:"
        else:
            valid_names = "\n".join(valid_names)
            error_msg = "Did you mean?"

        embed.description = f"{error_msg}\n```\n{valid_names}\n```"
        embed.set_footer(
            text="To add more pride leaders, feel free to open a pull request!"
        )

        return embed

    def embed_builder(self, pride_leader: dict) -> discord.Embed:
        """Generate an Embed with information about a pride leader."""
        name = [name for name, info in PRIDE_RESOURCE.items() if info == pride_leader][
            0
        ]

        embed = discord.Embed(
            title=name, description=pride_leader["About"], color=Colours.blue
        )
        embed.add_field(name="Known for", value=pride_leader["Known for"], inline=False)
        embed.add_field(
            name="D.O.B and Birth place", value=pride_leader["Born"], inline=False
        )
        embed.add_field(
            name="Awards and honors", value=pride_leader["Awards"], inline=False
        )
        embed.add_field(
            name="For More Information", value=f"Do `$wiki {name}`", inline=False
        )
        embed.set_thumbnail(url=pride_leader["url"])
        return embed

    @commands.command(aliases=("pl", "prideleader"))
    async def pride_leader(
        self, ctx: Context, *, pride_leader_name: Optional[str]
    ) -> None:
        """
        Information about a Pride Leader.
        Returns information about the specified pride leader
        and if there is no pride leader given, return a random pride leader.
        """
        if not pride_leader_name:
            leader = random.choice(list(PRIDE_RESOURCE.values()))
        else:
            leader = PRIDE_RESOURCE.get(pride_leader_name.title())
            if not leader:
                embed = self.invalid_embed_generate(pride_leader_name)
                await ctx.send(embed=embed)
                return

        embed = self.embed_builder(leader)
        await ctx.send(embed=embed)
