from __future__ import annotations

from core import Cog, Context, Parrot
from discord.ext import commands

from ._utils import (
    BanditConverter,
    Flake8Converter,
    LintCode,
    MypyConverter,
    PyLintConverter,
    PyrightConverter,
    RuffConverter,
)


class Linter(Cog):
    """Bot gives you some linting tools. Like flake8, pylint, mypy, bandit, pyright. Can also format code with black and imports with isort"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="lintcode", aliases=["lint"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode(self, ctx: Context):
        """To lint your codes"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @lintcode.command(name="flake8", aliases=["f8", "flake"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode_flake8(self, ctx: Context, *, flag: Flake8Converter):
        """Lint code with flake8

        **Flags**
        `--code` - To lint the code
        `--ignore` - To ignore some errors
        `--max_line_length` - To set the max line length
        `--max_complexity` - To set the max complexity
        `--select` - To select some errors

        **Example**
        `--ignore E203,W503 --max_line_length 120 --max_complexity 10 --select E111,E112,E113,E901,E902 --code def foo(): pass`
        """
        linter = LintCode(flag).set_linttype("flake8")
        await linter.lint(ctx)

    @commands.command(name="flake8", aliases=["f8", "flake"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode_flake8_shortcut(self, ctx: Context, *, code: str):
        """Shortcut for `lintcode flake8` with no flags, just the code"""
        linter = LintCode(code).set_linttype("flake8")
        await linter.lint_with_flake8(ctx)

    @lintcode.command(name="pylint", aliases=["pyl"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode_pylint(self, ctx: Context, *, flag: PyLintConverter):
        """Lint code with pylint

        **Flags**
        `--code` - To lint the code
        `--confidence` - To set the confidence
        `--disable` - To disable some errors
        `--enable` - To enable some errors

        **Example**
        `--confidence HIGH --code def foo(): pass`
        """
        linter = LintCode(flag).set_linttype("pylint")
        await linter.lint(ctx)

    @commands.command(name="pylint", aliases=["pyl"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode_pylint_shortcut(self, ctx: Context, *, code: str):
        """Shortcut for `lintcode pylint` with no flags, just the code"""
        linter = LintCode(code).set_linttype("pylint")
        await linter.lint_with_pylint(ctx)

    @lintcode.command(name="mypy", aliases=["mp"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode_mypy(self, ctx: Context, *, flag: MypyConverter):
        """Lint code with mypy"""
        linter = LintCode(flag).set_linttype("mypy")
        await linter.lint(ctx)

    @lintcode.command(name="bandit", aliases=["bd"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode_bandit(self, ctx: Context, *, flag: BanditConverter):
        """Lint code with bandit

        **Flags**
        `--code` - To lint the code
        `--skip` - To skip some errors
        `--read` - To read the code from a file
        `--verbose` - To set the verbosity level
        `--level` - To set the severity level
        `--confidence` - To set the confidence level

        **Example**
        `--skip B101 --read yes --verbose yes --level low --confidence low --code def foo(): pass`
        """
        linter = LintCode(flag).set_linttype("bandit")
        await linter.lint(ctx)

    @commands.command(name="bandit", aliases=["bd"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def lintcode_bandit_shortcut(self, ctx: Context, *, code: str):
        """Shortcut for `lintcode bandit` with no flags, just the code"""
        linter = LintCode(code).set_linttype("bandit")
        await linter.lint_with_bandit(ctx)

    @lintcode.command(name="black", aliases=["fmt"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def black(self, ctx: Context, *, code: str):
        """Format code with black"""
        linter = LintCode(code)
        await linter.run_black(ctx)

    @lintcode.command(name="black_isort", aliases=["fmt_isort"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def black_isort(self, ctx: Context, *, code: str):
        """Format code with black and isort"""
        linter = LintCode(code)
        await linter.run_isort_with_black(ctx)

    @lintcode.command(name="isort", aliases=["is"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def isort(self, ctx: Context, *, code: str):
        """Format code with isort"""
        linter = LintCode(code)
        await linter.run_isort(ctx)

    @lintcode.command(name="yapf", aliases=["yf"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def yapf(self, ctx: Context, *, code: str):
        """Format code with yapf"""
        linter = LintCode(code)
        await linter.run_yapf(ctx)

    @lintcode.command(name="autopep8", aliases=["ap8"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def autopep8(self, ctx: Context, *, code: str):
        """Format code with autopep8"""
        linter = LintCode(code)
        await linter.run_autopep8(ctx)

    @lintcode.command(name="pyright", aliases=["pyr"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def pyright(self, ctx: Context, *, code: PyrightConverter):
        """Lint code with pyright

        **Flags**
        `--code` - To lint the code

        **Example**
        `--code def foo(): pass`
        """
        linter = LintCode(code).set_linttype("pyright")
        await linter.lint(ctx)

    @commands.command(name="pyright", aliases=["pyr"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def pyright_shortcut(self, ctx: Context, *, code: str):
        """Shortcut for `lintcode pyright` with no flags, just the code"""
        linter = LintCode(code).set_linttype("pyright")
        await linter.lint_with_pyright(ctx)

    @lintcode.command(name="ruff", aliases=["rf"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def ruff(self, ctx: Context, *, flag: RuffConverter):
        """Lint code with ruff"""
        linter = LintCode(flag).set_linttype("ruff")
        await linter.lint(ctx)

    @commands.command(name="ruff", aliases=["rf"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def ruff_shortcut(self, ctx: Context, *, code: str):
        """Shortcut for `lintcode ruff` with no flags, just the code"""
        linter = LintCode(code).set_linttype("ruff")
        await linter.lint_with_ruff(ctx)
