from __future__ import annotations

import ast
import atexit
import json
import os
import re
import time
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, cast

import click
from bson import ObjectId, json_util
from colorama import just_fix_windows_console
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError
from rich import box
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

import readline

type Document = MutableMapping[str, Any]
type ReadonlyDocument = Mapping[str, Any]
type JsonValue = Any

APP_NAME: Final = "pymongosh"
VERSION: Final = "1.0.0"
DEFAULT_DB: Final = "test"
DEFAULT_HISTORY: Final = Path.home() / ".pymongosh_history"
MAX_PREVIEW_DOCS: Final = 100


class MongoShellHighlighter(RegexHighlighter):
    base_style = "mongo."
    highlights = [
        r"(?P<keyword>\b(?:show|use|db|help|exit|quit|true|false|null)\b)",
        r"(?P<method>\b(?:find|findOne|insertOne|insertMany|updateOne|updateMany|replaceOne|deleteOne|deleteMany|aggregate|countDocuments|estimatedDocumentCount|distinct|createIndex|createIndexes|dropIndex|dropIndexes|getIndexes|drop|renameCollection|stats|validate|runCommand|limit|skip|sort|project)\b)",
        r'(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')',
        r"(?P<number>\b-?(?:0|[1-9]\d*)(?:\.\d+)?\b)",
        r"(?P<objectid>ObjectId\([^)]+\))",
        r"(?P<punct>[{}\[\](),.:])",
    ]


THEME: Final = Theme(
    {
        "title": "bold cyan",
        "muted": "dim",
        "ok": "bold green",
        "warn": "bold yellow",
        "error": "bold red",
        "prompt.db": "bold bright_cyan",
        "prompt.sep": "dim white",
        "prompt.arrow": "bold bright_green",
        "mongo.keyword": "bold magenta",
        "mongo.method": "bold cyan",
        "mongo.string": "green",
        "mongo.number": "bright_blue",
        "mongo.objectid": "yellow",
        "mongo.punct": "white",
    },
)

console = Console(theme=THEME, highlighter=MongoShellHighlighter())


class ShellError(RuntimeError):
    """User-facing shell error."""


@dataclass(slots=True)
class CursorOptions:
    limit: int | None = None
    skip: int = 0
    sort: list[tuple[str, int]] = field(default_factory=list)
    projection: Document | None = None


@dataclass(slots=True)
class ShellState:
    client: MongoClient[Document]
    db_name: str
    uri: str
    verbose: bool = False
    max_rows: int = 50

    @property
    def db(self) -> Database[Document]:
        return self.client[self.db_name]


@dataclass(frozen=True, slots=True)
class Invocation:
    target: str
    method: str
    args_text: str
    chain_text: str = ""


class ValueParser:
    """Parse a practical subset of mongosh/JavaScript values into Python/BSON values."""

    _UNQUOTED_KEY = re.compile(r"(?P<prefix>[{,]\s*)(?P<key>[A-Za-z_$][\w$.-]*)(?P<suffix>\s*:)")
    _NEW_OBJECT_ID = re.compile(r"\bnew\s+ObjectId\s*\(", re.IGNORECASE)
    _ISO_DATE = re.compile(r"\bISODate\s*\(")

    @classmethod
    def parse_args(cls, text: str) -> tuple[Any, ...]:
        text = text.strip()
        if not text:
            return ()
        normalized = cls._normalize(text)
        try:
            expr = ast.parse(f"f({normalized})", mode="eval")
        except SyntaxError as exc:
            message = f"Could not parse arguments: {exc.msg}"
            raise ShellError(message) from exc
        if not isinstance(expr.body, ast.Call):
            raise ShellError("Invalid argument list")
        return tuple(cls._eval_node(node) for node in expr.body.args)

    @classmethod
    def parse_value(cls, text: str) -> Any:
        args = cls.parse_args(text)
        if len(args) != 1:
            raise ShellError("Expected exactly one value")
        return args[0]

    @classmethod
    def _normalize(cls, text: str) -> str:
        out = cls._NEW_OBJECT_ID.sub("ObjectId(", text)
        out = cls._ISO_DATE.sub("ISODate(", out)
        out = re.sub(r"\btrue\b", "True", out, flags=re.IGNORECASE)
        out = re.sub(r"\bfalse\b", "False", out, flags=re.IGNORECASE)
        out = re.sub(r"\bnull\b", "None", out, flags=re.IGNORECASE)
        # Quote common JavaScript object keys: {name: "Ada", $set: {...}}
        previous = None
        while previous != out:
            previous = out
            out = cls._UNQUOTED_KEY.sub(lambda m: f"{m.group('prefix')}{json.dumps(m.group('key'))}{m.group('suffix')}", out)
        return out

    @classmethod
    def _eval_node(cls, node: ast.AST) -> Any:  # noqa: C901, PLR0911, PLR0912
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Dict):
            return {cls._eval_node(k): cls._eval_node(v) for k, v in zip(node.keys, node.values, strict=True) if k is not None}
        if isinstance(node, ast.List):
            return [cls._eval_node(v) for v in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(cls._eval_node(v) for v in node.elts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value = cls._eval_node(node.operand)
            if isinstance(value, (int, float)):
                return -value
        if isinstance(node, ast.Name) and node.id in {"True", "False", "None"}:
            return {"True": True, "False": False, "None": None}[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            args = [cls._eval_node(a) for a in node.args]
            if node.func.id == "ObjectId":
                return ObjectId(*args)
            if node.func.id == "ISODate":
                if len(args) != 1 or not isinstance(args[0], str):
                    raise ShellError("ISODate() expects one ISO-8601 string")
                value = args[0].replace("Z", "+00:00")
                return datetime.fromisoformat(value)
            if node.func.id == "Date":
                if not args:
                    return datetime.now(UTC)
                if len(args) == 1 and isinstance(args[0], str):
                    return datetime.fromisoformat(args[0].replace("Z", "+00:00"))
        expression = ast.unparse(node)
        message = f"Unsupported expression: {expression}"
        raise ShellError(message)


class Completer:
    CURSOR_METHODS: Final = (
        "limit(",
        "skip(",
        "sort(",
        "project(",
    )
    COLLECTION_METHODS: Final = (
        "find(",
        "findOne(",
        "aggregate(",
        "insertOne(",
        "insertMany(",
        "updateOne(",
        "updateMany(",
        "replaceOne(",
        "deleteOne(",
        "deleteMany(",
        "countDocuments(",
        "estimatedDocumentCount()",
        "distinct(",
        "createIndex(",
        "getIndexes()",
        "dropIndex(",
        "dropIndexes()",
        "drop()",
        "renameCollection(",
        "stats()",
        "validate()",
    )
    WORDS: Final = (
        "show dbs",
        "show collections",
        "show users",
        "show roles",
        "use ",
        "db",
        "db.runCommand(",
        "db.stats()",
        "db.dropDatabase()",
        "db.createCollection(",
        "db.getCollectionNames()",
        "help",
        "clear",
        "exit",
    )

    def __init__(self, state: ShellState) -> None:
        self.state = state
        self.matches: list[str] = []

    def __call__(self, text: str, index: int) -> str | None:
        if index == 0:
            candidates = self._candidates(text)
            self.matches = sorted(c for c in candidates if c.startswith(text))
        return self.matches[index] if index < len(self.matches) else None

    def _candidates(self, text: str) -> list[str]:
        if text.startswith("db."):
            remainder = text[3:]
            if "." in remainder:
                collection, member = remainder.split(".", 1)
                if ")." in member:
                    chain, _ = member.rsplit(".", 1)
                    chain_prefix = f"db.{collection}.{chain}."
                    return [f"{chain_prefix}{method}" for method in self.CURSOR_METHODS]
                return [f"db.{collection}.{method}" for method in self.COLLECTION_METHODS]

            candidates = [f"db.{name}" for name in self._collection_names()]
            candidates.extend(word for word in self.WORDS if word.startswith("db."))
            return candidates

        candidates = list(self.WORDS)
        candidates.extend(f"db.{name}" for name in self._collection_names())
        return candidates

    def _collection_names(self) -> list[str]:
            try:
                return self.state.db.list_collection_names()
            except PyMongoError:
                return []


def split_top_level(text: str, separator: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for i, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == separator and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return [p for p in parts if p]


def extract_call(text: str, open_paren: int) -> tuple[str, int]:
    depth = 0
    quote: str | None = None
    escaped = False
    for i in range(open_paren, len(text)):
        char = text[i]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1 : i], i + 1
    raise ShellError("Unclosed parenthesis")


def parse_invocation(command: str) -> Invocation:
    # db.collection.method(...) or db.getCollection("name").method(...)
    get_collection = re.match(r'^db\.getCollection\((?P<q>["\'])(?P<name>.+?)(?P=q)\)\.(?P<method>\w+)\(', command)
    if get_collection:
        target = get_collection.group("name")
        method = get_collection.group("method")
        open_paren = get_collection.end() - 1
        args, end = extract_call(command, open_paren)
        return Invocation(target, method, args, command[end:].strip())

    match = re.match(r"^db\.(?P<target>[A-Za-z_$][\w$-]*)\.(?P<method>\w+)\(", command)
    if not match:
        raise ShellError('Expected db.<collection>.<method>(...) or db.getCollection("name").<method>(...)')
    args, end = extract_call(command, match.end() - 1)
    return Invocation(match.group("target"), match.group("method"), args, command[end:].strip())


def parse_cursor_chain(chain: str) -> CursorOptions:
    options = CursorOptions()
    rest = chain.strip()
    while rest:
        match = re.match(r"^\.(?P<method>limit|skip|sort|project)\(", rest)
        if not match:
            message = f"Unsupported cursor chain: {rest}"
            raise ShellError(message)
        args_text, end = extract_call(rest, match.end() - 1)
        args = ValueParser.parse_args(args_text)
        method = match.group("method")
        if method == "limit":
            options.limit = int(_required_arg(args, 0, "limit"))
        elif method == "skip":
            options.skip = int(_required_arg(args, 0, "skip"))
        elif method == "project":
            options.projection = _as_document(_required_arg(args, 0, "projection"))
        elif method == "sort":
            value = _required_arg(args, 0, "sort")
            options.sort = normalize_sort(value, args[1] if len(args) > 1 else None)
        rest = rest[end:].strip()
    return options


def normalize_sort(value: Any, direction: Any = None) -> list[tuple[str, int]]:
    if isinstance(value, str):
        direction_int = int(direction if direction is not None else ASCENDING)
        return [(value, direction_int)]
    if isinstance(value, Mapping):
        return [(str(k), int(v)) for k, v in value.items()]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        result: list[tuple[str, int]] = []
        for pair in value:
            if not isinstance(pair, Sequence) or len(pair) != 2:
                raise ShellError("sort list must contain [field, direction] pairs")
            result.append((str(pair[0]), int(pair[1])))
        return result
    raise ShellError("sort expects a field name, object, or list of pairs")


def _required_arg(args: Sequence[Any], index: int, name: str) -> Any:
    try:
        return args[index]
    except IndexError as exc:
        message = f"Missing required argument: {name}"
        raise ShellError(message) from exc


def _as_document(value: Any) -> Document:
    if not isinstance(value, MutableMapping):
        if isinstance(value, Mapping):
            return dict(value)
        raise ShellError("Expected an object/document")
    return cast(Document, value)


def bson_json(value: Any) -> str:
    return json_util.dumps(value, indent=2, ensure_ascii=False)


def print_value(value: Any) -> None:
    if value is None:
        return
    try:
        console.print(JSON(bson_json(value)))
    except Exception:
        console.print(repr(value))


def print_documents(docs: Iterable[ReadonlyDocument], max_rows: int) -> None:
    materialized = list(docs)
    if not materialized:
        console.print("[muted]No documents matched.[/muted]")
        return
    shown = materialized[:max_rows]
    for i, doc in enumerate(shown, 1):
        console.rule(f"[muted]document {i}[/muted]", style="dim")
        print_value(doc)
    if len(materialized) > max_rows:
        console.print(f"[warn]Showing {max_rows} of {len(materialized)} documents.[/warn]")


def command_result(result: Any) -> Any:
    attrs = (
        "acknowledged",
        "inserted_id",
        "inserted_ids",
        "matched_count",
        "modified_count",
        "deleted_count",
        "upserted_id",
        "raw_result",
    )
    data: dict[str, Any] = {}
    for attr in attrs:
        if hasattr(result, attr):
            value = getattr(result, attr)
            if value not in (None, [], {}):
                data[attr] = value
    return data or result


def execute_collection(state: ShellState, inv: Invocation) -> None:  # noqa: C901, PLR0912, PLR0915
    collection: Collection[Document] = state.db[inv.target]
    args = ValueParser.parse_args(inv.args_text)
    method = inv.method

    if method == "find":
        query = _as_document(args[0]) if args else {}
        projection = _as_document(args[1]) if len(args) > 1 and args[1] is not None else None
        opts = parse_cursor_chain(inv.chain_text)
        if opts.projection is not None:
            projection = opts.projection
        cursor = collection.find(query, projection)
        if opts.sort:
            cursor = cursor.sort(opts.sort)
        if opts.skip:
            cursor = cursor.skip(opts.skip)
        limit = opts.limit if opts.limit is not None else state.max_rows
        cursor = cursor.limit(limit + 1 if limit > 0 else 0)
        docs = list(cursor)
        print_documents(docs[:limit] if limit > 0 else docs, limit if limit > 0 else state.max_rows)
        if limit > 0 and len(docs) > limit:
            console.print("[warn]More results exist; use .limit(n) to change the limit.[/warn]")
        return

    if inv.chain_text:
        message = f"Cursor chaining is only supported after find(); got {inv.chain_text}"
        raise ShellError(message)

    if method == "findOne":
        filt = _as_document(args[0]) if args else {}
        projection = _as_document(args[1]) if len(args) > 1 and args[1] is not None else None
        print_value(collection.find_one(filt, projection))
    elif method == "insertOne":
        print_value(command_result(collection.insert_one(_as_document(_required_arg(args, 0, "document")))))
    elif method == "insertMany":
        docs = _required_arg(args, 0, "documents")
        if not isinstance(docs, list):
            raise ShellError("insertMany expects an array of documents")
        print_value(command_result(collection.insert_many([_as_document(d) for d in docs])))
    elif method == "updateOne":
        filt = _as_document(_required_arg(args, 0, "filter"))
        update = _as_document(_required_arg(args, 1, "update"))
        options = _as_document(args[2]) if len(args) > 2 else {}
        print_value(command_result(collection.update_one(filt, update, **_mongo_options(options, {"upsert", "array_filters", "hint"}))))
    elif method == "updateMany":
        filt = _as_document(_required_arg(args, 0, "filter"))
        update = _as_document(_required_arg(args, 1, "update"))
        options = _as_document(args[2]) if len(args) > 2 else {}
        print_value(command_result(collection.update_many(filt, update, **_mongo_options(options, {"upsert", "array_filters", "hint"}))))
    elif method == "replaceOne":
        filt = _as_document(_required_arg(args, 0, "filter"))
        replacement = _as_document(_required_arg(args, 1, "replacement"))
        options = _as_document(args[2]) if len(args) > 2 else {}
        print_value(command_result(collection.replace_one(filt, replacement, **_mongo_options(options, {"upsert", "hint"}))))
    elif method == "deleteOne":
        filt = _as_document(_required_arg(args, 0, "filter"))
        print_value(command_result(collection.delete_one(filt)))
    elif method == "deleteMany":
        filt = _as_document(_required_arg(args, 0, "filter"))
        print_value(command_result(collection.delete_many(filt)))
    elif method == "aggregate":
        pipeline = _required_arg(args, 0, "pipeline")
        if not isinstance(pipeline, list):
            raise ShellError("aggregate expects an array pipeline")
        docs = list(collection.aggregate(pipeline))
        print_documents(docs, state.max_rows)
    elif method == "countDocuments":
        filt = _as_document(args[0]) if args else {}
        console.print(collection.count_documents(filt))
    elif method == "estimatedDocumentCount":
        console.print(collection.estimated_document_count())
    elif method == "distinct":
        key = str(_required_arg(args, 0, "field"))
        filt = _as_document(args[1]) if len(args) > 1 else None
        print_value(collection.distinct(key, filt))
    elif method == "createIndex":
        spec = _required_arg(args, 0, "keys")
        keys = normalize_sort(spec, args[1] if len(args) > 1 and not isinstance(args[1], Mapping) else None)
        options_index = 2 if len(args) > 1 and not isinstance(args[1], Mapping) else 1
        options = _as_document(args[options_index]) if len(args) > options_index else {}
        console.print(collection.create_index(keys, **dict(options)))
    elif method == "getIndexes":
        print_value(list(collection.list_indexes()))
    elif method == "dropIndex":
        collection.drop_index(_required_arg(args, 0, "index"))
        console.print("[ok]Index dropped.[/ok]")
    elif method == "dropIndexes":
        collection.drop_indexes()
        console.print("[ok]Indexes dropped.[/ok]")
    elif method == "drop":
        collection.drop()
        console.print(f"[ok]Dropped collection {inv.target!r}.[/ok]")
    elif method == "renameCollection":
        new_name = str(_required_arg(args, 0, "newName"))
        options = _as_document(args[1]) if len(args) > 1 else {}
        collection.rename(new_name, **dict(options))
        console.print(f"[ok]Renamed to {new_name!r}.[/ok]")
    elif method == "stats":
        print_value(state.db.command("collStats", inv.target))
    elif method == "validate":
        print_value(state.db.command("validate", inv.target))
    else:
        message = f"Unsupported collection method: {method}"
        raise ShellError(message)


def _mongo_options(options: Mapping[str, Any], allowed: set[str]) -> dict[str, Any]:
    aliases = {"arrayFilters": "array_filters"}
    out: dict[str, Any] = {}
    for key, value in options.items():
        normalized = aliases.get(key, key)
        if normalized in allowed:
            out[normalized] = value
        else:
            message = f"Unsupported option for this helper: {key}"
            raise ShellError(message)
    return out


def show_databases(state: ShellState) -> None:
    rows = state.client.list_databases()
    table = Table(title="Databases", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Size", justify="right")
    table.add_column("Empty", justify="center")
    for row in rows:
        size = int(row.get("sizeOnDisk", 0))
        table.add_row(str(row.get("name", "")), human_bytes(size), "yes" if row.get("empty") else "no")
    console.print(table)


def show_collections(state: ShellState) -> None:
    names = state.db.list_collection_names()
    table = Table(title=f"Collections · {state.db_name}", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("#", justify="right", style="muted")
    table.add_column("Collection")
    for i, name in enumerate(sorted(names), 1):
        table.add_row(str(i), name)
    console.print(table if names else "[muted]No collections.[/muted]")


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def execute(state: ShellState, raw: str) -> bool:  # noqa: C901, PLR0911, PLR0912, PLR0915
    command = raw.strip().rstrip(";").strip()
    if not command:
        return True
    if command in {"exit", "quit", ".exit"}:
        return False
    if command in {"clear", "cls"}:
        console.clear()
        return True
    if command in {"help", "?"}:
        print_help()
        return True
    if command in {"show dbs", "show databases"}:
        show_databases(state)
        return True
    if command in {"show collections", "show tables"}:
        show_collections(state)
        return True
    if command == "show users":
        print_value(state.db.command({"usersInfo": 1}).get("users", []))
        return True
    if command == "show roles":
        print_value(state.db.command({"rolesInfo": 1, "showBuiltinRoles": False}).get("roles", []))
        return True
    if command == "db":
        console.print(state.db_name)
        return True
    if command.startswith("use "):
        db_name = command[4:].strip()
        if not db_name:
            raise ShellError("Usage: use <database>")
        state.db_name = db_name
        console.print(f"[ok]switched to db[/ok] [bold]{db_name}[/bold]")
        return True

    db_method = re.match(r"^db\.(?P<method>stats|dropDatabase|createCollection|getCollectionNames|getName|version)\(", command)
    if db_method:
        args_text, end = extract_call(command, db_method.end() - 1)
        if command[end:].strip():
            raise ShellError("Unexpected text after database method")
        args = ValueParser.parse_args(args_text)
        method = db_method.group("method")
        if method == "stats":
            print_value(state.db.command("dbStats"))
        elif method == "dropDatabase":
            print_value(state.client.drop_database(state.db_name) or {"ok": 1})
        elif method == "createCollection":
            name = str(_required_arg(args, 0, "name"))
            options = _as_document(args[1]) if len(args) > 1 else {}
            state.db.create_collection(name, **dict(options))
            console.print(f"[ok]Created collection {name!r}.[/ok]")
        elif method == "getCollectionNames":
            print_value(state.db.list_collection_names())
        elif method == "getName":
            console.print(state.db_name)
        elif method == "version":
            console.print(state.client.server_info().get("version", "unknown"))
        return True

    run_command = re.match(r"^db\.runCommand\(", command)
    if run_command:
        args_text, end = extract_call(command, run_command.end() - 1)
        if command[end:].strip():
            raise ShellError("Unexpected text after runCommand()")
        args = ValueParser.parse_args(args_text)
        doc = _as_document(_required_arg(args, 0, "command"))
        print_value(state.db.command(doc))
        return True

    if command.startswith("db."):
        execute_collection(state, parse_invocation(command))
        return True

    raise ShellError("Unknown command. Type 'help' for supported syntax.")


def print_help() -> None:
    console.print(
        Markdown(
            """
# PyMongoSH commands

- `show dbs` / `show collections`
- `use <database>` / `db`
- `db.<collection>.find(filter, projection).sort({...}).skip(n).limit(n)`
- `findOne`, `insertOne`, `insertMany`, `updateOne`, `updateMany`, `replaceOne`
- `deleteOne`, `deleteMany`, `aggregate`, `countDocuments`, `estimatedDocumentCount`, `distinct`
- `createIndex`, `getIndexes`, `dropIndex`, `dropIndexes`, `drop`, `renameCollection`
- `stats`, `validate`, `db.runCommand({...})`
- BSON helpers: `ObjectId("...")`, `ISODate("...")`, `Date("...")`
- `clear`, `help`, `exit`

JavaScript-style unquoted object keys, `true`, `false`, and `null` are accepted.
            """.strip(),
        ),
    )


def setup_readline(state: ShellState, history_file: Path) -> None:
    if readline is None:
        return
    try:
        if history_file.exists():
            readline.read_history_file(str(history_file))
        readline.set_history_length(2000)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(" \t\n")
        readline.set_completer(Completer(state))
        atexit.register(lambda: readline.write_history_file(str(history_file)))
    except OSError:
        pass


def prompt_text(state: ShellState) -> Text:
    text = Text()
    text.append(state.db_name, style="prompt.db")
    text.append(" ", style="prompt.sep")
    text.append("❯", style="prompt.arrow")
    return text


def print_banner(state: ShellState, elapsed_ms: float) -> None:
    host = "MongoDB"
    try:
        address = state.client.address
        if address:
            host = f"{address[0]}:{address[1]}"
    except PyMongoError:
        pass
    banner = Text()
    banner.append("PyMongoSH", style="bold bright_cyan")
    banner.append(f"  v{VERSION}\n", style="muted")
    banner.append("Connected", style="ok")
    banner.append(f"  {host}  ·  {elapsed_ms:.0f} ms\n", style="white")
    banner.append("Database", style="muted")
    banner.append(f"   {state.db_name}", style="bold")
    console.print(Panel(banner, border_style="cyan", box=box.ROUNDED, padding=(1, 2)))


def repl(state: ShellState, history_file: Path) -> None:
    setup_readline(state, history_file)
    while True:
        try:
            raw = console.input(prompt_text(state) + Text(" "))
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not raw.strip():
            continue
        # Rich-highlighted echo: practical highlighting without prompt_toolkit.
        if state.verbose:
            console.print(Text("↳ ", style="muted") + MongoShellHighlighter()(raw))
        try:
            if not execute(state, raw):
                break
        except ShellError as exc:
            console.print(Panel(str(exc), title="Shell error", border_style="red"))
        except PyMongoError as exc:
            console.print(Panel(str(exc), title=exc.__class__.__name__, border_style="red"))
        except Exception as exc:
            console.print(Panel(f"{exc.__class__.__name__}: {exc}", title="Error", border_style="red"))


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--uri", envvar="MONGODB_URI", help="MongoDB URI. Defaults to MONGODB_URI.")
@click.option("--database", "database_name", "-d", default=None, help="Initial database name.")
@click.option("--max-rows", type=click.IntRange(1, MAX_PREVIEW_DOCS), default=50, show_default=True)
@click.option("--history-file", type=click.Path(path_type=Path), default=DEFAULT_HISTORY, show_default=True)
@click.option("--verbose", "-v", is_flag=True, help="Echo each command with Rich syntax highlighting.")
@click.version_option(VERSION, prog_name=APP_NAME)
def main(uri: str | None, database_name: str | None, max_rows: int, history_file: Path, verbose: bool) -> None:
    """A polished PyMongo-powered shell with mongosh-like syntax."""
    just_fix_windows_console()
    load_dotenv()
    resolved_uri = uri or os.getenv("MONGO_URI")
    if not resolved_uri:
        raise click.ClickException("MONGO_URI is not set. Put it in .env or pass --uri.")

    client: MongoClient[Document] = MongoClient(
        resolved_uri,
        appname=APP_NAME,
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
    )
    started = time.perf_counter()
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        client.close()
        error = f"MongoDB connection failed: {exc}"
        raise click.ClickException(error) from exc

    if database_name is None:
        try:
            database_name = client.get_default_database().name
        except Exception:
            database_name = DEFAULT_DB

    state = ShellState(client=client, db_name=database_name, uri=resolved_uri, verbose=verbose, max_rows=max_rows)
    try:
        print_banner(state, (time.perf_counter() - started) * 1000)
        repl(state, history_file)
    finally:
        client.close()
        console.print("[muted]Connection closed.[/muted]")


if __name__ == "__main__":
    main()
