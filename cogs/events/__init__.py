from __future__ import annotations

from typing import TYPE_CHECKING

from .error import CommandError
from .link_to_codeblock import LinkToCodeblock
from .scam_link_detection import ScamLinkDetection

if TYPE_CHECKING:
    from core import Parrot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(CommandError(bot))
    await bot.add_cog(LinkToCodeblock(bot))
    await bot.add_cog(ScamLinkDetection(bot))
