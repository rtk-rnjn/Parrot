from __future__ import annotations


from typing import TYPE_CHECKING, Optional, cast
import logging


if TYPE_CHECKING:
    LoggerClass = logging.Logger
else:
    LoggerClass = logging.getLoggerClass()

TRACE_LEVEL = 5


class CustomLogger(LoggerClass):
    """Custom implementation of the `Logger` class with an added `trace` method."""

    def trace(self, msg: str, *args, **kwargs) -> None:
        """
        Log 'msg % args' with severity 'TRACE'.
        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.
        logger.trace("Houston, we have an %s", "interesting problem", exc_info=1)
        """
        if self.isEnabledFor(TRACE_LEVEL):
            self.log(TRACE_LEVEL, msg, *args, **kwargs)


def get_logger(name: Optional[str] = None) -> CustomLogger:
    """Utility to make mypy recognise that logger is of type `CustomLogger`."""
    # no need to be honest, but why not using it
    return cast(CustomLogger, logging.getLogger(name))


def setup() -> None:
    logging.TRACE = TRACE_LEVEL
    logging.addLevelName(TRACE_LEVEL, "TRACE")
    logging.setLoggerClass(CustomLogger)
    root_log = get_logger()
    format_string = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s | %(message)s"
    log_format = logging.Formatter(format_string)
    root_log.setLevel(logging.INFO)

    get_logger("discord").setLevel(logging.WARNING)
    get_logger("websockets").setLevel(logging.WARNING)
    get_logger("chardet").setLevel(logging.WARNING)
    get_logger("pymongo").setLevel(logging.WARNING)
    get_logger("motor").setLevel(logging.WARNING)
    # Set back to the default of INFO even if asyncio's debug mode is enabled.
    get_logger("asyncio").setLevel(logging.INFO)
