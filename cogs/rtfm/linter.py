from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from core import Parrot


class Linter(commands.Cog):
    """Bot gives you some linting tools. Like flake8, pylint, mypy, bandit, pyright."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="lintcode", aliases=["lint"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode(self, ctx: commands.Context[Parrot]):
        """To lint your codes."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @lintcode.command(name="flake8", aliases=["f8", "flake"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode_flake8(
        self,
        ctx: commands.Context[Parrot],
        *,
        flag: Flake8Converter = commands.parameter(description="The code or flags to lint with flake8."),  # noqa: B008
    ):
        """Lint code with flake8."""
        linter = LintCode(flag).set_linttype("flake8")
        await linter.lint(ctx)

    @commands.command(name="flake8", aliases=["f8", "flake"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode_flake8_shortcut(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: str = commands.parameter(description="The code to lint with flake8."),
    ):
        """Shortcut for `lintcode flake8` with no flags, just the code."""
        linter = LintCode(code).set_linttype("flake8")
        await linter.lint_with_flake8(ctx)

    @lintcode.command(name="pylint", aliases=["pyl"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode_pylint(
        self,
        ctx: commands.Context[Parrot],
        *,
        flag: PyLintConverter = commands.parameter(description="The code or flags to lint with pylint."),  # noqa: B008
    ):
        """Lint code with pylint."""
        linter = LintCode(flag).set_linttype("pylint")
        await linter.lint(ctx)

    @commands.command(name="pylint", aliases=["pyl"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode_pylint_shortcut(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: str = commands.parameter(description="The code to lint with pylint."),
    ):
        """Shortcut for `lintcode pylint` with no flags, just the code."""
        linter = LintCode(code).set_linttype("pylint")
        await linter.lint_with_pylint(ctx)

    @lintcode.command(name="mypy", aliases=["mp"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode_mypy(
        self,
        ctx: commands.Context[Parrot],
        *,
        flag: MypyConverter = commands.parameter(description="The code or flags to lint with mypy."),  # noqa: B008
    ):
        """Lint code with mypy."""
        linter = LintCode(flag).set_linttype("mypy")
        await linter.lint(ctx)

    @lintcode.command(name="bandit", aliases=["bd"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode_bandit(
        self,
        ctx: commands.Context[Parrot],
        *,
        flag: BanditConverter = commands.parameter(description="The code or flags to lint with bandit."),  # noqa: B008
    ):
        """Lint code with bandit."""
        linter = LintCode(flag).set_linttype("bandit")
        await linter.lint(ctx)

    @commands.command(name="bandit", aliases=["bd"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def lintcode_bandit_shortcut(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: str = commands.parameter(description="The code to lint with bandit."),
    ):
        """Shortcut for `lintcode bandit` with no flags, just the code."""
        linter = LintCode(code).set_linttype("bandit")
        await linter.lint_with_bandit(ctx)

    @lintcode.command(name="black", aliases=["fmt"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def black(self, ctx: commands.Context[Parrot], *, code: str = commands.parameter(description="The code to format with black.")):
        """Format code with black."""
        linter = LintCode(code)
        await linter.run_black(ctx)

    @lintcode.command(name="black_isort", aliases=["fmt_isort"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def black_isort(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: str = commands.parameter(description="The code to format with black and isort."),
    ):
        """Format code with black and isort."""
        linter = LintCode(code)
        await linter.run_isort_with_black(ctx)

    @lintcode.command(name="isort", aliases=["is"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def isort(self, ctx: commands.Context[Parrot], *, code: str = commands.parameter(description="The code to format with isort.")):
        """Format code with isort."""
        linter = LintCode(code)
        await linter.run_isort(ctx)

    @lintcode.command(name="yapf", aliases=["yf"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def yapf(self, ctx: commands.Context[Parrot], *, code: str = commands.parameter(description="The code to format with yapf.")):
        """Format code with yapf."""
        linter = LintCode(code)
        await linter.run_yapf(ctx)

    @lintcode.command(name="autopep8", aliases=["ap8"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def autopep8(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: str = commands.parameter(description="The code to format with autopep8."),
    ):
        """Format code with autopep8."""
        linter = LintCode(code)
        await linter.run_autopep8(ctx)

    @lintcode.command(name="pyright", aliases=["pyr"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def pyright(
        self,
        ctx: commands.Context[Parrot],
        *,
        code: PyrightConverter = commands.parameter(description="The code or flags to lint with pyright."),  # noqa: B008
    ):
        """Lint code with pyright."""
        linter = LintCode(code).set_linttype("pyright")
        await linter.lint(ctx)

    @commands.command(name="pyright", aliases=["pyr"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def pyright_shortcut(self, ctx: commands.Context[Parrot], *, code: str = commands.parameter(description="The code to lint with pyright.")):
        """Shortcut for `lintcode pyright` with no flags, just the code."""
        linter = LintCode(code).set_linttype("pyright")
        await linter.lint_with_pyright(ctx)

    @lintcode.command(name="ruff", aliases=["rf"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def ruff(
        self,
        ctx: commands.Context[Parrot],
        *,
        flag: RuffConverter = commands.parameter(description="The code or flags to lint with ruff."),  # noqa: B008
    ):
        """Lint code with ruff."""
        linter = LintCode(flag).set_linttype("ruff")
        await linter.lint(ctx)

    @commands.command(name="ruff", aliases=["rf"])
    @commands.max_concurrency(1, commands.BucketType.user)
    async def ruff_shortcut(self, ctx: commands.Context[Parrot], *, code: str = commands.parameter(description="The code to lint with ruff.")):
        """Shortcut for `lintcode ruff` with no flags, just the code."""
        linter = LintCode(code).set_linttype("ruff")
        await linter.lint_with_ruff(ctx)


async def setup(bot: Parrot):
    await bot.add_cog(Linter(bot))
