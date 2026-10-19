from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StdlibMeta:
    name: str
    category: str
    summary: str
    highlights: tuple[str, ...]
    example: str
    source_path: str | None = None


STDLIB_CURATED: dict[str, StdlibMeta] = {
    "asyncio": StdlibMeta(
        name="asyncio",
        category="Concurrent Execution / Networking",
        summary="Asynchronous I/O, event loops, coroutines, tasks, synchronization primitives, and streams using `async` / `await`.",
        highlights=("asyncio.run", "asyncio.TaskGroup", "asyncio.gather", "asyncio.to_thread", "asyncio.timeout", "asyncio.Queue", "asyncio.Lock"),
        example="async with asyncio.TaskGroup() as tg:\n    t1 = tg.create_task(fetch_user(1))\n    t2 = tg.create_task(fetch_user(2))",
        source_path="Lib/asyncio/__init__.py",
    ),
    "collections": StdlibMeta(
        name="collections",
        category="Data Types",
        summary="Specialized container datatypes providing high-performance alternatives to Python's general-purpose `dict`, `list`, `set`, and `tuple`.",
        highlights=("deque", "Counter", "defaultdict", "namedtuple", "ChainMap", "OrderedDict"),
        example="from collections import Counter, defaultdict, deque\ncounts = Counter(['a', 'b', 'a']).most_common(1)",
        source_path="Lib/collections/__init__.py",
    ),
    "itertools": StdlibMeta(
        name="itertools",
        category="Functional / Iterators",
        summary="Fast, memory-efficient iterator building blocks inspired by APL, Haskell, and SML (combinatorics, infinite streams, grouping, batching).",
        highlights=("batched", "chain", "islice", "groupby", "product", "permutations", "combinations", "pairwise", "cycle"),
        example="from itertools import batched, pairwise\nlist(batched(range(7), 3))  # [(0, 1, 2), (3, 4, 5), (6,)]",
        source_path="Modules/itertoolsmodule.c",
    ),
    "functools": StdlibMeta(
        name="functools",
        category="Higher-Order Functions",
        summary="Higher-order functions and operations on callable objects: memoization caches, partial application, total ordering, and singledispatch.",
        highlights=("cache", "lru_cache", "partial", "wraps", "reduce", "singledispatch", "cached_property", "total_ordering"),
        example="from functools import cache, partial\n@cache\ndef fib(n: int) -> int:\n    return n if n < 2 else fib(n - 1) + fib(n - 2)",
        source_path="Lib/functools.py",
    ),
    "pathlib": StdlibMeta(
        name="pathlib",
        category="File & Directory Access",
        summary="Object-oriented filesystem paths with POSIX and Windows semantics, replacing most `os.path` and `glob` boilerplate.",
        highlights=("Path", "PurePosixPath", "Path.read_text", "Path.write_text", "Path.rglob", "Path.mkdir", "Path.resolve"),
        example="from pathlib import Path\nfor py_file in Path('src').rglob('*.py'):\n    print(py_file.stem, py_file.stat().st_size)",
        source_path="Lib/pathlib/__init__.py",
    ),
    "dataclasses": StdlibMeta(
        name="dataclasses",
        category="Data Types",
        summary="Decorator and functions for automatically adding generated special methods (`__init__`, `__repr__`, `__eq__`) to user-defined classes.",
        highlights=("dataclass", "field", "asdict", "astuple", "replace", "KW_ONLY"),
        example="from dataclasses import dataclass, field\n@dataclass(slots=True, frozen=True)\nclass Point:\n    x: float\n    y: float",
        source_path="Lib/dataclasses.py",
    ),
    "typing": StdlibMeta(
        name="typing",
        category="Runtime Type Support",
        summary="Support for gradual static type annotations, Protocols, TypeVars, TypedDicts, Literals, and runtime inspection helpers.",
        highlights=("Any", "Literal", "Annotated", "Protocol", "TypedDict", "TypeGuard", "TypeIs", "overload", "TYPE_CHECKING"),
        example="from typing import Literal, TypedDict\nclass Config(TypedDict):\n    mode: Literal['dev', 'prod']\n    port: int",
        source_path="Lib/typing.py",
    ),
    "re": StdlibMeta(
        name="re",
        category="Text Processing",
        summary="Regular expression matching, searching, splitting, and substitution operations supporting Unicode and byte patterns.",
        highlights=("compile", "search", "match", "fullmatch", "findall", "finditer", "sub", "split", "escape"),
        example="import re\nPATTERN = re.compile(r'(?P<user>[\\w.-]+)@(?P<host>[\\w.-]+)')\nif m := PATTERN.search(email):\n    print(m['user'], m['host'])",
        source_path="Lib/re/__init__.py",
    ),
    "json": StdlibMeta(
        name="json",
        category="Data Serialization",
        summary="RFC 8259 JSON encoder and decoder for converting between Python primitives (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`) and JSON text.",
        highlights=("loads", "dumps", "load", "dump", "JSONDecodeError", "JSONEncoder"),
        example="import json\npayload = json.dumps({'ok': True, 'items': [1, 2]}, indent=2)\ndata = json.loads(payload)",
        source_path="Lib/json/__init__.py",
    ),
    "datetime": StdlibMeta(
        name="datetime",
        category="Date & Time",
        summary="Classes for manipulating dates, times, timedeltas, and timezone-aware timestamps (combine with `zoneinfo` for IANA timezones).",
        highlights=("datetime", "date", "time", "timedelta", "timezone", "UTC"),
        example="from datetime import UTC, datetime, timedelta\nnow = datetime.now(tz=UTC)\ntomorrow = now + timedelta(days=1)",
        source_path="Lib/datetime.py",
    ),
    "contextlib": StdlibMeta(
        name="contextlib",
        category="Context Managers",
        summary="Utilities for building and composing `with` and `async with` context managers (`@contextmanager`, `suppress`, `ExitStack`, `aclosing`).",
        highlights=("contextmanager", "asynccontextmanager", "suppress", "ExitStack", "AsyncExitStack", "closing", "redirect_stdout"),
        example="from contextlib import suppress\nwith suppress(FileNotFoundError):\n    Path('temp.txt').unlink()",
        source_path="Lib/contextlib.py",
    ),
    "inspect": StdlibMeta(
        name="inspect",
        category="Runtime Introspection",
        summary="Inspect live objects: retrieve function signatures, source code, class hierarchies, docstrings, and stack frames.",
        highlights=("signature", "getsource", "getdoc", "iscoroutinefunction", "ismethod", "getmembers"),
        example="import inspect\nsig = inspect.signature(sorted)\nprint(sig)  # (iterable, /, *, key=None, reverse=False)",
        source_path="Lib/inspect.py",
    ),
    "ast": StdlibMeta(
        name="ast",
        category="Python Language Services",
        summary="Parse Python source code into an Abstract Syntax Tree (AST), inspect or transform nodes, and safely evaluate literals (`ast.literal_eval`).",
        highlights=("parse", "literal_eval", "unparse", "walk", "NodeVisitor", "NodeTransformer", "get_docstring"),
        example="import ast\nvalue = ast.literal_eval(\"{'a': [1, 2, 3]}\")  # Safe alternative to eval()!",
        source_path="Lib/ast.py",
    ),
    "secrets": StdlibMeta(
        name="secrets",
        category="Cryptographic Services",
        summary="Generate cryptographically strong random numbers suitable for managing passwords, account authentication, and security tokens.",
        highlights=("token_hex", "token_urlsafe", "choice", "randbelow", "compare_digest"),
        example="import secrets\napi_key = secrets.token_urlsafe(32)",
        source_path="Lib/secrets.py",
    ),
    "hashlib": StdlibMeta(
        name="hashlib",
        category="Cryptographic Services",
        summary="Secure hash and message digest algorithms including SHA-256, SHA-512, SHA-3, BLAKE2, and `scrypt` / `pbkdf2_hmac` password hashing.",
        highlights=("sha256", "blake2b", "file_digest", "pbkdf2_hmac", "scrypt"),
        example="import hashlib\ndigest = hashlib.sha256(b'hello world').hexdigest()",
        source_path="Lib/hashlib.py",
    ),
    "subprocess": StdlibMeta(
        name="subprocess",
        category="Process Management",
        summary="Spawn new processes, connect to their input/output/error pipes, and obtain their return codes safely without shell injection.",
        highlights=("run", "Popen", "CompletedProcess", "CalledProcessError", "TimeoutExpired", "PIPE"),
        example="import subprocess\nres = subprocess.run(['git', 'status', '-s'], capture_output=True, text=True, check=True)",
        source_path="Lib/subprocess.py",
    ),
    "unittest": StdlibMeta(
        name="unittest",
        category="Testing",
        summary="Unit testing framework supporting test automation, setup/teardown fixtures, async test cases (`IsolatedAsyncioTestCase`), and mocking (`unittest.mock`).",
        highlights=("TestCase", "IsolatedAsyncioTestCase", "mock.patch", "mock.MagicMock", "mock.AsyncMock"),
        example="from unittest.mock import AsyncMock\nmock_fetch = AsyncMock(return_value={'status': 200})",
        source_path="Lib/unittest/__init__.py",
    ),
}
