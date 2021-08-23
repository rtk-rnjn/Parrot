from discord.ext import commands

__all__ = ("Context", )


class Context(commands.Context):
    """A custom implementation of commands.Context class."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return "{0.__class__.__name__}".format(self)
    
    async def send(self, content: any = None, **kwargs):
        if not (_perms := self.channel.permissions_for(self.me)).send_messages:
            try:
                await self.author.send(
                    f"Bot can't send any messages in {self.channel.mention} channel. Please provide sufficient permissions."
                )
            except discord.Forbidden:
                pass
            return
        await self.trigger_typing()
        await super().send(content, **kwargs)
        return