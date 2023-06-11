from __future__ import annotations

import asyncio
import os
import pathlib
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

import aiofiles
from jishaku.paginators import PaginatorInterface

import discord
from core import Context
from discord.ext import commands

try:
    import orjson as json
except ImportError:
    import json

import isort
from black import FileMode, format_str
from colorama import Fore

languages = pathlib.Path("extra/lang.txt").read_text()
GITHUB_API_URL = "https://api.github.com"
API_ROOT_RP = "https://realpython.com/search/api/v1/"
ARTICLE_URL = "https://realpython.com{article_url}"
SEARCH_URL_REAL = "https://realpython.com/search?q={user_search}"
BASE_URL_SO = "https://api.stackexchange.com/2.2/search/advanced"
SO_PARAMS = {"order": "desc", "sort": "activity", "site": "stackoverflow"}
SEARCH_URL_SO = "https://stackoverflow.com/search?q={query}"
URL = "https://cheat.sh/python/{search}"
ESCAPE_TT = str.maketrans({"`": "\\`"})
ANSI_RE = re.compile(r"\x1b\[.*?m")
# We need to pass headers as curl otherwise it would default to aiohttp which would return raw html.
HEADERS = {"User-Agent": "curl/7.68.0"}

ERROR_MESSAGE_CHEAT_SHEET = """
Unknown cheat sheet. Please try to reformulate your query.
**Examples**:
```md
$cht read json
$cht hello world
$cht lambda
```
"""

WTF_PYTHON_RAW_URL = "http://raw.githubusercontent.com/satwikkansal/wtfpython/master/"
BASE_URL = "https://github.com/satwikkansal/wtfpython"
API_ROOT = "https://www.codewars.com/api/v1/code-challenges/{kata_id}"
MINIMUM_CERTAINTY = 55
ERROR_MESSAGE = """
Unknown WTF Python Query. Please try to reformulate your query.
**Examples**:
```md
$wtf wild imports
$wtf subclass
$wtf del
```
"""
TIMEOUT = 120
BOOKMARK_EMOJI = "\N{PUSHPIN}"

MAPPING_OF_KYU: Dict[int, int] = {
    8: 0xDDDBDA,
    7: 0xDDDBDA,
    6: 0xECB613,
    5: 0xECB613,
    4: 0x3C7EBB,
    3: 0x3C7EBB,
    2: 0x866CC7,
    1: 0x866CC7,
}

# Supported languages for a kata on codewars.com
SUPPORTED_LANGUAGES: Dict[str, List[str]] = {
    "stable": [
        "c",
        "c#",
        "c++",
        "clojure",
        "coffeescript",
        "coq",
        "crystal",
        "dart",
        "elixir",
        "f#",
        "go",
        "groovy",
        "haskell",
        "java",
        "javascript",
        "kotlin",
        "lean",
        "lua",
        "nasm",
        "php",
        "python",
        "racket",
        "ruby",
        "rust",
        "scala",
        "shell",
        "sql",
        "swift",
        "typescript",
    ],
    "beta": [
        "agda",
        "bf",
        "cfml",
        "cobol",
        "commonlisp",
        "elm",
        "erlang",
        "factor",
        "forth",
        "fortran",
        "haxe",
        "idris",
        "julia",
        "nim",
        "objective-c",
        "ocaml",
        "pascal",
        "perl",
        "powershell",
        "prolog",
        "purescript",
        "r",
        "raku",
        "reason",
        "solidity",
        "vb.net",
    ],
}


NEGATIVE_REPLIES: List[str] = ["! YOU DONE? !", "! OK, HERE IS AN ERROR !", "! F. !"]


class Icons:
    bookmark: str = "https://images-ext-2.discordapp.net/external/zl4oDwcmxUILY7sD9ZWE2fU5R7n6QcxEmPYSE5eddbg/%3Fv%3D1/https/cdn.discordapp.com/emojis/654080405988966419.png?width=20&height=20"


class InformationDropdown(discord.ui.Select):
    """A dropdown inheriting from ui.Select that allows finding out other information about the kata."""

    original_message: discord.Message

    def __init__(
        self,
        language_embed: discord.Embed,
        tags_embed: discord.Embed,
        other_info_embed: discord.Embed,
        main_embed: discord.Embed,
    ):
        options: List[discord.SelectOption] = [
            discord.SelectOption(
                label="Main Information",
                description="See the kata's difficulty, description, etc.",
                emoji="\N{EARTH GLOBE AMERICAS}",
            ),
            discord.SelectOption(
                label="Languages",
                description="See what languages this kata supports!",
                emoji="\N{PAGE FACING UP}",
            ),
            discord.SelectOption(
                label="Tags",
                description="See what categories this kata falls under!",
                emoji="\N{ROUND PUSHPIN}",
            ),
            discord.SelectOption(
                label="Other Information",
                description="See how other people performed on this kata and more!",
                emoji="\N{INFORMATION SOURCE}",
            ),
        ]

        # We map the option label to the embed instance so that it can be easily looked up later in O(1)
        self.mapping_of_embeds: Dict[str, discord.Embed] = {
            "Main Information": main_embed,
            "Languages": language_embed,
            "Tags": tags_embed,
            "Other Information": other_info_embed,
        }

        super().__init__(
            placeholder="See more information regarding this kata",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Callback for when someone clicks on a dropdown."""
        # Edit the message to the embed selected in the option
        # The `original_message` attribute is set just after the message is sent with the view.
        # The attribute is not set during initialization.
        result_embed = self.mapping_of_embeds[self.values[0]]
        await self.original_message.edit(embed=result_embed)


# linting

from ._bandit import BanditConverter
from ._bandit import validate_flag as bandit_validate_flag
from ._flake8 import Flake8Converter
from ._flake8 import validate_flag as flake8_validate_flag
from ._mypy import MypyConverter
from ._mypy import validate_flag as mypy_validate_flag
from ._pylint import PyLintConverter
from ._pylint import validate_flag as pylint_validate_flag


async def code_to_file(code: str) -> str:
    filename = f"temp/runner_{int(datetime.now(timezone.utc).timestamp())}.py"
    async with aiofiles.open(filename, "w") as f:
        await f.write(code)

    return filename


def background_task(func: Callable, *args: Any, **kwargs: Any) -> Callable[[], Any]:
    """Decorator for running a function in the background."""

    def wrapper() -> Any:
        return func(*args, **kwargs)

    return wrapper


async def lint(cmd: str, filename: str) -> Dict[str, str]:
    proc = await asyncio.create_subprocess_shell(
        f"{cmd} {filename}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    payload = {"main": f"{cmd} {filename} exited with {proc.returncode}"}
    if stdout:
        payload["stdout"] = stdout.decode()
    if stderr:
        payload["stderr"] = stderr.decode()

    threading.Thread(target=background_task(os.remove, filename)).start()

    return payload


class LintCode:
    source: str
    language: Optional[str]

    def __init__(
        self,
        flag: Union[
            Flake8Converter, MypyConverter, PyLintConverter, BanditConverter, str
        ],
    ) -> None:
        self.codeblock = flag if isinstance(flag, str) else flag.code
        self.flag = flag

        self.get_code()

    def get_code(self) -> str:
        try:
            block, code = self.codeblock.split("\n", 1)
        except ValueError:
            self.source = self.codeblock
            self.language = None
        else:
            if not block.startswith("```") and not code.endswith("```"):
                self.source = self.codeblock
                self.language = None
            else:
                self.language = block[3:]
                self.source = code.rstrip("`").replace("```", "")

        return self.source

    def set_linttype(self, linttype: str) -> LintCode:
        self.linttype = linttype
        return self

    async def lint(self, ctx: Context) -> None:
        if self.linttype not in {"flake8", "bandit", "pylint", "mypy"}:
            await ctx.reply("Invalid lint type.")
            return

        if self.language not in {"python", "py", None}:
            await ctx.reply("Invalid language.")
            return

        filename = await code_to_file(self.source)

        cmd_str = ""
        if self.linttype == "flake8":
            cmd_str = flake8_validate_flag(self.flag)
        elif self.linttype == "bandit":
            cmd_str = bandit_validate_flag(self.flag)
        elif self.linttype == "pylint":
            cmd_str = pylint_validate_flag(self.flag)
        elif self.linttype == "mypy":
            cmd_str = mypy_validate_flag(self.flag)

        data = await lint(cmd_str, filename) if cmd_str else {}

        if not data:
            await ctx.reply("No output.")
            return

        if "main" in data:
            await ctx.reply(f"```ansi\n{data['main']}```")
        if "stdout" in data:
            pages = commands.Paginator(prefix="```ansi\n", suffix="```", max_size=1980)
            for line in data["stdout"].splitlines():
                pages.add_line(f"{Fore.WHITE}{line}")

            interference = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interference.send_to(ctx)

        if "stderr" in data:
            pages = commands.Paginator(prefix="```ansi\n", suffix="```", max_size=1980)
            for line in data["stderr"].splitlines():
                pages.add_line(f"{Fore.RED}{line}")

            interference = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interference.send_to(ctx)

    async def lint_with_pyright(self, ctx: Context) -> None:
        # sourcery skip: move-assign
        filename = await code_to_file(self.source)
        data = await lint("pyright --outputjson", filename)

        await ctx.reply(f"```ansi\n{data['main']}```")

        if data.get("stdout"):
            data = json.loads(data["stdout"])
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            pages.add_line(f"{Fore.WHITE}Pyright Version - {Fore.WHITE}{data['version']}\n")
            
            pages.add_line(
                f"{Fore.RED}{data['summary']['errorCount']} errors - {Fore.YELLOW}{data['summary']['warningCount']} warnings - {Fore.BLUE}{data['summary']['informationCount']} information\n"
            )
            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

            if data["generalDiagnostics"]:
                await interface.add_line(f"{Fore.WHITE}General Diagnostics:\n")
                for error in data["generalDiagnostics"]:
                    file = f"{Fore.WHITE}{filename}"
                    line = f"{Fore.GREEN}{error['range']['start']['line']}:{error['range']['end']['line']}"
                    severity = error["severity"]
                    if severity.lower() == "error":
                        severity = f"{Fore.RED}{severity}"
                    elif severity.lower() == "warning":
                        severity = f"{Fore.YELLOW}{severity}"
                    elif severity.lower() == "information":
                        severity = f"{Fore.BLUE}{severity}"

                    message = f"{Fore.BLUE}{error['message']}"
                    rule = f"{Fore.WHITE}({Fore.CYAN}{error.get('rule', 'N/A')}{Fore.WHITE})"

                    await interface.add_line(
                        f"{file}:{line} - {severity} - {message} {rule}"
                    )
                
                await interface.add_line(f"\n{Fore.BLUE}Diagnosed completed in {data['summary']['timeInSec']} seconds")

        if data.get("stderr"):
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            for line in data["stderr"].splitlines():
                pages.add_line(f"{Fore.RED}{line}\n")

            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

    async def run_black(self, ctx: Context) -> None:
        ini = time.perf_counter()
        res = await ctx.bot.func(format_str, self.source, mode=FileMode())
        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(
                f"```ansi\n{Fore.RED}[No Changes in the code, already formatted]```"
            )
            return

        await ctx.reply(
            f"```ansi\n{Fore.GREEN}[Formated Code in {int(end-ini)} seconds]``````py\n{res}```"
        )

    async def run_isort(self, ctx: Context) -> None:
        ini = time.perf_counter()
        res = await ctx.bot.func(isort.code, self.source)
        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(f"```ansi\n{Fore.RED}[No Changes]```")
            return

        await ctx.reply(
            f"```ansi\n{Fore.GREEN}[Formated Code in {int(end-ini)} seconds]``````py\n{res}```"
        )

    async def run_isort_with_black(self, ctx: Context) -> None:
        import isort
        from black import FileMode, format_str

        ini = time.perf_counter()
        res = await ctx.bot.func(isort.code, self.source)
        res = await ctx.bot.func(format_str, res, mode=FileMode())
        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(f"```ansi\n{Fore.RED}[No Changes]```")
            return

        await ctx.reply(
            f"```ansi\n{Fore.GREEN}[Formated Code in {int(end-ini)} seconds]``````py\n{res}```"
        )
