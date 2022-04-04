from __future__ import annotations
import email
from typing import Any, Dict

from core import Parrot, Cog, Context
from tabulate import tabulate
from datetime import datetime
from discord.ext import commands, tasks
import discord
from utilities.deco import with_role

STAFF_ROLES = [771025632184369152, 793531029184708639]


class Sports(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

        # ipl url - the url to the ipl score page.
        # to my localhost to be honest.
        self.url = None

    def create_embed_ipl(self, *, data: Dict[str, Any],) -> discord.Embed:
        embed = discord.Embed(
            title=data["title"], timestamp=datetime.utcnow()
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
```
{crr}
```
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
        return embed

    @commands.group(name="ipl", invoke_without_command=True)
    async def ipl(self, ctx: Context) -> None:
        """To get the IPL score"""
        if ctx.invoked_subcommand is None:
            if not self.url:
                return await ctx.send(f"{ctx.author.mention} No IPL score page set | Ask for it in support server")

            url = f"http://127.0.0.1:1729/cricket_api?url={self.url}"
            response = await self.bot.http_session.get(url)

            if response.status != 200:
                return await ctx.send(f"{ctx.author.mention} Could not get IPL score | Ask for it in support server")

            data = await response.json()
            embed = self.create_embed_ipl(data=data)
            await ctx.send(embed=embed)

    @with_role(*STAFF_ROLES)
    @ipl.command(name="set")
    async def set_ipl_url(self, ctx: Context, *, url: str) -> None:
        """Set the IPL score page url"""
        if url.startswith(('<', '[')) and url.endswith(('>', ']')):
            url = url[1:-1]

        self.url = url
        await ctx.send(f"Set IPL score page to <{url}>")

    @tasks.loop(seconds=60)
    async def annouce_task(self,):
        if self.url is None:
            return

        url = f"http://127.0.0.1:1729/cricket_api?url={self.url}"
        response = await self.bot.http_session.get(url)

        if response.status != 200:
            return

        data = await response.json()
        embed = self.create_embed_ipl(data=data)

        pass
