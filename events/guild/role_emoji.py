from core import Cog, Parrot


class GuildRoleEmoji(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_role_create(self, role):
        pass

    @Cog.listener()
    async def on_guild_role_delete(self, role):
        parrot_db = await self.bot.db('parrot_db')

        if data := await parrot_db['server_config'].find_one({'_id': role.guild.id}):
            if data['mod_role'] == role.id:
                await parrot_db['server_config'].update_one({'_id': role.guild.id}, {'$set': {'mod_role': None}})
            if data['mute_role'] == role.id:
                await parrot_db['server_config'].update_one({'_id': role.guild.id}, {'$set': {'mute_role': None}})

        if data := await parrot_db['global_chat'].find_one({'_id': role.guild.id}):
            if data['ignore-role'] == role.id:
                await parrot_db['global_chat'].update_one({'_id': role.guild.id}, {'$set': {'ignore-role': None}})

        if data := await parrot_db['telephone'].find_one({'_id': role.guild.id}):
            if data['pingrole'] == role.id:
                await parrot_db['telephone'].update_one({'_id': role.guild.id}, {'$set': {'pingrole': None}})

        if data := await parrot_db['ticket'].find_one({'_id': role.guild.id}):
            await parrot_db['ticket'].update_one({'_id': role.guild.id}, {'$pull': {'valid-roles': role.id, 'pinged-roles': role.id, 'verified-roles': role.id}})

    @Cog.listener()
    async def on_guild_role_update(self, before, after):
        pass

    @Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        pass


def setup(bot):
    bot.add_cog(GuildRoleEmoji(bot))
