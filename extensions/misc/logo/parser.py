from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .utils import LogoRuntimeError, LogoSyntaxError, get_max_list_length, get_max_nesting_depth, get_max_source_length, get_max_word_length


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
    """
    A bracketed Logo list `[ ... ]` that acts both as a sequence of data values
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
    if value.is_integer() and abs(value) < 1e15:
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


def tokenize_and_read(source: str) -> tuple[Token, ...]:  # noqa: PLR0912, PLR0915
    """
    Tokenizes MSWLogo source code and reads `[ ... ]` into nested `LogoList` objects.
    Enforces `MAX_SOURCE_LENGTH`, `MAX_NESTING_DEPTH`, `MAX_LIST_LENGTH`, and `MAX_WORD_LENGTH`.
    """
    max_source = get_max_source_length()
    if len(source) > max_source:
        msg = f"Program source length ({len(source)}) exceeds maximum of {max_source} characters."
        raise LogoSyntaxError(msg)

    max_depth = get_max_nesting_depth()
    max_list = get_max_list_length()
    max_word = get_max_word_length()

    stack: list[tuple[list[Token], int, int]] = [([], 1, 1)]
    n = len(source)
    i = 0
    line = 1
    line_start = 0

    def _append_token(tok: Token) -> None:
        curr_list = stack[-1][0]
        if len(curr_list) >= max_list:
            msg = f"Maximum list or program token count ({max_list}) exceeded."
            raise LogoSyntaxError(msg)
        curr_list.append(tok)

    while i < n:
        ch = source[i]

        # Newlines
        if ch == "\n":
            line += 1
            i += 1
            line_start = i
            continue

        # Whitespace
        if ch in " \t\r":
            i += 1
            continue

        # Comments (; to end of line)
        if ch == ";":
            while i < n and source[i] != "\n":
                i += 1
            continue

        col = i - line_start + 1
        space_before = i == 0 or source[i - 1] in " \t\r\n[("

        # List open bracket
        if ch == "[":
            if len(stack) > max_depth:
                msg = f"Maximum bracket nesting depth ({max_depth}) exceeded at line {line}, column {col}."
                raise LogoSyntaxError(msg)
            stack.append(([], line, col))
            i += 1
            continue

        # List close bracket
        if ch == "]":
            if len(stack) <= 1:
                msg = f"Unexpected ']' at line {line}, column {col}."
                raise LogoSyntaxError(msg)
            items, open_line, open_col = stack.pop()
            depth = len(stack)
            child_max = 0
            for item in items:
                if isinstance(item, LogoList):
                    child_max = max(child_max, item.depth)
            logo_list = LogoList(
                tuple(items),
                line=open_line,
                column=open_col,
                depth=child_max + 1 if child_max else 1,
            )
            if depth - 1 + logo_list.depth > max_depth:
                msg = f"Maximum bracket nesting depth ({max_depth}) exceeded."
                raise LogoSyntaxError(msg)
            _append_token(logo_list)
            i += 1
            continue

        # Quoted word literal: "word
        if ch == '"':
            i += 1
            start = i
            while i < n and source[i] not in " \t\r\n[];()":
                i += 1
            word_val = source[start:i]
            if len(word_val) > max_word:
                msg = f"Word length ({len(word_val)}) exceeds maximum of {max_word} characters at line {line}, column {col}."
                raise LogoSyntaxError(msg)
            _append_token(WordToken(word_val, line=line, column=col))
            continue

        # Variable reference: :var
        if ch == ":":
            i += 1
            start = i
            while i < n and (source[i].isalnum() or source[i] in "_?"):
                i += 1
            var_name = source[start:i]
            if not var_name:
                msg = f"Expected variable name after ':' at line {line}, column {col}."
                raise LogoSyntaxError(msg)
            if len(var_name) > max_word:
                msg = f"Variable name exceeds maximum length ({max_word}) at line {line}, column {col}."
                raise LogoSyntaxError(msg)
            _append_token(VarToken(var_name.upper(), line=line, column=col))
            continue

        # Two-character operators (<=, >=, <>, !=)
        if i + 1 < n and source[i : i + 2] in _TWO_CHAR_OPS:
            op = source[i : i + 2]
            i += 2
            space_after = i >= n or source[i] in " \t\r\n])"
            _append_token(
                SymbolToken(
                    op,
                    raw=op,
                    line=line,
                    column=col,
                    space_before=space_before,
                    space_after=space_after,
                )
            )
            continue

        # Numeric literal (digits or leading dot followed by digit)
        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            m = _NUMBER_RE.match(source, i)
            if m:
                raw_num = m.group(0)
                i = m.end()
                try:
                    val = float(raw_num)
                except ValueError as exc:
                    msg = f"Invalid number {raw_num!r} at line {line}, column {col}."
                    raise LogoSyntaxError(msg) from exc
                if not math.isfinite(val):
                    msg = f"Numeric literal {raw_num!r} is not finite at line {line}, column {col}."
                    raise LogoSyntaxError(msg)
                _append_token(NumberToken(val, raw=raw_num, line=line, column=col))
                continue

        # Single-character operators and parens
        if ch in _SINGLE_CHAR_OPS:
            # Special case: '-' followed by digits when preceded by '-' or operator?
            # We preserve '-' as a SymbolToken with accurate space_before / space_after metadata
            # so the arity-driven evaluator can resolve `foo 10 -5` vs `foo 10 - 5` vs `[100 -50]`.
            i += 1
            space_after = i >= n or source[i] in " \t\r\n])"
            _append_token(
                SymbolToken(
                    ch,
                    raw=ch,
                    line=line,
                    column=col,
                    space_before=space_before,
                    space_after=space_after,
                )
            )
            continue

        # Unquoted symbol / identifier / command name (may include ? or # for FOREACH/REPCOUNT)
        start = i
        while i < n and source[i] not in _DELIMITERS:
            # Allow '-' inside identifier only if not an arithmetic expression? No, in Logo a-b without spaces is subtraction.
            if source[i] == "-":
                break
            i += 1
        raw_sym = source[start:i]
        if not raw_sym:
            msg = f"Unexpected character {ch!r} at line {line}, column {col}."
            raise LogoSyntaxError(msg)
        if len(raw_sym) > max_word:
            msg = f"Identifier length ({len(raw_sym)}) exceeds maximum of {max_word} at line {line}, column {col}."
            raise LogoSyntaxError(msg)
        space_after = i >= n or source[i] in " \t\r\n])"
        _append_token(
            SymbolToken(
                raw_sym.upper(),
                raw=raw_sym,
                line=line,
                column=col,
                space_before=space_before,
                space_after=space_after,
            )
        )

    if len(stack) > 1:
        _, open_line, open_col = stack[-1]
        msg = f"Unclosed '[' starting at line {open_line}, column {open_col}."
        raise LogoSyntaxError(msg)

    return tuple(stack[0][0])


class LogoParser:
    """
    Lisp-style tokenizer and bracket reader for MSWLogo.
    Replaces the rigid Lark LALR grammar while preserving the `LogoParser().parse(source)` API.
    """

    def parse(self, source: str) -> tuple[Token, ...]:
        if not isinstance(source, str):
            msg = "Program source must be a string."
            raise LogoSyntaxError(msg)
        return tokenize_and_read(source)
