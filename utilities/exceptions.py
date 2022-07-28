from discord.ext import commands as cmd


class ParrotCheckFailure(cmd.CheckFailure):
    pass


class ParrotTimeoutError(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You did't responded on time!")


class StarError(ParrotCheckFailure):
    def __init__(self, error: str):
        super().__init__(error)


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
        super().__init__("You must be in your own Hub channel to use this command")


class NoDJRole(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You must have DJ role to use this command.")


class NotInVoice(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You must be in a voice channel to use this command.")


class NotBotInVoice(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Bot is not is voice channel")


class NotSameVoice(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You must be in same voice channel as the bot to use the this command.")


class NotGuildOwner(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You must be the owner of the Server to use this command")


class NotMe(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            "I don't know how you reach this error. Thing is, you can't use this command"
        )


# command disabled


class CommandDisabledChannel(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this channel")


class CommandDisabledRole(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled for this role")


class CommandDisabledServer(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Command Disabled. This command is disabled in this server")
