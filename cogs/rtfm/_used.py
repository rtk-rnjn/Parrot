from __future__ import annotations

from discord.utils import escape_markdown
from yaml import safe_load as yaml_load

from ._tio import Tio

quickmap: dict[str, str] = {
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

with open("assets/default_langs.yml", encoding="utf-8") as file:
    default_langs = yaml_load(file)

with open("assets/lang.txt", encoding="utf-8") as file:
    languages = {line.strip() for line in file}


def resolve_language(language: str) -> str:
    language = language.lower()
    return default_langs[quickmap.get(language, language)]


def language_error(language: str) -> str:
    suggestions = [lang for lang in languages if lang.startswith(language[:3])][:10]

    message = f"`{language}` not available."

    if suggestions:
        message += " Did you mean:\n" + "\n".join(suggestions)

    return message


async def execute_run(language: str, code_string: str) -> str:
    language = resolve_language(language)

    if language not in languages:
        return language_error(language)

    result = await Tio(language, code_string).send()

    if result is None:
        return "```\n```"

    try:
        start = result.rindex("Real time: ")
        end = result.rindex("%\nExit code: ")
        result = result[:start] + result[end + 2 :]
    except ValueError:
        # Too much output removes these markers.
        pass

    return f"```\n{escape_markdown(result.strip())}```"
