from discord.ext import commands as cmd
from utilities.config import SUPPORT_SERVER


class ParrotCheckFailure(cmd.CheckFailure):
    pass


class CustomError(ParrotCheckFailure):
    def __init__(self, msg: str):
        super().__init__(msg)


class ParrotTimeoutError(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You did't responded on time!")


class StarError(CustomError):
    pass


class TimeError(ParrotCheckFailure):
    def __init__(self):
        super().__init__("Make sure you use the proper syntax. Ex. `1h30m` or `3600s` or just `45`")


class NoModRole(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You are missing Moderator role to use this command")


class NoVerifiedRoleTicket(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You are missing Ticket Verified role or the required permission to use this command")


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
        super().__init__("Bot must in voice channel to use this command.")


class NotVoter(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            "You must be a voter to use this command. To vote should be on [top.gg](https://top.gg/bot/800780974274248764/vote)"
        )


class NotPremiumServer(ParrotCheckFailure):
    def __init__(self):
        super().__init__("This command is only available on the premium server.")


class NotInSupportServer(ParrotCheckFailure):
    def __init__(self):
        super().__init__(
            f"You must be in the support server to use this command. To join the support server ({SUPPORT_SERVER})"
        )


class NotSameVoice(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You must be in same voice channel as the bot to use the this command.")


class NotGuildOwner(ParrotCheckFailure):
    def __init__(self):
        super().__init__("You must be the owner of the Server to use this command")


class NotMe(ParrotCheckFailure):
    def __init__(self):
        super().__init__("I don't know how you reach this error. Thing is, you can't use this command")


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
