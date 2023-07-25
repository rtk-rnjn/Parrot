from __future__ import annotations

import re
from typing import Annotated, Literal

from pyparsing import Optional

from discord.ext import commands
from utilities.converters import convert_bool

# https://pycodestyle.pycqa.org/en/latest/intro.html#error-codes
# https://flake8.pycqa.org/en/latest/user/error-codes.html

POSSIBLE_FLAKE8_CODE = re.compile(r"([A-Z]\d{2,4})")


class Flake8Converter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str
    ignore: str | None = None
    select: str | None = None
    max_line_length: int | None = None
    max_doc_length: int | None = None
    max_complexity: int | None = None
    statistics: Annotated[bool | None, convert_bool] = None
    doctests: Annotated[bool | None, convert_bool] = None
    color: Literal["auto", "always", "never"] | None = None
    verbose: Annotated[bool | None, convert_bool] = None
    count: Annotated[bool | None, convert_bool] = None


def validate_flake8_code(code: str) -> list[str]:
    return POSSIBLE_FLAKE8_CODE.findall(code)


def validate_flag(flag: Flake8Converter) -> str:
    cmd = "flake8 "
    if flag.count:
        cmd += "--count "

    if flag.verbose:
        cmd += "-v "

    if flag.color:
        cmd += f"--color={flag.color} "

    if flag.ignore:
        _ig = flag.ignore.replace(",", " ")
        if codes := validate_flake8_code(_ig):
            cmd += f"--ignore {','.join(codes)} "

    if flag.select:
        _sl = flag.select.replace(",", " ")
        if codes := validate_flake8_code(_sl):
            cmd += f"--select {','.join(codes)} "

    if flag.max_line_length:
        cmd += f"--max-line-length {flag.max_line_length} "

    if flag.max_doc_length:
        cmd += f"--max-doc-length {flag.max_doc_length} "

    if flag.max_complexity:
        cmd += f"--max-complexity {flag.max_complexity} "

    if flag.statistics:
        cmd += "--statistics "

    if flag.doctests:
        cmd += "--doctests "

    return cmd
