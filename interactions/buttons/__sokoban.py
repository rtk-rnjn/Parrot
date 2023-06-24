from __future__ import annotations

import time
from typing import List, Optional

import discord
from core import Context


class SokobanGame:
    """The real sokoban game"""

    legend = {
        " ": "<:blank:922048341964103710>",
        "#": ":white_large_square:",
        "@": ":flushed:",
        "$": ":soccer:",
        ".": ":o:",
        "x": ":x:",  # TODO: change the "x"
    }

    # Do not DM me or mail me how this works
    # Thing is, I myself forget
    def __init__(self, level: List[str]):
        self.level = level
        self.player = []
        self.blocks = []
        self.target = []

    def __repr__(self):
        return self.show()

    def display_board(self) -> str:
        main = ""
        for i in self.level:
            for j in i:
                main += self.legend[j]
            main += "\n"
        return main

    def _get_cords(self):
        self.player, self.blocks = [], []
        for index, i in enumerate(self.level):
            for _index, j in enumerate(i):
                if j == "@":
                    self.player = [index, _index]
                if j in ("$", "x"):
                    self.blocks.append([index, _index])
                if j in (".", "x"):
                    self.target.append([index, _index])

    def show(self) -> str:
        main = ""
        for i in self.level:
            for j in i:
                main += str(j)
            main += "\n"
        return main

    def move_up(self) -> None:
        if self.level[self.player[0] - 1][self.player[1]] in (" ", "."):
            self.level[self.player[0] - 1][self.player[1]] = "@"
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0] - 1, self.player[1]]
            return

        if (self.level[self.player[0] - 1][self.player[1]] in ("$", "x")) and (
            self.level[self.player[0] - 2][self.player[1]] in (" ", ".")
        ):
            self.level[self.player[0] - 1][self.player[1]] = "@"
            self.level[self.player[0] - 2][self.player[1]] = (
                "$" if self.level[self.player[0] - 2][self.player[1]] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0] - 1, self.player[1]]
            return

    def move_down(self) -> None:
        if self.level[self.player[0] + 1][self.player[1]] in (" ", "."):
            self.level[self.player[0] + 1][self.player[1]] = "@"
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0] + 1, self.player[1]]
            return

        if (self.level[self.player[0] + 1][self.player[1]] in ("$", "x")) and (
            self.level[self.player[0] + 2][self.player[1]] in (" ", ".")
        ):
            self.level[self.player[0] + 1][self.player[1]] = "@"
            self.level[self.player[0] + 2][self.player[1]] = (
                "$" if self.level[self.player[0] + 2][self.player[1]] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0] + 1, self.player[1]]
            return

    def move_left(self) -> None:
        if self.level[self.player[0]][self.player[1] - 1] in (" ", "."):
            self.level[self.player[0]][self.player[1] - 1] = "@"
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0], self.player[1] - 1]
            return

        if (self.level[self.player[0]][self.player[1] - 1] in ("$", "x")) and (
            self.level[self.player[0]][self.player[1] - 2] in (" ", ".")
        ):
            self.level[self.player[0]][self.player[1] - 1] = "@"
            self.level[self.player[0]][self.player[1] - 2] = (
                "$" if self.level[self.player[0]][self.player[1] - 2] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0], self.player[1] - 1]
            return

    def move_right(self) -> None:
        if self.level[self.player[0]][self.player[1] + 1] in (" ", "."):
            self.level[self.player[0]][self.player[1] + 1] = "@"
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0], self.player[1] + 1]
            return

        if (self.level[self.player[0]][self.player[1] + 1] in ("$", "x")) and (
            self.level[self.player[0]][self.player[1] + 2] in (" ", ".")
        ):
            self.level[self.player[0]][self.player[1] + 1] = "@"
            self.level[self.player[0]][self.player[1] + 2] = (
                "$" if self.level[self.player[0]][self.player[1] + 2] == " " else "x"
            )
            self.level[self.player[0]][self.player[1]] = " " if self.player not in self.target else "."
            self.player = [self.player[0], self.player[1] + 1]
            return

    def is_game_over(self) -> bool:
        self.player = []
        self.blocks = []
        for index, i in enumerate(self.level):
            for _index, j in enumerate(i):
                if j == "@":
                    self.player = [index, _index]
                if j in ("$", "x"):
                    self.blocks.append([index, _index])
        return self.target == self.blocks


class SokobanGameView(discord.ui.View):
    def __init__(
        self,
        game: SokobanGame,
        user: discord.Member,
        ctx: Context,
        level: Optional[int] = None,
        *,
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        self.user = user
        self.game = game
        self._original_game = game
        self.level = level or 1
        self.ctx = ctx

        self.ini = time.perf_counter()
        self.moves = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user == interaction.user:
            return True
        await interaction.response.send_message(
            f"Only **{self.user}** can interact. Run the command if you want to.",
            ephemeral=True,
        )
        return False

    def make_win_embed(self) -> discord.Embed:
        embed = (
            discord.Embed(title="You win! :tada:", timestamp=discord.utils.utcnow())
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png")
        )
        embed.description = f"{self.game.display_board()}"
        embed.add_field(
            name="Thanks for playing",
            value=f"For next level type `{self.ctx.prefix}sokoban {self.level+1}`",
        )
        return embed

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER R}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.game = self._original_game
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="\N{UPWARDS BLACK ARROW}", style=discord.ButtonStyle.red, disabled=False)
    async def upward(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.moves += 1
        self.game.move_up()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png")
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(embed=self.make_win_embed(), view=None)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
        label="\u200b",
        style=discord.ButtonStyle.primary,
        disabled=False,
    )
    async def null_button2(self, interaction: discord.Interaction, _: discord.ui.Button):
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
        self.moves += 1
        self.game.move_left()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png")
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(embed=self.make_win_embed(), view=None)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{DOWNWARDS BLACK ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def downward(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.moves += 1
        self.game.move_down()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png")
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(embed=self.make_win_embed(), view=None)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        emoji="\N{BLACK RIGHTWARDS ARROW}",
        label="\u200b",
        style=discord.ButtonStyle.red,
        disabled=False,
        row=1,
    )
    async def right(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.moves += 1
        self.game.move_right()
        embed = (
            discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png")
        )

        if self.game.is_game_over():
            await interaction.response.edit_message(embed=self.make_win_embed(), view=None)

        await interaction.response.edit_message(embed=embed, view=self)

    async def start(self, ctx: Context):
        await ctx.send(
            embed=discord.Embed(
                title="Sokoban Game",
                description=f"{self.game.display_board()}",
                timestamp=discord.utils.utcnow(),
            )
            .set_footer(text=f"User: {self.user}")
            .set_thumbnail(url="https://cdn.discordapp.com/attachments/894938379697913916/922772599627472906/icon.png"),
            view=self,
        )
