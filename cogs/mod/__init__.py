from __future__ import annotations

from .mod import Mod
from .profanity import Profanity
from .anti_links import LinkProt
from .nudes_detection import NudeDetection

from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Mod(bot))
    bot.add_cog(Profanity(bot))
    bot.add_cog(LinkProt(bot))
    bot.add_cog(NudeDetection)