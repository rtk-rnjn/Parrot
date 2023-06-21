from __future__ import annotations

import re
from typing import Dict, List

from yaml import safe_load as yaml_load  # type: ignore

import discord
from core import Parrot
from discord.ext import commands

from ._tio import Tio

with open("extra/lang.txt", encoding="utf-8", errors="ignore") as f:
    languages = f.read().split("\n")

wrapping: Dict[str, str] = {
    "c": "#include <stdio.h>\nint main() {code}",
    "cpp": "#include <iostream>\nint main() {code}",
    "cs": "using System;class Program {static void Main(string[] args) {code}}",
    "java": "public class Main {public static void main(String[] args) {code}}",
    "rust": "fn main() {code}",
    "d": "import std.stdio; void main(){code}",
    "kotlin": "fun main(args: Array<String>) {code}",
}

with open("extra/default_langs.yml", "r", encoding="utf-8", errors="ignore") as file:
    default_langs = yaml_load(file)


def prepare_payload(payload: str):
    try:
        language, text = re.split(r"\s+", payload, maxsplit=1)
    except ValueError:
        # single word : no code yet no file attached
        emb = discord.Embed(
            title="SyntaxError",
            description="Command `run` missing a required argument: `code`",
            colour=0xFF0000,
        )
        return ("", emb, True)

    return (language, text, False)


async def execute_run(
    bot: Parrot,
    language: str,
    code: str,  # type: ignore
) -> str:
    # Powered by tio.run

    options = {"--stats": False, "--wrapped": False}

    lang = language.strip("`").lower()

    optionsAmount = len(options)

    # Setting options and removing them from the beginning of the command
    # options may be separated by any single whitespace, which we keep in the list
    code: List[str] = re.split(r"(\s)", code, maxsplit=optionsAmount)

    for option in options:
        if option in code[: optionsAmount * 2]:
            options[option] = True
            i = code.index(option)
            code.pop(i)
            code.pop(i)  # remove following whitespace character

    code = "".join(code)  # type: ignore

    compilerFlags = []
    commandLineOptions = []
    args = []
    inputs = []

    lines = code.split("\n")  # type: ignore
    code = []
    for line in lines:
        if line.startswith("input "):
            inputs.append(" ".join(line.split(" ")[1:]).strip("`"))
        elif line.startswith("compiler-flags "):
            compilerFlags.extend(line[15:].strip("`").split(" "))
        elif line.startswith("command-line-options "):
            commandLineOptions.extend(line[21:].strip("`").split(" "))
        elif line.startswith("arguments "):
            args.extend(line[10:].strip("`").split(" "))
        else:
            code.append(line)

    inputs = "\n".join(inputs)

    code = "\n".join(code)  # type: ignore

    # common identifiers, also used in highlight.js and thus discord codeblocks
    quickmap: Dict[str, str] = {
        "asm": "assembly",
        "c#": "cs",
        "c++": "cpp",
        "csharp": "cs",
        "f#": "fs",
        "fsharp": "fs",
        "js": "javascript",
        "nimrod": "nim",
        "py": "python",
        "q#": "qs",
        "rs": "rust",
        "sh": "bash",
        "python": "python",
    }

    lang = quickmap.get(lang) or lang

    if lang in default_langs:
        lang = default_langs[lang]
    if lang not in languages:  # this is intentional
        matches = []
        i = 0
        for language in languages:
            if language.startswith(lang[:3]):
                matches.append(language)
                i += 1
                if i == 10:
                    break
        output = f"`{lang}` not available."
        if matches := "\n".join(matches):
            output = f"{output} Did you mean:\n{matches}"

        return output

    code = code.strip("`")  # type: ignore

    if "\n" in code:
        firstLine = code.splitlines()[0]  # type: ignore
        if re.fullmatch(r"([0-9A-z]*)\b", firstLine):
            code = code[len(firstLine) + 1 :]

    if options["--wrapped"]:
        if not (any(map(lambda x: lang.split("-")[0] == x, wrapping))) or lang in (
            "cs-mono-shell",
            "cs-csi",
        ):
            return f"`{lang}` cannot be wrapped."

        for beginning in wrapping:
            if lang.split("-")[0] == beginning:
                code = wrapping[beginning].replace("code", code)  # type: ignore
                break

    tio = Tio(
        lang,
        code,  # type: ignore
        compilerFlags=compilerFlags,
        inputs=inputs,
        commandLineOptions=commandLineOptions,
        args=args,
    )

    result = await tio.send()

    if not options["--stats"]:
        try:
            start = result.rindex("Real time: ")
            end = result.rindex("%\nExit code: ")
            result = result[:start] + result[end + 2 :]
        except ValueError:
            # Too much output removes this markers
            pass

    if len(result) > 1992 or result.count("\n") > 40:
        # If it exceeds 2000 characters (Discord longest message), counting ` and ph\n characters
        # Or if it floods with more than 40 lines
        # Create a hastebin and send it back
        link = await bot.mystbin.create_paste(filename="output.txt", content=result)

        if link is None:
            output = (
                "Your output was too long, but I couldn't make an online bin out of it."
            )
        else:
            output = f"Output was too long (more than 2000 characters or 40 lines) so I put it here: {link.url}"

        return output

    zero = "\N{zero width space}"
    output = re.sub("```", f"{zero}`{zero}`{zero}`{zero}", result)

    # p, as placeholder, prevents Discord from taking the first line
    # as a language identifier for markdown and remove it

    return f"```p\n{output}```"


def get_raw(link: str) -> str:
    """Returns the url for raw version on a hastebin-like"""
    link = link.strip("<>/")  # Allow for no-embed links

    authorized = (
        "https://hastebin.com",
        "https://gist.github.com",
        "https://gist.githubusercontent.com",
    )

    if not any(link.startswith(url) for url in authorized):
        raise commands.BadArgument(
            f"Bot only accept links from {', '.join(authorized)}. (Starting with 'http')."
        )

    domain = link.split("/")[2]

    if domain == "hastebin.com":
        if "/raw/" in link:
            return link
        token = link.split("/")[-1]
        if "." in token:
            token = token[: token.rfind(".")]  # removes extension
        return f"https://hastebin.com/raw/{token}"
    # Github uses redirection so raw -> usercontent and no raw -> normal
    # We still need to ensure we get a raw version after this potential redirection
    return link if "/raw" in link else f"{link}/raw"
