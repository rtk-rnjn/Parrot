from __future__ import annotations

from discord.ext import commands

BASIC_USAGE = """
1. <foo> - This argument is mandatory
2. <foos...> - This argument is mandatory and can take multiple values
3. [foo] - This argument is optional
4. [foos...] - This argument is optional and can take multiple values
5. [foo=bar] - This argument is optional and has a default value of `bar`
6. [foo|bar] - This argument is optional so you can either use foo or bar, or don't specify it at all

Additionally, the bot uses converters which makes specifying roles, members, channels etc, easy and fool-proof. When asked to specify a member, you can provide it a mention, an id, a name or a nickname. This principle works for every single command where applicable.

Note: Do not literally type out `<` `>` `[` `]` `|` etc.
"""
class Help(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__(
            command_attrs={
                "help": "Shows this message.",
                "description": "Shows this message.",
            },
        )

    async def send_bot_help(self, mapping: dict[commands.Cog | None, list[commands.Command]]) -> None:
        ctx = self.context
        destination = self.get_destination()


        data = {cog: mapping[cog] for cog in mapping if cog is not None and mapping[cog]}
