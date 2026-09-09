from __future__ import annotations

import asyncio
import importlib.metadata as pkg_resources
import io
import json
import os
import re
import tempfile
import threading
import time
from functools import partial
from typing import TypeVar

import arrow
import autopep8
import bandit
import discord
import flake8
import isort
import pylint
import pyright
from black import FileMode, format_str
from colorama import Fore
from discord.ext import commands
from jishaku.paginators import PaginatorInterface
from yapf.yapflib.yapf_api import FormatCode as yapf_format

from ._bandit import BanditConverter
from ._bandit import validate_flag as bandit_validate_flag
from ._flake8 import Flake8Converter
from ._flake8 import validate_flag as flake8_validate_flag
from ._mypy import MypyConverter
from ._mypy import validate_flag as mypy_validate_flag
from ._pylint import PyLintConverter
from ._pylint import validate_flag as pylint_validate_flag
from ._pyright import PyrightConverter
from ._pyright import validate_flag as pyright_validate_flag
from ._ruff import RuffConverter
from ._ruff import validate_flag as ruff_validate_flag

GITHUB_API_URL = "https://api.github.com"

REAL_PYTHON_ROOT_API = "https://realpython.com/search/api/v1/"
REAL_PYTHON_ARTICLE_URL = "https://realpython.com{article_url}"
REAL_PYTHON_SEARCH_URL = "https://realpython.com/search?q={user_search}"

STACKOVERFLOW_BASE_API = "https://api.stackexchange.com/2.2/search/advanced"
STACKOVERFLOW_PARAMS = {"order": "desc", "sort": "activity", "site": "stackoverflow"}
STACKOVERFLOW_SEARCH_URL = "https://stackoverflow.com/search?q={query}"

CHEAT_SH_PYTHON_URL = "https://cheat.sh/python/{search}"
ANSI_RE = re.compile(r"\x1b\[.*?m")

CURL_HEADERS = {"User-Agent": "curl/7.68.0"}


WTF_PYTHON_RAW_URL = "http://raw.githubusercontent.com/satwikkansal/wtfpython/master/"
WTF_PYTHON_BASE_URL = "https://github.com/satwikkansal/wtfpython"

MINIMUM_CERTAINTY = 55


async def lint(cmd: str, filename: str) -> dict[str, str]:
    proc = await asyncio.create_subprocess_shell(f"{cmd} {filename}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    # some formatting
    cmd = re.sub(" +", " ", cmd)  # remove extra spaces

    arguments = cmd.split(" ")

    command = arguments[0]
    command = f"{Fore.GREEN}{command}"

    rest = []
    for argument in arguments[1:]:
        if argument.startswith("-") or argument.startswith("--"):
            arg = f"{Fore.BLUE}{argument}"
        else:
            arg = f"{Fore.YELLOW}{argument}"
        rest.append(arg)

    filename = f"{Fore.CYAN}{filename}"

    complete_cmd_str = f"$ {command} {' '.join(rest)} {filename}"
    payload = {"main": f"{complete_cmd_str}\n\n{Fore.CYAN}Return Code: {Fore.RED}{proc.returncode}"}
    if stdout:
        payload["stdout"] = stdout.decode()
    if stderr:
        payload["stderr"] = stderr.decode()

    threading.Thread(target=partial(os.remove, filename)).start()

    return payload


FlagT = TypeVar("FlagT", Flake8Converter, MypyConverter, PyLintConverter, BanditConverter, PyrightConverter, RuffConverter, str)


async def code_to_file(code: str) -> str:
    def create_file() -> str:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
        ) as file:
            file.write(code)
            return file.name

    return await asyncio.to_thread(create_file)


class LintCode:
    source: str
    language: str | None

    def __init__(self, flag: FlagT) -> None:
        self.codeblock: str = flag if isinstance(flag, str) else flag.code
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

    def set_linttype(self, lint_type: str) -> LintCode:
        self.lint_type = lint_type
        return self

    def _lint_command(self) -> str:
        converters = {
            "flake8": (Flake8Converter, flake8_validate_flag),
            "bandit": (BanditConverter, bandit_validate_flag),
            "pylint": (PyLintConverter, pylint_validate_flag),
            "mypy": (MypyConverter, mypy_validate_flag),
            "pyright": (PyrightConverter, pyright_validate_flag),
            "ruff": (RuffConverter, ruff_validate_flag),
        }
        converter_type, validator = converters.get(self.lint_type, (None, None))
        if converter_type is not None and isinstance(self.flag, converter_type):
            return validator(self.flag)
        return ""

    async def _send_lint_output(self, ctx: commands.Context, data: dict[str, str]) -> None:
        if "main" in data:
            await ctx.reply(f"```ansi\n{data['main']}```")
        for key, color in (("stdout", Fore.WHITE), ("stderr", Fore.RED)):
            if key not in data:
                continue
            pages = commands.Paginator(prefix="```ansi\n", suffix="```", max_size=1980)
            for line in data[key].splitlines():
                pages.add_line(f"{color}{line}")
            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

    async def lint(self, ctx: commands.Context) -> None:
        if self.lint_type not in {"flake8", "bandit", "pylint", "mypy"}:
            await ctx.reply("Invalid lint type.")
            return

        if self.language not in {"python", "py", None}:
            await ctx.reply("Invalid language.")
            return

        filename = await code_to_file(self.source)

        cmd_str = self._lint_command()
        data = await lint(cmd_str, filename) if cmd_str else {}

        if not data:
            await ctx.reply("No output.")
            return

        await self._send_lint_output(ctx, data)

    async def lint_with_pyright(self, ctx: commands.Context) -> None:
        filename = await code_to_file(self.source)
        data = await lint("pyright --outputjson", filename)

        await ctx.reply(f"```ansi\n{data['main']}```")

        if data.get("stdout"):
            json_data = json.loads(data["stdout"])
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            pages.add_line(f"{Fore.WHITE}Pyright Version - {Fore.WHITE}{pyright.__version__}\n")

            pages.add_line(
                f"{Fore.RED}{json_data['summary']['errorCount']} errors - {Fore.YELLOW}{json_data['summary']['warningCount']} warnings - {Fore.BLUE}{json_data['summary']['informationCount']} information",
            )
            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)
            await interface.add_line(f"\n{Fore.MAGENTA}Diagnosed completed in {json_data['summary']['timeInSec']} seconds\n")

            if json_data["generalDiagnostics"]:
                await interface.add_line(f"{Fore.WHITE}General Diagnostics:\n")
                for error in json_data["generalDiagnostics"]:
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

                    await interface.add_line(f"{file}:{line} - {severity} - {message} {rule}")

        if data.get("stderr"):
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            for line in data["stderr"].splitlines():
                pages.add_line(f"{Fore.RED}{line}\n")

            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

    async def lint_with_flake8(self, ctx: commands.Context) -> None:
        filename = await code_to_file(self.source)
        data = await lint("flake8 --format=json", filename)

        await ctx.reply(f"```ansi\n{data['main']}```")

        if data.get("stdout"):
            json_data: dict = json.loads(data["stdout"])
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            pages.add_line(f"{Fore.WHITE}Flake8 Version - {Fore.WHITE}{flake8.__version__}\n")
            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

            for result in json_data.values():
                for error in result:
                    line = f"{Fore.GREEN}{error['line_number']}"
                    column = f"{Fore.GREEN}{error['column_number']}"
                    code = f"{Fore.RED}{error['code']}"
                    message = f"{Fore.BLUE}{error['text']}"
                    physical_line = f"{Fore.CYAN}{error['physical_line']}"
                    await interface.add_line(f"{Fore.WHITE}{filename}:{line:>2}:{column:<2} - {code} - {message}\n>>> {physical_line}")

        if data.get("stderr"):
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            for line in data["stderr"].splitlines():
                pages.add_line(f"{Fore.RED}{line}\n")

            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

    async def lint_with_ruff(self, ctx: commands.Context) -> None:
        filename = await code_to_file(self.source)
        data = await lint("ruff --format=json", filename)

        await ctx.reply(f"```ansi\n{data['main']}```")

        if data.get("stdout"):
            json_data = json.loads(data["stdout"])

            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)

            # Thanks `AAA3A#1157` (829612600059887649)
            try:
                ruff_version = pkg_resources.version("ruff")
            except pkg_resources.PackageNotFoundError:
                ruff_version = "Unknown"

            pages.add_line(f"{Fore.WHITE}Ruff Version - {Fore.WHITE}{ruff_version}\n")  # TODO: Get version from ruff

            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

            for result in json_data:
                code = f"{Fore.RED}{result['code']}"
                message = f"{Fore.BLUE}{result['message']}"
                location_row = f"{Fore.YELLOW}{result['location']['row']}"
                location_col = f"{Fore.YELLOW}{result['location']['column']}"

                end_location_row = f"{Fore.YELLOW}{result['end_location']['row']}"
                end_location_col = f"{Fore.YELLOW}{result['end_location']['column']}"

                await interface.add_line(
                    f"{Fore.WHITE}{filename}:{location_row}:{location_col}{Fore.WHITE}-{end_location_row}:{end_location_col} {Fore.WHITE}- {code} {Fore.WHITE}- {message}",
                )
                if result["fix"]:
                    applicability = f"{Fore.CYAN}{result['fix']['applicability']}"
                    fix_message = f"{Fore.GREEN}{result['fix']['message']}"
                    await interface.add_line(f"{Fore.WHITE}Fix: {fix_message} {Fore.WHITE}({applicability}{Fore.WHITE})\n")
                else:
                    await interface.add_line(f"{Fore.WHITE}Fix: {Fore.RED}No Fix available at this moment\n")
                await interface.add_line(f"{Fore.WHITE}{'-' * 50}\n")

        if data.get("stderr"):
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            for line in data["stderr"].splitlines():
                pages.add_line(f"{Fore.RED}{line}\n")

            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

    async def lint_with_pylint(self, ctx: commands.Context) -> None:
        filename = await code_to_file(self.source)
        data = await lint("pylint -f json", filename)

        await ctx.reply(f"```ansi\n{data['main']}```")

        if data.get("stdout"):
            json_data = json.loads(data["stdout"])

            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)

            pages.add_line(f"{Fore.WHITE}Pylint Version - {Fore.WHITE}{pylint.__version__}\n")

            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

            for result in json_data:
                line = f"{Fore.GREEN}{result['line']}"
                column = f"{Fore.GREEN}{result['column']}"
                message = f"{Fore.BLUE}{result['message']}"
                message_id = f"{Fore.RED}{result['message-id']}"
                symbol = f"{Fore.WHITE}({Fore.CYAN}{result['symbol']}{Fore.WHITE})"
                await interface.add_line(f"{Fore.WHITE}{filename}:{line:>2}:{column:<2} - {message_id} - {message:<13} {symbol}")

    async def lint_with_bandit(self, ctx: commands.Context) -> None:
        filename = await code_to_file(self.source)
        data = await lint("bandit -f json", filename)

        await ctx.reply(f"```ansi\n{data['main']}```")

        if data.get("stdout"):
            json_data = json.loads(data["stdout"])
            pages = commands.Paginator(prefix="```ansi", suffix="```", max_size=1980)
            pages.add_line(f"{Fore.MAGENTA}Bandit Version - {Fore.MAGENTA}{bandit.__version__}\n")

            interface = PaginatorInterface(ctx.bot, pages, owner=ctx.author)
            await interface.send_to(ctx)

            # Generated at: Ex format: 2023-06-11T17:51:53Z
            to_fmt = "%d/%m/%Y %H:%M:%S"
            try:
                generated_at = arrow.get(json_data["generated_at"]).to("local").format(to_fmt)
            except arrow.ParserError:
                generated_at = "Unknown"

            await interface.add_line(f"{Fore.MAGENTA}Generated at: {Fore.MAGENTA}{generated_at}\n")

            confidence_high = json_data["metrics"]["_totals"]["CONFIDENCE.HIGH"]
            confidence_low = json_data["metrics"]["_totals"]["CONFIDENCE.LOW"]
            confidence_medium = json_data["metrics"]["_totals"]["CONFIDENCE.MEDIUM"]
            confidence_undefined = json_data["metrics"]["_totals"]["CONFIDENCE.UNDEFINED"]

            await interface.add_line(
                f"{Fore.WHITE}Confidence: {Fore.RED}{confidence_high} High {Fore.WHITE}- {Fore.YELLOW}{confidence_medium} Medium {Fore.WHITE}- {Fore.GREEN}{confidence_low} Low {Fore.WHITE}- {Fore.CYAN}{confidence_undefined} Undefined",
            )

            severity_high = json_data["metrics"]["_totals"]["SEVERITY.HIGH"]
            severity_low = json_data["metrics"]["_totals"]["SEVERITY.LOW"]
            severity_medium = json_data["metrics"]["_totals"]["SEVERITY.MEDIUM"]
            severity_undefined = json_data["metrics"]["_totals"]["SEVERITY.UNDEFINED"]

            await interface.add_line(
                f"{Fore.WHITE}Severity  : {Fore.RED}{severity_high} High {Fore.WHITE}- {Fore.YELLOW}{severity_medium} Medium {Fore.WHITE}- {Fore.GREEN}{severity_low} Low {Fore.WHITE}- {Fore.CYAN}{severity_undefined} Undefined",
            )

            loc = json_data["metrics"]["_totals"]["loc"]
            nosec = json_data["metrics"]["_totals"]["nosec"]
            skipped_tests = json_data["metrics"]["_totals"]["skipped_tests"]

            await interface.add_line(
                f"\n{Fore.WHITE}Lines of Code {Fore.WHITE}{loc} - {Fore.RED}Lines of Code (#NoSec) {nosec} {Fore.WHITE}- {Fore.YELLOW}Skipped Tests {skipped_tests}\n",
            )

            for result in json_data["results"]:
                code = f"{Fore.CYAN}{result['code']}"
                col_offset = f"{Fore.GREEN}{result['col_offset']}"
                # end_col_offset = f"{Fore.GREEN}{result['end_col_offset']}"
                issue_confidence = f"{Fore.WHITE}{result['issue_confidence']}"
                issue_severity = f"{Fore.WHITE}{result['issue_severity']}"
                issue_text = f"{Fore.BLUE}{result['issue_text']}"
                line_number = f"{Fore.GREEN}{result['line_number']}"
                # line_range = f"{Fore.WHITE}{result['line_range']}"
                more_info = f"{Fore.WHITE}{result['more_info']}"
                test_id = f"{Fore.RED}{result['test_id']}"
                test_name = f"{Fore.WHITE}{result['test_name']}"
                if result.get("issue_cwe"):
                    issue_cwe_id = f"{Fore.WHITE}{result['issue_cwe']['id']}"
                    issue_cwe_link = f"{Fore.WHITE}{result['issue_cwe']['link']}"
                else:
                    issue_cwe_id = f"{Fore.WHITE}None"
                    issue_cwe_link = f"{Fore.WHITE}None"

                await interface.add_line(
                    f"{Fore.YELLOW}>> Issue [{test_id:>4}:{test_name:<9}] {issue_text}\n"
                    f"{Fore.WHITE}   Severity : {issue_severity:<6}  Confidence: {issue_confidence:<6}\n"
                    f"{Fore.WHITE}   CWE ID   : {issue_cwe_id:<6}  CWE Link: {issue_cwe_link}\n"
                    f"{Fore.WHITE}   More Info: {more_info}\n"
                    f"{Fore.WHITE}   Location : {filename}{line_number:>2}:{col_offset:<2}\n"
                    f"{Fore.WHITE}   Code     :\n{code}\n"
                    f"{Fore.WHITE}{'-' * 50}\n",
                )

    async def run_black(self, ctx: commands.Context) -> None:
        ini = time.perf_counter()
        res = await asyncio.to_thread(format_str, self.source, mode=FileMode())
        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(f"```ansi\n{Fore.RED}[No Changes in the code, already formatted]```")
            return
        if len(res) > 2000:
            await ctx.reply(f"```ansi\n{Fore.RED}[The formated code is too long, to display]```")
            await ctx.reply(file=discord.File(fp=io.BytesIO(res.encode("utf-8")), filename="formated.py"))
            return

        await ctx.reply(f"```ansi\n{Fore.GREEN}[Formated Code in {int(end - ini)} seconds]``````py\n{res}```")

    async def run_isort(self, ctx: commands.Context) -> None:
        ini = time.perf_counter()
        res: str = await asyncio.to_thread(isort.code, self.source)
        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(f"```ansi\n{Fore.RED}[No Changes]```")
            return

        if len(res) > 2000:
            await ctx.reply(f"```ansi\n{Fore.RED}[The formated code is too long, to display]```")
            await ctx.reply(file=discord.File(fp=io.BytesIO(res.encode("utf-8")), filename="formated.py"))
            return

        await ctx.reply(f"```ansi\n{Fore.GREEN}[Formated Code in {int(end - ini)} seconds]``````py\n{res}```")

    async def run_autopep8(self, ctx: commands.Context) -> None:
        ini = time.perf_counter()
        res = await asyncio.to_thread(autopep8.fix_code, self.source)
        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(f"```ansi\n{Fore.RED}[No Changes]```")
            return
        if len(res) > 2000:
            await ctx.reply(f"```ansi\n{Fore.RED}[The formated code is too long, to display]```")
            await ctx.reply(file=discord.File(fp=io.BytesIO(res.encode("utf-8")), filename="formated.py"))
            return

        await ctx.reply(f"```ansi\n{Fore.GREEN}[Formated Code in {int(end - ini)} seconds]``````py\n{res}```")

    async def run_yapf(self, ctx: commands.Context) -> None:
        ini = time.perf_counter()
        res = await asyncio.to_thread(yapf_format, self.source)
        if isinstance(res, tuple):
            res = res[0]

        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(f"```ansi\n{Fore.RED}[No Changes]```")
            return
        if len(res) > 2000:
            await ctx.reply(f"```ansi\n{Fore.RED}[The formated code is too long, to display]```")
            await ctx.reply(file=discord.File(fp=io.BytesIO(res.encode("utf-8")), filename="formated.py"))
            return

        await ctx.reply(f"```ansi\n{Fore.GREEN}[Formated Code in {int(end - ini)} seconds]``````py\n{res}```")

    async def run_isort_with_black(self, ctx: commands.Context) -> None:

        ini = time.perf_counter()
        res = await asyncio.to_thread(isort.code, self.source)
        res = await asyncio.to_thread(format_str, res, mode=FileMode())
        end = time.perf_counter()

        if res == self.source:
            await ctx.reply(f"```ansi\n{Fore.RED}[No Changes]```")
            return

        if len(res) > 2000:
            await ctx.reply(f"```ansi\n{Fore.RED}[The formated code is too long, to display]```")
            await ctx.reply(file=discord.File(fp=io.BytesIO(res.encode("utf-8")), filename="formated.py"))
            return

        await ctx.reply(f"```ansi\n{Fore.GREEN}[Formated Code in {int(end - ini)} seconds]``````py\n{res}```")
