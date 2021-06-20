from discord.ext import commands as cmd


class ParrotError(cmd.CheckFailure):
    pass


class NotGuildOwner(ParrotError):
    def __init__(self):
        super().__init__(
            "Error: Not Guild Owner. You must be the owner of the Server to use this command."
        )


class NotPremiumUser(ParrotError):
    def __init__(self):
        super().__init__(
            "Error: Not Premium User. You must be premium member to use this command."
        )


class NotPremiumGuild(ParrotError):
    def __init__(self):
        super().__init__(
            "Error: Not Premium Guild. This server must be premium as to use this command."
        )


class NotMe(ParrotError):
    def __init__(self):
        super().__init__(
            "Error: Not !! Ritik Ranjan [\*.*]#9230. I don't know how you reach this error. Thing is, you can't use this command."
        )
