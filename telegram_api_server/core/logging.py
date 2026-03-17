import logging
import sys

from pythonjsonlogger import jsonlogger


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(session_name)s %(message_id)s"
        )
    )
    root.handlers = [handler]
