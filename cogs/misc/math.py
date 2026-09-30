from __future__ import annotations

import asyncio
import re
from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import discord
import sympy
from discord.ext import commands
from sympy import Expr
from sympy.parsing.sympy_parser import convert_xor, implicit_multiplication, parse_expr, standard_transformations

if TYPE_CHECKING:
    from core import Parrot


MAX_EXPRESSION_LENGTH = 256
MAX_OPERATION_COUNT = 500

MATH_REACTION = "\N{MEMO}"
PENDING_TIMEOUT = 10 * 60

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FUNCTION_CALL_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
ALLOWED_CHARS_RE = re.compile(r"^[A-Za-z0-9_+*/^().=\-\s]+$")
NUMBER_RE = re.compile(r"(?<![A-Za-z_])\d+(?:\.\d*)?(?:[eE][+-]?\d+)?")
OPERATOR_RE = re.compile(r"[+*/^=]|(?<!^)-")


MATH_FUNCTIONS = frozenset(
    {
        "sqrt",
        "sin",
        "cos",
        "tan",
        "log",
    }
)

MATH_CONSTANTS = frozenset(
    {
        "pi",
        "E",
    }
)

ALLOWED_FUNCTIONS = {
    "sqrt": sympy.sqrt,
    "sin": sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "log": sympy.log,
}

ALLOWED_CONSTANTS = {
    "pi": sympy.pi,
    "E": sympy.E,
}

TRANSFORMATIONS = (
    *standard_transformations,
    implicit_multiplication,
    convert_xor,
)

# parse_expr() generates calls to these names internally.
# Keeping the global namespace explicit prevents exposing SymPy's
# complete namespace.
PARSER_GLOBALS = {
    "Symbol": sympy.Symbol,
    "Integer": sympy.Integer,
    "Float": sympy.Float,
    "Rational": sympy.Rational,
    "Add": sympy.Add,
    "Mul": sympy.Mul,
    "Pow": sympy.Pow,
}


class MathParseError(ValueError):
    """Raised when user input is outside the supported math syntax."""


class EvaluationError(ValueError):
    """Raised when a parsed expression cannot be evaluated safely."""


@dataclass(frozen=True)
class Expression:
    value: sympy.Expr


@dataclass(frozen=True)
class Assignment:
    name: str
    value: sympy.Expr


@dataclass
class PendingExpression:
    message: discord.Message
    task: asyncio.Task[None] | None = None


class VariableStore(Protocol):
    """Storage interface for scoped mathematical variables."""

    def get(self, scope: Hashable) -> Mapping[str, Expr]: ...

    def set(self, scope: Hashable, name: str, value: Expr) -> None: ...


class InMemoryVariableStore:
    """In-memory storage for scoped mathematical variables."""

    def __init__(self) -> None:
        self._scopes: dict[Hashable, dict[str, Expr]] = {}

    def get(self, scope: Hashable) -> Mapping[str, Expr]:
        return self._scopes.get(scope, {})

    def set(self, scope: Hashable, name: str, value: Expr) -> None:
        self._scopes.setdefault(scope, {})[name] = value

    def clear(self, scope: Hashable) -> None:
        self._scopes.pop(scope, None)


def _validate_text(text: str) -> str:
    """Validate basic input constraints before parsing."""

    text = text.strip()

    if not text:
        msg = "Expression is empty."
        raise MathParseError(msg)

    if len(text) > MAX_EXPRESSION_LENGTH:
        msg = "Expression is too long."
        raise MathParseError(msg)

    if not ALLOWED_CHARS_RE.fullmatch(text):
        msg = "Unsupported characters."
        raise MathParseError(msg)

    if "__" in text:
        msg = "Invalid identifier."
        raise MathParseError(msg)

    return text


def _validate_operation_count(value: sympy.Expr) -> None:
    if value.count_ops() > MAX_OPERATION_COUNT:
        msg = "Expression is too complicated."
        raise MathParseError(msg)


def _parse_expression(
    text: str,
    variables: Mapping[str, sympy.Expr],
) -> sympy.Expr:
    """Parse a mathematical expression using the restricted SymPy namespace."""

    local_dict: dict[str, object] = {}
    local_dict.update(ALLOWED_FUNCTIONS)
    local_dict.update(ALLOWED_CONSTANTS)
    local_dict.update(variables)

    function_names = {match.group(1) for match in FUNCTION_CALL_RE.finditer(text)}

    for name in function_names:
        if name not in ALLOWED_FUNCTIONS:
            msg = f"Unknown function: {name}"
            raise MathParseError(msg)

    try:
        result = parse_expr(
            text,
            local_dict=local_dict,
            global_dict=PARSER_GLOBALS,
            transformations=TRANSFORMATIONS,
            evaluate=True,
        )
    except (
        ArithmeticError,
        NameError,
        SyntaxError,
        TypeError,
        ValueError,
    ) as exc:
        msg = "Invalid mathematical expression."
        raise MathParseError(msg) from exc

    if not isinstance(result, sympy.Expr):
        msg = "Expression did not produce a mathematical value."
        raise MathParseError(msg)

    try:
        _validate_operation_count(result)
    except MathParseError as exc:
        raise MathParseError(str(exc)) from exc

    return result


def parse_input(
    text: str,
    store: VariableStore,
    scope: Hashable,
) -> Expression | Assignment:
    """Parse an expression or simple variable assignment."""

    text = _validate_text(text)

    if text.count("=") > 1:
        msg = "Only simple assignments are supported."
        raise MathParseError(msg)

    variables = dict(store.get(scope))

    if "=" not in text:
        return Expression(
            value=_parse_expression(text, variables),
        )

    lhs, rhs = text.split("=", 1)
    name = lhs.strip()

    if not IDENTIFIER_RE.fullmatch(name):
        msg = "The left side of an assignment must be a variable name."
        raise MathParseError(msg)

    if name in ALLOWED_FUNCTIONS or name in ALLOWED_CONSTANTS:
        msg = f"Cannot assign to {name}."
        raise MathParseError(msg)

    if not rhs.strip():
        msg = "Assignment is missing a value."
        raise MathParseError(msg)

    value = _parse_expression(rhs, variables)

    return Assignment(
        name=name,
        value=value,
    )


def _format_value(value: sympy.Expr) -> str:
    if value.count_ops() > MAX_OPERATION_COUNT:
        msg = "Expression is too complicated."
        raise EvaluationError(msg)

    return sympy.sstr(value)


def evaluate_input(
    text: str,
    store: VariableStore,
    scope: Hashable,
) -> str:
    """Parse, evaluate, store assignments, and return a Discord-ready result."""

    try:
        result = parse_input(text, store, scope)
    except MathParseError as exc:
        raise EvaluationError(str(exc)) from exc

    if isinstance(result, Assignment):
        store.set(scope, result.name, result.value)
        return f"{result.name} = {_format_value(result.value)}"

    return _format_value(result.value)


def looks_like_math(text: str) -> bool:
    """Return whether text plausibly looks like a supported expression."""

    text = text.strip()

    if not text or len(text) > MAX_EXPRESSION_LENGTH:
        return False

    if not ALLOWED_CHARS_RE.fullmatch(text):
        return False

    if text.count("=") > 1:
        return False

    if "=" in text:
        lhs, rhs = text.split("=", 1)

        if not IDENTIFIER_RE.fullmatch(lhs.strip()):
            return False

        if not rhs.strip():
            return True

    function_names = {match.group(1) for match in FUNCTION_CALL_RE.finditer(text)}

    if any(name not in MATH_FUNCTIONS for name in function_names):
        return False

    identifiers = set(IDENTIFIER_RE.findall(text))
    identifiers -= MATH_FUNCTIONS | MATH_CONSTANTS

    has_numeric_literal = bool(NUMBER_RE.search(text))
    has_operator = bool(OPERATOR_RE.search(text))

    # Reject ordinary prose such as:
    # "I ate 25 apples"
    #
    # Short variable names such as x, y, xy are allowed because they are
    # much less likely to be ordinary prose.
    if identifiers and not has_numeric_literal and not function_names and not all(len(name) <= 2 for name in identifiers):
        return False

    if has_numeric_literal or function_names or has_operator:
        return True

    # Parenthesized expressions such as "(x)" are also plausible math.
    return "(" in text and ")" in text


class Math(commands.Cog):
    """Reaction-triggered inline mathematical expressions."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.store = InMemoryVariableStore()
        self.pending: dict[int, PendingExpression] = {}

    def cog_unload(self) -> None:
        for pending in self.pending.values():
            if pending.task is not None:
                pending.task.cancel()

        self.pending.clear()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        if not looks_like_math(message.content):
            return

        try:
            await message.add_reaction(MATH_REACTION)
        except discord.Forbidden, discord.HTTPException:
            return

        pending = PendingExpression(message=message)
        pending.task = asyncio.create_task(self._expire(message.id))

        self.pending[message.id] = pending

    @commands.Cog.listener()
    async def on_reaction_add(
        self,
        reaction: discord.Reaction,
        user: discord.User | discord.Member,
    ) -> None:
        if user.bot or str(reaction.emoji) != MATH_REACTION:
            return

        pending = self.pending.pop(
            reaction.message.id,
            None,
        )

        if pending is None:
            return

        if pending.task is not None:
            pending.task.cancel()

        result = self._evaluate(
            pending.message.content,
            user.id,
        )

        await pending.message.reply(
            result,
            mention_author=False,
        )

    async def _expire(self, message_id: int) -> None:
        try:
            await asyncio.sleep(PENDING_TIMEOUT)
        except asyncio.CancelledError:
            return

        self.pending.pop(message_id, None)

    def _evaluate(
        self,
        text: str,
        user_id: int,
    ) -> str:
        try:
            result = evaluate_input(
                text,
                self.store,
                user_id,
            )
        except EvaluationError as exc:
            return f"Math error: {exc}"

        if "=" in text:
            return result

        return f"{text.strip()} = {result}"


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Math(bot))
