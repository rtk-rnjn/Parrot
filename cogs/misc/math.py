from __future__ import annotations

import asyncio
import contextlib
import keyword
import logging
import re
from collections import OrderedDict
from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import discord
import mpmath
import sympy
from discord.ext import commands
from sympy import Expr, Integer
from sympy.parsing.sympy_parser import auto_number, auto_symbol, convert_xor, implicit_multiplication, parse_expr

if TYPE_CHECKING:
    from core import Parrot

log = logging.getLogger(__name__)

MAX_EXPRESSION_LENGTH = 256  # characters accepted by the parser
MAX_DETECT_LENGTH = 120  # characters accepted by the detector (stricter)
MAX_TOKENS = 120
MAX_PAREN_DEPTH = 12
MAX_LITERAL_DIGITS = 30
MAX_OPERATION_COUNT = 500  # size of a *result* expression
MAX_RESULT_CHARS = 500
MAX_POWER_BITS = 10_000  # refuse a ** b when the result would exceed this many bits
MAX_EXACT_INTEGER_BITS = 1_000  # bigger integers are shown in scientific notation
MAX_VARIABLES_PER_SCOPE = 50
MAX_SCOPES = 10_000
EVALUATION_TIMEOUT = 5.0  # seconds

MATH_REACTION = "\N{MEMO}"
PENDING_TIMEOUT = 10 * 60  # seconds a flagged message stays evaluable
ONLY_AUTHOR_CAN_EVALUATE = True


class MathError(ValueError):
    """Base class. The message is always safe to show to users."""


class MathParseError(MathError):
    """Raised when user input is outside the supported math syntax."""


class EvaluationError(MathError):
    """Raised when a parsed expression cannot be evaluated safely."""


def _guarded(function):
    """Wrap a SymPy function so its arguments pass the size guard first.

    ``parse_expr(evaluate=False)`` only defers *operators*; function calls such
    as ``sqrt(...)`` would still evaluate their (unevaluated) arguments while the
    text is being parsed, i.e. before any guard has run.
    """

    def call(*args: Expr, **_ignored: object) -> Expr:
        return function(*(_evaluate_tree(arg) for arg in args))

    return call


FUNCTIONS = {
    name: _guarded(function)
    for name, function in {
        "sqrt": sympy.sqrt,
        "sin": sympy.sin,
        "cos": sympy.cos,
        "tan": sympy.tan,
        "asin": sympy.asin,
        "acos": sympy.acos,
        "atan": sympy.atan,
        "sinh": sympy.sinh,
        "cosh": sympy.cosh,
        "tanh": sympy.tanh,
        "exp": sympy.exp,
        "log": sympy.log,  # natural log; log(x, base) is also accepted
        "ln": sympy.log,
        "log10": lambda x: sympy.log(x, 10),
        "abs": sympy.Abs,
        "floor": sympy.floor,
        "ceil": sympy.ceiling,
    }.items()
}

CONSTANTS = {
    "pi": sympy.pi,
    "E": sympy.E,
}

# Names parse_expr() emits internally. They are exposed to the parser but users
# may not type them.
PARSER_GLOBALS: dict[str, object] = {
    "__builtins__": {},
    "Symbol": sympy.Symbol,
    "Integer": sympy.Integer,
    "Float": sympy.Float,
    "Rational": sympy.Rational,
    "Add": sympy.Add,
    "Mul": sympy.Mul,
    "Pow": sympy.Pow,
}
_INTERNAL_NAMES = frozenset(PARSER_GLOBALS) - {"__builtins__"}

# Implicit multiplication (2x, 3(x + 1), (x + 1)(x - 1), 2pi) is enabled.
# Splitting of names (xy -> x*y) is deliberately *not*: ``xy`` is one variable.
TRANSFORMATIONS = (auto_symbol, auto_number, convert_xor, implicit_multiplication)


NUM, NAME, OP = "num", "name", "op"
Token = tuple[str, str]

_TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(?P<num>\d+(?:\.\d*)?|\.\d+)"
    r"|(?P<name>[A-Za-z][A-Za-z0-9]*)"
    r"|(?P<op>\*\*|[-+*/^(),=])"
    r")",
)


def tokenize(text: str) -> list[Token]:
    """Split text into tokens, rejecting any character outside the grammar.

    The parser rebuilds its input from these tokens, so nothing that is not
    listed above (``.`` attribute access, ``_``, brackets, quotes, ``;`` ...)
    can ever reach SymPy's ``parse_expr``.
    """

    text = text.strip()
    tokens: list[Token] = []
    position = 0

    while position < len(text):
        match = _TOKEN_RE.match(text, position)

        if match is None:
            character = text[position:].lstrip()[0]
            msg = f"Unsupported character {character!r}."
            raise MathParseError(msg)

        kind = match.lastgroup
        tokens.append((kind, match.group(kind)))  # type: ignore[arg-type]
        position = match.end()

    return tokens


_VARIABLE_RE = re.compile(r"[A-Za-z][0-9]*")  # x, y, x1 -- but not words
_DATE_OR_RANGE_RE = re.compile(r"\d+(?:[-/]\d+)+")  # 3-4, 24/7, 2024-01-05
_BINARY_OPERATORS = frozenset({"+", "-", "*", "/", "^", "**"})


def _is_variable(name: str, known: frozenset[str]) -> bool:
    if name in FUNCTIONS or name in CONSTANTS:
        return False

    return name in known or _VARIABLE_RE.fullmatch(name) is not None


def _plausible_shape(tokens: list[Token], known: frozenset[str]) -> bool:  # noqa: PLR0911
    """Check that tokens form something expression-shaped (not that it parses)."""

    if not tokens:
        return False

    depth = 0
    previous: Token | None = None

    for index, (kind, token) in enumerate(tokens):
        following = tokens[index + 1][1] if index + 1 < len(tokens) else None

        if kind == NAME:
            if token in FUNCTIONS:
                if following != "(":
                    return False
            elif token in CONSTANTS or _is_variable(token, known):
                if following == "(":
                    return False
            else:
                return False  # an ordinary word
        elif token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
            if depth < 0:
                return False
        elif token == ",":
            if depth == 0:
                return False
        elif token == "=":
            return False

        # Two operands in a row are only plausible as implicit multiplication
        # of a number ("2x", "2pi"); "x 5" or "3 4" are prose.
        if previous is not None and kind in {NUM, NAME} and previous[0] in {NUM, NAME} and previous[0] != NUM:
            return False

        if previous is not None and kind == NUM and previous[0] == NUM:
            return False

        previous = (kind, token)

    if depth != 0:
        return False

    start = 1 if tokens[0][1] in {"+", "-"} else 0

    if start >= len(tokens):
        return False

    start_kind, start_token = tokens[start]
    end_kind, end_token = tokens[-1]

    return (start_kind in {NUM, NAME} or start_token == "(") and (end_kind in {NUM, NAME} or end_token == ")")


def _has_math_signal(tokens: list[Token]) -> bool:
    """A function call, or a binary operator between two operands."""

    for index, (kind, token) in enumerate(tokens):
        if kind == NAME and token in FUNCTIONS:
            return True

        if token in _BINARY_OPERATORS and index > 0:
            previous_kind, previous_token = tokens[index - 1]

            if previous_kind in {NUM, NAME} or previous_token == ")":
                return True

    return False


def looks_like_math(text: str, known_names: Iterable[str] = ()) -> bool:  # noqa: PLR0911
    """Return whether text plausibly is a supported expression or assignment.

    Deliberately conservative: a false positive costs everybody a stray reaction,
    a false negative costs one person an extra command. Words are never accepted
    unless they are supported functions/constants or a variable the caller
    already knows about (``known_names``); single letters (``x``, ``y2``) are.
    """

    text = text.strip()

    if not text or len(text) > MAX_DETECT_LENGTH or "\n" in text:
        return False

    if _DATE_OR_RANGE_RE.fullmatch(text):
        return False

    try:
        tokens = tokenize(text)
    except MathParseError:
        return False

    known = frozenset(known_names)
    equals = [index for index, (_, token) in enumerate(tokens) if token == "="]

    if len(equals) > 1:
        return False

    if equals:
        index = equals[0]
        lhs, rhs = tokens[:index], tokens[index + 1 :]

        return len(lhs) == 1 and lhs[0][0] == NAME and _is_variable(lhs[0][1], known) and _plausible_shape(rhs, known)

    if not _plausible_shape(tokens, known) or not _has_math_signal(tokens):
        return False

    has_function = any(kind == NAME and token in FUNCTIONS for kind, token in tokens)

    # "n/a", "w/o", "a-b": letters glued together by one operator are usually
    # abbreviations, not algebra. Digits, spaces, parentheses, powers, or a real
    # function call make the intent clearer.
    return bool(
        has_function or "**" in text or re.search(r"[\d\s^(]", text),
    )


@dataclass(frozen=True)
class Expression:
    value: Expr  # unevaluated tree
    source: str


@dataclass(frozen=True)
class Assignment:
    name: str
    value: Expr


def _validate_tokens(tokens: list[Token]) -> None:
    if not tokens:
        msg = "Expression is empty."
        raise MathParseError(msg)

    if len(tokens) > MAX_TOKENS:
        msg = "Expression is too complicated."
        raise MathParseError(msg)

    depth = 0

    for index, (kind, token) in enumerate(tokens):
        following = tokens[index + 1][1] if index + 1 < len(tokens) else None

        if kind == NUM:
            if sum(character.isdigit() for character in token) > MAX_LITERAL_DIGITS:
                msg = "Number is too long."
                raise MathParseError(msg)
        elif kind == NAME:
            if token in FUNCTIONS:
                if following != "(":
                    msg = f"{token} needs parentheses, e.g. {token}(x)."
                    raise MathParseError(msg)
            elif following == "(":
                msg = f"Unknown function: {token}. (Use * for multiplication.)"
                raise MathParseError(msg)
            elif token in _INTERNAL_NAMES or keyword.iskeyword(token):
                msg = f"{token!r} is not a valid name."
                raise MathParseError(msg)
        elif token == "(":
            depth += 1

            if depth > MAX_PAREN_DEPTH:
                msg = "Expression is nested too deeply."
                raise MathParseError(msg)
        elif token == ")":
            depth -= 1

            if depth < 0:
                msg = "Unbalanced parentheses."
                raise MathParseError(msg)

    if depth:
        msg = "Unbalanced parentheses."
        raise MathParseError(msg)

    last_kind, last_token = tokens[-1]

    if last_kind == OP and last_token != ")":
        msg = f"Expression is incomplete: it ends with {last_token!r}."
        raise MathParseError(msg)


def _build(tokens: list[Token], variables: Mapping[str, Expr]) -> Expr:
    """Turn validated tokens into an *unevaluated* SymPy tree."""

    _validate_tokens(tokens)

    source = " ".join(token for _, token in tokens)
    local_dict: dict[str, object] = {**variables, **FUNCTIONS, **CONSTANTS}

    try:
        result = parse_expr(
            source,
            local_dict=local_dict,
            global_dict=dict(PARSER_GLOBALS),
            transformations=TRANSFORMATIONS,
            evaluate=False,
        )
    except MathError:
        raise
    except RecursionError:
        msg = "Expression is nested too deeply."
        raise MathParseError(msg) from None
    except Exception as exc:
        msg = "Invalid mathematical expression."
        raise MathParseError(msg) from exc

    if not isinstance(result, Expr):
        msg = "That is not a complete mathematical expression."
        raise MathParseError(msg)

    return result


def parse_input(text: str, variables: Mapping[str, Expr]) -> Expression | Assignment:
    """Parse an expression or a simple ``name = expression`` assignment."""

    text = text.strip()

    if not text:
        msg = "Expression is empty."
        raise MathParseError(msg)

    if len(text) > MAX_EXPRESSION_LENGTH:
        msg = "Expression is too long."
        raise MathParseError(msg)

    tokens = tokenize(text)
    equals = [index for index, (_, token) in enumerate(tokens) if token == "="]

    if len(equals) > 1:
        msg = "Only simple assignments are supported."
        raise MathParseError(msg)

    if not equals:
        return Expression(_build(tokens, variables), source=text)

    index = equals[0]
    lhs, rhs = tokens[:index], tokens[index + 1 :]

    if len(lhs) != 1 or lhs[0][0] != NAME:
        msg = "The left side of an assignment must be a single variable name."
        raise MathParseError(msg)

    name = lhs[0][1]

    if name in FUNCTIONS or name in CONSTANTS or name in _INTERNAL_NAMES or keyword.iskeyword(name):
        msg = f"Cannot assign to {name}."
        raise MathParseError(msg)

    if not rhs:
        msg = "Assignment is missing a value."
        raise MathParseError(msg)

    return Assignment(name, _build(rhs, variables))


def _check_power(base: Integer, exponent: Integer) -> None:
    """Refuse exact powers that would produce absurdly large integers."""

    if not (base.is_Rational and exponent.is_Rational) or base in {0, 1, -1}:
        return

    bits = max(abs(base.p).bit_length(), base.q.bit_length())

    if abs(exponent.p) * bits > MAX_POWER_BITS * exponent.q:
        msg = "Result is too large to compute."
        raise EvaluationError(msg)


def _evaluate_tree(expression: Expr) -> Expr:
    """Evaluate bottom-up, checking every power *before* SymPy computes it."""

    if not expression.args:
        return expression

    args = tuple(_evaluate_tree(arg) for arg in expression.args)

    if isinstance(expression, sympy.Pow):
        _check_power(*args)

    return expression.func(*args)


def _validate_result(value: Expr) -> None:
    if value.has(sympy.nan):
        msg = "Undefined result."
        raise EvaluationError(msg)

    if value.has(sympy.zoo):
        msg = "Division by zero (or undefined result)."
        raise EvaluationError(msg)

    if value.count_ops() > MAX_OPERATION_COUNT:
        msg = "Result is too complicated."
        raise EvaluationError(msg)


def _number(value: Expr) -> str:
    """Format a numeric value with 12 significant digits."""

    return str(mpmath.nstr(sympy.N(value, 15), 12))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("**", "^"))


def _render(value: Integer) -> tuple[str | None, str | None]:
    """Return ``(exact, approximation)``; either may be ``None``."""

    if value.is_Float:
        return _number(value), None

    if value.is_Integer and value.p.bit_length() > MAX_EXACT_INTEGER_BITS:
        return None, _number(value)

    try:
        exact = sympy.sstr(value).replace("**", "^")
    except ValueError:  # Python's int -> str digit limit inside a bigger expression
        msg = "Result is too large to display."
        raise EvaluationError(msg) from None

    if len(exact) > MAX_RESULT_CHARS:
        msg = "Result is too long to display."
        raise EvaluationError(msg)

    approximation = None

    if not value.free_symbols and not value.is_Integer and value.is_real:
        try:
            approximation = _number(value)
        except Exception:
            approximation = None

    return exact, approximation


def _join(lhs: str, exact: str | None, approximation: str | None) -> str:
    if exact is None:
        return f"{lhs} \N{ALMOST EQUAL TO} {approximation}"

    if approximation is None:
        return f"{lhs} = {exact}"

    return f"{lhs} = {exact} \N{ALMOST EQUAL TO} {approximation}"


@dataclass(frozen=True)
class Evaluation:
    text: str
    assignment: Assignment | None = None


def evaluate_input(text: str, variables: Mapping[str, Expr]) -> Evaluation:
    """Parse and evaluate ``text``. Pure: it never mutates ``variables``.

    Raises ``MathError`` (safe to show) for anything the user got wrong.

    Future commands (``simplify:``, ``factor:``, ``solve:``, ``graph:`` ...) fit
    here: split a ``command:`` prefix off in ``parse_input`` and dispatch on it
    below, reusing the same tokenizer, variables and guards.
    """

    parsed = parse_input(text, variables)
    value = _evaluate_tree(parsed.value)
    _validate_result(value)
    exact, approximation = _render(value)

    if isinstance(parsed, Assignment):
        if sympy.Symbol(parsed.name) in value.free_symbols:
            msg = f"{parsed.name} cannot be defined in terms of itself."
            raise EvaluationError(msg)

        return Evaluation(
            _join(parsed.name, exact, approximation),
            Assignment(parsed.name, value),
        )

    if exact is not None and approximation is None and _compact(exact) == _compact(parsed.source):
        names = ", ".join(sorted(symbol.name for symbol in value.free_symbols))
        note = f"  (already simplified; undefined: {names})" if names else ""
        return Evaluation(exact + note)

    return Evaluation(_join(parsed.source, exact, approximation))


class VariableStore(Protocol):
    """Storage interface for scoped mathematical variables."""

    def get(self, scope: Hashable) -> Mapping[str, Expr]: ...

    def set(self, scope: Hashable, name: str, value: Expr) -> None: ...


class InMemoryVariableStore:
    """Bounded in-memory store. Scopes are opaque keys; variables are lost on restart."""

    def __init__(
        self,
        *,
        max_scopes: int = MAX_SCOPES,
        max_variables: int = MAX_VARIABLES_PER_SCOPE,
    ) -> None:
        self._scopes: OrderedDict[Hashable, dict[str, Expr]] = OrderedDict()
        self._max_scopes = max_scopes
        self._max_variables = max_variables

    def get(self, scope: Hashable) -> Mapping[str, Expr]:
        variables = self._scopes.get(scope)

        if variables is None:
            return {}

        self._scopes.move_to_end(scope)
        return dict(variables)  # a copy: safe to hand to a worker thread

    def set(self, scope: Hashable, name: str, value: Expr) -> None:
        variables = self._scopes.get(scope)

        if variables is None:
            variables = self._scopes[scope] = {}

            while len(self._scopes) > self._max_scopes:
                self._scopes.popitem(last=False)
        elif name not in variables and len(variables) >= self._max_variables:
            msg = f"Variable limit reached ({self._max_variables})."
            raise EvaluationError(msg)

        variables[name] = value
        self._scopes.move_to_end(scope)

    def clear(self, scope: Hashable) -> None:
        self._scopes.pop(scope, None)


class Math(commands.Cog):
    """Reaction-triggered inline mathematical expressions."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.store: VariableStore = InMemoryVariableStore()
        self._busy: set[int] = set()

    @staticmethod
    def _scope(guild_id: int | None, channel_id: int, user_id: int) -> Hashable:
        """Who owns a set of variables. This is the *only* place that decides it.

        Alternatives: ``("guild", guild_id)``, ``("channel", channel_id)`` or
        ``("guild-user", guild_id, user_id)``.
        """

        return ("user", user_id)

    async def _calculate(self, content: str, scope: Hashable) -> str:
        """Evaluate ``content`` in ``scope`` and return the Discord reply text."""

        variables = self.store.get(scope)

        try:
            evaluation = await asyncio.wait_for(
                asyncio.to_thread(evaluate_input, content, variables),
                timeout=EVALUATION_TIMEOUT,
            )

            # Committed here, on the event loop, and only after success, so a
            # timed-out worker thread can never change anybody's variables.
            if evaluation.assignment is not None:
                self.store.set(scope, evaluation.assignment.name, evaluation.assignment.value)
        except MathError as exc:
            return f"Math error: {exc}"
        except TimeoutError:
            return "Math error: that took too long to evaluate."
        except Exception:
            log.exception("Unexpected error while evaluating %r", content)
            return "Math error: could not evaluate that expression."

        return f"`{evaluation.text}`"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        scope = self._scope(message.guild.id, message.channel.id, message.author.id)

        if not looks_like_math(message.content, self.store.get(scope).keys()):
            return

        try:
            await message.add_reaction(MATH_REACTION)
        except discord.Forbidden, discord.HTTPException:
            return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or str(payload.emoji) != MATH_REACTION:
            return

        if self.bot.user is None or payload.user_id == self.bot.user.id:
            return

        if payload.message_id in self._busy:
            return

        self._busy.add(payload.message_id)

        try:
            await self._handle_reaction(payload)
        finally:
            self._busy.discard(payload.message_id)

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent) -> None:
        channel = self.bot.get_partial_messageable(payload.channel_id, guild_id=payload.guild_id)

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException:
            return

        # Only messages this bot flagged. Survives restarts and uncached messages.
        if not any(str(reaction.emoji) == MATH_REACTION and reaction.me for reaction in message.reactions):
            return

        if ONLY_AUTHOR_CAN_EVALUATE and payload.user_id != message.author.id:
            return

        age = discord.utils.utcnow() - message.created_at

        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction(MATH_REACTION, self.bot.user)

        if age.total_seconds() > PENDING_TIMEOUT:
            return

        scope = self._scope(payload.guild_id, payload.channel_id, message.author.id)
        reply = await self._calculate(message.content, scope)

        try:
            await message.reply(reply, mention_author=False)
        except discord.HTTPException:
            return


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Math(bot))
