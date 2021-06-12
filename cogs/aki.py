import asyncio

import akinator
from akinator.async_aki import Akinator
from discord.ext.commands import BucketType, cooldown

aki = Akinator()

import datetime

import discord
import requests
from discord.ext import commands


class GuessName(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @cooldown(1, 60, BucketType.user)
    async def guess(self, ctx):
        q = await aki.start_game()
        question_num = 1
        while aki.progression <= 80:
            question = q + "\n\t"
            embed = discord.Embed(color=0xFF0000)
            embed.add_field(
                name=f"Q-{question_num}\n{question}",
                value=
                "Reply with `yes/y` `no/n` `i/idk/i don't know` `p/probably` `proably not/pn`",
            )
            await ctx.send(embed=embed)

            def check(m):
                replies = ["yes", "y", "no", "n", "i", "idk", "i don't know", "probably", "p", "probably not", "pn"]
                return (m.content in replies and m.channel == ctx.channel
                        and m.author == ctx.author)

            msg = await self.client.wait_for("message", check=check)
            if msg.content == "b":
                try:
                    q = await aki.back()
                except akinator.CantGoBackAnyFurther:
                    pass
            else:
                q = await aki.answer(msg.content)
            question_num += 1
        await aki.win()

        embed = discord.Embed(
            title=
            f"It's {aki.first_guess['name']} ({aki.first_guess['description']})! Was I correct?\n\t",
            color=0xFF0000,
        )
        embed.add_field(name="Reply with `yes/y` `no/n`", value="\u200b")
        await ctx.send(embed=embed)

        def check(m):
            return (m.content == "yes" and m.channel == ctx.channel
                    and m.author == ctx.author)

        correct = await self.client.wait_for("message", check=check)
        if correct.content.lower() == "yes" or correct.content.lower() == "y":
            embed = discord.Embed(title="Yay! I guessed it right",
                                  color=0xFF0000)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Yay! I guessed it right",
                                  color=0xFF0000)
            await ctx.send(embed=embed)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(GuessName.guess())
        loop.close()


def setup(client):
    client.add_cog(GuessName(client))