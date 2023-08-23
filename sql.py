from __future__ import annotations

import os
import sqlite3

import tabulate
from colorama import Fore, just_fix_windows_console

con = sqlite3.connect("cached.sqlite")
cur = con.cursor()

if os.name == "nt":
    just_fix_windows_console()


# shutup, i know this is bad, but it's just a quick script


def parse_input(query: str) -> sqlite3.Cursor | str:
    try:
        cursor = cur.execute(query)
    except sqlite3.OperationalError as e:
        return f"Invalid input {e}"
    else:
        return cursor


while True:
    query = input(f"{Fore.CYAN}SQL> {Fore.RESET}")
    if query.lower() in {"exit", "quit"}:
        break

    if query.lower() in {"cls", "clear"}:
        if os.name == "nt":
            os.system("cls")
        elif os.name == "posix":
            os.system("clear")
        continue

    result = parse_input(query)
    if isinstance(result, str):
        print(result)
        continue

    if r := result.fetchall():
        headers = [description[0] for description in result.description]
        table = tabulate.tabulate(r, headers=headers, tablefmt="psql")
        print(table)
    print(f"{Fore.WHITE}Query OK: {Fore.RED}{result.rowcount}{Fore.WHITE} rows affected{Fore.RESET}")

    con.commit()

con.close()
