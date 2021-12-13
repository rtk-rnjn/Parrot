from __future__ import annotations
from core.Parrot import Parrot

from discord.ext import commands
import discord, typing, asyncio, io, functools
from utilities.emotes import emojis

__all__ = ("Context", )

THUMBS_UP = "\N{THUMBS UP SIGN}"

CONFIRM_REACTIONS = (
    THUMBS_UP,
    "\N{THUMBS DOWN SIGN}",
)


class ConfirmationView(discord.ui.View):
    def __init__(self, *, timeout: float, author_id: int, reacquire: bool,
                 ctx: Context, delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: typing.Optional[bool] = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.ctx: Context = ctx
        self.reacquire: bool = reacquire
        self.message: typing.Optional[discord.Message] = None

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        else:
            await interaction.response.send_message(
                'This confirmation dialog is not for you.', ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.reacquire:
            await self.ctx.acquire()
        if self.delete_after and self.message:
            await self.message.delete()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button,
                      interaction: discord.Interaction):
        self.value = True
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button,
                     interaction: discord.Interaction):
        self.value = False
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_message()
        self.stop()


class Context(commands.Context):
    """A custom implementation of commands.Context class."""
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
    
    def __repr__(self):
        # we need this for our cache key strategy
        return f'<{self.bot.user.name} Context>'
    
    @property
    def session(self):
        return self.bot.session

    @discord.utils.cached_property
    def replied_reference(self):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    def with_type(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            context = args[0] if isinstance(args[0],
                                            commands.Context) else args[1]
            try:
                async with context.typing():
                    await func(*args, **kwargs)
            except discord.Forbidden:
                await func(*args, **kwargs)

        return wrapped

    async def show_help(self, command=None):
        cmd = self.bot.get_command('help')
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)

    async def send(self,
                   content: typing.Optional[str] = None,
                   **kwargs) -> typing.Optional[discord.Message]:
        if not (self.channel.permissions_for(self.me)).send_messages:
            try:
                await self.author.send(
                    "Bot don't have permission to send message in that channel. Please give me sufficient permissions to do so."
                )
            except discord.Forbidden:
                pass
            return

        return await super().send(content, **kwargs)

    async def entry_to_code(self, entries):
        width = max(len(a) for a, b in entries)
        output = ['```']
        for name, entry in entries:
            output.append(f'{name:<{width}}: {entry}')
        output.append('```')
        await self.send('\n'.join(output))

    async def indented_entry_to_code(self, entries):
        width = max(len(a) for a, b in entries)
        output = ['```']
        for name, entry in entries:
            output.append(f'\u200b{name:>{width}}: {entry}')
        output.append('```')
        await self.send('\n'.join(output))

    async def emoji(self, emoji: str) -> str:
        return emojis[emoji]

    async def prompt(self,
                     message: str,
                     *,
                     timeout: float = 60.0,
                     delete_after: bool = True,
                     reacquire: bool = True,
                     author_id: typing.Optional[int] = None,
                     **kwargs) -> typing.Optional[bool]:
        author_id = author_id or self.author.id
        view = ConfirmationView(
            timeout=timeout,
            delete_after=delete_after,
            reacquire=reacquire,
            ctx=self,
            author_id=author_id,
        )
        view.message = await self.send(message, view=view, **kwargs)
        await view.wait()
        return view.value

    async def release(self):
        await asyncio.sleep(0)

    async def safe_send(self, content, *, escape_mentions=True, **kwargs):
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop('file', None)
            return await self.send(file=discord.File(
                fp, filename='message_too_long.txt'),
                                   **kwargs)
        else:
            return await self.send(content)

    async def bulk_add_reactions(self, message: discord.Message, *reactions: typing.Union[discord.Emoji, str]) -> None:
        coros = [asyncio.ensure_future(message.add_reaction(reaction)) for reaction in reactions]
        await asyncio.wait(coros)
    
    async def confirm(
        self,
        bot: Parrot,
        channel: discord.TextChannel,
        user: typing.Union[discord.Member, discord.User],
        *args: typing.Any,
        timeout: float = 60,
        delete_after: bool = False,
        **kwargs: typing.Any,
    ) -> typing.Optional[bool]:
        message = await channel.send(*args, **kwargs)
        await self.bulk_add_reactions(message, *CONFIRM_REACTIONS)

        def check(payload: discord.RawReactionActionEvent) -> bool:
            return (
                payload.message_id == message.id and payload.user_id == user.id and str(payload.emoji) in CONFIRM_REACTIONS
            )

        try:
            payload = await bot.wait_for("raw_reaction_add", check=check, timeout=timeout)
            return str(payload.emoji) == THUMBS_UP
        except asyncio.TimeoutError:
            return None
        finally:
            if delete_after:
                await message.delete()
