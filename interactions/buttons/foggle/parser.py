# https://github.com/bijij/BotBot

from __future__ import annotations

import re
from collections.abc import Callable

OPS: dict[str, Callable[[int, int], int | None]] = {
    "^": lambda x, y: x**y,
    "+": lambda x, y: x + y,
    "-": lambda x, y: x - y,
    "*": lambda x, y: x * y,
    "/": lambda x, y: None if x % y else x // y,
}


class View:
    def __init__(self, string: str, base: int = 10) -> None:
        self.string = string
        self.strip_base_identifier()
        self.base = base
        self.idx = 0

    def peek(self) -> str:
        try:
            return self.string[self.idx]
        except IndexError:
            return ""

    def strip_base_identifier(self):
        self.string = re.sub(r"0[BXbx]", "", self.string)

    def strip_ws(self):
        while self.peek().isspace():
            self.idx += 1

    def parse_int(self) -> int | None:
        n = 0
        got_digit = False
        while re.match(r"[0-9]", self.peek()):  # only digits
            n = n * 10 + int(self.peek(), self.base)
            self.idx += 1
            got_digit = True
        self.strip_ws()
        return n if got_digit else None

    def parse_base_expr(self) -> int | None:
        if self.peek() != "(":
            return self.parse_int()
        self.idx += 1
        self.strip_ws()
        e = self.parse_expr()
        if e is None or self.peek() != ")":
            return None
        self.idx += 1
        self.strip_ws()
        return e

    def parse_prec_lvl(self, ops: tuple[str, ...], below: Callable[[], int | None]) -> Callable[[], int | None]:
        def parser():
            e = below()
            if e is None:
                return None
            while self.peek() in ops:
                op = OPS[self.peek()]
                self.idx += 1
                self.strip_ws()
                next = below()
                if next is None:
                    return None
                e = op(e, next)
                if e is None:
                    return None
            return e

        return parser

    def parse_expr(self) -> int | None:
        return self.parse_prec_lvl(("+", "-"), self.parse_prec_lvl(("*", "/"), self.parse_base_expr))()

    def parse_full(self) -> int | None:
        self.strip_ws()
        e = self.parse_expr()
        return None if self.idx < len(self.string) else e
