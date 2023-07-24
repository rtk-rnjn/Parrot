import argparse
import ast

import ttg


def clielement():
    """CLI for the truth_table_generator package."""
    parser = argparse.ArgumentParser()
    parser.add_argument("variables", help="List of variables e. g. \"['p', 'q']\"")
    parser.add_argument(
        "-p",
        "--propositions",
        help="List of propositions e. g. \"['p or q', 'p and q']\"",
    )  # NOQA long line
    parser.add_argument("-i", "--ints", default="True", help="True for 0 and 1; False for words")
    parser.add_argument(
        "-a",
        "--ascending",
        default="False",
        help="True for reverse output (False before True)",
    )
    args = parser.parse_args()

    variables = ast.literal_eval(args.variables)
    ints = ast.literal_eval(args.ints)
    asc = ast.literal_eval(args.ascending)

    print()
    if args.propositions is None:
        propositions = []
    else:
        propositions = ast.literal_eval(args.propositions)
    print(ttg.Truths(variables, propositions, ints, asc))
    print()


if __name__ == "__main__":
    clielement()
