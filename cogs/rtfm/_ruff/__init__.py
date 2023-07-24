from __future__ import annotations

import re
from typing import Optional

from discord.ext import commands

POSSIBLE_RUFF_CODE = re.compile(r"([A-Z]\d{2,4})")


class RuffConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str
    ignore: Optional[str] = None
    select: Optional[str] = None
    line_length: Optional[int] = None
    max_doc_length: Optional[int] = None
    max_complexity: Optional[int] = None


def validate_Ruff_code(code: str) -> list[str]:
    return POSSIBLE_RUFF_CODE.findall(code)


def validate_flag(flag: RuffConverter) -> str:
    cmd = "ruff "

    if flag.ignore:
        _ig = flag.ignore.replace(",", " ")
        if codes := validate_Ruff_code(_ig):
            cmd += f"--ignore {','.join(codes)} "

    if flag.select:
        _sl = flag.select.replace(",", " ")
        if codes := validate_Ruff_code(_sl):
            cmd += f"--select {','.join(codes)} "

    if flag.line_length:
        cmd += f"--max-line-length {flag.max_complexity} "

    if flag.max_doc_length:
        cmd += f"--max-doc-length {flag.max_doc_length} "

    if flag.max_complexity:
        cmd += f"--max-complexity {flag.max_complexity} "

    return cmd
