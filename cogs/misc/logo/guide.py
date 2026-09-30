from __future__ import annotations

import discord

EMBED_COLOR = discord.Color.blurple()


def build_logo_guide() -> list[discord.Embed]:
    pages: list[discord.Embed] = []

    # 1. Intro
    embed = discord.Embed(
        title="\N{TURTLE} Logo Guide (1/8): Introduction",
        description=(
            "Logo lets you draw pictures by giving commands to a **turtle**.\n"
            "The turtle walks around a canvas and leaves a line behind it.\n\n"
            "**Quick facts**\n"
            "• Commands are **not case-sensitive** (`fd` = `FD`)\n"
            "• The canvas is **1000\N{MULTIPLICATION SIGN}800**, and the turtle starts in the center\n"
            "• The turtle starts facing **up** (0° = north, 90° = east)\n"
            "• Comments start with `;`\n\n"
            "**Your first program**\n"
            "```logo\n"
            "REPEAT 4 [FD 100 RT 90] ; draw a square\n"
            "```"
        ),
        color=EMBED_COLOR,
    )
    pages.append(embed)

    # 2. Movement
    embed = (
        discord.Embed(
            title="\N{TURTLE} Logo Guide (2/8): Movement",
            description="Move and turn the turtle. Values can be numbers or expressions.",
            color=EMBED_COLOR,
        )
        .add_field(
            name="Commands",
            value=(
                "`FD n` / `FORWARD n`: move forward\n"
                "`BK n` / `BACK n`: move backward\n"
                "`RT n` / `RIGHT n`: turn right *n* degrees\n"
                "`LT n` / `LEFT n`: turn left *n* degrees"
            ),
            inline=False,
        )
        .add_field(
            name="Example: a triangle",
            value="```logo\nFD 100 RT 120\nFD 100 RT 120\nFD 100 RT 120\n```",
            inline=False,
        )
    )
    pages.append(embed)

    # 3. Pen
    embed = (
        discord.Embed(
            title="\N{TURTLE} Logo Guide (3/8): Pen & Colors",
            description="Control whether the turtle draws, and how the line looks.",
            color=EMBED_COLOR,
        )
        .add_field(
            name="Commands",
            value=(
                "`PU` / `PENUP`: lift the pen (move without drawing)\n"
                "`PD` / `PENDOWN`: put the pen down (draw again)\n"
                '`SETPC "COLOR` / `SETPENCOLOR`: change color\n'
                "`SETWIDTH n` / `SETW n`: line width (1 to 50)"
            ),
            inline=False,
        )
        .add_field(
            name="Colors",
            value=(
                "Write a **single quote before the name**, no closing quote.\n"
                "```\n"
                "BLACK, WHITE, RED, GREEN, BLUE, YELLOW,\n"
                "CYAN, MAGENTA, ORANGE, PURPLE, PINK, BROWN\n"
                "```"
            ),
            inline=False,
        )
        .add_field(
            name="Example",
            value='```logo\nSETPC "RED\nSETWIDTH 5\nFD 100\nPU FD 30 PD\nSETPC "BLUE\nFD 100\n```',
            inline=False,
        )
    )
    pages.append(embed)

    # 4. Position
    embed = (
        discord.Embed(
            title="\N{TURTLE} Logo Guide (4/8): Position & Heading",
            description="Jump straight to a spot or direction instead of walking there.",
            color=EMBED_COLOR,
        )
        .add_field(
            name="Commands",
            value=(
                "`HOME`: return to the center, facing up\n"
                "`SETXY x y`: go to coordinates (`0 0` is the center)\n"
                "`SETH n` / `SETHEADING n`: face a compass direction\n"
                "`CS` / `CLEARSCREEN`: erase all lines"
            ),
            inline=False,
        )
        .add_field(
            name="Coordinates",
            value="Positive **x** goes right and positive **y** goes up.",
            inline=False,
        )
        .add_field(
            name="Note",
            value="`SETXY` draws a line if the pen is down. Use `PU` first to jump without drawing.",
            inline=False,
        )
        .add_field(
            name="Example",
            value="```logo\nPU SETXY -100 50 PD\nSETH 90\nFD 200\n```",
            inline=False,
        )
    )
    pages.append(embed)

    # 5. Repeat
    embed = (
        discord.Embed(
            title="\N{TURTLE} Logo Guide (5/8): Repeating Things",
            description=("`REPEAT n [ ... ]` runs the commands inside the brackets *n* times.\nLoops can be nested."),
            color=EMBED_COLOR,
        )
        .add_field(
            name="Hexagon",
            value="```logo\nREPEAT 6 [FD 80 RT 60]\n```",
            inline=False,
        )
        .add_field(
            name="Flower (nested loops)",
            value="```logo\nREPEAT 12 [\n  REPEAT 4 [FD 60 RT 90]\n  RT 30\n]\n```",
            inline=False,
        )
        .add_field(name="Limit", value="`n` must be between 0 and 10,000.", inline=False)
    )
    pages.append(embed)

    # 6. Variables & math
    embed = (
        discord.Embed(
            title="\N{TURTLE} Logo Guide (6/8): Variables & Math",
            description=("Store numbers with `MAKE` and read them with a colon: `:NAME`.\nVariables can change, and that's how you build spirals."),
            color=EMBED_COLOR,
        )
        .add_field(
            name="Operators",
            value=("`+`  `-`  `*`  `/`  and parentheses `( )`\nComparisons `=` `<` `>` give `1` (true) or `0` (false)"),
            inline=False,
        )
        .add_field(
            name="Example: square spiral",
            value="```logo\nMAKE :S 5\nREPEAT 40 [\n  FD :S RT 90\n  MAKE :S :S + 5\n]\n```",
            inline=False,
        )
        .add_field(
            name="Example: math in commands",
            value="```logo\nMAKE :SIZE 50\nFD :SIZE * 2\nRT 360 / 5\n```",
            inline=False,
        )
    )
    pages.append(embed)

    # 7. Procedures
    embed = (
        discord.Embed(
            title="\N{TURTLE} Logo Guide (7/8): Procedures",
            description=("Define your own commands with `TO name :param ... END`, then call them by name. Arguments come after the name."),
            color=EMBED_COLOR,
        )
        .add_field(
            name="Example",
            value=(
                "```logo\n"
                "TO SQUARE :SIZE\n"
                "  REPEAT 4 [FD :SIZE RT 90]\n"
                "END\n\n"
                "TO FLOWER :SIZE\n"
                "  REPEAT 12 [SQUARE :SIZE RT 30]\n"
                "END\n\n"
                'SETPC "PURPLE\n'
                "FLOWER 80\n"
                "```"
            ),
            inline=False,
        )
        .add_field(
            name="Good to know",
            value=(
                "• Procedures can be defined anywhere in your program\n"
                "• You must pass exactly as many arguments as parameters\n"
                "• Procedures can call other procedures"
            ),
            inline=False,
        )
    )
    pages.append(embed)

    # 8. Limits & errors
    embed = (
        discord.Embed(
            title="\N{TURTLE} Logo Guide (8/8): Limits & Troubleshooting",
            description="Programs are sandboxed so nobody can freeze the bot.",
            color=EMBED_COLOR,
        )
        .add_field(
            name="Limits",
            value=(
                "• Max **100,000** operations per program\n"
                "• `REPEAT` count: 0 to **10,000**\n"
                "• Procedure nesting depth: **100**\n"
                "• Pen width: 1 to **50**"
            ),
            inline=False,
        )
        .add_field(
            name="Common errors",
            value=(
                "**Syntax error**: check for a missing `]` or `END`\n"
                "**Unknown variable**: use `MAKE :X 1` before `:X`\n"
                "**Unknown color**: pick one from the color list\n"
                "**Expects N argument(s)**: wrong argument count in a procedure call"
            ),
            inline=False,
        )
        .add_field(
            name="Tip",
            value="Wrap your code in a code block and test small pieces first.",
            inline=False,
        )
    )
    pages.append(embed)

    return pages
