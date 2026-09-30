from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lark import Lark, Transformer
from lark.exceptions import UnexpectedInput

GRAMMAR_PATH = Path(__file__).with_name("grammar.lark")


# AST nodes


@dataclass(frozen=True)
class Number:
    value: float


@dataclass(frozen=True)
class Variable:
    name: str


@dataclass(frozen=True)
class Binary:
    operator: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Unary:
    operator: str
    operand: Any


@dataclass(frozen=True)
class Command:
    name: str
    args: tuple[Any, ...] = ()


@dataclass(frozen=True)
class Repeat:
    count: Any
    body: tuple[Any, ...]


@dataclass(frozen=True)
class Make:
    name: str
    value: Any


@dataclass(frozen=True)
class Procedure:
    name: str
    parameters: tuple[str, ...]
    body: tuple[Any, ...]


@dataclass(frozen=True)
class ProcedureCall:
    name: str
    arguments: tuple[Any, ...]


# Transformer


class LogoTransformer(Transformer):
    def start(self, items):
        return tuple(items)

    def forward(self, items):
        return Command("FD", (items[0],))

    def backward(self, items):
        return Command("BK", (items[0],))

    def right(self, items):
        return Command("RT", (items[0],))

    def left(self, items):
        return Command("LT", (items[0],))

    def pen_up(self, _):
        return Command("PU")

    def pen_down(self, _):
        return Command("PD")

    def home(self, _):
        return Command("HOME")

    def clear_screen(self, _):
        return Command("CS")

    def set_pen_color(self, items):
        return Command("SETPC", (str(items[0]),))

    def set_pen_width(self, items):
        return Command("SETWIDTH", (items[0],))

    def set_xy(self, items):
        return Command("SETXY", (items[0], items[1]))

    def set_heading(self, items):
        return Command("SETH", (items[0],))

    def repeat(self, items):
        count = items[0]
        body = tuple(items[1:])
        return Repeat(count, body)

    def make(self, items):
        name = str(items[0]).lstrip(":").upper()
        return Make(name, items[1])

    def variable_name(self, items):
        return str(items[0])

    def parameter(self, items):
        return str(items[0]).lstrip(":").upper()

    def procedure(self, items):
        name = str(items[0]).upper()

        parameters = []
        body = []

        for item in items[1:]:
            if isinstance(item, str):
                parameters.append(item)
            else:
                body.append(item)

        return Procedure(name=name, parameters=tuple(parameters), body=tuple(body))

    def procedure_call(self, items):
        name = str(items[0]).upper()

        return ProcedureCall(name=name, arguments=tuple(items[1:]))

    # Expressions

    def number(self, items):
        return Number(float(items[0]))

    def variable(self, items):
        return Variable(str(items[0]).lstrip(":").upper())

    def add(self, items):
        return Binary("+", items[0], items[1])

    def sub(self, items):
        return Binary("-", items[0], items[1])

    def mul(self, items):
        return Binary("*", items[0], items[1])

    def div(self, items):
        return Binary("/", items[0], items[1])

    def neg(self, items):
        return Unary("-", items[0])

    def equal(self, items):
        return Binary("=", items[0], items[1])

    def less(self, items):
        return Binary("<", items[0], items[1])

    def greater(self, items):
        return Binary(">", items[0], items[1])


# Parser


class LogoParser:
    def __init__(self) -> None:
        grammar = GRAMMAR_PATH.read_text(encoding="utf-8")

        self.parser = Lark(grammar, parser="lalr", lexer="contextual", start="start")

    def parse(self, source: str) -> tuple[Any, ...]:
        try:
            tree = self.parser.parse(source)
            return LogoTransformer().transform(tree)

        except UnexpectedInput as exc:
            line = getattr(exc, "line", "?")
            column = getattr(exc, "column", "?")

            msg = f"Logo syntax error at line {line}, column {column}: {exc}"
            raise ValueError(msg) from exc
