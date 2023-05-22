import re
import string
import unicodedata
from typing import Dict, List

import discord

FILENAME_STRING = "{effect}_{author}.png"


def replace_many(
    sentence: str,
    replacements: Dict[str, str],
    *,
    ignore_case: bool = False,
    match_case: bool = False,
) -> str:
    if ignore_case:
        replacements = {
            word.lower(): replacement for word, replacement in replacements.items()
        }

    words_to_replace = sorted(replacements, key=lambda s: (-len(s), s))

    # Join and compile words to replace into a regex
    pattern = "|".join(re.escape(word) for word in words_to_replace)
    regex = re.compile(pattern, re.I if ignore_case else 0)

    def _repl(match: re.Match) -> str:
        """Returns replacement depending on `ignore_case` and `match_case`."""
        word: str = match[0]
        replacement = replacements[word.lower() if ignore_case else word]

        if not match_case:
            return replacement

        # Clean punctuation from word so string methods work
        cleaned_word = word.translate(str.maketrans("", "", string.punctuation))
        if cleaned_word.isupper():
            return replacement.upper()
        if cleaned_word[0].isupper():
            return replacement.capitalize()
        return replacement.lower()

    return regex.sub(_repl, sentence)


def file_safe_name(effect: str, display_name: str) -> str:
    """Returns a file safe filename based on the given effect and display name."""
    valid_filename_chars = f"-_. {string.ascii_letters}{string.digits}"

    file_name = FILENAME_STRING.format(effect=effect, author=display_name)

    # Replace spaces
    file_name = file_name.replace(" ", "_")

    # Normalize unicode characters
    cleaned_filename = (
        unicodedata.normalize("NFKD", file_name).encode("ASCII", "ignore").decode()
    )

    # Remove invalid filename characters
    cleaned_filename = "".join(c for c in cleaned_filename if c in valid_filename_chars)
    return cleaned_filename


class AnagramGame:
    """
    Used for creating instances of anagram games.
    Once multiple games can be run at the same time, this class' instances
    can be used for keeping track of each anagram game.
    """

    def __init__(self, scrambled: str, correct: List[str]) -> None:
        self.scrambled = scrambled
        self.correct = set(correct)

        self.winners = set()

    async def message_creation(self, message: discord.Message) -> None:
        """Check if the message is a correct answer and remove it from the list of answers."""
        if message.content.lower() in self.correct:
            self.winners.add(message.author.mention)
            self.correct.remove(message.content.lower())


def suppress_links(message: str) -> str:
    """Accepts a message that may contain links, suppresses them, and returns them."""
    for link in set(re.findall(r"https?://[^\s]+", message, re.IGNORECASE)):
        message = message.replace(link, f"<{link}>")
    return message
