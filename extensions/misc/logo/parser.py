from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .utils import LogoRuntimeError, LogoSyntaxError, get_max_list_length, get_max_nesting_depth, get_max_source_length, get_max_word_length

MAX_FORMAT_NUMBER_ABS_VALUE_THRESHOLD = 1000000000000000.0


@dataclass(frozen=True)
class WordToken:
    """A quoted Logo word literal, e.g. "RED, "x, "#FF0000."""

    value: str
    line: int = 1
    column: int = 1


@dataclass(frozen=True)
class VarToken:
    """A variable reference token, e.g. :X, :SIZE."""

    name: str
    line: int = 1
    column: int = 1


@dataclass(frozen=True)
class NumberToken:
    """A numeric literal token, e.g. 100, 3.14, .5."""

    value: float
    raw: str = ""
    line: int = 1
    column: int = 1


@dataclass(frozen=True)
class SymbolToken:
    """An unquoted identifier, operator, or parenthesis token."""

    name: str
    raw: str = ""
    line: int = 1
    column: int = 1
    space_before: bool = True
    space_after: bool = True


class LogoList:  # noqa: PLW1641
    """A bracketed Logo list `[ ... ]` that acts both as a sequence of data values
    (numbers, strings, sublists) and as an executable token stream for control
    primitives (`REPEAT`, `IF`, `IFELSE`, `WHILE`, `UNTIL`, `FOR`, `FOREACH`, `RUN`).
    """

    __slots__ = ("_tokens", "_values", "column", "depth", "line")

    def __init__(
        self,
        tokens: tuple[Token, ...],
        *,
        values: tuple[Any, ...] | None = None,
        line: int = 1,
        column: int = 1,
        depth: int = 1,
    ) -> None:
        max_len = get_max_list_length()
        max_depth = get_max_nesting_depth()
        if depth > max_depth:
            msg = f"Maximum list nesting depth ({max_depth}) exceeded."
            raise LogoSyntaxError(msg)
        if len(tokens) > max_len:
            msg = f"Maximum list length ({max_len}) exceeded."
            raise LogoRuntimeError(msg)
        self._tokens = tokens
        self._values = values
        self.line = line
        self.column = column
        self.depth = depth

    @property
    def tokens(self) -> tuple[Token, ...]:
        return self._tokens

    @property
    def values(self) -> tuple[Any, ...]:
        if self._values is None:
            self._values = self._compute_values(self._tokens)
        return self._values

    @staticmethod
    def _compute_values(tokens: tuple[Token, ...]) -> tuple[Any, ...]:
        out: list[Any] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            # Fold unary minus attached to a number inside data lists, e.g. [100 -50]
            if (
                isinstance(tok, SymbolToken)
                and tok.name == "-"
                and tok.space_before
                and not tok.space_after
                and i + 1 < n
                and isinstance(tokens[i + 1], NumberToken)
            ):
                nxt = tokens[i + 1]
                assert isinstance(nxt, NumberToken)
                out.append(-nxt.value)
                i += 2
                continue
            if isinstance(tok, (NumberToken, WordToken)):
                out.append(tok.value)
            elif isinstance(tok, VarToken):
                out.append(f":{tok.name}")
            elif isinstance(tok, SymbolToken):
                out.append(tok.raw or tok.name)
            elif isinstance(tok, LogoList):
                out.append(tok)
            i += 1
        max_len = get_max_list_length()
        if len(out) > max_len:
            msg = f"Maximum list length ({max_len}) exceeded."
            raise LogoRuntimeError(msg)
        return tuple(out)

    @classmethod
    def from_values(cls, items: list[Any] | tuple[Any, ...]) -> LogoList:  # noqa: PLR0912
        max_len = get_max_list_length()
        max_depth = get_max_nesting_depth()
        if len(items) > max_len:
            msg = f"Maximum list length ({max_len}) exceeded."
            raise LogoRuntimeError(msg)

        tokens: list[Token] = []
        computed_values: list[Any] = []
        max_child_depth = 0

        for item in items:
            if isinstance(item, LogoList):
                if item.depth + 1 > max_depth:
                    msg = f"Maximum list nesting depth ({max_depth}) exceeded."
                    raise LogoRuntimeError(msg)
                max_child_depth = max(max_child_depth, item.depth)
                tokens.append(item)
                computed_values.append(item)
            elif isinstance(item, (int, float)) and not isinstance(item, bool):
                fval = float(item)
                if not math.isfinite(fval):
                    msg = "Numeric value in list must be finite."
                    raise LogoRuntimeError(msg)
                tokens.append(NumberToken(fval, _format_number(fval)))
                computed_values.append(fval)
            elif isinstance(item, str):
                max_word = get_max_word_length()
                if len(item) > max_word:
                    msg = f"Maximum word length ({max_word}) exceeded."
                    raise LogoRuntimeError(msg)
                computed_values.append(item)
                tokens.extend(_value_str_to_tokens(item))
            elif isinstance(item, (WordToken, VarToken, NumberToken, SymbolToken)):
                tokens.append(item)
                if isinstance(item, (NumberToken, WordToken)):
                    computed_values.append(item.value)
                elif isinstance(item, VarToken):
                    computed_values.append(f":{item.name}")
                else:
                    computed_values.append(item.raw or item.name)
            else:
                sval = str(item)
                computed_values.append(sval)
                tokens.extend(_value_str_to_tokens(sval))

        return cls(
            tuple(tokens),
            values=tuple(computed_values),
            depth=max_child_depth + 1,
        )

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.values)

    def __getitem__(self, index: int | slice) -> Any:
        return self.values[index]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LogoList):
            return self.values == other.values
        if isinstance(other, (tuple, list)):
            return self.values == tuple(other)
        return False

    def __repr__(self) -> str:
        return f"[{self.to_logo_string()}]"

    def to_logo_string(self) -> str:
        parts: list[str] = []
        for v in self.values:
            if isinstance(v, LogoList):
                parts.append(f"[{v.to_logo_string()}]")
            elif isinstance(v, float):
                parts.append(_format_number(v))
            else:
                parts.append(str(v))
        return " ".join(parts)


type Token = WordToken | VarToken | NumberToken | SymbolToken | LogoList


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    if value == 0.0:
        return "0"
    if value.is_integer() and abs(value) < MAX_FORMAT_NUMBER_ABS_VALUE_THRESHOLD:
        return str(int(value))
    return f"{value:.10g}"


def _value_str_to_tokens(text: str) -> list[Token]:
    s = text.strip()
    if not s:
        return [WordToken("")]
    if s.startswith('"'):
        return [WordToken(s[1:])]
    if s.startswith(":") and len(s) > 1:
        return [VarToken(s[1:].upper())]
    try:
        num = float(s)
        if math.isfinite(num):
            return [NumberToken(num, s)]
    except ValueError:
        pass
    return [SymbolToken(s.upper(), raw=s)]


_NUMBER_RE = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_TWO_CHAR_OPS = {"<=", ">=", "<>", "!="}
_SINGLE_CHAR_OPS = {"+", "-", "*", "/", "%", "^", "=", "<", ">", "(", ")"}
_DELIMITERS = set(" \t\r\n[];()+*/%^=<>")


class _LogoTokenizer:
    def __init__(self, source: str, max_depth: int, max_list: int, max_word: int) -> None:
        self.source = source
        self.max_depth = max_depth
        self.max_list = max_list
        self.max_word = max_word
        self.stack: list[tuple[list[Token], int, int]] = [([], 1, 1)]
        self.index = 0
        self.line = 1
        self.line_start = 0

    def _append(self, token: Token) -> None:
        current = self.stack[-1][0]
        if len(current) >= self.max_list:
            msg = f"Maximum list or program token count ({self.max_list}) exceeded."
            raise LogoSyntaxError(msg)
        current.append(token)

    def _skip_ignored(self) -> bool:
        char = self.source[self.index]
        if char == "\n":
            self.line += 1
            self.index += 1
            self.line_start = self.index
            return True
        if char in " \t\r":
            self.index += 1
            return True
        if char == ";":
            while self.index < len(self.source) and self.source[self.index] != "\n":
                self.index += 1
            return True
        return False

    def _read_list_open(self, column: int) -> None:
        if len(self.stack) > self.max_depth:
            msg = f"Maximum bracket nesting depth ({self.max_depth}) exceeded at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        self.stack.append(([], self.line, column))
        self.index += 1

    def _read_list_close(self, column: int) -> None:
        if len(self.stack) <= 1:
            msg = f"Unexpected ']' at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        items, open_line, open_column = self.stack.pop()
        child_depth = max((item.depth for item in items if isinstance(item, LogoList)), default=0)
        logo_list = LogoList(tuple(items), line=open_line, column=open_column, depth=child_depth + 1 if child_depth else 1)
        if len(self.stack) - 1 + logo_list.depth > self.max_depth:
            msg = f"Maximum bracket nesting depth ({self.max_depth}) exceeded."
            raise LogoSyntaxError(msg)
        self._append(logo_list)
        self.index += 1

    def _read_quoted_word(self, column: int) -> None:
        self.index += 1
        start = self.index
        while self.index < len(self.source) and self.source[self.index] not in " \t\r\n[];()":
            self.index += 1
        word = self.source[start : self.index]
        if len(word) > self.max_word:
            msg = f"Word length ({len(word)}) exceeds maximum of {self.max_word} characters at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        self._append(WordToken(word, line=self.line, column=column))

    def _read_variable(self, column: int) -> None:
        self.index += 1
        start = self.index
        while self.index < len(self.source) and (self.source[self.index].isalnum() or self.source[self.index] in "_?"):
            self.index += 1
        name = self.source[start : self.index]
        if not name:
            msg = f"Expected variable name after ':' at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        if len(name) > self.max_word:
            msg = f"Variable name exceeds maximum length ({self.max_word}) at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        self._append(VarToken(name.upper(), line=self.line, column=column))

    def _append_symbol(self, text: str, raw: str, column: int, space_before: bool) -> None:
        space_after = self.index >= len(self.source) or self.source[self.index] in " \t\r\n])"
        self._append(
            SymbolToken(
                text,
                raw=raw,
                line=self.line,
                column=column,
                space_before=space_before,
                space_after=space_after,
            )
        )

    def _read_operator(self, char: str, column: int, space_before: bool) -> bool:
        pair = self.source[self.index : self.index + 2]
        if self.index + 1 < len(self.source) and pair in _TWO_CHAR_OPS:
            self.index += 2
            self._append_symbol(pair, pair, column, space_before)
            return True
        if char not in _SINGLE_CHAR_OPS:
            return False
        self.index += 1
        self._append_symbol(char, char, column, space_before)
        return True

    def _read_number(self, char: str, column: int) -> bool:
        is_numeric_start = char.isdigit() or (char == "." and self.index + 1 < len(self.source) and self.source[self.index + 1].isdigit())
        if not is_numeric_start:
            return False
        match = _NUMBER_RE.match(self.source, self.index)
        if match is None:
            return False
        raw = match.group(0)
        self.index = match.end()
        try:
            value = float(raw)
        except ValueError as exc:
            msg = f"Invalid number {raw!r} at line {self.line}, column {column}."
            raise LogoSyntaxError(msg) from exc
        if not math.isfinite(value):
            msg = f"Numeric literal {raw!r} is not finite at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        self._append(NumberToken(value, raw=raw, line=self.line, column=column))
        return True

    def _read_symbol(self, char: str, column: int, space_before: bool) -> None:
        start = self.index
        while self.index < len(self.source) and self.source[self.index] not in _DELIMITERS and self.source[self.index] != "-":
            self.index += 1
        raw = self.source[start : self.index]
        if not raw:
            msg = f"Unexpected character {char!r} at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        if len(raw) > self.max_word:
            msg = f"Identifier length ({len(raw)}) exceeds maximum of {self.max_word} at line {self.line}, column {column}."
            raise LogoSyntaxError(msg)
        self._append_symbol(raw.upper(), raw, column, space_before)

    def _read_token(self) -> None:
        if self._skip_ignored():
            return
        char = self.source[self.index]
        column = self.index - self.line_start + 1
        space_before = self.index == 0 or self.source[self.index - 1] in " \t\r\n[("
        if char == "[":
            self._read_list_open(column)
        elif char == "]":
            self._read_list_close(column)
        elif char == '"':
            self._read_quoted_word(column)
        elif char == ":":
            self._read_variable(column)
        elif self._read_operator(char, column, space_before) or self._read_number(char, column):
            return
        else:
            self._read_symbol(char, column, space_before)

    def read(self) -> tuple[Token, ...]:
        while self.index < len(self.source):
            self._read_token()
        if len(self.stack) > 1:
            _, open_line, open_column = self.stack[-1]
            msg = f"Unclosed '[' starting at line {open_line}, column {open_column}."
            raise LogoSyntaxError(msg)
        return tuple(self.stack[0][0])


def tokenize_and_read(source: str) -> tuple[Token, ...]:
    """Tokenize MSWLogo source and read nested lists while enforcing parser limits."""
    max_source = get_max_source_length()
    if len(source) > max_source:
        msg = f"Program source length ({len(source)}) exceeds maximum of {max_source} characters."
        raise LogoSyntaxError(msg)
    tokenizer = _LogoTokenizer(source, get_max_nesting_depth(), get_max_list_length(), get_max_word_length())
    return tokenizer.read()


class LogoParser:
    """Lisp-style tokenizer and bracket reader for MSWLogo.
    Replaces the rigid Lark LALR grammar while preserving the `LogoParser().parse(source)` API.
    """

    def parse(self, source: str) -> tuple[Token, ...]:
        if not isinstance(source, str):
            msg = "Program source must be a string."
            raise LogoSyntaxError(msg)
        return tokenize_and_read(source)
