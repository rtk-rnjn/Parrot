from __future__ import annotations

import itertools
import re
from distutils.util import strtobool

import numpy as np
import pandas as pd
import pyparsing
from prettytable import PrettyTable
from tabulate import tabulate

# dict of boolean operations
OPERATIONS = {
    "not": (lambda x: not x),
    "-": (lambda x: not x),
    "~": (lambda x: not x),
    "or": (lambda x, y: x or y),
    "nor": (lambda x, y: not (x or y)),
    "xor": (lambda x, y: x != y),
    "and": (lambda x, y: x and y),
    "nand": (lambda x, y: not (x and y)),
    "=>": (lambda x, y: (not x) or y),
    "implies": (lambda x, y: (not x) or y),
    "=": (lambda x, y: x == y),
    "!=": (lambda x, y: x != y),
}


def recursive_map(func, data):
    """Recursively applies a map function to a list and all sublists."""
    if isinstance(data, list):
        return [recursive_map(func, elem) for elem in data]
    else:
        return func(data)


def string_to_bool(string):
    """Converts a string to boolean if string is either 'True' or 'False'
    otherwise returns it unchanged.
    """

    try:
        string = bool(strtobool(string))
    except ValueError:
        pass
    return string


def solve_phrase(phrase):
    """Recursively evaluates a logical phrase that has been grouped into
    sublists where each list is one operation.
    """
    if isinstance(phrase, bool):
        return phrase
    if isinstance(phrase, list):
        # list with just a list in it
        if len(phrase) == 1:
            return solve_phrase(phrase[0])
        # single operand operation
        if len(phrase) == 2:
            return OPERATIONS[phrase[0]](solve_phrase(phrase[1]))
        # double operand operation
        else:
            return OPERATIONS[phrase[1]](
                solve_phrase(phrase[0]), solve_phrase([phrase[2]])
            )


def group_operations(phrase):
    """Recursively groups logical operations into separate lists based on
    the order of operations such that each list is one operation.
    Order of operations is:
        not, and, or, implication
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
    """
    Class Truhts with modules for table formatting, valuation and CLI
    """

    def __init__(self, bases=None, phrases=None, ints=True, ascending=False):
        if not bases:
            raise Exception("Base items are required")
        self.bases = bases
        self.phrases = phrases or []
        self.ints = ints

        # generate the sets of booleans for the bases
        if ascending:
            order = [False, True]
        else:
            order = [True, False]

        self.base_conditions = list(itertools.product(order, repeat=len(bases)))

        # regex to match whole words defined in self.bases
        # used to add object context to variables in self.phrases
        self.p = re.compile(r"(?<!\w)(" + "|".join(self.bases) + r")(?!\w)")

        # used for parsing logical operations and parenthesis
        self.to_match = pyparsing.Word(pyparsing.alphanums)
        for item in itertools.chain(
            self.bases, [key for key, val in OPERATIONS.items()]
        ):
            self.to_match |= item
        self.parens = pyparsing.nestedExpr("(", ")", content=self.to_match)

    def calculate(self, *args):
        """
        Evaluates the logical value for each expression
        """
        bools = dict(zip(self.bases, args))

        eval_phrases = []
        for phrase in self.phrases:
            # substitute bases in phrase with boolean values as strings
            phrase = self.p.sub(
                lambda match: str(bools[match.group(0)]), phrase
            )  # NOQA long line
            # wrap phrase in parens
            phrase = "(" + phrase + ")"
            # parse the expression using pyparsing
            interpreted = self.parens.parseString(phrase).asList()[0]
            # convert any 'True' or 'False' to boolean values
            interpreted = recursive_map(string_to_bool, interpreted)
            # group operations
            interpreted = group_operations(interpreted)
            # evaluate the phrase
            eval_phrases.append(solve_phrase(interpreted))

        # add the bases and evaluated phrases to create a single row
        row = [val for key, val in bools.items()] + eval_phrases
        if self.ints:
            row = [int(c) for c in row]
        return row

    def as_prettytable(self):
        """
        Returns table using PrettyTable package
        """
        table = PrettyTable(self.bases + self.phrases)
        for conditions_set in self.base_conditions:
            table.add_row(self.calculate(*conditions_set))
        return table

    def as_pandas(self):
        """
        Table as Pandas DataFrame
        """
        df_columns = self.bases + self.phrases
        df = pd.DataFrame(columns=df_columns)
        for conditions_set in self.base_conditions:
            df.loc[len(df)] = self.calculate(*conditions_set)
        df.index = np.arange(1, len(df) + 1)  # index starting in one
        return df

    def as_tabulate(self, index=True, table_format="psql", align="center"):
        """
        Returns table using tabulate package
        """
        table = tabulate(
            Truths.as_pandas(self),
            headers="keys",
            tablefmt=table_format,
            showindex=index,
            colalign=[align]
            * (len(Truths.as_pandas(self).columns) + index),  # NOQA long
        )
        return table

    def valuation(self, col_number=-1):
        """
        Evaluates an expression in a table column as a tautology, a
        contradiction or a contingency
        """
        df = Truths.as_pandas(self)
        if col_number == -1:
            pass
        elif col_number not in range(1, len(df.columns) + 1):
            raise Exception("Indexer is out-of-bounds")
        else:
            col_number = col_number - 1

        if sum(df.iloc[:, col_number]) == len(df):
            val = "Tautology"
        elif sum(df.iloc[:, col_number]) == 0:
            val = "Contradiction"
        else:
            val = "Contingency"
        return val

    def __str__(self):
        table = Truths.as_tabulate(self, index=False)
        return str(table)
