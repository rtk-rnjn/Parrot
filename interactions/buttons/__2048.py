from __future__ import annotations

import itertools
import random
from typing import Any, List, Optional

import discord

from core import Parrot

URL_THUMBNAIL = "https://cdn.discordapp.com/attachments/894938379697913916/922771882904793120/41NgOgTVblL.png"


class Twenty48:
    def __init__(self, number_to_display_dict, *, size: int = 4) -> None:
        self.has_empty = True
        self.board = [[0 for _ in range(size)] for _ in range(size)]
        self.size = size
        self.message = None
        self._controls = ["w", "a", "s", "d"]
        self._conversion = number_to_display_dict

    def reverse(self, board: List[List[int]]) -> List[List[int]]:
        new_board: List[List[int]] = []
        for i in range(self.size):
            new_board.append([])
            for j in range(self.size):
                new_board[i].append(board[i][(self.size - 1) - j])
        return new_board

    def transp(self, board: List[List[int]]) -> List[List[int]]:
        new_board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        for i in range(self.size):
            for j in range(self.size):
                new_board[i][j] = board[j][i]
        return new_board

    def merge(self, board: List[List[int]]) -> List[List[int]]:
        for i in range(self.size):
            for j in range(self.size - 1):
                if board[i][j] == board[i][j + 1] and board[i][j] != 0:
                    board[i][j] += board[i][j]
                    board[i][j + 1] = 0
        return board

    def compress(self, board: List[List[int]]) -> List[List[int]]:
        new_board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        for i in range(self.size):
            pos = 0
            for j in range(self.size):
                if board[i][j] != 0:
                    new_board[i][pos] = board[i][j]
                    pos += 1
        return new_board

    def move_left(self) -> None:
        stage = self.compress(self.board)
        stage = self.merge(stage)
        stage = self.compress(stage)
        self.board = stage

    def move_right(self) -> None:
        stage = self.reverse(self.board)
        stage = self.compress(stage)
        stage = self.merge(stage)
        stage = self.compress(stage)
        stage = self.reverse(stage)
        self.board = stage

    def move_up(self) -> None:
        stage = self.transp(self.board)
        stage = self.compress(stage)
        stage = self.merge(stage)
        stage = self.compress(stage)
        stage = self.transp(stage)
        self.board = stage

    def move_down(self) -> None:
        stage = self.transp(self.board)
        stage = self.reverse(stage)
        stage = self.compress(stage)
        stage = self.merge(stage)
        stage = self.compress(stage)
        stage = self.reverse(stage)
        stage = self.transp(stage)
        self.board = stage

    def spawn_new(self) -> None:
        board = self.board
        zeroes = [
            (j, i) for j, sub in enumerate(board) for i, el in enumerate(sub) if el == 0
        ]
        if not zeroes:
            self.has_empty = False
            return
        i, j = random.choice(zeroes)
        board[i][j] = 2
        self.has_empty = 0 in itertools.chain(*self.board)

    def number_to_emoji(self) -> str:
        board = self.board
        GameString = ""
        emoji_array = [[self._conversion[str(l)] for l in row] for row in board]
        for row in emoji_array:
            GameString += "".join(row) + "\n"
        return GameString

    def lost(self) -> Optional[bool]:
        if self.has_empty:
            return None

        board = [list(i) for i in self.board]
        restore = lambda: setattr(self, "board", board)

        self.move_up()
        if self.board != board:
            return restore()
        self.move_down()
        if self.board != board:
            return restore()
        self.move_left()
        if self.board != board:
            return restore()
        self.move_right()
        if self.board != board:
            return restore()
        return True

    def start(self) -> None:

        self.board[random.randrange(4)][random.randrange(4)] = 2
        self.board[random.randrange(4)][random.randrange(4)] = 2

        board_string = self.number_to_emoji()


class Twenty48_Button(discord.ui.View):
    def __init__(
        self, game: Twenty48, user: discord.Member, timeout: float = 60.0, *, bot: Parrot, **kwargs: Any
    ) -> None:
        super().__init__(timeout=timeout, **kwargs)
        self.game = game

        self.__conversion = game._conversion
        self.__controls = game._controls
        self.__size = game.size
        self.__board = game.board
        self.__has_empty = game.has_empty
        self.__message = game.message

        self.bot = bot
        self.user = user

        self._moves = 0

    def make_original_instance(self) -> Twenty48:
        original_game = Twenty48(self.__conversion)
        original_game.board = self.__board
        original_game.has_empty = self.__has_empty
        original_game.size = self.__size
        original_game.message = self.__message
        original_game._controls = self.__controls
        return original_game

    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if interaction.user == self.user:
            return True
        await interaction.response.send_message(
            content="This isn't your game!", ephemeral=True
        )
        return False

    async def update_to_db(self) -> None:
        await self.bot.mongo.extra.games_leaderboard.games_leaderboard(
            {"_id": self.user.id,},
            {"$inc": {"twenty48.games_played": 1, "twenty48.total_moves": self._moves}},
            upsert=True,
        )

    async def on_timeout(self):
        await self.update_to_db()

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER R}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game = self.make_original_instance()
        self._moves = 0
        board_string = self.game.number_to_emoji()
        embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{board_string}",
            )
            .set_footer(text=f"Total Moves: {self._moves}")
        )
        await self.update_to_db()
        await interaction.response.edit_message(content=f"{interaction.user.mention}", embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{UPWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
    )
    async def upward(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_up()
        self._moves += 1
        self.game.spawn_new()
        board_string = self.game.number_to_emoji()
        embed: discord.Embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{board_string}",
            )
            .set_footer(text=f"Total Moves: {self._moves}")
        )
        if self.game.lost():
            for c in self.children:
                c.disabled = True
            embed.add_field(name="Result", value="`You are out of moves`")
            await self.update_to_db()
        await interaction.response.edit_message(content=f"{interaction.user.mention}", embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button2(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        await self.update_to_db()
        self.stop()
        await interaction.message.delete()

    @discord.ui.button(
        emoji="\N{LEFTWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def left(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_left()
        self._moves += 1
        self.game.spawn_new()
        board_string = self.game.number_to_emoji()
        embed: discord.Embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{board_string}",
            )
            .set_footer(text=f"Total Moves: {self._moves}")
        )
        if self.game.lost():
            for c in self.children:
                c.disabled = True
            embed.add_field(name="Result", value="`You are out of moves`")
            await self.update_to_db()

        await interaction.response.edit_message(content=f"{interaction.user.mention}", embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{DOWNWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def down(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_down()
        self._moves += 1
        self.game.spawn_new()
        board_string = self.game.number_to_emoji()
        embed: discord.Embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{board_string}",
            )
            .set_footer(text=f"Total Moves: {self._moves}")
        )
        if self.game.lost():
            for c in self.children:
                c.disabled = True
            embed.add_field(name="Result", value="`You are out of moves`")
            await self.update_to_db()
        await interaction.response.edit_message(content=f"{interaction.user.mention}", embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{BLACK RIGHTWARDS ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def right(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game.move_right()
        self._moves += 1
        self.game.spawn_new()
        board_string = self.game.number_to_emoji()
        embed: discord.Embed = (
            discord.Embed(
                title="2048 Game",
                description=f"{board_string}",
            )
            .set_footer(text=f"Total Moves: {self._moves}")
        )
        if self.game.lost():
            for c in self.children:
                c.disabled = True
            embed.add_field(name="Result", value="`You are out of moves`")
            await self.update_to_db()
        await interaction.response.edit_message(content=f"{interaction.user.mention}", embed=embed, view=self)
