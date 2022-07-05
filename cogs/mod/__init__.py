from __future__ import annotations

from core import Parrot

from .anti_links import LinkProt
from .emoji_caps_prot import EmojiCapsProt
from .mention_prot import MentionProt
from .mod import Moderator
from .profanity import Profanity
from .spam_prot import SpamProt


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Moderator(bot))
    await bot.add_cog(Profanity(bot))
    await bot.add_cog(LinkProt(bot))
    await bot.add_cog(SpamProt(bot))
    await bot.add_cog(EmojiCapsProt(bot))
    await bot.add_cog(MentionProt(bot))
