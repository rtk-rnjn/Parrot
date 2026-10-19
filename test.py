#!/usr/bin/env python3
"""
Convert non-ASCII Unicode characters in a project to their Unicode names.

Modes
-----
escape (default)  Python files only. Inside string literals, replace each
                  non-ASCII char with \\N{NAME}, e.g. "caf\N{LATIN SMALL LETTER E WITH ACUTE}" -> "caf\\N{LATIN SMALL LETTER E WITH ACUTE}".
                  Uses `tokenize`, so identifiers, comments and code are untouched.
                  Raw strings are skipped (\\N doesn't work in them).
text              Any text file. Replace each non-ASCII char with " NAME "
                  (spaced plain words), e.g. "caf\N{LATIN SMALL LETTER E WITH ACUTE}" -> "caf LATIN SMALL LETTER E WITH ACUTE ".

Usage
-----
  python unicode_to_names.py PATH                 # dry run (shows what would change)
  python unicode_to_names.py PATH --write         # apply changes
  python unicode_to_names.py PATH --mode text --ext .md .txt --write
  python unicode_to_names.py PATH --comments --write   # escape mode: also convert comments to " NAME " text
"""
import argparse
import io
import re
import sys
import tokenize
import unicodedata
from pathlib import Path

SKIP_DIRS = {".git", ".hg", ".svn", "venv", ".venv", "env", "node_modules",
             "__pycache__", ".tox", ".mypy_cache", "build", "dist", ".idea"}
NON_ASCII = re.compile(r"[^\x00-\x7f]")
STRING_PREFIX = re.compile(r"^([A-Za-z]*)['\"]")


def char_name(ch: str) -> str | None:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return None


def to_escape(text: str) -> str:
    def sub(m):
        ch = m.group()
        name = char_name(ch)
        if name:
            return "\\N{%s}" % name
        cp = ord(ch)
        return f"\\u{cp:04x}" if cp <= 0xFFFF else f"\\U{cp:08x}"
    return NON_ASCII.sub(sub, text)


def to_spaced(text: str) -> str:
    def sub(m):
        ch = m.group()
        return f" {char_name(ch) or f'U+{ord(ch):04X}'} "
    return NON_ASCII.sub(sub, text)


def convert_python(source: str, comments: bool, warnings: list[str]) -> str:
    """Escape non-ASCII chars inside (non-raw) string literals via tokenize."""
    if not NON_ASCII.search(source):
        return source

    # absolute offset of each line start
    lines = source.splitlines(keepends=True)
    starts, pos = [0], 0
    for ln in lines:
        pos += len(ln)
        starts.append(pos)

    def offset(row, col):
        return starts[row - 1] + col

    edits = []  # (start, end, replacement)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError) as e:
        warnings.append(f"tokenize failed ({e}); file left unchanged")
        return source

    for tok in tokens:
        if not NON_ASCII.search(tok.string):
            continue
        s, e = offset(*tok.start), offset(*tok.end)
        if tok.type == tokenize.STRING:
            prefix = STRING_PREFIX.match(tok.string)
            if prefix and "r" in prefix.group(1).lower():
                warnings.append(f"line {tok.start[0]}: raw string skipped")
                continue
            if prefix and "b" in prefix.group(1).lower():
                continue  # non-ASCII bytes literals are a SyntaxError anyway
            edits.append((s, e, to_escape(tok.string)))
        elif tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            if "{" in tok.string or "}" in tok.string:
                warnings.append(f"line {tok.start[0]}: f-string with braces skipped")
                continue
            edits.append((s, e, to_escape(tok.string)))
        elif tok.type == tokenize.COMMENT and comments:
            edits.append((s, e, to_spaced(tok.string)))
        elif tok.type == tokenize.NAME:
            warnings.append(f"line {tok.start[0]}: non-ASCII identifier {tok.string!r} left alone")

    for s, e, rep in sorted(edits, reverse=True):
        source = source[:s] + rep + source[e:]
    return source


def iter_files(root: Path, exts: set[str]):
    if root.is_file():
        yield root
        return
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix.lower() in exts:
            yield p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path)
    ap.add_argument("--mode", choices=["escape", "text"], default="escape")
    ap.add_argument("--ext", nargs="+", help="file extensions to process (default: .py for escape, .txt .md .rst for text)")
    ap.add_argument("--comments", action="store_true", help="escape mode: also convert comments to spaced names")
    ap.add_argument("--write", action="store_true", help="apply changes (default is dry run)")
    args = ap.parse_args()

    exts = {e if e.startswith(".") else "." + e for e in (args.ext or
            ([".py"] if args.mode == "escape" else [".txt", ".md", ".rst"]))}
    exts = {e.lower() for e in exts}

    changed = 0
    for f in iter_files(args.path, exts):
        try:
            original = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"SKIP {f}: {e}", file=sys.stderr)
            continue

        warnings: list[str] = []
        if args.mode == "escape":
            new = convert_python(original, args.comments, warnings)
        else:
            new = to_spaced(original)

        for w in warnings:
            print(f"  warn {f}: {w}", file=sys.stderr)
        if new == original:
            continue

        changed += 1
        print(f"{'UPDATED' if args.write else 'WOULD CHANGE'} {f}")
        if args.write:
            if f.suffix == ".py":  # make sure the result still parses
                try:
                    compile(new, str(f), "exec")
                except SyntaxError as e:
                    print(f"  ERROR {f}: result would not compile ({e}); skipped", file=sys.stderr)
                    continue
            f.write_text(new, encoding="utf-8")

    print(f"\n{changed} file(s) {'modified' if args.write else 'would be modified (dry run; use --write)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())