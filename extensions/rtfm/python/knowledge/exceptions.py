from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExceptionInfo:
    name: str
    category: str
    summary: str
    causes: tuple[str, ...]
    fix: str
    example: str
    anchor: str | None = None


EXCEPTIONS_DB: dict[str, ExceptionInfo] = {
    "SyntaxError": ExceptionInfo(
        name="SyntaxError",
        category="Compiler / Parser Error",
        summary="Raised when the parser encounters source code that violates Python's grammar rules.",
        causes=(
            "Unclosed parentheses `(`, brackets `[`, braces `{`, or string quotes",
            "Missing colon `:` after `if`, `for`, `while`, `def`, `class`, or `match`",
            "Using assignment `=` instead of comparison `==` or walrus `:=` inside an expression",
            "Using a reserved keyword (like `class`, `from`, `async`, `lambda`) as a variable name",
        ),
        fix="Check the caret `^` marker and the line immediately above it for unclosed delimiters or missing colons.",
        example="# Bad\nif user = 'admin'\n    print('hi')\n\n# Good\nif user == 'admin':\n    print('hi')",
    ),
    "IndentationError": ExceptionInfo(
        name="IndentationError",
        category="SyntaxError Subclass",
        summary="Raised when indentation levels are inconsistent or a required indented block is missing.",
        causes=(
            "Leaving an empty suite after `def`, `if`, `for`, or `class` without `pass` or `...`",
            "Mixing tabs and spaces in the same file (raises `TabError`)",
            "Misaligned spaces when copying and pasting code blocks",
        ),
        fix="Configure your editor to insert 4 spaces per tab (PEP 8) and add `pass` or `...` to empty blocks.",
        example="# Bad\ndef todo():\n\n# Good\ndef todo() -> None:\n    ...",
    ),
    "TabError": ExceptionInfo(
        name="TabError",
        category="IndentationError Subclass",
        summary="Raised when indentation contains an inconsistent mix of tabs and spaces in the same block.",
        causes=("Mixing literal `\\t` tab characters and space characters within the same file.",),
        fix="Convert all tabs to 4 spaces in your editor (`Expand Tabs to Spaces`).",
        example="# Configure your editor/formatter (e.g., ruff format / black) to standardize on 4 spaces.",
    ),
    "TypeError": ExceptionInfo(
        name="TypeError",
        category="Runtime Error",
        summary="Raised when an operation or function is applied to an object of an inappropriate type.",
        causes=(
            "Concatenating `str` and `int` directly (`'Age: ' + 20`)",
            "Calling a non-callable object (`len = 5; len('abc')` or indexing a function `func[0]`)",
            "Passing the wrong number of positional or keyword arguments to a function",
            "Passing an unhashable mutable object (`list`, `dict`, `set`) as a `dict` key or `set` element",
        ),
        fix="Inspect types with `type(obj)` or static type checking, use f-strings (`f'Age: {age}'`), and convert mutable keys to `tuple`.",
        example="# Bad\nresult = 'Count: ' + 42\n\n# Good\nresult = f'Count: {42}'",
    ),
    "ValueError": ExceptionInfo(
        name="ValueError",
        category="Runtime Error",
        summary="Raised when an argument has the right type, but an inappropriate or unparseable value.",
        causes=(
            "Converting a non-numeric string with `int('abc')` or `float('N/A')`",
            "Unpacking a sequence into the wrong number of variables (`a, b = [1, 2, 3]`)",
            "Calling `list.remove(x)` or `list.index(x)` when `x` is not in the list",
            "Passing out-of-domain math inputs like `math.sqrt(-1)`",
        ),
        fix="Validate input before conversion, or catch `ValueError` in a narrow `try ... except ValueError:` block.",
        example="raw = '42a'\ntry:\n    number = int(raw)\nexcept ValueError:\n    number = 0",
    ),
    "KeyError": ExceptionInfo(
        name="KeyError",
        category="LookupError Subclass",
        summary="Raised when a mapping (`dict`, `os.environ`) key is not found in the set of existing keys.",
        causes=(
            "Accessing `data['missing']` directly when the key is optional",
            "Removing a non-existent element from a set with `set.remove(x)`",
            "Unescaped `{braces}` inside a `str.format()` template string",
        ),
        fix="Use `data.get('key', default)` for optional keys, `collections.defaultdict` for grouping, or `set.discard(x)`.",
        example="# Bad\ntoken = payload['token']\n\n# Good\ntoken = payload.get('token')",
    ),
    "IndexError": ExceptionInfo(
        name="IndexError",
        category="LookupError Subclass",
        summary="Raised when a sequence subscript (`list`, `tuple`, `str`) is out of range.",
        causes=(
            "Indexing `items[0]` or `items[-1]` on an empty list `[]`",
            "Off-by-one loop bounds (`items[len(items)]` instead of `items[len(items) - 1]`)",
            "Mutating/popping from a list while iterating over its indices",
        ),
        fix="Check `if items:` before indexing, iterate directly over elements (`for item in items:`), or slice (`items[:1]`).",
        example="# Safe first element\nfirst = items[0] if items else None",
    ),
    "AttributeError": ExceptionInfo(
        name="AttributeError",
        category="Runtime Error",
        summary="Raised when an attribute reference or assignment fails on an object.",
        causes=(
            "Calling a method on `None` (`NoneType object has no attribute ...`) because an earlier lookup returned `None`",
            "Misspelling a method or attribute name (e.g. `list.add()` instead of `list.append()`)",
            "Assigning a new attribute to an object using `__slots__`",
            "Shadowing a standard library module with a local file of the same name (e.g. naming your script `discord.py` or `random.py`)",
        ),
        fix="Guard `None` values (`if obj is not None:`), check `dir(obj)`, and ensure none of your local files shadow library names.",
        example="match = re.search(r'\\d+', text)\nif match is not None:\n    print(match.group(0))",
    ),
    "NameError": ExceptionInfo(
        name="NameError",
        category="Runtime Error",
        summary="Raised when a local or global variable name is not found in any enclosing scope.",
        causes=(
            "Typo in a variable or function identifier",
            "Using a variable that was only defined inside an `if` or `try` branch that did not execute",
            "Forgetting to import a module or symbol before referencing it",
        ),
        fix="Initialize variables before conditional branches and verify imports at the top of the module.",
        example="result = None\nif condition:\n    result = compute()\nprint(result)",
    ),
    "UnboundLocalError": ExceptionInfo(
        name="UnboundLocalError",
        category="NameError Subclass",
        summary="Raised when a local variable is referenced in a function before it has been assigned a value.",
        causes=(
            "Mutating/reassigning an outer/global variable (`count += 1`) inside a function without `global` or `nonlocal`",
            "Assigning to a variable later in the function body after reading it earlier",
        ),
        fix="Declare `nonlocal var` (for closures) or `global var` (for module state), or pass the value as a parameter and return the updated value.",
        example="def make_counter():\n    count = 0\n    def inc() -> int:\n        nonlocal count\n        count += 1\n        return count\n    return inc",
    ),
    "ImportError": ExceptionInfo(
        name="ImportError",
        category="Module Loading Error",
        summary="Raised when an `import` statement fails to load a module or cannot find a requested name inside it.",
        causes=(
            "Circular imports between two modules that import symbols from each other at import time",
            "Importing a symbol that was renamed or removed in a newer package version",
            "Relative import (`from . import x`) executed in a script run directly rather than as a package (`python -m pkg.mod`)",
        ),
        fix="Break circular imports by moving type-only imports under `if TYPE_CHECKING:` and running packages with `python -m`.",
        example="from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from .bot import Bot",
    ),
    "ModuleNotFoundError": ExceptionInfo(
        name="ModuleNotFoundError",
        category="ImportError Subclass",
        summary="Raised when a module cannot be located at all in `sys.path`.",
        causes=(
            "Package is not installed in the active virtual environment",
            "Running the script with a different Python interpreter than the one `pip` installed into",
            "Misspelling the import name (e.g. `import beautifulsoup4` instead of `import bs4`, or `import PIL` for `Pillow`)",
        ),
        fix="Always install with `python -m pip install <pkg>` using the exact interpreter that runs your script.",
        example="# Install into the matching interpreter\n# python3 -m pip install aiohttp",
    ),
    "ZeroDivisionError": ExceptionInfo(
        name="ZeroDivisionError",
        category="ArithmeticError Subclass",
        summary="Raised when the second argument of a division (`/`, `//`) or modulo (`%`, `divmod`) operation is zero.",
        causes=(
            "Computing an average `total / len(items)` when `items` is empty",
            "Computing percentages or ratios where the denominator can be `0`",
        ),
        fix="Check the denominator before dividing (`total / count if count else 0.0`).",
        example="average = sum(scores) / len(scores) if scores else 0.0",
    ),
    "OverflowError": ExceptionInfo(
        name="OverflowError",
        category="ArithmeticError Subclass",
        summary="Raised when the result of an arithmetic operation is too large to be represented (typically in `float` or C-level fixed integers).",
        causes=(
            "Float exponentiation exceeding `sys.float_info.max` (~`1.8e308`), such as `math.exp(1000)` or `10.0 ** 400`",
            "Passing an integer larger than 64 bits to a C extension expecting a C `long`",
        ),
        fix="Use integer arithmetic (`int` has arbitrary precision in Python), `decimal.Decimal`, or work in log-space (`math.log`).",
        example="# Python ints have arbitrary precision, but floats overflow at ~1.8e308:\nbig_int = 10 ** 500  # OK",
    ),
    "FileNotFoundError": ExceptionInfo(
        name="FileNotFoundError",
        category="OSError Subclass",
        summary="Raised when a file or directory is requested but does not exist (errno `ENOENT`).",
        causes=(
            "Relative paths resolved against the current working directory (`os.getcwd()`) instead of the script's directory",
            "Writing to a file inside a parent directory that hasn't been created yet",
        ),
        fix="Anchor paths relative to `Path(__file__).resolve().parent` and call `path.parent.mkdir(parents=True, exist_ok=True)` before writing.",
        example="from pathlib import Path\nBASE_DIR = Path(__file__).resolve().parent\ndata = (BASE_DIR / 'config.json').read_text(encoding='utf-8')",
    ),
    "PermissionError": ExceptionInfo(
        name="PermissionError",
        category="OSError Subclass",
        summary="Raised when trying to run an operation without adequate filesystem or OS access rights (`EACCES`, `EPERM`).",
        causes=(
            "Opening a directory path with `open()` as if it were a file",
            "Writing to a protected system path or a file locked by another process on Windows",
        ),
        fix="Check `path.is_file()` before opening, and verify user permissions (`chmod` / file ownership).",
        example="if path.is_file():\n    content = path.read_text(encoding='utf-8')",
    ),
    "TimeoutError": ExceptionInfo(
        name="TimeoutError",
        category="OSError Subclass",
        summary="Raised when a system function or `asyncio.timeout()` / `asyncio.wait_for()` exceeds its deadline.",
        causes=(
            "A network request or coroutine took longer than the configured timeout window",
            "`asyncio.timeout(seconds)` context manager expired",
        ),
        fix="Wrap network and slow async calls in `async with asyncio.timeout(10):` and handle `TimeoutError` gracefully.",
        example="async with asyncio.timeout(10):\n    data = await fetch_remote()",
    ),
    "RecursionError": ExceptionInfo(
        name="RecursionError",
        category="RuntimeError Subclass",
        summary="Raised when the interpreter detects that the maximum recursion depth (`sys.getrecursionlimit()`, default 1000) is exceeded.",
        causes=(
            "Missing or unreachable base case in a recursive function",
            "A property getter (`@property def x(self): return self.x`) calling itself instead of `self._x`",
            "Deep graph/tree traversal on large inputs without an explicit stack",
        ),
        fix="Verify your base case, fix self-referential properties (`self._x`), or rewrite deep traversals iteratively using a `list`/`deque` stack.",
        example="# Bad\n@property\ndef name(self) -> str:\n    return self.name  # infinite recursion!\n\n# Good\n@property\ndef name(self) -> str:\n    return self._name",
    ),
    "StopIteration": ExceptionInfo(
        name="StopIteration",
        category="Iterator Signal",
        summary="Raised by `next(iterator)` to signal that there are no further items produced by the iterator.",
        causes=(
            "Calling `next(it)` manually without providing a default value when the iterator may be exhausted",
            "Raising `StopIteration` directly inside a generator (PEP 479 converts this into a `RuntimeError`)",
        ),
        fix="Pass a fallback default `next(it, None)` and use `return` instead of `raise StopIteration` inside generators.",
        example="first_even = next((x for x in nums if x % 2 == 0), None)",
    ),
    "UnicodeDecodeError": ExceptionInfo(
        name="UnicodeDecodeError",
        category="ValueError / UnicodeError Subclass",
        summary="Raised when a byte sequence cannot be decoded using the specified text encoding (such as UTF-8 or cp1252).",
        causes=(
            "Opening a UTF-8 file on Windows without specifying `encoding='utf-8'`",
            "Attempting to `.decode('utf-8')` binary data (images, compressed payloads, or Latin-1 encoded files)",
        ),
        fix="Always pass `encoding='utf-8'` to `open()` / `Path.read_text()`, or use `errors='replace'` when decoding untrusted bytes.",
        example="text = raw_bytes.decode('utf-8', errors='replace')",
    ),
    "RuntimeError": ExceptionInfo(
        name="RuntimeError",
        category="Runtime Error",
        summary="Raised when an error does not fall into a more specific category, such as mutating a dict/set during iteration or event-loop misuse.",
        causes=(
            "`dictionary changed size during iteration` when adding/deleting keys inside `for k in d:`",
            "`Set changed size during iteration` when mutating a set while looping over it",
            "Calling `asyncio.run()` from inside an already running event loop",
        ),
        fix="Iterate over a snapshot (`for k in list(d):`) when mutating collections, and `await` coroutines directly inside async functions.",
        example="for key in list(cache):\n    if is_expired(cache[key]):\n        del cache[key]",
    ),
    "NotImplementedError": ExceptionInfo(
        name="NotImplementedError",
        category="RuntimeError Subclass",
        summary="Raised by abstract methods in user base classes to indicate that subclasses must override the method.",
        causes=(
            "Calling a base class method that is meant to be overridden by a subclass",
            "Returning `NotImplementedError` instead of `NotImplemented` from binary special methods like `__eq__` or `__add__`",
        ),
        fix="Use `@abc.abstractmethod` on abstract base classes so instantiation fails early, and return `NotImplemented` (not raise `NotImplementedError`) in `__eq__`/`__lt__`.",
        example="class Plugin(abc.ABC):\n    @abc.abstractmethod\n    async def run(self) -> None:\n        raise NotImplementedError",
    ),
    "AssertionError": ExceptionInfo(
        name="AssertionError",
        category="Runtime Error",
        summary="Raised when an `assert` statement fails.",
        causes=(
            "An internal invariant check (`assert x > 0`) evaluated to `False`",
            "Using `assert` for user-input validation (note: `python -O` strips all `assert` statements!)",
        ),
        fix="Use `assert` only for internal invariants and unit tests; raise `ValueError` or `TypeError` for runtime input validation.",
        example="if amount <= 0:\n    raise ValueError('Amount must be positive')",
    ),
    "MemoryError": ExceptionInfo(
        name="MemoryError",
        category="Runtime Error",
        summary="Raised when an operation runs out of available RAM.",
        causes=(
            "Materializing a huge list (`list(range(10**10))` or `.read()` on a multi-GB file) in memory at once",
            "Unbounded in-memory caches without an eviction policy",
        ),
        fix="Stream files line-by-line or in chunks, use generators/iterators, and bound caches with `@functools.lru_cache(maxsize=...)`.",
        example="with open('huge.log', encoding='utf-8') as fp:\n    for line in fp:  # streams one line at a time in O(1) memory\n        process(line)",
    ),
    "EOFError": ExceptionInfo(
        name="EOFError",
        category="Runtime Error",
        summary="Raised when `input()` hits an end-of-file condition (Ctrl-D / Ctrl-Z or closed stdin pipe) without reading any data.",
        causes=("Calling `input()` in a non-interactive environment or after stdin is exhausted.",),
        fix="Wrap `input()` loops in `try ... except EOFError:` or iterate over `sys.stdin`.",
        example="try:\n    line = input('Prompt: ')\nexcept EOFError:\n    line = ''",
    ),
}
