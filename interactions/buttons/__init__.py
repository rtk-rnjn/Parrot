import discord, asyncio
from discord.ext import commands
from core import Parrot, Cog, Context
from datetime import datetime

from .tic_tac_toe import TicTacToe 
from .battleship import Battleship
from .rps import RPS
from .mine_sweeper import Minesweeper

import akinator
from akinator.async_aki import Akinator

class game(Cog):
    """All commands in this category are in testing for now"""

    def __init__(self, bot: Parrot):
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='\N{VIDEO GAME}')
    
    @commands.command()
    async def ttt(self, ctx: Context, *, member: discord.Member):
        """Basic Tic-Tac-Toe game"""
        await ctx.send('Tic Tac Toe: X goes first', view=TicTacToe(member.id))
    
    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def aki(self, ctx: Context):
        """Answer the questions and let the bot guess your character!"""
        aki = Akinator()
        q = await aki.start_game()
        question_num = 1
        while aki.progression <= 80:
            question = q + "\n\t"
            embed = discord.Embed(color=0xFF0000)
            embed.add_field(
                name=f"Q-{question_num}\n{question}",
                value="Reply with `yes/y` | `no/n` | `i/idk/i don't know` | `p/probably` | `proably not/pn`",
            )
            await ctx.send(embed=embed)

            def check(m):
                replies = ("yes", "y", "no", "n", "i", "idk", "i don't know", "probably", "p", "probably not", "pn")
                return (m.content.lower() in replies and m.channel == ctx.channel and m.author == ctx.author)
            try:
              msg = await self.bot.wait_for("message", check=check, timeout=30)
            except Exception:
              return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
            if msg.content.lower() in ("b", "back"):
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
        embed.set_image(url=f"{aki.first_guess['absolute_picture_path']}")
        embed.add_field(name="Reply with `yes/y` `no/n`", value="\u200b")
        await ctx.send(embed=embed)

        def check(m):
            return (m.content.lower() in ("yes", "y", "no", "n") and m.channel == ctx.channel and m.author == ctx.author)

        try: 
            correct = await self.bot.wait_for("message", check=check, timeout=30)
        except Exception: 
            return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
        if correct.content.lower() == "yes" or correct.content.lower() == "y":
            embed = discord.Embed(title="Yay! I guessed it right", color=0xFF0000)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Oof! Kinda hard one", color=0xFF0000)
            await ctx.send(embed=embed)
    

def setup(bot: Parrot):
    bot.add_cog(game(bot))
    bot.add_cog(TicTacToe(bot))
    bot.add_cog(Battleship(bot))
    bot.add_cog(RPS(bot))
    bot.add_cog(Minesweeper(bot))