from __future__ import annotations

import pymongo

import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.robopages import SimplePages

from .flag import GameCommandFlag


class Stats(Cog):
    """Your stats for various things"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def top(self, ctx: Context):
        """To display your statistics of games, WIP"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @top.command(name="2048")
    async def twenty_four_eight_stats(
        self,
        ctx: Context,
        user: discord.User | discord.Member | None = None,
        *,
        flag: GameCommandFlag,
    ):
        """2048 Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `moves` or `played`
        `--order_by`: Sort the list either `asc` (ascending) or `desc` (descending)
        `--limit`: To limit the search, default is 100
        """
        user = user or ctx.author
        col = self.bot.game_collections
        sort_by = f"game_twenty48_{flag.sort_by.lower()}" if flag.sort_by else "game_twenty48_played"
        order_by = pymongo.ASCENDING if flag.order_by == "asc" else pymongo.DESCENDING

        FILTER: dict = {sort_by: {"$exists": True}}

        if flag.me:
            FILTER["_id"] = user.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}
        LIMIT = flag.limit or float("inf")
        entries = []
        i = 0
        async for data in col.find(FILTER).sort(sort_by, order_by):
            user = await self.bot.get_or_fetch_member(ctx.guild, data["_id"], in_guild=False)
            entries.append(
                f"""User: `{user or 'NA'}`
`Games Played`: {data['game_twenty48_played']} games played
`Total Moves `: {data['game_twenty48_moves']} moves
""",
            )
            if i > LIMIT:
                break
            i += 1
        if not entries:
            await ctx.send(f"{ctx.author.mention} No results found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command(name="countryguess")
    async def country_guess_stats(
        self,
        ctx: Context,
        user: discord.User | None = None,
        *,
        flag: GameCommandFlag,
    ):
        """Country Guess Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `moves` or `played`
        `--order_by`: Sort the list either `asc` (ascending) or `desc` (descending)
        `--limit`: To limit the search, default is 100
        """
        return await self.__guess_stats(game_type="country_guess", ctx=ctx, user=user, flag=flag)

    @top.command(name="hangman")
    async def hangman_stats(
        self,
        ctx: Context,
        user: discord.User | None = None,
        *,
        flag: GameCommandFlag,
    ):
        """Country Guess Game stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list either by `win` or `games`
        `--order_by`: Sort the list either `1` (ascending) or `-1` (descending)
        """
        return await self.__guess_stats(game_type="hangman", ctx=ctx, user=user, flag=flag)

    async def __guess_stats(
        self,
        *,
        game_type: str,
        ctx: Context,
        user: discord.User | discord.Member | None = None,
        flag: GameCommandFlag,
    ):
        user = user or ctx.author
        col = self.bot.game_collections

        sort_by = f"game_{game_type}_{flag.sort_by or 'played'}"
        order_by = pymongo.ASCENDING if flag.order_by == "asc" else pymongo.DESCENDING

        FILTER: dict = {sort_by: {"$exists": True}}

        if flag.me and flag._global:
            return await ctx.send(f"{ctx.author.mention} you can't use both `--me` and `--global` at the same time!")

        if flag.me:
            FILTER["_id"] = user.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}

        LIMIT = flag.limit or float("inf")
        entries = []
        i = 0
        async for data in col.find(FILTER).sort(sort_by, order_by):
            user = await self.bot.get_or_fetch_member(ctx.guild, data["_id"], in_guild=False)
            entries.append(
                f"""User: `{user or 'NA'}`
`Games Played`: {data[f'game_{game_type}_played']} games played
`Total Wins  `: {data[f'game_{game_type}_won']} Wins
`Total Loss  `: {data[f'game_{game_type}_loss']} Loss
""",
            )
            if i > LIMIT:
                break
            i += 1
        if not entries:
            await ctx.send(f"{ctx.author.mention} No records found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command(name="chess")
    async def chess_stats(
        self,
        ctx: Context,
        user: discord.User | None = None,
        *,
        flag: GameCommandFlag,
    ):
        """Chess Game stats

        Flag Options:
        `--sort_by`: Sort the list either by `won` or `draw`
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        user = user or ctx.author  # type: ignore
        col = self.bot.game_collections

        data = await col.find_one(
            {"_id": user.id, "game_chess_played": {"$exists": True}},
        )
        if not data:
            await ctx.send(f"{f'{ctx.author.mention} you' if user is ctx.author else user} haven't played chess yet!")

            return
        entries = []
        chess_data = data["game_chess_stat"]
        for i in chess_data:
            user1 = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, i["game_chess_player_1"])
            user2 = await self.bot.getch(self.bot.get_user, self.bot.fetch_user, i["game_chess_player_2"])
            if not user1 and not user2:
                continue

            if ctx.author.id in {user1.id, user2.id}:
                entries.append(
                    f"""**{user1 or 'NA'} vs {user2 or 'NA'}**
`Winner`: {i["game_chess_winner"]}
""",
                )
            else:
                entries.append(
                    f"""{user1 or 'NA'} vs {user2 or 'NA'}
`Winner`: {i["game_chess_winner"]}
""",
                )
        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command(name="reaction")
    async def top_reaction(self, ctx: Context, *, flag: GameCommandFlag):
        """Reaction Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("reaction_test", ctx, flag)

    @top.command(name="memory")
    async def top_memory(self, ctx: Context, *, flag: GameCommandFlag):
        """Memory Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("memory_test", ctx, flag)

    async def __test_stats(self, game_type: str, ctx: Context, flag: GameCommandFlag):
        entries = []
        i = 1
        sort_by = f"game_{game_type}_{flag.sort_by or 'played'}".replace(" ", "_").lower()
        FILTER: dict = {sort_by: {"$exists": True}}
        if flag.me:
            FILTER["_id"] = ctx.author.id
        elif not flag._global:
            FILTER["_id"] = {"$in": [m.id for m in ctx.guild.members]}

        LIMIT = flag.limit or float("inf")
        col = self.bot.game_collections
        async for data in col.find(FILTER).sort(
            sort_by,
            pymongo.ASCENDING if flag.order_by == "asc" else pymongo.DESCENDING,
        ):
            user = await self.bot.get_or_fetch_member(ctx.guild, data["_id"], in_guild=False)
            if user is None:
                continue

            if user.id == ctx.author.id:
                entries.append(
                    f"""**{user or 'NA'}**
`{sort_by.replace('_', ' ').title()}`: {data[sort_by]}
""",
                )
            else:
                entries.append(
                    f"""{user or 'NA'}
`{sort_by.replace('_', ' ').title()}`: {data[sort_by]}
""",
                )
            if i >= LIMIT:
                break
            i += 1

        if not entries:
            await ctx.send(f"{ctx.author.mention} No records found")
            return

        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @top.command("typing")
    async def top_typing(self, ctx: Context, *, flag: GameCommandFlag):
        """Typing Test Stats

        Flag Options:
        `--me`: Only show your stats
        `--global`: Show global stats
        `--sort_by`: Sort the list by any of the following: `speed`, `accuracy`, `wpm`
        `--order_by`: Sort the list in ascending or descending order. `-1` (decending) or `1` (ascending)
        `--limit`: Limit the list to the top `limit` entries.
        """
        await self.__test_stats("typing_test", ctx, flag)

