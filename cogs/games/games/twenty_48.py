from __future__ import annotations

import itertools
import random
from io import BytesIO
from typing import TYPE_CHECKING, Literal

import discord
from discord.ext import commands
from jishaku.functools import executor_function as executor
from PIL import Image, ImageDraw, ImageFont

from .utils import DEFAULT_COLOR, BaseView, DiscordColor, Player, double_wait

if TYPE_CHECKING:
    from core.bot import Parrot

Board = list[list[int]]


class Twenty48:
    """2048 game, reaction-based.

    Slide numbered tiles on a grid, combining matching
    numbers to reach 2048.
    """

    player: Player

    def __init__(
        self,
        number_to_display_mapping: dict[str, str] | None = None,
        *,
        render_image: bool = True,
    ) -> None:
        self.embed_color: DiscordColor | None = None
        self.embed: discord.Embed | None = None

        self.board: Board = [[0 for _ in range(4)] for _ in range(4)]
        self.message: discord.Message | None = None

        self._controls = [
            "\N{LEFTWARDS BLACK ARROW}",
            "\N{BLACK RIGHTWARDS ARROW}",
            "\N{UPWARDS BLACK ARROW}",
            "\N{DOWNWARDS BLACK ARROW}",
        ]
        self._conversion = number_to_display_mapping or {}
        self._render_image = render_image

        if self._render_image:
            self._color_mapping: dict[str, tuple[tuple[int, int, int], int]] = {
                "0": ((204, 192, 179), 50),
                "2": ((237, 227, 217), 50),
                "4": ((237, 224, 200), 50),
                "8": ((242, 177, 121), 50),
                "16": ((245, 149, 100), 50),
                "32": ((246, 124, 95), 50),
                "64": ((246, 94, 59), 50),
                "128": ((236, 206, 113), 40),
                "256": ((236, 203, 96), 40),
                "512": ((236, 199, 80), 40),
                "1024": ((236, 196, 62), 30),
                "2048": ((236, 193, 46), 30),
                "4096": ((59, 57, 49), 30),
                "8192": ((59, 57, 49), 30),
            }

            self.LIGHT_CLR = (249, 246, 242)
            self.DARK_CLR = (119, 110, 101)
            self.BG_CLR = (187, 173, 160)

            self.BORDER_W = 20
            self.SQ_S = 100
            self.SPACE_W = 15

            self.IMG_LENGTH = self.BORDER_W * 2 + self.SQ_S * 4 + self.SPACE_W * 3

            self._font = ImageFont.truetype("assets/ClearSans-Bold.ttf", 50)

    def _reverse(self, board: Board) -> Board:
        return [row[::-1] for row in board]

    def _transp(self, board: Board) -> Board:
        return [[board[i][j] for i in range(4)] for j in range(4)]

    def _merge(self, board: Board) -> Board:
        for i in range(4):
            for j in range(3):
                tile = board[i][j]
                if tile == board[i][j + 1] and tile != 0:
                    board[i][j] *= 2
                    board[i][j + 1] = 0
        return board

    def _compress(self, board: Board) -> Board:
        new_board = [[0 for _ in range(4)] for _ in range(4)]
        for i in range(4):
            pos = 0
            for j in range(4):
                if board[i][j] != 0:
                    new_board[i][pos] = board[i][j]
                    pos += 1
        return new_board

    def move_left(self) -> None:
        stage = self._compress(self.board)
        stage = self._merge(stage)
        stage = self._compress(stage)
        self.board = stage

    def move_right(self) -> None:
        stage = self._reverse(self.board)
        stage = self._compress(stage)
        stage = self._merge(stage)
        stage = self._compress(stage)
        stage = self._reverse(stage)
        self.board = stage

    def move_up(self) -> None:
        stage = self._transp(self.board)
        stage = self._compress(stage)
        stage = self._merge(stage)
        stage = self._compress(stage)
        stage = self._transp(stage)
        self.board = stage

    def move_down(self) -> None:
        stage = self._transp(self.board)
        stage = self._reverse(stage)
        stage = self._compress(stage)
        stage = self._merge(stage)
        stage = self._compress(stage)
        stage = self._reverse(stage)
        stage = self._transp(stage)
        self.board = stage

    def spawn_new(self) -> bool:
        board = self.board
        zeroes = [(j, i) for j, sub in enumerate(board) for i, el in enumerate(sub) if el == 0]

        if not zeroes:
            return True
        else:
            i, j = random.choice(zeroes)
            board[i][j] = 2
            return False

    def number_to_emoji(self) -> str:
        board = self.board
        game_string = ""

        emoji_array = [[self._conversion.get(str(cell), f"`{cell}` ") for cell in row] for row in board]

        for row in emoji_array:
            game_string += "".join(row) + "\n"
        return game_string

    def check_win(self) -> bool:
        flattened = itertools.chain(*self.board)

        for num in (2048, 4096, 8192):
            if num in flattened:
                if num == 2048:
                    self.embed = discord.Embed(description="", color=self.embed_color)
                if self.embed is not None:
                    self.embed.description = (self.embed.description or "") + f"\N{WHITE MEDIUM STAR}: Congrats! You hit **{num}**!\n"

                    if num == self.win_at:
                        self.embed.description += "**Game Over! You Won**\n"
                        return True
        return False

    @executor
    def render_image(self) -> discord.File:
        SQ = self.SQ_S
        with Image.new("RGB", (self.IMG_LENGTH, self.IMG_LENGTH), self.BG_CLR) as img:
            cursor = ImageDraw.Draw(img)

            x = y = self.BORDER_W
            for row in self.board:
                for tile in row:
                    t = str(tile)
                    color, fsize = self._color_mapping.get(t, (self.BG_CLR, 50))
                    font = self._font.font_variant(size=fsize)
                    cursor.rounded_rectangle((x, y, x + SQ, y + SQ), radius=5, width=0, fill=color)

                    if t != "0":
                        text_fill = self.DARK_CLR if t in ("2", "4") else self.LIGHT_CLR
                        cursor.text(
                            (x + SQ / 2, y + SQ / 2),
                            t,
                            font=font,
                            anchor="mm",
                            fill=text_fill,
                        )

                    x += SQ + self.SPACE_W
                x = self.BORDER_W
                y += SQ + self.SPACE_W

            buf = BytesIO()
            img.save(buf, "PNG")
        buf.seek(0)
        return discord.File(buf, "2048.png")

    async def _wait_for_reaction(
        self,
        ctx: commands.Context[Parrot],
        timeout: float | None,
    ) -> tuple[discord.Reaction, discord.User] | None:
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                str(reaction.emoji) in self._controls and user == self.player and self.message is not None and reaction.message.id == self.message.id
            )

        try:
            done, _ = await double_wait(
                ctx.bot.wait_for("reaction_add", timeout=timeout, check=check),
                ctx.bot.wait_for("reaction_remove", timeout=timeout, check=check),
            )
        except TimeoutError:
            return None
        return done.pop().result()

    async def _process_reaction(
        self,
        emoji: str,
        user: discord.User,
        delete_button: bool,
        remove_reaction_after: bool,
    ) -> bool:
        stop = "\N{BLACK SQUARE FOR STOP}"
        if delete_button and emoji == stop:
            if self.message is not None:
                await self.message.delete()
            return True

        moves = {
            "\N{BLACK RIGHTWARDS ARROW}": self.move_right,
            "\N{LEFTWARDS BLACK ARROW}": self.move_left,
            "\N{DOWNWARDS BLACK ARROW}": self.move_down,
            "\N{UPWARDS BLACK ARROW}": self.move_up,
        }
        move = moves.get(emoji)
        if move is not None:
            move()

        if remove_reaction_after and self.message is not None:
            try:
                await self.message.remove_reaction(emoji, user)
            except discord.DiscordException:
                pass
        return False

    async def _update_message(self) -> None:
        if self.message is None:
            return
        if self._render_image:
            image = await self.render_image()
            await self.message.edit(attachments=[image], embed=self.embed)
        else:
            await self.message.edit(content=self.number_to_emoji(), embed=self.embed)

    async def start(  # noqa: PLR0913
        self,
        ctx: commands.Context[Parrot],
        *,
        win_at: Literal[2048, 4096, 8192] = 8192,
        timeout: float | None = None,
        remove_reaction_after: bool = False,
        delete_button: bool = False,
        embed_color: DiscordColor = DEFAULT_COLOR,
        **kwargs,
    ) -> discord.Message:
        self.win_at = win_at
        self.embed_color = embed_color
        self.player = ctx.author

        self.board[random.randrange(4)][random.randrange(4)] = 2
        self.board[random.randrange(4)][random.randrange(4)] = 2

        if self._render_image:
            image = await self.render_image()
            self.message = await ctx.reply(file=image, **kwargs)
        else:
            board_string = self.number_to_emoji()
            self.message = await ctx.reply(board_string, **kwargs)

        if delete_button:
            self._controls.append("\N{BLACK SQUARE FOR STOP}")

        for button in self._controls:
            await self.message.add_reaction(button)

        while not ctx.bot.is_closed():
            reaction_result = await self._wait_for_reaction(ctx, timeout)
            if reaction_result is None:
                break
            reaction, user = reaction_result

            emoji = str(reaction.emoji)
            if await self._process_reaction(emoji, user, delete_button, remove_reaction_after):
                break

            lost = self.spawn_new()
            won = self.check_win()

            if lost:
                self.embed = discord.Embed(
                    description="Game Over! You lost.",
                    color=self.embed_color,
                )

            await self._update_message()

            if won or lost:
                break

        return self.message


class Twenty48_Button(discord.ui.Button["BaseView"]):
    def __init__(self, game: BetaTwenty48, emoji: str, row: int | None = None) -> None:
        self.game = game

        style = discord.ButtonStyle.red if emoji == "\N{BLACK SQUARE FOR STOP}" else discord.ButtonStyle.blurple

        super().__init__(style=style, emoji=discord.PartialEmoji(name=emoji), row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        if interaction.user != self.game.player:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        emoji = str(self.emoji)

        if emoji == "\N{BLACK SQUARE FOR STOP}":
            self.view.stop()
            assert interaction.message is not None
            await interaction.message.delete()
            return

        elif emoji == "\N{BLACK RIGHTWARDS ARROW}":
            self.game.move_right()

        elif emoji == "\N{LEFTWARDS BLACK ARROW}":
            self.game.move_left()

        elif emoji == "\N{DOWNWARDS BLACK ARROW}":
            self.game.move_down()

        elif emoji == "\N{UPWARDS BLACK ARROW}":
            self.game.move_up()

        lost = self.game.spawn_new()
        won = self.game.check_win()

        if won or lost:
            self.view.disable_all()
            self.view.stop()

        if lost:
            self.game.embed = discord.Embed(
                description="Game Over! You lost.",
                color=self.game.embed_color,
            )

        if self.game._render_image:
            image = await self.game.render_image()
            await interaction.response.edit_message(attachments=[image], embed=self.game.embed)
        else:
            board_string = self.game.number_to_emoji()
            await interaction.response.edit_message(content=board_string, embed=self.game.embed)


class BetaTwenty48(Twenty48):
    """2048 game, button-based.

    Same as :class:`Twenty48` but uses arrow buttons
    for movement.
    """

    async def start(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        win_at: Literal[2048, 4096, 8192] = 2048,
        timeout: float | None = None,
        delete_button: bool = False,
        embed_color: DiscordColor = DEFAULT_COLOR,
        **kwargs,
    ) -> discord.Message:
        self.win_at = win_at
        self.embed_color = embed_color

        self.player = ctx.author
        self.view = BaseView(timeout=timeout)

        self.board[random.randrange(4)][random.randrange(4)] = 2
        self.board[random.randrange(4)][random.randrange(4)] = 2

        if delete_button:
            self._controls.append("\N{BLACK SQUARE FOR STOP}")

        self._add_buttons()

        if self._render_image:
            image = await self.render_image()
            self.message = await ctx.reply(file=image, view=self.view, **kwargs)
        else:
            board_string = self.number_to_emoji()
            self.message = await ctx.reply(content=board_string, view=self.view, **kwargs)
        self.view.message = self.message

        await self.view.wait()
        return self.message

    def _add_buttons(self) -> None:
        # [ ] [^] [-]
        # [<] [v] [>]

        blank_button = discord.ui.Button(style=discord.ButtonStyle.gray, label="\N{ZERO WIDTH SPACE}", disabled=True)
        up_button = Twenty48_Button(self, "\N{UPWARDS BLACK ARROW}")
        quit_button = Twenty48_Button(self, "\N{BLACK SQUARE FOR STOP}")

        down_button = Twenty48_Button(self, "\N{DOWNWARDS BLACK ARROW}", row=1)
        left_button = Twenty48_Button(self, "\N{LEFTWARDS BLACK ARROW}", row=1)
        right_button = Twenty48_Button(self, "\N{BLACK RIGHTWARDS ARROW}", row=1)

        self.view.add_item(blank_button)
        self.view.add_item(up_button)
        self.view.add_item(quit_button)
        self.view.add_item(left_button)
        self.view.add_item(down_button)
        self.view.add_item(right_button)
