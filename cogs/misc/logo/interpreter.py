from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .parser import Binary, Command, Make, Number, Procedure, ProcedureCall, Repeat, Unary, Variable
from .turtle import Turtle, parse_color

MAX_OPERATIONS = 100_000
MAX_REPEAT = 10_000
MAX_CALL_DEPTH = 100


class LogoRuntimeError(Exception):
    pass


@dataclass
class Environment:
    values: dict[str, float]
    parent: Environment | None = None

    def get(self, name: str) -> float:
        name = name.upper()

        if name in self.values:
            return self.values[name]

        if self.parent is not None:
            return self.parent.get(name)

        msg = f"Unknown variable :{name}"
        raise LogoRuntimeError(msg)

    def set(self, name: str, value: float) -> None:
        name = name.upper()
        env: Environment | None = self
        root = self
        while env is not None:
            if name in env.values:
                env.values[name] = value
                return
            root = env
            env = env.parent
        root.values[name] = value


class LogoInterpreter:
    def __init__(
        self,
        turtle: Turtle | None = None,
    ) -> None:
        self.turtle = turtle or Turtle()

        self.global_env = Environment({})
        self.procedures: dict[str, Procedure] = {}

        self.operations = 0
        self.call_depth = 0

    # Public API

    def execute(self, program: tuple[Any, ...]) -> None:
        for node in program:
            if isinstance(node, Procedure):
                self.procedures[node.name] = node

        for node in program:
            if not isinstance(node, Procedure):
                self.execute_node(node, self.global_env)

    # Node execution

    def execute_node(self, node: Any, env: Environment) -> None:
        self.operations += 1

        if self.operations > MAX_OPERATIONS:
            msg = "Program execution limit exceeded."
            raise LogoRuntimeError(msg)

        if isinstance(node, Command):
            self.execute_command(node, env)
            return

        if isinstance(node, Repeat):
            count = self.require_int(self.evaluate(node.count, env))

            if count < 0 or count > MAX_REPEAT:
                msg = f"REPEAT must be between 0 and {MAX_REPEAT}."
                raise LogoRuntimeError(msg)

            for _ in range(count):
                for child in node.body:
                    self.execute_node(child, env)

            return

        if isinstance(node, Make):
            env.set(node.name, self.evaluate(node.value, env))
            return

        if isinstance(node, ProcedureCall):
            self.execute_procedure(node, env)
            return

        msg = f"Unsupported AST node: {type(node).__name__}"
        raise LogoRuntimeError(msg)

    # Commands

    def execute_command(self, command: Command, env: Environment) -> None:
        handlers = {
            "FD": lambda: self.turtle.forward(self.evaluate(command.args[0], env)),
            "BK": lambda: self.turtle.backward(self.evaluate(command.args[0], env)),
            "RT": lambda: self.turtle.right(self.evaluate(command.args[0], env)),
            "LT": lambda: self.turtle.left(self.evaluate(command.args[0], env)),
            "PU": self.turtle.pen_up,
            "PD": self.turtle.pen_down_mode,
            "HOME": self.turtle.home,
            "CS": self.turtle.clear,
            "SETWIDTH": lambda: self.turtle.set_width(self.require_int(self.evaluate(command.args[0], env))),
            "SETH": lambda: self.turtle.set_heading(self.evaluate(command.args[0], env)),
            "SETXY": lambda: self.turtle.set_xy(self.evaluate(command.args[0], env), self.evaluate(command.args[1], env)),
            "SETPC": lambda: self.turtle.set_color(parse_color(command.args[0])),
        }
        handler = handlers.get(command.name)
        if handler is None:
            msg = f"Unknown command: {command.name}"
            raise LogoRuntimeError(msg)
        handler()

    # Procedures

    def execute_procedure(self, call: ProcedureCall, caller_env: Environment) -> None:
        procedure = self.procedures.get(call.name)

        if procedure is None:
            msg = f"Unknown procedure: {call.name}"
            raise LogoRuntimeError(msg)

        if self.call_depth >= MAX_CALL_DEPTH:
            msg = "Maximum procedure recursion depth exceeded."
            raise LogoRuntimeError(msg)

        if len(call.arguments) != len(procedure.parameters):
            msg = f"{call.name} expects {len(procedure.parameters)} argument(s), got {len(call.arguments)}."
            raise LogoRuntimeError(msg)

        local_values = {}

        for parameter, argument in zip(procedure.parameters, call.arguments, strict=False):
            local_values[parameter] = self.evaluate(argument, caller_env)

        local_env = Environment(local_values, caller_env)

        self.call_depth += 1

        try:
            for node in procedure.body:
                self.execute_node(node, local_env)
        finally:
            self.call_depth -= 1

    # Expression evaluation

    def evaluate(self, expression: Any, env: Environment) -> float:
        if isinstance(expression, Number):
            return expression.value

        if isinstance(expression, Variable):
            return env.get(expression.name)

        if isinstance(expression, Unary):
            value = self.evaluate(expression.operand, env)
            if expression.operator != "-":
                msg = f"Unknown unary operator: {expression.operator}"
                raise LogoRuntimeError(msg)
            return -value

        if isinstance(expression, Binary):
            return self.evaluate_binary(expression, env)

        msg = f"Cannot evaluate {type(expression).__name__}"
        raise LogoRuntimeError(msg)

    def evaluate_binary(self, expression: Binary, env: Environment) -> float:
        left = self.evaluate(expression.left, env)
        right = self.evaluate(expression.right, env)
        operations = {
            "+": lambda: left + right,
            "-": lambda: left - right,
            "*": lambda: left * right,
            "/": lambda: self._divide(left, right),
            "=": lambda: float(left == right),
            "<": lambda: float(left < right),
            ">": lambda: float(left > right),
        }
        operation = operations.get(expression.operator)
        if operation is None:
            msg = f"Unknown binary operator: {expression.operator}"
            raise LogoRuntimeError(msg)
        return operation()

    @staticmethod
    def _divide(left: float, right: float) -> float:
        if right == 0:
            msg = "Division by zero."
            raise LogoRuntimeError(msg)
        return left / right

    @staticmethod
    def require_int(value: float) -> int:
        if not math.isfinite(value):
            msg = "Value must be finite."
            raise LogoRuntimeError(msg)

        if not value.is_integer():
            msg = f"Expected an integer, got {value}."
            raise LogoRuntimeError(msg)

        return int(value)
