from __future__ import annotations

import itertools
import re

import numpy as np
import pandas as pd
import pyparsing
from discord.ext import commands
from tabulate import tabulate

SINGLE_OPERAND_COUNT = 2

# fmt: off
OPERATIONS = {
    "not"    : (lambda x: not x),
    "-"      : (lambda x: not x),
    "~"      : (lambda x: not x),
    "or"     : (lambda x, y: x or y),
    "nor"    : (lambda x, y: not (x or y)),
    "xor"    : (lambda x, y: x != y),
    "and"    : (lambda x, y: x and y),
    "nand"   : (lambda x, y: not (x and y)),
    "=>"     : (lambda x, y: (not x) or y),
    "implies": (lambda x, y: (not x) or y),
    "="      : (lambda x, y: x == y),
    "!="     : (lambda x, y: x != y),
}
# fmt: on


def recursive_map(func, data):
    """Recursively applies a map function to a list and all sublists."""
    if isinstance(data, list):
        return [recursive_map(func, elem) for elem in data]
    return func(data)


def string_to_bool(string: str):
    """Converts a string to boolean if string is either 'True' or 'False'
    otherwise returns it unchanged.
    """
    string = str(string).lower()
    if string in {
        "true",
        "t",
        "1",
        "yes",
        "y",
        "on",
        "enable",
        "enabled",
        "not none",
        "not null",
    }:
        return True
    if string in {
        "false",
        "f",
        "0",
        "no",
        "n",
        "off",
        "disable",
        "disabled",
        "none",
        "null",
    }:
        return False
    return string


def solve_phrase(phrase):
    """Recursively evaluates a logical phrase that has been grouped into sublists where each list is one operation."""
    if isinstance(phrase, bool):
        return phrase
    if isinstance(phrase, list):
        # list with just a list in it
        if len(phrase) == 1:
            return solve_phrase(phrase[0])
        # single operand operation
        if len(phrase) == SINGLE_OPERAND_COUNT:
            return OPERATIONS[phrase[0]](solve_phrase(phrase[1]))
        return OPERATIONS[phrase[1]](solve_phrase(phrase[0]), solve_phrase([phrase[2]]))
    return None


def group_operations(phrase: list):
    """Recursively groups logical operations into separate lists based on
    the order of operations such that each list is one operation.
    Order of operations is:
        not, and, or, implication.
    """
    if isinstance(phrase, list):
        for operator in ["not", "~", "-"]:
            while operator in phrase:
                index = phrase.index(operator)
                phrase[index] = [operator, group_operations(phrase[index + 1])]
                phrase.pop(index + 1)
        for operator in ["and", "nand"]:
            while operator in phrase:
                index = phrase.index(operator)
                phrase[index] = [
                    group_operations(phrase[index - 1]),
                    operator,
                    group_operations(phrase[index + 1]),
                ]
                phrase.pop(index + 1)
                phrase.pop(index - 1)
        for operator in ["or", "nor", "xor"]:
            while operator in phrase:
                index = phrase.index(operator)
                phrase[index] = [
                    group_operations(phrase[index - 1]),
                    operator,
                    group_operations(phrase[index + 1]),
                ]
                phrase.pop(index + 1)
                phrase.pop(index - 1)
    return phrase


class Truths:
    """Class Truhts with modules for table formatting, valuation and CLI."""

    def __init__(self, bases=None, phrases=None, ints=True, ascending=False) -> None:
        if not bases:
            msg = "Base items are required"
            raise Exception(msg)
        self.bases = bases
        self.phrases = phrases or []
        self.ints = ints

        # generate the sets of booleans for the bases
        order = [False, True] if ascending else [True, False]
        self.base_conditions = list(itertools.product(order, repeat=len(bases)))

        # regex to match whole words defined in self.bases
        # used to add object context to variables in self.phrases
        self.p = re.compile(r"(?<!\w)(" + "|".join(self.bases) + r")(?!\w)")

        # used for parsing logical operations and parenthesis
        self.to_match = pyparsing.Word(pyparsing.alphanums)
        for item in itertools.chain(self.bases, [key for key, val in OPERATIONS.items()]):
            self.to_match |= item
        self.parens = pyparsing.nestedExpr("(", ")", content=self.to_match)

    def calculate(self, *args):
        """Evaluates the logical value for each expression."""
        bools = dict(zip(self.bases, args, strict=False))

        eval_phrases = []
        for phrase in self.phrases:
            expression = self.p.sub(lambda match: str(bools[match.group(0)]), phrase)
            expression = "(" + expression + ")"

            interpreted = self.parens.parseString(expression).asList()[0]

            interpreted = recursive_map(string_to_bool, interpreted)
            interpreted = group_operations(interpreted)

            eval_phrases.append(solve_phrase(interpreted))

        row = [val for key, val in bools.items()] + eval_phrases
        if self.ints:
            row = [int(c) for c in row]
        return row

    def as_pandas(self):
        """Table as Pandas DataFrame."""
        df_columns = self.bases + self.phrases
        df = pd.DataFrame(columns=df_columns)
        for conditions_set in self.base_conditions:
            df.loc[len(df)] = self.calculate(*conditions_set)
        df.index = np.arange(1, len(df) + 1)
        return df

    def as_tabulate(self, index=True, table_format="psql", align="center"):
        """Returns table using tabulate package."""
        return tabulate(
            self.as_pandas(),
            headers="keys",
            tablefmt=table_format,
            showindex=index,
            colalign=[align] * (len(Truths.as_pandas(self).columns) + index),
        )

    def valuation(self, col_number=-1):
        """Evaluates an expression in a table column as a tautology, a
        contradiction or a contingency.
        """
        df = self.as_pandas()
        if col_number == -1:
            pass
        elif col_number not in range(1, len(df.columns) + 1):
            msg = "Indexer is out-of-bounds"
            raise Exception(msg)
        else:
            col_number = col_number - 1

        if sum(df.iloc[:, col_number]) == len(df):
            return "Tautology"
        if sum(df.iloc[:, col_number]) == 0:
            return "Contradiction"
        return "Contingency"

    def __str__(self) -> str:
        table = self.as_tabulate(index=False)
        return str(table)


class TTFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    var: str = commands.flag(
        description="The variable to evaluate.",
        default="p, q",
        aliases=["variables", "v", "vars", "variable"],
    )
    con: str = commands.flag(
        description="The logical expression to evaluate.",
        default="p and q",
        aliases=["cons", "condition", "conditions", "expr", "expression"],
    )
    ascending: bool = commands.flag(
        description="Whether to sort the base conditions in ascending order.",
        default=True,
    )
    table_format: str = commands.flag(description="The format of the table.", default="psql")
    align: str = commands.flag(description="The alignment of the table.", default="center")
    valuation: bool = commands.flag(description="Whether to show the valuation of the table.", default=False)
    latex: bool = commands.flag(description="Whether to show the table in LaTeX format.", default=False)
