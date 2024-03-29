from __future__ import annotations

import logging
import logging.handlers

from colorama import Fore


def handler(filename: str) -> logging.handlers.RotatingFileHandler:
    return logging.handlers.RotatingFileHandler(
        filename=filename,
        encoding="utf-8",
        maxBytes=1 * 1024 * 1024,  # 1 MiB
        backupCount=1,  # Rotate through 1 files
    )


DT_FMT = "%Y-%m-%d %H:%M:%S"


class StreamFormatter(logging.Formatter):
    GRAY = f"{Fore.LIGHTBLACK_EX}"
    GREY = GRAY

    RED = f"{Fore.RED}"
    YELLOW = f"{Fore.YELLOW}"
    GREEN = f"{Fore.GREEN}"
    WHITE = f"{Fore.WHITE}"
    BLUE = f"{Fore.BLUE}"
    CYAN = f"{Fore.CYAN}"

    RESET = f"{Fore.RESET}"

    fmt = "{} %(asctime)s {} - {} %(name)s {} - {} %(levelname)s {} - {} %(message)s {} ({}%(filename)s/%(module)s.%(funcName)s{}:{}%(lineno)d{}){}"

    # fmt: off
    formats = {
        logging.DEBUG   : fmt.format(WHITE, WHITE, YELLOW, WHITE, GRAY  , WHITE, BLUE, WHITE, CYAN, YELLOW, GREEN, WHITE, RESET),
        logging.INFO    : fmt.format(WHITE, WHITE, YELLOW, WHITE, GREEN , WHITE, BLUE, WHITE, CYAN, YELLOW, GREEN, WHITE, RESET),
        logging.WARNING : fmt.format(WHITE, WHITE, YELLOW, WHITE, YELLOW, WHITE, BLUE, WHITE, CYAN, YELLOW, GREEN, WHITE, RESET),
        logging.ERROR   : fmt.format(WHITE, WHITE, YELLOW, WHITE, RED   , WHITE, BLUE, WHITE, CYAN, YELLOW, GREEN, WHITE, RESET),
        logging.CRITICAL: fmt.format(WHITE, WHITE, YELLOW, WHITE, RED   , WHITE, BLUE, WHITE, CYAN, YELLOW, GREEN, WHITE, RESET),
    }
    # fmt: on

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        log_fmt = self.formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt, DT_FMT)
        return formatter.format(record)


class FileStreamFormatter(logging.Formatter):
    """Discord Stream Formatter"""

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s - (%(filename)s/%(module)s.%(funcName)s:%(lineno)d)"

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        formatter = logging.Formatter(self.fmt, DT_FMT)
        return formatter.format(record)
