from __future__ import annotations

from .mod import Moderator
from .profanity import Profanity
from .anti_links import LinkProt
from .spam_prot import SpamProt
from .emoji_caps_prot import EmojiCapsProt
from .mention_prot import MentionProt

from core import Parrot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Moderator(bot))
    await bot.add_cog(Profanity(bot))
    await bot.add_cog(LinkProt(bot))
    await bot.add_cog(SpamProt(bot))
    await bot.add_cog(EmojiCapsProt(bot))
    await bot.add_cog(MentionProt(bot))
