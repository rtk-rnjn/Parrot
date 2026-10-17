from __future__ import annotations

import asyncio
import contextvars
import dataclasses
import functools
import re
import secrets
import time
from typing import Any

from jinja2 import StrictUndefined, TemplateSyntaxError, nodes, pass_eval_context
from jinja2.sandbox import ImmutableSandboxedEnvironment
from jinja2.visitor import NodeVisitor

__all__ = [
    "SandboxConfig",
    "SandboxForbiddenSyntax",
    "SandboxInternalError",
    "SandboxMemoryExceeded",
    "SandboxOperatorLimitExceeded",
    "SandboxOutputLimitExceeded",
    "SandboxRenderError",
    "SandboxSecurityViolation",
    "SandboxTemplateSyntaxError",
    "SandboxTimeoutExceeded",
    "render_sandboxed",
    "validate_template",
]


class SandboxRenderError(Exception):
    pass


class SandboxTemplateSyntaxError(SandboxRenderError):
    pass


class SandboxSecurityViolation(SandboxRenderError):
    pass


class SandboxOutputLimitExceeded(SandboxRenderError):
    pass


class SandboxOperatorLimitExceeded(SandboxRenderError):
    pass


class SandboxTimeoutExceeded(SandboxRenderError):
    pass


class SandboxMemoryExceeded(SandboxRenderError):
    pass


class SandboxInternalError(SandboxRenderError):
    pass


class SandboxForbiddenSyntax(SandboxRenderError):
    def __init__(self, message: str, *, line: int | None = None):
        super().__init__(message)
        self.line = line


@dataclasses.dataclass(frozen=True)
class SandboxConfig:
    max_output_bytes: int = 256 * 1024
    max_sequence_repeat: int = 10_000
    max_combined_sequence_length: int = 100_000
    max_operand_length: int = 256
    max_int_bits: int = 1024

    allow_power_operator: bool = False
    max_exponent: int = 32
    max_power_base_abs: int = 1_000_000

    wall_timeout_seconds: float = 1.5
    max_loop_steps: int = 20_000
    max_template_chars: int = 100_000
    output_encoding: str = "utf-8"

    def validate(self) -> None:
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value <= 0:
                msg = f"{field.name} must be > 0"
                raise ValueError(msg)


class RestrictedNodeVisitor(NodeVisitor):
    FORBIDDEN_NODES = {  # noqa: RUF012
        nodes.Extends: "extends",
        nodes.Include: "include",
        nodes.Import: "import",
        nodes.FromImport: "from import",
    }

    def generic_visit(self, node: nodes.Node, *args: Any, **kwargs: Any):
        forbidden = self.FORBIDDEN_NODES.get(type(node))
        if forbidden is not None:
            error = f"{forbidden!r} is disabled"
            raise SandboxForbiddenSyntax(error, line=getattr(node, "lineno", None))
        return super().generic_visit(node, *args, **kwargs)


_TICK_NAME = f"_t{secrets.token_hex(6)}"
_BAD_FORMAT = re.compile(r"\{[^{}]*:[^{}]*(?:\d{6,}|\{)")
_PAD_METHODS = frozenset({"center", "ljust", "rjust", "zfill"})
SEQUENCE_TYPES = (str, bytes, tuple, list)
DISABLED_FILTERS = ("center", "indent", "format", "batch", "slice")


@dataclasses.dataclass
class _Budget:
    deadline: float
    steps: int = 0


_budget: contextvars.ContextVar[_Budget | None] = contextvars.ContextVar("sandbox_budget", default=None)


class HardenedSandboxedEnvironment(ImmutableSandboxedEnvironment):
    intercepted_binops = frozenset({"*", "**", "+", "%"})

    def __init__(self, config: SandboxConfig, **kwargs: Any):
        super().__init__(undefined=StrictUndefined, **kwargs)
        self._cfg = config
        self.globals = {_TICK_NAME: self._tick}
        for name in DISABLED_FILTERS:
            self.filters.pop(name, None)
        self.filters["replace"] = self._filter_replace
        self.filters["join"] = self._guard_join(self.filters["join"])

    def _tick(self) -> None:
        budget = _budget.get()
        if budget is None:
            return
        budget.steps += 1
        if budget.steps > self._cfg.max_loop_steps:
            msg = "template exceeded the loop/macro step limit"
            raise SandboxOperatorLimitExceeded(msg)
        if time.monotonic() > budget.deadline:
            msg = "template took too long to render"
            raise SandboxTimeoutExceeded(msg)

    def _operand_too_long(self, value: Any) -> bool:
        return isinstance(value, SEQUENCE_TYPES) and len(value) > self._cfg.max_operand_length

    def _filter_replace(self, value: Any, old: Any, new: Any, count: int | None = None) -> str:
        if self._operand_too_long(new):
            msg = "replacement text exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        res = str(value).replace(str(old), str(new), -1 if count is None else int(count))
        if len(res) > self._cfg.max_combined_sequence_length:
            msg = "replacement result exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        return res

    def _guard_join(self, original: Any) -> Any:
        @pass_eval_context
        def do_join(eval_ctx: Any, value: Any, d: Any = "", attribute: Any = None) -> Any:
            if self._operand_too_long(d):
                msg = "join separator exceeds configured limit"
                raise SandboxOperatorLimitExceeded(msg)
            res = original(eval_ctx, value, d, attribute)
            if isinstance(res, SEQUENCE_TYPES) and len(res) > self._cfg.max_combined_sequence_length:
                msg = "join result exceeds configured limit"
                raise SandboxOperatorLimitExceeded(msg)
            return res

        return do_join

    def _guard_text_call(self, owner: str | bytes, name: str, args: tuple[Any, ...]) -> None:
        cfg = self._cfg
        first_int = args[0] if args and isinstance(args[0], int) else 0
        violated = (
            (name == "replace" and len(args) > 1 and self._operand_too_long(args[1]))
            or (name == "join" and len(owner) > cfg.max_operand_length)
            or (name in _PAD_METHODS and first_int > cfg.max_combined_sequence_length)
            or (name == "expandtabs" and first_int > cfg.max_operand_length)
        )
        if violated:
            msg = f"arguments to {name}() exceed configured limits"
            raise SandboxOperatorLimitExceeded(msg)

    def wrap_str_format(self, value: Any) -> Any:
        wrapped = super().wrap_str_format(value)
        if wrapped is None:
            return None
        owner = getattr(value, "__self__", None)
        if isinstance(owner, str) and _BAD_FORMAT.search(owner) is not None:
            msg = "format width/precision exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        return wrapped

    def call(self, context: Any, obj: Any, /, *args: Any, **kwargs: Any) -> Any:
        owner = getattr(obj, "__self__", None)
        if isinstance(owner, (str, bytes)):
            self._guard_text_call(owner, getattr(obj, "__name__", ""), args)
        result = super().call(context, obj, *args, **kwargs)
        if isinstance(result, SEQUENCE_TYPES) and len(result) > self._cfg.max_combined_sequence_length:
            msg = "result length exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        return result

    def call_binop(self, context: Any, operator: str, left: Any, right: Any) -> Any:
        if operator == "*":
            return self._safe_mul(left, right)
        if operator == "**":
            return self._safe_pow(left, right)
        if operator == "+":
            return self._safe_add(left, right)
        if operator == "%":
            return self._safe_mod(left, right)
        return super().call_binop(context, operator, left, right)

    def _safe_mul(self, left: Any, right: Any) -> Any:
        if isinstance(left, SEQUENCE_TYPES) and isinstance(right, int):
            self._check_repeat_limits(len(left), right)
        elif isinstance(right, SEQUENCE_TYPES) and isinstance(left, int):
            self._check_repeat_limits(len(right), left)
        elif isinstance(left, int) and isinstance(right, int) and left.bit_length() + right.bit_length() > self._cfg.max_int_bits:
            msg = "integer result exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)

        return left * right  # type: ignore[operator]

    def _check_repeat_limits(self, unit_len: int, repeat: int) -> None:
        if repeat < 0:
            return
        if repeat > self._cfg.max_sequence_repeat:
            msg = "sequence repeat exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        if unit_len * repeat > self._cfg.max_combined_sequence_length:
            msg = "sequence result length exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)

    def _safe_pow(self, left: Any, right: Any) -> Any:
        if not self._cfg.allow_power_operator:
            msg = "power operator is disabled"
            raise SandboxOperatorLimitExceeded(msg)
        if not isinstance(left, int) or not isinstance(right, int):
            msg = "power only allowed for integers"
            raise SandboxOperatorLimitExceeded(msg)
        if abs(right) > self._cfg.max_exponent:
            msg = "exponent exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        if abs(left) > self._cfg.max_power_base_abs:
            msg = "base exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        return left**right

    def _safe_add(self, left: Any, right: Any) -> Any:
        if (
            isinstance(left, SEQUENCE_TYPES)
            and isinstance(right, SEQUENCE_TYPES)
            and type(left) is type(right)
            and (len(left) + len(right) > self._cfg.max_combined_sequence_length)
        ):
            msg = "concatenation result exceeds configured limit"
            raise SandboxOperatorLimitExceeded(msg)
        return left + right  # type: ignore[operator]

    def _safe_mod(self, left: Any, right: Any) -> Any:
        if isinstance(left, (str, bytes)):
            msg = "string formatting with % is disabled"
            raise SandboxSecurityViolation(msg)
        return left % right


config = SandboxConfig()
config.validate()
env = HardenedSandboxedEnvironment(
    config,
    loader=None,
    autoescape=False,
    extensions=["jinja2.ext.do"],
    enable_async=True,
    auto_reload=False,
)


@functools.lru_cache(maxsize=256)
def _compile(code: str):
    if len(code) > config.max_template_chars:
        msg = f"template is longer than {config.max_template_chars} characters"
        raise SandboxTemplateSyntaxError(msg)

    try:
        tree = env.parse(code)
    except TemplateSyntaxError as error:
        msg = f"line {error.lineno}: {error.message}"
        raise SandboxTemplateSyntaxError(msg) from error

    try:
        RestrictedNodeVisitor().visit(tree)
    except SandboxForbiddenSyntax as error:
        msg = f"line {error.line}: {error}" if error.line else str(error)
        raise SandboxForbiddenSyntax(msg, line=error.line) from error

    for node in list(tree.find_all((nodes.For, nodes.Macro, nodes.CallBlock))):
        tick = nodes.ExprStmt(nodes.Call(nodes.Name(_TICK_NAME, "load"), [], [], None, None))
        tick.set_lineno(node.lineno)
        tick.set_environment(env)
        node.body.insert(0, tick)

    return env.from_string(tree)


def validate_template(code: str) -> None:
    _compile(code)


async def _collect(template: Any, context: dict[str, Any]) -> str:
    parts: list[str] = []
    size = 0
    async for chunk in template.generate_async(context):
        size += len(chunk.encode(config.output_encoding))
        if size > config.max_output_bytes:
            msg = "template output is too large"
            raise SandboxOutputLimitExceeded(msg)
        parts.append(chunk)
    return "".join(parts)


async def render_sandboxed(code: str, **context: Any) -> str:
    config.validate()
    template = _compile(code)

    token = _budget.set(_Budget(deadline=time.monotonic() + config.wall_timeout_seconds))
    try:
        return await asyncio.wait_for(_collect(template, context), config.wall_timeout_seconds)
    except TimeoutError as error:
        msg = "template took too long to render"
        raise SandboxTimeoutExceeded(msg) from error
    finally:
        _budget.reset(token)
