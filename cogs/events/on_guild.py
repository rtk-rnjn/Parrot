from core import Parrot, Cog
from database.global_chat import gchat_on_join, gchat_on_remove
from database.telephone import telephone_on_join, telephone_on_remove
from database.ticket import ticket_on_join, ticket_on_remove
from database.logging import logging_on_join, logging_on_remove
from database.server_config import guild_join, guild_remove


class OnGuildJoin(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild):
        await gchat_on_join(guild.id)
        await telephone_on_join(guild.id)
        await ticket_on_join(guild.id)
        await logging_on_join(guild.id)
        await guild_join(guild.id)

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                channel.send(
                    "Thank you for adding me to this server! Default prefix are `$` and `@Parrot` (Mention)!"
                )
                break

    @Cog.listener()
    async def on_guild_remove(self, guild):
        await gchat_on_remove(guild.id)
        await telephone_on_remove(guild.id)
        await ticket_on_remove(guild.id)
        await logging_on_remove(guild.id)
        await guild_remove(guild.id)


def setup(bot):
    bot.add_cog(OnGuildJoin(bot))
