from discord.ext import commands as cmd
import random

with open("extra/quote.txt") as f:
    quote = f.read()

quote = quote.split('\n')


class ParrotError(cmd.CheckFailure):
    pass


class NotGuildOwner(ParrotError):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot Guild Owner. You must be the owner of the Server to use this command."
        )


class NotPremiumUser(ParrotError):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot Premium User. You must be premium member to use this command."
        )


class NotPremiumGuild(ParrotError):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot Premium Guild. This server must be premium as to use this command."
        )


class NotMe(ParrotError):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot !! Ritik Ranjan [\*.*]#9230. I don't know how you reach this error. Thing is, you can't use this command."
        )
