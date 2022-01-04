from core import Parrot
from ._snakes_cog import Snakes


def setup(bot: Parrot) -> None:
    """Load the Snakes Cog."""
    bot.add_cog(Snakes(bot))
