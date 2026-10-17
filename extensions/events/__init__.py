from __future__ import annotations

from typing import TYPE_CHECKING

from .arbitrary import ArbitraryEvents
from .error import CommandError
from .link_to_codeblock import LinkToCodeblock
from .meta import GuildEventListener
from .registered_events import RegisteredEvents
from .scam_link_detection import ScamLinkDetection

if TYPE_CHECKING:
    from core import Bot


async def setup(bot: Bot) -> None:
    await bot.add_cog(CommandError(bot))
    await bot.add_cog(LinkToCodeblock(bot))
    await bot.add_cog(ScamLinkDetection(bot))
    await bot.add_cog(ArbitraryEvents(bot))
    await bot.add_cog(RegisteredEvents(bot))
    await bot.add_cog(GuildEventListener(bot))
