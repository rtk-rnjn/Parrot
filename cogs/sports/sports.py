from __future__ import annotations

from core import Parrot, Cog, Context
from tabulate import tabulate

from discord.ext import commands
import discord
from utilities.deco import with_role

STAFF_ROLES = [771025632184369152, 793531029184708639]


class Sports(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        # ipl url - the url to the ipl score page.
        # to my localhost to be honest.
        self.url = None

    @commands.group(name="ipl")
    async def ipl(self, ctx: Context) -> None:
        """To get the IPL score"""
        if not self.url:
            return await ctx.send("No IPL score page set.")

        url = f"http://127.0.0.1:1729/cricket_api?url={self.url}"
        response = await self.bot.http_session.get(url)

        if response.status != 200:
            return await ctx.send("Could not get IPL score.")

        data = await response.json()

        embed = discord.Embed(
            title=data["title"], timestamp=ctx.message.created_at
        )
        embed.set_footer(text=data["status"])

        table1 = tabulate(data['batting'], headers="keys")
        table2 = tabulate(data['bowling'], headers="keys")
        crr = "\n".join(data["crr"])

        extra = ""
        if extra_ := data.get('extra'):
            for temp in extra_:
                extra += "".join(temp) + "\n"
        embed.description = f"""
> `{data['team_one']} | {data['team_two']}`
{'`'*3}
{crr}
{'`'*3}
{extra}
"""
        if data.get('batting'):
            embed.add_field(
                name="Batting - Stats", value=f"```\n{table1}```", inline=False
            )

        if data.get('bowling'):
            embed.add_field(
                name="Bowling - Stats", value=f"```\n{table2}```", inline=False
            )

        embed.add_field(
            name="Recent Commentry", value="- " + "\n - ".join(i for i in data["commentry"][:2] if i), inline=False
        )
        await ctx.send(embed=embed)


    @with_role(*STAFF_ROLES)
    @ipl.command(name="set")
    async def set_ipl_url(self, ctx: Context, *, url: str) -> None:
        """Set the IPL score page url"""
        self.url = url
        await ctx.send(f"Set IPL score page to {url}")
