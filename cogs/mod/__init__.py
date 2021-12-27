from __future__ import annotations

from .mod import Mod
from .profanity import Profanity
from .anti_links import LinkProt
from .spam_prot import SpamProt
from .emoji_caps_prot import EmojiCapsProt
from .mention_prot import MentionProt

from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Mod(bot))
    bot.add_cog(Profanity(bot))
    bot.add_cog(LinkProt(bot))
    bot.add_cog(SpamProt(bot))
    bot.add_cog(EmojiCapsProt(bot))
    bot.add_cog(MentionProt(bot))
