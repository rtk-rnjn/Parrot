from .ipc import IpcRoutes


def setup(bot):
    bot.add_cog(IpcRoutes(bot))
