import discord
from discord.ext import commands
from core import Parrot, Cog, Context
from datetime import datetime

from .tic_tac_toe import TicTacToe 
from .mine_sweeper import boardClass

class game(Cog):
    """All commands in this category are in testing for now"""

    def __init__(self, bot: Parrot):
        self.bot = bot
  
    @commands.command()
    async def ttt(self, ctx: Context, *, member: discord.Member):
        """Basic Tic-Tac-Toe game"""
        await ctx.send('Tic Tac Toe: X goes first', view=TicTacToe())

    @commands.command()
    async def minesweeper(self, ctx: Context, boardSize: int=None, numMines: int=None):
        """Basic MineSweeper Game"""
        boardSize = boardSize or 6
        numMines = numMines or 6
        gameOver = False
        winner = False
        Board = boardClass(boardSize, numMines)
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channe.id
 
        while not gameOver:
            msg = await ctx.send(embed=discord.embed(title="MineSweeper 1.0", description=f"```\n{Board}\n```", timestamp=datetime.utcnow(), color=ctx.author.color).set_footer(text=f"{ctx.author.name}"))
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
                    Board.makeMove(lc[0], lc[1])
                    gameOver = Board.hitMine(lc[0], lc[1])
                if Board.isWinner() and gameOver == False:
                    gameOver = True
                    winner = True
                break
        if winner:
            return await ctx.send(f"{ctx.author.mention} :tada: you win the game")
        else:
            return await ctx.send(f"{ctx.author.mention} you hit the mine")
        return await ctx.send(f"{ctx.author.mention} game ended")
    
def setup(bot):
    bot.add_cog(game(bot))