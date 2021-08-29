import discord, asyncio
from discord.ext import commands
from core import Parrot, Cog, Context
from datetime import datetime

from .tic_tac_toe import TicTacToe 
from .mine_sweeper import boardClass

import akinator
from akinator.async_aki import Akinator

class game(Cog):
    """All commands in this category are in testing for now"""

    def __init__(self, bot: Parrot):
        self.bot = bot
  
    @commands.command()
    async def ttt(self, ctx: Context, *, member: discord.Member):
        """Basic Tic-Tac-Toe game"""
        await ctx.send('Tic Tac Toe: X goes first', view=TicTacToe())

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def minesweeper(self, ctx: Context, boardSize: int=None, numMines: int=None):
        """Basic MineSweeper Game"""
        boardSize = boardSize or 6
        numMines = numMines or 6
        gameOver = False
        winner = False
        Board = boardClass(boardSize, numMines)
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
 
        while not gameOver:
            msg = await ctx.send(embed=discord.Embed(title="MineSweeper 1.0", description=f"```\n{Board}\n```", timestamp=datetime.utcnow(), color=ctx.author.color).set_footer(text=f"{ctx.author.name}"))
            await msg.reply(f"{ctx.author.mention} Make the move, first come X then Y. Example: `1, 2` or `1 2` | Type `cancel` to quit")
            while True:
                try:
                    loc = await self.bot.wait_for('message', timeout=60, check=check)
                except Exception:
                    return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
                if loc.content.lower() == "cancel":
                    return await ctx.send(f"{ctx.author.mention} game canceled")
                elif len(loc.content.replace(',', '').split(" ")) == 2:
                    lc = loc.content.replace(',', '').split(" ")
                    Board.makeMove(int(lc[0]), int(lc[1]))
                    gameOver = Board.hitMine(int(lc[0]), int(lc[1]))
                if Board.isWinner() and gameOver == False:
                    gameOver = True
                    winner = True
                break
        if winner:
            return await ctx.send(f"{ctx.author.mention} :tada: you win the game")
        else:
            return await ctx.send(f"{ctx.author.mention} you hit the mine")
        return await ctx.send(f"{ctx.author.mention} game ended")
    
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
                value=
                "Reply with `yes/y` | `no/n` | `i/idk/i don't know` | `p/probably` | `proably not/pn`",
            )
            await ctx.send(embed=embed)

            def check(m):
                replies = [
                    "yes", "y", "no", "n", "i", "idk", "i don't know",
                    "probably", "p", "probably not", "pn"
                ]
                return (m.content in replies and m.channel == ctx.channel
                        and m.author == ctx.author)
            try:
              msg = await self.bot.wait_for("message", check=check, timeout=30)
            except Exception:
              return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
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
        embed.set_image(url=f"{aki.first_guess['absolute_picture_path']}")
        embed.add_field(name="Reply with `yes/y` `no/n`", value="\u200b")
        await ctx.send(embed=embed)

        def check(m):
            return (m.content.lower() in ["yes", "y"]
                    and m.channel == ctx.channel and m.author == ctx.author)

        try: 
            correct = await self.bot.wait_for("message", check=check, timeout=30)
        except Exception: 
            return await ctx.send(f"{ctx.author.mention} you didn't answer on time")
        if correct.content.lower() == "yes" or correct.content.lower() == "y":
            embed = discord.Embed(title="Yay! I guessed it right",
                                  color=0xFF0000)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Oof! Kinda hard one",
                                  color=0xFF0000)
            await ctx.send(embed=embed)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(GuessName.guess())
        loop.close()
    
def setup(bot):
    bot.add_cog(game(bot))