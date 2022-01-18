from discord.ext import commands as cmd


class ParrotCheckFaliure(cmd.CheckFailure):
    pass


class TimeError(ParrotCheckFaliure):
    def __init__(self):
        super().__init__(
            "Make sure you use the proper syntax. Ex. `1h30m` or `3600s` or just `45`"
        )


class NoModRole(ParrotCheckFaliure):
    def __init__(self):
        super().__init__("You are missing Mod role to use this command")


class NoVerifiedRoleTicket(ParrotCheckFaliure):
    def __init__(self):
        super().__init__(
            "You are missing Ticket Verified role or the required permission to use this command"
        )


class NotGuildOwner(ParrotCheckFaliure):
    def __init__(self):
        super().__init__("You must be the owner of the Server to use this command")


class NotMe(ParrotCheckFaliure):
    def __init__(self):
        super().__init__(
            "I don't know how you reach this error. Thing is, you can't use this command"
        )


# command disabled


class DisabledCommandChannel(ParrotCheckFaliure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this channel")


class CommandDisabledCategory(ParrotCheckFaliure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this category")


class CommandDisabledServer(ParrotCheckFaliure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this server")
