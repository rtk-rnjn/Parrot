from discord.ext import commands as cmd
import random

with open("extra/quote.txt") as f:
    quote = f.read()

quote = quote.split('\n')


class ParrotCheckFaliure(cmd.CheckFailure):
    pass


class ParrotCheckAnyFailure(cmd.CheckAnyFailure):
		pass


class NotMod(ParrotCheckAnyFailure):
		def __init__(self):
				super().__init__(
					f"{random.choice(quote)}\n\nNot Mod. You are missing Mod role or the required permission to use this command."
				)


class NoVerifiedRoleTicket(ParrotCheckAnyFailure):
		def __init__(self):
				super().__init__(
					f"{random.choice(quote)}\n\nNot Verified Role. You are missing Ticket Verified role or the required permission to use this command."
				)


class NotGuildOwner(ParrotCheckFaliure):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot Guild Owner. You must be the owner of the Server to use this command."
        )


class NotPremiumUser(ParrotCheckFaliure):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot Premium User. You must be premium member to use this command."
        )


class NotPremiumGuild(ParrotCheckFaliure):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot Premium Guild. This server must be premium as to use this command."
        )


class NotMe(ParrotCheckFaliure):
    def __init__(self):
        super().__init__(
            f"{random.choice(quote)}\n\nNot !! Ritik Ranjan [\*.*]#9230. I don't know how you reach this error. Thing is, you can't use this command."
        )
