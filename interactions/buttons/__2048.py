from __future__ import annotations

import itertools
import random
from typing import Any, Optional, Union

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

    def reverse(self, board: list[list[int]]) -> list[list[int]]:
        new_board: list[list[int]] = []
        for i in range(self.size):
            new_board.append([])
            for j in range(self.size):
                new_board[i].append(board[i][(self.size - 1) - j])
        return new_board

    def transp(self, board: list[list[int]]) -> list[list[int]]:
        new_board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        for i, j in itertools.product(range(self.size), range(self.size)):
            new_board[i][j] = board[j][i]
        return new_board

    def merge(self, board: list[list[int]]) -> list[list[int]]:
        for i, j in itertools.product(range(self.size), range(self.size - 1)):
            if board[i][j] == board[i][j + 1] and board[i][j] != 0:
                board[i][j] += board[i][j]
                board[i][j + 1] = 0
        return board

    def compress(self, board: list[list[int]]) -> list[list[int]]:
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
        zeroes = [(j, i) for j, sub in enumerate(board) for i, el in enumerate(sub) if el == 0]
        if not zeroes:
            self.has_empty = False
            return
        i, j = random.choice(zeroes)
        board[i][j] = 2
        self.has_empty = 0 in itertools.chain(*self.board)

    def number_to_emoji(self) -> str:
        board = self.board
        emoji_array = [[self._conversion[str(i)] for i in row] for row in board]
        return "".join("".join(row) + "\n" for row in emoji_array)

    def lost(self) -> Optional[bool]:
        if self.has_empty:
            return None

        board = [list(i) for i in self.board]

        def restore():
            return setattr(self, "board", board)

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
        return restore() if self.board != board else True

    def start(self) -> None:
        self.board[random.randrange(4)][random.randrange(4)] = 2
        self.board[random.randrange(4)][random.randrange(4)] = 2

        self.number_to_emoji()


class Twenty48_Button(discord.ui.View):
    def __init__(
        self,
        game: Twenty48,
        user: Union[discord.Member, discord.User],
        timeout: float = 60.0,
        *,
        bot: Parrot,
        **kwargs: Any,
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
        await interaction.response.send_message(content="This isn't your game!", ephemeral=True)
        return False

    async def update_to_db(self) -> None:
        col = self.bot.game_collections
        await col.update_one(
            {"_id": self.user.id},
            {
                "$inc": {"game_twenty48_played": 1, "game_twenty48_moves": self._moves},
            },
            upsert=True,
        )

    async def on_timeout(self):
        await self.update_to_db()

    async def _game_lost(self, embed: discord.Embed) -> None:
        if self.game.lost():
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True

            embed.add_field(name="Result", value="`You are out of moves`")
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
        embed = discord.Embed(
            title="2048 Game",
            description=f"{board_string}",
        ).set_footer(text=f"Total Moves: {self._moves}")
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
        embed: discord.Embed = discord.Embed(
            title="2048 Game",
            description=f"{board_string}",
        ).set_footer(text=f"Total Moves: {self._moves}")
        await self._game_lost(embed)
        await interaction.response.edit_message(content=f"{interaction.user.mention}", embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button2(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.update_to_db()
        self.stop()

        if interaction.message:
            await interaction.message.delete(delay=0)

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
        embed: discord.Embed = discord.Embed(
            title="2048 Game",
            description=f"{board_string}",
        ).set_footer(text=f"Total Moves: {self._moves}")
        await self._game_lost(embed)

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
        embed: discord.Embed = discord.Embed(
            title="2048 Game",
            description=f"{board_string}",
        ).set_footer(text=f"Total Moves: {self._moves}")
        await self._game_lost(embed)
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
        embed: discord.Embed = discord.Embed(
            title="2048 Game",
            description=f"{board_string}",
        ).set_footer(text=f"Total Moves: {self._moves}")
        await self._game_lost(embed)
        await interaction.response.edit_message(content=f"{interaction.user.mention}", embed=embed, view=self)
