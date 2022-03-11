from discord.ext import commands as cmd


class ParrotCheckFailure(cmd.CheckFailure):
    pass


class ParrotTimeoutError(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            "You did't responded on time!"
        )


class TimeError(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            "Make sure you use the proper syntax. Ex. `1h30m` or `3600s` or just `45`"
        )


class NoModRole(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You are missing Moderator role to use this command")


class NoVerifiedRoleTicket(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            "You are missing Ticket Verified role or the required permission to use this command"
        )


class InHubVoice(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            "You must be in your own Hub channel to use this command"
        )


class NotGuildOwner(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You must be the owner of the Server to use this command")


class NotMe(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            "I don't know how you reach this error. Thing is, you can't use this command"
        )


# command disabled


class DisabledCommandChannel(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this channel")


class CommandDisabledCategory(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this category")


class CommandDisabledServer(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this server")
