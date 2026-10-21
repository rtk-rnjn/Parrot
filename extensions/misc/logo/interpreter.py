from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .parser import LogoList, LogoParser, NumberToken, SymbolToken, Token, VarToken, WordToken, _format_number, tokenize_and_read
from .turtle import PolygonFillOp, Turtle, parse_color
from .utils import (
    LogoRuntimeError,
    LogoSyntaxError,
    get_max_call_depth,
    get_max_list_length,
    get_max_nesting_depth,
    get_max_operations,
    get_max_output_lines,
    get_max_procedures,
    get_max_repeat,
    get_max_variables,
    get_max_word_length,
)


@dataclass(frozen=True)
class Procedure:
    name: str
    parameters: tuple[str, ...]
    body: tuple[Token, ...]


class _StopSignal(Exception):
    """Internal control-flow signal raised by STOP."""


class _OutputSignal(Exception):
    """Internal control-flow signal raised by OUTPUT."""

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value


class _TailCallSignal(Exception):
    """Internal control-flow signal used for tail-call optimization (TCO)."""

    def __init__(self, procedure: Procedure, arguments: list[Any]) -> None:
        super().__init__()
        self.procedure = procedure
        self.arguments = arguments


class _TokenStream:
    __slots__ = ("length", "pos", "tokens")

    def __init__(self, tokens: tuple[Token, ...], pos: int = 0) -> None:
        self.tokens = tokens
        self.pos = pos
        self.length = len(tokens)

    def at_end(self) -> bool:
        return self.pos >= self.length

    def peek(self, offset: int = 0) -> Token | None:
        idx = self.pos + offset
        if 0 <= idx < self.length:
            return self.tokens[idx]
        return None

    def next(self) -> Token:
        if self.pos >= self.length:
            msg = "Unexpected end of input."
            raise LogoSyntaxError(msg)
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok


@dataclass
class Environment:
    values: dict[str, Any] = field(default_factory=dict)
    parent: Environment | None = None
    locals_declared: set[str] = field(default_factory=set)
    test_state: bool | None = None
    repcount: int | None = None
    foreach_item: Any = None
    has_foreach_item: bool = False

    def get(self, name: str) -> Any:
        key = name.upper()
        env: Environment | None = self
        while env is not None:
            if key in env.values:
                return env.values[key]
            env = env.parent
        msg = f"Unknown variable :{key}"
        raise LogoRuntimeError(msg)

    def has(self, name: str) -> bool:
        key = name.upper()
        env: Environment | None = self
        while env is not None:
            if key in env.values and env.values[key] is not None:
                return True
            env = env.parent
        return False

    def declare_local(self, name: str) -> None:
        key = name.upper()
        self.locals_declared.add(key)

    def set(self, name: str, value: Any, max_vars: int = 500) -> None:
        key = name.upper()
        env: Environment | None = self
        root = self
        while env is not None:
            if key in env.locals_declared or key in env.values:
                env.values[key] = value
                return
            root = env
            env = env.parent
        if key not in root.values and len(root.values) >= max_vars:
            msg = f"Maximum number of variables ({max_vars}) exceeded."
            raise LogoRuntimeError(msg)
        root.values[key] = value

    def get_repcount(self) -> int:
        env: Environment | None = self
        while env is not None:
            if env.repcount is not None:
                return env.repcount
            env = env.parent
        msg = "REPCOUNT can only be used inside a loop."
        raise LogoRuntimeError(msg)

    def get_foreach_item(self) -> Any:
        env: Environment | None = self
        while env is not None:
            if env.has_foreach_item:
                return env.foreach_item
            env = env.parent
        msg = "? can only be used inside FOREACH."
        raise LogoRuntimeError(msg)

    def get_test_state(self) -> bool:
        env: Environment | None = self
        while env is not None:
            if env.test_state is not None:
                return env.test_state
            env = env.parent
        msg = "IFTRUE/IFFALSE used before TEST."
        raise LogoRuntimeError(msg)


@dataclass(frozen=True)
class PrimitiveSpec:
    name: str
    default_arity: int
    min_arity: int
    max_arity: int  # -1 for unlimited variadic inside (...)
    handler: Callable[[list[Any], Environment, bool], Any]
    raw_first_var_fallback: bool = False
    lazy_lists: bool = False


_INFIX_PRECEDENCE: dict[str, int] = {
    "=": 10,
    "<>": 10,
    "!=": 10,
    "<": 10,
    ">": 10,
    "<=": 10,
    ">=": 10,
    "+": 20,
    "-": 20,
    "*": 30,
    "/": 30,
    "%": 30,
    "^": 40,
}


class LogoInterpreter:
    def __init__(
        self,
        turtle: Turtle | None = None,
        *,
        seed: int | None = None,
    ) -> None:
        self.turtle = turtle or Turtle()
        self.global_env = Environment({})
        self.procedures: dict[str, Procedure] = {}
        self.primitives: dict[str, PrimitiveSpec] = {}
        self.output: list[str] = []

        self.operations = 0
        self.call_depth = 0
        self._expr_depth = 0
        self._rng = random.Random(seed)

        self._max_operations = get_max_operations()
        self._max_repeat = get_max_repeat()
        self._max_call_depth = get_max_call_depth()
        self._max_nesting_depth = get_max_nesting_depth()
        self._max_list_length = get_max_list_length()
        self._max_word_length = get_max_word_length()
        self._max_variables = get_max_variables()
        self._max_procedures = get_max_procedures()
        self._max_output_lines = get_max_output_lines()

        self._register_all_primitives()

    # Budget and validation helpers
    def _tick(self, cost: int = 1) -> None:
        self.operations += cost
        if self.operations > self._max_operations:
            msg = "Program execution limit exceeded."
            raise LogoRuntimeError(msg)

    @staticmethod
    def _check_finite(value: float) -> float:
        if not math.isfinite(value):
            msg = "Arithmetic overflow or non-finite number."
            raise LogoRuntimeError(msg)
        return 0.0 if value == 0.0 else value

    def _to_number(self, value: Any, context: str = "expression") -> float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return self._check_finite(float(value))
        if isinstance(value, str):
            s = value.strip()
            s = s.removeprefix('"')
            try:
                return self._check_finite(float(s))
            except ValueError as exc:
                msg = f"Expected a number in {context}, got {value!r}."
                raise LogoRuntimeError(msg) from exc
        msg = f"Expected a number in {context}, got {self._format_value(value)}."
        raise LogoRuntimeError(msg)

    def _require_int(self, value: Any, context: str = "expression") -> int:
        num = self._to_number(value, context)
        if not num.is_integer():
            msg = f"Expected an integer in {context}, got {num!r}."
            raise LogoRuntimeError(msg)
        return int(num)

    def _to_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if not math.isfinite(value):
                msg = "Condition value must be finite."
                raise LogoRuntimeError(msg)
            return value != 0.0
        if isinstance(value, str):
            s = value.strip().lstrip('"').upper()
            if s in ("TRUE", "1"):
                return True
            if s in ("FALSE", "0"):
                return False
        msg = f"Expected truth value (TRUE/FALSE or 1/0), got {self._format_value(value)}."
        raise LogoRuntimeError(msg)

    def _to_word_str(self, value: Any) -> str:
        if isinstance(value, LogoList):
            msg = f"Expected a word, got list {value!r}."
            raise LogoRuntimeError(msg)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            s = _format_number(float(value))
        else:
            s = str(value)
            s = s.removeprefix('"')
        if len(s) > self._max_word_length:
            msg = f"Maximum word length ({self._max_word_length}) exceeded."
            raise LogoRuntimeError(msg)
        return s

    def _format_value(self, value: Any, show_brackets: bool = False) -> str:
        if isinstance(value, LogoList):
            inner = value.to_logo_string()
            return f"[{inner}]" if show_brackets else inner
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return _format_number(float(value))
        if isinstance(value, str):
            return value.removeprefix('"')
        return str(value)

    def _require_list(self, value: Any, context: str) -> LogoList:
        if isinstance(value, LogoList):
            return value
        msg = f"{context} expects a list [ ... ], got {self._format_value(value)}."
        raise LogoRuntimeError(msg)

    def _values_equal(self, a: Any, b: Any, depth: int = 0) -> bool:
        self._tick()
        if depth > self._max_nesting_depth:
            msg = "Maximum comparison nesting depth exceeded."
            raise LogoRuntimeError(msg)
        if isinstance(a, LogoList) and isinstance(b, LogoList):
            va, vb = a.values, b.values
            if len(va) != len(vb):
                return False
            return all(self._values_equal(x, y, depth + 1) for x, y in zip(va, vb, strict=False))
        if isinstance(a, LogoList) or isinstance(b, LogoList):
            return False
        # Numeric comparison if both can be parsed as finite numbers
        try:
            na = self._to_number(a)
            nb = self._to_number(b)
            return abs(na - nb) <= 1e-9
        except LogoRuntimeError:
            sa = self._to_word_str(a).upper()
            sb = self._to_word_str(b).upper()
            return sa == sb

    # Top-level entry points
    def run(self, source: str) -> Turtle:
        """Convenience method: parses and executes Logo source code and returns the Turtle."""
        tokens = LogoParser().parse(source)
        self.execute(tokens)
        return self.turtle

    def execute(self, program: tuple[Any, ...] | list[Any] | str) -> None:
        tokens = tokenize_and_read(program) if isinstance(program, str) else tuple(program)

        # Pre-extract top-level TO ... END definitions so forward calls work
        remaining_tokens = self._extract_procedures(tokens)
        stream = _TokenStream(remaining_tokens)
        try:
            self._execute_stream(stream, self.global_env, in_tail_pos=False)
        except _StopSignal:
            return
        except _OutputSignal as exc:
            msg = "OUTPUT can only be used inside a procedure."
            raise LogoRuntimeError(msg) from exc

    def _extract_procedures(self, tokens: tuple[Token, ...]) -> tuple[Token, ...]:
        out: list[Token] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if isinstance(tok, SymbolToken) and tok.name == "TO":
                i = self._parse_to_definition(tokens, i)
            elif isinstance(tok, SymbolToken) and tok.name == "END":
                msg = f"Unexpected END outside procedure definition at line {tok.line}, column {tok.column}."
                raise LogoSyntaxError(msg)
            else:
                out.append(tok)
                i += 1
        return tuple(out)

    def _parse_to_definition(self, tokens: tuple[Token, ...], start_idx: int) -> int:
        n = len(tokens)
        to_tok = tokens[start_idx]
        idx = start_idx + 1
        if idx >= n:
            msg = f"Expected procedure name after TO at line {to_tok.line}."
            raise LogoSyntaxError(msg)

        name_tok = tokens[idx]
        if not isinstance(name_tok, SymbolToken) or name_tok.name in _INFIX_PRECEDENCE or name_tok.name in ("(", ")", "TO", "END"):
            msg = f"Invalid procedure name at line {getattr(name_tok, 'line', to_tok.line)}."
            raise LogoSyntaxError(msg)

        proc_name = name_tok.name.upper()
        if proc_name in self.primitives:
            msg = f"Cannot redefine built-in primitive: {proc_name}"
            raise LogoRuntimeError(msg)
        if proc_name not in self.procedures and len(self.procedures) >= self._max_procedures:
            msg = f"Maximum number of procedures ({self._max_procedures}) exceeded."
            raise LogoRuntimeError(msg)

        idx += 1
        params: list[str] = []
        while idx < n and isinstance(tokens[idx], VarToken):
            vtok = tokens[idx]
            assert isinstance(vtok, VarToken)
            params.append(vtok.name.upper())
            idx += 1

        body: list[Token] = []
        found_end = False
        while idx < n:
            curr = tokens[idx]
            if isinstance(curr, SymbolToken) and curr.name == "END":
                found_end = True
                idx += 1
                break
            if isinstance(curr, SymbolToken) and curr.name == "TO":
                msg = f"Nested TO is not allowed inside procedure {proc_name} at line {curr.line}."
                raise LogoSyntaxError(msg)
            body.append(curr)
            idx += 1

        if not found_end:
            msg = f"Procedure {proc_name} starting at line {to_tok.line} is missing END."
            raise LogoSyntaxError(msg)

        self.procedures[proc_name] = Procedure(
            name=proc_name,
            parameters=tuple(params),
            body=tuple(body),
        )
        return idx

    # Statement stream execution
    def _execute_list(
        self,
        code_list: LogoList,
        env: Environment,
        *,
        in_tail_pos: bool = False,
        allow_value: bool = False,
    ) -> Any:
        self._tick()
        stream = _TokenStream(code_list.tokens)
        return self._execute_stream(
            stream,
            env,
            in_tail_pos=in_tail_pos,
            allow_value=allow_value,
        )

    def _execute_stream(
        self,
        stream: _TokenStream,
        env: Environment,
        *,
        in_tail_pos: bool = False,
        allow_value: bool = False,
    ) -> Any:
        last_val: Any = None
        while not stream.at_end():
            self._tick()
            tok = stream.peek()
            if isinstance(tok, SymbolToken) and tok.name == "TO":
                stream.pos = self._parse_to_definition(stream.tokens, stream.pos)
                continue
            if isinstance(tok, SymbolToken) and tok.name == "END":
                msg = f"Unexpected END at line {tok.line}, column {tok.column}."
                raise LogoSyntaxError(msg)

            val = self._execute_statement_or_expr(
                stream,
                env,
                in_tail_pos=in_tail_pos,
                allow_value=allow_value,
            )
            if val is not None:
                if not allow_value:
                    msg = f"You don't say what to do with {self._format_value(val, show_brackets=True)}."
                    raise LogoRuntimeError(msg)
                last_val = val
        return last_val

    def _execute_statement_or_expr(
        self,
        stream: _TokenStream,
        env: Environment,
        *,
        in_tail_pos: bool = False,
        allow_value: bool = False,
    ) -> Any:
        tok = stream.peek()
        if tok is None:
            return None

        # Parenthesized call or expression at statement level: e.g. (PRINT "A "B) or (SUM 1 2 3)
        if isinstance(tok, SymbolToken) and tok.name == "(":
            if allow_value:
                return self._eval_expr(stream, env)
            return self._eval_paren_or_expr(stream, env, statement_ok=True)

        # Standard command or procedure call
        if isinstance(tok, SymbolToken):
            name = tok.name.upper()
            if name in self.primitives or name in self.procedures:
                stream.next()
                res = self._invoke_named(
                    name,
                    tok,
                    stream,
                    env,
                    variadic_until_paren=False,
                    in_tail_pos=in_tail_pos,
                )
                # If the call returned a value and an infix operator follows (when allow_value=True)
                if res is not None and allow_value:
                    return self._eval_infix_continuation(res, stream, env, min_prec=0)
                return res

            if not allow_value:
                msg = f"Unknown command or procedure: {tok.raw or tok.name}"
                raise LogoRuntimeError(msg)

        if allow_value:
            return self._eval_expr(stream, env)

        msg = f"Unexpected token {self._token_desc(tok)} at start of statement."
        raise LogoRuntimeError(msg)

    @staticmethod
    def _token_desc(tok: Token) -> str:
        if isinstance(tok, NumberToken):
            return tok.raw or _format_number(tok.value)
        if isinstance(tok, WordToken):
            return f'"{tok.value}'
        if isinstance(tok, VarToken):
            return f":{tok.name}"
        if isinstance(tok, SymbolToken):
            return tok.raw or tok.name
        if isinstance(tok, LogoList):
            return repr(tok)
        return str(tok)

    # Expression evaluation (Pratt / precedence climbing + arity-driven calls)
    def _eval_expr(
        self,
        stream: _TokenStream,
        env: Environment,
        min_prec: int = 0,
        *,
        stop_on_attached_minus: bool = False,
    ) -> Any:
        self._tick()
        self._expr_depth += 1
        if self._expr_depth > self._max_nesting_depth:
            self._expr_depth -= 1
            msg = f"Maximum expression nesting depth ({self._max_nesting_depth}) exceeded."
            raise LogoRuntimeError(msg)
        try:
            left = self._eval_unary(
                stream,
                env,
                stop_on_attached_minus=stop_on_attached_minus,
            )
            return self._eval_infix_continuation(
                left,
                stream,
                env,
                min_prec=min_prec,
                stop_on_attached_minus=stop_on_attached_minus,
            )
        finally:
            self._expr_depth -= 1

    def _eval_infix_continuation(
        self,
        left: Any,
        stream: _TokenStream,
        env: Environment,
        min_prec: int = 0,
        *,
        stop_on_attached_minus: bool = False,
    ) -> Any:
        while not stream.at_end():
            tok = stream.peek()
            if not isinstance(tok, SymbolToken):
                break
            op = tok.name
            prec = _INFIX_PRECEDENCE.get(op)
            if prec is None or prec < min_prec:
                break

            # Arity-sensitive minus rule:
            # If '-' is preceded by whitespace and immediately followed by a token without whitespace
            # (e.g. `SETXY 100 -50` or `foo 10 -5` when more arguments are still expected),
            # do not consume '-' as binary subtraction; let it start the next argument as unary '-'.
            if op == "-" and stop_on_attached_minus and tok.space_before and not tok.space_after:
                break

            stream.next()
            self._tick()
            next_min_prec = prec if op == "^" else prec + 1
            right = self._eval_expr(
                stream,
                env,
                min_prec=next_min_prec,
                stop_on_attached_minus=stop_on_attached_minus,
            )
            left = self._apply_binary_op(op, left, right)
        return left

    def _eval_unary(
        self,
        stream: _TokenStream,
        env: Environment,
        *,
        stop_on_attached_minus: bool = False,
    ) -> Any:
        if stream.at_end():
            msg = "Expected an expression, but reached end of input."
            raise LogoSyntaxError(msg)

        tok = stream.peek()
        if isinstance(tok, SymbolToken) and tok.name in ("-", "+"):
            stream.next()
            self._tick()
            operand = self._eval_unary(
                stream,
                env,
                stop_on_attached_minus=stop_on_attached_minus,
            )
            num = self._to_number(operand, f"unary {tok.name}")
            return self._check_finite(-num if tok.name == "-" else num)

        return self._eval_primary(
            stream,
            env,
            stop_on_attached_minus=stop_on_attached_minus,
        )

    def _eval_primary(  # noqa: PLR0911
        self,
        stream: _TokenStream,
        env: Environment,
        *,
        stop_on_attached_minus: bool = False,
    ) -> Any:
        self._tick()
        tok = stream.next()

        if isinstance(tok, NumberToken):
            return self._check_finite(tok.value)

        if isinstance(tok, WordToken):
            return tok.value

        if isinstance(tok, VarToken):
            return env.get(tok.name)

        if isinstance(tok, LogoList):
            return tok

        if isinstance(tok, SymbolToken):
            if tok.name == "(":
                stream.pos -= 1
                return self._eval_paren_or_expr(stream, env, statement_ok=False)

            if tok.name == "?":
                return env.get_foreach_item()

            if tok.name == "#":
                return float(env.get_repcount())

            name = tok.name.upper()
            if name in self.primitives or name in self.procedures:
                res = self._invoke_named(
                    name,
                    tok,
                    stream,
                    env,
                    variadic_until_paren=False,
                    in_tail_pos=False,
                    caller_stop_on_minus=stop_on_attached_minus,
                )
                if res is None:
                    msg = f"{name} did not output a value."
                    raise LogoRuntimeError(msg)
                return res

            msg = f"Unknown procedure or variable: {tok.raw or tok.name}"
            raise LogoRuntimeError(msg)

        msg = f"Cannot evaluate {self._token_desc(tok)}."
        raise LogoRuntimeError(msg)

    def _eval_paren_or_expr(
        self,
        stream: _TokenStream,
        env: Environment,
        *,
        statement_ok: bool = False,
    ) -> Any:
        open_tok = stream.next()  # consume '('
        if stream.at_end():
            msg = f"Unclosed '(' at line {open_tok.line}, column {open_tok.column}."
            raise LogoSyntaxError(msg)

        first = stream.peek()
        second = stream.peek(1)

        # Check if this is a Lisp-style parenthesized procedure call: `(SUM 1 2 3 4)` or `(PRINT "A "B)`
        if isinstance(first, SymbolToken):
            fname = first.name.upper()
            is_known = fname in self.primitives or fname in self.procedures
            if is_known:
                # If a 0-arg reporter like `(XCOR + 10)` is followed immediately by an infix operator,
                # parse it as a normal parenthesized expression rather than a variadic call.
                arity = self._get_default_arity(fname)
                second_is_infix = (
                    isinstance(second, SymbolToken)
                    and second.name in _INFIX_PRECEDENCE
                    and not (second.name == "-" and second.space_before and not second.space_after and arity > 0)
                )
                if not (arity == 0 and second_is_infix):
                    stream.next()  # consume procedure name
                    res = self._invoke_named(
                        fname,
                        first,
                        stream,
                        env,
                        variadic_until_paren=True,
                        in_tail_pos=False,
                    )
                    # If an infix operator still appears before ')' (e.g. `(ABS -5 + 2)`), continue infix
                    if not stream.at_end():
                        nxt = stream.peek()
                        if isinstance(nxt, SymbolToken) and nxt.name != ")":
                            if res is None:
                                msg = f"Expected ')' after {fname} call."
                                raise LogoSyntaxError(msg)
                            res = self._eval_infix_continuation(res, stream, env, min_prec=0)
                    close_tok = stream.peek()
                    if not isinstance(close_tok, SymbolToken) or close_tok.name != ")":
                        msg = f"Expected ')' to close '(' from line {open_tok.line}."
                        raise LogoSyntaxError(msg)
                    stream.next()  # consume ')'
                    if res is None and not statement_ok:
                        msg = f"{fname} did not output a value."
                        raise LogoRuntimeError(msg)
                    return res

        # Standard parenthesized expression: `(10 + 5)`
        val = self._eval_expr(stream, env, min_prec=0, stop_on_attached_minus=False)
        close_tok = stream.peek()
        if not isinstance(close_tok, SymbolToken) or close_tok.name != ")":
            msg = f"Expected ')' to close '(' from line {open_tok.line}."
            raise LogoSyntaxError(msg)
        stream.next()  # consume ')'
        return val

    def _get_default_arity(self, name: str) -> int:
        if name in self.primitives:
            return self.primitives[name].default_arity
        if name in self.procedures:
            return len(self.procedures[name].parameters)
        return 0

    def _invoke_named(  # noqa: PLR0912, PLR0915
        self,
        name: str,
        call_tok: SymbolToken,
        stream: _TokenStream,
        env: Environment,
        *,
        variadic_until_paren: bool = False,
        in_tail_pos: bool = False,
        caller_stop_on_minus: bool = False,
    ) -> Any:
        self._tick()
        if name in self.primitives:
            spec = self.primitives[name]
            args: list[Any] = []

            if variadic_until_paren:
                while not stream.at_end():
                    peeked = stream.peek()
                    if isinstance(peeked, SymbolToken) and peeked.name == ")":
                        break
                    if len(args) == 0 and spec.raw_first_var_fallback and isinstance(peeked, VarToken):
                        vtok = stream.next()
                        assert isinstance(vtok, VarToken)
                        args.append(env.get(vtok.name) if env.has(vtok.name) else vtok.name)
                    else:
                        args.append(
                            self._eval_expr(
                                stream,
                                env,
                                stop_on_attached_minus=True,
                            )
                        )
                if len(args) < spec.min_arity:
                    msg = f"{name} expects at least {spec.min_arity} argument(s), got {len(args)}."
                    raise LogoRuntimeError(msg)
                if spec.max_arity != -1 and len(args) > spec.max_arity:
                    msg = f"{name} expects at most {spec.max_arity} argument(s), got {len(args)}."
                    raise LogoRuntimeError(msg)
            else:
                arity = spec.default_arity
                for idx in range(arity):
                    if stream.at_end():
                        msg = f"{name} expects {arity} argument(s), got {idx}."
                        raise LogoRuntimeError(msg)
                    peeked = stream.peek()
                    if isinstance(peeked, SymbolToken) and peeked.name == ")":
                        msg = f"{name} expects {arity} argument(s), got {idx}."
                        raise LogoRuntimeError(msg)
                    if idx == 0 and spec.raw_first_var_fallback and isinstance(peeked, VarToken):
                        vtok = stream.next()
                        assert isinstance(vtok, VarToken)
                        args.append(env.get(vtok.name) if env.has(vtok.name) else vtok.name)
                    else:
                        more_args_Remain = (idx < arity - 1) or caller_stop_on_minus
                        args.append(
                            self._eval_expr(
                                stream,
                                env,
                                stop_on_attached_minus=more_args_Remain,
                            )
                        )
                # Special convenience for IF with 3 arguments without parens: `IF cond [then] [else]`
                if name == "IF" and not stream.at_end():
                    nxt = stream.peek()
                    if isinstance(nxt, SymbolToken) and nxt.name == "ELSE":
                        stream.next()
                        if stream.at_end():
                            msg = "Expected list after ELSE."
                            raise LogoSyntaxError(msg)
                        args.append(self._eval_expr(stream, env, stop_on_attached_minus=caller_stop_on_minus))

            is_tail = in_tail_pos and stream.at_end()
            return spec.handler(args, env, is_tail)

        # User-defined procedure
        proc = self.procedures.get(name)
        if proc is None:
            msg = f"Unknown procedure: {name}"
            raise LogoRuntimeError(msg)

        arity = len(proc.parameters)
        args = []
        if variadic_until_paren:
            while not stream.at_end():
                peeked = stream.peek()
                if isinstance(peeked, SymbolToken) and peeked.name == ")":
                    break
                args.append(self._eval_expr(stream, env, stop_on_attached_minus=True))
            if len(args) != arity:
                msg = f"{name} expects {arity} argument(s), got {len(args)}."
                raise LogoRuntimeError(msg)
        else:
            for idx in range(arity):
                if stream.at_end():
                    msg = f"{name} expects {arity} argument(s), got {idx}."
                    raise LogoRuntimeError(msg)
                peeked = stream.peek()
                if isinstance(peeked, SymbolToken) and peeked.name == ")":
                    msg = f"{name} expects {arity} argument(s), got {idx}."
                    raise LogoRuntimeError(msg)
                more_args_remain = (idx < arity - 1) or caller_stop_on_minus
                args.append(
                    self._eval_expr(
                        stream,
                        env,
                        stop_on_attached_minus=more_args_remain,
                    )
                )

        if in_tail_pos and stream.at_end():
            raise _TailCallSignal(proc, args)

        return self._call_user_procedure(proc, args, env)

    def _call_user_procedure(
        self,
        procedure: Procedure,
        arguments: list[Any],
        caller_env: Environment,
    ) -> Any:
        if self.call_depth >= self._max_call_depth:
            msg = "Maximum procedure recursion depth exceeded."
            raise LogoRuntimeError(msg)

        self.call_depth += 1
        try:
            curr_proc = procedure
            curr_args = arguments
            while True:
                self._tick()
                local_values: dict[str, Any] = {}
                local_declared: set[str] = set()
                for param, arg in zip(curr_proc.parameters, curr_args, strict=False):
                    key = param.upper()
                    local_values[key] = arg
                    local_declared.add(key)

                local_env = Environment(
                    values=local_values,
                    parent=caller_env,
                    locals_declared=local_declared,
                )
                body_stream = _TokenStream(curr_proc.body)
                try:
                    self._execute_stream(body_stream, local_env, in_tail_pos=True)
                    return None
                except _TailCallSignal as tail:
                    curr_proc = tail.procedure
                    curr_args = tail.arguments
                    continue
                except _StopSignal:
                    return None
                except _OutputSignal as out:
                    return out.value
        finally:
            self.call_depth -= 1

    def _apply_binary_op(self, op: str, left: Any, right: Any) -> float:  # noqa: PLR0911, PLR0912
        self._tick()
        if op == "=":
            return 1.0 if self._values_equal(left, right) else 0.0
        if op in ("<>", "!="):
            return 0.0 if self._values_equal(left, right) else 1.0

        lnum = self._to_number(left, f"operator {op}")
        rnum = self._to_number(right, f"operator {op}")

        if op == "+":
            return self._check_finite(lnum + rnum)
        if op == "-":
            return self._check_finite(lnum - rnum)
        if op == "*":
            return self._check_finite(lnum * rnum)
        if op == "/":
            if rnum == 0.0:
                msg = "Division by zero."
                raise LogoRuntimeError(msg)
            return self._check_finite(lnum / rnum)
        if op == "%":
            if rnum == 0.0:
                msg = "Division by zero in modulo."
                raise LogoRuntimeError(msg)
            return self._check_finite(math.fmod(lnum, rnum))
        if op == "^":
            return self._safe_power(lnum, rnum)
        if op == "<":
            return 1.0 if lnum < rnum else 0.0
        if op == ">":
            return 1.0 if lnum > rnum else 0.0
        if op == "<=":
            return 1.0 if lnum <= rnum else 0.0
        if op == ">=":
            return 1.0 if lnum >= rnum else 0.0

        msg = f"Unknown binary operator: {op}"
        raise LogoRuntimeError(msg)

    def _safe_power(self, base: float, exp: float) -> float:
        if base == 0.0 and exp < 0.0:
            msg = "Zero cannot be raised to a negative power."
            raise LogoRuntimeError(msg)
        if base < 0.0 and not exp.is_integer():
            msg = "Negative base cannot be raised to a fractional power."
            raise LogoRuntimeError(msg)
        if abs(base) > 1.0 and exp > 1024.0:
            msg = "Exponent is too large (numeric overflow)."
            raise LogoRuntimeError(msg)
        try:
            res = math.pow(base, exp)
        except (OverflowError, ValueError) as exc:
            msg = "Numeric overflow in power operation."
            raise LogoRuntimeError(msg) from exc
        return self._check_finite(res)

    # Primitive registration
    def _reg(
        self,
        names: str | tuple[str, ...],
        default_arity: int,
        handler: Callable[[list[Any], Environment, bool], Any],
        *,
        min_arity: int | None = None,
        max_arity: int | None = None,
        raw_first_var_fallback: bool = False,
    ) -> None:
        if isinstance(names, str):
            names = (names,)
        lo = default_arity if min_arity is None else min_arity
        hi = default_arity if max_arity is None else max_arity
        for name in names:
            uname = name.upper()
            self.primitives[uname] = PrimitiveSpec(
                name=uname,
                default_arity=default_arity,
                min_arity=lo,
                max_arity=hi,
                handler=handler,
                raw_first_var_fallback=raw_first_var_fallback,
            )

    def _register_all_primitives(self) -> None:  # noqa: PLR0915
        # --- Turtle Movement & Position ---
        self._reg(
            ("FD", "FORWARD"),
            1,
            lambda a, e, t: self.turtle.forward(self._to_number(a[0], "FD")),
        )
        self._reg(
            ("BK", "BACK", "BACKWARD"),
            1,
            lambda a, e, t: self.turtle.backward(self._to_number(a[0], "BK")),
        )
        self._reg(
            ("RT", "RIGHT"),
            1,
            lambda a, e, t: self.turtle.right(self._to_number(a[0], "RT")),
        )
        self._reg(
            ("LT", "LEFT"),
            1,
            lambda a, e, t: self.turtle.left(self._to_number(a[0], "LT")),
        )
        self._reg(("PU", "PENUP"), 0, lambda a, e, t: self.turtle.pen_up())
        self._reg(("PD", "PENDOWN"), 0, lambda a, e, t: self.turtle.pen_down_mode())
        self._reg(("PPT", "PENPAINT"), 0, lambda a, e, t: self.turtle.pen_paint())
        self._reg(("PE", "PENERASE"), 0, lambda a, e, t: self.turtle.pen_erase())
        self._reg(("PX", "PENREVERSE"), 0, lambda a, e, t: self.turtle.pen_reverse())
        self._reg(("ST", "SHOWTURTLE"), 0, lambda a, e, t: self.turtle.show_turtle())
        self._reg(("HT", "HIDETURTLE"), 0, lambda a, e, t: self.turtle.hide_turtle())
        self._reg("HOME", 0, lambda a, e, t: self.turtle.home())
        self._reg(("CS", "CLEARSCREEN"), 0, lambda a, e, t: self.turtle.clear_screen())
        self._reg("CLEAN", 0, lambda a, e, t: self.turtle.clean())
        self._reg(
            "SETXY",
            2,
            lambda a, e, t: self.turtle.set_xy(
                self._to_number(a[0], "SETXY"),
                self._to_number(a[1], "SETXY"),
            ),
        )
        self._reg("SETPOS", 1, self._prim_setpos)
        self._reg("SETX", 1, lambda a, e, t: self.turtle.set_x(self._to_number(a[0], "SETX")))
        self._reg("SETY", 1, lambda a, e, t: self.turtle.set_y(self._to_number(a[0], "SETY")))
        self._reg(
            ("SETH", "SETHEADING"),
            1,
            lambda a, e, t: self.turtle.set_heading(self._to_number(a[0], "SETH")),
        )
        self._reg("POS", 0, lambda a, e, t: LogoList.from_values(list(self.turtle.get_pos())))
        self._reg("XCOR", 0, lambda a, e, t: self.turtle.get_xcor())
        self._reg("YCOR", 0, lambda a, e, t: self.turtle.get_ycor())
        self._reg("HEADING", 0, lambda a, e, t: self.turtle.get_heading())
        self._reg("TOWARDS", 1, self._prim_towards)
        self._reg(("DIST", "DISTANCE"), 1, self._prim_distance)
        self._reg(("SHOWNP", "SHOWN?"), 0, lambda a, e, t: 1.0 if self.turtle.visible else 0.0)
        self._reg(
            ("PENDOWNP", "PENDOWN?"),
            0,
            lambda a, e, t: 1.0 if self.turtle.pen_down else 0.0,
        )

        # --- Turtle Shapes, Fills, Labels & Colors ---
        self._reg(
            "ARC",
            2,
            lambda a, e, t: self.turtle.arc(
                self._to_number(a[0], "ARC angle"),
                self._to_number(a[1], "ARC radius"),
            ),
        )
        self._reg(
            "CIRCLE",
            1,
            lambda a, e, t: self.turtle.arc(360.0, self._to_number(a[0], "CIRCLE radius")),
        )
        self._reg(
            "ELLIPSE",
            2,
            lambda a, e, t: self.turtle.ellipse(
                self._to_number(a[0], "ELLIPSE rx"),
                self._to_number(a[1], "ELLIPSE ry"),
            ),
        )
        self._reg("DOT", 0, self._prim_dot, min_arity=0, max_arity=1)
        self._reg("FILL", 0, lambda a, e, t: self.turtle.fill())
        self._reg("FILLED", 2, self._prim_filled)
        self._reg("LABEL", 1, lambda a, e, t: self.turtle.label(self._format_value(a[0])))
        self._reg(
            ("SETLABELHEIGHT", "SETFONTSIZE"),
            1,
            lambda a, e, t: self.turtle.set_label_height(self._require_int(a[0], "SETLABELHEIGHT")),
        )
        self._reg(
            ("SETPC", "SETPENCOLOR", "SETPENCOLOUR"),
            1,
            lambda a, e, t: self.turtle.set_color(parse_color(a[0])),
        )
        self._reg(
            ("SETFC", "SETFLOODCOLOR", "SETFLOODCOLOUR"),
            1,
            lambda a, e, t: self.turtle.set_flood_color(parse_color(a[0])),
        )
        self._reg(
            ("SETBG", "SETSC", "SETSCREENCOLOR", "SETBACKGROUNDCOLOR"),
            1,
            lambda a, e, t: self.turtle.set_bg_color(parse_color(a[0])),
        )
        self._reg(
            ("SETPENSIZE", "SETWIDTH", "SETW"),
            1,
            self._prim_setpensize,
        )
        self._reg(
            ("PENCOLOR", "PC"),
            0,
            lambda a, e, t: LogoList.from_values(list(self.turtle.pen_color)),
        )
        self._reg(
            ("SCREENCOLOR", "SC", "BG"),
            0,
            lambda a, e, t: LogoList.from_values(list(self.turtle.bg_color)),
        )
        self._reg("PENSIZE", 0, lambda a, e, t: float(self.turtle.pen_width))

        # --- Multi-Turtle Commands (Tier 2 with hard cap) ---
        self._reg(
            "SETTURTLE",
            1,
            lambda a, e, t: self.turtle.set_turtle(self._require_int(a[0], "SETTURTLE")),
        )
        self._reg("TURTLE", 0, lambda a, e, t: float(self.turtle._active_ids[0]))
        self._reg("TURTLES", 0, lambda a, e, t: float(self.turtle.max_turtle_id()))
        self._reg("WHO", 0, self._prim_who)
        self._reg("TELL", 1, self._prim_tell)
        self._reg("ASK", 2, self._prim_ask)

        # --- Control Flow ---
        self._reg("REPEAT", 2, self._prim_repeat)
        self._reg("REPCOUNT", 0, lambda a, e, t: float(e.get_repcount()))
        self._reg("IF", 2, self._prim_if, min_arity=2, max_arity=3)
        self._reg("IFELSE", 3, self._prim_ifelse)
        self._reg("TEST", 1, self._prim_test)
        self._reg(("IFTRUE", "IFT"), 1, self._prim_iftrue)
        self._reg(("IFFALSE", "IFF"), 1, self._prim_iffalse)
        self._reg("FOR", 2, self._prim_for)
        self._reg("WHILE", 2, self._prim_while)
        self._reg("UNTIL", 2, self._prim_until)
        self._reg("FOREACH", 2, self._prim_foreach)
        self._reg("RUN", 1, self._prim_run)
        self._reg("STOP", 0, self._prim_stop)
        self._reg(("OUTPUT", "OP"), 1, self._prim_output)
        self._reg("IGNORE", 1, lambda a, e, t: None)

        # --- Variables & Scope ---
        self._reg("MAKE", 2, self._prim_make, raw_first_var_fallback=True)
        self._reg(
            "LOCAL",
            1,
            self._prim_local,
            min_arity=1,
            max_arity=-1,
            raw_first_var_fallback=True,
        )
        self._reg("LOCALMAKE", 2, self._prim_localmake, raw_first_var_fallback=True)
        self._reg("THING", 1, self._prim_thing)
        self._reg(("NAMEP", "NAME?"), 1, self._prim_namep)

        # --- Math & Logic ---
        self._reg("SUM", 2, self._prim_sum, min_arity=0, max_arity=-1)
        self._reg("DIFFERENCE", 2, lambda a, e, t: self._apply_binary_op("-", a[0], a[1]))
        self._reg(
            "MINUS",
            1,
            lambda a, e, t: self._check_finite(-self._to_number(a[0], "MINUS")),
        )
        self._reg("PRODUCT", 2, self._prim_product, min_arity=0, max_arity=-1)
        self._reg("QUOTIENT", 2, self._prim_quotient, min_arity=1, max_arity=2)
        self._reg("REMAINDER", 2, self._prim_remainder)
        self._reg("MODULO", 2, self._prim_modulo)
        self._reg("SQRT", 1, self._prim_sqrt)
        self._reg(
            "POWER",
            2,
            lambda a, e, t: self._safe_power(self._to_number(a[0], "POWER"), self._to_number(a[1], "POWER")),
        )
        self._reg("EXP", 1, self._prim_exp)
        self._reg("LN", 1, self._prim_ln)
        self._reg("LOG10", 1, self._prim_log10)
        self._reg(
            "SIN",
            1,
            lambda a, e, t: self._check_finite(math.sin(math.radians(self._to_number(a[0], "SIN")))),
        )
        self._reg(
            "COS",
            1,
            lambda a, e, t: self._check_finite(math.cos(math.radians(self._to_number(a[0], "COS")))),
        )
        self._reg(
            "TAN",
            1,
            lambda a, e, t: self._check_finite(math.tan(math.radians(self._to_number(a[0], "TAN")))),
        )
        self._reg("ARCTAN", 1, self._prim_arctan, min_arity=1, max_arity=2)
        self._reg(
            "RADSIN",
            1,
            lambda a, e, t: self._check_finite(math.sin(self._to_number(a[0], "RADSIN"))),
        )
        self._reg(
            "RADCOS",
            1,
            lambda a, e, t: self._check_finite(math.cos(self._to_number(a[0], "RADCOS"))),
        )
        self._reg("RADARCTAN", 1, self._prim_radarctan, min_arity=1, max_arity=2)
        self._reg("RANDOM", 1, self._prim_random, min_arity=1, max_arity=2)
        self._reg("RERANDOM", 0, self._prim_rerandom, min_arity=0, max_arity=1)
        self._reg("INT", 1, lambda a, e, t: float(math.trunc(self._to_number(a[0], "INT"))))
        self._reg("ROUND", 1, self._prim_round)
        self._reg("ABS", 1, lambda a, e, t: abs(self._to_number(a[0], "ABS")))
        self._reg("SIGN", 1, self._prim_sign)
        self._reg("PI", 0, lambda a, e, t: math.pi)

        # Comparisons & Boolean Logic
        self._reg(
            ("EQUALP", "EQUAL?"),
            2,
            lambda a, e, t: 1.0 if self._values_equal(a[0], a[1]) else 0.0,
        )
        self._reg(
            ("NOTEQUALP", "NOTEQUAL?"),
            2,
            lambda a, e, t: 0.0 if self._values_equal(a[0], a[1]) else 1.0,
        )
        self._reg(
            ("LESSP", "LESS?"),
            2,
            lambda a, e, t: self._apply_binary_op("<", a[0], a[1]),
        )
        self._reg(
            ("GREATERP", "GREATER?"),
            2,
            lambda a, e, t: self._apply_binary_op(">", a[0], a[1]),
        )
        self._reg(
            ("LESSEQUALP", "LESSEQUAL?"),
            2,
            lambda a, e, t: self._apply_binary_op("<=", a[0], a[1]),
        )
        self._reg(
            ("GREATEREQUALP", "GREATEREQUAL?"),
            2,
            lambda a, e, t: self._apply_binary_op(">=", a[0], a[1]),
        )
        self._reg("AND", 2, self._prim_and, min_arity=1, max_arity=-1)
        self._reg("OR", 2, self._prim_or, min_arity=1, max_arity=-1)
        self._reg("NOT", 1, lambda a, e, t: 0.0 if self._to_bool(a[0]) else 1.0)
        self._reg("TRUE", 0, lambda a, e, t: 1.0)
        self._reg("FALSE", 0, lambda a, e, t: 0.0)

        # --- Data (List & Word) Primitives ---
        self._reg(
            "LIST",
            2,
            lambda a, e, t: LogoList.from_values(a),
            min_arity=0,
            max_arity=-1,
        )
        self._reg(("SENTENCE", "SE"), 2, self._prim_sentence, min_arity=0, max_arity=-1)
        self._reg("WORD", 2, self._prim_word, min_arity=0, max_arity=-1)
        self._reg("FIRST", 1, self._prim_first)
        self._reg("LAST", 1, self._prim_last)
        self._reg(("BUTFIRST", "BF"), 1, self._prim_butfirst)
        self._reg(("BUTLAST", "BL"), 1, self._prim_butlast)
        self._reg("ITEM", 2, self._prim_item)
        self._reg("PICK", 1, self._prim_pick)
        self._reg("COUNT", 1, self._prim_count)
        self._reg("FPUT", 2, self._prim_fput)
        self._reg("LPUT", 2, self._prim_lput)
        self._reg(("EMPTYP", "EMPTY?"), 1, self._prim_emptyp)
        self._reg(
            ("WORDP", "WORD?"),
            1,
            lambda a, e, t: 0.0 if isinstance(a[0], LogoList) else 1.0,
        )
        self._reg(
            ("LISTP", "LIST?"),
            1,
            lambda a, e, t: 1.0 if isinstance(a[0], LogoList) else 0.0,
        )
        self._reg(("NUMBERP", "NUMBER?"), 1, self._prim_numberp)
        self._reg(("MEMBERP", "MEMBER?"), 2, self._prim_memberp)
        self._reg("LOWERCASE", 1, lambda a, e, t: self._to_word_str(a[0]).lower())
        self._reg("UPPERCASE", 1, lambda a, e, t: self._to_word_str(a[0]).upper())
        self._reg("ASCII", 1, self._prim_ascii)
        self._reg("CHAR", 1, self._prim_char)

        # --- Output Primitives ---
        self._reg(("PRINT", "PR"), 1, self._prim_print, min_arity=0, max_arity=-1)
        self._reg("TYPE", 1, self._prim_type, min_arity=0, max_arity=-1)
        self._reg("SHOW", 1, self._prim_show, min_arity=0, max_arity=-1)

    # --- Turtle Primitive Implementations ---
    def _prim_setpos(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        lst = self._require_list(args[0], "SETPOS")
        vals = lst.values
        if len(vals) != 2:
            msg = f"SETPOS expects a list of 2 numbers [x y], got {len(vals)}."
            raise LogoRuntimeError(msg)
        self.turtle.set_xy(self._to_number(vals[0], "SETPOS"), self._to_number(vals[1], "SETPOS"))

    def _prim_towards(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        lst = self._require_list(args[0], "TOWARDS")
        vals = lst.values
        if len(vals) != 2:
            msg = f"TOWARDS expects a list of 2 numbers [x y], got {len(vals)}."
            raise LogoRuntimeError(msg)
        return self.turtle.towards(self._to_number(vals[0], "TOWARDS"), self._to_number(vals[1], "TOWARDS"))

    def _prim_distance(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        lst = self._require_list(args[0], "DISTANCE")
        vals = lst.values
        if len(vals) != 2:
            msg = f"DISTANCE expects a list of 2 numbers [x y], got {len(vals)}."
            raise LogoRuntimeError(msg)
        tx = self._to_number(vals[0], "DISTANCE")
        ty = self._to_number(vals[1], "DISTANCE")
        return self._check_finite(math.hypot(tx - self.turtle.get_xcor(), ty - self.turtle.get_ycor()))

    def _prim_dot(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        if not args:
            self.turtle.dot()
            return
        lst = self._require_list(args[0], "DOT")
        vals = lst.values
        if len(vals) != 2:
            msg = f"DOT expects a list of 2 numbers [x y], got {len(vals)}."
            raise LogoRuntimeError(msg)
        self.turtle.dot((self._to_number(vals[0], "DOT"), self._to_number(vals[1], "DOT")))

    def _prim_filled(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        fill_color = parse_color(args[0])
        body = self._require_list(args[1], "FILLED")
        op_index_before = len(self.turtle.ops)
        self.turtle.begin_polygon()
        try:
            self._execute_list(body, env, in_tail_pos=False)
        finally:
            self.turtle.end_polygon(fill_color)
            # Move PolygonFillOp right before the outline segments drawn during FILLED
            if len(self.turtle.ops) > op_index_before and isinstance(self.turtle.ops[-1], object) and isinstance(self.turtle.ops[-1], PolygonFillOp):
                poly_op = self.turtle.ops.pop()
                self.turtle.ops.insert(op_index_before, poly_op)

    def _prim_setpensize(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        val = args[0]
        if isinstance(val, LogoList):
            if not val.values:
                msg = "SETPENSIZE list cannot be empty."
                raise LogoRuntimeError(msg)
            width = self._require_int(val.values[0], "SETPENSIZE")
        else:
            width = self._require_int(val, "SETPENSIZE")
        self.turtle.set_width(width)

    def _prim_who(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        w = self.turtle.who()
        if isinstance(w, int):
            return float(w)
        return LogoList.from_values([float(tid) for tid in w])

    def _prim_tell(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        target = args[0]
        if isinstance(target, LogoList):
            tids = [self._require_int(v, "TELL") for v in target.values]
            self.turtle.tell(tids)
        else:
            self.turtle.set_turtle(self._require_int(target, "TELL"))

    def _prim_ask(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        target = args[0]
        body = self._require_list(args[1], "ASK")
        prev_active = self.turtle._active_ids
        try:
            if isinstance(target, LogoList):
                tids = [self._require_int(v, "ASK") for v in target.values]
                self.turtle.tell(tids)
            else:
                self.turtle.set_turtle(self._require_int(target, "ASK"))
            return self._execute_list(body, env, in_tail_pos=False, allow_value=True)
        finally:
            self.turtle._active_ids = prev_active

    # --- Control Flow Primitive Implementations ---
    def _prim_repeat(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        count = self._require_int(args[0], "REPEAT")
        if count < 0 or count > self._max_repeat:
            msg = f"REPEAT must be between 0 and {self._max_repeat}."
            raise LogoRuntimeError(msg)
        body = self._require_list(args[1], "REPEAT")
        loop_env = Environment(parent=env)
        for i in range(1, count + 1):
            self._tick()
            loop_env.repcount = i
            self._execute_list(body, loop_env, in_tail_pos=False)

    def _prim_if(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        cond = self._to_bool(args[0])
        then_list = self._require_list(args[1], "IF")
        if cond:
            return self._execute_list(then_list, env, in_tail_pos=is_tail, allow_value=True)
        if len(args) == 3:
            else_list = self._require_list(args[2], "IF")
            return self._execute_list(else_list, env, in_tail_pos=is_tail, allow_value=True)
        return None

    def _prim_ifelse(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        cond = self._to_bool(args[0])
        then_list = self._require_list(args[1], "IFELSE")
        else_list = self._require_list(args[2], "IFELSE")
        chosen = then_list if cond else else_list
        return self._execute_list(chosen, env, in_tail_pos=is_tail, allow_value=True)

    def _prim_test(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        env.test_state = self._to_bool(args[0])

    def _prim_iftrue(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        state = env.get_test_state()
        body = self._require_list(args[0], "IFTRUE")
        if state:
            return self._execute_list(body, env, in_tail_pos=is_tail, allow_value=True)
        return None

    def _prim_iffalse(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        state = env.get_test_state()
        body = self._require_list(args[0], "IFFALSE")
        if not state:
            return self._execute_list(body, env, in_tail_pos=is_tail, allow_value=True)
        return None

    def _prim_for(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        ctrl = self._require_list(args[0], "FOR control")
        body = self._require_list(args[1], "FOR body")
        ctrl_stream = _TokenStream(ctrl.tokens)
        if ctrl_stream.at_end():
            msg = "FOR control list requires [varname start end] or [varname start end step]."
            raise LogoRuntimeError(msg)
        first_tok = ctrl_stream.next()
        if isinstance(first_tok, SymbolToken):
            var_name = first_tok.name.upper()
        elif isinstance(first_tok, WordToken):
            var_name = first_tok.value.upper()
        elif isinstance(first_tok, VarToken):
            var_name = first_tok.name.upper()
        else:
            msg = "FOR control list must start with a variable name."
            raise LogoRuntimeError(msg)

        start_val = self._to_number(self._eval_expr(ctrl_stream, env, stop_on_attached_minus=True), "FOR start")
        end_val = self._to_number(self._eval_expr(ctrl_stream, env, stop_on_attached_minus=True), "FOR end")
        if not ctrl_stream.at_end():
            step_val = self._to_number(
                self._eval_expr(ctrl_stream, env, stop_on_attached_minus=False),
                "FOR step",
            )
        else:
            step_val = 1.0 if start_val <= end_val else -1.0

        if not ctrl_stream.at_end():
            msg = "Too many items in FOR control list."
            raise LogoRuntimeError(msg)
        if step_val == 0.0:
            msg = "FOR step cannot be zero."
            raise LogoRuntimeError(msg)

        loop_env = Environment(parent=env)
        loop_env.declare_local(var_name)
        curr = start_val
        iterations = 0
        while (step_val > 0 and curr <= end_val + 1e-9) or (step_val < 0 and curr >= end_val - 1e-9):
            iterations += 1
            if iterations > self._max_repeat:
                msg = f"FOR loop exceeded maximum iterations ({self._max_repeat})."
                raise LogoRuntimeError(msg)
            self._tick()
            loop_env.repcount = iterations
            loop_env.set(var_name, curr, self._max_variables)
            self._execute_list(body, loop_env, in_tail_pos=False)
            curr = self._check_finite(curr + step_val)

    def _prim_while(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        cond_list = self._require_list(args[0], "WHILE condition")
        body_list = self._require_list(args[1], "WHILE body")
        loop_env = Environment(parent=env)
        iterations = 0
        while True:
            self._tick()
            cond_val = self._execute_list(cond_list, loop_env, allow_value=True)
            if not self._to_bool(cond_val):
                break
            iterations += 1
            if iterations > self._max_repeat:
                msg = f"WHILE loop exceeded maximum iterations ({self._max_repeat})."
                raise LogoRuntimeError(msg)
            loop_env.repcount = iterations
            self._execute_list(body_list, loop_env, in_tail_pos=False)

    def _prim_until(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        cond_list = self._require_list(args[0], "UNTIL condition")
        body_list = self._require_list(args[1], "UNTIL body")
        loop_env = Environment(parent=env)
        iterations = 0
        while True:
            self._tick()
            cond_val = self._execute_list(cond_list, loop_env, allow_value=True)
            if self._to_bool(cond_val):
                break
            iterations += 1
            if iterations > self._max_repeat:
                msg = f"UNTIL loop exceeded maximum iterations ({self._max_repeat})."
                raise LogoRuntimeError(msg)
            loop_env.repcount = iterations
            self._execute_list(body_list, loop_env, in_tail_pos=False)

    def _prim_foreach(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        data = args[0]
        body = self._require_list(args[1], "FOREACH")
        items = list(data.values) if isinstance(data, LogoList) else list(self._to_word_str(data))

        loop_env = Environment(parent=env, has_foreach_item=True)
        for idx, item in enumerate(items, start=1):
            if idx > self._max_repeat:
                msg = f"FOREACH exceeded maximum iterations ({self._max_repeat})."
                raise LogoRuntimeError(msg)
            self._tick()
            loop_env.repcount = idx
            loop_env.foreach_item = item
            self._execute_list(body, loop_env, in_tail_pos=False)

    def _prim_run(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        target = args[0]
        if isinstance(target, LogoList):
            return self._execute_list(target, env, in_tail_pos=is_tail, allow_value=True)
        if isinstance(target, str):
            tokens = tokenize_and_read(target)
            stream = _TokenStream(tokens)
            return self._execute_stream(stream, env, in_tail_pos=is_tail, allow_value=True)
        msg = f"RUN expects a list or word, got {self._format_value(target)}."
        raise LogoRuntimeError(msg)

    def _prim_stop(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        raise _StopSignal()

    def _prim_output(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        raise _OutputSignal(args[0])

    # --- Variable & Scope Implementations ---
    def _extract_var_name(self, raw: Any, context: str) -> str:
        name = self._to_word_str(raw).strip().lstrip(":").lstrip('"').upper()
        if not name:
            msg = f"{context} variable name cannot be empty."
            raise LogoRuntimeError(msg)
        return name

    def _prim_make(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        name = self._extract_var_name(args[0], "MAKE")
        env.set(name, args[1], self._max_variables)

    def _prim_local(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        for arg in args:
            if isinstance(arg, LogoList):
                for item in arg.values:
                    env.declare_local(self._extract_var_name(item, "LOCAL"))
            else:
                env.declare_local(self._extract_var_name(arg, "LOCAL"))

    def _prim_localmake(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        name = self._extract_var_name(args[0], "LOCALMAKE")
        env.declare_local(name)
        env.set(name, args[1], self._max_variables)

    def _prim_thing(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        name = self._extract_var_name(args[0], "THING")
        return env.get(name)

    def _prim_namep(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        name = self._extract_var_name(args[0], "NAMEP")
        return 1.0 if env.has(name) else 0.0

    # --- Math & Logic Implementations ---
    def _prim_sum(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        total = 0.0
        for a in args:
            self._tick()
            total = self._check_finite(total + self._to_number(a, "SUM"))
        return total

    def _prim_product(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        prod = 1.0
        for a in args:
            self._tick()
            prod = self._check_finite(prod * self._to_number(a, "PRODUCT"))
        return prod

    def _prim_quotient(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        if len(args) == 1:
            denom = self._to_number(args[0], "QUOTIENT")
            if denom == 0.0:
                msg = "Division by zero."
                raise LogoRuntimeError(msg)
            return self._check_finite(1.0 / denom)
        return self._apply_binary_op("/", args[0], args[1])

    def _prim_remainder(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        a = self._to_number(args[0], "REMAINDER")
        b = self._to_number(args[1], "REMAINDER")
        if b == 0.0:
            msg = "Division by zero."
            raise LogoRuntimeError(msg)
        return self._check_finite(math.fmod(a, b))

    def _prim_modulo(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        a = self._to_number(args[0], "MODULO")
        b = self._to_number(args[1], "MODULO")
        if b == 0.0:
            msg = "Division by zero."
            raise LogoRuntimeError(msg)
        return self._check_finite(a % b)

    def _prim_sqrt(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        x = self._to_number(args[0], "SQRT")
        if x < 0.0:
            msg = "SQRT requires a non-negative number."
            raise LogoRuntimeError(msg)
        return self._check_finite(math.sqrt(x))

    def _prim_exp(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        x = self._to_number(args[0], "EXP")
        if x > 709.0:
            msg = "Numeric overflow in EXP."
            raise LogoRuntimeError(msg)
        return self._check_finite(math.exp(x))

    def _prim_ln(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        x = self._to_number(args[0], "LN")
        if x <= 0.0:
            msg = "LN requires a positive number."
            raise LogoRuntimeError(msg)
        return self._check_finite(math.log(x))

    def _prim_log10(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        x = self._to_number(args[0], "LOG10")
        if x <= 0.0:
            msg = "LOG10 requires a positive number."
            raise LogoRuntimeError(msg)
        return self._check_finite(math.log10(x))

    def _prim_arctan(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        if len(args) == 1:
            x = self._to_number(args[0], "ARCTAN")
            return self._check_finite(math.degrees(math.atan(x)))
        dx = self._to_number(args[0], "ARCTAN")
        dy = self._to_number(args[1], "ARCTAN")
        return self._check_finite(math.degrees(math.atan2(dy, dx)))

    def _prim_radarctan(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        if len(args) == 1:
            x = self._to_number(args[0], "RADARCTAN")
            return self._check_finite(math.atan(x))
        dx = self._to_number(args[0], "RADARCTAN")
        dy = self._to_number(args[1], "RADARCTAN")
        return self._check_finite(math.atan2(dy, dx))

    def _prim_random(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        if len(args) == 1:
            n = self._require_int(args[0], "RANDOM")
            if n <= 0:
                msg = f"RANDOM requires a positive integer, got {n}."
                raise LogoRuntimeError(msg)
            return float(self._rng.randrange(n))
        lo = self._require_int(args[0], "RANDOM")
        hi = self._require_int(args[1], "RANDOM")
        if lo > hi:
            msg = f"RANDOM range start ({lo}) cannot exceed end ({hi})."
            raise LogoRuntimeError(msg)
        return float(self._rng.randint(lo, hi))

    def _prim_rerandom(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        seed = self._require_int(args[0], "RERANDOM") if args else 0
        self._rng.seed(seed)

    def _prim_round(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        x = self._to_number(args[0], "ROUND")
        if x >= 0.0:
            return float(math.floor(x + 0.5))
        return float(math.ceil(x - 0.5))

    def _prim_sign(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        x = self._to_number(args[0], "SIGN")
        if x > 0.0:
            return 1.0
        if x < 0.0:
            return -1.0
        return 0.0

    def _eval_bool_arg(self, arg: Any, env: Environment) -> bool:
        if isinstance(arg, LogoList):
            val = self._execute_list(arg, env, allow_value=True)
            return self._to_bool(val)
        return self._to_bool(arg)

    def _prim_and(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        for arg in args:
            self._tick()
            if not self._eval_bool_arg(arg, env):
                return 0.0
        return 1.0

    def _prim_or(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        for arg in args:
            self._tick()
            if self._eval_bool_arg(arg, env):
                return 1.0
        return 0.0

    # --- Data (Word & List) Implementations ---
    def _prim_sentence(self, args: list[Any], env: Environment, is_tail: bool) -> LogoList:
        flat: list[Any] = []
        for arg in args:
            self._tick()
            if isinstance(arg, LogoList):
                flat.extend(arg.values)
            else:
                flat.append(arg)
            if len(flat) > self._max_list_length:
                msg = f"Maximum list length ({self._max_list_length}) exceeded in SENTENCE."
                raise LogoRuntimeError(msg)
        return LogoList.from_values(flat)

    def _prim_word(self, args: list[Any], env: Environment, is_tail: bool) -> str:
        parts: list[str] = []
        total_len = 0
        for arg in args:
            self._tick()
            s = self._to_word_str(arg)
            total_len += len(s)
            if total_len > self._max_word_length:
                msg = f"Maximum word length ({self._max_word_length}) exceeded in WORD."
                raise LogoRuntimeError(msg)
            parts.append(s)
        return "".join(parts)

    def _prim_first(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        val = args[0]
        if isinstance(val, LogoList):
            if not val.values:
                msg = "FIRST cannot be applied to an empty list."
                raise LogoRuntimeError(msg)
            return val.values[0]
        s = self._to_word_str(val)
        if not s:
            msg = "FIRST cannot be applied to an empty word."
            raise LogoRuntimeError(msg)
        return s[0]

    def _prim_last(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        val = args[0]
        if isinstance(val, LogoList):
            if not val.values:
                msg = "LAST cannot be applied to an empty list."
                raise LogoRuntimeError(msg)
            return val.values[-1]
        s = self._to_word_str(val)
        if not s:
            msg = "LAST cannot be applied to an empty word."
            raise LogoRuntimeError(msg)
        return s[-1]

    def _prim_butfirst(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        val = args[0]
        if isinstance(val, LogoList):
            if not val.values:
                msg = "BUTFIRST cannot be applied to an empty list."
                raise LogoRuntimeError(msg)
            return LogoList.from_values(list(val.values[1:]))
        s = self._to_word_str(val)
        if not s:
            msg = "BUTFIRST cannot be applied to an empty word."
            raise LogoRuntimeError(msg)
        return s[1:]

    def _prim_butlast(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        val = args[0]
        if isinstance(val, LogoList):
            if not val.values:
                msg = "BUTLAST cannot be applied to an empty list."
                raise LogoRuntimeError(msg)
            return LogoList.from_values(list(val.values[:-1]))
        s = self._to_word_str(val)
        if not s:
            msg = "BUTLAST cannot be applied to an empty word."
            raise LogoRuntimeError(msg)
        return s[:-1]

    def _prim_item(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        idx = self._require_int(args[0], "ITEM")
        val = args[1]
        seq = val.values if isinstance(val, LogoList) else tuple(self._to_word_str(val))
        if idx < 1 or idx > len(seq):
            msg = f"ITEM index {idx} out of bounds (1..{len(seq)})."
            raise LogoRuntimeError(msg)
        return seq[idx - 1]

    def _prim_pick(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        val = args[0]
        seq = val.values if isinstance(val, LogoList) else tuple(self._to_word_str(val))
        if not seq:
            msg = "PICK cannot be applied to an empty list or word."
            raise LogoRuntimeError(msg)
        return seq[self._rng.randrange(len(seq))]

    def _prim_count(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        val = args[0]
        if isinstance(val, LogoList):
            return float(len(val.values))
        return float(len(self._to_word_str(val)))

    def _prim_fput(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        item, target = args[0], args[1]
        if isinstance(target, LogoList):
            if len(target.values) + 1 > self._max_list_length:
                msg = f"Maximum list length ({self._max_list_length}) exceeded in FPUT."
                raise LogoRuntimeError(msg)
            return LogoList.from_values([item, *target.values])
        prefix = self._to_word_str(item)
        if len(prefix) != 1:
            msg = "FPUT into a word requires a 1-character word."
            raise LogoRuntimeError(msg)
        base = self._to_word_str(target)
        if len(base) + 1 > self._max_word_length:
            msg = f"Maximum word length ({self._max_word_length}) exceeded in FPUT."
            raise LogoRuntimeError(msg)
        return prefix + base

    def _prim_lput(self, args: list[Any], env: Environment, is_tail: bool) -> Any:
        item, target = args[0], args[1]
        if isinstance(target, LogoList):
            if len(target.values) + 1 > self._max_list_length:
                msg = f"Maximum list length ({self._max_list_length}) exceeded in LPUT."
                raise LogoRuntimeError(msg)
            return LogoList.from_values([*target.values, item])
        suffix = self._to_word_str(item)
        if len(suffix) != 1:
            msg = "LPUT into a word requires a 1-character word."
            raise LogoRuntimeError(msg)
        base = self._to_word_str(target)
        if len(base) + 1 > self._max_word_length:
            msg = f"Maximum word length ({self._max_word_length}) exceeded in LPUT."
            raise LogoRuntimeError(msg)
        return base + suffix

    def _prim_emptyp(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        val = args[0]
        if isinstance(val, LogoList):
            return 1.0 if len(val.values) == 0 else 0.0
        return 1.0 if len(self._to_word_str(val)) == 0 else 0.0

    def _prim_numberp(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        val = args[0]
        if isinstance(val, LogoList):
            return 0.0
        try:
            self._to_number(val)
            return 1.0
        except LogoRuntimeError:
            return 0.0

    def _prim_memberp(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        needle, haystack = args[0], args[1]
        if isinstance(haystack, LogoList):
            for elem in haystack.values:
                if self._values_equal(needle, elem):
                    return 1.0
            return 0.0
        s_needle = self._to_word_str(needle).upper()
        s_haystack = self._to_word_str(haystack).upper()
        return 1.0 if s_needle in s_haystack else 0.0

    def _prim_ascii(self, args: list[Any], env: Environment, is_tail: bool) -> float:
        s = self._to_word_str(args[0])
        if not s:
            msg = "ASCII requires a non-empty word."
            raise LogoRuntimeError(msg)
        return float(ord(s[0]))

    def _prim_char(self, args: list[Any], env: Environment, is_tail: bool) -> str:
        code = self._require_int(args[0], "CHAR")
        if code < 32 or code > 126:
            msg = f"CHAR code must be printable ASCII (32..126), got {code}."
            raise LogoRuntimeError(msg)
        return chr(code)

    # --- Output Primitives ---
    def _append_output(self, line: str) -> None:
        if len(self.output) >= self._max_output_lines:
            msg = f"Maximum output lines ({self._max_output_lines}) exceeded."
            raise LogoRuntimeError(msg)
        if len(line) > self._max_word_length:
            line = line[: self._max_word_length]
        self.output.append(line)

    def _prim_print(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        text = " ".join(self._format_value(a, show_brackets=False) for a in args)
        self._append_output(text)

    def _prim_type(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        text = "".join(self._format_value(a, show_brackets=False) for a in args)
        if self.output:
            combined = self.output[-1] + text
            if len(combined) > self._max_word_length:
                msg = f"Maximum output line length ({self._max_word_length}) exceeded."
                raise LogoRuntimeError(msg)
            self.output[-1] = combined
        else:
            self._append_output(text)

    def _prim_show(self, args: list[Any], env: Environment, is_tail: bool) -> None:
        text = " ".join(self._format_value(a, show_brackets=True) for a in args)
        self._append_output(text)
