from __future__ import annotations

import discord

EMBED_COLOR = discord.Color.blurple()


def build_logo_guide() -> list[discord.Embed]:
    raw_pages: list[tuple[str, discord.Embed]] = []

    # 1. Introduction
    raw_pages.append(
        (
            "Introduction",
            discord.Embed(
                title="Logo Guide: Introduction",
                description=(
                    "Logo lets you draw vector graphics by giving commands to a **turtle**.\n"
                    "The turtle walks around the canvas and leaves a trail behind it.\n\n"
                    "**Quick facts**\n"
                    "\N{BULLET} Commands are **not case-sensitive** (`fd 50` = `FD 50`)\n"
                    "\N{BULLET} The canvas is **1000\N{MULTIPLICATION SIGN}800**, and `(0, 0)` is the center\n"
                    "\N{BULLET} The turtle starts facing **up** (`0\N{DEGREE SIGN}` = north, `90\N{DEGREE SIGN}` = east)\n"
                    "\N{BULLET} Comments start with `;` and run to the end of the line\n\n"
                    "**Your first programs**\n"
                    "```logo\n"
                    "REPEAT 4 [FD 100 RT 90]   ; draw a square\n"
                    "REPEAT 5 [FD 120 RT 144]  ; draw a 5-pointed star\n"
                    "```"
                ),
                color=EMBED_COLOR,
            ),
        )
    )

    # 2. Movement, Position & Heading
    raw_pages.append(
        (
            "Movement & Position",
            discord.Embed(
                title="Logo Guide: Movement & Position",
                description=(
                    "Walk relative to the turtle's direction or jump straight to `(x, y)` coordinates "
                    "(positive **x** goes right, positive **y** goes up)."
                ),
                color=EMBED_COLOR,
            )
            .add_field(
                name="Walking & Turning",
                value=(
                    "`FD n` / `FORWARD n`: move forward *n* pixels\n"
                    "`BK n` / `BACK n`: move backward *n* pixels\n"
                    "`RT n` / `RIGHT n`: turn clockwise *n* degrees\n"
                    "`LT n` / `LEFT n`: turn counter-clockwise *n* degrees"
                ),
                inline=False,
            )
            .add_field(
                name="Jumping, Clearing & Reporters",
                value=(
                    "`HOME`: go to `(0, 0)` facing `0\N{DEGREE SIGN}` (draws if pen is down)\n"
                    "`SETXY x y` / `SETPOS [x y]`: move to `(x, y)`\n"
                    "`SETX x` / `SETY y`: move horizontally or vertically\n"
                    "`SETH n` / `SETHEADING n`: face compass angle *n*\n"
                    "`CS` / `CLEARSCREEN`: erase everything **and** reset to `(0, 0)`\n"
                    "`CLEAN`: erase lines **without** moving the turtle\n"
                    "`ST` / `HT`: show or hide the turtle cursor\n"
                    "`XCOR`, `YCOR`, `POS`, `HEADING`, `TOWARDS [x y]`, `DIST [x y]`"
                ),
                inline=False,
            )
            .add_field(
                name="Example",
                value="```logo\nPU SETXY -100 50 PD\nSETH 90\nFD 200\n```",
                inline=False,
            ),
        )
    )

    # 3. Pen & Colors
    raw_pages.append(
        (
            "Pen & Colors",
            discord.Embed(
                title="Logo Guide: Pen & Colors",
                description="Control whether the turtle draws, its stroke width, and canvas/pen colors.",
                color=EMBED_COLOR,
            )
            .add_field(
                name="Pen Commands",
                value=(
                    "`PU` / `PENUP`: lift pen (move without drawing)\n"
                    "`PD` / `PENDOWN` / `PPT`: normal drawing mode\n"
                    "`PE` / `PENERASE`: erase mode (draws with background color)\n"
                    "`PX` / `PENREVERSE`: invert underlying pixel colors\n"
                    "`SETPENSIZE n` / `SETWIDTH n`: line width (`1` to `50`)"
                ),
                inline=False,
            )
            .add_field(
                name="Color Commands (`SETPC`, `SETBG`, `SETFC`)",
                value=(
                    '`SETPC "NAME`: named color (single quote before name, no closing quote)\n'
                    '`SETPC "#RRGGBB`: hex color (`"#FF5733` or `"#F80`)\n'
                    "`SETPC [r g b]`: RGB list (`0` to `255`, e.g. `SETPC [255 87 51]`)\n"
                    "`SETPC n`: MSWLogo palette index (`0` to `15`)\n"
                    "`SETBG ...` / `SETSC ...`: set canvas background color\n"
                    "`SETFC ...`: set flood-fill color"
                ),
                inline=False,
            )
            .add_field(
                name="Named Colors",
                value=(
                    "```\n"
                    "BLACK, WHITE, RED, GREEN, LIME, BLUE, YELLOW, CYAN, AQUA,\n"
                    "MAGENTA, ORANGE, PURPLE, VIOLET, PINK, BROWN, TAN, FOREST,\n"
                    "SALMON, GRAY, SILVER, NAVY, TEAL, MAROON, OLIVE, GOLD, CORAL\n"
                    "```"
                ),
                inline=False,
            ),
        )
    )

    # 4. Shapes, Fills & Labels
    raw_pages.append(
        (
            "Shapes, Fills & Text",
            discord.Embed(
                title="Logo Guide: Shapes, Fills & Text",
                description="Draw curves, filled polygons, flood-fills, and text labels.",
                color=EMBED_COLOR,
            )
            .add_field(
                name="Commands",
                value=(
                    "`CIRCLE r`: draw a full circle of radius *r* around the turtle\n"
                    "`ARC angle r`: draw an arc sweeping clockwise from current heading\n"
                    "`ELLIPSE rx ry`: draw an ellipse with radii *rx* and *ry*\n"
                    "`DOT` / `(DOT [x y])`: plot a dot of the current pen width\n"
                    "`FILLED color [ ... ]`: fill the polygon traced by the commands inside `[ ... ]`\n"
                    "`FILL`: flood-fill the enclosed region around the turtle\n"
                    '`LABEL "text`: draw text at the turtle (`SETLABELHEIGHT n` sets font size `4..100`)'
                ),
                inline=False,
            )
            .add_field(
                name="Example: Filled Sunburst",
                value=('```logo\nSETBG "NAVY\nSETPC "ORANGE\nFILLED "GOLD [\n  REPEAT 18 [FD 120 RT 160]\n]\n```'),
                inline=False,
            ),
        )
    )

    # 5. Loops
    raw_pages.append(
        (
            "Loops & Iteration",
            discord.Embed(
                title="Logo Guide: Loops (`REPEAT`, `FOR`, `WHILE`, `FOREACH`)",
                description="Run a bracketed list `[ ... ]` multiple times. Inside any loop, `REPCOUNT` (or `#`) gives the 1-based step number.",
                color=EMBED_COLOR,
            )
            .add_field(
                name="Loop Primitives",
                value=(
                    "`REPEAT n [ ... ]`: run body *n* times\n"
                    "`FOR [var start end] [ ... ]`: count from *start* to *end*\n"
                    "`FOR [var start end step] [ ... ]`: count with custom *step*\n"
                    "`WHILE [cond] [ ... ]`: repeat while *cond* is true\n"
                    "`UNTIL [cond] [ ... ]`: repeat until *cond* becomes true\n"
                    "`FOREACH list [ ... ]`: run body for each item (`?` reads current item)"
                ),
                inline=False,
            )
            .add_field(
                name="Examples",
                value=(
                    "```logo\n"
                    "; Rainbow spiral using FOR\n"
                    "FOR [S 5 150 3] [\n"
                    "  SETPC MODULO REPCOUNT 15 + 1\n"
                    "  FD :S RT 89\n"
                    "]\n\n"
                    "; Cycle through colors with FOREACH\n"
                    "FOREACH [RED GOLD LIME CYAN] [\n"
                    "  SETPC ? FD 80 RT 90\n"
                    "]\n"
                    "```"
                ),
                inline=False,
            ),
        )
    )

    # 6. Conditionals & Logic
    raw_pages.append(
        (
            "Conditionals & Logic",
            discord.Embed(
                title="Logo Guide: Conditionals (`IF`, `IFELSE`, `TEST`)",
                description='Branch based on comparisons. In Logo, `1` (or `"TRUE`) is true and `0` (or `"FALSE`) is false.',
                color=EMBED_COLOR,
            )
            .add_field(
                name="Conditionals & Operators",
                value=(
                    "`IF cond [then_list]`: run if *cond* is true\n"
                    "`IFELSE cond [then_list] [else_list]`: run first list if true, second if false\n"
                    "`TEST cond` \N{RIGHTWARDS ARROW} `IFTRUE [...]` / `IFFALSE [...]`\n"
                    "**Comparisons**: `=`  `<>` (or `!=`)  `<`  `>`  `<=`  `>=`\n"
                    "**Logic**: `AND a b`, `OR a b`, `NOT a` (or variadic `(AND a b c)`)"
                ),
                inline=False,
            )
            .add_field(
                name="Example: Alternating Star",
                value=('```logo\nREPEAT 12 [\n  IFELSE (REPCOUNT % 2) = 0 [SETPC "RED] [SETPC "CYAN]\n  FD 100 RT 150\n]\n```'),
                inline=False,
            ),
        )
    )

    # 7. Variables & Math
    raw_pages.append(
        (
            "Variables & Math",
            discord.Embed(
                title="Logo Guide: Variables & Math",
                description=('Set variables with a **quoted word** (`MAKE "NAME val`) and read them with a **colon** (`:NAME` or `THING "NAME`).'),
                color=EMBED_COLOR,
            )
            .add_field(
                name="Arithmetic & Math Functions",
                value=(
                    "**Infix**: `+`  `-`  `*`  `/`  `%` (remainder)  `^` (power)\n"
                    "**Functions**: `SUM`, `DIFFERENCE`, `PRODUCT`, `QUOTIENT`, `REMAINDER`, `MODULO`, "
                    "`SQRT`, `POWER`, `ABS`, `INT`, `ROUND`, `SIGN`, `SIN`, `COS`, `TAN`, `ARCTAN`, `PI`\n"
                    "**Random**: `RANDOM n` (`0..n-1`), `(RANDOM min max)`, `RERANDOM seed`"
                ),
                inline=False,
            )
            .add_field(
                name="Example: Square Spiral",
                value=('```logo\nMAKE "S 5\nREPEAT 40 [\n  FD :S RT 90\n  MAKE "S :S + 4\n]\n```'),
                inline=False,
            ),
        )
    )

    # 8. Procedures & Recursion
    raw_pages.append(
        (
            "Procedures & Recursion",
            discord.Embed(
                title="Logo Guide: Procedures (`TO ... END`, `OUTPUT`, `STOP`)",
                description=("Define your own commands or value-returning functions with `TO name :p1 :p2 ... END`."),
                color=EMBED_COLOR,
            )
            .add_field(
                name="Procedure Tools",
                value=(
                    "`STOP`: exit the current procedure immediately\n"
                    "`OUTPUT val` / `OP val`: exit and return *val* to the caller\n"
                    '`LOCAL "X` / `LOCALMAKE "X val`: keep variables local to the procedure\n'
                    "*Tail-recursive procedures are automatically optimized (TCO)!*"
                ),
                inline=False,
            )
            .add_field(
                name="Example: Recursive Fractal Tree",
                value=(
                    "```logo\n"
                    "TO TREE :LEN\n"
                    "  IF :LEN < 8 [STOP]\n"
                    "  FD :LEN\n"
                    "  LT 30 TREE :LEN * 0.7 RT 60\n"
                    "  TREE :LEN * 0.7 LT 30\n"
                    "  PU BK :LEN PD\n"
                    "END\n\n"
                    'PU SETXY 0 -200 PD SETPC "FOREST\n'
                    "TREE 90\n"
                    "```"
                ),
                inline=False,
            ),
        )
    )

    # 9. Lists, Words & Multi-Turtle
    raw_pages.append(
        (
            "Lists & Multi-Turtle",
            discord.Embed(
                title="Logo Guide: Lists, Words & Multiple Turtles",
                description="Manipulate lists/words and command up to 16 turtles simultaneously.",
                color=EMBED_COLOR,
            )
            .add_field(
                name="Data & Output Primitives",
                value=(
                    "`LIST`, `SENTENCE`/`SE`, `WORD`, `FIRST`, `LAST`, `BUTFIRST`/`BF`, `BUTLAST`/`BL`\n"
                    "`ITEM i x`, `PICK x`, `COUNT x`, `FPUT`, `LPUT`, `EMPTYP`, `MEMBERP`\n"
                    "`PRINT x` / `(PRINT a b ...)`, `SHOW x`, `TYPE x`"
                ),
                inline=False,
            )
            .add_field(
                name="Multiple Turtles (`0` to `15`)",
                value=(
                    "`SETTURTLE n`: switch to turtle *n*\n"
                    "`TELL [0 1 2 3]`: send movement/drawing commands to several turtles at once\n"
                    "`ASK n [ ... ]`: temporarily run commands as turtle *n*\n"
                    "`WHO`: returns the active turtle ID(s)"
                ),
                inline=False,
            )
            .add_field(
                name="Example: 4 Synchronized Turtles",
                value=("```logo\nTELL [0 1 2 3]\nFOREACH [0 1 2 3] [ASK ? [SETH ? * 90 SETPC ? + 1]]\nREPEAT 36 [FD 15 RT 10]\n```"),
                inline=False,
            ),
        )
    )

    # 10. Limits & Troubleshooting
    raw_pages.append(
        (
            "Limits & Troubleshooting",
            discord.Embed(
                title="Logo Guide: Limits & Troubleshooting",
                description="Every program runs in an isolated sandbox with strict resource caps.",
                color=EMBED_COLOR,
            )
            .add_field(
                name="Sandbox Limits",
                value=(
                    "\N{BULLET} Source length: **2,000** characters\n"
                    "\N{BULLET} Execution budget: **200,000** operations (3s wall-clock timeout)\n"
                    "\N{BULLET} Loop limit (`REPEAT`/`FOR`/`WHILE`): **10,000** iterations\n"
                    "\N{BULLET} Drawn segments: **20,000**  |  `FILL` calls: **50**\n"
                    "\N{BULLET} Non-tail call depth: **100**  |  Pen width: **1 to 50**"
                ),
                inline=False,
            )
            .add_field(
                name="Common Errors & Fixes",
                value=(
                    '\N{BULLET} **Unknown variable `:X`**: set it first with `MAKE "X 10` (use a quote `"` on `MAKE`, colon `:` to read)\n'
                    "\N{BULLET} **Two negative arguments (`SETXY 100 -50`)**: keep a space before `-50` and no space after `-` (`100 - 50` subtracts!)\n"
                    '\N{BULLET} **Unknown color**: prefix hex codes with `#` (`SETPC "#ACE`) or use `[r g b]`'
                ),
                inline=False,
            ),
        )
    )

    total = len(raw_pages)
    embeds: list[discord.Embed] = []
    for idx, (section_label, embed) in enumerate(raw_pages, start=1):
        embed.title = f"\N{TURTLE} Logo Guide ({idx}/{total}): {section_label}"
        embed.set_footer(text=f"Page {idx} of {total} \N{MIDDLE DOT} Use the buttons or menu below to navigate")
        embeds.append(embed)

    return embeds
