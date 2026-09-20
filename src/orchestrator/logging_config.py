import json
import logging
from datetime import datetime, timezone

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    """Minimal structured (JSON Lines) log formatter — one JSON object per line.

    No third-party dependency: this project's logging volume doesn't justify one,
    and a stdlib Formatter subclass covers what a log aggregator actually needs
    (timestamp, level, logger, message, exception, plus any `extra=` fields).
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Configures root logging to emit JSON lines to stdout.

    Called explicitly from every real entrypoint (the CLI loop and the API's
    startup) rather than as an import-time side effect, so importing this
    package for tests doesn't reconfigure global logging as a side effect.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
