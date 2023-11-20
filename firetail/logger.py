import logging
import sys
from threading import Lock

configured_loggers_lock = Lock()
configured_loggers = set()


def get_stdout_logger(debug):
    stdout_logger_name = __name__ + "_stdout"
    stdout_logger = logging.getLogger(stdout_logger_name)

    requires_config = False
    with configured_loggers_lock:
        if stdout_logger_name not in configured_loggers:
            configured_loggers.add(stdout_logger_name)
            requires_config = True

    if requires_config:
        stdout_logger.propagate = False
        stdout_logger.setLevel(logging.DEBUG if debug else logging.INFO)
        stdout_logger.addHandler(logging.StreamHandler(sys.stdout))

    return stdout_logger
