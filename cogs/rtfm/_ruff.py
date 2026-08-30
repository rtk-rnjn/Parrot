from __future__ import annotations

import re

from discord.ext import commands

POSSIBLE_RUFF_CODE = re.compile(r"([A-Z]\d{2,4})")


class RuffConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str = commands.flag(description="The code to lint with ruff.")
    ignore: str | None = commands.flag(description="Comma-separated list of error codes to ignore.", default=None)
    select: str | None = commands.flag(description="Comma-separated list of error codes to select.", default=None)
    line_length: int | None = commands.flag(description="Maximum allowed line length.", default=None)
    max_doc_length: int | None = commands.flag(description="Maximum allowed docstring length.", default=None)
    max_complexity: int | None = commands.flag(description="Maximum allowed complexity.", default=None)


def validate_Ruff_code(code: str) -> list[str]:
    return POSSIBLE_RUFF_CODE.findall(code)


def validate_flag(flag: RuffConverter) -> str:
    cmd = "ruff "

    if flag.ignore:
        _ig = flag.ignore.replace(",", " ")
        codes = validate_Ruff_code(_ig)
        if codes:
            cmd += f"--ignore {','.join(codes)} "

    if flag.select:
        _sl = flag.select.replace(",", " ")
        codes = validate_Ruff_code(_sl)
        if codes:
            cmd += f"--select {','.join(codes)} "

    if flag.line_length:
        cmd += f"--max-line-length {flag.max_complexity} "

    if flag.max_doc_length:
        cmd += f"--max-doc-length {flag.max_doc_length} "

    if flag.max_complexity:
        cmd += f"--max-complexity {flag.max_complexity} "

    return cmd
