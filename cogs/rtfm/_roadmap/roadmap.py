from __future__ import annotations

from core import Cog, Parrot


class Roadmap(Cog):
    """Roadmap.sh scraper. Please visit https://roadmap.sh/ for more information."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
