from __future__ import annotations

import dataclasses
from typing import Any

from jinja2 import StrictUndefined, nodes
from jinja2.sandbox import ImmutableSandboxedEnvironment
from jinja2.visitor import NodeVisitor

__all__ = [
    "SandboxConfig",
    "SandboxErrorInfo",
    "SandboxRenderError",
    "SandboxTemplateSyntaxError",
    "SandboxSecurityViolation",
    "SandboxOutputLimitExceeded",
    "SandboxOperatorLimitExceeded",
    "SandboxTimeoutExceeded",
    "SandboxMemoryExceeded",
    "SandboxInternalError",
    "SandboxForbiddenSyntax",
    "render_sandboxed",
    "format_sandbox_error",
]


class SandboxRenderError(Exception):
    def __init__(self, message: str, *, info: SandboxErrorInfo | None = None):
        super().__init__(message)
        self.info = info


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
class SandboxErrorInfo:
    error_type: str
    message: str
    template_name: str | None = None
    line: int | None = None
    column: int | None = None
    source_line: str | None = None
    traceback: str | None = None
    kind: str = "internal"  # syntax|security|operator_limit|output_limit|timeout|memory|internal|forbidden_syntax
    node_type: str | None = None  # best-effort AST node at error line


@dataclasses.dataclass(frozen=True)
class SandboxConfig:
    max_output_bytes: int = 256 * 1024
    max_sequence_repeat: int = 10_000
    max_combined_sequence_length: int = 100_000

    allow_power_operator: bool = False
    max_exponent: int = 32
    max_power_base_abs: int = 1_000_000

    wall_timeout_seconds: float = 1.5
    max_template_chars: int = 100_000
    output_encoding: str = "utf-8"

    max_memory_bytes: int = 256 * 1024 * 1024

    def validate(self) -> None:
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be > 0")
        if self.max_sequence_repeat <= 0:
            raise ValueError("max_sequence_repeat must be > 0")
        if self.max_combined_sequence_length <= 0:
            raise ValueError("max_combined_sequence_length must be > 0")
        if self.max_exponent <= 0:
            raise ValueError("max_exponent must be > 0")
        if self.max_power_base_abs <= 0:
            raise ValueError("max_power_base_abs must be > 0")
        if self.wall_timeout_seconds <= 0:
            raise ValueError("wall_timeout_seconds must be > 0")
        if self.max_template_chars <= 0:
            raise ValueError("max_template_chars must be > 0")
        if self.max_memory_bytes <= 0:
            raise ValueError("max_memory_bytes must be > 0")


@dataclasses.dataclass(frozen=True)
class ParsedTemplateMeta:
    lines: list[str]
    node_type_by_line: dict[int, str]


class RestrictedNodeVisitor(NodeVisitor):
    FORBIDDEN_NODES = {
        # Keep loader-related features disabled.
        nodes.Extends: "extends",
        nodes.Include: "include",
        nodes.Import: "import",
        nodes.FromImport: "from import",
    }

    def generic_visit(
        self,
        node: nodes.Node,
        *args: Any,
        **kwargs: Any,
    ):
        forbidden = self.FORBIDDEN_NODES.get(type(node))
        if forbidden is not None:
            error = f"{forbidden!r} is disabled"
            raise SandboxForbiddenSyntax(error, line=getattr(node, "lineno", None))
        return super().generic_visit(node, *args, **kwargs)


class HardenedSandboxedEnvironment(ImmutableSandboxedEnvironment):
    intercepted_binops = frozenset({"*", "**", "+"})

    def __init__(self, config: SandboxConfig, **kwargs: Any):
        super().__init__(undefined=StrictUndefined, **kwargs)
        self._cfg = config
        self.globals = {}

    def call_binop(self, context: Any, operator: str, left: Any, right: Any) -> Any:
        if operator == "*":
            return self._safe_mul(left, right)
        if operator == "**":
            return self._safe_pow(left, right)
        if operator == "+":
            return self._safe_add(left, right)
        return super().call_binop(context, operator, left, right)

    def _safe_mul(self, left: Any, right: Any) -> Any:
        sequence_types = (str, bytes, tuple, list)

        if isinstance(left, sequence_types) and isinstance(right, int):
            self._check_repeat_limits(len(left), right)
        elif isinstance(right, sequence_types) and isinstance(left, int):
            self._check_repeat_limits(len(right), left)

        return left * right  # type: ignore[operator]

    def _check_repeat_limits(self, unit_len: int, repeat: int) -> None:
        if repeat < 0:
            return
        if repeat > self._cfg.max_sequence_repeat:
            raise SandboxOperatorLimitExceeded("sequence repeat exceeds configured limit")
        if unit_len * repeat > self._cfg.max_combined_sequence_length:
            raise SandboxOperatorLimitExceeded("sequence result length exceeds configured limit")

    def _safe_pow(self, left: Any, right: Any) -> Any:
        if not self._cfg.allow_power_operator:
            raise SandboxOperatorLimitExceeded("power operator is disabled")
        if not isinstance(left, int) or not isinstance(right, int):
            raise SandboxOperatorLimitExceeded("power only allowed for integers")
        if abs(right) > self._cfg.max_exponent:
            raise SandboxOperatorLimitExceeded("exponent exceeds configured limit")
        if abs(left) > self._cfg.max_power_base_abs:
            raise SandboxOperatorLimitExceeded("base exceeds configured limit")
        return left**right

    def _safe_add(self, left: Any, right: Any) -> Any:
        sequence_types = (str, bytes, tuple, list)
        if isinstance(left, sequence_types) and isinstance(right, sequence_types) and type(left) is type(right):
            if len(left) + len(right) > self._cfg.max_combined_sequence_length:
                raise SandboxOperatorLimitExceeded("concatenation result exceeds configured limit")
        return left + right  # type: ignore[operator]


config = SandboxConfig()
config.validate()
env = HardenedSandboxedEnvironment(config, loader=None, autoescape=False, extensions=[], enable_async=True, auto_reload=True)


def format_sandbox_error(exc: SandboxRenderError) -> str:
    """
    Compiler-style error output.
    If exact column is unavailable, underline the entire non-whitespace span.
    """
    info = getattr(exc, "info", None)
    if info is None:
        return f"SandboxError: {exc}"

    header = f"{info.error_type}: {info.message}"

    loc = []
    if info.template_name:
        loc.append(f"template={info.template_name}")
    if info.line is not None:
        loc.append(f"line={info.line}")
    if info.column is not None:
        loc.append(f"col={info.column}")
    if info.node_type:
        loc.append(f"node={info.node_type}")
    if loc:
        header = f"{header} ({', '.join(loc)})"

    if info.source_line is None:
        return header

    line_no = info.line if info.line is not None else 0
    snippet = info.source_line.rstrip("\n")
    gutter = f"{line_no:>4} | "

    # If we have a real column, point there with single caret.
    if info.column is not None and info.column > 0:
        caret_pos = info.column - 1
        marker = " " * caret_pos + "^"
    else:
        # No reliable column: underline full meaningful part of the line.
        # Keep indentation spaces, then mark non-space content with ^^^^^
        leading_ws = len(snippet) - len(snippet.lstrip(" \t"))
        content_len = len(snippet.rstrip()) - leading_ws
        if content_len <= 0:
            content_len = max(len(snippet), 1)
            leading_ws = 0
        marker = " " * leading_ws + "^" * content_len

    marker_line = " " * len(gutter) + marker
    return f"{header}\n{gutter}{snippet}\n{marker_line}"


async def render_sandboxed(code: str, **context: Any) -> str:
    config.validate()
    template = env.from_string(code)
    result = await template.render_async(context)

    return result
