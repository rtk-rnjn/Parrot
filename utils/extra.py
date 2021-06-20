from traceback import format_exception
import logging


def load_ext(bot, extensions: list):
    for ext in extensions:
        try:
            bot.load_extension(ext)
            print(ext)
        except Exception as e:
            tb = format_exception(type(e), e, e.__traceback__)
            tbe = "".join(tb) + ""
            print(tbe)


def logger(get_logger: str, file_name: str):
    """Main file to start the logging system"""

    logger = logging.getLogger(get_logger)

    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename=file_name,
                                  encoding='utf-8',
                                  mode='w')
    handler.setFormatter(
        logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

    logger.addHandler(handler)
