from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .automod import Automod
from .timers import AutomodTimers

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Automod(bot))
    await bot.add_cog(AutomodTimers(bot))
