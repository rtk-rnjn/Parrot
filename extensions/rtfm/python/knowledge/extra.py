"""Curated reference data for the extra ``python`` subcommands.

Drop this next to ``knowledge.py``. It has no dependencies on the cog.
All ``doc`` / ``anchor`` values are paths relative to https://docs.python.org/3/
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = (
    "DUNDERS_DB",
    "GOTCHAS_DB",
    "IDIOMS_DB",
    "KEYWORDS_DB",
    "TYPING_DB",
    "DunderInfo",
    "GotchaInfo",
    "IdiomInfo",
    "KeywordInfo",
    "TypingInfo",
    "lookup_dunder",
    "normalise_dunder",
)


@dataclass(frozen=True, slots=True)
class KeywordInfo:
    name: str
    summary: str
    example: str
    doc: str
    since: str | None = None


@dataclass(frozen=True, slots=True)
class DunderInfo:
    name: str
    group: str
    summary: str
    called_by: str
    signature: str
    example: str
    backs: str = ""
    anchor: str = ""

    @property
    def doc(self) -> str:
        return self.anchor or f"reference/datamodel.html#object.{self.name}"


@dataclass(frozen=True, slots=True)
class GotchaInfo:
    key: str
    title: str
    aliases: tuple[str, ...]
    summary: str
    bad: str
    good: str
    why: str


@dataclass(frozen=True, slots=True)
class IdiomInfo:
    key: str
    title: str
    aliases: tuple[str, ...]
    summary: str
    example: str
    notes: str = ""
    since: str | None = None


@dataclass(frozen=True, slots=True)
class TypingInfo:
    key: str
    title: str
    aliases: tuple[str, ...]
    summary: str
    example: str
    since: str | None
    doc: str


_STMT = "reference/simple_stmts.html"
_COMPOUND = "reference/compound_stmts.html"
_EXPR = "reference/expressions.html"


def _create_keyword_entry(name: str, summary: str, example: str, doc: str, since: str | None = None) -> tuple[str, KeywordInfo]:
    return name, KeywordInfo(name, summary, example, doc, since)


KEYWORDS_DB: dict[str, KeywordInfo] = dict(
    (
        _create_keyword_entry(
            "False",
            "The false value of type `bool`. It is a singleton, but prefer `if not x` over `x is False`.",
            "flag = False\nprint(isinstance(flag, int))  # True, bool subclasses int",
            "library/constants.html#False",
        ),
        _create_keyword_entry(
            "None",
            'The only value of `NoneType`, meaning "no value". Functions without `return` give `None`. Test with `is None`.',
            'result = {}.get("key")\nif result is None:\n    print("missing")',
            "library/constants.html#None",
        ),
        _create_keyword_entry(
            "True", "The true value of type `bool`. `True == 1` and `True + True == 2`.", "print(True + True)  # 2", "library/constants.html#True"
        ),
        _create_keyword_entry(
            "and",
            "Short-circuit AND. Returns the first falsy operand, otherwise the last operand (not always a `bool`).",
            "0 and 1      # 0\n2 and 3      # 3\nname = user and user.name",
            f"{_EXPR}#boolean-operations",
        ),
        _create_keyword_entry(
            "as",
            "Binds a name in `import`, `with`, `except` and `match` patterns.",
            "import numpy as np\nwith open(path) as f:\n    ...\ntry:\n    ...\nexcept ValueError as exc:\n    ...",
            f"{_STMT}#import",
        ),
        _create_keyword_entry(
            "assert",
            "Raises `AssertionError` when the condition is falsy. Stripped under `python -O`, so never use it to validate input.",
            'assert isinstance(n, int), "n must be an int"',
            f"{_STMT}#assert",
        ),
        _create_keyword_entry(
            "async",
            "Declares a coroutine function (`async def`), or an asynchronous `for` / `with` block.",
            "async def fetch():\n    async with session.get(url) as resp:\n        return await resp.text()",
            f"{_COMPOUND}#coroutines",
            "3.7",
        ),
        _create_keyword_entry(
            "await",
            "Suspends the current coroutine until the awaitable finishes. Only valid inside `async def`.",
            'data = await asyncio.sleep(1, result="done")',
            f"{_EXPR}#await-expression",
            "3.7",
        ),
        _create_keyword_entry(
            "break",
            "Leaves the nearest enclosing loop immediately and skips the loop's `else` clause.",
            "for n in nums:\n    if n < 0:\n        break",
            f"{_STMT}#break",
        ),
        _create_keyword_entry(
            "class",
            "Defines a class. The body runs once, in its own namespace, when the statement executes.",
            'class Dog(Animal):\n    sound = "woof"',
            f"{_COMPOUND}#class-definitions",
        ),
        _create_keyword_entry(
            "continue",
            "Skips the rest of the current loop iteration and moves to the next one.",
            "for n in nums:\n    if n % 2:\n        continue\n    print(n)",
            f"{_STMT}#continue",
        ),
        _create_keyword_entry(
            "def",
            "Defines a function. Defaults are evaluated once, when `def` executes.",
            'def greet(name: str = "world") -> str:\n    return f"hello {name}"',
            f"{_COMPOUND}#function-definitions",
        ),
        _create_keyword_entry(
            "del",
            "Removes a name binding, an item or a slice. It does not by itself free the object.",
            'del items[0]\ndel mapping["k"]\ndel name',
            f"{_STMT}#del",
        ),
        _create_keyword_entry(
            "elif",
            '"Else if": the next condition of an `if` chain, checked only if earlier ones were falsy.',
            "if n < 0:\n    ...\nelif n == 0:\n    ...",
            f"{_COMPOUND}#if",
        ),
        _create_keyword_entry(
            "else",
            "Fallback branch of `if`. Also valid on `for` / `while` (runs when no `break` happened) and `try` (runs when nothing was raised).",
            'for n in nums:\n    if n == target:\n        break\nelse:\n    print("not found")',
            f"{_COMPOUND}#if",
        ),
        _create_keyword_entry(
            "except",
            "Handles exceptions from a `try` block. `except*` (3.11+) handles `ExceptionGroup`s.",
            "try:\n    int(s)\nexcept ValueError as exc:\n    print(exc)",
            f"{_COMPOUND}#try",
        ),
        _create_keyword_entry(
            "finally",
            "Always runs, even after `return`, `break` or an unhandled exception. Use it for cleanup.",
            "try:\n    work()\nfinally:\n    lock.release()",
            f"{_COMPOUND}#finally",
        ),
        _create_keyword_entry(
            "for",
            "Iterates over any iterable. Also begins comprehensions and generator expressions.",
            'for i, ch in enumerate("abc"):\n    print(i, ch)',
            f"{_COMPOUND}#for",
        ),
        _create_keyword_entry(
            "from",
            "Three jobs: `from x import y`, exception chaining `raise A from B`, and delegation `yield from it`.",
            'from pathlib import Path\nraise RuntimeError("bad") from exc\nyield from other()',
            f"{_STMT}#import",
        ),
        _create_keyword_entry(
            "global",
            "Makes assignments in a function target the module-level name instead of creating a local.",
            "counter = 0\ndef bump():\n    global counter\n    counter += 1",
            f"{_STMT}#global",
        ),
        _create_keyword_entry(
            "if",
            "Runs a block only when the condition is truthy. Also forms conditional expressions `a if cond else b`.",
            'label = "adult" if age >= 18 else "minor"',
            f"{_COMPOUND}#if",
        ),
        _create_keyword_entry(
            "import", "Loads a module (once, cached in `sys.modules`) and binds it to a name.", "import json\nfrom os import path", f"{_STMT}#import"
        ),
        _create_keyword_entry(
            "in",
            "Membership test (`x in container`) and the iteration part of `for x in iterable`.",
            '"a" in "cat"      # True\n3 in {1, 2, 3}    # True',
            f"{_EXPR}#membership-test-operations",
        ),
        _create_keyword_entry(
            "is",
            "Identity test: are both names bound to the very same object? Use it for `None`, `True`, `False`, not for values.",
            "x is None\na = []; b = []\na is b   # False\na == b   # True",
            f"{_EXPR}#is-not",
        ),
        _create_keyword_entry(
            "lambda", "Creates a small anonymous function from a single expression.", "sorted(words, key=lambda w: w.lower())", f"{_EXPR}#lambda"
        ),
        _create_keyword_entry(
            "nonlocal",
            "Makes assignments target a name in the nearest enclosing function scope.",
            "def counter():\n    n = 0\n    def inc():\n        nonlocal n\n        n += 1\n        return n\n    return inc",
            f"{_STMT}#nonlocal",
        ),
        _create_keyword_entry(
            "not",
            "Boolean negation. Always returns a real `bool`. Binds looser than comparison operators.",
            "not []          # True\nnot x in items  # same as not (x in items)",
            f"{_EXPR}#boolean-operations",
        ),
        _create_keyword_entry(
            "or",
            "Short-circuit OR. Returns the first truthy operand, otherwise the last operand.",
            'name = user_input or "anonymous"',
            f"{_EXPR}#boolean-operations",
        ),
        _create_keyword_entry(
            "pass", "Does nothing. Fills a block that syntactically needs a statement.", "class Marker:\n    pass", f"{_STMT}#pass"
        ),
        _create_keyword_entry(
            "raise",
            "Raises an exception. A bare `raise` inside `except` re-raises the active one.",
            'raise ValueError("negative")\nraise AppError() from original',
            f"{_STMT}#raise",
        ),
        _create_keyword_entry(
            "return",
            "Leaves a function, optionally with a value (default `None`). Inside `try`, `finally` still runs first.",
            "def area(w, h):\n    return w * h",
            f"{_STMT}#return",
        ),
        _create_keyword_entry(
            "try",
            "Starts an exception-handling block with `except`, `else` and `finally` clauses.",
            'try:\n    value = int(raw)\nexcept ValueError:\n    value = 0\nelse:\n    print("parsed")',
            f"{_COMPOUND}#try",
        ),
        _create_keyword_entry(
            "while",
            "Repeats while the condition is truthy. Takes an optional `else` like `for`.",
            "while queue:\n    job = queue.pop()",
            f"{_COMPOUND}#while",
        ),
        _create_keyword_entry(
            "with",
            "Runs a block inside a context manager, calling `__enter__` and `__exit__` for setup and cleanup.",
            'with open("a.txt") as f, open("b.txt", "w") as g:\n    g.write(f.read())',
            f"{_COMPOUND}#with",
        ),
        _create_keyword_entry(
            "yield",
            "Turns a function into a generator and hands one value back to the caller, pausing until resumed.",
            "def countdown(n):\n    while n:\n        yield n\n        n -= 1",
            f"{_EXPR}#yield-expressions",
        ),
        # soft keywords
        _create_keyword_entry(
            "_",
            "Soft keyword: in a `match` block it is the wildcard pattern (matches anything, binds nothing). Everywhere else it is a normal name.",
            'match command:\n    case "go":\n        ...\n    case _:\n        print("unknown")',
            f"{_COMPOUND}#wildcard-patterns",
            "3.10",
        ),
        _create_keyword_entry(
            "case",
            "Soft keyword: one pattern branch inside a `match` block, with an optional `if` guard.",
            "match point:\n    case (0, 0):\n        ...\n    case (x, y) if x == y:\n        ...",
            f"{_COMPOUND}#match",
            "3.10",
        ),
        _create_keyword_entry(
            "match",
            "Soft keyword: starts structural pattern matching (PEP 634). It is still usable as a variable name elsewhere.",
            'match event:\n    case {"type": "click", "x": x}:\n        print(x)',
            f"{_COMPOUND}#match",
            "3.10",
        ),
        _create_keyword_entry(
            "type",
            "Soft keyword: declares a lazily evaluated type alias (PEP 695). Outside that statement `type` is still the builtin.",
            "type Point = tuple[float, float]\ntype Tree[T] = T | list[Tree[T]]",
            f"{_STMT}#type",
            "3.12",
        ),
    ),
)


def normalise_dunder(query: str) -> str:
    core = query.strip().strip("`").casefold().strip("_")
    return f"__{core}__" if core else ""


def _create_dunder_info(
    name: str, group: str, summary: str, called_by: str, signature: str, example: str, backs: str = "", anchor: str = ""
) -> DunderInfo:
    return DunderInfo(name, group, summary, called_by, signature, example, backs, anchor)


_BINARY_OPS: tuple[tuple[str, str, str, str], ...] = (
    ("add", "+", "operator.add", "addition"),
    ("sub", "-", "operator.sub", "subtraction"),
    ("mul", "*", "operator.mul", "multiplication"),
    ("matmul", "@", "operator.matmul", "matrix multiplication"),
    ("truediv", "/", "operator.truediv", "true division"),
    ("floordiv", "//", "operator.floordiv", "floor division"),
    ("mod", "%", "operator.mod", "remainder / `%` formatting"),
    ("pow", "**", "operator.pow", "exponentiation"),
    ("lshift", "<<", "operator.lshift", "left shift"),
    ("rshift", ">>", "operator.rshift", "right shift"),
    ("and", "&", "operator.and_", "bitwise AND"),
    ("xor", "^", "operator.xor", "bitwise XOR"),
    ("or", "|", "operator.or_", "bitwise OR / set union / dict merge"),
)


def _arithmetic() -> list[DunderInfo]:
    out: list[DunderInfo] = []
    for n, sym, func, label in _BINARY_OPS:
        sig = "(self, other, modulo=None)" if n == "pow" else "(self, other)"
        out.append(
            _create_dunder_info(
                f"__{n}__",
                "Numeric operators",
                f"Implements {label} for `a {sym} b`. Return `NotImplemented` when the other operand's type isn't supported.",
                f"`a {sym} b` calls `type(a).__{n}__(a, b)` first.",
                f"def __{n}__{sig} -> object",
                f"class Money:\n    def __{n}__(self, other):\n        if not isinstance(other, Money):\n            return NotImplemented\n        return Money(self.cents {sym} other.cents)",
                f"Operator `{sym}` / `{func}`",
            )
        )
        out.append(
            _create_dunder_info(
                f"__r{n}__",
                "Numeric operators",
                f"Reflected {label}: runs when the left operand can't handle `a {sym} b`, so the right operand gets a go.",
                f"`a {sym} b` calls `type(b).__r{n}__(b, a)` if `type(a)` lacks `__{n}__` or returns `NotImplemented`.",
                f"def __r{n}__{sig} -> object",
                f"class Money:\n    def __r{n}__(self, other):  # handles `5 {sym} Money(...)`\n        return Money(other {sym} self.cents)",
                f"Operator `{sym}` (right-hand side)",
            )
        )
        out.append(
            _create_dunder_info(
                f"__i{n}__",
                "Numeric operators",
                f"In-place {label} for `a {sym}= b`. Mutate `self` if you can and return it.",
                f"`a {sym}= b` calls `type(a).__i{n}__(a, b)`, falling back to `__{n}__` / `__r{n}__`.",
                f"def __i{n}__{sig} -> object",
                f"class Bag:\n    def __i{n}__(self, other):\n        ...  # mutate self in place\n        return self  # the result is rebound to the name",
                f"Operator `{sym}=`",
            )
        )
    return out


def _comparisons() -> list[DunderInfo]:
    reflect = {"lt": "gt", "le": "ge", "eq": "eq", "ne": "ne", "gt": "lt", "ge": "le"}
    symbols = {"lt": "<", "le": "<=", "eq": "==", "ne": "!=", "gt": ">", "ge": ">="}
    out: list[DunderInfo] = []
    for n, sym in symbols.items():
        extra = " Defining `__eq__` without `__hash__` makes instances unhashable." if n == "eq" else ""
        out.append(
            _create_dunder_info(
                f"__{n}__",
                "Comparison",
                f"Rich comparison for `a {sym} b`. Return `NotImplemented` for unsupported types, never raise.{extra}",
                f"`a {sym} b` calls `type(a).__{n}__(a, b)`, then the reflected `type(b).__{reflect[n]}__(b, a)`.",
                f"def __{n}__(self, other) -> bool",
                f"class Version:\n    def __{n}__(self, other):\n        if not isinstance(other, Version):\n            return NotImplemented\n        return self.parts {sym} other.parts",
                f"Operator `{sym}` / `operator.{n}`",
            )
        )
    return out


DUNDERS_DB: dict[str, DunderInfo] = {
    info.name: info
    for info in (
        # object lifecycle
        _create_dunder_info(
            "__new__",
            "Object lifecycle",
            "Static method that creates the instance before `__init__`. Needed for immutable subclasses and singletons.",
            "`Cls(...)` calls `Cls.__new__(Cls, ...)`, then `__init__` on the result.",
            "def __new__(cls, *args, **kwargs) -> Self",
            "class Singleton:\n    _inst = None\n    def __new__(cls):\n        if cls._inst is None:\n            cls._inst = super().__new__(cls)\n        return cls._inst",
        ),
        _create_dunder_info(
            "__init__",
            "Object lifecycle",
            "Initialises a freshly created instance. Must return `None`.",
            "`Cls(...)` calls it after `__new__` returned an instance of `Cls`.",
            "def __init__(self, *args, **kwargs) -> None",
            "class Point:\n    def __init__(self, x, y):\n        self.x, self.y = x, y",
        ),
        _create_dunder_info(
            "__del__",
            "Object lifecycle",
            "Finaliser, called when the object is about to be destroyed. Timing is not guaranteed, so prefer context managers.",
            "The interpreter, when the reference count hits zero or the object is collected.",
            "def __del__(self) -> None",
            "class Conn:\n    def __del__(self):\n        self.close()",
        ),
        _create_dunder_info(
            "__init_subclass__",
            "Class creation",
            "Hook called on a parent class each time it is subclassed. Often replaces simple metaclasses.",
            "`class Child(Parent, **kw)` calls `Parent.__init_subclass__(**kw)`.",
            "def __init_subclass__(cls, **kwargs) -> None",
            "class Plugin:\n    registry = []\n    def __init_subclass__(cls, **kw):\n        super().__init_subclass__(**kw)\n        Plugin.registry.append(cls)",
        ),
        _create_dunder_info(
            "__class_getitem__",
            "Class creation",
            "Makes `Cls[...]` work on the class itself, used for generic aliases such as `list[int]`.",
            "`Cls[item]` where `Cls` is a class.",
            "def __class_getitem__(cls, item) -> GenericAlias",
            "class Box:\n    __class_getitem__ = classmethod(types.GenericAlias)\n\nBox[int]",
        ),
        _create_dunder_info(
            "__set_name__",
            "Descriptors",
            "Tells a descriptor the attribute name it was assigned to when the owner class is created.",
            "`type.__new__` calls it for every class attribute that defines it.",
            "def __set_name__(self, owner, name) -> None",
            'class Field:\n    def __set_name__(self, owner, name):\n        self.private = "_" + name',
        ),
        _create_dunder_info(
            "__slots__",
            "Class creation",
            "Class variable listing allowed attributes. Removes the per-instance `__dict__`, saving memory.",
            "Read by `type.__new__` when the class is created.",
            '__slots__ = ("x", "y")',
            'class Point:\n    __slots__ = ("x", "y")',
            anchor="reference/datamodel.html#slots",
        ),
        _create_dunder_info(
            "__match_args__",
            "Class creation",
            "Tuple naming the attributes that positional patterns in `match` map to.",
            "`case Point(1, 2)` looks up `Point.__match_args__`.",
            '__match_args__ = ("x", "y")',
            'class Point:\n    __match_args__ = ("x", "y")\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n\nmatch Point(1, 2):\n    case Point(x, y): ...',
        ),
        # representation
        _create_dunder_info(
            "__repr__",
            "Representation",
            "Unambiguous, developer-oriented string; ideally valid Python that recreates the object.",
            "`repr(obj)`, the REPL, and `!r`. Also the fallback for `str()`.",
            "def __repr__(self) -> str",
            'class P:\n    def __repr__(self):\n        return f"P({self.x!r}, {self.y!r})"',
            "Builtin `repr()`",
        ),
        _create_dunder_info(
            "__str__",
            "Representation",
            "Readable, user-facing string.",
            '`str(obj)`, `print(obj)`, `f"{obj}"`.',
            "def __str__(self) -> str",
            'class P:\n    def __str__(self):\n        return f"({self.x}, {self.y})"',
            "Builtin `str()`",
        ),
        _create_dunder_info(
            "__bytes__",
            "Representation",
            "Returns a `bytes` representation.",
            "`bytes(obj)`.",
            "def __bytes__(self) -> bytes",
            'class Id:\n    def __bytes__(self):\n        return self.value.to_bytes(4, "big")',
            "Builtin `bytes()`",
        ),
        _create_dunder_info(
            "__format__",
            "Representation",
            "Implements the format-spec mini-language for the object.",
            '`format(obj, spec)`, `f"{obj:spec}"`, `str.format`.',
            "def __format__(self, spec: str) -> str",
            'class Temp:\n    def __format__(self, spec):\n        return format(self.c, spec) + " C"',
            "Builtin `format()`",
        ),
        _create_dunder_info(
            "__hash__",
            "Comparison",
            "Integer hash used by `dict` and `set`. Equal objects must hash equal. Set to `None` to mark unhashable.",
            "`hash(obj)`; dict/set lookups.",
            "def __hash__(self) -> int",
            "class P:\n    def __hash__(self):\n        return hash((self.x, self.y))",
            "Builtin `hash()`",
        ),
        _create_dunder_info(
            "__bool__",
            "Representation",
            "Truth value. If missing, `__len__` is tried, otherwise the object is always truthy.",
            "`bool(obj)`, `if obj:`, `not obj`.",
            "def __bool__(self) -> bool",
            "class Basket:\n    def __bool__(self):\n        return bool(self.items)",
            "Builtin `bool()`",
        ),
        _create_dunder_info(
            "__dir__",
            "Attribute access",
            "Returns the attribute names reported by `dir()`.",
            "`dir(obj)`.",
            "def __dir__(self) -> Iterable[str]",
            'class Dyn:\n    def __dir__(self):\n        return [*super().__dir__(), "magic"]',
            "Builtin `dir()`",
        ),
        # attribute access & descriptors
        _create_dunder_info(
            "__getattribute__",
            "Attribute access",
            "Runs for every attribute lookup. Easy to recurse by accident; always go through `super()`.",
            "`obj.name`.",
            "def __getattribute__(self, name: str) -> object",
            'class Spy:\n    def __getattribute__(self, name):\n        print("get", name)\n        return super().__getattribute__(name)',
            "Builtin `getattr()`",
        ),
        _create_dunder_info(
            "__getattr__",
            "Attribute access",
            "Fallback, called only when normal lookup fails with `AttributeError`.",
            "`obj.name` after the normal lookup failed.",
            "def __getattr__(self, name: str) -> object",
            "class Proxy:\n    def __getattr__(self, name):\n        return getattr(self._target, name)",
            "Builtin `getattr()`",
        ),
        _create_dunder_info(
            "__setattr__",
            "Attribute access",
            "Runs for every attribute assignment.",
            "`obj.name = value`.",
            "def __setattr__(self, name: str, value) -> None",
            'class Frozen:\n    def __setattr__(self, name, value):\n        raise AttributeError("read-only")',
            "Builtin `setattr()`",
        ),
        _create_dunder_info(
            "__delattr__",
            "Attribute access",
            "Runs when an attribute is deleted.",
            "`del obj.name`.",
            "def __delattr__(self, name: str) -> None",
            "class Guard:\n    def __delattr__(self, name):\n        raise AttributeError(name)",
            "Builtin `delattr()`",
        ),
        _create_dunder_info(
            "__get__",
            "Descriptors",
            "Descriptor read. Functions use it to become bound methods; `property` uses it too.",
            "`obj.attr` when `attr` is found on the class and defines `__get__`.",
            "def __get__(self, obj, objtype=None) -> object",
            "class Const:\n    def __get__(self, obj, objtype=None):\n        return 42",
        ),
        _create_dunder_info(
            "__set__",
            "Descriptors",
            "Descriptor write. Defining it makes a data descriptor, which wins over the instance `__dict__`.",
            "`obj.attr = value` when `attr` on the class defines `__set__`.",
            "def __set__(self, obj, value) -> None",
            'class Positive:\n    def __set__(self, obj, value):\n        if value <= 0:\n            raise ValueError\n        obj.__dict__["n"] = value',
        ),
        _create_dunder_info(
            "__delete__",
            "Descriptors",
            "Descriptor delete.",
            "`del obj.attr` when `attr` on the class defines `__delete__`.",
            "def __delete__(self, obj) -> None",
            'class Tracked:\n    def __delete__(self, obj):\n        print("deleted")',
        ),
        # callables & types
        _create_dunder_info(
            "__call__",
            "Callables",
            "Makes instances callable like functions.",
            "`obj(*args, **kwargs)`.",
            "def __call__(self, *args, **kwargs) -> object",
            "class Adder:\n    def __init__(self, n): self.n = n\n    def __call__(self, x):\n        return x + self.n\n\nAdder(2)(3)  # 5",
            "Builtin `callable()`",
        ),
        _create_dunder_info(
            "__instancecheck__",
            "Class creation",
            "Customises `isinstance(x, Cls)`. Defined on a metaclass.",
            "`isinstance(obj, Cls)`.",
            "def __instancecheck__(cls, instance) -> bool",
            'class Meta(type):\n    def __instancecheck__(cls, inst):\n        return hasattr(inst, "close")',
            "Builtin `isinstance()`",
            "reference/datamodel.html#type.__instancecheck__",
        ),
        _create_dunder_info(
            "__subclasscheck__",
            "Class creation",
            "Customises `issubclass(x, Cls)`. Defined on a metaclass.",
            "`issubclass(sub, Cls)`.",
            "def __subclasscheck__(cls, subclass) -> bool",
            'class Meta(type):\n    def __subclasscheck__(cls, sub):\n        return hasattr(sub, "close")',
            "Builtin `issubclass()`",
            "reference/datamodel.html#type.__subclasscheck__",
        ),
        # containers
        _create_dunder_info(
            "__len__",
            "Containers",
            "Number of items. Also the fallback for truthiness.",
            "`len(obj)`.",
            "def __len__(self) -> int",
            "class Deck:\n    def __len__(self):\n        return len(self.cards)",
            "Builtin `len()`",
        ),
        _create_dunder_info(
            "__length_hint__",
            "Containers",
            "Optional estimate of length, used to pre-size buffers.",
            "`operator.length_hint(obj)`.",
            "def __length_hint__(self) -> int",
            "class Stream:\n    def __length_hint__(self):\n        return 1000",
            "`operator.length_hint()`",
        ),
        _create_dunder_info(
            "__getitem__",
            "Containers",
            "Indexing, slicing and key lookup. Also lets objects be iterated with the old sequence protocol (indexes 0, 1, 2... until `IndexError`).",
            "`obj[key]`.",
            "def __getitem__(self, key) -> object",
            "class Deck:\n    def __getitem__(self, i):\n        return self.cards[i]",
            "Subscript `[]`",
        ),
        _create_dunder_info(
            "__setitem__",
            "Containers",
            "Item or slice assignment.",
            "`obj[key] = value`.",
            "def __setitem__(self, key, value) -> None",
            "class Grid:\n    def __setitem__(self, pos, value):\n        self.cells[pos] = value",
            "Subscript assignment",
        ),
        _create_dunder_info(
            "__delitem__",
            "Containers",
            "Item or slice deletion.",
            "`del obj[key]`.",
            "def __delitem__(self, key) -> None",
            "class Grid:\n    def __delitem__(self, pos):\n        del self.cells[pos]",
            "`del obj[key]`",
        ),
        _create_dunder_info(
            "__missing__",
            "Containers",
            "Called by `dict` subclasses when a key is absent. How `defaultdict` works.",
            "`d[key]` on a `dict` subclass when `key` is missing.",
            "def __missing__(self, key) -> object",
            "class Counter0(dict):\n    def __missing__(self, key):\n        return 0",
        ),
        _create_dunder_info(
            "__contains__",
            "Containers",
            "Membership test. Falls back to iteration when absent.",
            "`item in obj`.",
            "def __contains__(self, item) -> bool",
            "class Evens:\n    def __contains__(self, n):\n        return n % 2 == 0",
            "Operator `in`",
        ),
        _create_dunder_info(
            "__iter__",
            "Iteration",
            "Returns an iterator. Generators make this a one-liner with `yield`.",
            "`iter(obj)`, `for x in obj`, unpacking, `list(obj)`.",
            "def __iter__(self) -> Iterator",
            "class Playlist:\n    def __iter__(self):\n        yield from self.songs",
            "Builtin `iter()`",
        ),
        _create_dunder_info(
            "__next__",
            "Iteration",
            "Returns the next item or raises `StopIteration`.",
            "`next(it)`, and each step of a `for` loop.",
            "def __next__(self) -> object",
            "class Count:\n    def __init__(self): self.n = 0\n    def __iter__(self): return self\n    def __next__(self):\n        self.n += 1\n        return self.n",
            "Builtin `next()`",
        ),
        _create_dunder_info(
            "__reversed__",
            "Iteration",
            "Custom reverse iteration.",
            "`reversed(obj)`.",
            "def __reversed__(self) -> Iterator",
            "class Playlist:\n    def __reversed__(self):\n        return iter(self.songs[::-1])",
            "Builtin `reversed()`",
        ),
        # context managers & async
        _create_dunder_info(
            "__enter__",
            "Context managers",
            "Sets up the context. Its return value is bound by `as`.",
            "Start of `with obj as name:`.",
            "def __enter__(self) -> object",
            "class Timer:\n    def __enter__(self):\n        self.t = time.perf_counter()\n        return self",
        ),
        _create_dunder_info(
            "__exit__",
            "Context managers",
            "Cleans up. Receives the exception info; returning a truthy value suppresses the exception.",
            "End of the `with` block, normal or not.",
            "def __exit__(self, exc_type, exc, tb) -> bool | None",
            "class Timer:\n    def __exit__(self, exc_type, exc, tb):\n        print(time.perf_counter() - self.t)\n        return False",
        ),
        _create_dunder_info(
            "__aenter__",
            "Async",
            "Async version of `__enter__`; must be awaitable.",
            "Start of `async with obj as name:`.",
            "async def __aenter__(self) -> object",
            "class Pool:\n    async def __aenter__(self):\n        await self.connect()\n        return self",
        ),
        _create_dunder_info(
            "__aexit__",
            "Async",
            "Async version of `__exit__`.",
            "End of an `async with` block.",
            "async def __aexit__(self, exc_type, exc, tb) -> bool | None",
            "class Pool:\n    async def __aexit__(self, *exc):\n        await self.close()",
        ),
        _create_dunder_info(
            "__await__",
            "Async",
            "Makes instances awaitable. Must return an iterator.",
            "`await obj`.",
            "def __await__(self) -> Iterator",
            "class Ready:\n    def __await__(self):\n        yield from asyncio.sleep(0).__await__()\n        return 42",
        ),
        _create_dunder_info(
            "__aiter__",
            "Async",
            "Returns an asynchronous iterator (not a coroutine).",
            "`async for x in obj`, `aiter(obj)`.",
            "def __aiter__(self) -> AsyncIterator",
            "class Feed:\n    def __aiter__(self):\n        return self",
            "Builtin `aiter()`",
        ),
        _create_dunder_info(
            "__anext__",
            "Async",
            "Returns an awaitable producing the next item, or raises `StopAsyncIteration`.",
            "Each step of `async for`, `anext(it)`.",
            "async def __anext__(self) -> object",
            "class Feed:\n    async def __anext__(self):\n        if not self.items:\n            raise StopAsyncIteration\n        return self.items.pop(0)",
            "Builtin `anext()`",
        ),
        # numeric: unary & conversion
        _create_dunder_info(
            "__neg__",
            "Numeric operators",
            "Unary minus.",
            "`-obj`.",
            "def __neg__(self) -> object",
            "class V:\n    def __neg__(self):\n        return V(-self.x)",
            "Operator `-` (unary) / `operator.neg`",
        ),
        _create_dunder_info(
            "__pos__",
            "Numeric operators",
            "Unary plus.",
            "`+obj`.",
            "def __pos__(self) -> object",
            "class V:\n    def __pos__(self):\n        return V(+self.x)",
            "Operator `+` (unary) / `operator.pos`",
        ),
        _create_dunder_info(
            "__abs__",
            "Numeric operators",
            "Absolute value.",
            "`abs(obj)`.",
            "def __abs__(self) -> object",
            "class V:\n    def __abs__(self):\n        return (self.x**2 + self.y**2) ** 0.5",
            "Builtin `abs()`",
        ),
        _create_dunder_info(
            "__invert__",
            "Numeric operators",
            "Bitwise inversion.",
            "`~obj`.",
            "def __invert__(self) -> object",
            "class Mask:\n    def __invert__(self):\n        return Mask(~self.bits)",
            "Operator `~` / `operator.invert`",
        ),
        _create_dunder_info(
            "__divmod__",
            "Numeric operators",
            "Quotient and remainder as a tuple.",
            "`divmod(a, b)`.",
            "def __divmod__(self, other) -> tuple",
            "class Money:\n    def __divmod__(self, n):\n        return divmod(self.cents, n)",
            "Builtin `divmod()`",
        ),
        _create_dunder_info(
            "__rdivmod__",
            "Numeric operators",
            "Reflected `divmod`.",
            "`divmod(a, b)` when `type(a)` can't handle it.",
            "def __rdivmod__(self, other) -> tuple",
            "class Money:\n    def __rdivmod__(self, n):\n        return divmod(n, self.cents)",
            "Builtin `divmod()` (right-hand side)",
        ),
        _create_dunder_info(
            "__int__",
            "Conversion",
            "Converts to `int`.",
            "`int(obj)`.",
            "def __int__(self) -> int",
            "class Cents:\n    def __int__(self):\n        return self.value",
            "Builtin `int()`",
        ),
        _create_dunder_info(
            "__float__",
            "Conversion",
            "Converts to `float`.",
            "`float(obj)`.",
            "def __float__(self) -> float",
            "class Cents:\n    def __float__(self):\n        return self.value / 100",
            "Builtin `float()`",
        ),
        _create_dunder_info(
            "__complex__",
            "Conversion",
            "Converts to `complex`.",
            "`complex(obj)`.",
            "def __complex__(self) -> complex",
            "class Pt:\n    def __complex__(self):\n        return complex(self.x, self.y)",
            "Builtin `complex()`",
        ),
        _create_dunder_info(
            "__index__",
            "Conversion",
            "Lossless integer conversion. Lets an object be used as a list index, in `range()`, `hex()`, `bin()` and `oct()`.",
            "`operator.index(obj)`, `seq[obj]`, `hex(obj)`.",
            "def __index__(self) -> int",
            "class Slot:\n    def __index__(self):\n        return self.n\n\n[10, 20, 30][Slot(1)]",
            "`operator.index()`",
        ),
        _create_dunder_info(
            "__round__",
            "Numeric operators",
            "Rounding, with an optional number of digits.",
            "`round(obj, ndigits)`.",
            "def __round__(self, ndigits=None) -> object",
            "class Money:\n    def __round__(self, ndigits=None):\n        return Money(round(self.amount, ndigits))",
            "Builtin `round()`",
        ),
        _create_dunder_info(
            "__trunc__",
            "Numeric operators",
            "Truncates towards zero.",
            "`math.trunc(obj)`.",
            "def __trunc__(self) -> int",
            "class Money:\n    def __trunc__(self):\n        return int(self.amount)",
            "`math.trunc()`",
            "library/math.html#math.trunc",
        ),
        _create_dunder_info(
            "__floor__",
            "Numeric operators",
            "Rounds down.",
            "`math.floor(obj)`.",
            "def __floor__(self) -> int",
            "class Money:\n    def __floor__(self):\n        return self.cents // 100",
            "`math.floor()`",
            "library/math.html#math.floor",
        ),
        _create_dunder_info(
            "__ceil__",
            "Numeric operators",
            "Rounds up.",
            "`math.ceil(obj)`.",
            "def __ceil__(self) -> int",
            "class Money:\n    def __ceil__(self):\n        return -(-self.cents // 100)",
            "`math.ceil()`",
            "library/math.html#math.ceil",
        ),
        # copy / pickle / misc
        _create_dunder_info(
            "__copy__",
            "Copy & pickle",
            "Customises shallow copies.",
            "`copy.copy(obj)`.",
            "def __copy__(self) -> Self",
            "class Doc:\n    def __copy__(self):\n        return Doc(self.text)",
            "`copy.copy()`",
            "library/copy.html",
        ),
        _create_dunder_info(
            "__deepcopy__",
            "Copy & pickle",
            "Customises deep copies. Receives the memo dict.",
            "`copy.deepcopy(obj)`.",
            "def __deepcopy__(self, memo: dict) -> Self",
            "class Doc:\n    def __deepcopy__(self, memo):\n        return Doc(copy.deepcopy(self.parts, memo))",
            "`copy.deepcopy()`",
            "library/copy.html",
        ),
        _create_dunder_info(
            "__reduce__",
            "Copy & pickle",
            "Tells `pickle` how to rebuild the object: a callable plus its arguments.",
            "`pickle.dumps(obj)`, `copy.copy(obj)`.",
            "def __reduce__(self) -> tuple",
            "class P:\n    def __reduce__(self):\n        return (P, (self.x, self.y))",
            "`pickle`",
            "library/pickle.html#object.__reduce__",
        ),
        _create_dunder_info(
            "__getstate__",
            "Copy & pickle",
            "Returns the state to pickle or copy (default: `__dict__`).",
            "`pickle.dumps(obj)`, `copy.copy(obj)`.",
            "def __getstate__(self) -> object",
            'class Conn:\n    def __getstate__(self):\n        return {"url": self.url}',
            "`pickle`",
            "library/pickle.html#object.__getstate__",
        ),
        _create_dunder_info(
            "__setstate__",
            "Copy & pickle",
            "Restores state produced by `__getstate__`.",
            "`pickle.loads(data)`.",
            "def __setstate__(self, state) -> None",
            'class Conn:\n    def __setstate__(self, state):\n        self.url = state["url"]\n        self.connect()',
            "`pickle`",
            "library/pickle.html#object.__setstate__",
        ),
        _create_dunder_info(
            "__sizeof__",
            "Representation",
            "Reports the object's own size in bytes.",
            "`sys.getsizeof(obj)` (adds GC overhead).",
            "def __sizeof__(self) -> int",
            "class Blob:\n    def __sizeof__(self):\n        return len(self.data)",
            "`sys.getsizeof()`",
            "library/sys.html#sys.getsizeof",
        ),
        _create_dunder_info(
            "__fspath__",
            "Representation",
            "Returns a file-system path as `str` or `bytes`. Implements `os.PathLike`.",
            "`os.fspath(obj)`, and any function accepting path-likes.",
            "def __fspath__(self) -> str",
            'class Doc:\n    def __fspath__(self):\n        return "/tmp/doc.txt"\n\nopen(Doc())',
            "`os.fspath()`",
            "library/os.html#os.PathLike.__fspath__",
        ),
        _create_dunder_info(
            "__buffer__",
            "Representation",
            "Exposes a buffer to Python code (PEP 688).",
            "`memoryview(obj)`.",
            "def __buffer__(self, flags: int) -> memoryview",
            "class Raw:\n    def __buffer__(self, flags):\n        return memoryview(self.data)",
            "`memoryview()`",
        ),
        *_arithmetic(),
        *_comparisons(),
    )
}


def lookup_dunder(query: str) -> DunderInfo | None:
    return DUNDERS_DB.get(normalise_dunder(query))


GOTCHAS_DB: tuple[GotchaInfo, ...] = (
    GotchaInfo(
        "mutable-default",
        "Mutable default arguments",
        ("mutable-defaults", "default-arg", "default-args", "mutable"),
        "A default like `[]` or `{}` is created once and shared by every call.",
        "def add(item, bucket=[]):\n    bucket.append(item)\n    return bucket\n\nadd(1)  # [1]\nadd(2)  # [1, 2]  <- same list again",
        "def add(item, bucket=None):\n    if bucket is None:\n        bucket = []\n    bucket.append(item)\n    return bucket",
        "Defaults are evaluated once, when `def` runs, and stored on the function (`add.__defaults__`).",
    ),
    GotchaInfo(
        "late-binding",
        "Late-binding closures",
        ("closure", "closures", "lambda-loop", "late-binding-closures"),
        "Closures capture variables, not values, so loop lambdas all see the final value.",
        "funcs = [lambda: i for i in range(3)]\nprint([f() for f in funcs])  # [2, 2, 2]",
        "funcs = [lambda i=i: i for i in range(3)]\nprint([f() for f in funcs])  # [0, 1, 2]\n\n# or: functools.partial(show, i)",
        "`i` is looked up when the lambda is called, by which point the loop has finished. A default argument freezes the value at definition time.",
    ),
    GotchaInfo(
        "is-vs-eq",
        "`is` vs `==`",
        ("is", "identity", "equality", "is-equal"),
        "`==` compares values; `is` compares object identity. Using `is` on numbers or strings is unreliable.",
        'a = int("1000")\nb = int("1000")\nprint(a == b)  # True\nprint(a is b)  # False (implementation detail!)',
        "if a == b:\n    ...\nif value is None:  # `is` is for singletons: None, True, False\n    ...",
        "Small ints and some strings are cached, so `is` sometimes appears to work. Since 3.8 comparing with a literal via `is` raises a `SyntaxWarning`.",
    ),
    GotchaInfo(
        "modify-while-iterating",
        "Modifying a list while iterating",
        ("mutate-while-iterating", "remove-in-loop", "iterating-and-removing", "list-remove-loop"),
        "Removing items from a list inside a `for` loop skips elements.",
        "nums = [2, 4, 6, 1]\nfor n in nums:\n    if n % 2 == 0:\n        nums.remove(n)\nprint(nums)  # [4, 1]  <- 4 survived",
        "nums = [n for n in nums if n % 2]  # new list\n# or in place: nums[:] = [n for n in nums if n % 2]\n# dicts: iterate over list(d) when deleting keys",
        "The loop walks by index; deleting shifts later items left and the next index jumps over one. Dicts raise `RuntimeError` instead.",
    ),
    GotchaInfo(
        "list-multiplication",
        "Shared references in `[[0]] * n`",
        ("shared-reference", "grid", "2d-list", "list-of-lists", "nested-list"),
        "Multiplying a list of lists repeats the *same* inner list.",
        "grid = [[0] * 3] * 3\ngrid[0][0] = 1\nprint(grid)  # [[1, 0, 0], [1, 0, 0], [1, 0, 0]]",
        "grid = [[0] * 3 for _ in range(3)]\ngrid[0][0] = 1\nprint(grid)  # [[1, 0, 0], [0, 0, 0], [0, 0, 0]]",
        "`seq * n` copies references, not objects. That is fine for ints and strings but not for mutable items.",
    ),
    GotchaInfo(
        "float-equality",
        "Floating-point equality",
        ("float", "floats", "floating-point", "0.1-0.2", "float-compare"),
        "Most decimal fractions can't be represented exactly in binary floats.",
        "print(0.1 + 0.2)         # 0.30000000000000004\nprint(0.1 + 0.2 == 0.3)  # False",
        'import math\nfrom decimal import Decimal\n\nmath.isclose(0.1 + 0.2, 0.3)             # True\nDecimal("0.1") + Decimal("0.2") == Decimal("0.3")  # True',
        "Floats are IEEE-754 binary doubles. Compare with a tolerance, or use `decimal` / `fractions` for exact money-style maths.",
    ),
    GotchaInfo(
        "single-element-tuple",
        "Single-element tuples",
        ("tuple", "one-tuple", "trailing-comma", "singleton-tuple"),
        "Parentheses don't make a tuple; the comma does.",
        "t = (1)\nprint(type(t))  # <class 'int'>",
        "t = (1,)\nprint(type(t))  # <class 'tuple'>\nt = 1,          # parentheses optional",
        "`(1)` is just `1` grouped. The trailing comma is what builds the tuple.",
    ),
    GotchaInfo(
        "class-attribute",
        "Shared mutable class attributes",
        ("shared-class-attribute", "class-variable", "class-var", "class-vars"),
        "A list defined in the class body is shared by every instance.",
        "class Team:\n    members = []\n    def add(self, name):\n        self.members.append(name)\n\na, b = Team(), Team()\na.add(\"ann\")\nprint(b.members)  # ['ann']",
        "class Team:\n    def __init__(self):\n        self.members = []\n\n# dataclasses: members: list = field(default_factory=list)",
        "Attribute lookup falls through from the instance to the class, and `.append` mutates the one shared list.",
    ),
    GotchaInfo(
        "generator-exhaustion",
        "Exhausted generators",
        ("generator", "generators", "iterator-exhausted", "iterators", "one-shot"),
        "Generators and iterators can only be consumed once.",
        "squares = (n * n for n in range(3))\nprint(list(squares))  # [0, 1, 4]\nprint(list(squares))  # []",
        "squares = [n * n for n in range(3)]   # reusable list\n# or recreate it, or split it with itertools.tee",
        "An iterator remembers its position and never rewinds. The second `list()` starts at the end.",
    ),
    GotchaInfo(
        "sort-returns-none",
        "`list.sort()` returns `None`",
        ("sort", "sorted", "append-returns-none", "in-place"),
        "Methods that mutate in place, such as `sort`, `append`, `reverse` and `extend`, return `None`.",
        "nums = [3, 1, 2].sort()\nprint(nums)  # None",
        "nums = sorted([3, 1, 2])   # new sorted list\n# or\nnums = [3, 1, 2]\nnums.sort()",
        "Python separates mutating methods (return `None`) from functions that return new objects (`sorted`, `reversed`).",
    ),
    GotchaInfo(
        "bare-except",
        "Bare `except:`",
        ("except", "catch-all", "exception-swallowing", "except-exception"),
        "A bare `except:` also catches `KeyboardInterrupt` and `SystemExit`, and hides real bugs.",
        "try:\n    work()\nexcept:      # Ctrl+C can't stop this, typos vanish silently\n    pass",
        'try:\n    work()\nexcept (OSError, ValueError) as exc:  # name what you expect\n    logger.warning("failed: %s", exc)\n# last resort: except Exception, which still lets Ctrl+C through',
        "`BaseException` is the root, and `KeyboardInterrupt`, `SystemExit` and `GeneratorExit` derive from it directly, not from `Exception`.",
    ),
    GotchaInfo(
        "tuple-augmented",
        "`+=` on a list inside a tuple",
        ("tuple-plus-equals", "augmented-assignment", "tuple-mutation", "tuple-iadd"),
        "The assignment raises, but the mutation has already happened.",
        "t = ([1], 2)\ntry:\n    t[0] += [3]\nexcept TypeError as exc:\n    print(exc)  # 'tuple' object does not support item assignment\nprint(t)         # ([1, 3], 2)",
        "t[0].extend([3])  # mutate the list, no assignment needed",
        "`t[0] += x` does `t[0] = t[0].__iadd__(x)`. The in-place add succeeds on the list, then storing the result back into the tuple fails.",
    ),
    GotchaInfo(
        "eq-without-hash",
        "`__eq__` without `__hash__`",
        ("hash", "unhashable", "eq-hash", "hashable"),
        "Defining `__eq__` on a class sets `__hash__` to `None`, so instances can't go in sets or dict keys.",
        "class P:\n    def __init__(self, x):\n        self.x = x\n    def __eq__(self, other):\n        return self.x == other.x\n\n{P(1)}  # TypeError: unhashable type: 'P'",
        "class P:\n    def __init__(self, x):\n        self.x = x\n    def __eq__(self, other):\n        return isinstance(other, P) and self.x == other.x\n    def __hash__(self):\n        return hash(self.x)\n\n# or: @dataclass(frozen=True)",
        "Equal objects must have equal hashes, so Python refuses to inherit `object.__hash__` once you change equality. Only hash immutable data.",
    ),
    GotchaInfo(
        "strip-chars",
        "`str.strip` takes characters, not a substring",
        ("strip", "lstrip", "rstrip", "removesuffix", "removeprefix"),
        "`strip`, `lstrip` and `rstrip` remove any of the given *characters*.",
        'print("test.txt".strip(".txt"))  # \'es\'',
        'print("test.txt".removesuffix(".txt"))  # \'test\'   (3.9+)\nprint("v1.2".removeprefix("v"))        # \'1.2\'',
        "The argument is treated as a set of characters (`.`, `t`, `x`) removed from both ends until a different one appears.",
    ),
    GotchaInfo(
        "unbound-local",
        "`UnboundLocalError`",
        ("local-scope", "scope", "global-nonlocal", "unboundlocalerror"),
        "Assigning to a name anywhere in a function makes it local for the *whole* function.",
        "count = 0\ndef bump():\n    count += 1  # UnboundLocalError\n\nbump()",
        "count = 0\ndef bump():\n    global count\n    count += 1\n\n# better: return the new value, or keep state on an object",
        "The compiler decides a name is local if it is assigned anywhere in the body, so the read in `count += 1` finds an unset local.",
    ),
)


IDIOMS_DB: tuple[IdiomInfo, ...] = (
    IdiomInfo(
        "flatten",
        "Flatten a list of lists",
        ("flatten-list", "chain", "nested-list", "flat"),
        "Join nested iterables into one flat sequence.",
        "from itertools import chain\n\nnested = [[1, 2], [3], [4, 5]]\nflat = list(chain.from_iterable(nested))\n# [1, 2, 3, 4, 5]\n\n# comprehension version\nflat = [x for sub in nested for x in sub]",
        "One level only. For arbitrary depth you need recursion.",
    ),
    IdiomInfo(
        "group-by",
        "Group items by a key",
        ("groupby", "group", "bucket", "defaultdict"),
        "Collect items into buckets with `defaultdict`.",
        "from collections import defaultdict\n\ngroups = defaultdict(list)\nfor word in words:\n    groups[len(word)].append(word)\n\n# itertools.groupby needs sorted input:\nfrom itertools import groupby\nfor key, items in groupby(sorted(words, key=len), key=len): ...",
        "`itertools.groupby` only groups *adjacent* items, so sort by the same key first.",
    ),
    IdiomInfo(
        "read-file",
        "Read and write files",
        ("file", "open", "read", "write", "read-lines", "pathlib"),
        "Use `pathlib` for whole files and a `with` block for streaming.",
        'from pathlib import Path\n\ntext = Path("data.txt").read_text(encoding="utf-8")\nPath("out.txt").write_text(text, encoding="utf-8")\n\nwith open("big.log", encoding="utf-8") as f:\n    for line in f:   # lazy, one line at a time\n        handle(line.rstrip("\\n"))',
        "Always pass `encoding=` for text files so behaviour doesn't depend on the OS locale.",
    ),
    IdiomInfo(
        "count",
        "Count occurrences",
        ("counter", "frequency", "histogram", "most-common"),
        "`Counter` is a dict of counts with helpers.",
        "from collections import Counter\n\ncounts = Counter(\"mississippi\")\ncounts.most_common(2)   # [('i', 4), ('s', 4)]\ncounts[\"z\"]             # 0, missing keys count as zero",
    ),
    IdiomInfo(
        "dedupe",
        "Remove duplicates, keep order",
        ("unique", "uniq", "remove-duplicates", "dedup"),
        "Dicts preserve insertion order, so `dict.fromkeys` dedupes in order.",
        "items = [3, 1, 3, 2, 1]\nunique = list(dict.fromkeys(items))  # [3, 1, 2]\n\nset(items)  # unique too, but arbitrary order",
        "Items must be hashable.",
    ),
    IdiomInfo(
        "merge-dicts",
        "Merge dictionaries",
        ("dict-merge", "update-dict", "combine-dicts"),
        "Later keys win.",
        'a = {"x": 1, "y": 2}\nb = {"y": 3}\n\nmerged = a | b           # {\'x\': 1, \'y\': 3}  (3.9+)\nmerged = {**a, **b}      # works everywhere\na |= b                   # in place',
        "Both forms are shallow, so nested dicts are not merged recursively.",
        "3.9",
    ),
    IdiomInfo(
        "swap",
        "Swap variables",
        ("swap-variables", "tuple-unpacking", "unpack", "star-unpack"),
        "Tuple unpacking needs no temporary variable.",
        "a, b = b, a\n\nfirst, *rest = [1, 2, 3, 4]       # 1, [2, 3, 4]\nhead, *_, tail = [1, 2, 3, 4]    # 1, 4",
    ),
    IdiomInfo(
        "transpose",
        "Transpose a matrix",
        ("zip", "zip-star", "matrix", "columns"),
        "`zip(*rows)` turns rows into columns.",
        "matrix = [[1, 2, 3], [4, 5, 6]]\ncols = list(zip(*matrix))    # [(1, 4), (2, 5), (3, 6)]\n\nzip(a, b, strict=True)       # raise if lengths differ (3.10+)",
        "`zip` stops at the shortest input unless `strict=True`.",
    ),
    IdiomInfo(
        "chunk",
        "Split into chunks",
        ("batch", "batched", "split-list", "partition"),
        "`itertools.batched` yields tuples of up to `n` items.",
        "from itertools import batched\n\nfor batch in batched(range(7), 3):\n    print(batch)   # (0, 1, 2) (3, 4, 5) (6,)\n\n# before 3.12:\n[items[i:i + 3] for i in range(0, len(items), 3)]",
        "`batched` was added in 3.12; 3.13 added the `strict=` option.",
        "3.12",
    ),
    IdiomInfo(
        "sort-by-key",
        "Sort by one or more keys",
        ("sort", "sorted", "key", "custom-sort", "sort-objects"),
        "`key=` runs once per item, and tuples sort field by field.",
        'from operator import attrgetter, itemgetter\n\nsorted(people, key=lambda p: (p.age, p.name))\nsorted(rows, key=itemgetter("score"), reverse=True)\nsorted(people, key=attrgetter("name"))',
        "Sorting is stable, so you can sort twice (secondary key first) to combine criteria.",
    ),
    IdiomInfo(
        "invert-dict",
        "Invert a dictionary",
        ("reverse-dict", "swap-keys-values"),
        "Swap keys and values.",
        "d = {\"a\": 1, \"b\": 2}\ninverse = {v: k for k, v in d.items()}  # {1: 'a', 2: 'b'}",
        "Values must be unique and hashable, or later keys overwrite earlier ones.",
    ),
    IdiomInfo(
        "enumerate",
        "Loop with index",
        ("index", "loop-index", "range-len", "enumerate-loop"),
        "Use `enumerate` instead of `range(len(...))`.",
        "for i, name in enumerate(names, start=1):\n    print(i, name)",
    ),
    IdiomInfo(
        "any-all",
        "Test a condition across items",
        ("any", "all", "exists", "predicate"),
        "`any` and `all` short-circuit over a generator.",
        "any(n > 3 for n in nums)        # at least one\nall(s.strip() for s in lines)   # every one truthy\nnot any(...)                    # none",
        "Pass a generator expression, not a list, so evaluation can stop early.",
    ),
    IdiomInfo(
        "max-by",
        "Find the max or min by a key",
        ("max", "min", "largest", "smallest", "argmax"),
        "`key=` and `default=` cover most cases.",
        "longest = max(words, key=len, default=None)\ncheapest = min(items, key=lambda i: i.price)",
        "`default=` avoids `ValueError` on an empty iterable.",
    ),
    IdiomInfo(
        "context-manager",
        "Write a context manager",
        ("contextmanager", "with-statement", "contextlib", "setup-teardown"),
        "`contextlib.contextmanager` turns a generator into one.",
        'from contextlib import contextmanager\nimport time\n\n@contextmanager\ndef timer(label):\n    start = time.perf_counter()\n    try:\n        yield\n    finally:\n        print(label, time.perf_counter() - start)\n\nwith timer("work"):\n    do_work()',
        "Wrap `yield` in `try/finally` so cleanup runs on exceptions.",
    ),
    IdiomInfo(
        "timing",
        "Time a piece of code",
        ("timeit", "perf-counter", "benchmark", "stopwatch"),
        "Use `perf_counter` for elapsed time and `timeit` for micro-benchmarks.",
        'import time, timeit\n\nstart = time.perf_counter()\nwork()\nprint(time.perf_counter() - start)\n\ntimeit.timeit("sum(range(100))", number=10_000)',
        "Don't use `time.time()` for durations, because the system clock can jump.",
    ),
    IdiomInfo(
        "walrus",
        "Assign inside an expression",
        ("walrus-operator", "assignment-expression", "named-expression"),
        "`:=` binds and returns a value in one step.",
        'if (n := len(data)) > 10:\n    print(f"{n} items")\n\nwhile (chunk := f.read(4096)):\n    process(chunk)',
        "Needs 3.8+. Skip it when a plain assignment is just as clear.",
        "3.8",
    ),
    IdiomInfo(
        "pairwise",
        "Iterate over consecutive pairs",
        ("sliding-window", "consecutive", "neighbors", "adjacent"),
        "`itertools.pairwise` yields overlapping pairs.",
        "from itertools import pairwise\n\nlist(pairwise([1, 4, 9, 16]))  # [(1, 4), (4, 9), (9, 16)]\ndiffs = [b - a for a, b in pairwise(nums)]",
        "",
        "3.10",
    ),
    IdiomInfo(
        "json",
        "Read and write JSON",
        ("json-file", "serialize", "dump", "loads"),
        "`load` / `dump` work on files, `loads` / `dumps` on strings.",
        'import json\nfrom pathlib import Path\n\ndata = json.loads(Path("in.json").read_text(encoding="utf-8"))\nPath("out.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")',
        "Keys become strings; tuples become lists; `datetime` needs a custom `default=`.",
    ),
    IdiomInfo(
        "subprocess",
        "Run a command",
        ("shell", "run-command", "exec", "os-system"),
        "`subprocess.run` with a list of arguments, never a shell string built from user input.",
        'import subprocess\n\nresult = subprocess.run(\n    ["git", "status", "--short"],\n    capture_output=True, text=True, check=True, timeout=30,\n)\nprint(result.stdout)',
        "`check=True` raises `CalledProcessError` on a non-zero exit code.",
    ),
    IdiomInfo(
        "dataclass",
        "Define a simple data class",
        ("dataclasses", "record", "struct", "namedtuple"),
        "`@dataclass` writes `__init__`, `__repr__` and `__eq__` for you.",
        "from dataclasses import dataclass, field\n\n@dataclass(frozen=True, slots=True)\nclass Point:\n    x: float\n    y: float = 0.0\n    tags: tuple[str, ...] = ()\n\n@dataclass\nclass Team:\n    members: list[str] = field(default_factory=list)",
        "`slots=True` needs 3.10+. Mutable defaults require `field(default_factory=...)`.",
        "3.7",
    ),
    IdiomInfo(
        "dict-get",
        "Get dictionary value with fallback",
        ("get", "setdefault", "default-value", "fallback"),
        "Use `dict.get()` to avoid `KeyError` or `dict.setdefault()` to initialize.",
        'user = data.get("user", "Guest")\n\n# setdefault returns the value, setting it if missing\ncache.setdefault(key, []).append(value)',
        "`get()` does not modify the dict, whereas `setdefault()` does.",
    ),
    IdiomInfo(
        "suppress",
        "Ignore specific exceptions",
        ("try-except-pass", "ignore-error", "contextlib-suppress", "silence"),
        "`contextlib.suppress` replaces `try/except/pass` with a clean context manager.",
        "from contextlib import suppress\nimport os\n\nwith suppress(FileNotFoundError):\n    os.remove('somefile.tmp')",
        "Only catches the exact exceptions provided.",
    ),
    IdiomInfo(
        "memoize",
        "Cache function results",
        ("cache", "lru-cache", "memoization", "functools"),
        "`@cache` or `@lru_cache` saves the results of expensive function calls.",
        "from functools import cache, lru_cache\n\n@cache\ndef fibonacci(n):\n    if n < 2: return n\n    return fibonacci(n - 1) + fibonacci(n - 2)\n\n@lru_cache(maxsize=128)\ndef fetch_url(url): ...",
        "Arguments to the cached function must be hashable. `@cache` was added in 3.9.",
        "3.2",
    ),
    IdiomInfo(
        "remove-affix",
        "Remove string prefix or suffix",
        ("removeprefix", "removesuffix", "strip-string", "trim"),
        "`str.removeprefix()` safely removes exact substrings, unlike `lstrip()`/`rstrip()`.",
        'filename = "data_backup.csv"\nname = filename.removesuffix(".csv")\n\nurl = "https://example.com"\ndomain = url.removeprefix("https://")',
        "`strip()` removes sets of characters, while these remove exact substrings.",
        "3.9",
    ),
    IdiomInfo(
        "match-case",
        "Structural pattern matching",
        ("match", "case", "switch-statement", "pattern-matching"),
        "`match/case` replaces complex if/elif chains and easily unpacks sequences or objects.",
        'def handle_command(cmd):\n    match cmd.split():\n        case ["quit"]:\n            return "Goodbye!"\n        case ["go", direction] if direction in ("north", "south"):\n            return f"Walking {direction}"\n        case _:\n            return "Unknown command"',
        "You can match literal values, shapes, types, and add `if` guards.",
        "3.10",
    ),
    IdiomInfo(
        "iter-sentinel",
        "Call a function until a sentinel value",
        ("iter", "while-loop", "read-chunks", "sentinel"),
        "The two-argument form of `iter(callable, sentinel)` yields until the sentinel is returned.",
        'from functools import partial\n\nwith open("binary_data", "rb") as f:\n    # Read 1024-byte chunks until reaching an empty bytes object\n    for chunk in iter(partial(f.read, 1024), b""):\n        process(chunk)',
        "A cleaner alternative to an infinite `while True:` loop with a `break` inside.",
    ),
    IdiomInfo(
        "chain-map",
        "Search across multiple dictionaries",
        ("chainmap", "multiple-dicts", "scope", "fallback-dict"),
        "`collections.ChainMap` groups multiple dicts into a single view without copying.",
        "from collections import ChainMap\n\ndefaults = {'color': 'red', 'user': 'guest'}\ncommand_line_args = {'user': 'admin'}\n\n# Lookups check command_line_args first, then defaults\nconfig = ChainMap(command_line_args, defaults)\nconfig['user']   # 'admin'\nconfig['color']  # 'red'",
        "Writes/updates only ever affect the first dictionary in the chain.",
    ),
    IdiomInfo(
        "f-strings",
        "Format strings cleanly",
        ("f-string", "format", "interpolation", "debug-string"),
        "Prefix strings with `f` to embed expressions, and use `=` for easy debugging.",
        'name = "Alice"\nage = 30\nprint(f"User {name} is {age} years old.")\n\n# Debugging feature (Python 3.8+):\nprint(f"{name=}, {age=}")  # name=\'Alice\', age=30\n\n# Formatting:\npi = 3.14159\nprint(f"Pi rounded: {pi:.2f}")',
        "Evaluated at runtime; generally faster than `.format()` or `%` formatting.",
        "3.6",
    ),
    IdiomInfo(
        "generator-expr",
        "Lazy list comprehension",
        ("generator", "yield", "memory-efficient", "comprehension"),
        "Use parentheses instead of brackets to process large datasets without blowing up memory.",
        '# List comprehension: builds the entire list in memory\nsquares_list = [x*x for x in range(1_000_000)]\n\n# Generator expression: computes one item at a time\nsquares_gen = (x*x for x in range(1_000_000))\nsum_of_squares = sum(squares_gen)',
        "Generator expressions can only be iterated over once.",
    ),
    IdiomInfo(
        "type-hints",
        "Add static typing to variables and functions",
        ("typing", "type-hints", "annotations", "mypy"),
        "Annotate variables, arguments, and return types to catch bugs before running.",
        'def greet(name: str, age: int | None = None) -> str:\n    if age:\n        return f"Hi {name}, you are {age}."\n    return f"Hi {name}."\n\nnumbers: list[int] = [1, 2, 3]',
        "The `|` syntax for unions (e.g., `int | None`) was introduced in Python 3.10.",
        "3.5",
    )
)


_TYPING = "library/typing.html"


def _create_typing_info(key: str, title: str, aliases: tuple[str, ...], summary: str, example: str, since: str | None, doc: str) -> TypingInfo:
    return TypingInfo(key, title, aliases, summary, example, since, doc)


TYPING_DB: tuple[TypingInfo, ...] = (
    _create_typing_info(
        "protocol",
        "Protocol",
        ("structural", "duck-typing", "structural-typing"),
        "Structural typing: any class with the right methods matches, no inheritance needed.",
        "from typing import Protocol\n\nclass SupportsClose(Protocol):\n    def close(self) -> None: ...\n\ndef shutdown(res: SupportsClose) -> None:\n    res.close()   # any object with .close() is accepted",
        "3.8",
        f"{_TYPING}#typing.Protocol",
    ),
    _create_typing_info(
        "typevar",
        "TypeVar and generics",
        ("generic-function", "generics", "t", "typevars", "pep695"),
        "A placeholder that links types in a signature, e.g. input and output.",
        '# 3.12+ syntax (PEP 695)\ndef first[T](items: list[T]) -> T:\n    return items[0]\n\nclass Stack[T]:\n    def push(self, item: T) -> None: ...\n\n# before 3.12\nT = TypeVar("T")\ndef first(items: list[T]) -> T: ...',
        "3.5",
        f"{_TYPING}#typing.TypeVar",
    ),
    _create_typing_info(
        "generic",
        "Generic",
        ("generic-class", "generic-base"),
        "Base class for user-defined generic classes (before the 3.12 `class Box[T]` syntax).",
        'from typing import Generic, TypeVar\n\nT = TypeVar("T")\n\nclass Box(Generic[T]):\n    def __init__(self, item: T) -> None:\n        self.item = item\n\nBox(3)  # Box[int]',
        "3.5",
        f"{_TYPING}#typing.Generic",
    ),
    _create_typing_info(
        "paramspec",
        "ParamSpec",
        ("decorator-typing", "param-spec", "p-args"),
        "Captures a callable's whole parameter list so decorators keep the wrapped signature.",
        "from collections.abc import Callable\nfrom functools import wraps\n\ndef logged[**P, R](fn: Callable[P, R]) -> Callable[P, R]:\n    @wraps(fn)\n    def inner(*args: P.args, **kwargs: P.kwargs) -> R:\n        print(fn.__name__)\n        return fn(*args, **kwargs)\n    return inner",
        "3.10",
        f"{_TYPING}#typing.ParamSpec",
    ),
    _create_typing_info(
        "typevartuple",
        "TypeVarTuple / Unpack",
        ("variadic", "unpack", "typevar-tuple", "star-args-typing"),
        "A variadic generic: abstracts over a variable number of types, e.g. array shapes.",
        'def args_to_tuple[*Ts](*args: *Ts) -> tuple[*Ts]:\n    return args\n\nargs_to_tuple(1, "a")  # tuple[int, str]',
        "3.11",
        f"{_TYPING}#typing.TypeVarTuple",
    ),
    _create_typing_info(
        "typeddict",
        "TypedDict",
        ("typed-dict", "dict-schema", "json-typing"),
        "Describes a dict with a fixed set of string keys and per-key types. Plain dict at runtime.",
        'from typing import TypedDict, NotRequired\n\nclass Movie(TypedDict):\n    title: str\n    year: NotRequired[int]\n\nm: Movie = {"title": "Alien"}',
        "3.8",
        f"{_TYPING}#typing.TypedDict",
    ),
    _create_typing_info(
        "required",
        "Required / NotRequired / ReadOnly",
        ("notrequired", "readonly", "read-only", "total"),
        "Mark individual `TypedDict` keys as required, optional, or read-only.",
        "from typing import TypedDict, Required, NotRequired, ReadOnly\n\nclass Config(TypedDict, total=False):\n    name: Required[str]\n    debug: bool\n    id: ReadOnly[int]   # 3.13+",
        "3.11",
        f"{_TYPING}#typing.NotRequired",
    ),
    _create_typing_info(
        "namedtuple",
        "NamedTuple",
        ("named-tuple", "typed-namedtuple"),
        "Typed, immutable record with tuple behaviour.",
        "from typing import NamedTuple\n\nclass Point(NamedTuple):\n    x: float\n    y: float = 0.0\n\nPoint(1.0).x   # 1.0\nx, y = Point(1, 2)",
        "3.6",
        f"{_TYPING}#typing.NamedTuple",
    ),
    _create_typing_info(
        "literal",
        "Literal",
        ("literals", "enum-like", "exact-value"),
        "Restricts a value to specific literals.",
        'from typing import Literal\n\ndef open_file(mode: Literal["r", "w", "a"]) -> None: ...\n\nopen_file("x")  # type checker error',
        "3.8",
        f"{_TYPING}#typing.Literal",
    ),
    _create_typing_info(
        "final",
        "Final and @final",
        ("constant", "constants", "no-override", "final-decorator"),
        "`Final` marks a name as never reassigned; `@final` stops a class being subclassed or a method overridden.",
        "from typing import Final, final\n\nMAX_RETRIES: Final = 3\n\n@final\nclass Config: ...",
        "3.8",
        f"{_TYPING}#typing.Final",
    ),
    _create_typing_info(
        "classvar",
        "ClassVar",
        ("class-var", "class-variable-typing"),
        "Marks an attribute as belonging to the class, not instances. Dataclasses skip it.",
        "from typing import ClassVar\n\nclass Counter:\n    total: ClassVar[int] = 0\n    name: str",
        "3.5.3",
        f"{_TYPING}#typing.ClassVar",
    ),
    _create_typing_info(
        "optional",
        "Optional and Union",
        ("union", "none", "x-or-none", "pipe", "or-none"),
        "`X | Y` means either type. `Optional[X]` is just `X | None`.",
        "def find(name: str) -> int | None: ...\n\ndef parse(v: int | str | None = None) -> str: ...\n\n# older: Optional[int], Union[int, str]",
        "3.10",
        f"{_TYPING}#typing.Optional",
    ),
    _create_typing_info(
        "callable",
        "Callable",
        ("function-type", "callback", "callables"),
        "Types a function or callback: `Callable[[arg types], return type]`. Import it from `collections.abc`.",
        'from collections.abc import Callable\n\ndef apply(fn: Callable[[int, str], bool], n: int) -> bool:\n    return fn(n, "x")\n\nhandler: Callable[..., None]   # any arguments',
        "3.9",
        "library/collections.abc.html#collections.abc.Callable",
    ),
    _create_typing_info(
        "annotated",
        "Annotated",
        ("metadata", "annotation-metadata", "field-constraints"),
        "Attaches extra metadata to a type without changing it. Libraries read it.",
        'from typing import Annotated\n\nMeters = Annotated[float, "unit: m"]\n\ndef run(distance: Meters) -> None: ...\n# e.g. pydantic: Annotated[int, Field(gt=0)]',
        "3.9",
        f"{_TYPING}#typing.Annotated",
    ),
    _create_typing_info(
        "type-alias",
        "Type aliases (`type` statement)",
        ("alias", "typealias", "type-statement", "type-keyword"),
        "Names a complex type. The `type` statement (3.12) is lazy, so aliases can refer to themselves.",
        "type Vector = list[float]\ntype Json = dict[str, Json] | list[Json] | str | int | None\n\n# before 3.12\nfrom typing import TypeAlias\nVector: TypeAlias = list[float]",
        "3.12",
        "reference/simple_stmts.html#type",
    ),
    _create_typing_info(
        "overload",
        "overload",
        ("overloads", "multiple-signatures"),
        "Declares several signatures for a function that has one real implementation.",
        "from typing import overload\n\n@overload\ndef load(x: str) -> str: ...\n@overload\ndef load(x: bytes) -> bytes: ...\ndef load(x):\n    return x",
        "3.5",
        f"{_TYPING}#typing.overload",
    ),
    _create_typing_info(
        "self",
        "Self",
        ("self-type", "return-self", "fluent"),
        "The type of the current class, correct in subclasses too. Good for builders and `__enter__`.",
        "from typing import Self\n\nclass Builder:\n    def add(self, x: int) -> Self:\n        ...\n        return self",
        "3.11",
        f"{_TYPING}#typing.Self",
    ),
    _create_typing_info(
        "typeguard",
        "TypeGuard / TypeIs",
        ("type-guard", "typeis", "type-is", "narrowing", "narrow"),
        "Lets a function tell the type checker how to narrow a value. `TypeIs` (3.13) also narrows the `else` branch.",
        "from typing import TypeIs\n\ndef is_str(x: object) -> TypeIs[str]:\n    return isinstance(x, str)\n\ndef f(v: int | str):\n    if is_str(v):\n        v.upper()   # str here, int in the else branch",
        "3.13",
        f"{_TYPING}#typing.TypeIs",
    ),
    _create_typing_info(
        "never",
        "Never / NoReturn",
        ("noreturn", "bottom", "unreachable", "assert-never"),
        "`NoReturn` is for functions that never return; `Never` is the empty type, handy for exhaustive checks.",
        "from typing import NoReturn, assert_never\n\ndef fail(msg: str) -> NoReturn:\n    raise RuntimeError(msg)\n\ndef handle(x: int | str) -> None:\n    match x:\n        case int(): ...\n        case str(): ...\n        case _:\n            assert_never(x)",
        "3.11",
        f"{_TYPING}#typing.Never",
    ),
    _create_typing_info(
        "any",
        "Any / object",
        ("dynamic", "untyped"),
        "`Any` opts out of checking. `object` accepts anything but only allows what every object supports.",
        "from typing import Any\n\ndef f(x: Any) -> None:\n    x.whatever()   # allowed\n\ndef g(x: object) -> None:\n    x.whatever()   # error",
        "3.5",
        f"{_TYPING}#typing.Any",
    ),
    _create_typing_info(
        "cast",
        "cast",
        ("casting", "type-cast"),
        'Tells the checker "trust me". Does nothing at runtime, so validate first when unsure.',
        'from typing import cast\n\nvalue = cast("list[int]", data)',
        "3.5",
        f"{_TYPING}#typing.cast",
    ),
    _create_typing_info(
        "override",
        "override",
        ("overriding", "method-override"),
        "Marks a method as overriding a parent method, so the checker complains if the parent changes.",
        "from typing import override\n\nclass Child(Parent):\n    @override\n    def run(self) -> None: ...",
        "3.12",
        f"{_TYPING}#typing.override",
    ),
    _create_typing_info(
        "type-checking",
        "TYPE_CHECKING",
        ("typecheckingconstant", "circular-import", "forward-reference", "forward-ref"),
        "`False` at runtime and `True` for checkers. Guards imports needed only for annotations, avoiding cycles.",
        "from __future__ import annotations\nfrom typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from .models import User\n\ndef load(uid: int) -> User: ...",
        "3.5.2",
        f"{_TYPING}#typing.TYPE_CHECKING",
    ),
    _create_typing_info(
        "abc",
        "Abstract collection types",
        ("sequence", "mapping", "iterable", "collections-abc", "abstract-types", "list-vs-sequence"),
        "Annotate parameters with the loosest ABC that works (`Iterable`, `Sequence`, `Mapping`) and return concrete types.",
        "from collections.abc import Iterable, Mapping, Sequence\n\ndef total(xs: Iterable[int]) -> int:\n    return sum(xs)\n\ndef lookup(m: Mapping[str, int], k: str) -> int:\n    return m[k]",
        "3.9",
        "library/collections.abc.html",
    ),
)
