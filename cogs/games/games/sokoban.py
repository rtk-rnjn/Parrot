from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from enum import StrEnum

import discord
from discord.ext import commands

LEVELS_DIR = pathlib.Path("assets/sokoban")


EMOTES = {
    "blank": "<:blank:922048341964103710>",
    "wall": "\N{WHITE LARGE SQUARE}",
    "player": "\N{FLUSHED FACE}",
    "box": "\N{SOCCER BALL}",
    "target": "\N{HEAVY LARGE CIRCLE}",
    "box_on_target": "\N{CROSS MARK}",
}


class Direction(StrEnum):
    UP = "up"
    LEFT = "left"
    DOWN = "down"
    RIGHT = "right"


DIRECTION_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.UP: (-1, 0),
    Direction.LEFT: (0, -1),
    Direction.DOWN: (1, 0),
    Direction.RIGHT: (0, 1),
}


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def moved(self, direction: Direction) -> Position:
        row_delta, col_delta = DIRECTION_DELTAS[direction]

        return Position(
            self.row + row_delta,
            self.col + col_delta,
        )


@dataclass(frozen=True)
class GameState:
    player: Position
    blocks: frozenset[Position]
    moves: int


@dataclass
class SokobanGame:
    """
    Sokoban game engine.

    Level characters:

        . = target
        $ = box
        @ = player
        x = box on target
          = empty floor
    """

    level: list[str]

    player: Position = field(init=False)
    blocks: set[Position] = field(init=False, default_factory=set)
    targets: set[Position] = field(init=False, default_factory=set)
    walls: set[Position] = field(init=False, default_factory=set)

    rows: int = field(init=False)
    cols: int = field(init=False)

    moves: int = 0
    history: list[GameState] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.level:
            raise ValueError("Sokoban level is empty.")

        self.rows = len(self.level)
        self.cols = max(len(row) for row in self.level)

        found_player: Position | None = None

        for row, line in enumerate(self.level):
            for col in range(self.cols):
                char = line[col] if col < len(line) else " "

                position = Position(row, col)

                match char:
                    case "#":
                        self.walls.add(position)

                    case ".":
                        self.targets.add(position)

                    case "$":
                        self.blocks.add(position)

                    case "@":
                        if found_player is not None:
                            raise ValueError(
                                "Level contains more than one player.",
                            )

                        found_player = position

                    case "x":
                        self.blocks.add(position)
                        self.targets.add(position)

                    case " ":
                        pass

                    case _:
                        message = f"Invalid character {char!r} at row {row + 1}, column {col + 1}."
                        raise ValueError(message)

        if found_player is None:
            raise ValueError("Level does not contain a player.")

        if len(self.blocks) != len(self.targets):
            message = f"Level has {len(self.blocks)} blocks but {len(self.targets)} targets."
            raise ValueError(message)

        self.player = found_player

    def display_board(self) -> str:
        """
        Render the board using Discord emojis.

        The board is NOT put inside a code block because custom
        Discord emojis need to be rendered by Discord.
        """

        lines: list[str] = []

        for row in range(self.rows):
            cells: list[str] = []

            for col in range(self.cols):
                position = Position(row, col)

                if position in self.walls:
                    emoji = EMOTES["wall"]

                elif position == self.player:
                    emoji = EMOTES["player"]

                elif position in self.blocks:
                    if position in self.targets:
                        emoji = EMOTES["box_on_target"]
                    else:
                        emoji = EMOTES["box"]

                elif position in self.targets:
                    emoji = EMOTES["target"]

                else:
                    emoji = EMOTES["blank"]

                cells.append(emoji)

            lines.append("".join(cells))

        return "\n".join(lines)

    def is_inside(self, position: Position) -> bool:
        return 0 <= position.row < self.rows and 0 <= position.col < self.cols

    def is_wall(self, position: Position) -> bool:
        return position in self.walls

    def block_at(self, position: Position) -> bool:
        return position in self.blocks

    def save_state(self) -> None:
        self.history.append(
            GameState(
                player=self.player,
                blocks=frozenset(self.blocks),
                moves=self.moves,
            ),
        )

    def move(self, direction: Direction) -> bool:  # noqa: PLR0911
        """
        Attempt to move the player.

        Returns:
            True  -> game state changed
            False -> movement was blocked
        """

        new_player = self.player.moved(direction)

        if not self.is_inside(new_player):
            return False

        if self.is_wall(new_player):
            return False

        if not self.block_at(new_player):
            self.save_state()

            self.player = new_player
            self.moves += 1

            return True

        new_block = new_player.moved(direction)

        if not self.is_inside(new_block):
            return False

        if self.is_wall(new_block):
            return False

        if self.block_at(new_block):
            return False

        self.save_state()

        self.blocks.remove(new_player)
        self.blocks.add(new_block)

        self.player = new_player
        self.moves += 1

        return True

    def undo(self) -> bool:
        if not self.history:
            return False

        state = self.history.pop()

        self.player = state.player
        self.blocks = set(state.blocks)
        self.moves = state.moves

        return True

    def restart(self) -> None:
        fresh = SokobanGame(self.level.copy())

        self.player = fresh.player
        self.blocks = fresh.blocks
        self.targets = fresh.targets
        self.walls = fresh.walls

        self.rows = fresh.rows
        self.cols = fresh.cols

        self.moves = 0
        self.history.clear()

    def is_game_over(self) -> bool:
        return self.blocks == self.targets


def load_levels() -> dict[int, list[str]]:
    levels: dict[int, list[str]] = {}

    if not LEVELS_DIR.exists():
        message = f"Levels directory does not exist: {LEVELS_DIR}"
        raise FileNotFoundError(message)

    for file in LEVELS_DIR.glob("level*.txt"):
        if not file.is_file():
            continue

        try:
            level_number = int(file.stem[5:])
        except ValueError:
            continue

        text = file.read_text(encoding="utf-8")

        levels[level_number] = text.rstrip("\n").splitlines()

    if not levels:
        message = f"No level files found in {LEVELS_DIR}"
        raise RuntimeError(message)

    return dict(sorted(levels.items()))


LEVELS = load_levels()


class SokobanGameView(discord.ui.View):
    ctx: commands.Context[commands.Bot]
    user: discord.Member | discord.User
    level: int
    game: SokobanGame
    message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user.id:
            return True

        await interaction.response.send_message(f"Only **{self.user}** can control this Sokoban game.", ephemeral=True)

        return False

    def make_embed(self) -> discord.Embed:
        embed = (
            discord.Embed(
                title=f"Sokoban — Level {self.level}",
                description=self.game.display_board(),
                color=discord.Color.blurple(),
                timestamp=discord.utils.utcnow(),
            )
            .add_field(name="Controls", value=("Use the buttons below.\n↶ Undo\n↻ Restart"), inline=True)
            .set_footer(text=f"Moves: {self.game.moves}")
        )

        return embed

    def make_win_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="You win! 🎉",
            description=self.game.display_board(),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        embed.set_footer(text=f"Moves: {self.game.moves}")

        return embed

    async def update_game(self, interaction: discord.Interaction) -> None:
        if self.game.is_game_over():
            self.stop()

            await interaction.response.edit_message(embed=self.make_win_embed(), view=None)
            return

        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    async def perform_move(self, interaction: discord.Interaction, direction: Direction) -> None:
        self.game.move(direction)
        await self.update_game(interaction)

    @discord.ui.button(label="↶", style=discord.ButtonStyle.secondary, row=0)
    async def undo_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.game.undo()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(emoji="\N{UPWARDS BLACK ARROW}", style=discord.ButtonStyle.secondary, row=0)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.perform_move(interaction, Direction.UP)

    @discord.ui.button(emoji="\N{CROSS MARK}", style=discord.ButtonStyle.secondary, row=0)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()

        await interaction.response.edit_message(content="Sokoban game closed.", embed=None, view=None)

    @discord.ui.button(emoji="\N{LEFTWARDS BLACK ARROW}", style=discord.ButtonStyle.secondary, row=1)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.perform_move(interaction, Direction.LEFT)

    @discord.ui.button(emoji="\N{DOWNWARDS BLACK ARROW}", style=discord.ButtonStyle.secondary, row=1)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.perform_move(interaction, Direction.DOWN)

    @discord.ui.button(emoji="\N{BLACK RIGHTWARDS ARROW}", style=discord.ButtonStyle.secondary, row=1)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.perform_move(interaction, Direction.RIGHT)

    async def on_timeout(self) -> None:
        self.stop()

        if self.message is None:
            return

        try:
            await self.message.edit(view=None)
        except discord.HTTPException:
            pass

    async def start(self, ctx: commands.Context, level: int | None = 1) -> None:
        self.ctx = ctx
        self.user = ctx.author

        if level is None:
            level = 1

        if level not in LEVELS:
            await ctx.reply(f"Level {level} does not exist.")
            return

        self.level = level
        self.game = SokobanGame(LEVELS[level])

        embed = self.make_embed()

        self.message = await ctx.reply(embed=embed, view=self)
