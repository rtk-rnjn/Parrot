from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import aiofiles

from discord.ext import commands

# https://pycodestyle.pycqa.org/en/latest/intro.html#error-codes
# https://flake8.pycqa.org/en/latest/user/error-codes.html

POSSIBLE_FLAKE8_CODE = re.compile(r"([A-Z]\d{2,3})")


class Flake8Converter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    ignore: Optional[str] = commands.flag(aliases=["i"])
    select: Optional[str] = commands.flag(aliases=["s"])
    max_line_length: Optional[int] = commands.flag(aliases=["l"])
    max_doc_length: Optional[int] = commands.flag(aliases=["d"])
    max_complexity: Optional[int] = commands.flag(aliases=["c"])
    statistics: Optional[bool] = commands.flag(aliases=["t"])
    doctests: Optional[bool] = commands.flag(aliases=["D"])


def validate_flake8_code(code: str) -> List[str]:
    return POSSIBLE_FLAKE8_CODE.findall(code)


def validate_flag(flag: Flake8Converter) -> str:
    cmd = "flake8 -v --color=never --count"
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
