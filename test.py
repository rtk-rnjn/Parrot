#!/usr/bin/env python3
"""
Remove the walrus operator (:=) from Python files.

Auto-fixed (safe) cases, when the header is on a single line:
  if (x := expr):            if (x := expr) > 0:          (also bare `if x := expr:`)
  while (x := expr):         while (x := expr) is not None:   (no `else:` clause)
Everything else (comprehensions, `and`/`or` chains, lambdas, elif, call args, ...)
is reported with file:line so you can rewrite it by hand.

Usage:
  python remove_walrus.py PATH            # dry run
  python remove_walrus.py PATH --write    # apply
"""
import argparse
import ast
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".hg", ".svn", "venv", ".venv", "env", "node_modules",
             "__pycache__", ".tox", ".mypy_cache", "build", "dist", ".idea"}


def cidx(line: str, byte_off: int) -> int:
    """ast offsets are UTF-8 byte offsets; convert to str index."""
    return len(line.encode("utf-8")[:byte_off].decode("utf-8"))


def fix_source(src: str):
    tree = ast.parse(src)
    lines = src.split("\n")
    handled: set[int] = set()
    edits = []  # (lineno, new_lines)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.While)):
            continue
        test = node.test
        if isinstance(test, ast.NamedExpr):
            w = test
        elif isinstance(test, ast.Compare) and isinstance(test.left, ast.NamedExpr):
            w = test.left  # leftmost operand is evaluated first, so hoisting is safe
        else:
            continue
        if sum(isinstance(n, ast.NamedExpr) for n in ast.walk(test)) != 1:
            continue
        if any(isinstance(n, ast.NamedExpr) for n in ast.walk(w.value)):
            continue
        if not isinstance(w.target, ast.Name):
            continue
        if isinstance(node, ast.While) and node.orelse:
            continue  # `while True` + break would skip the else clause

        line = lines[node.lineno - 1]
        kw = "if " if isinstance(node, ast.If) else "while "
        if test.end_lineno != node.lineno or not line.lstrip().startswith(kw) \
                or not line.rstrip().endswith(":"):
            continue  # multi-line header, `elif`, or trailing comment

        indent = line[: len(line) - len(line.lstrip())]
        name = w.target.id
        value = ast.get_source_segment(src, w.value)
        a, b = cidx(line, w.col_offset), cidx(line, w.end_col_offset)
        if a > 0 and line[a - 1] == "(" and line[b:b + 1] == ")":
            a, b = a - 1, b + 1
        new_header = line[:a] + name + line[b:]

        if isinstance(node, ast.If):
            new = [indent + f"{name} = {value}", new_header]
        else:
            test_text = new_header.strip()[len("while"):-1].strip()
            cond = f"not {test_text}" if test_text.isidentifier() else f"not ({test_text})"
            body_line = lines[node.body[0].lineno - 1]
            body_indent = body_line[: len(body_line) - len(body_line.lstrip())]
            unit = body_indent[len(indent):] or "    "
            new = [
                indent + "while True:",
                body_indent + f"{name} = {value}",
                body_indent + f"if {cond}:",
                body_indent + unit + "break",
            ]
        edits.append((node.lineno, new))
        handled.add(id(w))

    for lineno, new in sorted(edits, reverse=True):  # bottom-up keeps line numbers valid
        lines[lineno - 1: lineno] = new

    remaining = [n.lineno for n in ast.walk(tree)
                 if isinstance(n, ast.NamedExpr) and id(n) not in handled]
    return "\n".join(lines), len(edits), sorted(remaining)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    files = [args.path] if args.path.is_file() else [
        p for p in args.path.rglob("*.py") if not any(part in SKIP_DIRS for part in p.parts)]

    fixed_total, manual_total = 0, 0
    for f in files:
        try:
            src = f.read_text(encoding="utf-8")
            if ":=" not in src:
                continue
            new, n_fixed, remaining = fix_source(src)
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"SKIP {f}: {e}", file=sys.stderr)
            continue

        if n_fixed:
            fixed_total += n_fixed
            print(f"{'FIXED' if args.write else 'WOULD FIX'} {f}: {n_fixed} walrus use(s)")
            if args.write:
                ast.parse(new)  # sanity check before saving
                f.write_text(new, encoding="utf-8")
        for ln in remaining:
            manual_total += 1
            print(f"MANUAL {f}:{ln}")

    print(f"\n{fixed_total} auto-fixed{'' if args.write else ' (dry run; use --write)'}, "
          f"{manual_total} need manual rewrite")
    return 0


if __name__ == "__main__":
    sys.exit(main())