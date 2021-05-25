import sys
import os
import logging


def setup_logging():
    DEBUG_MODE = 'DEBUG' in os.environ

    log_format = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(log_format)

    logger = logging.getLogger("pydispix")
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    logger.addHandler(stream_handler)
